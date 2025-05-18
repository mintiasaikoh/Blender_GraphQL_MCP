#!/bin/bash
# Blender GraphQL MCP - Blenderアドオンインストールスクリプト (macOS/Linux用)
# このスクリプトは、Blender GraphQL MCPアドオンをBlenderのアドオンディレクトリにインストールします

# 色を使用して出力を見やすくする
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BOLD='\033[1m'

echo -e "${BOLD}Blender GraphQL MCP - Blenderアドオンインストール${NC}"
echo "=========================="
echo ""

# 現在のスクリプトの絶対パスを取得
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# アドオンのルートディレクトリ（スクリプトの親ディレクトリ）
ADDON_ROOT="$( dirname "$SCRIPT_DIR" )"

# Blenderのバージョンを確認
read -p "インストール先のBlenderのバージョンを入力してください（例: 4.2, 4.3, 4.4）: " BLENDER_VERSION

# OSを確認
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    echo "macOSが検出されました"
    
    # macOSではアプリケーションフォルダやユーザーフォルダにBlenderがインストールされる可能性がある
    POTENTIAL_PATHS=(
        "/Applications/Blender.app/Contents/Resources/${BLENDER_VERSION}/scripts/addons"
        "$HOME/Applications/Blender.app/Contents/Resources/${BLENDER_VERSION}/scripts/addons"
        "$HOME/Library/Application Support/Blender/${BLENDER_VERSION}/scripts/addons"
    )
    
    # 指定されたパスが存在するか確認
    ADDON_DIR=""
    for path in "${POTENTIAL_PATHS[@]}"; do
        if [ -d "$path" ]; then
            ADDON_DIR="$path"
            break
        fi
    done
    
    # アドオンディレクトリが見つからない場合、ユーザーに選択を促す
    if [ -z "$ADDON_DIR" ]; then
        echo -e "${YELLOW}警告: Blender ${BLENDER_VERSION}のアドオンディレクトリが自動検出できませんでした${NC}"
        read -p "Blenderのアドオンディレクトリを手動で入力してください: " ADDON_DIR
    fi
    
else
    # Linux
    echo "Linuxが検出されました"
    
    # Linuxではいくつかの場所にBlenderがインストールされる可能性がある
    POTENTIAL_PATHS=(
        "/usr/share/blender/${BLENDER_VERSION}/scripts/addons"
        "/opt/blender/blender-${BLENDER_VERSION}-linux-x64/scripts/addons"
        "$HOME/.config/blender/${BLENDER_VERSION}/scripts/addons"
    )
    
    # 指定されたパスが存在するか確認
    ADDON_DIR=""
    for path in "${POTENTIAL_PATHS[@]}"; do
        if [ -d "$path" ]; then
            ADDON_DIR="$path"
            break
        fi
    done
    
    # アドオンディレクトリが見つからない場合、ユーザーに選択を促す
    if [ -z "$ADDON_DIR" ]; then
        echo -e "${YELLOW}警告: Blender ${BLENDER_VERSION}のアドオンディレクトリが自動検出できませんでした${NC}"
        read -p "Blenderのアドオンディレクトリを手動で入力してください: " ADDON_DIR
    fi
fi

# アドオンディレクトリが存在するか確認
if [ ! -d "$ADDON_DIR" ]; then
    echo -e "${RED}エラー: 指定されたアドオンディレクトリが存在しません: $ADDON_DIR${NC}"
    exit 1
fi

# アドオンの宛先ディレクトリ
TARGET_DIR="$ADDON_DIR/blender_graphql_mcp"

# 既存のインストールをチェック
if [ -d "$TARGET_DIR" ]; then
    echo -e "${YELLOW}注意: Blender GraphQL MCPアドオンがすでにインストールされています${NC}"
    read -p "上書きしますか？(y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "インストールを中止しました"
        exit 0
    fi
    
    # 既存のインストールをバックアップ
    BACKUP_DIR="${TARGET_DIR}_backup_$(date +%Y%m%d_%H%M%S)"
    echo "既存のインストールをバックアップします: $BACKUP_DIR"
    mv "$TARGET_DIR" "$BACKUP_DIR"
fi

# ディレクトリを作成
mkdir -p "$TARGET_DIR"

# アドオンファイルをコピー
echo "アドオンファイルをコピーしています..."
cp -r "$ADDON_ROOT"/* "$TARGET_DIR"
cp -r "$ADDON_ROOT"/.* "$TARGET_DIR" 2>/dev/null || true

# インストール結果の確認
if [ -f "$TARGET_DIR/__init__.py" ]; then
    echo -e "${GREEN}✓ アドオンのインストールが完了しました${NC}"
    echo "インストール先: $TARGET_DIR"
    echo ""
    echo -e "${BOLD}次のステップ:${NC}"
    echo "1. Blenderを起動します"
    echo "2. [編集] > [プリファレンス] > [アドオン]を開きます"
    echo "3. 「Blender GraphQL MCP」を検索して有効化します"
    echo ""
    echo "アドオンが有効化されたら、サイドバーの「MCP」タブからサーバーを起動できます"
    echo ""
    echo "Claude Desktopとの接続を設定するには、以下のスクリプトを実行してください："
    echo "  ./scripts/setup_mcp_remote.sh"
else
    echo -e "${RED}エラー: アドオンのインストールに失敗しました${NC}"
    echo "手動でインストールを試みてください："
    echo "1. $ADDON_ROOTの内容を$TARGET_DIRにコピーしてください"
    echo "2. Blenderを起動し、アドオンを有効化してください"
fi