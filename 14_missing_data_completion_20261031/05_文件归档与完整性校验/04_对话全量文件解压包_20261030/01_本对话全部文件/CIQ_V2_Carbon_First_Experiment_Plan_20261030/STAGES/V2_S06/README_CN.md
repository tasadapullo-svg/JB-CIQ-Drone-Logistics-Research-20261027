# V2_S06 — 三分区空间网络冻结 / Spatial network acceptance

- 状态：**HOLD / PLANNED**。本阶段未运行任何正式数值实验。
- 论文对应：RQ1。
- 历史来源只读提交：`4569817b8145efe2ae06f4b21addc1986f971c12`，绝不覆盖旧 Stage 3–8。
- 目前阻断：未取得新版 QGIS 原件。

## 1. 执行步骤（不得跳过）
1. 以最新三分区 QGIS 工程为唯一新版空间源；不得用旧19点替换新版坐标
2. 导出所有点/线/区及原始图层 CRS、稳定 ID、所属国家、证据状态
3. 检查重复 ID、空几何、坐标精度、孤立点、起终点引用和道路接入
4. 叠加 CAAM/CAAS 适用空域、禁飞/待审批分层与边界；不得把直线候选当合法航线
5. 完成历史19点→新点 ID 对照（保留 deleted/new/modified）；冻结源文件哈希

## 2. 输入数据和证据

| 输入文件 | 格式 | 要求 |
|---|---|---|
| `qgis_project_bundle.zip` | ZIP | 最新 QGIS QGZ/QGS 与全部本地依赖；不得只提交地图图片 |
| `nodes.csv` | CSV | 完整新版节点清单 |
| `edges.csv` | CSV | 完整新版候选连接与类别 |
| `spatial_screen.csv` | CSV | 道路接入及空域/场地证据分类 |
| `legacy_crosswalk.csv` | CSV | 历史节点与新版节点关系 |

填写 `INPUT_REGISTER.csv` 的实际源路径/校验信息，放入本阶段 `inputs/`。数据模板仅含列名，不得当实际数据使用。

## 3. 预期产物
- `nodes_checked.csv`：可核验节点及空间证据
- `edges_checked.csv`：可核验连接及端点
- `spatial_exclusions.csv`：硬排除/待审批/情景适用分别编码
- `spatial_freeze.json`：CRS/输入 SHA/统计/人工验收签核

## 4. 放行检查
- [ ] 每条 node_id 唯一且坐标有效
- [ ] 每条 edge 的起终点存在
- [ ] CRS 与跨国边界口径明确
- [ ] 所有未知审批保留 UNKNOWN，不自动通过
- [ ] 空间输入哈希+版本冻结、人工认可

## 5. 独立验收方法

项目根目录执行：

```bash
python tools/verify_stage.py --root . --stage V2_S06
python tools/generate_sha256_manifest.py --directory STAGES/V2_S06 --output STAGES/V2_S06/SHA256_MANIFEST.csv
```

自动检查仅代表输入文件**结构有效**。`QA_GATES.csv` 里的 BLOCKED 不会被自动变成真实科学验收 PASS。

## 6. 上传 GitHub

将本阶段目录连同 `tools/`、`protocol/`、`references/` 上传至：`11_v2_carbon_first_experiments/V2_S06/`（建议新目录）；**不要覆盖**旧 `10_experiment_results/` 归档。

**论文声明边界：** 未取得新版 QGIS 原件。
