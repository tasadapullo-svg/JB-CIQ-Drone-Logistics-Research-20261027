# V2_S11 — 运营碳排放—成本与最小碳优化 / Carbon-cost-service optimization

- 状态：**HOLD / PLANNED**。本阶段未运行任何正式数值实验。
- 论文对应：RQ3。
- 历史来源只读提交：`4569817b8145efe2ae06f4b21addc1986f971c12`，绝不覆盖旧 Stage 3–8。
- 目前阻断：依赖 V2-S08~10 已批准的原始车辆/航次账本。

## 1. 执行步骤（不得跳过）
1. 定义主口径：燃油车辆 TTW CO2 + 充电电力 location-based CO2，单位一致；CO2e 仅在覆盖 CH4/N2O/口径统一后计算
2. 按充电地分别应用 MY/SG 电网因子；车队燃油、怠速、无人机充电、转运及共享行程均纳入
3. 统一输出按总输入订单、完成订单、共同服务队列、真实车次四种分母，禁止只挑 UAV 成功订单
4. 设定服务不能下降、按时率与成本上限为约束；成本容忍度设为显式情景且不强行推出有减排方案
5. 逐种子寻找满足约束的最低碳 M1/M2/混合配比，若不存在则如实输出 infeasible

## 2. 输入数据和证据

| 输入文件 | 格式 | 要求 |
|---|---|---|
| `trip_ledger.csv` | CSV | 唯一燃油车/无人机/充电车次原始活动量 |
| `order_mode_results.csv` | CSV | 可评价的同订单模式结果 |
| `emission_factor_register.csv` | CSV | 燃料及电力因子、气体、国家、年份和不确定性 |
| `cost_parameter_register.csv` | CSV | 成本参数 MYR、证据和区间 |
| `optimization_constraints.json` | JSON | 服务/准时/成本约束和情景 |

填写 `INPUT_REGISTER.csv` 的实际源路径/校验信息，放入本阶段 `inputs/`。数据模板仅含列名，不得当实际数据使用。

## 3. 预期产物
- `operational_carbon_ledger.csv`：燃油与电力独立碳账本
- `matched_comparison.csv`：服务匹配时间/成本/碳变化
- `pareto_feasible.csv`：可行 Pareto 情景/不可行原因
- `emission_QA.json`：单位和跨模式共享车次复算

## 4. 放行检查
- [ ] CO2 与 CO2e 口径不可混用
- [ ] MY/SG 供电按真实地点分账
- [ ] 排放相同物理车次不重复计
- [ ] 低碳结论必须满足已冻结的服务与成本约束
- [ ] 成本/能耗/排放因子缺失禁止输出净减排

## 5. 独立验收方法

项目根目录执行：

```bash
python tools/verify_stage.py --root . --stage V2_S11
python tools/generate_sha256_manifest.py --directory STAGES/V2_S11 --output STAGES/V2_S11/SHA256_MANIFEST.csv
```

自动检查仅代表输入文件**结构有效**。`QA_GATES.csv` 里的 BLOCKED 不会被自动变成真实科学验收 PASS。

## 6. 上传 GitHub

将本阶段目录连同 `tools/`、`protocol/`、`references/` 上传至：`11_v2_carbon_first_experiments/V2_S11/`（建议新目录）；**不要覆盖**旧 `10_experiment_results/` 归档。

**论文声明边界：** 依赖 V2-S08~10 已批准的原始车辆/航次账本。
