# CIQ 无人机物流 SCI 实验 — Stage 00 + Stage 01 正式审计报告

**报告编号：** CIQ-AUD-S00S01-20261030-R1  
**审计日期：** 2026-10-30（Asia/Kuala_Lumpur）  
**历史基线：** GitHub `tasadapullo-svg/JB-CIQ-Drone-Logistics-Research-20261027`，`main`，已观察到的提交 `4569817b8145efe2ae06f4b21addc1986f971c12`（2026-10-28）  
**新版空间输入：** 用户指定“最新 QGIS 三分区工程”；当前未取得可读取的 QGS/QGZ/GPKG 原件及其内容哈希  
**本轮实际操作：** GitHub 连接器远程关键文件内容核对、来源冲突分析、旧文件隔离策略、配套本地全量审计程序；没有运行任何新一轮数值仿真  
**状态：** **HOLD / NOT APPROVED（暂缓，尚未通过 Stage 00 + Stage 01 门槛）**  

> **声明：** 本报告是具备可核对证据的“初次审计裁定”，不是对 20,000 余文件完成本地哈希逐件验证后的终验报告。GitHub 历史打包报告中的数字属于其自身的历史审计结论；本轮不能将其冒充为独立重新验证。对未取得的最新 QGIS 工程、Stage 3–8 全部二进制结果及拆分大文件，不作通过声明。

## 1. 审计目标与方法

本轮只执行 Stage 00 和 Stage 01。Stage 00 冻结研究对象及空间输入，隔离旧项目中可污染新实验的文件；Stage 01 检查历史实验数据的可访问性、版本、依赖关系、模型与结论边界，形成后续 SCI 重跑的证据链。历史 Stage 3–8 保留作**只读基线**，不作为新版任务、天气、道路旅行时间或碳排放的自动输入。

证据等级：**E1**＝本轮远程实际读取文件内容及 Git blob 标识；**E2**＝历史审计文档声称但本轮未重算；**E3**＝仅从 README/目录映射识别路径；**U**＝未取得或无法独立核对。连接器提供的 40 位 `sha` 为 **Git blob 标识**，不是本轮实算的 SHA-256。

## 2. 关键结论

| 编号 | 结论 | 证据/状态 | 对新版实验的影响 |
|---|---|---|---|
| S00-01 | 历史 GitHub 快照以 A（Causeway）、B（Second Link）为原模型；Stage 6 固定站点与 Stage 8 的 19 个参考位置属于旧空间输入 | E1 | 旧节点、连线、站点映射全部禁止自动接入新版 QGIS |
| S00-02 | 最新 QGIS “三分区工程”在当前可访问的 GitHub 提交和 Google Drive 检索中尚未取得可直接读取的工程原件 | U | **硬阻断**：无法验收节点、边、CRS、图层来源、空间约束与版本哈希 |
| S01-01 | 早期 Stage 2 报告中的 918,000 行是 30 次重采样工程夹具；其 V5.5 冻结源及 V5.6 重采样程序存在缺口 | E1（审计文档） | 不能声称这些行是独立实测订单，不能无证据混入 Stage 6 样本 |
| S01-02 | Stage 6 实验采用 29,842 条冻结合成订单、30 种子、5 固定日期、三模式 89,526 行 | E1（Stage 6 README） | 新版必须建立一致订单全集、任务 ID、种子与配对协议；不能将 918,000 与 29,842 直接相加 |
| S01-03 | Stage 6 参数为 Generic UAV（0.70 kWh 电池、470 W 空载基础功率、4 km 每段限值）与电动地面车（0.23 kWh/km），并使用 0.740 kg CO2e/kWh 电网因子 | E1（`run_stage6.py`） | 不得冒充 DJI/Wingcopter 实际能耗、燃油汽车基线或已验证减排 |
| S01-04 | Stage 8 F0/F1 报告已明确两机型任务能耗未标定、19/19 参考位置未批准，候选直线不是合法航路 | E1 | 新版航线和监管筛查需要重新核对，不得承袭“合法可飞”标签 |
| S01-05 | README 指向的部分 Stage 6 辅助文件和 Stage 7.2 验证报告在相应精确路径返回未找到；不排除改名、改路径或嵌在归档中 | E1（访问测试） | 需要从完整工作区/路径映射恢复，不得宣布相应阶段可一键复现 |
| S01-06 | 五个月的天气质量汇总可读取，但 ERA5、NASA POWER、NEA 的观测类型不同，不能视为同一实测数据 | E1 | 后续天气重算必须按来源与时空分辨率分层，复核风雨约束 |

