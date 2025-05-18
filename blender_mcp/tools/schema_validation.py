"""
Blender GraphQL MCP - スキーマ検証モジュール
GraphQLスキーマの整合性を検証する機能
"""

import logging
from typing import Dict, Any, List, Set, Optional
from tools import (
    GraphQLSchema,
    GraphQLObjectType,
    GraphQLField,
    GraphQLNonNull,
    GraphQLList,
    GraphQLScalarType
)

logger = logging.getLogger("blender_graphql_mcp.tools.definitions_validation")

def validate_schema(schema: GraphQLSchema) -> Dict[str, Any]:
    """
    GraphQLスキーマの整合性を検証
    - リゾルバ関数の存在確認
    - 型定義の問題検出
    - 命名規則の一貫性チェック
    
    Args:
        schema: 検証するGraphQLスキーマ
        
    Returns:
        検証結果を含む辞書
    """
    results = {
        "valid": True,
        "missing_resolvers": [],
        "type_issues": [],
        "naming_issues": [],
        "potential_duplicates": []
    }
    
    if not schema:
        results["valid"] = False
        results["general_error"] = "スキーマがNoneです"
        return results
    
    # リゾルバモジュールの取得
    try:
        import sys
        resolver_module = sys.modules.get('RESOLVER_MODULE')
        if not resolver_module:
            import tools.resolver as default_resolver_module
            resolver_module = default_resolver_module
    except ImportError:
        logger.error("リゾルバモジュールを読み込めませんでした")
        results["valid"] = False
        results["general_error"] = "リゾルバモジュールが利用できません"
        return results
    
    # リゾルバ関数のチェック
    missing_resolvers = _check_resolvers(schema, resolver_module)
    if missing_resolvers:
        results["valid"] = False
        results["missing_resolvers"] = missing_resolvers
    
    # 命名規則の一貫性チェック
    naming_issues = _check_naming_conventions(schema)
    if naming_issues:
        results["naming_issues"] = naming_issues
    
    # 重複の可能性があるフィールドの検出
    potential_duplicates = _check_potential_duplicates(schema)
    if potential_duplicates:
        results["potential_duplicates"] = potential_duplicates
    
    # 型定義の問題検出
    type_issues = _check_type_definitions(schema)
    if type_issues:
        results["type_issues"] = type_issues
    
    return results

def _check_resolvers(schema: GraphQLSchema, resolver_module) -> List[str]:
    """リゾルバ関数の存在を確認"""
    missing_resolvers = []
    
    # クエリフィールドの確認
    query_type = schema.query_type
    if query_type:
        for field_name, field in query_type.fields.items():
            resolver_name = field.resolve.__name__ if hasattr(field, 'resolve') and field.resolve else None
            if not resolver_name or not hasattr(resolver_module, resolver_name):
                missing_resolvers.append(f"Query.{field_name}")
    
    # ミューテーションフィールドの確認
    mutation_type = schema.mutation_type
    if mutation_type:
        for field_name, field in mutation_type.fields.items():
            resolver_name = field.resolve.__name__ if hasattr(field, 'resolve') and field.resolve else None
            if not resolver_name or not hasattr(resolver_module, resolver_name):
                missing_resolvers.append(f"Mutation.{field_name}")
    
    return missing_resolvers

def _check_naming_conventions(schema: GraphQLSchema) -> List[str]:
    """命名規則の一貫性をチェック"""
    naming_issues = []
    
    # タイプ名のチェック（PascalCase）
    for type_name, type_def in schema.type_map.items():
        if type_name.startswith("__"):  # 内部型はスキップ
            continue
        
        # 型名はPascalCaseであるべき
        if not type_name[0].isupper() or "_" in type_name:
            naming_issues.append(f"型名 '{type_name}' はPascalCase形式ではありません")
    
    # フィールド名のチェック（camelCase）
    query_type = schema.query_type
    if query_type:
        for field_name in query_type.fields:
            if field_name.startswith("_"):  # 特殊フィールドはスキップ
                continue
            
            # フィールド名はcamelCaseであるべき
            if field_name[0].isupper() or "-" in field_name:
                naming_issues.append(f"クエリフィールド '{field_name}' はcamelCase形式ではありません")
    
    # ミューテーションフィールド名のチェック
    mutation_type = schema.mutation_type
    if mutation_type:
        for field_name in mutation_type.fields:
            if "." not in field_name and not field_name[0].islower():
                naming_issues.append(f"ミューテーションフィールド '{field_name}' はcamelCaseまたはdomain.operation形式ではありません")
    
    return naming_issues

def _check_potential_duplicates(schema: GraphQLSchema) -> List[str]:
    """潜在的な重複フィールドを検出"""
    potential_duplicates = []
    
    # ミューテーションフィールドの確認
    mutation_type = schema.mutation_type
    if mutation_type:
        field_purposes = {}  # 目的ごとのフィールドリスト
        
        for field_name in mutation_type.fields:
            # ドメイン部分を取得（例: mesh.create → mesh）
            domain = field_name.split('.')[0] if '.' in field_name else ""
            
            # 操作名を取得（例: mesh.create → create）
            operation = field_name.split('.')[-1] if '.' in field_name else field_name
            
            # 同様の操作を行う可能性のあるフィールドを検出
            for other_field in mutation_type.fields:
                if other_field == field_name:
                    continue
                
                other_operation = other_field.split('.')[-1] if '.' in other_field else other_field
                
                # 操作名が類似している場合（例: create/createMesh）
                if operation in other_operation or other_operation in operation:
                    key = f"{operation}/{other_operation}"
                    if key not in field_purposes:
                        field_purposes[key] = []
                    
                    if f"{field_name} と {other_field}" not in field_purposes[key] and f"{other_field} と {field_name}" not in field_purposes[key]:
                        field_purposes[key].append(f"{field_name} と {other_field}")
        
        # 類似操作をリストアップ
        for purpose, fields in field_purposes.items():
            for field_pair in fields:
                potential_duplicates.append(f"類似操作: {field_pair}")
    
    return potential_duplicates

def _check_type_definitions(schema: GraphQLSchema) -> List[str]:
    """型定義の問題を検出"""
    type_issues = []
    
    # 基本レスポンス型のフィールドをチェック
    response_types = []
    for type_name, type_def in schema.type_map.items():
        if type_name.startswith("__"):  # 内部型はスキップ
            continue
        
        if "Result" in type_name or "Response" in type_name:
            response_types.append(type_name)
            
            # 基本フィールドの存在チェック
            if hasattr(type_def, 'fields'):
                has_success = 'success' in type_def.fields
                has_status = 'status' in type_def.fields
                has_message = 'message' in type_def.fields
                
                if not (has_success and has_message):
                    type_issues.append(f"レスポンス型 '{type_name}' に必須フィールド(success/message)が不足しています")
    
    # 入力型のチェック
    input_types = []
    for type_name, type_def in schema.type_map.items():
        if type_name.startswith("__"):  # 内部型はスキップ
            continue
            
        if "Input" in type_name:
            input_types.append(type_name)
            
            # NonNullフィールドの適切な使用をチェック
            if hasattr(type_def, 'fields'):
                for field_name, field in type_def.fields.items():
                    if isinstance(field.type, GraphQLNonNull) and "id" not in field_name.lower() and "required" not in field_name.lower():
                        # 必須フィールドの命名が明確かチェック
                        type_issues.append(f"必須入力フィールド '{type_name}.{field_name}' は命名に 'Required' または 'Id' を含めるべきです")
    
    return type_issues
