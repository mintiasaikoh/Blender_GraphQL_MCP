"""
Blender GraphQL MCP - 命名規則ツール
GraphQLスキーマの命名規則を統一するためのユーティリティ
"""

import re
import logging
from typing import Dict, Any, List, Set, Tuple, Optional

logger = logging.getLogger("blender_graphql_mcp.tools.schema_naming")

# グローバル設定
DOMAIN_DELIMITER = "."  # ドメイン.操作 形式のデリミタ

def to_camel_case(snake_str: str) -> str:
    """スネークケースをキャメルケースに変換

    Args:
        snake_str: スネークケース文字列（例: "create_object"）

    Returns:
        キャメルケース文字列（例: "createObject"）
    """
    components = snake_str.split('_')
    # 最初の単語はそのまま、2単語目以降は先頭を大文字に
    return components[0] + ''.join(x.title() for x in components[1:])

def to_pascal_case(snake_str: str) -> str:
    """スネークケースをパスカルケースに変換

    Args:
        snake_str: スネークケース文字列（例: "create_object"）

    Returns:
        パスカルケース文字列（例: "CreateObject"）
    """
    components = snake_str.split('_')
    # すべての単語の先頭を大文字に
    return ''.join(x.title() for x in components)

def to_snake_case(camel_str: str) -> str:
    """キャメルケースまたはパスカルケースをスネークケースに変換

    Args:
        camel_str: キャメルケースまたはパスカルケース文字列（例: "createObject"）

    Returns:
        スネークケース文字列（例: "create_object"）
    """
    # 大文字の前にアンダースコアを挿入し、すべて小文字に変換
    pattern = re.compile(r'(?<!^)(?=[A-Z])')
    return pattern.sub('_', camel_str).lower()

def create_field_name(domain: str, operation: str) -> str:
    """ドメインと操作からフィールド名を生成

    Args:
        domain: ドメイン名（例: "object"）
        operation: 操作名（例: "create"）

    Returns:
        ドメイン.操作形式のフィールド名（例: "object.create"）
    """
    return f"{domain}{DOMAIN_DELIMITER}{operation}"

def parse_field_name(field_name: str) -> Tuple[str, str]:
    """フィールド名からドメインと操作を解析

    Args:
        field_name: ドメイン.操作形式のフィールド名（例: "object.create"）

    Returns:
        (ドメイン, 操作)のタプル（例: ("object", "create")）
    """
    if DOMAIN_DELIMITER in field_name:
        domain, operation = field_name.split(DOMAIN_DELIMITER, 1)
        return domain, operation
    else:
        # デリミタがない場合は全体を操作として扱い、ドメインは空文字列
        return "", field_name

def create_type_name(domain: str, operation: str, suffix: str = "Result") -> str:
    """ドメインと操作から型名を生成

    Args:
        domain: ドメイン名（例: "object"）
        operation: 操作名（例: "create"）
        suffix: 型名の接尾辞（例: "Result"）

    Returns:
        パスカルケースの型名（例: "ObjectCreateResult"）
    """
    # ドメインとオペレーションをパスカルケースに変換
    domain_pascal = to_pascal_case(domain)
    operation_pascal = to_pascal_case(operation)
    
    return f"{domain_pascal}{operation_pascal}{suffix}"

def create_input_type_name(domain: str, operation: str) -> str:
    """ドメインと操作から入力型名を生成

    Args:
        domain: ドメイン名（例: "object"）
        operation: 操作名（例: "create"）

    Returns:
        入力型名（例: "ObjectCreateInput"）
    """
    return create_type_name(domain, operation, suffix="Input")

def create_result_type_name(domain: str, operation: str) -> str:
    """ドメインと操作から結果型名を生成

    Args:
        domain: ドメイン名（例: "object"）
        operation: 操作名（例: "create"）

    Returns:
        結果型名（例: "ObjectCreateResult"）
    """
    return create_type_name(domain, operation, suffix="Result")

