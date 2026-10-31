# CIQ 无人机物流 SCI 研究 | Stage 00–01 第二轮审计与空间迁移关口报告

**文件号：** CIQ-S00S01-R2-20261030  
**审计日期：** 2026-10-30（Asia/Kuala_Lumpur）  
**冻结候选：** 最新 QGIS 三分区工程（尚未取得可解析原件）  
**历史基线：** `tasadapullo-svg/JB-CIQ-Drone-Logistics-Research-20261027`，`main`，提交 `4569817b8145efe2ae06f4b21addc1986f971c12`  
**结论：** **HOLD / NOT APPROVED**；天气、道路、运营碳排放重算：**NOT EXECUTED**

> 本报告记录本轮确已执行的连接器复核、模型谱系隔离与软件预检。历史仓库包含超过两万文件的完整性结论仍来自历史仓库自身的打包报告，并未由本轮逐件重新哈希。当前容器没有用户最新 QGIS 三分区原件；下述节点数据不得解释为对真实新网络的发现。

## 1. 审计增量和现时版本判断

- 本轮再次查询了 GitHub 主仓库及近期提交：连接器返回的最新可确认提交仍为 2026-10-28 的 `4569817b...`。**没有依据宣布 10 月 29 日修订的三分区 QGIS 文件已进入此历史提交**。
- 本地检查此前 Stage 00/01 R1 的成果文件与审计程序，确认它们在当前运行容器可用；检查了用户研究 QGIS 原件是否已进入当前容器，未发现最新工程 `.qgs/.qgz/.gpkg` 原件。
- 本轮尝试再次定位 `run_stage4_dispatch.py`（Stage 4/Stage 6 文档路径与部分扩展目录）及 Stage 7.2 报告，在检索的精确路径未取得。**这只证明特定路径没有返回文件，不能证明压缩包内或其他路径不存在**。
- 旧 Stage 8 F0/F1 报告明确：19/19 场址为搜索参考点，缺真实机型任务级能耗标定以及可执行航路和场站许可。本轮不擅自将其改为“已批准”。
- 已将 13 组历史 Stage 3–8 成果登记进版本谱系，统一设为 `HISTORICAL_*_ONLY`；已制定 13 个释放关口，其中仅历史提交身份确认为 `PASS_IDENTITY_ONLY`，**没有任何新计算许可证**。

## 2. 新旧实验数据隔离规则

| 数据层 | 历史可证据化内容 | 新实验判定 |
|---|---|---|
| 空间节点与连线 | Stage 8 旧 19 个参考点、76 条旧候选几何关系 | 不作为新版节点/航线；以新三分区工程为准，暂未冻结 |
| 合成任务 | Stage 2 的 918,000 条重采样记录；Stage 6 的 29,842 条条件任务、89,526 条模式记录 | 两套样本不得相加；重建独立任务主键与 M0/M1/M2 匹配规则 |
| 天气 | 2026 年 5–9 月 ERA5、NASA POWER、NEA 历史来源 | 可做来源审查；不得把网格数据描述为气象站实测 |
| 道路 | E02 原 128 条方向 OD，91 条模型可达、37 条异常或待吸附 | 旧 OD 与旧交通代理不可直接接入新空间网络 |
| 电动地面车 | 旧 Stage 6 的 0.23 kWh/km 条件情景 | 不能冒充燃油汽车排放基线 |
| 无人机能耗 | 通用机型旧 470 W/0.70 kWh/4 km 条件情景 | 禁止直接替代 DJI FlyCart 30 / Wingcopter 198 Cargo 的真实任务耗电 |
| 空域/审批 | Stage 8 几何预筛查，旧参考点均无站点批准证据 | WMP228、CTR、国界、CAAM/CAAS 均需按实验日期分层审查 |

## 3. R2 自动审计程序及其通过范围

交付 `r2_qgis_crosswalk.py`：可只读解析 QGS/QGZ 的 CRS 与图层源，计算工程及所引用 GeoPackage 的 SHA-256；枚举 GPKG 表、节点 ID、名称、分区、坐标（适用于 GeoPackage 点 WKB）、候选边 ID 与两端节点；按照旧/新 ID 和有充分 CRS 信息时的坐标差异创建对照表。**这些是自动筛查候选，不是无人机航线合法性或 QGIS 完整几何拓扑的科学验收**。

自动记录的主要文件：`new_qgis_layer_registry.csv`、`new_qgis_gpkg_table_registry.csv`、`new_qgis_node_candidates.csv`、`new_qgis_edge_candidates.csv`、`old_new_node_crosswalk_REVIEW_REQUIRED.csv`、`stage00_01_r2_gate.json`。

