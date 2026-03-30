"""
三省六部制 — 可插拔制度模块
将现有代码迁移为标准制度模块格式
"""
from regimes.san_sheng_liu_bu.regime import SanShengLiuBuRegime
from framework.core import RegimeRegistry

# 注册制度
RegimeRegistry.register("san_sheng_liu_bu")(SanShengLiuBuRegime)
