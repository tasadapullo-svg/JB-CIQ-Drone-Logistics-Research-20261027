# Johor Bahru–Singapore CIQ Drone Logistics Research

> A reproducible research package for multimodal drone-logistics analysis around the Johor Bahru–Singapore Causeway and Second Link CIQ areas.

[Current formal release](#current-formal-release-2026-10-30) · [中文版本说明](#中文版本说明先读) · [Repository contents](#repository-contents) · [Reproduction](#reproduction) · [Scientific limitations](#scientific-limitations)

## Current formal release: 2026-10-30

> **Version boundary:** directories `00`–`10`, `data`, and `outputs` preserve the research package completed through 2026-10-28. They are retained as historical groundwork and early-stage evidence. The formal research version starts on **2026-10-30** in directories `11`–`13`.

The 2026-10-30 release is based on a redesigned flight-study area, revised study points, explicitly identified no-fly constraints, a rebuilt QGIS project, and rerun experiments. Results dated 2026-10-31 are continuations and closure checks of this formal research line, not a return to the earlier version.

| Version | Repository location | Status and permitted use |
|---|---|---|
| Historical package through 2026-10-29 | `00_project_documentation/` through `10_experiment_results/`, plus `data/` and `outputs/` | Historical groundwork, feasibility evidence, method development, and provenance only. Do not substitute its spatial definitions or experimental outputs for the formal results. |
| Formal experiment results from 2026-10-30 | `11_formal_results_20261030/` | Current QGIS definition and formal S07–S11 experiment chain; this is the primary source for current results and conclusions. |
| Manuscript and theory closure dated 2026-10-31 | `12_manuscript_and_theory_20261031/` | Current writing control draft, theory-source starter, figure/table evidence index, and closure package. These are research and writing materials, not a completed submitted manuscript. |
| Version and release documentation | `13_release_documentation_20261031/` | Rules for interpreting the old and current versions. |
| Full missing-data completion | `14_missing_data_completion_20261031/` | Files whose SHA-256 content was not represented by the legacy package or directories `11`–`13`; original relative paths are retained beneath this directory. |

Start with:

- `11_formal_results_20261030/README_最终版实验结果_先读.md`
- `12_manuscript_and_theory_20261031/README_正式论文与理论材料_先读.md`
- `13_release_documentation_20261031/README_项目总览与版本规则_20261031.md`
- `13_release_documentation_20261031/FULL_UPLOAD_AUDIT_20261031.md`

## 中文版本说明（先读）

本仓库以 **2026年10月30日** 为正式版本分界点：

- 原有 `00–10`、`data` 和 `outputs` 保存截至10月28日形成的历史研究包；其中10月29日以前的方案、实验、图表与审查材料仅作为前期基础论证、方法演进和来源追溯，不作为当前正式结论的直接依据。
- `11_formal_results_20261030` 保存10月30日重新设计飞行区域、研究点位、明确禁飞区并重建 QGIS 后重新完成的正式实验结果，是当前论文结果与结论的主要依据。
- `12_manuscript_and_theory_20261031` 保存10月31日新增的全文收口总控稿、图表证据索引、理论来源起始表和收口材料包。这些文件属于10月30日正式研究路线的写作与证据整理成果，不是已经完成的投稿稿件。
- `13_release_documentation_20261031` 保存版本关系和文件使用顺序说明。
- `14_missing_data_completion_20261031` 补齐第一次更新后哈希审计发现的全部非敏感缺失数据，并保留源目录相对路径。

如果历史文件与当前正式结果存在差异，以 `11_formal_results_20261030` 及其10月31日闭环验证为准。历史文件仍保留，用于证明研究基础、解释版本变化和支持可追溯性。

最终逐文件审计覆盖22,896个当前源文件：22,740个研究文件已上传或由仓库中相同SHA-256内容代表，缺失为0；2个真实API密钥和154个 `__pycache__`、`.pyc`、临时文件因安全或可再生性质明确排除。完整明细见 `13_release_documentation_20261031/SOURCE_COVERAGE_MANIFEST_20261031.csv`。

## Project overview

This repository preserves the code, configuration, input data, weather records, GIS and road-network materials, experiment outputs, figures, validation reports, and integrity manifests used in a staged SCI research workflow for Johor Bahru–Singapore CIQ drone logistics.

The project compares conditional multimodal operating scenarios around two study areas:

- **Area A — Causeway:** the Johor Bahru–Woodlands crossing area.
- **Area B — Second Link:** the Iskandar Puteri–Tuas crossing area.
- **M0:** road-only reference scenario.
- **M1:** fixed-site or multilevel feeder scenario with a drone segment.
- **M2:** vehicle–drone coordinated scenario.

The package includes engineering audits and staged experiments from Stage 3 through Stage 8. It is intended for transparent scientific review and reproduction. It is **not** an operational deployment package, an aviation authorization, or proof that any candidate site or geometric connection is approved for flight.

## Repository status

Legacy package validation date: **2026-10-28**. Formal-results update date: **2026-10-31**.

| Check | Result |
|---|---:|
| Source files represented in the upload manifest | 20,031 / 20,031 |
| Files copied directly | 20,016 |
| Large source assets represented by verified parts | 13 |
| Credential files intentionally excluded | 2 |
| Duplicate SHA256 groups | 0 |
| Non-ASCII repository paths | 0 |
| Paths containing spaces | 0 |
| Largest tracked file | 20 MiB |
| Preserved weather-source files | 19,757 |

For the legacy `00`–`10`, `data`, and `outputs` package, every source file is accounted for in `github_upload_manifest.csv`. The two excluded files contain real API credentials and remain outside this public package. They are not required for reviewing the already downloaded data.

The formal update first added 997 tracked files across `11`–`13`, then added the hash-audited completion set in `14`. Files larger than 20 MiB are represented by verified `.parts` directories with `parts_manifest.json`, original byte size, and SHA-256. Run `python tools/reassemble_large_files.py --verify-only` to verify historical and current split assets.

## Research data and evidence classes

The repository deliberately separates observations, gridded products, model outputs, assumptions, and screening geometry.

| Evidence class | Examples | Required interpretation |
|---|---|---|
| Station observations | Singapore NEA records where station metadata is present | Observational data for the identified station and time only |
| Gridded/reanalysis weather | Open-Meteo ERA5 | Reanalysis/grid product, not station measurement |
| Gridded meteorological comparison | NASA POWER | Gridded product used for comparison, not station measurement |
| Road-network model | OSM-derived directed network and OD paths | Modelled network connectivity, not observed freight routes |
| Traffic proxy | FCD-derived hourly ratios and joint tables | Conditional traffic proxy, not direct travel-time observation for every OD |
| Demand records | Frozen multi-seed synthetic orders | Experimental fixtures, not independent real customer orders |
| Candidate drone geometry | Reference anchors and straight-line connections | Screening geometry only; not approved sites or permitted routes |
| Cost, energy, and emissions | Scenario parameters and staged calculations | Conditional model outputs unless an external source is explicitly documented |

Missing values are preserved as missing. They must not be converted to zero. Labels including `MODEL_NOT_OBSERVED`, `NOT_FLIGHT_ROUTES`, `NOT_AUTHORIZED`, and `UNVERIFIED` are part of the scientific meaning and must not be removed.

## Weather dataset

The weather package covers May–September 2026 for four reference points on the Malaysia and Singapore sides of the Causeway and Second Link.

Sources:

- **Open-Meteo ERA5:** hourly precipitation, 10 m and 100 m wind speed/direction, and 10 m gusts.
- **NASA POWER:** hourly precipitation, 10 m wind speed, and 10 m wind direction for cross-source comparison.
- **Singapore NEA:** station rainfall, wind speed, and wind direction records, with 30-minute summaries where source coverage permits.

Processed monthly workbooks are stored in `data/weather_2026/processed/`. Each workbook contains 16 sheets covering metadata, hourly products, NEA observations, station selection, source registration, cross-validation, API logs, and quality control.

| Month | Study hours per point | Main hourly rows | ERA5 rows | NASA rows | Verification anomalies |
|---|---:|---:|---:|---:|---:|
| 2026-05 | 744 | 2,976 | 2,980 | 2,976 | 0 |
| 2026-06 | 720 | 2,880 | 2,884 | 2,880 | 0 |
| 2026-07 | 744 | 2,976 | 2,980 | 2,976 | 0 |
| 2026-08 | 744 | 2,976 | 2,980 | 2,976 | 0 |
| 2026-09 | 720 | 2,880 | 2,884 | 2,880 | 0 |

The four extra ERA5 rows in each month are metadata/grid-return artifacts retained by the pipeline and are not additional study hours. Variable-level coverage, missingness, station selection, request logs, and SHA256 values are reported in the monthly QC and manifest files and in `data/weather_2026/processed/final_verification_summary.json`.

## Experiment stages

| Stage | Main purpose | Representative location |
|---|---|---|
| Stage 2 audit | Frozen-input audit, OD diagnostics, release-gate checks, and smoke testing | `outputs/stage2_20261027/` |
| Stage 3 | RQ1 M0 reference experiment | `10_experiment_results/Stage3_RQ1_M0/` |
| Stage 4 | Area B M1/M2 scenarios and paired orders | `10_experiment_results/stage4_area_b_m1_m2_scenarios/` |
| Stage 5 | Operational sensitivity, cost, energy, and carbon scenarios | `10_experiment_results/stage5_operational_sensitivity_cost_carbon/` |
| Stage 6 | Dual-region, multilevel feeder comparison using 30 frozen seeds | `10_experiment_results/stage6_dual_region_multilevel_feeder/` |
| Stage 7.1 | Audit, frozen protocol, and candidate experiment matrix | `10_experiment_results/stage7_1_audit_and_experiment_matrix/` |
| Stage 7.2 | Main experiments, statistics, uncertainty, and Pareto figures | `10_experiment_results/stage7_2_main_experiments_and_statistics/` |
| Stage 7.3 | Independent audit and remaining-experiment review | `10_experiment_results/stage7_3_independent_audit_and_remaining_experiments/` |
| Stage 7 extensions | Fuel/economic baselines, run-level checks, and joint uncertainty | `10_experiment_results/stage7_g06_g08_fuel_economy_and_operational_emissions/`, `stage7_g09_g10_run_level_validation/`, and `stage7_g11_g12_joint_uncertainty/` |
| Stage 8 | Airspace/energy evidence screening, supplementary experiments, and conclusion updates | `10_experiment_results/stage8_*` |

Stage 6 evaluates 29,842 frozen synthetic orders over 30 seeds and five fixed dates. The three scenario modes retain matching order identities, producing 89,526 mode-level records. The included Stage 6 README, acceptance report, QA JSON, sensitivity outputs, and order-level results define the exact interpretation boundary.

Stage 8 adds traceable aircraft-specification and spatial screening evidence. Its reference anchors and geometric links remain search zones and candidate connections; they do not establish land access, obstacle clearance, regulatory approval, BVLOS authorization, or permitted cross-border routes.

## Repository contents

```text
.
├── 00_project_documentation/          # Instructions and organization records
├── 01_research_design_and_manuscript/ # Research design and manuscript planning
├── 02_base_and_traffic_data/          # Frozen traffic and derived joint data
├── 03_gis_and_road_network/           # GIS inputs, OSM road model, code, tests, reports
├── 04_weather_data/                   # Compact weather summaries
├── 05_review_and_validation/          # Independent reviews and validation records
├── 06_figures_and_visualizations/     # Figures, maps, and visual materials
├── 07_code_and_tools/                 # Weather and workspace-maintenance scripts
├── 08_archives/                       # Preserved source/delivery archives
├── 09_other_materials/                # Literature and supporting materials
├── 10_experiment_results/             # Stage 3–8 outputs and supplementary analyses
├── 11_formal_results_20261030/         # Formal QGIS and rerun S07–S11 results
├── 12_manuscript_and_theory_20261031/  # Current manuscript closure and theory/evidence indexes
├── 13_release_documentation_20261031/  # Old-versus-current version rules
├── 14_missing_data_completion_20261031/ # Hash-audited completion of previously missing data
├── data/weather_2026/                 # Raw API responses, logs, QC, and workbooks
├── outputs/                           # Engineering audits and intermediate outputs
├── tools/reassemble_large_files.py    # Large-file verification and reconstruction
├── directory_mapping.csv              # Original-to-English directory mapping
├── path_mapping.csv                   # Original-to-English file mapping
└── github_upload_manifest.csv         # Size, SHA256, split, and exclusion manifest
```

Useful starting points:

- `GITHUB_VALIDATION_REPORT.md` — repository-level packaging checks.
- `data/weather_2026/processed/final_verification_summary.json` — monthly weather verification.
- `outputs/next_stage/DELIVERY_README.md` — early audit and release-gate findings.
- `outputs/stage2_20261027/STAGE2_README.md` — Stage 2 diagnostics and test scope.
- `10_experiment_results/stage6_dual_region_multilevel_feeder/README_STAGE6_CN.md` — Stage 6 methods, results, and limitations.
- `10_experiment_results/stage7_2_main_experiments_and_statistics/Stage7_2_validation_report_20261027.md` — Stage 7.2 validation.
- `10_experiment_results/stage8_f0_f1_airspace_and_energy_evidence/reports/CIQ_Stage8_F0_F1_formal_experiment_audit_report_20261028.md` — Stage 8 F0/F1 audit.

## Reproduction

### 1. Clone the repository

```bash
git clone https://github.com/tasadapullo-svg/JB-CIQ-Drone-Logistics-Research-20261027.git
cd JB-CIQ-Drone-Logistics-Research-20261027
```

On Windows, enable long-path support if the checkout location is deeply nested:

```powershell
git config --global core.longpaths true
```

### 2. Verify the large-file parts

Thirteen source assets larger than 20 MiB are stored as numbered binary parts. Verification reads the parts in sequence and checks their combined size and SHA256 without writing reconstructed archives:

```bash
python tools/reassemble_large_files.py --verify-only
```

Expected result: all 13 split assets pass.

To reconstruct them locally:

```bash
python tools/reassemble_large_files.py
```

Reconstructed files are written under `reassembled_large_files/`, which is intentionally ignored by Git.

### 3. Create a Python environment

Python requirements are stage-specific. Do not assume that every historical archive used one shared environment.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

For the GIS road-network module:

```powershell
python -m pip install -r 03_gis_and_road_network/road_network_project/JB_CIQ_E02_roadnet_V4_6/requirements.txt
```

For Stage 6:

```powershell
python -m pip install -r 10_experiment_results/stage6_dual_region_multilevel_feeder/requirements.txt
```

### 4. Run package-level verification

```powershell
python tools/reassemble_large_files.py --verify-only
python outputs/next_stage/tests/test_next_stage_audit.py
python outputs/stage2_20261027/tests/test_stage2.py
python 03_gis_and_road_network/road_network_project/JB_CIQ_E02_roadnet_V4_6/tests/independent_logic_test.py
```

Some historical scripts expect their working directory or an extracted upstream archive. Read the stage-specific instructions before rerunning a stage.

### 5. Reproduce Stage 6

```powershell
cd 10_experiment_results/stage6_dual_region_multilevel_feeder
python run_stage6.py
```

If the required upstream bundle is not in the default location, set the path explicitly:

```powershell
$env:CIQ_BUNDLE = "D:\path\to\upstream_bundle.zip"
python run_stage6.py
```

See `RUN_INSTRUCTIONS.md` in the Stage 6 directory for the required execution order and output descriptions.

## Provenance and integrity

- `directory_mapping.csv` maps the original directory names to the GitHub-safe English structure.
- `path_mapping.csv` maps every original path to its packaged path.
- `github_upload_manifest.csv` records source size, source SHA256, package status, split counts, and intentionally excluded secrets.
- Each `.parts` directory includes a `parts_manifest.json` with the original filename, byte size, SHA256, and ordered part list.
- Monthly weather workbooks have adjacent manifest and QC files.
- Major experimental deliveries contain their own SHA256 manifests, audit tables, or acceptance reports.

Do not rename or reorder `.parts/part_*.bin` files unless the associated manifest and hashes are regenerated.

## Scientific limitations

The following constraints apply to any paper, presentation, or downstream model using this repository:

1. ERA5 and NASA POWER values are gridded products and must not be described as station observations.
2. NEA values are station observations only when the corresponding station and source metadata are present.
3. Frozen demand records are synthetic experimental orders, not independent observed deliveries.
4. OSM-derived paths and traffic proxies provide modelled accessibility and travel conditions, not verified freight operations.
5. Candidate sites are reference anchors or search zones. Candidate straight lines are not approved drone routes.
6. Stage 6 and related cost, energy, and carbon outputs are conditional scenario results. They are not aircraft certification, company cost forecasts, or validated life-cycle claims.
7. Stage 8 aircraft and airspace work is a traceable pre-screening exercise. Regulatory, land-access, obstacle, and operational approvals remain external requirements.
8. Unknown or unverified values remain null or explicitly labelled; they must not be replaced with fabricated values or interpreted as zero.

## Security and data handling

- Real API credential files are excluded from version control.
- `.env`, private-key, certificate, virtual-environment, cache, and reconstructed-large-file patterns are ignored.
- Do not commit local credentials, personal tokens, or machine-specific secret configuration.
- Before publishing derived datasets, review their source terms and any applicable redistribution requirements.

## Citation and reuse

No standalone open-source or data license is included in this package. Repository availability does not by itself grant permission to reuse every third-party dataset or document. Cite the original data providers and methods described in the source registry and stage reports, and obtain permission from the repository owner before redistribution beyond the applicable source terms.

When citing results, identify the exact stage, scenario, input freeze, and validation report rather than citing the repository as a single undifferentiated dataset.

## 中文说明

本仓库是柔佛新山—新加坡 Causeway 与 Second Link 两个 CIQ 研究区域的无人机—地面车辆多模式物流 SCI 工程包，包含代码、配置、交通与气象数据、GIS/道路网络、Stage 3–8 实验结果、图表、审计报告和 SHA256 清单。

请注意：ERA5 与 NASA POWER 是网格/再分析产品，不是气象站实测；NEA 数据只有在明确记录站点元数据时才可称为站点观测。现有订单为冻结的合成实验订单，候选站点和几何连线不代表已批准的起降点或飞行航线。缺失值不得当作 0，所有 `MODEL_NOT_OBSERVED`、`NOT_FLIGHT_ROUTES`、`NOT_AUTHORIZED` 和 `UNVERIFIED` 标签必须保留。

仓库中的 13 个大型资产已拆分为不超过 20 MiB 的分卷。克隆后先运行：

```bash
python tools/reassemble_large_files.py --verify-only
```

完整文件对应关系和校验信息见 `github_upload_manifest.csv`。两个真实 API 密钥文件为避免泄露而未上传，其余源文件均已在清单中逐项对应。
