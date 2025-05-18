"""
Unified MCP GraphQL Constants
GraphQLモジュールで使用される定数とエラーメッセージ
"""

# GraphQLのオペレーション名
OPERATION_QUERY = "query"
OPERATION_MUTATION = "mutation"

# リレーションシップの定数
RELATIONSHIP_ABOVE = "above"
RELATIONSHIP_BELOW = "below"
RELATIONSHIP_LEFT = "left"
RELATIONSHIP_RIGHT = "right"
RELATIONSHIP_FRONT = "front"
RELATIONSHIP_BACK = "back"
RELATIONSHIP_INSIDE = "inside"
RELATIONSHIP_AROUND = "around"
RELATIONSHIP_ALIGNED = "aligned"

# スマートオブジェクトの種類
SMART_OBJECT_CUBE = "cube"
SMART_OBJECT_SPHERE = "sphere"
SMART_OBJECT_CYLINDER = "cylinder"
SMART_OBJECT_PLANE = "plane"
SMART_OBJECT_CONE = "cone"
SMART_OBJECT_TORUS = "torus"
SMART_OBJECT_TEXT = "text"
SMART_OBJECT_EMPTY = "empty"
SMART_OBJECT_LIGHT = "light"
SMART_OBJECT_CAMERA = "camera"

# ブーリアン演算の種類
BOOLEAN_OPERATION_UNION = "UNION"
BOOLEAN_OPERATION_DIFFERENCE = "DIFFERENCE"
BOOLEAN_OPERATION_INTERSECT = "INTERSECT"

# ブーリアンソルバー
BOOLEAN_SOLVER_FAST = "FAST"
BOOLEAN_SOLVER_EXACT = "EXACT"

# エラーメッセージ
ERROR_OBJECT_NOT_FOUND = "指定されたオブジェクトが見つかりません: {}"
ERROR_INVALID_RELATIONSHIP = "無効な関係指定です: {}"
ERROR_INVALID_OBJECT_TYPE = "無効なオブジェクト種類です: {}"
ERROR_INVALID_OPERATION = "無効な操作です: {}"
ERROR_GRAPHQL_NOT_AVAILABLE = "GraphQLライブラリがインストールされていません"
ERROR_PROPERTY_PARSE = "プロパティJSONの解析に失敗しました: {}"

# 成功メッセージ
SUCCESS_OBJECT_CREATED = "オブジェクト「{}」を作成しました"
SUCCESS_RELATIONSHIP_SET = "オブジェクト「{}」と「{}」の関係を「{}」に設定しました"
SUCCESS_BOOLEAN_OPERATION = "ブーリアン演算「{}」を実行しました"
