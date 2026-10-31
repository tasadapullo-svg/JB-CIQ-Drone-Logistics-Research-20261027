# V2_S08 — 汽油车纯道路 M0 基线 / Gasoline-car M0 benchmark

- 状态：**HOLD / PLANNED**。本阶段未运行任何正式数值实验。
- 论文对应：RQ2,RQ3。
- 历史来源只读提交：`4569817b8145efe2ae06f4b21addc1986f971c12`，绝不覆盖旧 Stage 3–8。
- 目前阻断：燃油车具体车型及油耗校准仍待冻结。

## 1. 执行步骤（不得跳过）
1. 以汽油配送车辆为主基线；柴油可作敏感性，不以旧电动车 M0 替代
2. 冻结车型、车辆质量/容量、载荷、城市/高速油耗、燃油排放因子、价格及来源版本
3. 统一包括去程、返程、整车共享里程、怠速、排队、站点作业及运营人员时长
4. 路网和车速驱动里程/时间，独立于机型；缺油耗实测时设置文献校准区间并标注情景
5. 核验车辆/旅行单位: L/100km、L/h、MYR/L、kg CO2/L，按燃油体积和类型分项

## 2. 输入数据和证据

| 输入文件 | 格式 | 要求 |
|---|---|---|
| `vehicle_registry.csv` | CSV | 汽油车型/容量/服务配置及证据 |
| `fuel_parameters.csv` | CSV | 油耗/怠速/油品密度/热值/因子可追溯参数 |
| `road_trips_m0.csv` | CSV | 基线去返程、共享路程、车次事件及证据 |
| `fuel_costs.csv` | CSV | 燃油价格和非燃油成本数据源 |

填写 `INPUT_REGISTER.csv` 的实际源路径/校验信息，放入本阶段 `inputs/`。数据模板仅含列名，不得当实际数据使用。

## 3. 预期产物
- `m0_trip_ledger.csv`：车次级油耗及 TTW CO2 台账
- `m0_order_results.csv`：逐任务时间/完成/按时/费用与分摊
- `m0_QA.json`：单位、路程、队列和误差检查
- `m0_baseline_freeze.json`：M0 定义及哈希

## 4. 放行检查
- [ ] 以汽油车为 M0 且车辆类型明确
- [ ] 油耗、怠速、燃油 CO2 因子具有出处/不确定性
- [ ] 所有去返程和共享路程不重复计数
- [ ] M0 与后续 M1/M2 使用同一任务与车队公平性协议
- [ ] 不能把旧电动车 kgCO2e 当汽油 CO2

## 5. 独立验收方法

项目根目录执行：

```bash
python tools/verify_stage.py --root . --stage V2_S08
python tools/generate_sha256_manifest.py --directory STAGES/V2_S08 --output STAGES/V2_S08/SHA256_MANIFEST.csv
```

自动检查仅代表输入文件**结构有效**。`QA_GATES.csv` 里的 BLOCKED 不会被自动变成真实科学验收 PASS。

## 6. 上传 GitHub

将本阶段目录连同 `tools/`、`protocol/`、`references/` 上传至：`11_v2_carbon_first_experiments/V2_S08/`（建议新目录）；**不要覆盖**旧 `10_experiment_results/` 归档。

**论文声明边界：** 燃油车具体车型及油耗校准仍待冻结。
