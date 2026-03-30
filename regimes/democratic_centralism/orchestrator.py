"""
民主集中制 — 编排引擎
流程：秘书处 → 议会 → 常委会 → 执行部委 → 监察部
"""
import traceback
from logger import logger

from regimes.democratic_centralism.agents import (
    secretary_dispatch,
    congress_discuss,
    committee_decide,
    executor_dispatch_and_collect,
    auditor_audit,
)

MAX_AUDIT_RETRIES = 2


def run_pipeline(user_message: str, task_store, on_event=None) -> dict:
    logger.debug(f"[DC] 收到提案: {user_message[:80]}")

    def emit(event_type, data):
        if on_event:
            try: on_event(event_type, data)
            except: pass

    # ── 1. 秘书处分拣 ──────────────────────────────────────────────
    emit("secretary_start", {"message": user_message})
    sec_result = secretary_dispatch(user_message, task_store)

    if sec_result.get("type") == "chat":
        return {"task_id": None, "result": sec_result["reply"], "state": "Done"}

    task_id = sec_result["task_id"]
    emit("secretary_done", {"task_id": task_id, "title": sec_result.get("title")})

    try:
        # ── 2. 议会讨论 ─────────────────────────────────────────────
        emit("congress_start", {})
        congress_result = congress_discuss(task_id, task_store)
        emit("congress_done", {"consensus": congress_result.get("consensus", "")[:80]})

        # ── 3. 常委会集中决策 ───────────────────────────────────────
        emit("committee_start", {})
        plan = committee_decide(task_id, congress_result, task_store)
        emit("committee_done", {"decision": plan.get("decision", "")[:80]})

        # ── 4. 执行 + 审计循环 ─────────────────────────────────────
        final_results = None
        for audit_round in range(1, MAX_AUDIT_RETRIES + 2):
            emit("executor_start", {"round": audit_round})
            results = executor_dispatch_and_collect(task_id, plan, task_store)

            emit("audit_start", {"round": audit_round})
            audit = auditor_audit(task_id, results, task_store)

            if audit.get("verdict") == "pass":
                final_results = results
                break

            if audit_round <= MAX_AUDIT_RETRIES:
                task_store.update_state(task_id, "Executing", "auditor", f"审计不通过，第{audit_round}轮重新执行")
            else:
                task_store.add_progress(task_id, "auditor", f"已达最大审计重做轮次({MAX_AUDIT_RETRIES})，强制通过")
                final_results = results

        # ── 5. 汇总 + 完成 ─────────────────────────────────────────
        final_report = _summarize(task_id, final_results, plan, task_store)
        task_store.update_state(task_id, "Done", "auditor", "任务圆满完成")
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
        logger.warning(f"[DC] 任务被阻塞: {err_str}")
        task_store.add_progress(task_id, "system", f"任务已阻塞: {err_str}")
        emit("blocked", {"task_id": task_id, "reason": err_str})
        return {"task_id": task_id, "result": err_str, "state": "Blocked"}

    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"[DC] 流程异常: {e}\n{tb}")
        task_store.add_progress(task_id, "system", f"流程异常: {e}")
        try: task_store.cancel_task(task_id, reason=f"异常: {e}")
        except: pass
        emit("error", {"task_id": task_id, "error": str(e)})
        return {"task_id": task_id, "result": f"流程异常: {e}", "state": "Cancelled"}


def _summarize(task_id, results, plan, task_store):
    """汇总执行结果"""
    from scripts.llm_client import chat
    task = task_store.get_task(task_id)
    summary_input = (
        f"任务：{task['title']}\n\n原始提案：{task['content']}\n\n"
        f"决策方案：{plan.get('plan', '')}\n\n各子任务执行结果：\n\n" +
        "\n\n---\n\n".join(f"【子任务】{r['task']}\n{r['result']}" for r in results)
    )
    prompt = "请将以上执行结果汇总为一份清晰的最终报告。格式：简要说明完成情况，核心成果分点列出，附上后续建议。"
    content, tokens = chat(prompt, [{"role": "user", "content": summary_input}])
    task_store.add_progress(task_id, "auditor", "汇总报告完成", tokens=tokens)
    return content
