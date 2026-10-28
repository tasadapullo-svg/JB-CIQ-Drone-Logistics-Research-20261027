# 道路与CIQ外部校准报告

## 状态

`NOT_CALIBRATED`

仓库没有Causeway/Second Link、双方向、2026年5–9月逐小时的CIQ等待观测。官方LTA来源提供实时交通图像和当前速度带；ICA公开材料提供事件级拥堵描述，但没有与现有OD、小时和方向可一一匹配的等待分钟序列。

因此：

- MAE、MdAE和SMAPE不计算，保持空值，而不是报告零误差。
- `ciq_wait_parameter_scenarios.csv`只建立参数接口，不填低/基准/高分钟数。
- 道路行驶时间与CIQ等待在schema中分离。
- 当前128个参考OD均为口岸周边境内OD，不跨越CIQ，CIQ等待对这些OD标记为不适用。
- 未来跨境OD必须另建方向明确的路线与口岸事件，且不得把道路拥堵代理和CIQ排队重复计入。
