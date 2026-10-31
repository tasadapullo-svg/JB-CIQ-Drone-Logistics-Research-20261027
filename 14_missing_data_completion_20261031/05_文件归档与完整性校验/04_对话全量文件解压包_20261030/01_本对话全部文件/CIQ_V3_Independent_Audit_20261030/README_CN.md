# V2-S06 | 2026-10-30 V3 QGIS 独立数据验收包

本包使用用户实际上传的 `CIQ_ABC_QGIS322_NEW_COMPLETE_PROJECT_ALL_FILES_V3.zip`，对 69 节点、121 条几何线、19 图层及完整性做真实离线审计。**不要把它称为已经完成的 S06 最终监管/运营验收。**

- 先读 `V3_Spatial_Input_Formal_Audit_CN.md`；独立源输入在 `inputs/ORIGINAL_V3_USER_UPLOAD.zip`，SHA256 与报告相符。
- 下载后可用系统 Python（建议安装 `geopandas`, `pandas`, `pyproj`, `shapely`）执行报告内的两份审计脚本。审计脚本当前示例采用绝对工作目录，需要在你自己的计算机按目录位置修改 `ROOT`, `OUT`, `Z`。
- 新 GIS 输入为研究参考网络，不能直接用于计算实际车辆道路里程、已许可飞行或真实运营碳减排。
- GitHub 建议以 `11_v2_carbon_first_experiments/V2-S06/` 单独归档。原始 QGIS 数据只读。
