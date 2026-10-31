# S09 两机型任务级条件性仿真审计报告

本阶段对 82,620 个冻结任务分别计算 DJI FlyCart 30 与 Wingcopter 198 Cargo，共 165,240 条机型—任务记录。结果是候选任务层，不是获批飞行或已调度架次。

## 主情景结果

{
  "DJI_FLYCART30": {
    "rows": 82620,
    "geometry_candidates": 28477,
    "payload_pass": 82620,
    "technical_feasible": 27191,
    "weather_relaxed_pass": 24281,
    "weather_strict_pass": 2631,
    "conditional_schedule_eligible": 23161,
    "grid_kwh_eligible_main_scenario": 43023.889465736574,
    "energy_evidence": "OEM_NOMINAL_RANGE_EQUIVALENT_PLUS_SCENARIO_RESERVE"
  },
  "WINGCOPTER198_CARGO": {
    "rows": 82620,
    "geometry_candidates": 28477,
    "payload_pass": 55080,
    "technical_feasible": 19009,
    "weather_relaxed_pass": 24349,
    "weather_strict_pass": 2631,
    "conditional_schedule_eligible": 16233,
    "grid_kwh_eligible_main_scenario": 19213.41795013333,
    "energy_evidence": "SCENARIO_PROXY_NOT_AIRCRAFT_CALIBRATION"
  }
}

DJI 能量采用官方双电池名义容量与无风测试航程的“名义航程当量”推导，并加入20% reserve与90%充电效率情景；这不是任务实测。Wingcopter缺少公开的任务电池kWh和载荷—能耗曲线，主情景采用0.10/0.08 kWh/km载货/空返代理，并提供0.05–0.20 kWh/km敏感性。因此绝对碳排放与机型优劣仍为 HOLD。

天气使用S07逐时ERA5代理，检查起飞和预计返航所落小时；10m风向按气象学“来向”转换迎风/横风。55,080任务带>10km空间警示：严格情景为HOLD，放宽情景仅用于条件性计算。0.5mm/h降雨门槛是研究情景，不是认证飞行包线。

116条V5候选线均为几何代理，不是批准航路；WMP228仅按V5参考圆筛查，全部场地权属、起降许可、其他空域、BVLOS与实际NOTAM仍未验证。`conditional_schedule_eligible`只表示技术/天气代理情景可进入S10，不表示合法可飞。
