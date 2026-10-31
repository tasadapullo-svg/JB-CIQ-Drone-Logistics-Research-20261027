# CIQ V5 — S07 GitHub 内原件数值验收工程（2026-10-30）

## 为什么制作本工程

历史的 5 份天气 XLSX、5 个月 FCD `.csv.gz`、A/B 原始有向道路文件均已上传到 GitHub；此前在 ChatGPT 运行环境中不能取回大文件的原始字节。因此无法在本地把历史审计摘要冒充最新数值复核。本工程提供**直接在 GitHub Actions 的 runner 上检查仓库原件**的可运行入口，不要求重新下载整个 GitHub 项目到 ChatGPT。

## 基准与结果边界

- 空间固定：V5 68 个活动节点（A29，B10，C29），不修改任何坐标或网络图层。
- 需求固定：82,620 条条件性合成订单、4,590 个种子×日期场景、22,950 个五模式运行键；禁止生成新订单、删单或把不同场景混合调度。
- 阶段目标：S07 **源文件字节与数据结构验收**。即使所有基本检查通过，仍必须单独核验 ERA5 风雨单位、累计降雨时段、FCD 道路方向/速度映射、C 区有向道路与 68 个站点真实车行入口，才能正式放行车辆和无人机运营仿真。
- 绝不能把历史参考订单 Stage 6、历史 E03 两口岸天气 CSV 和 FCD 汇总包列为**新版冻结订单必需原件**。它们用于溯源或交叉验证。
- 历史 A/B 路网只证明旧图的记录存在，无法证明 V5 A/B/C 有向路网、转向规则和跨境排除全部符合要求。
- 此工程不产生配送时间、燃油消耗、任务耗电或运营 CO₂e 的正式数值。

## 执行方案 A：GitHub Actions（推荐）

1. 下载并解压本 ZIP。
2. 将压缩包内 `.github/workflows/ciq-s07-true-numeric-qa.yml` 与 `tools/ciq_s07/` **按原目录结构复制到原 GitHub 仓库**（可通过本地 Git + Codex）。直接提交在单独 QA 分支，**不覆盖历史 Stage 3–8 与 V5 原工程**。
3. 推送分支时应触发 `CIQ V5 S07 actual weather traffic and road structural QA` 工作流；如仓库允许，也可在 Actions 页面手动运行。Actions 必须在 GitHub 仓库中启用。
4. 下载本次 run 生成的 `CIQ-V5-S07-actual-QA` artifact，查看 `S07_GITHUB_ACTUAL_NUMERIC_QA.json`、`S07_SOURCE_CHECK.csv`、`S07_WEATHER_MONTHLY_CHECK.csv` 和原始工作表提取 CSV。
5. 把 artifact ZIP 上传本聊天，可继续做逐小时风雨、道路 FCD 与 V5 节点覆盖的独立验收。**不能在实际运行前宣布 PASS。**

该 workflow 使用当前分支的测试程序与冻结输入 ZIP，同时通过 `actions/checkout` 将原始数据检出到历史提交 `4569817b8145efe2ae06f4b21addc1986f971c12`；不需要提供任何个人 API key，不写仓库数据。

## 执行方案 B：本地 Windows 已有 GitHub 工程

```bat
RUN_LOCAL_FROM_REPO.cmd "D:\path\to\JB-CIQ-Drone-Logistics-Research-20261027"
```

该路径必须指向含 `data/weather_2026/processed`、`02_base_and_traffic_data/traffic_data` 的本地仓库根目录。若本地版本不是固定提交，源文件的 Git blob/SHA-256 会明确暴露不匹配，而非静默采用新版数据。

## 不同放行门槛

| 门槛 | 核心文件/证据 | 本次离线环境 | 放行要求 |
|---|---|---|---|
| V5 冻结输入 | zip 内锁定 68 点、82,620 订单、4,590 场景、22,950 模式键 | **PASS，真实解压与 SHA-256 复算** | 不变 |
| S07 核心数值源文件 | 5 天气 XLSX + 1 份 FCD `.csv.gz` | **HOLD（0/6 本地原件字节）** | GitHub runner 验证后逐行检查 |
| 旧 A/B 路网原件 | A/B 有向边和节点表共 4 份 | **HOLD（0/4 本地原件字节）** | 仅归档/结构验收 |
| 4 份可选历史参考 | Stage6 订单、E03、FCD 归档/统计表 | **HOLD（0/4 本地原件字节）** | 非 V5 新订单放行前提 |
| S07 正式全路网 | V5 全 A/B/C 有向路网、路口转向、68 点真实入口与边界 | **HOLD** | 尚需独立获取与核验 |
| S08/S09/S10/S11 运营量 | 路由、风雨事件、实测或有依据的参数 | **NOT COMPUTED** | S07 数据放行之后 |

## 检查项

- 逐文件长度、Git blob SHA-1、天气 XLSX 对应来源 SHA-256、ZIP CRC。
- 五个月每月 `Weather_Hourly`：四参考位置、小时的有效解析（含 MYT +08/UTC）、重复/越月记录以及期望 4×（744/720）行。
- 五个月每月 `ERA5_Hourly`：记录预期多 4 行（每个点 1 条），输出其真实时间戳；不在证明来源前偷偷删除。
- FCD 全量压缩 CSV：345×3,672 行、节点/小时唯一性、空速/非正速/正常速统计；**不将缺失速度强制设为 0**。
- 旧 A/B：有向边数、长度合法性、边端点是否属于路网节点；这不是 V5 C 区路网审批。

## 当前本地真实结果

`qa/unit_test_actual_log.txt` 为 11/11 测试通过，覆盖实际生成的 OOXML XLSX（2,976 小时行 + 4 边界行）、重复时刻的负例、时区解析、FCD 速度缺失/零值、以及冻结输入 68/82,620/4,590/22,950 的全文件解压哈希复核。

`qa/s07_actual_run/S07_GITHUB_ACTUAL_NUMERIC_QA.json`：本地演示执行只有冻结输入 PASS；原件未挂载，S07 仍为 HOLD。**此结果不是 GitHub Actions 已远程运行的报告。**
