$ErrorActionPreference = 'Stop'
$StudyRoot = 'C:\Users\DELL\Desktop\CIQ 无人机物流 SCI 研_20261026'
$Tasks = Join-Path $StudyRoot '下载CIQ无人机物流SCI--本对话全部文件更新总ZIP\01_本对话全部文件\CIQ_V5_S07_Actual_QA_Gates_20261030\inputs\S07_V5_SYNTHETIC_TASKS_CONDITIONAL_DESIGN.csv'
$S07 = Join-Path $StudyRoot 'output_S07_S08_Codex_20261030\S07'
$Prices = Join-Path $StudyRoot 'output_S07_S08_Codex_20261030\shared\fuelprice_data_gov_my.csv'
$Output = Join-Path $StudyRoot 'output_S07_S08_Codex_20261030\S08\data'
py (Join-Path $StudyRoot 'output_S07_S08_Codex_20261030\S08\code\run_s08_petrol_m0.py') --s07 $S07 --tasks $Tasks --prices $Prices --out $Output
py -m unittest discover -s (Join-Path $StudyRoot 'output_S07_S08_Codex_20261030\S08\tests') -v
