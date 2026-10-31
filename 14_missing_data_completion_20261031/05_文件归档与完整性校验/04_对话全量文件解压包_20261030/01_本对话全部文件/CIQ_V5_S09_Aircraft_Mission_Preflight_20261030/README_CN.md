# CIQ V5-S09：冻结任务技术筛查与事件级无人机能耗计算框架

**2026-10-30 · 实际运行完成的条件性筛查，不是最终碳减排结果。**

## 冻结输入
- V5 `V5_FROZEN_SOURCE.zip` 原样只读；68 个活动节点、116 条 UAV 候选几何线。源数据中其它 5+4 条地面参考线不参与飞行边筛选。
- 2026-05 至 09 月 82,620 条合成订单，30 个随机种子；共同研究分母不删减。
- Wingcopter 198 Cargo 有效载重 4.7 kg；DJI FlyCart 30 双电池模式 30 kg。厂商规格不是逐任务标定。

## 已实际运行
- 逐单输出 `outputs/S09_V5_ALL_TASKS_OEM_PAYLOAD_AND_DIRECT_EDGE_SCREEN.csv`：载重、是否直接匹配 V5 候选边、可识别的几何距离、**非实测**的 DJI 测试距离组合代理、Wingcopter 92 km 最大航程上界。
- 逐边输出 `outputs/S09_V5_116_EDGE_OEM_DISTANCE_BOUNDARY_SCREEN.csv`：DJI 在显式假设下的几何代理与储备阈值。`25%` 是分析假设，不是厂家要求。不得作为飞行适航许可或任务实测能耗。
- 可复算 S09 悬停/巡航能耗和电网充电量的**参数化数学核心** `mission_energy_core.py`：未提供真实功率和实际起飞时天气时不得进入正式结果。
- 气象接口 `weather_event_contract.py`：要求 UTC 时段、实测/经核验来源以及覆盖整个飞行事件的小时数据；不得把订单释放时刻天气固定用于全航程。
- `qa/S07_S09_CURRENT_SOURCE_RELEASE_GATE.json`：原始天气和道路字节的严格放行。

## 运行
```bash
python code/build_s09_preflight.py --root .
python code/check_s07_sources.py --root .
python -m unittest discover -s tests -v
```
Windows 可直接使用 `RUN_WINDOWS.cmd`，联网补数据可先执行 `RUN_WINDOWS_RECOVER_S07.cmd`；该脚本不会自动批准道路入口或空域许可。

## 科学结论界线
1. 无直接候选几何连接 ≠ 不可完成配送；可由汽油车或多段接驳完成。
2. 逆向边 ≠ 已准许返程；必须审查实际路线与法规。
3. DJI 公开的满载/空载最大航程测试不能直接组合为经实测的电量模型。本文输出距离比例仅用于预筛查与敏感性情景。
4. Wingcopter 92 km 为公布的最大航程，**不是证明 4.7 kg 满载 92 km**；厂商网页未提供足够的任务级 kWh 模型。本站点条件下无法给出真实 Wingcopter/FC30 的碳排放排名。
5. 所有站点和空域证据仍为条件性研究，不代表已获运营许可。

## 研究剩余工作
- S07：五个月原始天气数值、全 A/B/C 有向路网、FCD、节点接入、订单情景标定；**HOLD**。
- S08：汽车多订单驾驶路线、汽油参数、共享车次排放；**方法已测试，正式结果 HOLD**。
- S09：真实机型能耗参数与天气事件验证；**载重/几何预筛查完成，真实能耗 HOLD**。
- S10：M0/M1/M2 五模式共享订单、车辆与无人机调度；**HOLD**。
- S11：同一排放边界下最低碳可行解与时间/成本约束；**HOLD**。
- S12：不确定性、独立复现和 SCI 图表；**HOLD**。

## 数据来源
- DJI: https://www.dji.com/flycart-30/specs
- Wingcopter Cargo: https://wsd.wingcopter.com/w198-cargo
- 固定 GitHub 提交 `4569817b8145efe2ae06f4b21addc1986f971c12`（历史源文件索引；不替换 V5）。
