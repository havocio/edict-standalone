"""
Dashboard API 服务器 — 纯 Python 标准库，零额外依赖
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

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ==================== 关键：使用统一日志模块 ====================
from logger import configure_logging, logger

configure_logging(
    log_file=ROOT / "dashboard.log",
    level=logging.DEBUG,
    console_output=True
)

logger.debug("✓ 日志系统已初始化，DEBUG 级别已启用")
logger.info("✓ 日志系统运行中")
# ================================================================================

# 使用通用 task_store（通过兼容层）
from framework import task_store
from scripts.orchestrator import run_pipeline


def _log(msg: str):
    logger.info(msg)


STATIC_DIR = ROOT / "dashboard" / "static"

_running_pipelines: dict[str, threading.Thread] = {}
_latest_result: dict = {"pending": False}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type="text/html"):
        if not path.exists():
            self.send_response(404)
            self.end_headers()
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length:
            raw = self.rfile.read(length)
            try:
                return json.loads(raw)
            except Exception:
                pass
        return {}

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path

        if path in ("/", "/index.html"):
            self._send_file(STATIC_DIR / "index.html")
            return

        if path.startswith("/api/"):
            self._handle_get_api(path, parse_qs(parsed.query))
            return

        rel = path.lstrip("/")
        target = STATIC_DIR / rel
        ext_map = {".js": "application/javascript", ".css": "text/css",
                   ".html": "text/html", ".png": "image/png",
                   ".svg": "image/svg+xml", ".ico": "image/x-icon"}
        ct = ext_map.get(Path(rel).suffix, "application/octet-stream")
        self._send_file(target, ct)

    def _handle_get_api(self, path, qs):
        if path == "/api/tasks":
            self._send_json(task_store.load_all_tasks())

        elif path == "/api/tasks/latest":
            self._send_json(_latest_result)

        elif path.startswith("/api/tasks/"):
            task_id = path.split("/api/tasks/")[1].split("/")[0]
            task = task_store.get_task(task_id)
            if task:
                self._send_json(task)
            else:
                self._send_json({"error": "not found"}, 404)

        elif path == "/api/stats":
            tasks = task_store.load_all_tasks()
            by_state = {}
            for t in tasks:
                s = t["state"]
                by_state[s] = by_state.get(s, 0) + 1
            self._send_json({
                "total": len(tasks),
                "by_state": by_state,
                "running": list(_running_pipelines.keys()),
            })

        elif path == "/api/regimes":
            # 返回当前制度和所有可用制度
            try:
                from regimes import get_current_regime, _discover_regimes
                from framework.core import RegimeRegistry
                current = get_current_regime()
                available = _discover_regimes()
                # 加载所有制度获取完整元数据
                from regimes import _load_all_regimes
                _load_all_regimes()
                all_metas = RegimeRegistry.list_all()
                self._send_json({
                    "current": {
                        "id": current.meta.id,
                        "name": current.meta.name,
                        "era": current.meta.era,
                        "description": current.meta.description,
                    },
                    "available": [
                        {"id": m.id, "name": m.name, "era": m.era, "tags": m.tags}
                        for m in all_metas
                    ],
                })
            except Exception as e:
                self._send_json({"error": str(e)}, 500)

        else:
            self._send_json({"error": "unknown endpoint"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read_body()
        self._handle_post_api(path, body)

    def _handle_post_api(self, path, body):
        if path == "/api/tasks/create":
            message = body.get("message", "").strip()
            if not message:
                self._send_json({"error": "message 不能为空"}, 400)
                return

            _log(f"收到新任务: {message[:100]}")

            _latest_result["pending"] = True
            _latest_result.pop("result", None)
            _latest_result.pop("task_id", None)
            _latest_result.pop("error", None)

            def run():
                import traceback
                try:
                    _log("开始处理任务...")
                    r = run_pipeline(message)
                    _latest_result["pending"] = False
                    _latest_result.update(r)
                    tid = r.get("task_id")
                    _log(f"任务完成: task_id={tid}, state={r.get('state')}")
                    if tid and tid in _running_pipelines:
                        del _running_pipelines[tid]
                except Exception as e:
                    _log(f"任务异常: {e}")
                    traceback.print_exc()
                    _latest_result["pending"] = False
                    _latest_result["error"] = str(e)
                    _latest_result["state"] = "Cancelled"
                    tid = _latest_result.get("task_id")
                    if tid and tid in _running_pipelines:
                        del _running_pipelines[tid]

            t = threading.Thread(target=run, daemon=True)
            t.start()
            self._send_json({"status": "accepted", "message": "任务已提交，正在处理..."})
            return

        if path == "/api/tasks/advance":
            task_id  = body.get("task_id")
            to_state = body.get("state")
            if not task_id or not to_state:
                self._send_json({"error": "缺少 task_id 或 state"}, 400)
                return
            try:
                task = task_store.force_advance(task_id, to_state)
                self._send_json(task)
            except Exception as e:
                self._send_json({"error": str(e)}, 400)
            return

        if path == "/api/tasks/cancel":
            task_id = body.get("task_id")
            reason  = body.get("reason", "用户取消")
            if not task_id:
                self._send_json({"error": "缺少 task_id"}, 400)
                return
            try:
                task_store.cancel_task(task_id, reason)
                self._send_json({"status": "cancelled"})
            except Exception as e:
                self._send_json({"error": str(e)}, 400)
            return

        if path == "/api/tasks/unblock":
            task_id = body.get("task_id")
            note    = body.get("note", "人工解除阻塞")
            if not task_id:
                self._send_json({"error": "缺少 task_id"}, 400)
                return
            try:
                task = task_store.unblock_task(task_id, note=note, agent="dashboard")
                self._send_json(task)
            except Exception as e:
                self._send_json({"error": str(e)}, 400)
            return

        # 门下省审核操作
        if path == "/api/tasks/review":
            task_id = body.get("task_id")
            verdict = body.get("verdict", "approved")
            reason  = body.get("reason", "")
            if not task_id:
                self._send_json({"error": "缺少 task_id"}, 400)
                return
            try:
                if verdict == "approved":
                    task = task_store.update_state(task_id, "Assigned", "dashboard", f"手动准奏: {reason}")
                else:
                    task = task_store.update_state(task_id, "Zhongshu", "dashboard", f"手动封驳: {reason}")
                self._send_json(task)
            except Exception as e:
                self._send_json({"error": str(e)}, 400)
            return

        self._send_json({"error": "unknown endpoint"}, 404)


def run_server(host="127.0.0.1", port=7891):
    # 启动时初始化制度状态机
    from regimes import get_current_regime
    regime = get_current_regime()
    task_store.configure_state_machine(
        regime.meta.state_transitions,
        regime.meta.state_agent_map,
    )
    _log(f"当前制度: {regime.meta.name} ({regime.meta.id})")
    
    server = HTTPServer((host, port), Handler)
    _log(f"Dashboard running -> http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        _log("服务已停止")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Edict Dashboard 服务器")
    p.add_argument("--host", default=os.getenv("DASHBOARD_HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(os.getenv("DASHBOARD_PORT", 7891)))
    args = p.parse_args()
    run_server(args.host, args.port)
