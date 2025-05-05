"""
GraphiQL HTML Template Provider
GraphiQLインターフェイスのHTMLテンプレートを提供するモジュール
"""

# GraphiQLインターフェイス用HTMLテンプレート
GRAPHIQL_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Blender GraphQL - GraphiQL</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            height: 100vh;
            width: 100vw;
            overflow: hidden;
            font-family: system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
        }
        #graphiql {
            height: 100vh;
        }
        .graphiql-container {
            background-color: #222;
            color: #eee;
        }
        .topBar {
            background-color: #333;
            border-bottom: 1px solid #555;
        }
        .docExplorerShow {
            color: #ddd;
        }
        .execute-button {
            background-color: #0053FF !important;
        }
        .execute-button:hover {
            background-color: #0040C0 !important;
        }
        .title {
            color: #eee;
        }
    </style>
    <link rel="stylesheet" href="https://unpkg.com/graphiql@2.4.7/graphiql.min.css">
</head>
<body>
    <div id="graphiql"></div>
    <script src="https://unpkg.com/react@17/umd/react.production.min.js"></script>
    <script src="https://unpkg.com/react-dom@17/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/graphiql@2.4.7/graphiql.min.js"></script>
    <script>
        const fetcher = async (graphQLParams) => {
            const response = await fetch('/graphql', {
                method: 'POST',
                headers: {
                    Accept: 'application/json',
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(graphQLParams),
                credentials: 'same-origin',
            });
            return await response.json();
        };

        const defaultQuery = `# Blender GraphQL API Examples

# 基本的な挨拶クエリ
# query {
#   hello
# }

# 現在のシーン情報を取得
query {
  sceneInfo {
    name
    objects {
      name
      type
      location { x y z }
    }
  }
}

# オブジェクトを作成するミューテーション
# mutation {
#   createObject(type: CUBE, name: "NewCube", location: {x: 0, y: 0, z: 0}) {
#     success
#     object {
#       name
#       location { x y z }
#     }
#   }
# }

# オブジェクトの位置を変更するミューテーション
# mutation {
#   transformObject(
#     name: "Cube", 
#     location: {x: 3, y: 0, z: 0},
#     rotation: {x: 45, y: 0, z: 0}
#   ) {
#     success
#     object {
#       name
#       location { x y z }
#       rotation { x y z }
#     }
#   }
# }
`;

        // GraphiQLを初期化
        ReactDOM.render(
            React.createElement(GraphiQL, {
                fetcher,
                defaultQuery,
                headerEditorEnabled: true,
                shouldPersistHeaders: true,
            }),
            document.getElementById('graphiql'),
        );
    </script>
</body>
</html>
"""

def get_graphiql_html():
    """GraphiQL HTMLテンプレートを返す"""
    return GRAPHIQL_HTML