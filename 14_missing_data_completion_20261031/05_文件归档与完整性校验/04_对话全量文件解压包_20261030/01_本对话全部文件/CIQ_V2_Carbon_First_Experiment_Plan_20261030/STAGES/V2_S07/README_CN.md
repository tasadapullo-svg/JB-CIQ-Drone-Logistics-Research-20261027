# V2_S07 — 任务—气象—交通同口径冻结 / Paired tasks & time-aligned weather/road

- 状态：**HOLD / PLANNED**。本阶段未运行任何正式数值实验。
- 论文对应：RQ1,RQ2。
- 历史来源只读提交：`4569817b8145efe2ae06f4b21addc1986f971c12`，绝不覆盖旧 Stage 3–8。
- 目前阻断：有历史天气/订单资料，但新空间任务映射及跨境 OD 未冻结。

## 1. 执行步骤（不得跳过）
1. 只选一种冻结合成需求总体（可优先沿用 Stage6 的29,842订单，经新空间映射后重新审定）
2. 为所有 M0/M1/M2 保留同一 task_id、seed、载重、时间戳、目的地与期限
3. 用有向 OSM OD 路径匹配交通小时；37 条旧异常仅作为候选、未经复核不得自动修复
4. 天气按计划起飞/飞行小时读取；验证降雨变量、单位、时区、ERA5 网格重复和 NEA 缺口
5. 跨境 OD 另建任务群；无真实等待数据时显式给出情景区间而非实测值

## 2. 输入数据和证据

| 输入文件 | 格式 | 要求 |
|---|---|---|
| `frozen_tasks.csv` | CSV | 不可变任务样本与任务总体ID |
| `road_od_hourly.csv` | CSV | 方向级道路 OD/小时代理与证据状态 |
| `weather_hourly.csv` | CSV | 降雨、风向/风速、时区、站点或网格来源 |
| `cross_border_wait.csv` | CSV | 国境等候实测/情景分离 |

填写 `INPUT_REGISTER.csv` 的实际源路径/校验信息，放入本阶段 `inputs/`。数据模板仅含列名，不得当实际数据使用。

## 3. 预期产物
- `paired_task_manifest.csv`：任务总体与种子/日期哈希
- `time_join_QA.csv`：天气道路时间戳覆盖及缺测
- `road_access_repair_log.csv`：可达性候选/实际修复逐条追踪
- `demand_freeze.json`：可评价分母及排除理由

## 4. 放行检查
- [ ] 同一 task_id 在各模式只定义一次
- [ ] 无跨日期或不同订单总体混合
- [ ] 未验证 37 OD 不视为 PASS
- [ ] 无法计算的数值为缺失而非 0
- [ ] 每条跨境任务有实际国家对及排队证据类型

## 5. 独立验收方法

项目根目录执行：

```bash
python tools/verify_stage.py --root . --stage V2_S07
python tools/generate_sha256_manifest.py --directory STAGES/V2_S07 --output STAGES/V2_S07/SHA256_MANIFEST.csv
```

自动检查仅代表输入文件**结构有效**。`QA_GATES.csv` 里的 BLOCKED 不会被自动变成真实科学验收 PASS。

## 6. 上传 GitHub

将本阶段目录连同 `tools/`、`protocol/`、`references/` 上传至：`11_v2_carbon_first_experiments/V2_S07/`（建议新目录）；**不要覆盖**旧 `10_experiment_results/` 归档。

**论文声明边界：** 有历史天气/订单资料，但新空间任务映射及跨境 OD 未冻结。
