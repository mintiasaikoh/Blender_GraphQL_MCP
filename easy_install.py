#!/usr/bin/env python3
"""
超簡単Blender GraphQL MCPインストーラー
一つのコマンドでBlenderにアドオンをインストールします
"""

import os
import sys
import shutil
import zipfile
import tempfile
import subprocess
from pathlib import Path

def get_blender_addons_path():
    """Blenderのアドオンディレクトリを自動検出"""
    # OSによる標準パスの候補
    if sys.platform == 'win32':
        # Windows
        paths = [
            os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'Blender Foundation', 'Blender'),
            'C:\\Program Files\\Blender Foundation\\Blender'
        ]
    elif sys.platform == 'darwin':
        # macOS
        paths = [
            os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'Blender'),
            '/Applications/Blender.app/Contents/Resources'
        ]
    else:
        # Linux
        paths = [
            os.path.join(os.path.expanduser('~'), '.config', 'blender'),
            '/usr/share/blender'
        ]
    
    # 各バージョンのBlenderを検索
    for base_path in paths:
        if os.path.exists(base_path):
            # ディレクトリ内のサブディレクトリを確認
            try:
                dirs = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
                # バージョン番号でソート（最新を最初に）
                dirs.sort(reverse=True)
                
                for version_dir in dirs:
                    # 数字で始まるディレクトリのみ処理（バージョン番号）
                    if version_dir[0].isdigit():
                        addon_path = os.path.join(base_path, version_dir, 'scripts', 'addons')
                        if os.path.exists(addon_path):
                            return addon_path
            except:
                continue
    
    # 見つからない場合はユーザー入力を求める
    print("Blenderのアドオンディレクトリを自動検出できませんでした。")
    path = input("Blenderのアドオンディレクトリのパスを入力してください: ")
    return path

def create_zip(source_dir, output_file):
    """ソースディレクトリからzipファイルを作成"""
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # 新しい構造のみを含める
        main_dirs = ['blender_mcp', 'docs']
        main_files = ['__init__.py', 'extension.toml', 'blender_manifest.toml', 'LICENSE', 'README.md']
        
        # メインファイルを追加
        for file in main_files:
            file_path = os.path.join(source_dir, file)
            if os.path.exists(file_path):
                zipf.write(file_path, os.path.basename(file_path))
        
        # メインディレクトリを追加
        for dir_name in main_dirs:
            dir_path = os.path.join(source_dir, dir_name)
            if os.path.exists(dir_path):
                for root, _, files in os.walk(dir_path):
                    for file in files:
                        # .gitや一時ファイルは除外
                        if file.startswith('.git') or file.endswith('.pyc') or file == '__pycache__':
                            continue
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, source_dir)
                        zipf.write(file_path, arcname)

def main():
    """メイン処理"""
    print("=== Blender GraphQL MCP 超簡単インストーラー ===")
    
    # ドライランモードのチェック
    import sys
    dry_run = "--dry-run" in sys.argv
    
    # 現在のディレクトリを取得
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 一時ディレクトリを作成
    with tempfile.TemporaryDirectory() as temp_dir:
        # zipファイルの作成先
        zip_path = os.path.join(temp_dir, "blender_graphql_mcp.zip")
        
        print(f"アドオンのzipファイルを作成中...")
        create_zip(current_dir, zip_path)
        
        # ドライランモードでない場合のみアドオンをインストール
        if not dry_run:
            # Blenderのアドオンディレクトリを検出
            addons_path = get_blender_addons_path()
            
            if not os.path.exists(addons_path):
                os.makedirs(addons_path, exist_ok=True)
                
            # アドオンディレクトリの作成
            addon_dir = os.path.join(addons_path, "blender_graphql_mcp")
            
            # 既存のアドオンを削除（あれば）
            if os.path.exists(addon_dir):
                print(f"既存のアドオンを削除中: {addon_dir}")
                shutil.rmtree(addon_dir)
            
            # zipファイルを展開
            print(f"アドオンをインストール中: {addons_path}")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(addon_dir)
        else:
            # ドライランの場合は内容の確認のみ
            print("ドライランモード: 実際のインストールはスキップします")
            print("\nzipファイルの内容:")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for file in zip_ref.namelist():
                    print(f"  - {file}")
        
        if not dry_run:
            print(f"アドオンが正常にインストールされました！")
            print(f"インストール先: {addon_dir}")
        else:
            print("\nドライラン完了: パッケージの内容確認が完了しました")
        
        # ドライランでない場合のみBlender起動の確認
        launch_blender = False
        if not dry_run:
            launch_blender = input("今すぐBlenderを起動しますか？ (y/n): ").lower().strip() == 'y'
        
        if launch_blender:
            # OSに応じたBlenderの検索と起動
            blender_path = None
            
            if sys.platform == 'win32':
                # Windows
                paths = [
                    "C:\\Program Files\\Blender Foundation\\Blender\\blender.exe",
                    "C:\\Program Files (x86)\\Blender Foundation\\Blender\\blender.exe"
                ]
            elif sys.platform == 'darwin':
                # macOS
                paths = [
                    "/Applications/Blender.app/Contents/MacOS/Blender",
                    os.path.expanduser("~/Applications/Blender.app/Contents/MacOS/Blender")
                ]
            else:
                # Linux
                paths = [
                    "/usr/bin/blender",
                    "/usr/local/bin/blender",
                    "/snap/bin/blender"
                ]
            
            # パスの存在チェック
            for path in paths:
                if os.path.exists(path):
                    blender_path = path
                    break
            
            if not blender_path:
                # ユーザーに直接パスを尋ねる
                blender_path = input("Blender実行ファイルのパスを入力してください: ")
            
            if blender_path and os.path.exists(blender_path):
                print(f"Blenderを起動中: {blender_path}")
                subprocess.Popen([blender_path])
            else:
                print("Blender実行ファイルが見つかりませんでした。手動で起動してください。")
        
        print("\n=== インストール完了 ===")
        print("Blenderでアドオンを有効にする方法:")
        print("1. Blenderを起動")
        print("2. 編集 > 設定 > アドオン")
        print("3. 'MCP'で検索")
        print("4. 'Blender MCP Tools'のチェックボックスをオン")
        print("\nお楽しみください！")

if __name__ == "__main__":
    main()