"""
三省六部制 — 制度定义与元数据

流程：
  皇上 → 太子分拣 → 中书规划 → 门下审议 → 已派发 → 执行中 → 待审查 → ✅ 已完成
                        ↑          │                              │
                        └──── 封驳 ─┘                    不通过 → 退回 Doing（最多 2 次）
                                                          异常  → Blocked（等待人工恢复）
"""
from framework.core import Role, FlowStep, RegimeMeta


# ── 角色定义 ──────────────────────────────────────────────────────────────────
ROLES = [
    Role(id="taizi",      name="太子",   icon="👑", description="消息分拣，判断任务类型"),
    Role(id="zhongshu",   name="中书省", icon="📜", description="任务规划，拆解为可执行方案"),
    Role(id="menxia",     name="门下省", icon="⚖️",  description="方案审核，可封驳回中书省"),
    Role(id="shangshu",   name="尚书省", icon="📋", description="任务分发与结果汇总"),
    Role(id="hubu",       name="户部",   icon="💰", description="数据处理与资源核算"),
    Role(id="libu",       name="礼部",   icon="📚", description="文档撰写与规范制定"),
    Role(id="bingbu",     name="兵部",   icon="⚔️",  description="代码开发与工程实现"),
    Role(id="xingbu",     name="刑部",   icon="🔒", description="安全审计与合规检查"),
    Role(id="gongbu",     name="工部",   icon="🏗️", description="基础设施与部署运维"),
    Role(id="libu_hr",    name="吏部",   icon="👤", description="人员评估与任务分配"),
]

# ── 状态定义 ──────────────────────────────────────────────────────────────────
STATES = [
    "Pending",      # 初始
    "Taizi",        # 太子处理中
    "Zhongshu",     # 中书省规划中
    "Menxia",       # 门下省审核中
    "Assigned",     # 已派发
    "Doing",        # 执行中
    "Review",       # 待审查
    "Done",         # 已完成
    "Cancelled",    # 已取消
    "Blocked",      # 已阻塞
]

STATE_TRANSITIONS = {
    "Pending":   ["Taizi"],
    "Taizi":     ["Zhongshu", "Done"],         # 简单任务太子可直接完成
    "Zhongshu":  ["Menxia"],
    "Menxia":    ["Assigned", "Zhongshu"],     # 封驳可退回中书省
    "Assigned":  ["Doing"],
    "Doing":     ["Review", "Doing"],           # Doing 允许自循环
    "Review":    ["Done", "Doing"],             # 审查不通过退回执行
    "Done":      [],
    "Cancelled": [],
    "Blocked":   ["Doing", "Assigned"],
}

STATE_AGENT_MAP = {
    "Pending":   None,
    "Taizi":     "taizi",
    "Zhongshu":  "zhongshu",
    "Menxia":    "menxia",
    "Assigned":  "shangshu",
    "Doing":     None,
    "Review":    "shangshu",
    "Done":      None,
    "Cancelled": None,
    "Blocked":   None,
}

# ── 流程步骤（用于可视化）─────────────────────────────────────────────────────
FLOW_STEPS = [
    FlowStep(from_state="Pending",  to_state="Taizi",     role="taizi"),
    FlowStep(from_state="Taizi",    to_state="Zhongshu",  role="taizi"),
    FlowStep(from_state="Zhongshu", to_state="Menxia",    role="zhongshu"),
    FlowStep(from_state="Menxia",   to_state="Assigned",  role="menxia"),
    FlowStep(from_state="Assigned", to_state="Doing",     role="shangshu"),
    FlowStep(from_state="Doing",    to_state="Review",    role="shangshu"),
    FlowStep(from_state="Review",   to_state="Done",      role="shangshu"),
]


# ── 制度元数据 ────────────────────────────────────────────────────────────────
META = RegimeMeta(
    id="san_sheng_liu_bu",
    name="三省六部制",
    era="隋唐",
    description="中书省起草方案、门下省审核封驳、尚书省执行汇总。决策、审核、执行三者严格分离，流水线式状态流转。",
    tags=["分权制衡", "流水线", "封驳审核"],
    roles=ROLES,
    states=STATES,
    state_transitions=STATE_TRANSITIONS,
    state_agent_map=STATE_AGENT_MAP,
    flow_steps=FLOW_STEPS,
)


class SanShengLiuBuRegime:
    """三省六部制 — 制度实例"""
    
    def __init__(self):
        self._meta = META
    
    @property
    def meta(self) -> RegimeMeta:
        return self._meta
    
    def dispatch(self, user_message: str, task_store, on_event=None) -> dict:
        """
        执行完整流水线
        委托给 orchestrator 实现
        """
        # 先注入状态机
        task_store.configure_state_machine(
            STATE_TRANSITIONS,
            STATE_AGENT_MAP,
        )
        
        from regimes.san_sheng_liu_bu.orchestrator import run_pipeline
        return run_pipeline(user_message, task_store, on_event=on_event)
