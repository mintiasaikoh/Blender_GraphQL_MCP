"""
Blender GraphQL MCP - スキーマレジストリ
GraphQLスキーマコンポーネントの登録と管理を一元化
"""

import logging
from typing import Dict, Any, Optional, List, Set
from tools import (
    GraphQLSchema,
    GraphQLObjectType,
    GraphQLType,
    GraphQLField
)

logger = logging.getLogger("blender_graphql_mcp.tools.definitions_registry")

class SchemaRegistry:
    """GraphQLスキーマコンポーネントを管理するレジストリ"""
    
    def __init__(self):
        """初期化"""
        self.types: Dict[str, GraphQLType] = {}
        self.query_fields: Dict[str, GraphQLField] = {}
        self.mutation_fields: Dict[str, GraphQLField] = {}
        self.registered_components: Set[str] = set()
        
    def register_type(self, name: str, type_def: GraphQLType) -> None:
        """型を登録
        
        Args:
            name: 型名
            type_def: GraphQL型定義
        """
        if name in self.types:
            logger.warning(f"型 '{name}' は既に登録されています。上書きします。")
            
        self.types[name] = type_def
        
    def register_query(self, name: str, field_def: GraphQLField) -> None:
        """クエリフィールドを登録
        
        Args:
            name: フィールド名
            field_def: GraphQLフィールド定義
        """
        if name in self.query_fields:
            logger.warning(f"クエリフィールド '{name}' は既に登録されています。上書きします。")
            
        self.query_fields[name] = field_def
        
    def register_mutation(self, name: str, field_def: GraphQLField) -> None:
        """ミューテーションフィールドを登録
        
        Args:
            name: フィールド名
            field_def: GraphQLフィールド定義
        """
        if name in self.mutation_fields:
            logger.warning(f"ミューテーションフィールド '{name}' は既に登録されています。上書きします。")
            
        self.mutation_fields[name] = field_def
        
    def get_type(self, name: str) -> Optional[GraphQLType]:
        """名前から型を取得
        
        Args:
            name: 型名
            
        Returns:
            GraphQL型定義（存在しない場合はNone）
        """
        return self.types.get(name)
        
    def register_component(self, component_name: str) -> bool:
        """コンポーネントの登録状態を記録
        
        Args:
            component_name: コンポーネント名
            
        Returns:
            初めての登録の場合はTrue、既に登録済みの場合はFalse
        """
        if component_name in self.registered_components:
            return False
            
        self.registered_components.add(component_name)
        return True
        
    def is_component_registered(self, component_name: str) -> bool:
        """コンポーネントが登録済みかどうかを確認
        
        Args:
            component_name: コンポーネント名
            
        Returns:
            登録済みの場合はTrue
        """
        return component_name in self.registered_components
        
    def build_schema(self) -> GraphQLSchema:
        """登録されたコンポーネントからスキーマを構築
        
        Returns:
            構築されたGraphQLスキーマ
        """
        # クエリタイプの構築
        query_type = GraphQLObjectType(
            name='Query',
            fields=self.query_fields
        )
        
        # ミューテーションタイプの構築
        mutation_type = GraphQLObjectType(
            name='Mutation',
            fields=self.mutation_fields
        )
        
        # スキーマの構築と返却
        logger.info(f"スキーマを構築しました: {len(self.types)}型, "
                   f"{len(self.query_fields)}クエリ, "
                   f"{len(self.mutation_fields)}ミューテーション")
        
        return GraphQLSchema(
            query=query_type,
            mutation=mutation_type,
            types=list(self.types.values())
        )

# グローバルインスタンス
schema_registry = SchemaRegistry()
