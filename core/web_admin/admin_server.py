"""
ウェブ管理インターフェースサーバー
ローカルホストで動作する管理用Webインターフェース
"""

import os
import json
import threading
import time
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

# FastAPIをインポート
try:
    from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    from pydantic import BaseModel
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

# タスクキューをインポート
from ..task_queue import get_task_queue, TaskStatus, Task, initialize_task_queue

# ロギング設定
logger = logging.getLogger('unified_mcp.web_admin')

class AdminServer:
    """
    管理用WebサーバークラスA
    ローカルホストでのみアクセス可能な管理インターフェースを提供
    """
    
    def __init__(self, host: str = "localhost", port: int = 8766):
        """
        管理サーバーを初期化
        
        Args:
            host: サーバーホスト（デフォルトはlocalhost）
            port: サーバーポート
        """
        self.host = host
        self.port = port
        self.app = None
        self.server_thread = None
        self.running = False
        self.connected_websockets = []  # WebSocket接続を管理
        
        # 現在のディレクトリからテンプレートパスを取得
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.templates_dir = os.path.join(current_dir, 'templates')
        self.static_dir = os.path.join(current_dir, 'static')
        
        # ディレクトリが存在しない場合は作成
        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(self.static_dir, exist_ok=True)
        
        logger.info(f"管理サーバーを初期化しました (host: {host}, port: {port})")
        
        # 必要なファイルが存在しない場合は作成
        self._ensure_template_files()
    
    def _ensure_template_files(self):
        """必要なテンプレートファイルを作成"""
        # インデックスHTMLテンプレート
        index_html = os.path.join(self.templates_dir, 'index.html')
        if not os.path.exists(index_html):
            with open(index_html, 'w', encoding='utf-8') as f:
                f.write("""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Blender GraphQL MCP 管理パネル</title>
    <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>Blender GraphQL MCP 管理パネル</h1>
        </header>
        
        <div class="tabs">
            <button class="tab-btn active" data-tab="dashboard">ダッシュボード</button>
            <button class="tab-btn" data-tab="tasks">タスク管理</button>
            <button class="tab-btn" data-tab="graphql">GraphQL</button>
            <button class="tab-btn" data-tab="logs">ログ</button>
            <button class="tab-btn" data-tab="settings">設定</button>
        </div>
        
        <div class="tab-content">
            <!-- ダッシュボードタブ -->
            <div id="dashboard" class="tab-pane active">
                <h2>システム状態</h2>
                <div class="status-cards">
                    <div class="card">
                        <h3>サーバー状態</h3>
                        <div class="status-indicator running" id="server-status">実行中</div>
                        <div class="details">
                            <p>ポート: <span id="server-port">8765</span></p>
                            <p>起動時間: <span id="server-uptime">0分</span></p>
                        </div>
                    </div>
                    <div class="card">
                        <h3>タスクキュー</h3>
                        <div class="status-indicator running" id="queue-status">実行中</div>
                        <div class="details">
                            <p>処理済み: <span id="completed-tasks">0</span></p>
                            <p>待機中: <span id="pending-tasks">0</span></p>
                            <p>実行中: <span id="running-tasks">0</span></p>
                        </div>
                    </div>
                    <div class="card">
                        <h3>メモリ使用量</h3>
                        <div class="progress-bar">
                            <div class="progress" id="memory-usage" style="width: 10%;">10%</div>
                        </div>
                        <div class="details">
                            <p>使用中: <span id="memory-used">0 MB</span></p>
                            <p>合計: <span id="memory-total">0 MB</span></p>
                        </div>
                    </div>
                </div>
                
                <h2>最近のアクティビティ</h2>
                <div class="activity-log" id="activity-log">
                    <div class="log-entry">
                        <span class="timestamp">00:00:00</span>
                        <span class="message">システム起動</span>
                    </div>
                </div>
            </div>
            
            <!-- タスク管理タブ -->
            <div id="tasks" class="tab-pane">
                <h2>タスク管理</h2>
                
                <div class="task-controls">
                    <button id="refresh-tasks">更新</button>
                    <button id="clear-completed">完了タスクをクリア</button>
                    <button id="create-test-task">テストタスク作成</button>
                </div>
                
                <div class="task-filters">
                    <label><input type="checkbox" class="task-filter" data-status="pending" checked> 待機中</label>
                    <label><input type="checkbox" class="task-filter" data-status="running" checked> 実行中</label>
                    <label><input type="checkbox" class="task-filter" data-status="completed" checked> 完了</label>
                    <label><input type="checkbox" class="task-filter" data-status="failed" checked> 失敗</label>
                    <label><input type="checkbox" class="task-filter" data-status="cancelled" checked> キャンセル済み</label>
                </div>
                
                <div class="tasks-container">
                    <table class="tasks-table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>名前</th>
                                <th>タイプ</th>
                                <th>状態</th>
                                <th>進捗</th>
                                <th>作成時間</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody id="tasks-list">
                            <!-- タスクリストはJavaScriptで動的に生成 -->
                        </tbody>
                    </table>
                </div>
                
                <div id="task-details" class="task-details">
                    <h3>タスク詳細</h3>
                    <div id="task-detail-content"></div>
                </div>
            </div>
            
            <!-- GraphQLタブ -->
            <div id="graphql" class="tab-pane">
                <h2>GraphQL 実行</h2>
                
                <div class="graphql-container">
                    <div class="graphql-editor">
                        <h3>クエリ</h3>
                        <textarea id="graphql-query" placeholder="GraphQLクエリを入力してください..."></textarea>
                        <div class="editor-controls">
                            <button id="run-query">実行</button>
                            <select id="sample-queries">
                                <option value="">サンプルクエリ...</option>
                                <option value="scene">シーン情報取得</option>
                                <option value="objects">オブジェクト一覧</option>
                                <option value="create-cube">立方体を作成</option>
                                <option value="transform">オブジェクト変換</option>
                                <option value="transaction">トランザクション実行</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="graphql-result">
                        <h3>結果</h3>
                        <pre id="graphql-result">// 結果がここに表示されます</pre>
                    </div>
                </div>
            </div>
            
            <!-- ログタブ -->
            <div id="logs" class="tab-pane">
                <h2>ログ表示</h2>
                
                <div class="log-controls">
                    <button id="refresh-logs">更新</button>
                    <button id="clear-logs">クリア</button>
                    <select id="log-level">
                        <option value="all">すべて</option>
                        <option value="info">情報以上</option>
                        <option value="warning">警告以上</option>
                        <option value="error">エラーのみ</option>
                    </select>
                </div>
                
                <div class="log-viewer">
                    <pre id="log-content"></pre>
                </div>
            </div>
            
            <!-- 設定タブ -->
            <div id="settings" class="tab-pane">
                <h2>システム設定</h2>
                
                <div class="settings-form">
                    <div class="form-group">
                        <label for="server-host">サーバーホスト:</label>
                        <input type="text" id="server-host" value="localhost">
                    </div>
                    
                    <div class="form-group">
                        <label for="server-port">サーバーポート:</label>
                        <input type="number" id="server-port-input" value="8765">
                    </div>
                    
                    <div class="form-group">
                        <label for="worker-threads">ワーカースレッド数:</label>
                        <input type="number" id="worker-threads" value="2" min="1" max="8">
                    </div>
                    
                    <div class="form-group">
                        <label>サーバー制御:</label>
                        <div class="button-group">
                            <button id="restart-server">サーバー再起動</button>
                            <button id="stop-server">サーバー停止</button>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label>タスクキュー設定:</label>
                        <div class="button-group">
                            <button id="restart-queue">キュー再起動</button>
                            <button id="clear-all-tasks">全タスククリア</button>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <button id="save-settings">設定を保存</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script src="/static/scripts.js"></script>
</body>
</html>
""")
        
        # CSSファイル
        css_file = os.path.join(self.static_dir, 'styles.css')
        if not os.path.exists(css_file):
            with open(css_file, 'w', encoding='utf-8') as f:
                f.write("""/* ベース設定 */
:root {
    --primary-color: #3498db;
    --secondary-color: #2ecc71;
    --accent-color: #e74c3c;
    --bg-color: #f5f5f5;
    --card-bg: #ffffff;
    --text-color: #333333;
    --border-color: #dddddd;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    line-height: 1.6;
    color: var(--text-color);
    background-color: var(--bg-color);
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

header {
    background-color: var(--primary-color);
    color: white;
    padding: 15px 20px;
    border-radius: 5px 5px 0 0;
    margin-bottom: 20px;
}

h1, h2, h3 {
    margin-bottom: 15px;
}

/* タブ関連 */
.tabs {
    display: flex;
    border-bottom: 1px solid var(--border-color);
    margin-bottom: 20px;
}

.tab-btn {
    padding: 10px 20px;
    background: none;
    border: none;
    cursor: pointer;
    font-size: 16px;
    opacity: 0.7;
    transition: all 0.3s;
}

.tab-btn:hover {
    opacity: 1;
    background-color: rgba(0, 0, 0, 0.05);
}

.tab-btn.active {
    opacity: 1;
    border-bottom: 3px solid var(--primary-color);
    font-weight: 600;
}

.tab-pane {
    display: none;
    padding: 15px 0;
}

.tab-pane.active {
    display: block;
}

/* カード関連 */
.status-cards {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.card {
    background-color: var(--card-bg);
    border-radius: 5px;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
    padding: 20px;
}

.status-indicator {
    display: inline-block;
    padding: 5px 10px;
    border-radius: 15px;
    color: white;
    font-size: 14px;
    margin-bottom: 10px;
}

.running {
    background-color: var(--secondary-color);
}

.stopped {
    background-color: var(--accent-color);
}

.warning {
    background-color: #f39c12;
}

.details p {
    margin-bottom: 5px;
    font-size: 14px;
}

/* プログレスバー */
.progress-bar {
    width: 100%;
    height: 20px;
    background-color: #e6e6e6;
    border-radius: 10px;
    margin-bottom: 10px;
    overflow: hidden;
}

.progress {
    height: 100%;
    background-color: var(--primary-color);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 12px;
    transition: width 0.5s;
}

/* アクティビティログ */
.activity-log {
    background-color: var(--card-bg);
    border-radius: 5px;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
    padding: 15px;
    height: 200px;
    overflow-y: auto;
}

.log-entry {
    padding: 5px 0;
    border-bottom: 1px solid var(--border-color);
    font-size: 14px;
}

.timestamp {
    color: #777;
    margin-right: 10px;
}

/* タスク管理 */
.task-controls, .task-filters {
    margin-bottom: 15px;
}

button {
    padding: 8px 15px;
    background-color: var(--primary-color);
    color: white;
    border: none;
    border-radius: 5px;
    cursor: pointer;
    margin-right: 10px;
    transition: background-color 0.3s;
}

button:hover {
    background-color: #2980b9;
}

.task-filters label {
    margin-right: 15px;
    font-size: 14px;
}

.tasks-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 20px;
}

.tasks-table th, .tasks-table td {
    padding: 10px;
    text-align: left;
    border-bottom: 1px solid var(--border-color);
}

.tasks-table th {
    background-color: #f2f2f2;
}

.task-details {
    background-color: var(--card-bg);
    border-radius: 5px;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
    padding: 20px;
    margin-top: 20px;
}

/* GraphQL */
.graphql-container {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
}

.graphql-editor, .graphql-result {
    background-color: var(--card-bg);
    border-radius: 5px;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
    padding: 20px;
}

textarea {
    width: 100%;
    height: 300px;
    font-family: 'Consolas', monospace;
    padding: 10px;
    border: 1px solid var(--border-color);
    border-radius: 5px;
    resize: vertical;
    margin-bottom: 10px;
}

.editor-controls {
    display: flex;
    justify-content: space-between;
}

select {
    padding: 8px;
    border-radius: 5px;
    border: 1px solid var(--border-color);
}

pre {
    background-color: #f9f9f9;
    padding: 15px;
    border-radius: 5px;
    overflow: auto;
    height: 300px;
    font-family: 'Consolas', monospace;
    white-space: pre-wrap;
}

/* ログ表示 */
.log-controls {
    margin-bottom: 15px;
    display: flex;
    align-items: center;
}

.log-viewer {
    background-color: #1e1e1e;
    color: #f0f0f0;
    border-radius: 5px;
    height: 400px;
    overflow: auto;
}

.log-viewer pre {
    background: none;
    color: inherit;
    height: 100%;
    padding: 15px;
}

/* 設定 */
.settings-form {
    background-color: var(--card-bg);
    border-radius: 5px;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
    padding: 20px;
}

.form-group {
    margin-bottom: 20px;
}

.form-group label {
    display: block;
    margin-bottom: 5px;
    font-weight: 600;
}

.form-group input[type="text"],
.form-group input[type="number"] {
    width: 100%;
    padding: 8px;
    border: 1px solid var(--border-color);
    border-radius: 5px;
}

.button-group {
    display: flex;
    gap: 10px;
}

#save-settings {
    background-color: var(--secondary-color);
}

#stop-server, #clear-all-tasks {
    background-color: var(--accent-color);
}

/* レスポンシブデザイン */
@media (max-width: 768px) {
    .status-cards {
        grid-template-columns: 1fr;
    }
    
    .graphql-container {
        grid-template-columns: 1fr;
    }
    
    .tabs {
        flex-wrap: wrap;
    }
    
    .tab-btn {
        flex: 1 0 auto;
        text-align: center;
    }
}
""")
        
        # JavaScriptファイル
        js_file = os.path.join(self.static_dir, 'scripts.js')
        if not os.path.exists(js_file):
            with open(js_file, 'w', encoding='utf-8') as f:
                f.write("""// 管理パネルメインJS

// WebSocket接続
let socket;
let reconnectInterval = 1000; // リコネクト間隔（ミリ秒）
let isConnected = false;

// 初期化関数
function initAdminPanel() {
    // タブ切り替え
    setupTabs();
    
    // WebSocket接続
    connectWebSocket();
    
    // 各タブの初期化
    initializeDashboard();
    initializeTasksTab();
    initializeGraphQLTab();
    initializeLogsTab();
    initializeSettingsTab();
}

// タブ切り替え機能
function setupTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            // アクティブなタブボタンを更新
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            // アクティブなタブパネルを更新
            const tabId = button.getAttribute('data-tab');
            tabPanes.forEach(pane => pane.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
        });
    });
}

// WebSocket接続
function connectWebSocket() {
    // WebSocketに接続
    socket = new WebSocket(`ws://${window.location.host}/ws`);
    
    // 接続イベント
    socket.addEventListener('open', (event) => {
        console.log('WebSocket接続が確立されました');
        isConnected = true;
        addActivityLog('WebSocket接続が確立されました');
        
        // 最初のデータを要求
        requestInitialData();
    });
    
    // メッセージ受信イベント
    socket.addEventListener('message', (event) => {
        const data = JSON.parse(event.data);
        
        // 受信したデータの種類に応じて処理
        switch(data.type) {
            case 'system_info':
                updateSystemInfo(data.data);
                break;
            case 'task_update':
                updateTaskInfo(data.data);
                break;
            case 'log_entry':
                addLogEntry(data.data);
                break;
            case 'activity':
                addActivityLog(data.data.message);
                break;
            default:
                console.log('未知のメッセージタイプ:', data.type);
        }
    });
    
    // エラーイベント
    socket.addEventListener('error', (event) => {
        console.error('WebSocket接続エラー:', event);
        isConnected = false;
    });
    
    // 切断イベント
    socket.addEventListener('close', (event) => {
        console.log('WebSocket接続が閉じられました');
        isConnected = false;
        
        // 再接続を試みる
        setTimeout(() => {
            console.log('WebSocketに再接続を試みます...');
            connectWebSocket();
        }, reconnectInterval);
    });
}

// 初期データのリクエスト
function requestInitialData() {
    if (!isConnected) return;
    
    // システム情報リクエスト
    socket.send(JSON.stringify({
        action: 'get_system_info'
    }));
    
    // タスク情報リクエスト
    socket.send(JSON.stringify({
        action: 'get_tasks'
    }));
    
    // ログリクエスト
    socket.send(JSON.stringify({
        action: 'get_logs',
        limit: 100
    }));
}

// システム情報の更新
function updateSystemInfo(data) {
    // サーバー情報
    document.getElementById('server-status').textContent = data.server_running ? '実行中' : '停止中';
    document.getElementById('server-status').className = 'status-indicator ' + (data.server_running ? 'running' : 'stopped');
    document.getElementById('server-port').textContent = data.server_port;
    document.getElementById('server-uptime').textContent = formatUptime(data.server_uptime);
    
    // タスクキュー情報
    document.getElementById('queue-status').textContent = data.queue_running ? '実行中' : '停止中';
    document.getElementById('queue-status').className = 'status-indicator ' + (data.queue_running ? 'running' : 'stopped');
    document.getElementById('completed-tasks').textContent = data.completed_tasks;
    document.getElementById('pending-tasks').textContent = data.pending_tasks;
    document.getElementById('running-tasks').textContent = data.running_tasks;
    
    // メモリ使用量
    const memoryPercent = Math.round((data.memory_used / data.memory_total) * 100);
    document.getElementById('memory-usage').style.width = `${memoryPercent}%`;
    document.getElementById('memory-usage').textContent = `${memoryPercent}%`;
    document.getElementById('memory-used').textContent = `${(data.memory_used / (1024 * 1024)).toFixed(2)} MB`;
    document.getElementById('memory-total').textContent = `${(data.memory_total / (1024 * 1024)).toFixed(2)} MB`;
    
    // 設定フォームの値も更新
    document.getElementById('server-host').value = data.server_host;
    document.getElementById('server-port-input').value = data.server_port;
    document.getElementById('worker-threads').value = data.worker_threads;
}

// タスク情報の更新
function updateTaskInfo(tasks) {
    const tasksList = document.getElementById('tasks-list');
    
    // 既存のタスクリストをクリア
    tasksList.innerHTML = '';
    
    // フィルター設定を取得
    const activeFilters = Array.from(document.querySelectorAll('.task-filter:checked'))
        .map(checkbox => checkbox.getAttribute('data-status'));
    
    // タスクをフィルタリングしてリストに追加
    tasks.filter(task => activeFilters.includes(task.status))
        .forEach(task => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${task.id.substring(0, 8)}...</td>
                <td>${task.name}</td>
                <td>${task.type}</td>
                <td><span class="status ${task.status}">${task.status}</span></td>
                <td>
                    <div class="progress-bar">
                        <div class="progress" style="width: ${task.progress * 100}%;">${Math.round(task.progress * 100)}%</div>
                    </div>
                </td>
                <td>${formatDateTime(task.created_at)}</td>
                <td>
                    <button class="view-task" data-id="${task.id}">詳細</button>
                    ${task.status === 'pending' ? `<button class="cancel-task" data-id="${task.id}">キャンセル</button>` : ''}
                </td>
            `;
            tasksList.appendChild(row);
        });
    
    // タスク詳細表示ボタンのイベントリスナー
    document.querySelectorAll('.view-task').forEach(button => {
        button.addEventListener('click', () => {
            const taskId = button.getAttribute('data-id');
            showTaskDetails(taskId, tasks.find(t => t.id === taskId));
        });
    });
    
    // タスクキャンセルボタンのイベントリスナー
    document.querySelectorAll('.cancel-task').forEach(button => {
        button.addEventListener('click', () => {
            const taskId = button.getAttribute('data-id');
            cancelTask(taskId);
        });
    });
}

// タスク詳細表示
function showTaskDetails(taskId, task) {
    const detailContent = document.getElementById('task-detail-content');
    
    if (!task) {
        // タスクが見つからない場合
        detailContent.innerHTML = '<p>タスクが見つかりません</p>';
        return;
    }
    
    // タスク実行時間を計算
    let executionTime = '';
    if (task.completed_at && task.started_at) {
        const seconds = Math.round((task.completed_at - task.started_at) * 100) / 100;
        executionTime = `<p>実行時間: ${seconds} 秒</p>`;
    }
    
    // タスクパラメータとレスポンスをフォーマット
    const params = JSON.stringify(task.params, null, 2);
    const result = task.result ? JSON.stringify(task.result, null, 2) : 'なし';
    const error = task.error ? JSON.stringify(task.error, null, 2) : 'なし';
    
    // 詳細内容を生成
    detailContent.innerHTML = `
        <h4>${task.name}</h4>
        <p>ID: ${task.id}</p>
        <p>タイプ: ${task.type}</p>
        <p>状態: ${task.status}</p>
        <p>進捗: ${Math.round(task.progress * 100)}%</p>
        <p>作成時間: ${formatDateTime(task.created_at)}</p>
        ${task.started_at ? `<p>開始時間: ${formatDateTime(task.started_at)}</p>` : ''}
        ${task.completed_at ? `<p>完了時間: ${formatDateTime(task.completed_at)}</p>` : ''}
        ${executionTime}
        <p>メッセージ: ${task.message}</p>
        
        <h5>パラメータ:</h5>
        <pre>${params}</pre>
        
        <h5>結果:</h5>
        <pre>${result}</pre>
        
        <h5>エラー:</h5>
        <pre>${error}</pre>
    `;
}

// タスクキャンセル
function cancelTask(taskId) {
    if (!isConnected) return;
    
    socket.send(JSON.stringify({
        action: 'cancel_task',
        task_id: taskId
    }));
    
    addActivityLog(`タスク ${taskId.substring(0, 8)}... をキャンセルしました`);
}

// テストタスク作成
function createTestTask() {
    if (!isConnected) return;
    
    socket.send(JSON.stringify({
        action: 'create_test_task',
        name: 'テストタスク'
    }));
    
    addActivityLog('テストタスクを作成しました');
}

// ログエントリを追加
function addLogEntry(logEntry) {
    const logContent = document.getElementById('log-content');
    
    // ログレベルに基づいてCSSクラスを追加
    let logClass = '';
    switch (logEntry.level) {
        case 'ERROR':
            logClass = 'log-error';
            break;
        case 'WARNING':
            logClass = 'log-warning';
            break;
        case 'INFO':
            logClass = 'log-info';
            break;
        default:
            logClass = 'log-debug';
    }
    
    // 新しいログを追加
    const logLine = document.createElement('div');
    logLine.className = `log-line ${logClass}`;
    logLine.innerHTML = `<span class="log-time">${logEntry.time}</span> <span class="log-level">[${logEntry.level}]</span> <span class="log-message">${logEntry.message}</span>`;
    
    logContent.appendChild(logLine);
    
    // 一番下にスクロール
    logContent.scrollTop = logContent.scrollHeight;
}

// アクティビティログを追加
function addActivityLog(message) {
    const activityLog = document.getElementById('activity-log');
    
    // 現在の時刻を取得
    const now = new Date();
    const timeString = now.toLocaleTimeString();
    
    // 新しいログエントリを作成
    const logEntry = document.createElement('div');
    logEntry.className = 'log-entry';
    logEntry.innerHTML = `<span class="timestamp">${timeString}</span> <span class="message">${message}</span>`;
    
    // ログに追加
    activityLog.appendChild(logEntry);
    
    // 最大エントリ数を制限（最新の20件を保持）
    const entries = activityLog.querySelectorAll('.log-entry');
    if (entries.length > 20) {
        activityLog.removeChild(entries[0]);
    }
    
    // 最新のエントリが見えるようにスクロール
    activityLog.scrollTop = activityLog.scrollHeight;
}

// ダッシュボードの初期化
function initializeDashboard() {
    // 自動更新タイマー
    setInterval(() => {
        if (isConnected) {
            socket.send(JSON.stringify({
                action: 'get_system_info'
            }));
        }
    }, 5000); // 5秒ごとに更新
}

// タスク管理タブの初期化
function initializeTasksTab() {
    // タスク一覧更新ボタン
    document.getElementById('refresh-tasks').addEventListener('click', () => {
        if (isConnected) {
            socket.send(JSON.stringify({
                action: 'get_tasks'
            }));
        }
    });
    
    // 完了タスククリアボタン
    document.getElementById('clear-completed').addEventListener('click', () => {
        if (isConnected) {
            socket.send(JSON.stringify({
                action: 'clear_completed_tasks'
            }));
        }
    });
    
    // テストタスク作成ボタン
    document.getElementById('create-test-task').addEventListener('click', createTestTask);
    
    // タスクフィルターの変更イベント
    document.querySelectorAll('.task-filter').forEach(checkbox => {
        checkbox.addEventListener('change', () => {
            // タスクリストを更新（現在のタスクデータを使用）
            if (isConnected) {
                socket.send(JSON.stringify({
                    action: 'get_tasks'
                }));
            }
        });
    });
    
    // 定期的にタスクリストを更新
    setInterval(() => {
        if (document.querySelector('#tasks.active') && isConnected) {
            socket.send(JSON.stringify({
                action: 'get_tasks'
            }));
        }
    }, 3000); // 3秒ごとに更新
}

// GraphQLタブの初期化
function initializeGraphQLTab() {
    const queryEditor = document.getElementById('graphql-query');
    const resultDisplay = document.getElementById('graphql-result');
    const runButton = document.getElementById('run-query');
    const sampleQueries = document.getElementById('sample-queries');
    
    // GraphQLクエリ実行ボタン
    runButton.addEventListener('click', () => {
        const query = queryEditor.value.trim();
        if (!query) return;
        
        // サーバーにクエリを送信
        fetch('/api/graphql', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query })
        })
        .then(response => response.json())
        .then(data => {
            // 結果を表示
            resultDisplay.textContent = JSON.stringify(data, null, 2);
            addActivityLog('GraphQLクエリを実行しました');
        })
        .catch(error => {
            console.error('GraphQLクエリ実行エラー:', error);
            resultDisplay.textContent = `エラー: ${error.message}`;
        });
    });
    
    // サンプルクエリ選択
    sampleQueries.addEventListener('change', () => {
        const selectedValue = sampleQueries.value;
        if (!selectedValue) return;
        
        let query = '';
        
        switch(selectedValue) {
            case 'scene':
                query = `{
  sceneInfo {
    name
    objects {
      name
      type
      location {
        x
        y
        z
      }
    }
  }
}`;
                break;
            case 'objects':
                query = `{
  objects {
    name
    type
    location {
      x
      y
      z
    }
    dimensions {
      x
      y
      z
    }
  }
}`;
                break;
            case 'create-cube':
                query = `mutation {
  createObject(
    type: CUBE,
    name: "GraphQLCube",
    location: {x: 0, y: 0, z: 0}
  ) {
    success
    object {
      name
      location {
        x
        y
        z
      }
      dimensions {
        x
        y
        z
      }
    }
  }
}`;
                break;
            case 'transform':
                query = `mutation {
  transformObject(
    name: "GraphQLCube",
    location: {x: 2, y: 3, z: 1},
    rotation: {x: 0.5, y: 0.3, z: 0.1}
  ) {
    success
    object {
      name
      location {
        x
        y
        z
      }
    }
  }
}`;
                break;
            case 'transaction':
                query = `mutation {
  createTransaction(
    name: "CreateAndTransformCube",
    commands_json: "[{\\"type\\": \\"create_primitive\\", \\"params\\": {\\"type\\": \\"cube\\", \\"name\\": \\"TxCube\\", \\"location\\": [0, 0, 0]}}, {\\"type\\": \\"transform_object\\", \\"params\\": {\\"name\\": \\"TxCube\\", \\"location\\": [2, 3, 1], \\"rotation\\": [0.1, 0.2, 0.3]}}]"
  ) {
    success
    message
    transactionId
    commandCount
  }
}`;
                break;
        }
        
        // エディタにクエリをセット
        queryEditor.value = query;
        sampleQueries.value = '';
    });
}

// ログタブの初期化
function initializeLogsTab() {
    // ログ更新ボタン
    document.getElementById('refresh-logs').addEventListener('click', () => {
        if (isConnected) {
            const level = document.getElementById('log-level').value;
            
            socket.send(JSON.stringify({
                action: 'get_logs',
                limit: 100,
                level: level === 'all' ? null : level
            }));
        }
    });
    
    // ログクリアボタン
    document.getElementById('clear-logs').addEventListener('click', () => {
        document.getElementById('log-content').innerHTML = '';
    });
    
    // ログレベル変更
    document.getElementById('log-level').addEventListener('change', () => {
        if (isConnected) {
            const level = document.getElementById('log-level').value;
            
            socket.send(JSON.stringify({
                action: 'get_logs',
                limit: 100,
                level: level === 'all' ? null : level
            }));
        }
    });
}

// 設定タブの初期化
function initializeSettingsTab() {
    // 設定保存ボタン
    document.getElementById('save-settings').addEventListener('click', () => {
        if (!isConnected) return;
        
        const host = document.getElementById('server-host').value;
        const port = parseInt(document.getElementById('server-port-input').value);
        const workerThreads = parseInt(document.getElementById('worker-threads').value);
        
        socket.send(JSON.stringify({
            action: 'save_settings',
            settings: {
                server_host: host,
                server_port: port,
                worker_threads: workerThreads
            }
        }));
        
        addActivityLog('設定を保存しました');
    });
    
    // サーバー再起動ボタン
    document.getElementById('restart-server').addEventListener('click', () => {
        if (!isConnected) return;
        
        socket.send(JSON.stringify({
            action: 'restart_server'
        }));
        
        addActivityLog('サーバーの再起動を要求しました');
    });
    
    // サーバー停止ボタン
    document.getElementById('stop-server').addEventListener('click', () => {
        if (!isConnected) return;
        
        socket.send(JSON.stringify({
            action: 'stop_server'
        }));
        
        addActivityLog('サーバーの停止を要求しました');
    });
    
    // キュー再起動ボタン
    document.getElementById('restart-queue').addEventListener('click', () => {
        if (!isConnected) return;
        
        socket.send(JSON.stringify({
            action: 'restart_queue'
        }));
        
        addActivityLog('タスクキューの再起動を要求しました');
    });
    
    // 全タスククリアボタン
    document.getElementById('clear-all-tasks').addEventListener('click', () => {
        if (!isConnected) return;
        
        socket.send(JSON.stringify({
            action: 'clear_all_tasks'
        }));
        
        addActivityLog('すべてのタスクをクリアしました');
    });
}

// ヘルパー関数: 時間フォーマット
function formatUptime(seconds) {
    const days = Math.floor(seconds / (24 * 60 * 60));
    const hours = Math.floor((seconds % (24 * 60 * 60)) / (60 * 60));
    const minutes = Math.floor((seconds % (60 * 60)) / 60);
    
    if (days > 0) {
        return `${days}日 ${hours}時間 ${minutes}分`;
    } else if (hours > 0) {
        return `${hours}時間 ${minutes}分`;
    } else {
        return `${minutes}分`;
    }
}

// ヘルパー関数: 日時フォーマット
function formatDateTime(timestamp) {
    if (!timestamp) return 'N/A';
    
    const date = new Date(timestamp * 1000);
    return date.toLocaleString();
}

// ページ読み込み時に初期化
document.addEventListener('DOMContentLoaded', initAdminPanel);
""")
    
    def initialize(self):
        """FastAPIアプリを初期化"""
        if not FASTAPI_AVAILABLE:
            logger.error("FastAPIが利用できません。管理インターフェースを起動できません。")
            return False
        
        # FastAPIアプリを作成
        self.app = FastAPI(
            title="Blender GraphQL MCP 管理パネル",
            docs_url=None,  # SwaggerUIを無効化
            redoc_url=None  # ReDocを無効化
        )
        
        # テンプレートの設定
        templates = Jinja2Templates(directory=self.templates_dir)
        
        # 静的ファイルの提供
        self.app.mount("/static", StaticFiles(directory=self.static_dir), name="static")
        
        # 接続されたWebSocketを管理
        self.connected_websockets = []
        
        # ルートエンドポイント
        @self.app.get("/", response_class=HTMLResponse)
        async def get_admin_panel(request: Request):
            """管理パネルのトップページを返す"""
            return templates.TemplateResponse("index.html", {"request": request})
        
        # WebSocketエンドポイント
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocketによるリアルタイム通信"""
            await websocket.accept()
            self.connected_websockets.append(websocket)
            
            try:
                # 初期システム情報を送信
                system_info = self.get_system_info()
                await websocket.send_text(json.dumps({
                    "type": "system_info",
                    "data": system_info
                }))
                
                # クライアントからのメッセージを処理
                while True:
                    data = await websocket.receive_text()
                    await self.process_websocket_message(websocket, data)
                    
            except WebSocketDisconnect:
                # 切断時の処理
                if websocket in self.connected_websockets:
                    self.connected_websockets.remove(websocket)
                logger.info("WebSocket接続が切断されました")
    
    async def process_websocket_message(self, websocket: WebSocket, message: str):
        """WebSocketメッセージを処理"""
        try:
            data = json.loads(message)
            action = data.get("action")
            
            if action == "get_system_info":
                # システム情報を取得して送信
                system_info = self.get_system_info()
                await websocket.send_text(json.dumps({
                    "type": "system_info",
                    "data": system_info
                }))
                
            elif action == "get_tasks":
                # タスク情報を取得して送信
                tasks = self.get_tasks()
                await websocket.send_text(json.dumps({
                    "type": "task_update",
                    "data": tasks
                }))
                
            elif action == "cancel_task":
                # タスクをキャンセル
                task_id = data.get("task_id")
                if task_id:
                    success = self.cancel_task(task_id)
                    await websocket.send_text(json.dumps({
                        "type": "activity",
                        "data": {
                            "message": f"タスク {task_id[:8]}... のキャンセル{'に成功' if success else 'に失敗'}しました"
                        }
                    }))
                    
                    # タスク一覧も更新して送信
                    tasks = self.get_tasks()
                    await websocket.send_text(json.dumps({
                        "type": "task_update",
                        "data": tasks
                    }))
                
            elif action == "clear_completed_tasks":
                # 完了タスクをクリア
                count = self.clear_completed_tasks()
                await websocket.send_text(json.dumps({
                    "type": "activity",
                    "data": {
                        "message": f"{count}個の完了タスクをクリアしました"
                    }
                }))
                
                # タスク一覧も更新して送信
                tasks = self.get_tasks()
                await websocket.send_text(json.dumps({
                    "type": "task_update",
                    "data": tasks
                }))
                
            elif action == "create_test_task":
                # テストタスクを作成
                task_name = data.get("name", "テストタスク")
                task_id = self.create_test_task(task_name)
                
                await websocket.send_text(json.dumps({
                    "type": "activity",
                    "data": {
                        "message": f"テストタスク '{task_name}' (ID: {task_id[:8]}...) を作成しました"
                    }
                }))
                
                # タスク一覧も更新して送信
                tasks = self.get_tasks()
                await websocket.send_text(json.dumps({
                    "type": "task_update",
                    "data": tasks
                }))
                
            elif action == "get_logs":
                # ログを取得して送信
                limit = data.get("limit", 100)
                level = data.get("level")
                logs = self.get_logs(limit, level)
                
                for log in logs:
                    await websocket.send_text(json.dumps({
                        "type": "log_entry",
                        "data": log
                    }))
                
            # 設定関連のアクション
            elif action == "save_settings":
                # 設定を保存
                settings = data.get("settings", {})
                success = self.save_settings(settings)
                
                await websocket.send_text(json.dumps({
                    "type": "activity",
                    "data": {
                        "message": f"設定の保存{'に成功' if success else 'に失敗'}しました"
                    }
                }))
                
                # システム情報も更新して送信
                system_info = self.get_system_info()
                await websocket.send_text(json.dumps({
                    "type": "system_info",
                    "data": system_info
                }))
                
            elif action == "restart_server":
                # サーバーを再起動
                success = self.restart_server()
                
                await websocket.send_text(json.dumps({
                    "type": "activity",
                    "data": {
                        "message": f"サーバーの再起動{'を開始しました' if success else 'に失敗しました'}"
                    }
                }))
                
            elif action == "stop_server":
                # サーバーを停止
                success = self.stop_server()
                
                await websocket.send_text(json.dumps({
                    "type": "activity",
                    "data": {
                        "message": f"サーバーの停止{'を開始しました' if success else 'に失敗しました'}"
                    }
                }))
                
            elif action == "restart_queue":
                # タスクキューを再起動
                success = self.restart_queue()
                
                await websocket.send_text(json.dumps({
                    "type": "activity",
                    "data": {
                        "message": f"タスクキューの再起動{'に成功' if success else 'に失敗'}しました"
                    }
                }))
                
                # システム情報も更新して送信
                system_info = self.get_system_info()
                await websocket.send_text(json.dumps({
                    "type": "system_info",
                    "data": system_info
                }))
                
            elif action == "clear_all_tasks":
                # 全タスクをクリア
                count = self.clear_all_tasks()
                
                await websocket.send_text(json.dumps({
                    "type": "activity",
                    "data": {
                        "message": f"{count}個のタスクをクリアしました"
                    }
                }))
                
                # タスク一覧も更新して送信
                tasks = self.get_tasks()
                await websocket.send_text(json.dumps({
                    "type": "task_update",
                    "data": tasks
                }))
            
            else:
                logger.warning(f"未知のアクション: {action}")
                
        except json.JSONDecodeError:
            logger.error(f"JSON解析エラー: {message}")
        except Exception as e:
            logger.error(f"WebSocketメッセージ処理エラー: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
    
    async def broadcast_system_update(self):
        """全接続クライアントにシステム更新を通知"""
        if not self.connected_websockets:
            return
        
        # システム情報を取得
        system_info = self.get_system_info()
        
        # 全クライアントに送信
        disconnected = []
        for websocket in self.connected_websockets:
            try:
                await websocket.send_text(json.dumps({
                    "type": "system_info",
                    "data": system_info
                }))
            except Exception:
                # 切断されたWebSocketを記録
                disconnected.append(websocket)
        
        # 切断されたWebSocketを削除
        for websocket in disconnected:
            if websocket in self.connected_websockets:
                self.connected_websockets.remove(websocket)
    
    async def broadcast_task_update(self, task):
        """全接続クライアントにタスク更新を通知"""
        if not self.connected_websockets:
            return
        
        # タスク情報を送信
        disconnected = []
        for websocket in self.connected_websockets:
            try:
                await websocket.send_text(json.dumps({
                    "type": "task_update",
                    "data": [task.to_dict()]
                }))
            except Exception:
                # 切断されたWebSocketを記録
                disconnected.append(websocket)
        
        # 切断されたWebSocketを削除
        for websocket in disconnected:
            if websocket in self.connected_websockets:
                self.connected_websockets.remove(websocket)
    
    def get_system_info(self):
        """システム情報を取得"""
        # タスクキューの状態を取得
        task_queue = get_task_queue()
        
        # メモリ使用量を取得
        import psutil
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_used = memory_info.rss
            memory_total = psutil.virtual_memory().total
        except:
            memory_used = 0
            memory_total = 1
        
        # サーバー起動時間
        import time
        from ..server_adapter import get_server_instance
        
        server = get_server_instance()
        server_start_time = getattr(server, 'start_time', time.time())
        server_uptime = time.time() - server_start_time
        
        # タスク統計
        tasks = task_queue.get_all_tasks()
        completed_tasks = sum(1 for t in tasks if t["status"] == TaskStatus.COMPLETED.value)
        pending_tasks = sum(1 for t in tasks if t["status"] == TaskStatus.PENDING.value)
        running_tasks = sum(1 for t in tasks if t["status"] == TaskStatus.RUNNING.value)
        
        return {
            "server_running": server.is_running() if server else False,
            "server_host": server.host if server else "localhost",
            "server_port": server.port if server else 8765,
            "server_uptime": server_uptime,
            "queue_running": task_queue.running,
            "worker_threads": task_queue.num_workers,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "running_tasks": running_tasks,
            "memory_used": memory_used,
            "memory_total": memory_total
        }
    
    def get_tasks(self):
        """全タスク情報を取得"""
        task_queue = get_task_queue()
        return task_queue.get_all_tasks()
    
    def cancel_task(self, task_id):
        """タスクをキャンセル"""
        task_queue = get_task_queue()
        return task_queue.cancel_task(task_id)
    
    def clear_completed_tasks(self, max_age_seconds=0):
        """完了タスクをクリア"""
        task_queue = get_task_queue()
        return task_queue.clear_completed_tasks(max_age_seconds)
    
    def clear_all_tasks(self):
        """全タスクをクリア"""
        task_queue = get_task_queue()
        
        # タスク数を取得
        all_tasks = task_queue.get_all_tasks()
        task_count = len(all_tasks)
        
        # キャンセル可能なタスクをキャンセル
        for task in all_tasks:
            task_id = task.get("id")
            if task_id and task.get("status") == TaskStatus.PENDING.value:
                task_queue.cancel_task(task_id)
        
        # 全タスクをクリア
        task_queue.clear_completed_tasks(0)
        
        return task_count
    
    def create_test_task(self, name="テストタスク"):
        """テストタスク（サンプル用）を作成"""
        task_queue = get_task_queue()
        
        # テスト用の長時間タスク
        import time
        def test_task_handler(params, progress_callback):
            # 10段階で進捗を更新しながら10秒かけて完了するタスク
            for i in range(10):
                progress = (i + 1) / 10.0
                progress_callback(progress, f"テスト進捗 {int(progress * 100)}%")
                time.sleep(1)
            return {"message": "テストタスク完了", "status": "success"}
        
        # タスクキューにハンドラーを登録（まだ登録されていなければ）
        if "test_task" not in task_queue.task_handlers:
            task_queue.register_task_handler("test_task", test_task_handler)
        
        # テストタスクを作成してキューに追加
        task_id = task_queue.create_and_add_task(
            "test_task",
            {"test_param": True},
            name=name
        )
        
        return task_id
    
    def get_logs(self, limit=100, level=None):
        """ログエントリを取得"""
        # 本来はログファイルから読み取るべきだが、簡易実装として
        # ダミーのログエントリを返す
        logs = []
        for i in range(limit):
            log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_level = "INFO"
            log_message = f"サンプルログエントリ #{i+1}"
            
            logs.append({
                "time": log_time,
                "level": log_level,
                "message": log_message
            })
        
        return logs
    
    def save_settings(self, settings):
        """設定を保存"""
        try:
            # サーバー設定の更新
            from ..server_adapter import get_server_instance
            
            server = get_server_instance()
            if server:
                # ホストとポートの更新（再起動が必要）
                if "server_host" in settings:
                    server.host = settings["server_host"]
                if "server_port" in settings:
                    server.port = int(settings["server_port"])
            
            # タスクキュー設定の更新
            task_queue = get_task_queue()
            if "worker_threads" in settings:
                task_queue.num_workers = int(settings["worker_threads"])
                
                # ワーカー数が変更された場合は再起動が必要
                if task_queue.running:
                    task_queue.stop()
                    task_queue.start()
            
            return True
        except Exception as e:
            logger.error(f"設定保存エラー: {str(e)}")
            return False
    
    def restart_server(self):
        """サーバーを再起動"""
        try:
            from ..server_adapter import get_server_instance, stop_server, start_server
            
            server = get_server_instance()
            if server:
                host = server.host
                port = server.port
                
                # サーバー停止
                stop_server()
                
                # 少し待機
                time.sleep(1)
                
                # サーバー再起動
                start_server(host=host, port=port)
                
                return True
            return False
        except Exception as e:
            logger.error(f"サーバー再起動エラー: {str(e)}")
            return False
    
    def stop_server(self):
        """サーバーを停止"""
        try:
            from ..server_adapter import stop_server
            stop_server()
            return True
        except Exception as e:
            logger.error(f"サーバー停止エラー: {str(e)}")
            return False
    
    def restart_queue(self):
        """タスクキューを再起動"""
        try:
            task_queue = get_task_queue()
            
            # キューの再起動
            if task_queue.running:
                task_queue.stop()
            
            # 少し待機
            time.sleep(1)
            
            # キュー再起動
            task_queue.start()
            
            return True
        except Exception as e:
            logger.error(f"タスクキュー再起動エラー: {str(e)}")
            return False
    
    def start(self):
        """サーバーを起動"""
        if self.running:
            logger.warning("管理サーバーは既に実行中です")
            return False
        
        if not FASTAPI_AVAILABLE:
            logger.error("FastAPIが利用できません。管理インターフェースを起動できません。")
            return False
        
        try:
            # アプリを初期化
            self.initialize()
            
            # サーバーをスレッドで起動
            def run_server():
                try:
                    import uvicorn
                    
                    # UVICORNでサーバーを起動
                    uvicorn.run(
                        self.app,
                        host=self.host,
                        port=self.port,
                        log_level="info"
                    )
                except Exception as e:
                    logger.error(f"管理サーバー実行エラー: {str(e)}")
                    self.running = False
            
            # スレッドを作成
            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()
            
            # 実行フラグを設定
            self.running = True
            
            logger.info(f"管理インターフェースを起動しました: http://{self.host}:{self.port}/")
            return True
            
        except Exception as e:
            logger.error(f"管理サーバー起動エラー: {str(e)}")
            return False
    
    def stop(self):
        """サーバーを停止"""
        if not self.running:
            logger.warning("管理サーバーは既に停止しています")
            return False
        
        # 実行フラグを更新
        self.running = False
        
        logger.info("管理インターフェースを停止しました")
        return True

# グローバルサーバーインスタンス
_admin_server_instance = None

def get_admin_server() -> AdminServer:
    """グローバルの管理サーバーインスタンスを取得"""
    global _admin_server_instance
    if _admin_server_instance is None:
        _admin_server_instance = AdminServer()
    return _admin_server_instance

def initialize_admin_server(host="localhost", port=8766) -> bool:
    """管理サーバーを初期化して起動"""
    server = get_admin_server()
    server.host = host
    server.port = port
    return server.start()

def shutdown_admin_server() -> bool:
    """管理サーバーを停止"""
    global _admin_server_instance
    if _admin_server_instance:
        result = _admin_server_instance.stop()
        _admin_server_instance = None
        return result
    return False