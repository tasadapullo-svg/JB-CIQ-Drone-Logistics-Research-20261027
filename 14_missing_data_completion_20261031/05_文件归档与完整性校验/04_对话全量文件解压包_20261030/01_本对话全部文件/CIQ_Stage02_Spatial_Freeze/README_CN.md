# CIQ Stage 02 — 三分区空间网络验收与冻结预检包

**当前裁定：HOLD — 尚无最新真实 QGIS 三分区工程及全部矢量依赖，未批准新计算。**

## 使用顺序

1. 在 QGIS Desktop 3.22.4 中打开**最新**三分区工程，确认所有本地矢量图层有效；**不要把旧 GitHub GIS 当成新工程**。
2. 将本包 `scripts/stage02_qgis_console.py` 放到 Windows 可访问的位置。在 QGIS 菜单 `插件/Plugins → Python Console`（通常 Ctrl+Alt+P）中执行：

   ```python
   exec(compile(open(r'D:\CIQ\stage02_qgis_console.py', encoding='utf-8').read(), r'D:\CIQ\stage02_qgis_console.py', 'exec'))
   ```

   将路径换成脚本实际所在位置；运行时不保存或修改 QGIS 工程。默认结果写入 `Documents/CIQ_Stage02_Audit`。如需指定位置/历史 CSV，可在 QGIS Console 先执行：

   ```python
   import os
   os.environ['CIQ_STAGE02_OUT'] = r'D:\CIQ_AUDITS\Stage02'
   os.environ['CIQ_LEGACY_19_CSV'] = r'D:\CIQ\historical\19_site_reference_anchors_NOT_LAUNCH_PADS.csv'
   ```

   **仅当该历史 CSV 确实存在时**填写第二行；不要用空模板冒充历史 19 点。
3. 程序导出图层清单、全部候选点/线、端点差距、标签状态、源文件哈希、旧新节点映射、问题清单及 `07_stage02_spatial_gate.json`。
4. 把 `Documents/CIQ_Stage02_Audit` 文件夹压缩连同**真实 QGIS 工程和所有本地依赖矢量数据**提供用于后续审核；不需上传天地图缓存或密钥。
5. 如只想先核对项目是否齐全，可在 Windows 系统 Python 中执行：

   ```powershell
   py -3 scripts\stage02_offline_precheck.py --project "D:\CIQ\latest\your_project.qgz" --search-dir "D:\CIQ\latest" --out "D:\CIQ_AUDITS\Stage02_offline"
   ```

   离线预检只能验 QGIS XML、图层引用文件与 SHA256；**不能替代** QGIS Python Console 的真实几何检查。

## 必须注意

- 该工具保守地将具备可识别 ID/区域字段或物流层名称的点、线归为**候选**；不自动认定它们都是配送站或合法航路。若实际字段使用其他命名，请记录后补充规则；不能默默丢弃。
- 连线端点 50m 检查仅为几何 QA 阈值，**不是 UAV 航线安全缓冲或监管标准**。
- `A_N05`、`A_N07`、`C21`、`A_C03` 单列复核；缺失不意味着应擅自添加。
- A/B/C 三分区仍需对应 Causeway、Second Link 与新增分区的实际研究定义，不可仅按 ID 前缀猜测。
- WMP228、WMKJ CTR、CAAM、CAAS、跨境事项另立权威资料和有效日期登记；参考线不是许可航线。
- 历史 Stage 3–8 仅供方法和结果对照；旧 19 参考点、旧 91/128 有路 OD、旧电动车和通用 UAV 电耗不直接进入新的运算。
- 所有自动输出的科学计算开关固定为 FALSE。研究者需对有效空间图层、版本/哈希、气象与交通的统一任务模型签署审核后，才能进入后续重算。

## 文件

- `scripts/stage02_qgis_console.py` — QGIS 3.22+ 内置 Python Console 逐要素验收工具（本容器没有 QGIS 运行时，未在真实 QGIS 中执行）。
- `scripts/stage02_offline_precheck.py` — QGS/QGZ 与图层来源只读预检（在当前容器已执行）。
- `results/actual_current_workspace/` — 对当前可访问文件实际执行的 HOLD 证据。
- `results/synthetic_test_console.txt` — 4 项**合成**测试，不能当作真实地理结果。
- `templates/` — 严格为零行/待签批的 nodes/edges/crosswalk、数据输入白名单和 Fig.1–7 数据契约。
- `STAGE02_PRELIMINARY_AUDIT_20261030.md/.docx` — 正式预审结论。
