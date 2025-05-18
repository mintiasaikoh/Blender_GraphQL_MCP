#!/bin/bash

echo "=== Blender GraphQL MCP 超簡単インストーラー ==="
echo ""

# Pythonが利用可能かチェック
if ! command -v python3 &> /dev/null; then
    echo "Python3が見つかりませんでした。Python3をインストールしてから再実行してください。"
    echo "macOSの場合: brew install python3"
    echo "Ubuntuの場合: sudo apt install python3"
    exit 1
fi

# 実行権限を付与
chmod +x easy_install.py

# インストールスクリプトを実行
python3 ./easy_install.py

echo ""
echo "何かキーを押して終了..."
read -n 1