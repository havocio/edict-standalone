"""
民主集中制 — 各 Agent 的逻辑
"""
import json, re
from typing import Optional
from scripts.llm_client import chat


def _extract_json(text: str) -> Optional[dict]:
    if not text or not text.strip():
        return None
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try: return json.loads(m.group(1))
        except: pass
    brace_count, start_idx = 0, None
    for i, ch in enumerate(text):
        if ch == '{':
            if brace_count == 0: start_idx = i
            brace_count += 1
        elif ch == '}':
            brace_count -= 1
            if brace_count == 0 and start_idx is not None:
                try: return json.loads(text[start_idx:i+1])
                except: break
    try: return json.loads(text.strip())
    except: return None


# ── 秘书处 ─────────────────────────────────────────────────────────────
SECRETARY_SYSTEM = """你是秘书处，负责接收群众（用户）的消息并转化为正式提案。
【重要】你必须且只能返回纯 JSON 格式，不要添加任何解释。
职责：将用户消息提炼为正式任务提案，提取标题和完整描述。
输出格式：{"type":"task","title":"简洁标题（≤20字）","content":"完整描述"}
注意：直接返回 JSON。"""


def secretary_dispatch(user_message: str, task_store) -> dict:
    from framework.core import get_current_regime_id
    content, tokens = chat(SECRETARY_SYSTEM, [{"role": "user", "content": user_message}])
    result = _extract_json(content) or {"type": "task", "title": "未命名任务", "content": user_message}
    # 所有消息都视为任务，不再区分闲聊
    if result.get("type") == "task":
        # 从公共函数获取当前制度 ID，确保任务归属正确
        regime_id = get_current_regime_id()
        task = task_store.create_task(
            title=result.get("title", "未命名任务"),
            content=result.get("content", user_message),
            source="secretary",
            regime_id=regime_id,
        )
        result["task_id"] = task["id"]
        task_store.update_state(task["id"], "Secretary", "secretary", "秘书处已受理提案")
        task_store.add_progress(task["id"], "secretary", "提案受理完成，转交议会讨论", tokens=tokens)
    return result


# ── 议会（多 Agent 讨论投票）────────────────────────────────────────────
CONGRESS_SYSTEM = """你是议会审议机制。现在要对一项提案进行多部门联合讨论。

讨论规则：
1. 各部门从各自专业角度分析提案
2. 每个部门提出自己的方案建议
3. 最后形成综合讨论结果

模拟以下部门讨论：
- 工业部：从工程实现角度分析
- 科技部：从技术方案角度分析
- 文化部：从用户体验角度分析
- 安全部：从风险控制角度分析

【重要】你必须且只能返回纯 JSON 格式：
{"discussions":[
  {"dept":"工业部","opinion":"意见","suggestion":"建议"},
  {"dept":"科技部","opinion":"意见","suggestion":"建议"},
  {"dept":"文化部","opinion":"意见","suggestion":"建议"},
  {"dept":"安全部","opinion":"意见","suggestion":"建议"}
],"consensus":"综合各方意见形成的共识要点",
"subtasks":[{"dept":"executor","task":"具体子任务描述"}]}
注意：直接返回 JSON。"""


def congress_discuss(task_id: str, task_store) -> dict:
    task = task_store.get_task(task_id)
    task_store.update_state(task_id, "Congress", "congress", "议会开始审议提案")
    task_store.add_progress(task_id, "congress", "各部门正在发言讨论...")

    prompt = f"提案：{task['title']}\n\n内容：{task['content']}"
    content, tokens = chat(CONGRESS_SYSTEM, [{"role": "user", "content": prompt}])
    result = _extract_json(content)
    if not result or "subtasks" not in result:
        result = {
            "discussions": [{"dept": "科技部", "opinion": content, "suggestion": content}],
            "consensus": content,
            "subtasks": [{"dept": "executor", "task": task["content"]}],
        }
    task_store.add_progress(
        task_id, "congress",
        f"议会讨论完成，{len(result.get('discussions', []))} 个部门发表意见，形成 {len(result.get('subtasks', []))} 个子任务",
        tokens=tokens,
    )
    return result


# ── 常务委员会（集中决策）───────────────────────────────────────────────
COMMITTEE_SYSTEM = """你是常务委员会，负责集中决策。议会已完成讨论，现在由你做出最终决策。
【重要】你必须且只能返回纯 JSON 格式。
职责：
1. 审阅议会各部门讨论结果
2. 权衡利弊，做出最终执行方案
3. 确定子任务分配
输出格式：
{"decision":"最终决策说明","plan":"执行方案概要（≤500字）","subtasks":[{"dept":"executor","task":"具体子任务"}]}
注意：直接返回 JSON。"""