def standardize_field_name(field_name: str) -> str:
    """フィールド名を標準形式に変換

    既存のフィールド名を解析し、ドメイン.操作形式か、キャメルケース形式かを判断して
    ドメイン.操作形式に標準化します。

    Args:
        field_name: 現在のフィールド名

    Returns:
        標準化されたフィールド名
    """
    # 既にドメイン.操作形式の場合はそのまま返す
    if DOMAIN_DELIMITER in field_name:
        return field_name
    
    # キャメルケースをスネークケースに変換して分析
    snake_case = to_snake_case(field_name)
    
    # 通常、動詞が最初に来るパターン（例: createObject）
    if '_' in snake_case:
        parts = snake_case.split('_', 1)
        if len(parts) == 2:
            operation, domain = parts
            # ドメインが単数形になるように調整（オプション）
            if domain.endswith('s') and not domain.endswith('ss'):
                domain = domain[:-1]
            return create_field_name(domain, operation)
    
    # 解析できない場合は、operation.domainではなくfieldNameとして扱う
    logger.warning(f"フィールド名 '{field_name}' は標準形式に変換できません。そのまま使用します。")
    return field_name

def migrate_field_name(field_name: str, preserve_legacy: bool = True) -> Tuple[str, Optional[str]]:
    """フィールド名を新しい命名規則に移行

    Args:
        field_name: 現在のフィールド名
        preserve_legacy: 古い形式も保持するかどうか

    Returns:
        (新しいフィールド名, 古いフィールド名) のタプル
        preserve_legacy=Falseの場合は古いフィールド名はNone
    """
    # 既にドメイン.操作形式の場合はそのまま返す
    if DOMAIN_DELIMITER in field_name:
        return field_name, None
    
    # 新しい命名規則に変換
    new_name = standardize_field_name(field_name)
    
    # 変更がない場合
    if new_name == field_name:
        return field_name, None
    
    # 古い形式を保持するかどうか
    old_name = field_name if preserve_legacy else None
    
    return new_name, old_name

# リファクタリングに役立つユーティリティ

def find_field_name_inconsistencies(
    field_names: List[str]
) -> Dict[str, List[str]]:
    """フィールド名の一貫性のない部分を検出

    Args:
        field_names: フィールド名のリスト

    Returns:
        {ドメイン: [一貫性のないフィールド名のリスト]} の辞書
    """
    domains: Dict[str, List[str]] = {}
    inconsistencies: Dict[str, List[str]] = {}
    
    # まずドメインごとにフィールドを分類
    for field_name in field_names:
        domain, _ = parse_field_name(field_name)
        
        if domain not in domains:
            domains[domain] = []
            
        domains[domain].append(field_name)
    
    # 各ドメイン内で一貫性を確認
    for domain, fields in domains.items():
        # ドメイン.操作形式とキャメルケース形式が混在しているか確認
        domain_op_format = [f for f in fields if DOMAIN_DELIMITER in f]
        camel_case_format = [f for f in fields if DOMAIN_DELIMITER not in f]
        
        # 両方の形式が存在する場合は不一致として記録
        if domain_op_format and camel_case_format:
            inconsistencies[domain] = camel_case_format
    
    return inconsistencies

def generate_migration_plan(
    field_names: List[str]
) -> Dict[str, str]:
    """フィールド名の移行計画を生成

    Args:
        field_names: 現在のフィールド名のリスト

    Returns:
        {古いフィールド名: 新しいフィールド名} の辞書
    """
    migration_plan = {}
    
    for field_name in field_names:
        new_name, old_name = migrate_field_name(field_name)
        
        # 移行が必要な場合
        if old_name and new_name != old_name:
            migration_plan[old_name] = new_name
    
    return migration_plan

def create_deprecated_field_map(
    migration_plan: Dict[str, str]
) -> Dict[str, Dict[str, Any]]:
    """非推奨フィールドの定義を生成

    Args:
        migration_plan: {古いフィールド名: 新しいフィールド名} の辞書

    Returns:
        {古いフィールド名: フィールド定義} の辞書
    """
    deprecated_fields = {}
    
    for old_name, new_name in migration_plan.items():
        # 非推奨フィールドの定義
        deprecated_fields[old_name] = {
            "deprecated": True,
            "deprecation_reason": f"このフィールドは非推奨です。代わりに `{new_name}` を使用してください。",
            "forwards_to": new_name
        }
    
    return deprecated_fields