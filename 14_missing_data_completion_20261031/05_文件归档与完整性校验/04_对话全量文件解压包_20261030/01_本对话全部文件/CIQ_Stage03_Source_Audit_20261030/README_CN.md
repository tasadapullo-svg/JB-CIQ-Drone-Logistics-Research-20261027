# CIQ Stage 03 — 历史气象 / 交通 / 排放源级预审（仅准备，不重算）

当前结论：`HOLD_RECALC_BLOCKED`。本包并不声称已经取得最新 QGIS 三分区工程，也未下载完整的历史原始 API 文件进行重新计算。

## 已完成的真实工作

- 通过已连接的 GitHub 仓库读取 `final_verification_summary.json` 和 Stage 6 主代码，提取可核对的五个月气象质量元数据及历史参数/逻辑。
- 固定 GitHub 提交 `4569817b8145efe2ae06f4b21addc1986f971c12`，登记两个核心文件的 Git blob SHA-1。
- 编制新版空间、天气、道路与排放输入契约和阻断登记。
- 提供标准库只读审计程序 `scripts/stage03_source_gate.py`，支持对克隆后的真实 GitHub 文件计算 Git blob ID / SHA256，并输出天气原报告质量检查和历史模型模式清单。
- 5 项合成测试通过，当前无输入的实际运行按预期返回 HOLD（退出码 2）。

## 运行方式（Windows PowerShell）

先克隆/更新 GitHub 历史仓库、保留只读副本，并运行 Stage 02 QGIS Console，得到 Stage 02 输出。然后：

```powershell
py -3 scripts\stage03_source_gate.py `
  --weather-summary "D:\CIQ\historical\data\weather_2026\processed\final_verification_summary.json" `
  --legacy-code "D:\CIQ\historical\10_experiment_results\stage6_dual_region_multilevel_feeder\run_stage6.py" `
  --stage02-gate "D:\Users\USERNAME\Documents\CIQ_Stage02_Audit\07_stage02_spatial_gate.json" `
  --out "D:\CIQ_AUDITS\Stage03_source_gate"
```

注意：`07_stage02_spatial_gate.json` 的默认状态总是 `scientific_spatial_input_frozen=false`，所以不会自动解锁数值仿真。即使报告/代码 Git blob 匹配也不意味着完整原始天气、机场空域/场站、燃油或能源模型通过验收。

## 主要文件

- `STAGE03_SOURCE_AUDIT_20261030.md/.docx` — 有来源定位的科学审计报告。
- `records/verified_connector_extract_NOT_RAW_DATA.json` — 远程读取摘要，**不是原始气象时序**。
- `records/model_migration_contract_v1.json` — 新模型输入接口与计算约束。
- `records/legacy_model_remediation_register.csv` — 旧 Stage 6 模型问题登记。
- `records/stage03_handoff_gates.csv` — 后续审核门槛。
- `scripts/stage03_source_gate.py` — 本地只读源文件哈希及元数据核查。
- `tests/test_stage03_source_gate.py` — 测试。
- `output/current_workspace/` — 真实当前工作区执行的 HOLD 证据。

**无数据的状态是 HOLD，不是零雨、零排放或通过。**
