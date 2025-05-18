# Blender GraphQL MCP - Blenderアドオンインストールスクリプト (Windows用)
# このスクリプトは、Blender GraphQL MCPアドオンをBlenderのアドオンディレクトリにインストールします

# 出力を見やすくするための関数
function Write-ColorOutput($ForegroundColor, $Text) {
    $PrevColor = $Host.UI.RawUI.ForegroundColor
    $Host.UI.RawUI.ForegroundColor = $ForegroundColor
    Write-Output $Text
    $Host.UI.RawUI.ForegroundColor = $PrevColor
}

Write-Output "Blender GraphQL MCP - Blenderアドオンインストール"
Write-Output "=========================="
Write-Output ""

# 現在のスクリプトの絶対パスを取得
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
# アドオンのルートディレクトリ（スクリプトの親ディレクトリ）
$ADDON_ROOT = Split-Path -Parent $SCRIPT_DIR

# Blenderのバージョンを確認
$BLENDER_VERSION = Read-Host "インストール先のBlenderのバージョンを入力してください（例: 4.2, 4.3, 4.4）"

# Windowsでは複数の場所にBlenderがインストールされる可能性がある
$POTENTIAL_PATHS = @(
    "C:\Program Files\Blender Foundation\Blender $BLENDER_VERSION\$BLENDER_VERSION\scripts\addons",
    "C:\Program Files\Blender Foundation\Blender\$BLENDER_VERSION\scripts\addons",
    "$env:APPDATA\Blender Foundation\Blender\$BLENDER_VERSION\scripts\addons"
)

# 指定されたパスが存在するか確認
$ADDON_DIR = $null
foreach ($path in $POTENTIAL_PATHS) {
    if (Test-Path $path) {
        $ADDON_DIR = $path
        break
    }
}

# アドオンディレクトリが見つからない場合、ユーザーに選択を促す
if (-not $ADDON_DIR) {
    Write-ColorOutput "Yellow" "警告: Blender ${BLENDER_VERSION}のアドオンディレクトリが自動検出できませんでした"
    $ADDON_DIR = Read-Host "Blenderのアドオンディレクトリを手動で入力してください"
}

# アドオンディレクトリが存在するか確認
if (-not (Test-Path $ADDON_DIR)) {
    Write-ColorOutput "Red" "エラー: 指定されたアドオンディレクトリが存在しません: $ADDON_DIR"
    exit 1
}

# アドオンの宛先ディレクトリ
$TARGET_DIR = Join-Path $ADDON_DIR "blender_graphql_mcp"

# 既存のインストールをチェック
if (Test-Path $TARGET_DIR) {
    Write-ColorOutput "Yellow" "注意: Blender GraphQL MCPアドオンがすでにインストールされています"
    $reply = Read-Host "上書きしますか？(y/n)"
    if ($reply -ne "y" -and $reply -ne "Y") {
        Write-Output "インストールを中止しました"
        exit 0
    }
    
    # 既存のインストールをバックアップ
    $BACKUP_DIR = "${TARGET_DIR}_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Write-Output "既存のインストールをバックアップします: $BACKUP_DIR"
    Move-Item -Path $TARGET_DIR -Destination $BACKUP_DIR -Force
}

# ディレクトリを作成
New-Item -Path $TARGET_DIR -ItemType Directory -Force | Out-Null

# アドオンファイルをコピー
Write-Output "アドオンファイルをコピーしています..."
Copy-Item -Path "$ADDON_ROOT\*" -Destination $TARGET_DIR -Recurse -Force

# インストール結果の確認
if (Test-Path "$TARGET_DIR\__init__.py") {
    Write-ColorOutput "Green" "✓ アドオンのインストールが完了しました"
    Write-Output "インストール先: $TARGET_DIR"
    Write-Output ""
    Write-Output "次のステップ:"
    Write-Output "1. Blenderを起動します"
    Write-Output "2. [編集] > [プリファレンス] > [アドオン]を開きます"
    Write-Output "3. 「Blender GraphQL MCP」を検索して有効化します"
    Write-Output ""
    Write-Output "アドオンが有効化されたら、サイドバーの「MCP」タブからサーバーを起動できます"
    Write-Output ""
    Write-Output "Claude Desktopとの接続を設定するには、以下のスクリプトを実行してください："
    Write-Output "  .\scripts\setup_mcp_remote.ps1"
}
else {
    Write-ColorOutput "Red" "エラー: アドオンのインストールに失敗しました"
    Write-Output "手動でインストールを試みてください："
    Write-Output "1. $ADDON_ROOTの内容を$TARGET_DIRにコピーしてください"
    Write-Output "2. Blenderを起動し、アドオンを有効化してください"
}