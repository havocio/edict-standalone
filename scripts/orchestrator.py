"""
编排引擎 — 完整流转：

  皇上 → 太子分拣 → 中书规划 → 门下审议 → 已派发 → 执行中 → 待审查 → ✅ 已完成
                        ↑          │                              │
                        └──── 封驳 ─┘                    不通过 → 退回 Doing（最多 2 次）
                                                          异常  → Blocked（等待人工恢复）
"""
import traceback
from pathlib import Path

# 使用统一日志模块
from logger import logger
logger.debug("✓ 编排引擎已初始化")

from scripts.agents import (
    taizi_dispatch,
    zhongshu_plan,
    menxia_review,
    shangshu_dispatch_and_collect,
    shangshu_review_result,
)
from scripts import task_store


MAX_MENXIA_ROUNDS  = 3   # 门下省封驳最大轮次
MAX_REVIEW_RETRIES = 2   # 待审查不通过最多退回几次


def run_pipeline(user_message: str, on_event=None) -> dict:
    """
    完整流水线驱动。

    on_event(event_type: str, data: dict) 可选回调，用于实时推送看板事件。
    返回: {"task_id": ..., "result": ..., "state": "Done"|"Cancelled"|"Blocked"}
    """
    logger.debug(f"[Orchestrator] 收到旨意: {user_message[:80]}")

    def emit(event_type, data):
        if on_event:
            try:
                on_event(event_type, data)
            except Exception:
                pass

    # ── 1. 太子分拣 ───────────────────────────────────────────────────────────
    logger.debug("[Orchestrator] 太子分拣开始...")
    emit("taizi_start", {"message": user_message})
    taizi_result = taizi_dispatch(user_message)

    # 简单闲聊 → 直接返回
    if taizi_result.get("type") == "chat":
        logger.debug("[Orchestrator] 太子判断为闲聊，直接回复")
        return {"task_id": None, "result": taizi_result["reply"], "state": "Done"}

    task_id = taizi_result["task_id"]
    logger.debug(f"[Orchestrator] 太子分拣完成 → task_id={task_id}, title={taizi_result.get('title')}")
    emit("taizi_done", {"task_id": task_id, "title": taizi_result.get("title")})

    try:
        # ── 2. 中书省规划 + 门下省审议（封驳循环）────────────────────────────
        plan = None
        for attempt in range(1, MAX_MENXIA_ROUNDS + 1):
            logger.debug(f"[Orchestrator] 第{attempt}轮中书省规划...")
            emit("zhongshu_start", {"attempt": attempt})
            plan = zhongshu_plan(task_id)
            logger.debug(f"[Orchestrator] 中书省规划完成: {plan.get('plan','')[:50]}...")
            emit("zhongshu_done", {"plan": plan.get("plan", "")[:120]})

            emit("menxia_start", {"attempt": attempt})
            review = menxia_review(task_id, plan, attempt=attempt)
            verdict = review.get("verdict")
            logger.debug(f"[Orchestrator] 门下省审核结果: {verdict}")
            emit("menxia_done", {"verdict": verdict, "reason": review.get("reason", "")})

            if verdict == "approved":
                break

            # 封驳：退回中书省重规划
            if attempt < MAX_MENXIA_ROUNDS:
                revised = review.get("revised_plan", "")
                task_store.update_state(
                    task_id, "Zhongshu", "menxia",
                    f"第{attempt}次封驳，退回重规划：{review.get('reason', '')}"
                )
                if revised:
                    # 把修改建议注入任务内容，供下轮中书省参考
                    tasks = task_store.load_all_tasks()
                    for t in tasks:
                        if t["id"] == task_id:
                            t["content"] += f"\n\n【门下省第{attempt}次封驳建议】\n{revised}"
                            task_store._save_all_tasks(tasks)
                            break
            else:
                # 已达最大轮次，强制通过，记录降级日志
                task_store.add_progress(
                    task_id, "menxia",
                    f"已达最大封驳轮次({MAX_MENXIA_ROUNDS})，强制通过执行"
                )

        # ── 3. 尚书省分发 + 六部执行（含 Blocked 处理）──────────────────────
        #    审查不通过时最多退回 MAX_REVIEW_RETRIES 次重做
        final_report = None
        exec_results = []

        for review_round in range(1, MAX_REVIEW_RETRIES + 2):   # +2 = 正常1次 + 最多重做次数
            logger.debug(f"[Orchestrator] 尚书省分发开始，审查轮次 {review_round}")
            emit("shangshu_start", {"review_round": review_round})

            # 若不是第一轮，说明上轮审查不通过，需要重新执行
            if review_round > 1:
                task_store.update_state(
                    task_id, "Assigned", "shangshu",
                    f"第{review_round}轮重新执行（审查不通过）"
                )

            # 执行（内部会更新 Assigned → Doing → Review）
            final_report, exec_results = shangshu_dispatch_and_collect(task_id, plan)

            # ── 4. 审查环节 ───────────────────────────────────────────────────
            logger.debug("[Orchestrator] 开始审查产出质量...")
            emit("review_start", {"round": review_round})
            review_result = shangshu_review_result(task_id, final_report, exec_results)
            review_verdict = review_result.get("verdict", "pass")
            logger.debug(f"[Orchestrator] 审查结果: {review_verdict}")
            emit("review_done", {
                "verdict": review_verdict,
                "reason": review_result.get("reason", ""),
                "failed_depts": review_result.get("failed_depts", []),
            })

            if review_verdict == "pass":
                break   # 审查通过，退出重做循环

            # 审查不通过 → 退回 Doing，继续下一轮（除非已达上限）
            if review_round <= MAX_REVIEW_RETRIES:
                failed = ", ".join(review_result.get("failed_depts", []))
                task_store.update_state(
                    task_id, "Doing", "shangshu",
                    f"第{review_round}轮审查不通过，需返工部门: {failed or '全部'}。{review_result.get('reason', '')}"
                )
                task_store.add_progress(
                    task_id, "shangshu",
                    f"[审查不通过] 第{review_round}轮，退回执行重做"
                )
            else:
                # 超过重做次数，降级通过，记录日志
                task_store.add_progress(
                    task_id, "shangshu",
                    f"已达最大审查重做轮次({MAX_REVIEW_RETRIES})，强制通过"
                )

        # ── 5. 完成 ───────────────────────────────────────────────────────────
        logger.debug("[Orchestrator] 任务完成！")
        task_store.update_state(task_id, "Done", "shangshu", "任务圆满完成")
        # 写入最终结果
        tasks = task_store.load_all_tasks()
        for t in tasks:
            if t["id"] == task_id:
                t["result"] = final_report
                task_store._save_all_tasks(tasks)
                break

        emit("done", {"task_id": task_id, "result": final_report})
        return {"task_id": task_id, "result": final_report, "state": "Done"}

    except RuntimeError as e:
        # 被 shangshu_dispatch_and_collect 抛出的 Blocked 异常
        err_str = str(e)
        logger.warning(f"[Orchestrator] 任务被阻塞: {err_str}")
        task_store.add_progress(task_id, "system", f"任务已阻塞，等待人工干预: {err_str}")
        emit("blocked", {"task_id": task_id, "reason": err_str})
        return {"task_id": task_id, "result": err_str, "state": "Blocked"}

    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"[Orchestrator] 流程异常: {e}\n{tb}")
        task_store.add_progress(task_id, "system", f"流程异常: {e}")
        try:
            task_store.cancel_task(task_id, reason=f"异常: {e}")
        except Exception:
            pass
        emit("error", {"task_id": task_id, "error": str(e), "traceback": tb})
        return {"task_id": task_id, "result": f"流程异常: {e}", "state": "Cancelled"}
