# S08 汽油车 M0 条件性基线

本目录保存4,590场景、82,620订单的条件性汽油车M0运行结果。模型使用S07当前OSM有向路径和无方向FCD速度代理；它不是实测企业车队结果。

- `code/run_s08_petrol_m0.py`：时间依赖多车、多订单取送、容量、期限、服务和返仓模型。
- `data/S08_ORDER_RESULTS*`：每个冻结订单唯一结果。
- `data/S08_SCENARIO_SUMMARY.csv`：4,590场景汇总。
- `data/S08_PHYSICAL_LEG_LEDGER.parquet`：物理车程只记一次，防止共享车程按订单重复计油耗。
- `data/S08_VEHICLE_EVENT_LOG.parquet`、`S08_VEHICLE_TRIPS.parquet`：车辆事件与行程。
- `PARAMETER_SOURCE_MATRIX.csv`：官方/文献参数与情景假设分级。
- `data/S08_PARAMETER_SENSITIVITY.csv`、`S08_VEHICLE_RESOURCE_SENSITIVITY_306_SCENARIOS.csv`：燃耗、价格、人工和车辆资源敏感性。
- `data/S08_SMALL_EXACT_ALGORITHM_VALIDATION.csv`：三订单小规模精确枚举对照。

排放主账本是汽油燃烧 `TTW CO₂`，不是WTW/LCA，也不冒充完整非CO₂温室气体CO₂e。

运行：PowerShell执行 `./RUN_REPRODUCE.ps1`。