## 3. Stage 00：输入冻结与旧文件隔离裁定

### 3.1 版本选择

**新版唯一空间权威输入（待冻结）：** 最新 QGIS 三分区工程及其直接引用的矢量文件、坐标参考系、站点/道路/区域图层和航行约束图层。必须由实际 `.qgz`/`.qgs` 文件、所有有效图层数据、SHA-256、修改/导出日期构成一个完整冻结包。不能以地图截图、旧 19 点 CSV 或 Fig. 1 排版图代替。

**只读历史参照：** GitHub 的 Stage 3–8、Stage 2 工程审计、旧 GIS、旧天气和交通派生表、旧仿真及图形。历史数据的代码、参数和结果可用于溯源、方法迁移和定量复现实验，但没有经过显式纳入审批不得进入新一轮计算。旧文件无需删除；仅建立“不可作为活动输入”的约束。

### 3.2 待实际 QGIS 核验的空间检查

- QGS/QGZ 中项目 CRS、各站点/边/区域图层 CRS 与坐标单位；图层源是否实际存在、有没有绝对路径失效、重复 ID、空几何、跨区错分。
- 三分区的边界含义、节点 ID 及连线 ID 总表；相对于旧 A/B 19 参考点的新增、删除、改名、移动、弃用记录。
- A_N05、A_N07、C21、A_C03 等此前讨论过的重点点位：应以新工程实际存在性为前提，单独核对真实地块、口岸/跨境属性、起降和道路接驳证据；不能仅凭地理中心点宣布场站成立。
- WMP228、Johor Bahru CTR、CAAM/CAAS 管辖边界、国界、受限及待审批类别，应记录图层**官方来源、版本与实验日期有效性**。红色范围不可自动当作全时段、全高度、全用途统一禁飞区。
- 新 GIS 覆盖的新加坡部分是否只是地理背景，还是有订单、CIQ 处理和跨境运营研究任务；必须在任务主表中明确，避免旧模型仅针对马来西亚境内却写成经验证跨境运营。

### 3.3 明确的目录隔离政策

| 历史路径 | 本阶段处理 | 新算式可直接读取？ |
|---|---|---|
| `10_experiment_results/Stage3_RQ1_M0/` 与其他 `stage4_*` 至 `stage8_*` | 保留旧仿真、统计、审计、图件 | **否** |
| `03_gis_and_road_network/` | 只读旧 OSM/OD/参考点与空间方法 | **否** |
| `06_figures_and_visualizations/` | 历史论文图与示意材料 | **否** |
| `02_base_and_traffic_data/`、`04_weather_data/`、`data/weather_2026/` | 历史气象/交通数据可供来源审查；需经新的数据门槛登记 | **默认否** |
| 用户最新 QGIS QGZ/QGS、对应 GPKG/GeoJSON/CSV | 唯一新版空间输入候选（尚未验证） | **暂缓，直至签批** |

## 4. Stage 01：关键文件逐件远程核查

以下“读取成功”只表示内容访问和版本标识得到核对；并不代表模型结果通过独立重新计算。

