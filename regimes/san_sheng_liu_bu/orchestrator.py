"""
三省六部制 — 编排引擎
从原 scripts/orchestrator.py 迁移而来，task_store 作为参数传入
"""
import traceback
from logger import logger

from regimes.san_sheng_liu_bu.agents import (
    taizi_dispatch,
    zhongshu_plan,
    menxia_review,
    shangshu_dispatch_and_collect,
    shangshu_review_result,
)

MAX_MENXIA_ROUNDS  = 3
MAX_REVIEW_RETRIES = 2


def run_pipeline(user_message: str, task_store, on_event=None) -> dict:
    """
    完整流水线驱动。
    on_event(event_type, data) 可选回调。
    返回: {"task_id", "result", "state"}
    """
    logger.debug(f"[Orchestrator] 收到旨意: {user_message[:80]}")

    def emit(event_type, data):
        if on_event:
            try: on_event(event_type, data)
            except: pass

    # ── 1. 太子分拣 ───────────────────────────────────────────────────
    logger.debug("[Orchestrator] 太子分拣开始...")
    emit("taizi_start", {"message": user_message})
    taizi_result = taizi_dispatch(user_message, task_store)

    # 所有消息都视为任务，不再区分闲聊
    task_id = taizi_result["task_id"]
    logger.debug(f"[Orchestrator] 太子分拣完成 → task_id={task_id}")
    emit("taizi_done", {"task_id": task_id, "title": taizi_result.get("title")})

    try:
        # ── 2. 中书省规划 + 门下省审议（封驳循环）────────────────────
        plan = None
        for attempt in range(1, MAX_MENXIA_ROUNDS + 1):
            emit("zhongshu_start", {"attempt": attempt})
            plan = zhongshu_plan(task_id, task_store)
            emit("zhongshu_done", {"plan": plan.get("plan", "")[:120]})

            emit("menxia_start", {"attempt": attempt})
            review = menxia_review(task_id, plan, task_store, attempt=attempt)
            verdict = review.get("verdict")

            if verdict == "approved":
                break

            if attempt < MAX_MENXIA_ROUNDS:
                revised = review.get("revised_plan", "")
                task_store.update_state(
                    task_id, "Zhongshu", "menxia",
                    f"第{attempt}次封驳，退回重规划：{review.get('reason', '')}"
                )
                if revised:
                    tasks = task_store.load_all_tasks()
                    for t in tasks:
                        if t["id"] == task_id:
                            t["content"] += f"\n\n【门下省第{attempt}次封驳建议】\n{revised}"
                            task_store._save_all_tasks(tasks)
                            break
            else:
                task_store.add_progress(task_id, "menxia", f"已达最大封驳轮次({MAX_MENXIA_ROUNDS})，强制通过")

        # ── 3. 尚书省分发 + 执行 + 审查 ──────────────────────────────
        final_report = None
        exec_results = []

        for review_round in range(1, MAX_REVIEW_RETRIES + 2):
            emit("shangshu_start", {"review_round": review_round})

            if review_round > 1:
                task_store.update_state(task_id, "Assigned", "shangshu", f"第{review_round}轮重新执行")

            final_report, exec_results = shangshu_dispatch_and_collect(task_id, plan, task_store)

            emit("review_start", {"round": review_round})
            review_result = shangshu_review_result(task_id, final_report, exec_results, task_store)
            review_verdict = review_result.get("verdict", "pass")

            if review_verdict == "pass":
                break

            if review_round <= MAX_REVIEW_RETRIES:
                failed = ", ".join(review_result.get("failed_depts", []))
                task_store.update_state(
                    task_id, "Doing", "shangshu",
                    f"第{review_round}轮审查不通过，需返工: {failed or '全部'}"
                )
            else:
                task_store.add_progress(task_id, "shangshu", f"已达最大审查重做轮次({MAX_REVIEW_RETRIES})，强制通过")

        # ── 4. 完成 ──────────────────────────────────────────────────
        task_store.update_state(task_id, "Done", "shangshu", "任务圆满完成")
        tasks = task_store.load_all_tasks()
        for t in tasks:
            if t["id"] == task_id:
                t["result"] = final_report
                task_store._save_all_tasks(tasks)
                break

        emit("done", {"task_id": task_id, "result": final_report})
        return {"task_id": task_id, "result": final_report, "state": "Done"}

    except RuntimeError as e:
        err_str = str(e)
        logger.warning(f"[Orchestrator] 任务被阻塞: {err_str}")
        task_store.add_progress(task_id, "system", f"任务已阻塞: {err_str}")
        emit("blocked", {"task_id": task_id, "reason": err_str})
        return {"task_id": task_id, "result": err_str, "state": "Blocked"}

    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"[Orchestrator] 流程异常: {e}\n{tb}")
        task_store.add_progress(task_id, "system", f"流程异常: {e}")
        try: task_store.cancel_task(task_id, reason=f"异常: {e}")
        except: pass
        emit("error", {"task_id": task_id, "error": str(e), "traceback": tb})
        return {"task_id": task_id, "result": f"流程异常: {e}", "state": "Cancelled"}
