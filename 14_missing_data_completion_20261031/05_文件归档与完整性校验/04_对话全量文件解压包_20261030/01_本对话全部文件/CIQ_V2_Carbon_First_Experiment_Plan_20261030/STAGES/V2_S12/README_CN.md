# V2_S12 — 统计、敏感性与 SCI 图表定稿 / Uncertainty, figures & independent replication

- 状态：**HOLD / PLANNED**。本阶段未运行任何正式数值实验。
- 论文对应：RQ1,RQ2,RQ3。
- 历史来源只读提交：`4569817b8145efe2ae06f4b21addc1986f971c12`，绝不覆盖旧 Stage 3–8。
- 目前阻断：等待前序阶段正式数值结果；当前只可冻结统计方案。

## 1. 执行步骤（不得跳过）
1. 以30个独立随机种子为主要重采样单位，不把89,526模式记录当独立样本
2. 按区域、车型、时段、天气、成本约束分层报告平均差异及区间，分母解释透明
3. 进行油耗、任务功率、返航备用、天气限制、地面拥堵、充电国别及跨境排队的联合敏感性
4. 绘制 Fig.3 模型/空间、Fig.4 道路气象、Fig.5 服务、Fig.6 碳成本、Fig.7 Pareto/不确定性，全部从机器可读结果直接产生
5. 独立复跑、代码和所有输入 SHA256、原始/生成数据版本冻结，整理 Results、Discussion、Limitations

## 2. 输入数据和证据

| 输入文件 | 格式 | 要求 |
|---|---|---|
| `paired_run_results.csv` | CSV | 按seed/date/zone/vehicle/uav/mode的完整账本汇总 |
| `uncertainty_draws.csv` | CSV | 有来源的联合参数不确定性抽样 |
| `release_qa.json` | JSON | 所有前序阶段签核和版本 |
| `figure_data.csv` | CSV | 每个子图真实数据源表 |

填写 `INPUT_REGISTER.csv` 的实际源路径/校验信息，放入本阶段 `inputs/`。数据模板仅含列名，不得当实际数据使用。

## 3. 预期产物
- `rq1_rq2_rq3_summary.csv`：论文三问逐条量化结果
- `sensitivity_summary.csv`：风雨/拥堵/油耗/能耗/成本边界
- `figures/`：Fig.3–Fig.7正式科研图
- `replication_report.md`：可重复执行日志和引用/限制

## 4. 放行检查
- [ ] 不将订单行数当独立样本数
- [ ] 不发表未授权飞行/实际净减排的断言
- [ ] 所有图表数值与输出CSV一致
- [ ] 最后一个seed每项计算可重放
- [ ] 公开汇总无密钥、无隐私、来源许可检查通过

## 5. 独立验收方法

项目根目录执行：

```bash
python tools/verify_stage.py --root . --stage V2_S12
python tools/generate_sha256_manifest.py --directory STAGES/V2_S12 --output STAGES/V2_S12/SHA256_MANIFEST.csv
```

自动检查仅代表输入文件**结构有效**。`QA_GATES.csv` 里的 BLOCKED 不会被自动变成真实科学验收 PASS。

## 6. 上传 GitHub

将本阶段目录连同 `tools/`、`protocol/`、`references/` 上传至：`11_v2_carbon_first_experiments/V2_S12/`（建议新目录）；**不要覆盖**旧 `10_experiment_results/` 归档。

**论文声明边界：** 等待前序阶段正式数值结果；当前只可冻结统计方案。
