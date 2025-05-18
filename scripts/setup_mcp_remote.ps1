# Blender GraphQL MCP - MCPリモート接続用セットアップスクリプト (Windows PowerShell用)
# このスクリプトは、mcp-remoteをインストールし、Claude DesktopでBlender GraphQL MCPを使用するための設定をサポートします

# 出力を見やすくするための関数
function Write-ColorOutput($ForegroundColor, $Text) {
    $PrevColor = $Host.UI.RawUI.ForegroundColor
    $Host.UI.RawUI.ForegroundColor = $ForegroundColor
    Write-Output $Text
    $Host.UI.RawUI.ForegroundColor = $PrevColor
}

Write-Output "Blender GraphQL MCP - MCPリモート接続セットアップ"
Write-Output "=========================="
Write-Output ""

# Node.jsがインストールされているか確認
try {
    $nodeVersion = node -v
    $npmVersion = npm -v
    Write-ColorOutput "Green" "✓ Node.js $nodeVersion が見つかりました"
    Write-ColorOutput "Green" "✓ npm $npmVersion が見つかりました"
} catch {
    Write-ColorOutput "Red" "エラー: Node.jsがインストールされていません"
    Write-Output "NodeJSをインストールする必要があります。以下の方法を試してください:"
    Write-Output ""
    Write-Output "1. 公式サイトからインストーラーをダウンロード: https://nodejs.org/"
    Write-Output "2. chocolateyを使用: choco install nodejs"
    Write-Output ""
    exit 1
}

Write-Output ""

# mcp-remoteのインストール
Write-Output "mcp-remoteのインストール中..."
npm install -g mcp-remote

# インストール結果を確認
try {
    Get-Command mcp-remote -ErrorAction Stop | Out-Null
    Write-ColorOutput "Green" "✓ mcp-remoteが正常にインストールされました"
} catch {
    Write-ColorOutput "Yellow" "注意: mcp-remoteのグローバルインストールに失敗した可能性があります"
    Write-Output "npxを使って直接実行する方法でも問題ありません"
}

Write-Output ""

# Claude Desktopの設定ファイルの場所を特定
$configDir = Join-Path $env:APPDATA "Claude"
$configFile = Join-Path $configDir "claude_desktop_config.json"

# 設定ディレクトリの存在確認と作成
if (-not (Test-Path $configDir)) {
    Write-ColorOutput "Yellow" "注意: Claude設定ディレクトリが見つかりません。作成します..."
    New-Item -Path $configDir -ItemType Directory | Out-Null
}

# 設定例の表示
Write-Output "Claude Desktop設定ファイルの場所:"
Write-Output $configFile
Write-Output ""
Write-Output "以下の内容を設定ファイルに設定してください:"
Write-Output "```json"
Write-Output '{
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
Write-Output "```"
Write-Output ""

# ユーザーに設定ファイルを作成するか尋ねる
$userInput = Read-Host "この設定ファイルを自動的に作成しますか？(y/n)"
if ($userInput -eq "y" -or $userInput -eq "Y") {
    # 既存の設定ファイルをチェック
    if (Test-Path $configFile) {
        Write-ColorOutput "Yellow" "警告: 既存の設定ファイルが見つかりました。バックアップを作成します..."
        Copy-Item -Path $configFile -Destination "$configFile.bak" -Force
        Write-Output "バックアップを作成しました: $configFile.bak"
        
        # 既存のJSONをパースして「mcpServers」キーが存在するか確認
        $existingConfig = Get-Content -Path $configFile -Raw | ConvertFrom-Json -ErrorAction SilentlyContinue
        if ($existingConfig -and (Get-Member -InputObject $existingConfig -Name "mcpServers" -MemberType Properties)) {
            Write-Output "既存の設定ファイルにはすでにmcpServersキーが含まれています。"
            Write-Output "手動で編集することをお勧めします。"
            Write-Output "エディタで設定ファイルを開いて編集してください: $configFile"
            exit 0
        }
    }
    
    # 新しい設定ファイルを作成
    @'
{
  "mcpServers": {
    "blender": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "http://localhost:8000"
      ]
    }
  }
}
'@ | Out-File -FilePath $configFile -Encoding utf8
    
    Write-ColorOutput "Green" "✓ 設定ファイルを作成しました: $configFile"
} else {
    Write-Output "設定ファイルは手動で作成または編集してください。"
}

Write-Output ""
Write-ColorOutput "Green" "セットアップは完了しました！"
Write-Output "Blender GraphQL MCPサーバーを起動し、Claude Desktopを再起動してください。"
Write-Output "Blenderサーバーはポート8000で実行する必要があります。"
Write-Output ""
Write-Output "問題が発生した場合:"
Write-Output "1. Blender GraphQL MCPサーバーが起動していることを確認"
Write-Output "2. ポート8000がアクセス可能であることを確認"
Write-Output "3. Claude Desktopを再起動して設定を反映"
Write-Output "4. Claude Desktopのログで詳細な情報を確認"
Write-Output ""