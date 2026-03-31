"""
民主集中制 — 制度定义与元数据

流程：
  用户消息 → 秘书处分拣 → 议会（多 Agent 投票讨论）→ 常务委员会（集中决策）
          → 执行部委 → 监察部审计 → ✅ 完成
"""
from framework.core import Role, FlowStep, RegimeMeta


ROLES = [
    Role(id="secretary",    name="秘书处",   icon="📋", description="消息分拣 + 简单回复"),
    Role(id="congress",     name="议会",     icon="🏛️", description="多 Agent 讨论，投票形成决议"),
    Role(id="committee",    name="常委会",   icon="🎯", description="集中决策，确定最终方案"),
    Role(id="executor",     name="执行部委", icon="⚙️",  description="按方案执行子任务"),
    Role(id="auditor",      name="监察部",   icon="📊", description="事后审计执行结果质量"),
]

STATES = [
    "Pending",      # 初始
    "Secretary",    # 秘书处处理中
    "Congress",     # 议会讨论中
    "Committee",    # 常委会决策中
    "Executing",    # 执行中
    "Audit",        # 审计中
    "Done",         # 已完成
    "Cancelled",    # 已取消
    "Blocked",      # 已阻塞
]

STATE_TRANSITIONS = {
    "Pending":   ["Secretary"],
    "Secretary": ["Congress", "Done"],     # 简单消息直接回复
    "Congress":  ["Committee"],
    "Committee": ["Executing"],
    "Executing": ["Audit", "Executing"],   # 允许子任务循环更新
    "Audit":     ["Done", "Executing"],    # 审计不通过退回执行
    "Done":      [],
    "Cancelled": [],
    "Blocked":   ["Executing", "Committee"],
}

STATE_AGENT_MAP = {
    "Pending":   None,
    "Secretary": "secretary",
    "Congress":  "congress",
    "Committee": "committee",
    "Executing": "executor",
    "Audit":     "auditor",
    "Done":      None,
    "Cancelled": None,
    "Blocked":   None,
}

FLOW_STEPS = [
    FlowStep(from_state="Pending",   to_state="Secretary", role="secretary"),
    FlowStep(from_state="Secretary", to_state="Congress",  role="secretary"),
    FlowStep(from_state="Congress",  to_state="Committee", role="congress"),
    FlowStep(from_state="Committee", to_state="Executing", role="committee"),
    FlowStep(from_state="Executing", to_state="Audit",     role="executor"),
    FlowStep(from_state="Audit",     to_state="Done",      role="auditor"),
]

META = RegimeMeta(
    id="democratic_centralism",
    name="民主集中制",
    era="现代",
    description="秘书处分拣 → 议会多 Agent 投票讨论 → 常委会集中决策 → 执行部委执行 → 监察部事后审计。民主讨论与集中决策相结合。",
    tags=["民主投票", "集中决策", "事后审计"],
    roles=ROLES,
    states=STATES,
    state_transitions=STATE_TRANSITIONS,
    state_agent_map=STATE_AGENT_MAP,
    flow_steps=FLOW_STEPS,
)


class DemocraticCentralismRegime:
    """民主集中制 — 制度实例"""

    def __init__(self):
        self._meta = META

    @property
    def meta(self) -> RegimeMeta:
        return self._meta

    def dispatch(self, user_message: str, task_store, on_event=None) -> dict:
        task_store.configure_state_machine(STATE_TRANSITIONS, STATE_AGENT_MAP)
        from regimes.democratic_centralism.orchestrator import run_pipeline
        return run_pipeline(user_message, task_store, on_event=on_event)
