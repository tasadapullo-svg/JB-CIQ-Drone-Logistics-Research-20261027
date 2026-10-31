# V2_S10 — M1/M2 混合物流统一仿真 / Road–air multimodal dispatch

- 状态：**HOLD / PLANNED**。本阶段未运行任何正式数值实验。
- 论文对应：RQ2,RQ3。
- 历史来源只读提交：`4569817b8145efe2ae06f4b21addc1986f971c12`，绝不覆盖旧 Stage 3–8。
- 目前阻断：依赖 V2-S06~09 数据及标定；不允许提前运行。

## 1. 执行步骤（不得跳过）
1. 运行 M0、M1 固定站点/转运、M2 车辆—无人机同步会合；两机型各独立情景
2. 同订单总体、同车辆类型/资源配置规则、天气样本与道路基线；固定随机数种子
3. 精确追踪转运、排队、充电、更换电池、往返、车辆回收与无人机失败后的地面回退
4. 按物理行程 ID 计车次；共享批量运输只记一次总行程再分摊；任务不因无人机失败而从分母删除
5. 先同日小样本逐事件审计，再运行冻结的30种子×5日期；跨境另设可溯源分层

## 2. 输入数据和证据

| 输入文件 | 格式 | 要求 |
|---|---|---|
| `dispatch_config.json` | JSON | 车辆/无人机/服务资源及策略 |
| `paired_tasks.csv` | CSV | 完全相同的任务输入和样本标识 |
| `road_trip_library.csv` | CSV | 可用道路行程与小时条件 |
| `uav_mission_library.csv` | CSV | 可用航次与机型能耗证据 |

填写 `INPUT_REGISTER.csv` 的实际源路径/校验信息，放入本阶段 `inputs/`。数据模板仅含列名，不得当实际数据使用。

## 3. 预期产物
- `event_log.csv`：逐事件日志：等待、装卸、起飞、回收、兜底
- `trip_ledger.csv`：唯一物理车辆/航次/共享干线行程
- `order_mode_results.csv`：M0/M1/M2逐任务完成、按时、费用分项
- `dispatch_QA.json`：同订单/容量/时间/服务公平性检查

## 4. 放行检查
- [ ] 每个 task × scenario × mode 一条最终结局
- [ ] 物理车次/航次 ID 唯一且共享里程只计一次
- [ ] 天气禁飞回退时仍保留任务且有真实耗时
- [ ] 同等需求及明确车队资源约束
- [ ] 小样本已验收且30种子运行可复现

## 5. 独立验收方法

项目根目录执行：

```bash
python tools/verify_stage.py --root . --stage V2_S10
python tools/generate_sha256_manifest.py --directory STAGES/V2_S10 --output STAGES/V2_S10/SHA256_MANIFEST.csv
```

自动检查仅代表输入文件**结构有效**。`QA_GATES.csv` 里的 BLOCKED 不会被自动变成真实科学验收 PASS。

## 6. 上传 GitHub

将本阶段目录连同 `tools/`、`protocol/`、`references/` 上传至：`11_v2_carbon_first_experiments/V2_S10/`（建议新目录）；**不要覆盖**旧 `10_experiment_results/` 归档。

**论文声明边界：** 依赖 V2-S06~09 数据及标定；不允许提前运行。
