# V2.1 SCI方法复审包 — 如何交给 ChatGPT Work

本包仅修订 **V2 实验实施方法与验收要求**，不含新仿真结果、不改变旧 GitHub、也没有擅自认证最新QGIS工程。

1. 在 ChatGPT 里切换到 Work 模式（若当前账户可用），将旧 V2 总工程ZIP和本 V2.1 方法审查 ZIP 作为附件；或连接 GitHub 仓库供其审查。若要直接访问本地QGIS，提供完整QGZ/QGS和全部外部图层，或使用有文件访问能力的桌面Work工作流。
2. 将 `WORK_MODE_MASTER_PROMPT_CN.md` 作为 Work 主任务描述；要求先报告缺失/证据等级和分支/PR方案，勿覆盖旧历史结果。
3. `SCI_METHOD_REVIEW_CN.md` 记录审查论证；`control/amendment_register.json` 是优先级和验收映射；`stages/` 目录为按 V2-S06…S12 分类的具体补强动作。
4. `MODEL_SCI_QA_TESTS.md` 是新增求解器必须通过的真运行测试，不等同旧工程的字段预检。
5. 每一个阶段在人工签署PASS之前都允许独立整理证据、构建情景参数边界，但不运行依赖未满足的下游正式实验。每个阶段给 ZIP、输入manifest、原始结果、源代码、hash、可重跑说明。

建议先从 S06 真 QGIS和 S08汽油基线证据、S09两机型能耗的并行证据调查开始，随后冻结 S07 统计抽样和 S10 调度计算口径。
