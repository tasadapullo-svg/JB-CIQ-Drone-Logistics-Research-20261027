# CIQ V2 低碳地空物流 SCI 后续实验总控（2026-10-30）

## 核心决定

**只围绕：汽油车 M0 对比；M1 固定接驳与 M2 车辆—无人机协同；天气/交通/成本约束下的运营 CO₂ 最小化。** 旧 Stage3–8 只读；V2 工作目录单独建立。不宣称当前已有新数值实验结果。

- 最新 GitHub 主分支版本：`4569817b8145efe2ae06f4b21addc1986f971c12`（2026-10-28 上传的历史版本）。
- 现有 Stage05 仅冻结方法；实际燃油油耗、两机型任务能耗、三分区 QGIS 原件仍缺。
- 主要订单候选：旧 Stage6 29,842 条合成订单、30个seed、5个日期，前提是新 GIS 可以逐笔映射；旧 Stage2 918,000 是不同的重采样夹具，**绝不合并**。
- 不把五个固定日混称为整个 5 月到 9 月运行结果。
- 研究对象以马来西亚—新加坡 CIQ 物流 **条件性研究** 呈现；旧128条OD全部非跨境，不得捏造跨境物流的已测结果。

## 执行顺序与研究问题

| 次序 | 阶段 | 研究工作 | 主要 RQ |
|---|---|---|---|
| 1 | `V2_S06` | 三分区空间网络冻结 | RQ1 |
| 2 | `V2_S07` | 任务—气象—交通同口径冻结 | RQ1,RQ2 |
| 3 | `V2_S08` | 汽油车纯道路 M0 基线 | RQ2,RQ3 |
| 4 | `V2_S09` | 双无人机能耗—天气—航路审计 | RQ1,RQ2,RQ3 |
| 5 | `V2_S10` | M1/M2 混合物流统一仿真 | RQ2,RQ3 |
| 6 | `V2_S11` | 运营碳排放—成本与最小碳优化 | RQ3 |
| 7 | `V2_S12` | 统计、敏感性与 SCI 图表定稿 | RQ1,RQ2,RQ3 |

## 核心对照（最小实验矩阵）

同一任务样本，分别对 M0 汽油车、M1-DJI、M1-Wingcopter、M2-DJI、M2-Wingcopter。柴油 M0 仅作敏感性，不能顶替汽油车。风险/天气/道路/能源的扩展只作解释因子，不扩大主研究问题。

## 最终 SCI 结论允许的类型

1. RQ1：已证实几何候选及条件性可达网络；不可直接称政府批准的部署位置。
2. RQ2：按同批任务量化时间、准时率、天气和拥堵条件下适用性；不将三模式不同任务分母相除。
3. RQ3：在服务/准时/成本约束下找运营 CO2 最低的方案；若不存在成本和服务均不劣的方案，则如实报告“没有可行净减排方案”。

## SCI 统计与样本边界

30 seed 为历史试验统计重复单位。任务数量和 mode 级记录不能伪装为独立实测样本。时间窗口固定5日期不是5个月每天实验。先做审计小样本，再做30-seed成对主试验，最后多因素联合不确定性。

## GitHub 上传目录建议

`11_v2_carbon_first_experiments/`。每个节点目录含 README、合同、输入模板、QA 门槛、输出注册和状态记录；每节点另附 ZIP。无需覆盖旧 `10_experiment_results/`。

## 如何执行检查

```bash
python tools/verify_stage.py --root . --stage V2_S06
python tools/verify_stage.py --root . --stage V2_S07
python tools/verify_stage.py --root . --stage V2_S08
python tools/verify_stage.py --root . --stage V2_S09
python tools/verify_stage.py --root . --stage V2_S10
python tools/verify_stage.py --root . --stage V2_S11
python tools/verify_stage.py --root . --stage V2_S12
```

**当前预期为 HOLD，不是脚本失败。** 缺原始数据时，工具应返回阻断明细，严禁虚构结果。

## 主要文件

- `protocol/MASTER_PROTOCOL_V2.json`：全局科学边界
- `control/EXPERIMENT_MATRIX.csv`：五模式+敏感性 11 组实验设计
- `control/MASTER_RELEASE_GATES.csv`：17 项跨阶段放行门槛
- `control/SCI_FIGURE_LINKAGE.csv`：与 Fig1/3/4/5/6/7 一一对应
- `references/SOURCE_REGISTER.csv`：官方来源及证据类型
- `tools/verify_stage.py`：输入结构和文件哈希检查（不自动给科学签字）
- `tools/validate_paired_results.py`：成对任务与 mode 分母审计
- `tools/generate_sha256_manifest.py`：上传前生成逐文件哈希
- `STAGES/V2_Sxx`：每个里程碑步骤、输入/输出模板和验收登记

**注意**：模板 CSV 只有列名，没有真实实验值；任何 0/空字段不代表实际零消耗或零成本。
