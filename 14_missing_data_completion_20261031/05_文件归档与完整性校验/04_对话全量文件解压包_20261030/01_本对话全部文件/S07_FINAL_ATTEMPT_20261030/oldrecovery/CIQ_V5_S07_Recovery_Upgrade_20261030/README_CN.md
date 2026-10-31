# CIQ V5 — S07 原件恢复与门禁修订工程

**这不是已经完成道路-天气-订单联合计算的结果包。** 包内保留冻结 V5 68 点表、82,620 条合成任务和 4,590 个种子日场景索引，外加可重复执行的恢复程序与实际 HOLD 记录。

## Windows 使用
- 如果 GitHub 仓库已完整克隆：命令行执行 `RUN_S07_WINDOWS.cmd "C:\\Users\\...\\JB-CIQ-Drone-Logistics-Research-20261027"`。
- 如果没有完整本地仓库但能够联网：双击 `RUN_S07_WINDOWS.cmd`，程序按 `4569817b8145efe2ae06f4b21addc1986f971c12` 固定 commit 下载 14 份数据。
- 如果需要新三分区 A/B/C 道路候选图：运行 `RUN_S07_C_ROAD_WINDOWS.cmd`。此程序依赖在线 OSMnx/Overpass，**道路图只是可建模候选，不是合法进出场地证明**。
- 检查 `qa/source_byte_gate.csv`、`qa/source_basic_numeric_audit.json`、`qa/S07_RELEASE_GATE.json`。

## 输出规范
`PASS_BYTES_HASH` = 完整原始字节及版本匹配；不能解释成「交通和天气科学验收合格」。仍需风雨单位、时刻区间、路网方向、站点道路接入及 C 区覆盖审查。

## 注意
不修改 V5 GIS，不重建原始合成订单，不覆盖历史 Stage 3–8，不生成未经核算的 M0/M1/M2 CO2e。
