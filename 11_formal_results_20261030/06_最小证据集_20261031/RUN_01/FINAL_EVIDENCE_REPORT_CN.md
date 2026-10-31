# 最小必要补充实验最终证据报告

## 模块 A：联合稳健性

状态：**PASS**。实际完成 900 个分层配对场景、13 组联合参数、5 种模式，共 58,500 条场景—配置—模式记录（每组每模式 16,200 张订单）。所有涉及 DJI/Wing 能耗变化的情景均重新执行任务资格、SOC、调度与地面回退；汽油倍率只在已验证路线和事件不变时重算燃油账本。基准复现与路线不变性检查均为 True / True。

M2-Wing 在基准子样本相对 M0 的运营排放代理变化为 -3.527%（负值表示降低；双向日期/种子聚类自助法 95% CI：-4.087% 至 -2.988%）。13 组中减排幅度范围为 2.416%–4.341%；非正减排（优势反转）配置：无；低于 1% 配置：无。满足完成率≥95%、全订单准时率≥90%后，最低排放模式计数为 {'M2_WING': 13}。该结果是模型内运营排放代理，不是实机、全生命周期或实际运营验证。

## 模块 B：冻结合成订单审计

状态：**CONDITIONAL**。82,620 个唯一订单覆盖 153 天、30 个种子和 4,590 个场景；每场景固定 18 单，每个始发分区固定 6 单。生成器、协议和冻结订单可逐项追溯。订单由“每区 5 个区内 + 1 个跨区压力订单”、离散重量集、离散时窗、均匀目的地和固定随机种子构成，适合相同任务条件下的受控模式比较，但不是 JB/CIQ 的经验需求样本。

主要限制：（1）缺少本地承运商订单量、OD、重量和承诺时窗的实测分布，不能推断市场代表性；（2）三区等量设计会人为均衡空间需求，不能外推真实需求密度；（3）Wingcopter 任务级能耗与电池参数仍缺少可复核的 OEM/实飞证据。因此 Methods 可冻结为“受控合成情景”，Results 只能冻结为条件性模型结论。

## English Methods (reproducible subset)

We evaluated joint parameter robustness on 900 paired scenarios selected from the frozen 4,590 date–seed scenarios. Within each month from May to September 2026, six dates were selected at fixed quantiles of an objective daily stress score: standardized mean wind gust plus standardized rainfall minus standardized observed FCD speed. All 30 frozen random seeds were retained for every selected date, yielding 180 scenarios per month. The same orders were compared across five modes: petrol-only M0, DJI and Wingcopter variants of M1, and DJI and Wingcopter variants of M2.

Thirteen parameter configurations combined petrol fuel-intensity multipliers G and aircraft mission-energy multipliers D and W. Nine configurations formed a 3 × 3 grid with G in {0.8, 1.0, 1.2} and equal D=W in {0.8, 1.0, 1.2}; four asymmetric corner configurations tested opposite DJI and Wing energy assumptions. Aircraft-energy changes were applied before mission qualification and triggered complete reruns of SOC feasibility, dispatch, timing, and ground fallback. Petrol multipliers were applied to the physical fuel ledger only after confirming identical vehicle kilometres and UAV-flight events within each fixed D/W dispatch pair. Operational emissions were calculated as petrol tank-to-wheel CO2 plus grid-input electricity multiplied by the frozen grid factor. These are operational proxies and exclude vehicle manufacture, infrastructure, and full fuel-cycle effects.

For each configuration and mode, we reported completion, all-order on-time performance, delivery time, vehicle kilometres, fuel, electricity, partial operating cost, and operational greenhouse-gas proxy. Percentage effects were paired against M0 by date and seed. Uncertainty intervals used 5,000 two-way cluster-bootstrap replicates that independently resampled dates and seeds. A mode was service-feasible only when completion was at least 95% and all-order on-time performance was at least 90%. Synthetic-order provenance was independently audited against the frozen generator and protocol; the resulting demand is treated as a balanced controlled experiment, not an observed or population-representative parcel-demand sample.