| 文件（相对于仓库根目录） | 本轮结果 | 审计意义 |
|---|---|---|
| `README.md` | 已读取（E1） | 仓库研究范围、证据类别、阶段目录和科学限制 |
| `GITHUB_VALIDATION_REPORT.md` | 已读取（E1） | 自报告 20,069 个文件（加入报告前）、13 组分卷资产、2 份密钥排除；未独立核对 |
| `.gitignore` | 已读取（E1） | 排除真实密钥、缓存、重建大型文件 |
| `directory_mapping.csv` | 已读取（E1） | 中文旧目录与英文仓库目录映射 |
| `github_upload_manifest.csv` | 路径与 Git blob 可识别，但远程内容返回空（U） | **不能逐行独立审核源文件数、大小及 SHA-256** |
| `path_mapping.csv` | 路径与 Git blob 可识别，但远程内容返回空（U） | **不能完整追踪全部改名文件** |
| `outputs/next_stage/DELIVERY_README.md` | 已读取（E1） | 918,000 重采样记录、128 OD、91 可达、37 异常及基线缺口 |
| `outputs/next_stage/validation_report.json` | 已读取（E1） | 机器可读旧门槛标记：正式全量模拟未启动；V5.5 和 V5.6 生成器缺失 |
| `outputs/next_stage/engineering_gap_report.md` | 已读取（E1） | 早期模型和来源缺口；与后续 Stage 6 实验并非同一验证阶段 |
| `outputs/stage2_20261027/STAGE2_README.md` | 已读取（E1） | Stage 2 是门槛/诊断测试，不是正式完整绩效仿真 |
| `outputs/stage2_20261027/tests/test_stage2.py` | 已读取（E1） | 已知测试结构；本轮未执行 |
| `10_experiment_results/stage6_dual_region_multilevel_feeder/README_STAGE6_CN.md` | 已读取（E1） | Stage 6 样本定义、条件性结果、模型限制 |
| 同目录 `run_stage6.py` | 已读取（E1） | 旧 A/B 固定站点、天气/路由/能耗/成本假设与任务状态机 |
| 同目录 `RUN_INSTRUCTIONS.md` | 已读取（E1） | 记录原工程的入口和依赖 |
| 同目录 `requirements.txt` | 已读取（E1） | 核心标准库，Excel 工具另计 |
| 同目录 `stage6_order_level.csv.gz` | 文件路径识别，二进制内容未解码（U） | 不能据此宣布逐订单数据通过行级复核 |
| 同目录 `run_stage4_dispatch.py`、`run_stage6_sensitivity.py`、`qa_and_report.py` | 指定精确路径未取得（U） | Stage 6 README 描述的就地复现链需要核实实际位置/归档成员 |
| 同目录 `stage6_QA.json`、`stage6_area_summary.csv` | 指定精确路径未取得（U） | 可能另在交付包内，暂不能验证摘要与代码输出对应关系 |
| `10_experiment_results/stage7_2_main_experiments_and_statistics/Stage7_2_validation_report_20261027.md` | README 指向路径未取得（U） | 不据此宣称文件全库缺失；需完整路径清单定位 |
| `10_experiment_results/stage8_f0_f1_airspace_and_energy_evidence/reports/CIQ_Stage8_F0_F1_formal_experiment_audit_report_20261028.md` | 已读取（E1） | F0 能耗与 F1 合规部署仍为 BLOCKED |
| `data/weather_2026/processed/final_verification_summary.json` | 已读取（E1） | 历史月份覆盖与交叉对照资料；未实算天气任务条件 |
| `tools/reassemble_large_files.py` | 已读取（E1） | 原工程按分卷 SHA-256 验证 13 组大文件的程序；本轮未执行 |

### 4.1 特别发现：不能混淆两个订单全集

Stage 2 工程审计记载的 30 种子、918,000 条 V5.6 订单，是重采样工程夹具，且冻结 V5.5 源和重采样代码缺口尚在；Stage 6 的 29,842 条是另一组已选取的合成订单，三个模式乘以 3 后有 89,526 模式级结果。它们不具备直接作为同一母样本或独立重复观测合并的资格。新版统一的任务 ID、需求生成说明、日期/区域/种子与同任务对比规则应重新冻结。

### 4.2 特别发现：旧 M0 碳排放口径不是新版汽车燃油基线

