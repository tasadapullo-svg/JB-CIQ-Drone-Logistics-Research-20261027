# Stage 04：道路与气象历史证据独立结构复核

## 本轮成果与适用边界

这次从 GitHub **实际读取历史诊断 CSV 的全部 128 条 OD 和 37 条修复日志**，复核过分类和 `repair_applied`，并读取历史天气 QC JSON 的五个月度元数据。计算结果参见 `records/STAGE04_connector_verified_evidence.json`。

未取得当前三分区 QGIS 工程；未独立重算原始逐小时天气、道路驾驶时间、燃油消耗或运营碳排放。本包任何状态都不得解释为主实验已释放。

## 核查结论

- 128 参考 OD：A=56、B=72，原始有路 91、异常 37。
- 37 异常诊断候选路径均可找到（A：7 个吸附/方向缺口；B：30 个道路入口数据缺口），但 `repair_applied=False`（37/37）。因此正式修复数为 **0**。
- 旧研究所含 `cross_border_route=True` 条数为 **0**；不要用旧道路集合宣称跨国运输绩效。
- 历史四点气象实际匹配 **2** 个 ERA5 返回网格；三个点共享同一格点。不要把四个点当四个独立的 ERA5 观测站。
- NEA 核心数据 5 月 PARTIAL、6–9 月 NOT_REQUESTED，官方再分析/模型产品仍不能冒充站点观测。

## 使用脚本

仅用 Python 标准库。读取本地完整历史文件执行：

```powershell
python scripts/stage04_evidence_gate.py `
  --od "D:\CIQ\outputs\stage2_20261027\od_connectivity_diagnostics.csv" `
  --repairs "D:\CIQ\outputs\stage2_20261027\od_route_repair_log.csv" `
  --weather-qc "D:\CIQ\data\weather_2026\processed\final_verification_summary.json" `
  --stage02-gate "D:\CIQ\CIQ_Stage02_Audit\07_stage02_spatial_gate.json" `
  --output "D:\CIQ\audit\stage04_road_weather_evidence_gate.json"
```

程序为只读审计，无条件返回 `HOLD_RECALC_BLOCKED`，退出码 `2` 表示**阻断数值计算**；不是脚本崩溃。可继续对代码/元数据审查，但不可跳过真实 QGIS 输入签批。`scripts/build_verified_records.py` 仅物化本轮人工复核过的 GitHub 连接结果登记，不替代从原始 CSV 重跑。

测试：`python -m unittest discover -s tests -v`，七项合成测试已运行通过。

## 本轮交付

- `STAGE04_FORMAL_AUDIT_20261030.docx` 与 `.md` — 正式报告
- `records/verified_historical_37_unapplied_OD_exceptions.csv` — **历史真实异常 ID 的复核登记**，不是合法可用路径
- `records/verified_historical_weather_grid_and_QC.csv` — 五个月已有天气质量元数据与返回网格重复性
- `records/STAGE04_connector_verified_evidence.json` — 已验证来源与结论
- `scripts/stage04_evidence_gate.py` — 用户本地完整文件核验工具
- `tests/test_stage04_evidence_gate.py` — 防止错误释放的测试
- `output/actual_workspace_audit.json` — 无原件情况下真实执行的阻断结果

## 下一阶段实际开始条件

三分区 QGIS QGS/QGZ 与全部依赖图层完成冻结；正式道路有向 OD 重新建立；天气原始逐小时数据与四点/节点暴露进行独立复核；两款 UAV 能耗和道路燃油参数来源完成冻结。补上后再进入 matched-task M0/M1/M2 实验，不能把旧 37 诊断候选路线视为已修复。
