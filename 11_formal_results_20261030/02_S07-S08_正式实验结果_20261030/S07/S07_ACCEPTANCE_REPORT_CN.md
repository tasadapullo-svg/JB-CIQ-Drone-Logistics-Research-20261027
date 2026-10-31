# S07 真实数据验收报告

- G07-W：**CONDITIONAL**；五个月 Weather_Hourly 共 14,688 行，ERA5 有效 grid-hour 7,344 行，边界记录 20 行。
- G07-R：**CONDITIONAL**；FCD 1,266,840 行，正速度 1,141,555，缺失 125,230，非正 55。
- G07-INTEGRATION：**CONDITIONAL**；保留订单 82,620，场景 4,590。
- S07 总裁定：**CONDITIONAL**。仅允许 S08 以条件性情景运行，不代表实际道路、入口或方向交通已经验证。

## 科学限制

- ERA5 is reanalysis and only two returned grid cells represent 68 nodes
- 31 nodes exceed the 10 km weather-proxy warning threshold
- FCD has no observed direction and its km/h unit is conditional on TomTom default
- current OSM is not a May-Sep 2026 historical snapshot
- road entrance legality, turn restrictions and cross-border permissions are unverified
