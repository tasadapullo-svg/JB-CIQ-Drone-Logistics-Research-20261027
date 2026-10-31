# CIQ V5 | S08 汽油车 M0 开发与双无人机载重初筛

**实验实况**：82,620 条 V5 冻结合成任务载重分析已真实运行；19/19 算法/核算单元测试通过；正式 M0 路线、时间、燃油/成本/碳排放 **HOLD**。没有修改 V5 原图、节点或任何冻结订单。

## 文件

- `inputs/`：V5 原始 ZIP、正式 68 点和订单原件、参数缺口与物理车辆行程输入契约。
- `code/run_actual_task_screen.py`：实际全量订单逐单筛查。
- `code/m0_multi_order_dispatch.py`：多订单车辆 pickup/dropoff 严格插入启发式。
- `code/m0_petrol_core.py`：共享行程一次性燃油/成本/CO2 账本。
- `code/strict_m0_release_gate.py`：禁止在未有真实路由及燃油参数时输出运营数字。
- `outputs/`：全任务独立筛查 CSV。
- `qa/`：真实统计、完整执行日志、HOLD 清单、测试、哈希。
- `docs/`：正式科研审计报告与剩余 6 阶段工作。

**运行**（Python 3.11+，不依赖第三方包）：Windows 双击 `RUN_WINDOWS.cmd`；其他平台：依次运行 `python code/run_actual_task_screen.py`、`python code/strict_m0_release_gate.py`、`python -m unittest discover -s tests -v`。

**数据边界**：球面最短距离只是地理 QA，不得用于汽车公里数或飞行航路。DJI 30 kg、Wingcopter 4.7 kg 仅为厂商载重技术初筛，绝非已批准的航空运营。输出任务仍为条件性合成需求。
