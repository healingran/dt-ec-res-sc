from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.websockets import WebSocket, WebSocketDisconnect
import asyncio
import json
import random
import sqlite3
import time  # ✅ 新增：用于生成时间戳

# 数据库连接函数（您已定义，保持不变）
def get_db_connection():
    conn = sqlite3.connect('smart_city.db')
    conn.row_factory = sqlite3.Row  # 让查询结果像字典一样访问
    return conn

app = FastAPI()

# 主页，用于测试连接
@app.get("/")
def hello():
    return {"message": "太牛了，记事本也能写智慧城市后端！"}

# WebSocket 端点：用于实时推送节点负载数据
@app.websocket("/ws/node_load")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()  # 接受客户端连接
    try:
        while True:
            # 模拟节点负载数据
            load_data = {
                "node": "server_01",
                "load": round(random.uniform(0.0, 1.0), 2),
                "timestamp": time.time()  # ✅ 修改：使用标准的Unix时间戳
            }
            
            # ✅ 【核心修改】：将 INSERT 改为 INSERT OR REPLACE
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                # 当 node_name 已存在时，替换整行数据；不存在时，插入新行。
                cursor.execute("""
                    INSERT OR REPLACE INTO nodes (node_name, load, timestamp)
                    VALUES (?, ?, ?)
                """, (load_data["node"], load_data["load"], load_data["timestamp"]))
                conn.commit()
                print(f"✅ 数据已更新到数据库: {load_data}")  # 修改了日志文本
            except sqlite3.Error as e:
                print(f"❌ 数据库操作错误: {e}")
            finally:
                conn.close()
            # ✅ 数据存储部分结束

            # 将数据转为 JSON 字符串并发送给客户端
            await websocket.send_text(json.dumps(load_data))
            await asyncio.sleep(1)  # 等待1秒，实现“每秒推送”
    except WebSocketDisconnect:
        print("客户端断开连接")
    except Exception as e:
        print(f"WebSocket 发生未知错误: {e}")

# ✅ 新增：API 接口 - 查询所有节点数据
@app.get("/api/nodes")
def get_all_nodes():
    """
    查询 nodes 表中所有的节点负载记录。
    返回格式： { "nodes": [ {...}, {...} ] }
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM nodes ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        # 将查询结果转换为字典列表
        nodes = [dict(row) for row in rows]
        return {"nodes": nodes}
    except sqlite3.Error as e:
        return {"error": f"数据库查询失败: {e}"}
    finally:
        conn.close()

# ✅ 新增：API 接口 - 根据节点名查询最新数据
@app.get("/api/nodes/{node_name}")
def get_latest_node_data(node_name: str):
    """
    查询指定节点的最新一条负载记录。
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT * FROM nodes 
            WHERE node_name = ? 
            ORDER BY timestamp DESC 
            LIMIT 1
        """, (node_name,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        else:
            return {"message": f"未找到节点 {node_name} 的数据"}
    except sqlite3.Error as e:
        return {"error": f"数据库查询失败: {e}"}
    finally:
        conn.close()

# 可选：提供一个简单的 HTML 页面用于测试 WebSocket
@app.get("/test")
def test_page():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WebSocket 测试</title>
    </head>
    <body>
        <h1>节点负载实时数据</h1>
        <div id="data">等待数据...</div>
        <hr>
        <h2>数据持久化验证</h2>
        <p>WebSocket服务每秒生成一条模拟数据，并自动存入数据库。</p>
        <p>你可以访问以下链接来验证：</p>
        <ul>
            <li><a href="/api/nodes" target="_blank">/api/nodes</a> - 查看所有历史数据</li>
            <li><a href="/api/nodes/server_01" target="_blank">/api/nodes/server_01</a> - 查看 server_01 的最新数据</li>
        </ul>
        <script>
            const ws = new WebSocket("ws://" + window.location.host + "/ws/node_load");
            ws.onmessage = function(event) {
                document.getElementById("data").innerText = `实时推送: ${event.data}`;
            };
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)