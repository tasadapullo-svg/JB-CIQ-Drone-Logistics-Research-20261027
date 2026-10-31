# CIQ Stage 00/01 R2 验收包使用说明

本包是 **SCI 实验输入冻结/历史数据迁移的预验收工具**，不是重新仿真结果。

## 你现在可以做什么

在 Windows 上，将最新 QGIS 工程及它引用的所有图层整理在同一可读取目录（或保证图层绝对路径确实可用）；同时保留 GitHub 历史仓库的原样只读副本。修改 `RUN_R2_ON_WINDOWS.ps1` 开头路径并运行。

命令（可以省略 `--old-nodes`，但对照表会保持未完成）：

```powershell
py -3 r2_qgis_crosswalk.py --qgis "D:\CIQ\最新三分区.qgz" --old-nodes "D:\CIQ\legacy_19nodes.csv" --out "D:\CIQ_AUDITS\R2_crosswalk"
```

当只想看阻断报告、尚无新 QGIS 时：

```powershell
py -3 r2_qgis_crosswalk.py --out "D:\CIQ_AUDITS\R2_missing_source_check"
```

**退出码 2 是 HOLD 的预期行为。** 不要将其改成 0 伪装为全部通过。

## 文件内容

- `CIQ_Stage00_01_R2_Formal_Audit_20261030.docx`：第二轮正式审计报告。
- `R2_release_gates.csv`：13 项释放门槛。
- `historical_stage3_8_lineage.csv`：13 组历史阶段谱系。
- `R2_old_to_new_parameter_boundary.csv`：哪些旧参数不可直接迁移。
- `R2_input_register_DENY_ALL.csv`：活动计算输入默认禁止清单。
- `r2_qgis_crosswalk.py`：只读 QGIS 图层、GeoPackage、节点、候选线、旧新 ID 核查。
- `stage00_01_local_auditor_R1.py`：只读历史仓库全文件 SHA-256 和 QGIS 图层初检。
- `tests/test_r2_qgis_crosswalk.py`：合成单元测试，非真实 SCI 数据。
- `no_new_qgis_proof/`：在当前容器未取得真实 QGIS 时的阻断记录。

## 注意事项

程序对 GeoPackage 中具有可识别字段的点/线层进行自动枚举；Shapefile、GeoJSON 和特殊字段模式仍需通过 QGIS 验证及扩展，不能把自动枚举的数量等同全网真实数量。QGIS 背景在线地图不等于空间输入失败，人工复核其来源即可。任何实际放飞和跨境运营都必须另行满足监管、场站和国境要求。本包不会发出自动 PASS，也不会重新计算天气、道路或碳排放。
