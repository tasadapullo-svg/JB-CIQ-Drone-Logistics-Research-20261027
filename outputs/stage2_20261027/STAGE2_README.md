# CIQ Stage 2交付说明

生成日期：2026-10-27（Asia/Shanghai）

## 执行范围

本包完成冻结证据链复核、128个有向OD逐条诊断、道路/CIQ分层、外部证据可匹配性核查，以及同一批既有订单的三模式诊断门槛测试。没有生成新订单，没有覆盖原始文件，没有启动918,000行正式三模式实验。

## 执行命令

```powershell
py outputs/stage2_20261027/scripts/run_stage2.py
py outputs/stage2_20261027/tests/test_stage2.py
py outputs/stage2_20261027/scripts/package_stage2.py
```

## 环境

`{"python": "3.14.3", "pandas": "2.3.3", "numpy": "2.5.0", "networkx": "3.6.1", "platform": "Windows-10-10.0.19045-SP0"}`

## 样本规模

- 订单冻结快照：30 seeds / 918,000 rows（只读审计）。
- 道路诊断：128个有向参考OD，其中37个原异常。
- 24小时道路检查：3072行。
- 三模式门槛样本：8个现有订单，24行。

## 解释限制

`smoke_order_results.parquet` 全部标记为 `NOT_EVALUABLE`，仅证明相同订单在M0/M1/M2均被保留及缺口被显式编码。它不是运营仿真结果，不支持RQ1–RQ3正式推断。
