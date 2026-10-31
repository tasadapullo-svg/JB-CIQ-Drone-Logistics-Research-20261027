$ErrorActionPreference = 'Stop'
$StudyRoot = 'C:\Users\DELL\Desktop\CIQ 无人机物流 SCI 研_20261026'
$GitHubRoot = 'C:\Users\DELL\Desktop\CIQ_Drone_Logistics_SCI_GitHub_20261028'
$Graph = Join-Path $StudyRoot 'output_S07_S08_Codex_20261030\S07\road\V5_ABC_DRIVE_DIRECTED_OSM_SNAPSHOT_NOT_HISTORICAL.graphml'
py (Join-Path $StudyRoot 'output_S07_S08_Codex_20261030\S07\code\run_s07_full.py') --root $StudyRoot --github $GitHubRoot --out (Join-Path $StudyRoot 'output_S07_S08_Codex_20261030\S07') --graphml $Graph
py -m unittest discover -s (Join-Path $StudyRoot 'output_S07_S08_Codex_20261030\S07\tests') -v