旧 `run_stage6.py` 定义 `van_kwh_per_km = 0.23`、`grid_kgCO2e_per_kwh = 0.740`，并含设施/设备日分摊的假设性项；这属于电动地面车条件情景。新版如要比较汽油/柴油车辆、纯地面与地空协同，必须先明确车辆种类、单位燃油消耗、里程/怠速/空载回程、共配/批量装载、CO2 与 CO2e、燃料上游与电力边界。不能直接把旧电动车结果称为道路汽车排放实测，也不能将碳因子与旧结果直接替代更新方案。

### 4.3 特别发现：两款真实无人机与旧 Generic UAV 不等价

Stage 8 报告确认 DJI FlyCart 30 与 Wingcopter 198 Cargo 公开规格，但任务级电池放电、载荷—功率—风雨—起降关系尚未足够标定。旧 470 W 通用功率不得用于新机型真实能耗计算；航程上界也不能直接转换为每单 kWh。Stage 8 中 19/19 参考点不是批准场站，76 条旧几何候选不是合法任务飞行路线。

### 4.4 特别发现：天气和道路证据是条件代理

历史天气包报告 2026 年 5–9 月、四个参考点，ERA5/NASA POWER 属网格数据，NEA 才可能是有站点元数据的实测。5 月历史交叉对照中 ERA5 与 NASA 降雨相关系数约 0.0277（见 `final_verification_summary.json`），提示不同产品不能互相当作完全一致的真值。历史路网 128 个有向 OD 中 91 条有模型路径，37 条断路/待吸附；区域小时 FCD 代理、转向限制、CIQ 排队与方向旅行时间外部标定存在独立缺口。新 QGIS 更改节点后，应重新建立 OD 而非静默继承旧旅行时间。

## 5. 阻断项、优先级和解除证据

| ID | 级别 | 阻断点 | 解除所需的最小证据 |
|---|---|---|---|
| B01 | Critical | 最新 QGIS 三分区原件未在本轮可读 | QGZ/QGS + 被引用的 GPKG/其他矢量、文件级 SHA-256、版本日期 |
| B02 | Critical | 新旧节点、ID、区域和候选航段映射未复核 | 旧/新节点差异表；有效节点、边、区域及用途冻结表 |
| B03 | Critical | 历史路径映射和上传清单无法逐行读取，分卷未在本轮校验 | 本地运行全量逐文件哈希；20,031 条源清单逐行对应；13 组大文件校验日志 |
| B04 | High | Stage 6 复现依赖按文档路径未取得；Stage 7.2 指定报告路径未取得 | 实际存在的文件路径/归档成员清单、依赖和一键复现测试 |
| B05 | Critical | 918,000 和 29,842 两种样本谱系不可混用 | 新版合成任务协议、唯一订单 ID、配对规则、重复/缺失核验 |
| B06 | Critical | 两真实机型功率与运营假设尚未建立同口径标定 | 飞行任务级能耗范围/来源、风雨/载荷情景、退化与敏感性表 |
| B07 | Critical | 监管空间边界、许可与场地真实性未证明 | 对实验日期有效 CAAM/CAAS 文件及空间图层分类、站点证据；未证实保持 `UNVERIFIED` |
| B08 | High | 新旧地面交通基线和运营碳核算边界不一致 | 车辆燃油/电力模式分列、任务级车辆链路、排放因子来源与边界注册表 |
| B09 | High | 旧路网方向路径及 CIQ 等待模型未独立验证 | 重建新 OD 与网络可达性；明确 CIQ 等待是实测、代理还是缺失 |
| B10 | High | 新加坡跨境业务和单纯地图背景的研究对象尚未在新版任务层定义 | 明确境内/跨境、清关与法规假设；不能从背景图推断跨境实际服务 |

## 6. 裁定与下一道释放门槛

- **Stage 00：HOLD。** 旧历史基线可锁定，但最新 QGIS 工程尚未完成文件、图层及空间语义审计。
- **Stage 01：PARTIAL / HOLD。** 已完成关键文本和代码文件的远程证据审读，建立了重要模型冲突清单；尚未完成全库的逐文件哈希、归档重组、全部 Stage 3–8 结果复算。
- **天气/道路/运营 CO2e 重新计算：NOT STARTED。** 不因部分历史 QA 报告自称通过而释放后续 Stage 02+ 计算。

