# E02 交接备注：由 GPT 继续校验与完成剩余步骤

## 当前完成情况

本包已使用真实 OpenStreetMap Overpass 数据完成以下工作：

- 下载 A（Causeway）和 B（Second Link）两个固定窗口的原始 OSM JSON，并保存下载端点、UTC 时间和 SHA256。
- 根据 OSM `oneway`、环岛及道路标签构建有向道路边、道路节点和 GeoJSON。
- 生成 FCD 点到 OSM 道路边的几何候选，但没有自动批准道路名称或行驶方向。
- 对 128 个参考方向 OD 运行初步模型路由，并生成道路距离、模型时间、连通性和异常清单。
- 复核路径长度不小于测地线距离；合成单行线逆行测试通过。
- 生成阶段验收报告、机器可读摘要和全工程 SHA256 清单。

当前状态为：

`E02_PRELIMINARY_OSM_NETWORK_BUILT_FORMAL_ACCEPTANCE_BLOCKED`

当前 91/128 个参考方向 OD 有模型路径，37 个没有有效模型路径或站点吸附超过 100 m。正式 `OBSERVATION_CALIBRATED` OD 数量为 0。

## GPT 必须继续完成的校验

1. **补齐 345 个 FCD 节点的道路覆盖**
   - 当前固定 A/B 下载窗口只覆盖 214 个节点，131 个节点位于两个窗口之外。
   - 不得丢弃窗口外节点，也不得在没有冻结范围说明时擅自扩大研究区域。
   - 先确认这些节点应归入 A、B，还是仅用于区域外交通背景，再按确认范围补充真实 OSM 数据。

2. **逐点确认 FCD 道路与行驶方向**
   - `E02_{A/B}_FCD_to_OSM_edge_CANDIDATES_NOT_APPROVED.csv` 只是最近边候选。
   - 必须结合道路名称、节点顺序、道路中心线、车道方向或其他外部证据确认 OSM way ID 和方向。
   - 未确认方向的 FCD 速度不得同时赋给正反两个方向。

3. **马来西亚法定边界与越境道路检查**
   - 当前矩形窗口不是法定国界。
   - 取得可追溯的马来西亚边界数据，记录来源、版本、下载时间和 SHA256。
   - 检查每条 OD 路径是否进入新加坡；不符合研究口径的越境道路必须排除或单独标记。

4. **OSM 转向限制**
   - 当前路由没有解析 `type=restriction` relation。
   - 下载并解析研究范围内的 `no_*`、`only_*` 等转向限制，重新计算受影响路径。
   - 保存限制 relation ID、涉及的 from/via/to 元素以及应用结果。

5. **异常路径和正反向差异**
   - 先处理 `outputs/E02_OD_route_anomalies_REVIEW_REQUIRED.csv`。
   - 核查断路、站点吸附、道路入口、异常绕行、环岛和单行线。
   - 路径修正必须来自真实道路或更可靠的接入点证据，不得创建直线伪道路。

6. **逐小时 FCD 交通标定**
   - 现有交通表有 1,266,840 条节点小时记录和 345 个节点，但没有行驶方向字段。
   - 只有在道路边和方向完成批准后，才能将 FCD 速度映射到相应有向道路边。
   - 明确缺失值、非正速度、无观测道路和模型速度回退规则，并报告每条 OD 的 FCD 观测长度覆盖率。

7. **独立导航时间验证**
   - 提供独立导航来源、查询日期时间、交通条件和样本 OD。
   - 将导航距离/时间与模型路径逐项比较，报告偏差和接受标准。
   - OSM 同源的公共路由服务只能作为程序交叉检查，不能单独视为完全独立的交通时间证据。

8. **正式放行与重新归档**
   - 只有国界、转向限制、FCD 方向、道路匹配和独立导航时间全部通过后，才允许将结果标记为 `OBSERVATION_CALIBRATED`。
   - 重新生成正式 OD 矩阵、QA 汇总、异常清单、运行日志和 SHA256 清单。
   - 保留当前模型结果，不覆盖原始 OSM JSON和原始 FCD 数据。

## 继续运行的基础命令

在工程根目录执行：

```powershell
py -m pip install -r requirements.txt
py code/e02_roadnet.py preflight --registry inputs/FCD_345_frozen_registry.csv --sites inputs/19_site_reference_anchors_NOT_LAUNCH_PADS.csv --out outputs
py tests/independent_logic_test.py
```

已有 OSM 原始响应可直接用于复算，不需要重复下载：

```powershell
py code/e02_roadnet.py build --area A --input outputs/OSM_A_overpass_response.json --registry inputs/FCD_345_frozen_registry.csv --sites inputs/19_site_reference_anchors_NOT_LAUNCH_PADS.csv --out outputs
py code/e02_roadnet.py build --area B --input outputs/OSM_B_overpass_response.json --registry inputs/FCD_345_frozen_registry.csv --sites inputs/19_site_reference_anchors_NOT_LAUNCH_PADS.csv --out outputs
```

## 建议给 GPT 的任务说明

请从 `outputs/E02_stage_acceptance_summary.json` 和 `outputs/E02_stage_acceptance_report.md` 开始，逐项完成本文件列出的剩余证据门槛。不得把 OSM 道路等级速度或未批准的最近边匹配写成 FCD 实测结果；不得把 19 个参考点写成已经批准的物流站点或真实订单；不得扩大到 E03–E08。

