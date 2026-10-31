CIQ A/C/B GIS QGIS 3.22.4 — V4: all 69 node IDs ONLY

【立即打开】
解压整个 ZIP（保留目录结构），双击 CIQ_ABC_69_SHORT_IDS_PORTABLE.qgz。
点位标签仅为节点编码，例如：A01、A_N05、B00、C01、A_P01、G_CIQ；
不显示“ | 完整地名”。原始 full name 字段仍保留于 GeoPackage 供科学核验。

数据和文件:
- QGIS 工程: CIQ_ABC_69_SHORT_IDS_PORTABLE.qgz / .qgs
- GIS 真实坐标与线路: data/CIQ_ABC_FINAL_EDITABLE.gpkg
- 全部节点审计: qa/QA_ALL_69_NODE_LABELS.csv
- 离线节点编号预览: figures/LABEL_QA_*_SHORT_IDS_ONLY_OFFLINE.png
- QGIS 构建/渲染: code/01_BUILD_COMPLETE_QGIS322.py
- 标签修复: code/02_REPAIR_ALL_69_LABELS_IN_OPEN_PROJECT.py

注意:
- 工程路径为相对路径，移动整个目录时保持 data 子目录位置不变。
- 地图底图使用网络 OSM XYZ 瓦片，需要联网；本地 GIS 图层离线可用。
- 工程可直接打开；需要重建布局与 PNG 时才运行构建脚本。
- 在 QGIS 中重新运行 code/01_BUILD_COMPLETE_QGIS322.py 会清空当前打开工程，先保存！
- WMP228 圆是历史敏感性参考，不是可直接作为现行禁飞范围的法律认定。
- 航线是几何候选，不代表已获批 UAV 航线。
- QGIS 3.22.4 真实界面渲染验收需要在用户电脑完成。
