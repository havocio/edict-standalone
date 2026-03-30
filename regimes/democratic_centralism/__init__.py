"""
民主集中制 — 可插拔制度模块
流程：秘书处分拣 → 议会讨论投票 → 常务委员会集中决策 → 执行部委 → 监察部审计
"""
from regimes.democratic_centralism.regime import DemocraticCentralismRegime
from framework.core import RegimeRegistry

RegimeRegistry.register("democratic_centralism")(DemocraticCentralismRegime)
