@echo off
echo === Blender GraphQL MCP 超簡単インストーラー ===
echo.

:: Pythonが利用可能かチェック
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Pythonが見つかりませんでした。Pythonをインストールしてから再実行してください。
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)

:: インストールスクリプトを実行
python easy_install.py

pause