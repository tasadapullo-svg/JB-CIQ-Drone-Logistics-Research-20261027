# CIQ 无人机物流 SCI｜V2-S06 V3 三分区正式空间输入构建

**内容已实际执行，不是仅给模板。** 读取 `inputs/CIQ_ABC_QGIS322_NEW_COMPLETE_PROJECT_ALL_FILES_V3.zip`，保留原包原字节、只读处理。冻结原始 69 节点 + 121 几何连接，输出 116 UAV 线、5 地面关系线。道路与法规运营状态均不冒充已验证。

## 文件目录

- `inputs/`: 用户原始 V3 完整 ZIP（不覆盖、不编辑）。
- `scripts/build_s06_inputs.py`: 真正读取 GeoPackage 和五张原始 CSV，逐点逐线验收并生成计算输入。
- `requirements.txt`: shapely + pyproj 版本范围；Python 3.9+。
- `outputs/data/`: 69 点主表、19 候选旧新 ID 对照、116 UAV 候选、5 地面交接关系、69 点道路/空域 HOLD 表、37 历史未修复 OD 关联表。
- `outputs/geojson/`: 69 点、116 UAV 与 5 地面参考，真正从源几何生成。
- `outputs/qa/`: 真实输入哈希、来源登记与机器可读验收门槛。
- `tests/`: 14 个基于实际上传 V3 数据的自动 QA，含误分类阻断测试。
- `qa/`: 构建执行日志、测试日志、打包校验和文件 SHA256 清单。
- `docs/`: 正式审计、输入数据字典、S07 交接说明。

## Windows 环境运行

从本 ZIP 解压，进入解压后根目录：

```powershell
py -m pip install -r requirements.txt
py scripts/build_s06_inputs.py --v3 inputs/CIQ_ABC_QGIS322_NEW_COMPLETE_PROJECT_ALL_FILES_V3.zip --out outputs --legacy-37 inputs/verified_historical_37_unapplied_OD_exceptions.csv
py -m unittest discover -s tests -v
```

本次额外引用了上一轮 Stage04 的 37 条未应用旧 OD 修复登记，且已在 `inputs/` 内附上其原始 CSV；本包在 `outputs/data/S06_legacy37_road_OD_exceptions_NOT_REPAIRED.csv` 中保留了已产生的核验结果。若不传 `--legacy-37`，主程序仍可独立运行，其余空间输入均可完整重建。

若带旧 OD 文件，可指定：

```powershell
py scripts/build_s06_inputs.py --v3 inputs/CIQ_ABC_QGIS322_NEW_COMPLETE_PROJECT_ALL_FILES_V3.zip --out outputs --legacy-37 路径\verified_historical_37_unapplied_OD_exceptions.csv
```

## 验收边界

**PASS:** 节点、真实几何、源文件哈希、分型隔离、候选旧新 ID、GeoJSON 导出。  
**CONDITIONAL GO:** S07 节点空间参照和天气/道路挂接框架。  
**HOLD:** 旧 19 点跨包坐标复核、实际 OSM 地面可行驶路由、当前 CAAM/CAAS 生效空域、获批起降地块与真实机型绝对能源与碳排放主实验。

本项目属于**条件性 SCI 仿真**，无需把获得航空经营许可作为理论情景模型开发的前提；但没有这类证据时，任何实际部署合法性、真实载重能耗或现实已实现的减排结论都不能发布。
