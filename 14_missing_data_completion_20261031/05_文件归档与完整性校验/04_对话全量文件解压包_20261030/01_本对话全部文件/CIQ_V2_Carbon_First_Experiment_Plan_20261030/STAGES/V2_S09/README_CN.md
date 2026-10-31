# V2_S09 — 双无人机能耗—天气—航路审计 / DJI and Wingcopter energy & eligibility

- 状态：**HOLD / PLANNED**。本阶段未运行任何正式数值实验。
- 论文对应：RQ1,RQ2,RQ3。
- 历史来源只读提交：`4569817b8145efe2ae06f4b21addc1986f971c12`，绝不覆盖旧 Stage 3–8。
- 目前阻断：官方规格已核实，但完整任务能耗参数尚未冻结。

## 1. 执行步骤（不得跳过）
1. 明确两机型: DJI FlyCart 30 双电池货箱和 Wingcopter 198 Cargo，型号版本不得混用
2. 区分官方标称载重/航程与实际任务可用能量；禁止用最大航程反推 kWh/km
3. 建载荷—飞行阶段（起降/巡航/悬停/返航）—风场—备用电量—充电效率模型
4. 分别审查雨量/阵风/高度/禁航条件、空域时效、航线长度与合法性；不将许可未知说成获批
5. 必须冻结可信任务能耗区间及来源；不足时仅输出几何上界和敏感性，阻止碳效益排名

## 2. 输入数据和证据

| 输入文件 | 格式 | 要求 |
|---|---|---|
| `uav_models.csv` | CSV | 型号、官方规格、证据与适用工况 |
| `uav_energy_parameters.csv` | CSV | 功耗/能量/储备/充电参数和区间来源 |
| `uav_candidate_missions.csv` | CSV | 载荷/路径/航时/天气与空间筛查 |
| `regulatory_scenarios.csv` | CSV | 批准/禁飞/待审批/仅模拟四类情景 |

填写 `INPUT_REGISTER.csv` 的实际源路径/校验信息，放入本阶段 `inputs/`。数据模板仅含列名，不得当实际数据使用。

## 3. 预期产物
- `uav_mission_energy.csv`：两机型逐航次电耗范围
- `uav_weather_restrictions.csv`：可飞性和天气回退原因
- `airspace_scenario_QA.csv`：限制与科研情景分开
- `uav_energy_freeze.json`：任务模型与假设的版本锁定

## 4. 放行检查
- [ ] 两机型分别识别且不能用470 W旧泛化模型
- [ ] 任务能耗包含带载/空载/起降/返航/充电损失
- [ ] 每条任务天气基于实际起飞/返航时刻
- [ ] 空域状态明确标记、未授权不能称可部署
- [ ] 能耗缺口未闭合则阻止定量减排排序

## 5. 独立验收方法

项目根目录执行：

```bash
python tools/verify_stage.py --root . --stage V2_S09
python tools/generate_sha256_manifest.py --directory STAGES/V2_S09 --output STAGES/V2_S09/SHA256_MANIFEST.csv
```

自动检查仅代表输入文件**结构有效**。`QA_GATES.csv` 里的 BLOCKED 不会被自动变成真实科学验收 PASS。

## 6. 上传 GitHub

将本阶段目录连同 `tools/`、`protocol/`、`references/` 上传至：`11_v2_carbon_first_experiments/V2_S09/`（建议新目录）；**不要覆盖**旧 `10_experiment_results/` 归档。

**论文声明边界：** 官方规格已核实，但完整任务能耗参数尚未冻结。
