# CIQ V5 S09 双机型九项完整验收包（2026-10-30）

**请先看：** `docs/S09_九项任务完整验收_正式报告_CN.md`。

## 最终裁定

`S09_FULL_AUDIT_EXECUTED__SCI_FINAL_RELEASE=HOLD`。已执行全 82,620 任务双机型技术匹配、165,933 条假设风/功率压力情景、M1/M2 事件接口和运营碳核算边界防错测试；原始天气、Wingcopter Cargo 配置及两机型任务级功率标定没有达到正式放行要求。

## 核心结果

- 冻结 68 节点、116 条 UAV 候选几何、82,620 订单、4,590 场景；没有修改原件。
- 两机型静态记录 165,240 行。
- DJI 方向一致直接候选+载重初筛 11,060 条；Wingcopter Cargo 冻结 4.7 kg 11,060 中仅 7,377 条载重初筛通过。
- **所有 `real_mission_energy_kwh` 和 `real_operational_CO2e_kg` 故意保持空白**，不能作为正式减排结论。
- 新编译运行后 37 项测试通过，冻结输入 SHA256 验证通过。

## 复现

Windows：双击 `RUN_S09_FULL_AUDIT_WINDOWS.cmd`，需 Python 3.10+，无需第三方包。

Linux/macOS：

```sh
python code/s09_full_validation.py --inputs inputs --outputs outputs
python code/s09_build_quality_tables.py
python -m unittest discover -s tests -p 'test_*.py' -v
```

`outputs/S09_9_WORKPACKAGES_FINAL_ACCEPTANCE_MATRIX.csv` 给出逐项 PASS/HOLD，`qa/S09_FINAL_EVIDENCE_STATUS.json` 给出未通过证据。需要原始气象和型号任务功率资料才可科学升级为最终放行，本包没有也不会虚构这些缺失值。
