"""
GraphQLスキーマの命名規則を統一
"""

import re
import logging

logger = logging.getLogger("blender_graphql_mcp.tools.naming_convention")

def to_camel_case(snake_str):
    """snake_case文字列をcamelCaseに変換"""
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])

def to_pascal_case(snake_str):
    """snake_case文字列をPascalCaseに変換"""
    components = snake_str.split('_')
    return ''.join(x.title() for x in components)

def to_snake_case(camel_str):
    """camelCaseまたはPascalCase文字列をsnake_caseに変換"""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel_str)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

class NamingConvention:
    """GraphQLスキーマ全体で命名規則を適用するクラス"""
    
    @staticmethod
    def type_name(name):
        """GraphQL型名のフォーマット（PascalCase）"""
        if '_' in name:  # snake_caseからの変換
            return to_pascal_case(name)
        return name
    
    @staticmethod
    def field_name(name):
        """GraphQLフィールド名のフォーマット（camelCase）"""
        if '_' in name:  # snake_caseからの変換
            return to_camel_case(name)
        return name
    
    @staticmethod
    def input_type_name(name):
        """GraphQL入力型名のフォーマット（PascalCase + Input）"""
        base_name = name
        if '_' in name:
            base_name = to_pascal_case(name)
        # 既に"Input"サフィックスがある場合は削除
        if base_name.endswith("Input"):
            base_name = base_name[:-5]
        return f"{base_name}Input"
    
    @staticmethod
    def enum_type_name(name):
        """GraphQL列挙型名のフォーマット（PascalCase）"""
        if '_' in name:
            return to_pascal_case(name)
        return name
    
    @staticmethod
    def enum_value_name(name):
        """GraphQL列挙値のフォーマット（SCREAMING_SNAKE_CASE）"""
        if any(c.islower() for c in name):
            # camelCaseまたはPascalCaseからSCREAMING_SNAKE_CASEへ変換
            return to_snake_case(name).upper()
        return name.upper()

    @staticmethod
    def standardize_all(schema_obj):
        """スキーマ内の全ての名前を標準化"""
        logger.info("スキーマ名の標準化を開始します...")
        # 実装は複雑なため省略。必要に応じて展開する
        return schema_obj