**最小可执行验收次序：**（1）本地对最新版 QGIS 和仓库全文逐文件生成 SHA-256 清单；（2）建立三分区新版节点—边—约束图层和新旧差异；（3）恢复历史 Stage 6/7 代码—配置—数据依赖与结果位置；（4）审核并冻结配对合成任务协议、天气/路网/能耗/排放模型输入注册表；（5）人工签批 Stage 00/01 后，才进行新的气象、道路及运营碳排放实验。

## 7. 本报告交付与复查命令

- `CIQ_Stage00_Stage01_Audit_Report_20261030.docx`：本正式审计报告可编辑版。
- `CIQ_Stage00_Stage01_Audit_Report_20261030.md`：报告 Markdown 原文。
- `stage00_01_local_auditor.py`：只读本地逐文件核验程序，输出 `file_level_sha256_inventory.csv`、`qgis_layers.csv`、`audit_summary.json`、`local_audit_report.md` 与 `active_inputs_DRAFT_DENY_ALL.json`。

```powershell
python stage00_01_local_auditor.py --repo "D:\\CIQ\\JB-CIQ-Drone-Logistics-Research-20261027" --qgis "D:\\CIQ\\Latest_QGIS_3zones\\project.qgz" --out "D:\\CIQ_AUDITS\\Stage00_01"
python "D:\\CIQ\\JB-CIQ-Drone-Logistics-Research-20261027\\tools\\reassemble_large_files.py" --verify-only
```

**注意：** `project.qgz` 是示例占位文件名，不是声称已发现的真实文件；必须改成最终 QGIS 工程的真实路径。`stage00_01_local_auditor.py` 不重跑科学模型，不会自行宣告人工审核通过。

## 8. 本轮可核查的主要历史出处

1. [GitHub 历史仓库](https://github.com/tasadapullo-svg/JB-CIQ-Drone-Logistics-Research-20261027)，基线提交 `4569817b8145efe2ae06f4b21addc1986f971c12`。
2. [仓库 README](https://github.com/tasadapullo-svg/JB-CIQ-Drone-Logistics-Research-20261027/blob/main/README.md)、[打包验收报告](https://github.com/tasadapullo-svg/JB-CIQ-Drone-Logistics-Research-20261027/blob/main/GITHUB_VALIDATION_REPORT.md)。
3. [Stage 2 验收 JSON](https://github.com/tasadapullo-svg/JB-CIQ-Drone-Logistics-Research-20261027/blob/main/outputs/next_stage/validation_report.json)、[缺口报告](https://github.com/tasadapullo-svg/JB-CIQ-Drone-Logistics-Research-20261027/blob/main/outputs/next_stage/engineering_gap_report.md)。
4. [Stage 6 方法与结果](https://github.com/tasadapullo-svg/JB-CIQ-Drone-Logistics-Research-20261027/blob/main/10_experiment_results/stage6_dual_region_multilevel_feeder/README_STAGE6_CN.md)、[Stage 6 仿真代码](https://github.com/tasadapullo-svg/JB-CIQ-Drone-Logistics-Research-20261027/blob/main/10_experiment_results/stage6_dual_region_multilevel_feeder/run_stage6.py)。
5. [Stage 8 F0/F1 审计](https://github.com/tasadapullo-svg/JB-CIQ-Drone-Logistics-Research-20261027/blob/main/10_experiment_results/stage8_f0_f1_airspace_and_energy_evidence/reports/CIQ_Stage8_F0_F1_formal_experiment_audit_report_20261028.md)、[天气源核验摘要](https://github.com/tasadapullo-svg/JB-CIQ-Drone-Logistics-Research-20261027/blob/main/data/weather_2026/processed/final_verification_summary.json)。

---

**发布判断：** 当前最严谨的结论是“旧基线已识别、关键科学冲突已审读、新版文件级验收未完成、后续计算继续阻断”。在补齐 QGIS 原件和全量逐文件结果之前，不给出 `PASS`。