def committee_decide(task_id: str, congress_result: dict, task_store) -> dict:
    task = task_store.get_task(task_id)
    task_store.update_state(task_id, "Committee", "committee", "常务委员会开始决策")
    task_store.add_progress(task_id, "committee", "正在审阅议会讨论结果，做出最终决策...")

    discussions_text = "\n".join(
        f"【{d['dept']}】意见：{d['opinion']} | 建议：{d['suggestion']}"
        for d in congress_result.get("discussions", [])
    )
    prompt = (
        f"提案：{task['title']}\n\n内容：{task['content']}\n\n"
        f"议会共识：{congress_result.get('consensus', '')}\n\n"
        f"各部门意见：\n{discussions_text}\n\n"
        f"议会建议子任务：\n" +
        "\n".join(f"- {s['task']}" for s in congress_result.get("subtasks", []))
    )
    content, tokens = chat(COMMITTEE_SYSTEM, [{"role": "user", "content": prompt}])
    result = _extract_json(content)
    if not result or "subtasks" not in result:
        result = {
            "decision": content,
            "plan": content,
            "subtasks": congress_result.get("subtasks", [{"dept": "executor", "task": task["content"]}]),
        }
    task_store.add_progress(task_id, "committee", f"常务委员会决策完成：{result.get('decision', '')[:60]}...", tokens=tokens)
    return result


# ── 执行部委 ───────────────────────────────────────────────────────────
EXECUTOR_SYSTEM = """你是执行部委，负责按照方案执行具体子任务。
收到任务后认真执行，给出详细、有价值的结果。"""


def executor_execute(task_id: str, subtask: str, task_store, context: str = "") -> str:
    user_msg = f"任务背景：{context}\n\n你的子任务：{subtask}"
    content, tokens = chat(EXECUTOR_SYSTEM, [{"role": "user", "content": user_msg}])
    task_store.add_progress(task_id, "executor", f"子任务执行完毕：{subtask[:30]}...", tokens=tokens)
    return content


def executor_dispatch_and_collect(task_id: str, plan: dict, task_store) -> tuple:
    task = task_store.get_task(task_id)
    task_store.update_state(task_id, "Executing", "executor", "执行部委开始执行方案")
    subtasks = plan.get("subtasks", [])
    results = []
    for i, st in enumerate(subtasks):
        sub = st.get("task", "")
        task_store.add_progress(task_id, "executor", f"执行第 {i+1}/{len(subtasks)} 个子任务...")
        try:
            result = executor_execute(task_id, sub, task_store, context=task.get("content", ""))
            results.append({"task": sub, "result": result, "ok": True})
        except Exception as e:
            task_store.block_task(task_id, reason=f"执行失败: {e}", agent="executor")
            results.append({"task": sub, "result": str(e), "ok": False})
            raise RuntimeError(f"[Blocked] 执行失败: {e}") from e
    task_store.update_state(task_id, "Audit", "executor", "执行完毕，进入审计")
    return results


# ── 监察部（事后审计）─────────────────────────────────────────────────
AUDITOR_SYSTEM = """你是监察部，负责对执行结果进行事后审计。
【重要】你必须且只能返回纯 JSON 格式。
审计标准：
1. 执行结果是否满足原始提案要求
2. 有无明显遗漏或质量问题
3. 输出是否具体、有价值
输出格式：{"verdict":"pass","reason":"审计意见","failed_tasks":[]}
或（不通过时）：{"verdict":"fail","reason":"原因","failed_tasks":["子任务描述"]}
审计宽松原则：结果基本满足要求则 pass。直接返回 JSON。"""


def auditor_audit(task_id: str, results: list, task_store) -> dict:
    task = task_store.get_task(task_id)
    task_store.add_progress(task_id, "auditor", "监察部开始事后审计...")
    results_text = "\n\n".join(f"【子任务】{r['task']}\n{r['result']}" for r in results)
    prompt = (
        f"原始提案：{task['title']}\n{task['content']}\n\n"
        f"执行结果：\n{results_text}"
    )
    content, tokens = chat(AUDITOR_SYSTEM, [{"role": "user", "content": prompt}])
    result = _extract_json(content) or {"verdict": "pass", "reason": content, "failed_tasks": []}
    task_store.add_progress(task_id, "auditor", f"审计结论：{'通过' if result.get('verdict') == 'pass' else '不通过'}", tokens=tokens)
    return result
