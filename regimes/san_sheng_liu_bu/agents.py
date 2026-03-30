"""
三省六部制 — 各 Agent 的系统提示词与调用逻辑
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


# ── 太子 ─────────────────────────────────────────────────────────────────
TAIZI_SYSTEM = """你是太子，皇上（用户）所有消息的第一接收人。
【重要】你必须且只能返回纯 JSON 格式，不要添加任何解释、引言或 markdown 代码块标记。
你的职责：
1. 判断消息类型：
   - 【闲聊/问答】：type 设为 "chat"，直接回复
   - 【正式旨意/复杂任务】：type 设为 "task"，提炼标题
2. 输出格式：
如果是任务：{"type":"task","title":"简洁标题（≤20字）","content":"完整描述"}
如果是闲聊：{"type":"chat","reply":"你的回复内容"}
注意：不要使用 ```json ``` 标记，直接返回 JSON。title 禁止包含 URL、路径、系统元数据"""


def taizi_dispatch(user_message: str, task_store) -> dict:
    content, tokens = chat(TAIZI_SYSTEM, [{"role": "user", "content": user_message}])
    result = _extract_json(content) or {"type": "chat", "reply": content}
    if result.get("type") == "task":
        task = task_store.create_task(
            title=result.get("title", "未命名任务"),
            content=result.get("content", user_message),
            source="taizi",
        )
        result["task_id"] = task["id"]
        task_store.update_state(task["id"], "Taizi", "taizi", "太子已接旨")
        task_store.add_progress(task["id"], "taizi", "消息分拣完成，转交中书省规划", tokens=tokens)
    return result


# ── 中书省 ───────────────────────────────────────────────────────────────
ZHONGSHU_SYSTEM = """你是中书省规划官，负责将皇上旨意拆解为可执行方案。
【重要】你必须且只能返回纯 JSON 格式，不要添加任何解释。
你的职责：
1. 分析任务需求，起草执行方案（不超过 500 字）
2. 列出需要调用的"部门"及其具体子任务
可调用部门：hubu（户部）、libu（礼部）、bingbu（兵部）、xingbu（刑部）、gongbu（工部）、libu_hr（吏部）
输出格式：{"plan":"方案概要（≤500字）","subtasks":[{"dept":"bingbu","task":"具体子任务"}]}
注意：直接返回 JSON。"""


def zhongshu_plan(task_id: str, task_store) -> dict:
    task = task_store.get_task(task_id)
    if not task:
        raise KeyError(f"任务不存在: {task_id}")
    task_store.update_state(task_id, "Zhongshu", "zhongshu", "中书省开始规划")
    task_store.add_progress(task_id, "zhongshu", "正在分析旨意，起草执行方案...")
    prompt = f"任务标题：{task['title']}\n\n旨意内容：\n{task['content']}"
    content, tokens = chat(ZHONGSHU_SYSTEM, [{"role": "user", "content": prompt}])
    result = _extract_json(content)
    if not result or "subtasks" not in result:
        result = {"plan": content, "subtasks": [{"dept": "bingbu", "task": task["content"]}]}
    task_store.add_progress(task_id, "zhongshu", f"方案已起草，包含 {len(result['subtasks'])} 个子任务", tokens=tokens)
    return result


# ── 门下省 ───────────────────────────────────────────────────────────────
MENXIA_SYSTEM = """你是门下省审议官，负责审核中书省的执行方案。
【重要】你必须且只能返回纯 JSON 格式，不要添加任何解释。
审核标准：方案可行性、完整性、风险。通常合理则准奏。
输出格式：{"verdict":"approved","reason":"审核意见"}
或（封驳时）：{"verdict":"rejected","reason":"原因","revised_plan":"修改建议"}
注意：直接返回 JSON。"""


def menxia_review(task_id: str, plan: dict, task_store, attempt: int = 1) -> dict:
    task = task_store.get_task(task_id)
    task_store.update_state(task_id, "Menxia", "menxia", f"门下省开始审议（第{attempt}轮）")
    task_store.add_progress(task_id, "menxia", "正在审核中书省方案...")
    prompt = (
        f"任务：{task['title']}\n\n中书省方案：\n{plan.get('plan', '')}\n\n子任务列表：\n" +
        "\n".join(f"- {s['dept']}: {s['task']}" for s in plan.get("subtasks", []))
    )
    content, tokens = chat(MENXIA_SYSTEM, [{"role": "user", "content": prompt}])
    result = _extract_json(content) or {"verdict": "approved", "reason": content}
    task_store.add_progress(task_id, "menxia", f"审核结论：{'准奏' if result.get('verdict') == 'approved' else '封驳'}", tokens=tokens)
    return result


# ── 六部 ─────────────────────────────────────────────────────────────────
DEPT_PROMPTS = {
    "hubu": "你是户部，专注数据处理与资源核算。收到任务后，认真执行并给出详细结果。",
    "libu": "你是礼部，专注文档撰写与规范制定。收到任务后，产出高质量文档或规范内容。",
    "bingbu": "你是兵部，专注代码开发与工程实现。收到任务后，给出可运行的代码或工程方案。",
    "xingbu": "你是刑部，专注安全审计与合规检查。收到任务后，识别风险点并给出改进建议。",
    "gongbu": "你是工部，专注基础设施与部署运维。收到任务后，给出具体的部署方案。",
    "libu_hr": "你是吏部，专注人员评估与任务分配。收到任务后，给出合理的人员安排建议。",
}


def dept_execute(dept: str, task_id: str, subtask: str, task_store, context: str = "") -> str:
    system_prompt = DEPT_PROMPTS.get(dept, f"你是{dept}，认真执行分配的任务。")
    user_msg = f"任务背景：{context}\n\n你的子任务：{subtask}"
    content, tokens = chat(system_prompt, [{"role": "user", "content": user_msg}])
    task_store.add_progress(task_id, dept, f"{dept} 子任务执行完毕", tokens=tokens)
    return content


# ── 尚书省 ───────────────────────────────────────────────────────────────
SHANGSHU_SYSTEM = """你是尚书省调度官，负责汇总各部执行结果并呈报皇上。
你的职责：
1. 整合所有子任务的执行结果
2. 去除重复和冗余内容
3. 形成清晰的最终报告
报告格式：简要说明完成情况、核心成果（按子任务分点列出）、风险或后续建议。语气简洁有力。"""


def shangshu_dispatch_and_collect(task_id: str, plan: dict, task_store) -> tuple:
    task = task_store.get_task(task_id)
    task_store.update_state(task_id, "Assigned", "shangshu", "尚书省接管，开始分发子任务")
    task_store.add_progress(task_id, "shangshu", "正在向六部分发子任务...")
    subtasks = plan.get("subtasks", [])
    results = []
    for i, st in enumerate(subtasks):
        dept, sub = st.get("dept", "bingbu"), st.get("task", "")
        task_store.add_progress(task_id, "shangshu", f"分发第 {i+1}/{len(subtasks)} 个子任务 → {dept}: {sub[:30]}...")
        if i == 0:
            task_store.update_state(task_id, "Doing", "shangshu", "六部开始执行")
        try:
            result = dept_execute(dept, task_id, sub, task_store, context=task.get("content", ""))
            results.append({"dept": dept, "task": sub, "result": result, "ok": True})
        except Exception as e:
            task_store.block_task(task_id, reason=f"{dept} 执行子任务失败: {e}", agent=dept)
            task_store.add_progress(task_id, "shangshu", f"[BLOCKED] {dept} 子任务执行失败")
            results.append({"dept": dept, "task": sub, "result": str(e), "ok": False})
            raise RuntimeError(f"[Blocked] {dept} 执行失败: {e}") from e
    task_store.update_state(task_id, "Review", "shangshu", "子任务全部完成，进入审查")
    task_store.add_progress(task_id, "shangshu", "正在汇总各部结果...")
    summary_input = (
        f"任务：{task['title']}\n\n原始旨意：{task['content']}\n\n各部执行结果：\n\n" +
        "\n\n---\n\n".join(f"【{r['dept']}】{r['task']}\n{r['result']}" for r in results)
    )
    final_report, tokens = chat(SHANGSHU_SYSTEM, [{"role": "user", "content": summary_input}])
    task_store.add_progress(task_id, "shangshu", "汇总完毕，准备呈报审查", tokens=tokens)
    return final_report, results


# ── 尚书省审查 ───────────────────────────────────────────────────────────
SHANGSHU_REVIEW_SYSTEM = """你是尚书省审查官，负责对各部执行结果进行最终质量审查。
【重要】你必须且只能返回纯 JSON 格式。
判断标准：产出是否完成子任务、有无明显缺陷或遗漏。
输出格式：{"verdict":"pass","reason":"审查意见","failed_depts":[]}
或（不通过时）：{"verdict":"fail","reason":"原因","failed_depts":["dept1"]}
审查宽松原则：结果基本完整则 pass。直接返回 JSON。"""


def shangshu_review_result(task_id: str, final_report: str, results: list, task_store) -> dict:
    task = task_store.get_task(task_id)
    task_store.add_progress(task_id, "shangshu", "正在审查各部产出质量...")
    results_text = "\n\n".join(f"【{r['dept']}】{r['task']}\n{r['result']}" for r in results)
    prompt = (
        f"原始旨意：{task['title']}\n{task['content']}\n\n"
        f"汇总报告：\n{final_report}\n\n各部详细产出：\n{results_text}"
    )
    content, tokens = chat(SHANGSHU_REVIEW_SYSTEM, [{"role": "user", "content": prompt}])
    result = _extract_json(content) or {"verdict": "pass", "reason": content, "failed_depts": []}
    task_store.add_progress(task_id, "shangshu", f"审查结论：{'通过' if result.get('verdict') == 'pass' else '不通过，退回返工'}", tokens=tokens)
    return result
