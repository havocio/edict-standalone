"""
Dashboard API 服务器 -- 纯 Python 标准库，零额外依赖
提供 REST API + 静态文件服务 + 制度信息 API
默认端口：7891
"""
import json
import logging
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

# ==================== 关键：使用统一日志模块 ====================
from logger import configure_logging, logger

configure_logging(
    log_file=ROOT / "dashboard.log",
    level=logging.DEBUG,
    console_output=True
)

logger.debug("[OK] 日志系统已初始化，DEBUG 级别已启用")
logger.info("[OK] 日志系统运行中")
# ================================================================================

# 静态文件目录（Vue 构建输出）
STATIC_DIR = ROOT / "dashboard-ui" / "dist"

# 导入制度相关模块
from framework import RegimeRegistry
from regimes import get_regime
from framework import task_store

# 运行时状态
_running_pipelines: dict[str, threading.Thread] = {}
_latest_result: dict = {"pending": False}

# 当前激活的制度 ID（运行时可切换，优先级高于 .env 中的 REGIME）
_current_regime_id: str = os.getenv("REGIME", "san_sheng_liu_bu")


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器"""

    def log_message(self, format, *args):
        """使用统一日志"""
        logger.info(f"[REQUEST] {self.address_string()} - {format % args}")

    def _send_json(self, data: dict, status: int = 200):
        """发送 JSON 响应"""
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def _send_error(self, message: str, status: int = 400):
        """发送错误响应"""
        self._send_json({"error": message}, status)

    def _serve_static(self, path: str):
        """服务静态文件"""
        if path == "/":
            path = "/index.html"

        file_path = STATIC_DIR / path.lstrip("/")

        # 安全检查：确保在 STATIC_DIR 内
        try:
            file_path.relative_to(STATIC_DIR)
        except ValueError:
            self._send_error("Forbidden", 403)
            return

        if not file_path.exists() or file_path.is_dir():
            # 尝试返回 index.html（SPA 路由支持）
            index_path = STATIC_DIR / "index.html"
            if index_path.exists():
                file_path = index_path
            else:
                self._send_error("Not found", 404)
                return

        # 确定 MIME 类型
        mime_types = {
            ".html": "text/html",
            ".js": "application/javascript",
            ".css": "text/css",
            ".json": "application/json",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
        }
        content_type = mime_types.get(file_path.suffix, "application/octet-stream")

        try:
            content = file_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            logger.error(f"静态文件服务错误: {e}")
            self._send_error("Internal error", 500)

    def do_GET(self):
        """处理 GET 请求"""
        parsed = urlparse(self.path)
        path = parsed.path

        # API 路由
        if path == "/api/tasks":
            self._handle_get_tasks()
        elif path == "/api/tasks/latest":
            self._handle_get_latest_task()
        elif path == "/api/regimes":
            self._handle_get_regimes()
        elif path.startswith("/api/tasks/"):
            task_id = path.split("/")[-1]
            self._handle_get_task(task_id)
        # 静态文件
        else:
            self._serve_static(path)

    def do_POST(self):
        """处理 POST 请求"""
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/tasks":
            self._handle_create_task()
        elif path == "/api/regimes/switch":
            self._handle_switch_regime()
        elif path.startswith("/api/tasks/") and path.endswith("/cancel"):
            task_id = path.split("/")[-2]
            self._handle_cancel_task(task_id)
        elif path.startswith("/api/tasks/") and path.endswith("/advance"):
            task_id = path.split("/")[-2]
            self._handle_advance_task(task_id)
        elif path.startswith("/api/tasks/") and path.endswith("/unblock"):
            task_id = path.split("/")[-2]
            self._handle_unblock_task(task_id)
        else:
            self._send_error("Not found", 404)

    def do_OPTIONS(self):
        """处理 CORS 预检请求"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    @staticmethod
    def _serialize_task(task: dict) -> dict:
        """序列化任务对象，补全缺失的 regime_id（历史任务兼容）"""
        if not task.get("regime_id"):
            task = dict(task)  # 浅拷贝，不改原对象
            task["regime_id"] = "san_sheng_liu_bu"
        return task

    def _handle_get_tasks(self):
        """获取所有任务"""
        tasks = [self._serialize_task(t) for t in task_store.load_all_tasks()]
        self._send_json({"tasks": tasks, "count": len(tasks)})

    def _handle_get_task(self, task_id: str):
        """获取单个任务"""
        task = task_store.get_task(task_id)
        if task:
            self._send_json(self._serialize_task(task))
        else:
            self._send_error("Task not found", 404)

    def _handle_get_latest_task(self):
        """获取最新任务状态（用于轮询）"""
        global _latest_result
        if _latest_result and not _latest_result.get("pending", False):
            self._send_json(self._serialize_task(_latest_result))
        else:
            self._send_json({"pending": True})

    def _handle_get_regimes(self):
        """获取所有可用制度"""
        metas = RegimeRegistry.list_all()
        regimes = []
        for meta in metas:
            regimes.append({
                "id": meta.id,
                "name": meta.name,
                "era": meta.era,
                "description": meta.description,
                "tags": meta.tags,
                "roles": [{"id": r.id, "name": r.name, "icon": r.icon, "description": r.description} for r in meta.roles],
                "states": meta.states,
                "role_count": len(meta.roles),
                "state_count": len(meta.states),
            })

        global _current_regime_id
        # 找当前制度完整对象
        current_obj = next((r for r in regimes if r["id"] == _current_regime_id), None)
        self._send_json({
            "regimes": regimes,
            "current": _current_regime_id,
            "current_obj": current_obj,
        })

    def _handle_switch_regime(self):
        """切换当前制度"""
        global _current_regime_id
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self._send_error("Empty body", 400)
            return

        try:
            body = self.rfile.read(content_length).decode()
            data = json.loads(body)
            regime_id = data.get("regime_id", "").strip()

            if not regime_id:
                self._send_error("regime_id is required", 400)
                return

            # 验证制度是否存在
            metas = RegimeRegistry.list_all()
            valid_ids = [m.id for m in metas]
            if regime_id not in valid_ids:
                self._send_error(f"Unknown regime: {regime_id}. Available: {valid_ids}", 400)
                return

            old_id = _current_regime_id
            _current_regime_id = regime_id
            os.environ["REGIME"] = regime_id
            logger.info(f"制度已切换: {old_id} -> {regime_id}")

            # 返回切换后的制度信息
            regime = RegimeRegistry.get(regime_id)
            meta = regime.meta
            self._send_json({
                "status": "switched",
                "from": old_id,
                "to": regime_id,
                "regime": {
                    "id": meta.id,
                    "name": meta.name,
                    "era": meta.era,
                    "description": meta.description,
                    "tags": meta.tags,
                    "roles": [{"id": r.id, "name": r.name, "icon": r.icon, "description": r.description} for r in meta.roles],
                    "states": meta.states,
                    "role_count": len(meta.roles),
                    "state_count": len(meta.states),
                }
            })

        except json.JSONDecodeError:
            self._send_error("Invalid JSON", 400)
        except Exception as e:
            logger.error(f"切换制度错误: {e}")
            self._send_error(str(e), 500)

    def _handle_create_task(self):
        """创建新任务"""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self._send_error("Empty body", 400)
            return

        try:
            body = self.rfile.read(content_length).decode()
            data = json.loads(body)
            message = data.get("message", "").strip()
            # 允许前端指定制度，否则用当前激活制度
            task_regime_id = data.get("regime_id", "").strip() or _current_regime_id

            if not message:
                self._send_error("Message is required", 400)
                return

            # 创建任务
            from main import process_message

            def run_task():
                global _latest_result
                try:
                    _latest_result = {"pending": True}
                    # 临时将 REGIME 环境变量设为此任务的制度
                    os.environ["REGIME"] = task_regime_id
                    result = process_message(message)
                    _latest_result = {"pending": False, "result": result}
                except Exception as e:
                    logger.error(f"任务处理错误: {e}")
                    _latest_result = {"pending": False, "error": str(e)}

            # 在后台线程运行
            threading.Thread(target=run_task, daemon=True).start()

            self._send_json({"status": "started", "message": "任务已启动", "regime_id": task_regime_id})

        except json.JSONDecodeError:
            self._send_error("Invalid JSON", 400)
        except Exception as e:
            logger.error(f"创建任务错误: {e}")
            self._send_error(str(e), 500)

    def _handle_cancel_task(self, task_id: str):
        """取消任务"""
        task = task_store.get_task(task_id)
        if not task:
            self._send_error("Task not found", 404)
            return

        task_store.cancel_task(task_id, "用户取消")
        self._send_json({"status": "cancelled", "task_id": task_id})

    def _handle_advance_task(self, task_id: str):
        """推进任务状态"""
        task = task_store.get_task(task_id)
        if not task:
            self._send_error("Task not found", 404)
            return

        regime = get_regime(_current_regime_id)
        current_state = task.get("state", "")

        # 找到下一个状态
        next_state = None
        for i, state in enumerate(regime.states):
            if state == current_state and i < len(regime.states) - 1:
                next_state = regime.states[i + 1]
                break

        if next_state:
            task_store.force_advance(task_id, next_state)
            self._send_json({"status": "advanced", "state": next_state})
        else:
            self._send_error("No next state", 400)

    def _handle_unblock_task(self, task_id: str):
        """解除任务阻塞"""
        task = task_store.get_task(task_id)
        if not task:
            self._send_error("Task not found", 404)
            return

        if task.get("state") == "Blocked":
            task_store.unblock_task(task_id)
            self._send_json({"status": "unblocked"})
        else:
            self._send_json({"status": "unchanged", "reason": "Task not blocked"})


def start_dashboard_server(port: int = 7891):
    """启动 Dashboard 服务器"""
    server = HTTPServer(("127.0.0.1", port), DashboardHandler)
    logger.info(f"[OK] Dashboard 服务器已启动: http://127.0.0.1:{port}")

    # 检查静态文件目录
    if not STATIC_DIR.exists():
        logger.warning(f"[WARN] 静态文件目录不存在: {STATIC_DIR}")
        logger.warning("  请运行: cd dashboard-ui && npm run build")
    elif not (STATIC_DIR / "index.html").exists():
        logger.warning(f"[WARN] 未找到 index.html，请构建前端")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("[OK] 服务器已停止")
        server.shutdown()


if __name__ == "__main__":
    port = int(os.getenv("DASHBOARD_PORT", "7891"))
    start_dashboard_server(port)
