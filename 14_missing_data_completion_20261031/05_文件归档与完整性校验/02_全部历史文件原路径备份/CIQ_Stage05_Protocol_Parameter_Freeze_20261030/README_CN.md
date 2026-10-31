# Stage 05 - 统一任务协议、燃油道路基线与双无人机参数来源审计

日期：2026-10-30。状态：MODEL CONTRACT FROZEN / NUMERIC INPUTS HOLD / RUN DENIED。

此包只读使用历史 GitHub commit 4569817b8145efe2ae06f4b21addc1986f971c12 的结果作为证据。没有把历史样本当作新版订单，也没有运行任何模式的新版数值实验。

交付文件：
- `STAGE05_FORMAL_AUDIT_20261030.docx`：中文审计报告。
- `records/source_registry.csv`：权威来源与访问日。
- `records/stage05_parameter_registry.csv`：双机型/燃油/电网参数；`BLOCKED` 的 value 保持空值。
- `records/stage05_unified_task_protocol.json`：不可变统一任务协议、模式定义与核算口径。
- `records/legacy_to_stage05_decision.csv`：旧模型保留/禁止迁移判定。
- `records/stage05_release_gates.csv`：18 项门槛。
- `records/stage05_strict_run_gate_DENY_ALL.json`：默认绝不放行。
- `scripts/stage05_release_check.py`：执行只读验收，不产生仿真。
- `tests/test_stage05_release_check.py`：合成单元测试。

执行：在压缩包解压目录运行 `python scripts/stage05_release_check.py`。输出 JSON 到 `results/stage05_release_result.json`。若缺任何真实输入证据，状态为 HOLD，不允许 M0/M1/M2 计算。

Stage 02 的新 QGIS 空间原件未冻结；完成空间输入与源级核验之后，才可考虑独立可复现的任务级 smoke test。绝不可把模拟许可状态写成真实 CAAM/CAAS 授权。
