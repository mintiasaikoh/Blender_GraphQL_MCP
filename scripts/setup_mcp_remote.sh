#!/bin/bash
# Blender GraphQL MCP - MCPリモート接続用セットアップスクリプト
# このスクリプトは、mcp-remoteをインストールし、Claude DesktopでBlender GraphQL MCPを使用するための設定をサポートします

# 色を使用して出力を見やすくする
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BOLD='\033[1m'

echo -e "${BOLD}Blender GraphQL MCP - MCPリモート接続セットアップ${NC}"
echo "=========================="
echo ""

# Node.jsがインストールされているか確認
if ! command -v node &> /dev/null; then
    echo -e "${RED}エラー: Node.jsがインストールされていません${NC}"
    echo "NodeJSをインストールする必要があります。以下の方法を試してください:"
    echo ""
    echo "macOSの場合:"
    echo "1. Homebrewを使用: brew install node"
    echo "2. 公式サイトからインストーラーをダウンロード: https://nodejs.org/"
    echo ""
    echo "Windowsの場合:"
    echo "1. 公式サイトからインストーラーをダウンロード: https://nodejs.org/"
    echo ""
    echo "Linuxの場合:"
    echo "1. パッケージマネージャーを使用: apt install nodejs npm または yum install nodejs npm"
    echo "2. nvmを使用: curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash"
    echo ""
    exit 1
fi

# Node.jsとnpmのバージョンを表示
NODE_VERSION=$(node -v)
NPM_VERSION=$(npm -v)
echo -e "${GREEN}✓ Node.js ${NODE_VERSION} が見つかりました${NC}"
echo -e "${GREEN}✓ npm ${NPM_VERSION} が見つかりました${NC}"
echo ""

# mcp-remoteのインストール
echo "mcp-remoteのインストール中..."
npm install -g mcp-remote

# インストール結果を確認
if ! command -v mcp-remote &> /dev/null; then
    echo -e "${YELLOW}注意: mcp-remoteのグローバルインストールに失敗した可能性があります${NC}"
    echo "npxを使って直接実行する方法でも問題ありません"
else
    echo -e "${GREEN}✓ mcp-remoteが正常にインストールされました${NC}"
fi
echo ""

# Claude Desktopの設定ファイルの場所を特定
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    CONFIG_DIR="$HOME/Library/Application Support/Claude"
    CONFIG_FILE="$CONFIG_DIR/claude_desktop_config.json"
elif [[ "$OSTYPE" == "msys"* ]] || [[ "$OSTYPE" == "cygwin"* ]] || [[ "$OSTYPE" == "win32"* ]]; then
    # Windows
    CONFIG_DIR="$APPDATA/Claude"
    CONFIG_FILE="$CONFIG_DIR/claude_desktop_config.json"
else
    # Linux
    CONFIG_DIR="$HOME/.config/Claude"
    CONFIG_FILE="$CONFIG_DIR/claude_desktop_config.json"
fi

# 設定ディレクトリの存在確認と作成
if [ ! -d "$CONFIG_DIR" ]; then
    echo -e "${YELLOW}注意: Claude設定ディレクトリが見つかりません。作成します...${NC}"
    mkdir -p "$CONFIG_DIR"
fi

# 設定例の表示
echo "Claude Desktop設定ファイルの場所:"
echo "$CONFIG_FILE"
echo ""
echo "以下の内容を$CONFIG_FILEに設定してください:"
echo -e "${BOLD}```json"
echo '{
  "mcpServers": {
    "blender": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "http://localhost:8000"
      ]
    }
  }
}'
echo -e "```${NC}"
echo ""

# ユーザーに設定ファイルを作成するか尋ねる
read -p "この設定ファイルを自動的に作成しますか？(y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # 既存の設定ファイルをチェック
    if [ -f "$CONFIG_FILE" ]; then
        echo -e "${YELLOW}警告: 既存の設定ファイルが見つかりました。バックアップを作成します...${NC}"
        cp "$CONFIG_FILE" "${CONFIG_FILE}.bak"
        echo "バックアップを作成しました: ${CONFIG_FILE}.bak"
        
        # 既存のJSONをパースして「mcpServers」キーが存在するか確認
        if grep -q "mcpServers" "$CONFIG_FILE"; then
            echo "既存の設定ファイルにはすでにmcpServersキーが含まれています。"
            echo "手動で編集することをお勧めします。"
            echo "エディタで設定ファイルを開いて編集してください: $CONFIG_FILE"
            exit 0
        fi
    fi
    
    # 新しい設定ファイルを作成
    echo '{
  "mcpServers": {
    "blender": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "http://localhost:8000"
      ]
    }
  }
}' > "$CONFIG_FILE"
    
    echo -e "${GREEN}✓ 設定ファイルを作成しました: $CONFIG_FILE${NC}"
else
    echo "設定ファイルは手動で作成または編集してください。"
fi

echo ""
echo -e "${GREEN}セットアップは完了しました！${NC}"
echo "Blender GraphQL MCPサーバーを起動し、Claude Desktopを再起動してください。"
echo "Blenderサーバーはポート8000で実行する必要があります。"
echo ""
echo -e "${BOLD}問題が発生した場合:${NC}"
echo "1. Blender GraphQL MCPサーバーが起動していることを確認"
echo "2. ポート8000がアクセス可能であることを確認"
echo "3. Claude Desktopを再起動して設定を反映"
echo "4. Claude Desktopのログで詳細な情報を確認"
echo ""