测试仅使用脚本临时构建的**虚构** GeoPackage（A/B/C 三个点、1 条线、3 条旧节点）：测试验证程序能够识别三分区、提取节点与边、将旧新 ID 分为匹配和删除/变动状态。测试 **PASS**，但真实 QGIS 未输入，科研输入验收仍为 **HOLD**。提供无 QGIS 情景的真实运行 `no_new_qgis_proof/stage00_01_r2_gate.json`，程序正确返回阻断。

### 3.1 新三分区工程冻结所需证据

1. 选定唯一 `.qgz` 或 `.qgs`，并携带所有实际使用的 `.gpkg` / `.shp` / `.geojson` / `.csv` 等图层。不要只上传截图、版式 PDF 或旧点表。
2. 计算工程和每个源文件 SHA-256；验证 CRS、几何完整性、坐标及国家边界；核对 A/B/C 的节点唯一性、名称字段、线路两端引用。
3. 逐点决定 `KEEP`、`MOVED`、`RENAMED`、`ADDED`、`REMOVED`、`SEARCH_ZONE`；A_N05、A_N07、C21、A_C03 仅在实际工程中存在时核实。
4. 明确新加坡一侧是背景地图、候选网络，还是含通关与监管假设的跨境物流实验；不能由背景地图自动推断可运营。
5. 将 CAAM/CAAS 有效日期、WMP228、Johor Bahru CTR、国界与场地状态作为证据字段，而不是用单一红色禁飞图形替代监管判定。

## 4. 释放关口与后续实验顺序

| 关口 | 本轮状态 | 下一步动作 |
|---|---|---|
| G00 历史 GitHub 提交身份 | PASS_IDENTITY_ONLY | 保持提交只读，不改写基线 |
| G01–G04 QGIS 原件、节点/线、旧新映射 | BLOCKED | 取得新版工程后执行脚本并人工审查 |
| G05–G06 历史复现链及全库哈希 | BLOCKED | 本地克隆固定提交，定位归档依赖并校验分卷 |
| G07–G08 任务协议与空域/场站 | BLOCKED | 冻结同任务分母、监管与地理证据 |
| G09–G11 天气、道路与 CO2e 模型 | NOT_STARTED | 仅在前述关口通过后重算 |
| G12 正式数值实验释放 | BLOCKED | 研究者审核并记录签批及活动输入清单 |

**正式裁定：Stage 00 = HOLD；Stage 01 = PARTIAL / HOLD。** 当前仅允许继续从历史文件提炼可复用的方法和参数溯源；不得发布新版三分区覆盖率、时间节约、经济性或减排效果。不得把软件测试 PASS 伪装为 GIS 输入或航空许可 PASS。

## 5. 用户本地执行步骤与证据交付

已提供 `RUN_R2_ON_WINDOWS.ps1` 及两支只读 Python 审计程序。配置实际的 GitHub 克隆目录、新 QGIS 工程路径和旧参考点 CSV 路径后，运行 Windows PowerShell 脚本即可生成全文件哈希、图层登记、节点/边、旧新对照、阻断报告、分卷核验日志。输出应放在独立审计目录，不得修改原 QGIS、历史实验文件或数据。

**最低下一次验收需要：** 最新三分区 QGIS 的工程文件 + 所有有效数据图层；如旧 Stage 8 19 点表位于压缩归档，则请在本地提供路径或随新工程一起导出，以便生成可核查的旧新坐标迁移表。若真实 GIS 图层名称/字段不符合自动识别规则，应通过 QGIS 人工检查并调整字段映射，而非把自动识别的“0 个节点”当作真实 0 个。

## 6. 证据来源

- GitHub 仓库及历史提交：<https://github.com/tasadapullo-svg/JB-CIQ-Drone-Logistics-Research-20261027/commit/4569817b8145efe2ae06f4b21addc1986f971c12>
- 历史 Stage 6 主脚本：`10_experiment_results/stage6_dual_region_multilevel_feeder/run_stage6.py`；Stage 6 README 和 RUN_INSTRUCTIONS。
- Stage 2 工程缺口：`outputs/next_stage/validation_report.json`、`engineering_gap_report.md`。
- Stage 8 空域/机型：`10_experiment_results/stage8_f0_f1_airspace_and_energy_evidence/reports/CIQ_Stage8_F0_F1_formal_experiment_audit_report_20261028.md`。
- 本次本地程序自测：`tests/test_r2_qgis_crosswalk.py`；实数据未加载；所有输出显式保留 `NOT_APPROVED` 状态。
