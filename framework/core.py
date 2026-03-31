"""
制度框架核心抽象层
定义所有制度必须实现的 Protocol 接口
"""
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable, Optional, Dict, List, Any
import importlib


@dataclass
class Role:
    """制度中的角色"""
    id: str                    # 唯一标识，如 "taizi", "zhongshu"
    name: str                  # 显示名，如 "太子", "中书省"
    icon: str                  # emoji 图标
    description: str           # 角色职责描述


@dataclass
class FlowStep:
    """流程步骤"""
    from_state: str            # 来源状态
    to_state: str              # 目标状态
    role: str                  # 负责此步骤的角色 id


@dataclass
class RegimeMeta:
    """制度元数据"""
    id: str                    # 唯一标识，如 "san_sheng_liu_bu"
    name: str                  # 显示名，如 "三省六部制"
    era: str                   # 朝代/时代，如 "隋唐"
    description: str           # 制度描述
    tags: List[str]            # 标签，如 ["分权制衡", "流水线"]
    
    roles: List[Role]          # 所有角色
    states: List[str]          # 状态列表（按顺序）
    state_transitions: Dict[str, List[str]]  # {state: [allowed_next_states]}
    state_agent_map: Dict[str, Optional[str]]  # {state: role_id}（可为 None）
    
    flow_steps: Optional[List[FlowStep]] = None  # 可选，用于流程可视化


@runtime_checkable
class Regime(Protocol):
    """
    制度协议 — 所有制度模块必须实现此接口
    
    一个制度模块是独立的包，包含：
    - regime.py：制度定义和元数据
    - agents.py：各角色的 Prompt 和 LLM 调用逻辑
    - orchestrator.py：完整流水线编排
    """
    
    @property
    def meta(self) -> RegimeMeta:
        """返回制度的元数据"""
        ...
    
    def dispatch(
        self,
        user_message: str,
        task_store: Any,
        on_event=None
    ) -> dict:
        """
        执行完整流水线
        
        Args:
            user_message: 用户输入的旨意
            task_store: 任务存储模块（提供持久化接口）
            on_event: 可选的实时事件回调，签名为 on_event(event_type: str, data: dict)
        
        Returns:
            {
                "task_id": str | None,
                "result": str,
                "state": "Done" | "Cancelled" | "Blocked"
            }
        """
        ...


class RegimeRegistry:
    """制度注册器 — 单例模式"""
    
    _instance = None
    _registry: Dict[str, type] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def register(cls, regime_id: str):
        """
        制度注册装饰器
        
        用法：
            @RegimeRegistry.register("san_sheng_liu_bu")
            class SanShengLiuBuRegime:
                ...
        """
        def decorator(regime_class):
            cls._registry[regime_id] = regime_class
            return regime_class
        return decorator
    
    @classmethod
    def get(cls, regime_id: str) -> Regime:
        """获取制度实例（单例）"""
        if regime_id not in cls._registry:
            # 动态导入模块
            try:
                importlib.import_module(f"regimes.{regime_id}")
            except ImportError as e:
                raise ImportError(f"无法加载制度模块: regimes.{regime_id}") from e
        
        regime_class = cls._registry.get(regime_id)
        if not regime_class:
            raise KeyError(f"制度未找到: {regime_id}，已注册: {list(cls._registry.keys())}")
        
        # 实例化（一般为单例）
        if not hasattr(regime_class, "_instance"):
            regime_class._instance = regime_class()
        return regime_class._instance
    
    @classmethod
    def list_all(cls) -> List[RegimeMeta]:
        """列出所有已注册的制度元数据"""
        # 先加载所有制度模块
        from regimes import _load_all_regimes
        _load_all_regimes()
        
        metas = []
        for regime_id in cls._registry.keys():
            try:
                regime = cls.get(regime_id)
                metas.append(regime.meta)
            except Exception:
                pass
        return metas
    
    @classmethod
    def get_meta(cls, regime_id: str) -> RegimeMeta:
        """获取指定制度的元数据"""
        regime = cls.get(regime_id)
        return regime.meta
