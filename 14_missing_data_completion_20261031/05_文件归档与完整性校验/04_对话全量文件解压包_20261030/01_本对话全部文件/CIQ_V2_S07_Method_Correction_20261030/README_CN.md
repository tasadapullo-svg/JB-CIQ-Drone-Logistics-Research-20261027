# V2-S07 方法补缺与开工核验交付包

**请先读** `docs/S07_FORMAL_METHOD_REVIEW_CN.md`，再查看 `records/S07_V2_2_REVISED_CONTRACT.json`。

- 本包不是正式 S07 天气/路网/任务融合结果，**没有编造任何订单、道路距离、天气或减排数值**。
- 本包的运行审计基于现有 S06 的实际 69 节点、116 UAV 候选线、5 地面参考线及 37 旧异常 OD 登记。运行结果存于 `qa/`。
- 标准库脚本 `code/preflight_s07.py` 只读、不修改输入目录。需要实际 S06 输出目录：

```bash
python code/preflight_s07.py \
  --s06 /path/to/CIQ_V2_S06_V3_Input_Build_20261030 \
  --output ./qa/new_run
```

若将来实际 S07 数据放在某个目录，再传 `--s07-input /path/to/S07/inputs`。文件存在仅能通过**来源存在检查**，不代表科学 QC 通过，必须执行完整字段/覆盖率/路由/订单验收。

- 测试命令：`CIQ_S06_ROOT=/path/to/s06 python -m unittest discover -s tests -v`（Windows 可以先设置环境变量）。
- GitHub 建议路径：`11_v2_carbon_first_experiments/V2_S07/review_20261030/`；不覆盖旧 `10_experiment_results`。
- 本阶段必须先解决 S06→S07 的真实天气/道路数据挂接与需求总体来源，才能进入正式运营模拟。
