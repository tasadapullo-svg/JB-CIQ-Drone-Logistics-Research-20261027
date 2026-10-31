# CIQ 研究 V2-S07：真实数据部分执行工程（2026-10-30）

## 定位

这是从用户 V3 原始 QGIS 和 S06 真实输出开始运行的**部分实数据构建工程**，而不是 S07 的完整天气—道路—订单融合结果，更不是已完成的汽油车或双无人机仿真。所有数值天气、旧新版订单主表、可行驶道路主图当前均保持 HOLD。没有虚构任何配送时间、油耗和碳排放。

## 内容

- `inputs/`：S06 69 节点、116+5 候选关系、37 旧异常；原始 V3 ZIP；历史 19 点 GitHub 坐标提取表与固定 blob 证据；5 个月天气 QA 提取及 XLSX 文件版本目录核对
- `code/build_s07_partial.py`：真实节点角色、跨版本对照、153天 3,672小时、月 QC、2格候选审计、空值天气模板、37异常阻断、输入来源及释放门槛、SHA256
- `code/recover_pinned_github_sources.py`：网络可用时从**固定提交**恢复实际 XLSX/历史道路/旧订单；SHA-1 Git blob 内容验证和 SHA-256
- `outputs/`：脚本真实生成的 9+ CSV / JSON
- `qa/`：自动测试日志、外部原件存在性检查、逐文件摘要及阶段释放状态
- `docs/`：科学解释与执行边界
- `tests/`：14 个自动化测试（读取实际 S06 数据而非伪造业务结果）

## 复现

在解压工程根目录执行：

```powershell
python code/build_s07_partial.py --root .
python -m unittest discover -s tests -v
python code/recover_pinned_github_sources.py --out external_sources
```

在**可联网的** Windows 电脑上恢复外部文件（本次当前沙盒网络不通，未执行下载）：

```powershell
python code/recover_pinned_github_sources.py --out external_sources --download
```

核对 `external_sources/github_source_validation.json`，只有 `PASS_GITHUB_BLOB_IDENTITY` 的文件可进入下一层行列与数值 QC。GitHub 文件是否与此前历史质量摘要一致必须另验；两者文件大小当前确有差异。

## 决定

- **GO**：V3 69 节点静态引用、角色/连接分类、19点 ID冲突筛查、五个月时区时间轴、月天气历史QC元数据
- **HOLD**：原始逐小时天气值、法定可行驶路网、69节点合法道路出入口、C区订单生成、旧单自动迁移、机型运营气象、正式 M0/M1/M2 减排结论

**如需提交论文结果，只能使用实际校验过的数值输出，不能使用本包中空值时间索引替代气象观测。**
