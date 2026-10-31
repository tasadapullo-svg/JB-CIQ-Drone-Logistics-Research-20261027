# V2-S07 R2 — 五个月天气与有向道路源文件恢复工程（2026-10-30）

本项目只读使用固定 GitHub 历史提交 `4569817b8145efe2ae06f4b21addc1986f971c12`。包含 S06 冻结空间输入、S07 已实测的 69 节点 / 3,672 小时时间索引和 19 点跨版本坐标对照，并提供真正尝试运行后的源文件恢复日志。

## 当前实际执行裁定

- 原始 V3 GIS 数据：此前验收通过，本包原样携带。
- 11 份关键 GitHub 源文件：已定位路径与 Git blob，含五个月 XLSX 的当前版本 SHA-256，但本执行环境 DNS 不可用，**11/11 未获得原始字节**。
- 五个月天气 XLSX：当前版本与每月独立 manifest 记录的字节数相符；与旧 `final_verification_summary.json` 记录的文件字节数不一致。须优先相信同一版本的 manifest，下载后才可进行实际 SHA-256 复核。
- 节点：69/69 保留。旧有向道路图 A/B 仍需要字节文件；C/PORT_A/GATEWAY 不会因缺网络被删除。
- 气象数值：尚未取回原件，本轮未创建新的实际数值时间序列。无输入时输出 HOLD，不填零值。
- 道路：目前不能计算新的燃油车可行驶距离，不把旧直线/有向路网结果自动当作新版完整路由。
- 历史 37 条异常 OD：继续留在原异常表中，不自动应用修复。
- 正式模拟：M0/M1/M2、时间、成本、碳排放重算均未启动。

## Windows 一键执行

解压整个包，使用 **Windows 10/11、Python 3.9+、有互联网的环境**，双击 `RUN_WINDOWS.cmd`。脚本执行后在 `recovered_sources` 下保存原件，以固定 GitHub 提交校验大小、Git blob SHA1；五个月 XLSX 还需校验与当前月 manifest 一致的 SHA-256，并对 XLSX 解压结构做 CRC 检查。

结果位于 `qa/actual_source_recovery_status.csv`、`qa/S07_R2_release_record.json`、`outputs/`。校验失败的原件不会被批准。源文件已经存在时可不联网，运行：

```powershell
py -3 code\recover_pinned_sources.py --index inputs\PINNED_SOURCE_INDEX.json --sources recovered_sources --out qa
py -3 code\read_weather_workbooks.py --index inputs\PINNED_SOURCE_INDEX.json --sources recovered_sources --out outputs --sheet Weather_Hourly
py -3 code\audit_legacy_road_graph.py --sources recovered_sources --nodes inputs\S06_69_node_master.csv --out outputs
py -3 code\join_verified_era5_to_nodes.py --source recovered_sources\E03_ERA5_JB_TWO_CIQ_WEATHER_HOURLY.csv --assignment inputs\S07_05_node_to_weather_grid_69_CANDIDATES_ONLY.csv --timeline inputs\S07_03_hourly_timeline_3672.csv --out outputs
py -3 code\s07_release_gate.py --root .
```

## 限制与下一步

当前天气关联仅对应历史 ERA5 **两个返回网格**，不代表 69 处有独立天气站记录；S10 应根据模拟起飞时刻按区间查询天气，降雨单位与有效时间仍需审计。旧 A/B 路网边表只用于核验历史有向拓扑和**道路最近节点候选**，并不能代替新 C 区道路数据、合法交叉口转向/道路进入性、跨境通关或货运车路由。

原 29,842 订单的 `stage6_order_level.csv.gz` 存储模式级记录（89,526 行），若恢复后用于复核原合成任务，必须仅从 M0 行按原订单 ID 读取，不允许将三模式行重复计作三批订单；旧 A 区 ID 已迁移，不能自动继承新的 A 节点。要正式冻结新三分区需求总体，应另行通过地理需求依据与合成生成器验证。

全部原始历史文件均只读，不覆盖旧 Stage 3–8。
