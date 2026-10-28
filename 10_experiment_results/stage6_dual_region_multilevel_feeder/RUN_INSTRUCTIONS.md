# Stage 6运行说明

## 环境

- Python 3.10或更高版本。
- 核心M0/M1/M2仿真、敏感性分析和QA仅使用Python标准库。
- 重新生成Excel报告需要Codex工作区提供的 `artifact_tool`；不影响CSV、JSON和压缩结果复算。

## 解压后的必要文件

- `CIQ_GPT校验所需三归档与关键数据_20261027.zip`
- `run_stage4_dispatch.py`
- `run_stage6.py`
- `run_stage6_sensitivity.py`
- `qa_and_report.py`

这些文件应位于同一 `Stage6` 文件夹中。

## 执行顺序

```powershell
cd Stage6
py run_stage6.py
py run_stage6_sensitivity.py
py qa_and_report.py
```

可选：重新生成Excel工作簿。

```powershell
py create_stage6_xlsx.py
```

如果输入包不与脚本位于同一目录，可设置：

```powershell
$env:CIQ_BUNDLE = "D:\path\CIQ_GPT校验所需三归档与关键数据_20261027.zip"
py run_stage6.py
```

## 主要输出

- `stage6_order_level.csv.gz`：30种子逐订单三模式结果。
- `stage6_area_summary.csv`：区域和模式汇总。
- `stage6_daily_modes.csv`：日级模式台账。
- `stage6_service_matched.csv`：同服务边界比较。
- `stage6_linehaul_batches_B.csv`：B区批量干线记录。
- `stage6_seed_paired.csv`、`stage6_seed_uncertainty.csv`：种子配对和区间结果。
- `stage6_QA.json`、`stage6_verified_tests.json`：验收状态。

运行时不得把情景参数改写为实测值，也不得把内部一致性测试解释为航空许可或外部校准。
