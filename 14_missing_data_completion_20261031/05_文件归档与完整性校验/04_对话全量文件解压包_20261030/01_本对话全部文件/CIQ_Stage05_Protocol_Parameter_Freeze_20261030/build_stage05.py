from pathlib import Path
import csv, json, hashlib, textwrap, os
BASE=Path('/mnt/data/CIQ_Stage05_Protocol_Parameter_Freeze_20261030')
R=BASE/'records'; R.mkdir(exist_ok=True)
DATE='2026-10-30'
SOURCES=[
('SRC01','DJI official specs','https://www.dji.com/flycart-30/specs','manufacturer','Spec page observed 2026-10-30; test-condition limited'),
('SRC02','Wingcopter Cargo specs','https://wsd.wingcopter.com/w198-cargo','manufacturer','Cargo-specific 92 km maximum; not generic W198 94 km'),
('SRC03','IPCC 2006 mobile combustion','https://www.ipcc-nggip.iges.or.jp/public/2006gl/vol2.html','methodology','Vol.2 Ch.3 tables, kgCO2/TJ fuel energy'),
('SRC04','Malaysia EC grid GEF 2022-2024 provisional','https://myenergystats.st.gov.my/documents/d/guest/grid-emission-factor-gef-in-malaysia-2022-2024-provisional-','government','Peninsular 2024 provisional 0.740 kgCO2e/kWh; generation average'),
('SRC05','Singapore NCCS Power / EMA','https://www.nccs.gov.sg/singapores-climate-action/mitigation-efforts/power/','government','Singapore grid 2024 0.402 kgCO2/kWh; CO2 not full CO2e'),
('SRC06','Singapore EMA GEF definition','https://www.ema.gov.sg/resources/faqs/statistics/carbon-emissions/what-is-grid-emission-factor-gef','government','Location-based grid calculation'),
('SRC07','GHG Protocol scope definitions','https://ghgptechassistance.zendesk.com/hc/en-us/articles/27680240285460-How-does-the-GHG-Protocol-define-and-categorize-emissions','standard-guidance','Mobile combustion Scope 1; acquired electricity Scope 2'),
('SRC08','CAAM UAS operations','https://www.caam.gov.my/public/unmanned-aircraft-system-uas/','regulator','SUP/ATF documentation; not authorization for project'),
('SRC09','CAAS UA cross border framework','https://www.caas.gov.sg/resources/media-and-publication/newsroom/cross-border-unmanned-aircraft-flights-are-prohibited-without-a-cross-border-per/','regulator','Cross-border permit requirements effective 2023-11-21'),
('SRC10','CAAS current permit rules','https://www.caas.gov.sg/unmanned-aircraft/operator-and-activity-permits/','regulator','Operator/activity permits may apply; no project license'),
('HIST01','Stage 6 legacy script','https://github.com/tasadapullo-svg/JB-CIQ-Drone-Logistics-Research-20261027/blob/4569817b8145efe2ae06f4b21addc1986f971c12/10_experiment_results/stage6_dual_region_multilevel_feeder/run_stage6.py','history','Blob SHA 1bbf7864ee9546b781f048d515c5d756da8752'),
('HIST02','Stage 8 F0/F1 review','https://github.com/tasadapullo-svg/JB-CIQ-Drone-Logistics-Research-20261027/blob/4569817b8145efe2ae06f4b21addc1986f971c12/10_experiment_results/stage8_f0_f1_airspace_and_energy_evidence/reports/CIQ_Stage8_F0_F1_formal_experiment_audit_report_20261028.md','history','Blob SHA d333b04bcc9e231064105c10dcab2e28bbb8974b'),
('HIST03','Stage 2 validation','https://github.com/tasadapullo-svg/JB-CIQ-Drone-Logistics-Research-20261027/blob/4569817b8145efe2ae06f4b21addc1986f971c12/outputs/stage2_20261027/stage2_gates.json','history','Original cross-border_route=False for all 128 old OD'),
]
with (R/'source_registry.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['source_id','title','url','source_class','audit_note','checked_date']);w.writerows([(*x,DATE) for x in SOURCES])

def p(name,unit,value,classification,source,scope,decision,comment):
 return dict(parameter=name,unit=unit,value=value,classification=classification,source_id=source,scope=scope,freeze_decision=decision,notes=comment)
P=[
 p('DJI_FC30_dual_payload_max','kg',30,'MANUFACTURER_SPEC','SRC01','FC30_DUAL','SCREENING_FROZEN','Manufacturer rated ceiling, not validated parcel operations'),
 p('DJI_FC30_dual_full_load_range','km',16,'MANUFACTURER_SPEC','SRC01','FC30_DUAL','SCREENING_FROZEN','At 30kg load, 15m/s, windless, full battery; not each leg or guaranteed round trip'),
 p('DJI_FC30_dual_empty_range','km',28,'MANUFACTURER_SPEC','SRC01','FC30_DUAL','SCREENING_FROZEN','Windless at 15m/s; no load'),
 p('DJI_FC30_wind_resistance_max','m/s',12,'MANUFACTURER_SPEC','SRC01','FC30_DUAL','SCREENING_FROZEN','Not an unconditional legal dispatch threshold'),
 p('DJI_DB2000_single_nominal_energy','kWh',1.9844,'MANUFACTURER_SPEC','SRC01','FC30_DUAL','SCREENING_FROZEN','Each DB2000 battery; nominal not usable energy'),
 p('DJI_FC30_dual_total_nominal_energy','kWh',3.9688,'DERIVED_MANUFACTURER_SPEC','SRC01','FC30_DUAL','SCREENING_FROZEN','2x1.9844; do not equate to flight energy'),
 p('DJI_FC30_takeoff_energy_model','kWh/task',None,'MISSING_MEASURED','SRC01','FC30_DUAL','BLOCKED','Requires mission phase power, payload/wind/flight path'),
 p('DJI_FC30_cruise_energy_model','kWh/km',None,'MISSING_MEASURED','SRC01','FC30_DUAL','BLOCKED','Do not derive from nominal energy / max range'),
 p('DJI_FC30_descent_landing_energy_model','kWh/task',None,'MISSING_MEASURED','SRC01','FC30_DUAL','BLOCKED','Includes hover/drop/recovery'),
 p('DJI_FC30_usable_SOC_reserve','fraction',None,'MISSING_POLICY','SRC01','FC30_DUAL','BLOCKED','Must be distinct from nominal battery energy'),
 p('DJI_FC30_charging_efficiency','fraction',None,'MISSING_EVIDENCE','SRC01','FC30_DUAL','BLOCKED','Wall input energy required'),
 p('Wingcopter_198_Cargo_payload_max','kg',4.7,'MANUFACTURER_SPEC','SRC02','W198_CARGO','SCREENING_FROZEN','Cargo model only'),
 p('Wingcopter_198_Cargo_max_range','km',92,'MANUFACTURER_SPEC','SRC02','W198_CARGO','SCREENING_FROZEN','Up to; load/weather/reserve profile unspecified'),
 p('Wingcopter_198_Cargo_wind_resistance','m/s',18,'MANUFACTURER_SPEC','SRC02','W198_CARGO','SCREENING_FROZEN','Up to, weather and operations limits unverified'),
 p('Wingcopter_198_Cargo_battery_nominal_energy','kWh',None,'MISSING_MANUFACTURER','SRC02','W198_CARGO','BLOCKED','Must not borrow generic W198 specs'),
 p('Wingcopter_198_Cargo_usable_SOC_reserve','fraction',None,'MISSING_MANUFACTURER','SRC02','W198_CARGO','BLOCKED','Reserve unknown'),
 p('Wingcopter_198_Cargo_mission_energy_model','kWh/task',None,'MISSING_MEASURED','SRC02','W198_CARGO','BLOCKED','No validated payload and weather task mapping'),
 p('Wingcopter_198_Cargo_charging_efficiency','fraction',None,'MISSING_EVIDENCE','SRC02','W198_CARGO','BLOCKED','No validated input-to-battery ratio'),
 p('petrol_TTW_fuel_energy_CO2_EF','kgCO2/TJ',69300,'IPCC_DEFAULT','SRC03','GASOLINE','METHOD_FROZEN','Tier1 fallback; local fuel chemistry preferred'),
 p('diesel_TTW_fuel_energy_CO2_EF','kgCO2/TJ',74100,'IPCC_DEFAULT','SRC03','DIESEL','METHOD_FROZEN','Tier1 fallback; local fuel chemistry preferred'),
 p('petrol_fuel_density','kg/L',None,'LOCAL_FUEL_NEEDED','SRC03','GASOLINE','BLOCKED','No invented density; fuel blend dependency'),
 p('diesel_fuel_density','kg/L',None,'LOCAL_FUEL_NEEDED','SRC03','DIESEL','BLOCKED','No invented density; blend dependence'),
 p('petrol_net_calorific_value','MJ/kg',None,'LOCAL_FUEL_NEEDED','SRC03','GASOLINE','BLOCKED','Must reconcile to local fuel composition'),
 p('diesel_net_calorific_value','MJ/kg',None,'LOCAL_FUEL_NEEDED','SRC03','DIESEL','BLOCKED','Needed when using IPCC kg/TJ'),
 p('petrol_car_fuel_consumption','L/100km',None,'LOCAL_VEHICLE_NEEDED','SRC03','M0_PETROL','BLOCKED','Representative type, traffic cycle and load needed'),
 p('diesel_van_fuel_consumption','L/100km',None,'LOCAL_VEHICLE_NEEDED','SRC03','M0_DIESEL','BLOCKED','Capacity-equivalent local van with evidence'),
 p('road_idle_fuel_lph','L/hour',None,'LOCAL_VEHICLE_NEEDED','SRC03','ROAD','BLOCKED','Avoid double counting if base fuel rate contains congestion/idling'),
 p('road_vehicle_capacity','kg',None,'MODEL_SCENARIO_NEEDED','HIST01','ROAD','BLOCKED','Match payload and vehicle load profile'),
 p('M0_M1_M2_operational_stops','minutes/stop',None,'MODEL_SCENARIO_NEEDED','HIST01','ALL','BLOCKED','Loading, unloading, transfer and charging queue service'),
 p('M0_fuel_price','MYR/L',None,'DATED_PRICE_NEEDED','','M0','BLOCKED','Do not freeze volatile 2026 price without date and source'),
 p('operational_labor_cost','MYR/hour',None,'EMPLOYMENT_EVIDENCE_NEEDED','','ALL','BLOCKED','Country and employer-specific; scenario only before validation'),
 p('Peninsular_MY_grid_GEF_2024_provisional','kgCO2e/kWh',0.740,'REGULATOR_GEF','SRC04','GRID_MY_PENINSULAR','REFERENCE_FROZEN','2024 provisional, not 2026 observation'),
 p('Singapore_grid_GEF_2024','kgCO2/kWh',0.402,'OFFICIAL_GEF','SRC05','GRID_SG','REFERENCE_FROZEN','CO2 only, not kgCO2e; cannot sum with Malaysia factor as harmonized CO2e'),
 p('GRID_MY_2026_location_factor','kgCO2e/kWh',None,'MISSING_YEAR_MATCH','','GRID_MY_PENINSULAR','BLOCKED','Year-match or explicitly prior-year proxy plus uncertainty'),
 p('GRID_SG_2026_harmonized_CO2e_factor','kgCO2e/kWh',None,'MISSING_GAS_MATCH','','GRID_SG','BLOCKED','Need compatible CO2e or conduct CO2-only separate inventory'),
 p('road_upstream_fuel_WTT_EF','kgCO2e/L',None,'OUTSIDE_CURRENT_BOUNDARY','SRC07','UPSTREAM','NOT_MAIN_RESULT','If added, report separate WTW analysis; do not mix with TTW'),
 p('battery_vehicle_embodied_emissions','kgCO2e/unit',None,'OUTSIDE_CURRENT_BOUNDARY','SRC07','LCA','NOT_MAIN_RESULT','Do not call operational emission life-cycle'),
 p('airspace_cross_border_permit','document+route_id',None,'EXTERNAL_AUTHORIZATION','SRC09','CROSS_BORDER_UAV','BLOCKED','No approved route identified'),
 p('actual_route_energy_reserve_margin','fraction',None,'MISSING_SCENARIO','','UAV','BLOCKED','Need wind, load, reserve and route detour'),
 p('weather_rain_dispatch_limits','mm/h',None,'AIRCRAFT_EVIDENCE_NEEDED','SRC01','UAV','BLOCKED','Old 0.1 mm/h generic is unsupported for either aircraft'),
 p('mission_timing_weather_resolution','minute',None,'DATA_RESOLUTION_NEEDED','HIST01','UAV','BLOCKED','Actual takeoff/return timestamps, not only release hour'),
 p('cross_border_CIQ_wait_model','min/crossing',None,'INDEPENDENT_SOURCE_NEEDED','HIST03','CROSS_BORDER','BLOCKED','No artificial 0-minute border wait'),
]
with (R/'stage05_parameter_registry.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.DictWriter(f,fieldnames=list(P[0]));w.writeheader();w.writerows(P)

contract={
 'version':'STAGE05_PROTOCOL_V1_20261030',
 'status':'PROTOCOL_FROZEN_NO_NUMERICAL_RUN',
 'historical_git_commit':'4569817b8145efe2ae06f4b21addc1986f971c12',
 'old_stage6_script_git_blob_sha':'1bbf7864ee9546b781f048d515c5d756da8752',
 'scope':{'geography':'Johor Bahru + Singapore CIQ comparison, A/B/C three-zone proposal; exact QGIS areas not yet verified',
          'historic_limit':'Old 128 ODs were all inland cross_border_route=False; never reclassify as cross-border',
          'primary_functional_unit':'one frozen synthetic consignment delivered to destination by deadline',
          'secondary_units':['per matched eligible order','per full fixed-demand scenario','per vehicle-day and per ton-km where denominators documented'],
          'period':'historical 2026-05 through 2026-09; exact dates remain to freeze with one demand population',
          'analysis_kind':'counterfactual conditional modeling, no observed shipment or approved UAV mission claim'},
 'task_schema_required':['task_id','seed','date_sgt','release_time_sgt','deadline_time_sgt','origin_node_id','destination_node_id','origin_country','destination_country','zone','payload_kg','parcel_count','demand_protocol_id','task_population_id'],
 'task_constraints':['Same immutable task IDs, locations, mass, timestamps and deadline for M0 M1 M2','One frozen sample only: never add 918000 resampled Stage2 to 29842 Stage6','UNREACHABLE, WEATHER_BLOCKED, NOT_AUTHORIZED and MISSING_INPUT retained as distinct outcomes','All order status and fallback outputs retained; no success-only denominator','Do not change synthetic-demand geography unless explicitly remapped and versioned','Cross-border class defined by actual country pair; no assumptions from zone names'],
 'modes':{'M0':{'definition':'road-only petrol car OR diesel van (distinct paired sensitivity profiles)','asset_boundary':'same depot/reposition/return/vehicle capacity and handling as corresponding mixed modes'},
          'M1':{'definition':'fixed-site feeder with consolidation and UAV segment as candidate scenario','asset_boundary':'road feeder, terminal and transfer, UAV outbound and return, charging, fallback, queuing and reserve'},
          'M2':{'definition':'vehicle-drone coordinated rendezvous with physical vehicle and drone time synchronization','asset_boundary':'shared vehicle kilometers counted once; moving drone launch, pickup recovery, wait, service and fallback'}},
 'time_components':['depot_preparation','road_queue','road_drive','CIQ_wait_if_crossing','cargo_transfer','UAV_charge','UAV_queue','UAV_takeoff','UAV_cruise','delivery','UAV_return_or_rendezvous','repositioning'],
 'weather_join':'proposed actual UAV takeoff+arrival+return hour or finer source resolution, flag uncertainty for longer hourly data',
 'road_join':'directed OSM/model path and source-hour traffic proxy; no invented reverse, CIQ customs modeled separately when crossing',
 'accounting':{'primary':'fuel tank-to-wheel CO2 plus location-based charging electricity CO2 using gas-consistent emission factors; primary CO2e withheld until harmonized full GHG inputs',
               'secondary':'fossil fuel upstream and embodied emissions excluded from operational totals; may be separate explicitly labeled sensitivity',
               'petrol_diesel_CO2_formula':'road_fuel_L = route_km * validated_L_per_100km/100 + validated_disjoint_idle_L; CO2_kg = road_fuel_L * density_kg_per_L * NCV_MJ_per_kg/1e6 * EF_kgCO2_per_TJ',
               'grid_CO2_formula':'sum_by_charging_country(wall_kWh * national_grid_kgCO2_per_kWh); do not use 0.740 MY kgCO2e and 0.402 SG kgCO2 as one CO2e ledger',
               'mission_electricity':'battery discharge kWh, charging loss, idle loads and battery swap logistics separately; no battery nominal/max range quotient',
               'no_double_count':['no grid factor on combusted fuel','no second count of shared M2 road movement','no repeated shared linehaul trip per parcel','no additional turnaround if part of route energy already'],
               'required_output_ledger':['operational_CO2_kg_if_gas_consistent','operational_CO2e_kg_if_harmonized','route_fuel_l','wall_charge_kWh_MY','wall_charge_kWh_SG','road_distance_km','UAV_flight_distance_km','batch_allocation_method','status_and_uncertainty']},
 'run_policy':{'allow_main_simulation':False,'stage02_spatial_required':True,'stage03_stage04_weather_road_required':True,'actual_parameter_energy_required':True,'independent_smoke_reproduction_required':True,'regulatory_status':'candidate_only; no legal cross-border flight claims'},
 'notes':'This freezes definitions and source hierarchy, NOT numerical mission energy, fuel economy, cost, or permit assumptions.'
}
(R/'stage05_unified_task_protocol.json').write_text(json.dumps(contract,indent=2,ensure_ascii=False),encoding='utf-8')

GATES=[
 ('G01','Latest QGIS three-zone spatial geometry and node/edge hashes','BLOCKED','No verified QGIS archive in active workspace','Stage02 evidence'),
 ('G02','New/old node mapping and crossing country indicators','BLOCKED','No validated new coordinate and crosswalk','Stage02 export'),
 ('G03','One frozen sample/population with source hash','BLOCKED','Legacy 918000 and 29842 distinct fixtures','Frozen-task registry'),
 ('G04','Same task ID and deadline across 3 modes','PROTOCOL_FROZEN','Schema and rules defined; no task data tested','Main sim matched tasks'),
 ('G05','Bidirectional road connectivity or flagged missing','BLOCKED','37 historical fixes not applied; new routes absent','New OSRM/OSM validation'),
 ('G06','Cross-border delay and in-country OD classification','BLOCKED','Old 128 OD all cross_border_route=False','Realistic crossing scenario/out-of-scope flag'),
 ('G07','Wind/rain at actual flight time and missingness','BLOCKED','Stage6 uses release-hour proxy and sparse NEA coverage','Mission-time weather join'),
 ('G08','DJI FlyCart 30 sourced mission energy curve','BLOCKED','Max-range/nominal-kWh do not measure task energy','Independent phase power/source'),
 ('G09','Wingcopter Cargo sourced mission energy curve','BLOCKED','No cargo-specific validated battery/energy source','Cargo energy data or explicit bounded scenarios'),
 ('G10','Validated petrol car or diesel van fuel curve','BLOCKED','No vehicle-type road-cycle/load specific L/100km','Local vehicle data or sourced range'),
 ('G11','Tank-to-wheel CO2 emission method and EF','METHOD_FROZEN','IPCC default 69300 and 74100 kgCO2/TJ','Fuel density/NCV & local composition needed'),
 ('G12','Country and gas consistent charging grid factors','BLOCKED','MY 0.740 CO2e vs SG 0.402 CO2 differ','Harmonize species and year, preserve charge location'),
 ('G13','M0 M1 M2 equivalent vehicle capacity, returns, fallback','PROTOCOL_FROZEN','Matching counterfactual rule defined, not test-run','Staged smoke test'),
 ('G14','Full cost model source and currency year','BLOCKED','Labor, fuel, charging, maintenance unknown','Source registry & cost scenario'),
 ('G15','Airspace/land and cross-border permit checks','BLOCKED','Candidates not authorized; CAAS cross-border permit required','Regulatory approvals or no-flight scenario'),
 ('G16','Computational reproducibility / source dependencies','BLOCKED','Legacy Stage6 references unverified run_stage4_dispatch.py','Immutable repository checkout and dependency/test run'),
 ('G17','Operational vs WTW vs LCA accounting separated','PROTOCOL_FROZEN','Boundary and separate ledgers defined','Run-level assertions'),
 ('G18','End-to-end independent smoke QA before full seed runs','BLOCKED','Not run against real frozen inputs','QA report and per-order checks')]
with (R/'stage05_release_gates.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['gate_id','test','status','evidence_or_gap','release_requirement']);w.writerows(GATES)

ISSUES=[
('M0','old Stage6 electric-van 0.23kWh/km; not ICE fuel baseline','MUST_REPLACE','No direct petrol/diesel CO2 conversion'),
('M0','old road reverse = twice forward when missing','MUST_REPLACE','Directed road path or unresolved; no silent mirror'),
('M0','old CIQ wait omitted','BLOCK_CROSS_BORDER','Separate waiting/queue where crossing; not zero'),
('M1/M2','old generic UAV 470W empty + 120W/kg etc','MUST_REPLACE','Not DJI or Wingcopter measured power'),
('M1/M2','old rain 0.1mm/h and gust 10m/s','MUST_REPLACE','Not manufacturer-specific weather envelope'),
('M1/M2','old 4 km per leg battery 0.70kWh','MUST_REPLACE','Not matched to actual FC30/W198 cargo'),
('M1/M2','old release-hour wind to time/energy','MUST_REPLACE','Use proposed launch and return times; hourly caveat'),
('ALL','same 29,842 synthetic tasks as local historic reference','READ_ONLY_BASELINE','Keep historic performance, remap only on approved new population'),
('ALL','Stage2 918000 engineering resamples','DO_NOT_COMBINE','Not 918000 independent empirical shipments'),
('ALL','old 19 reference anchors and straight lines','DO_NOT_PROMOTE','Not validated new QGIS stations or permitted UAV routes'),
('ACCOUNTING','old 0.740 grid factor applied to all vehicle & drone electricity','CONDITIONAL','2024 MY provisional reference; country and gas mismatch when SG added'),
('ACCOUNTING','old cost and embodied per-day guesses','MUST_REPLACE','No real-world cost or life cycle claims'),
('ACCOUNTING','shared M2 road trip allocation','RETAIN_LOGIC_VALIDATE','Count shared movement exactly once, record per-task allocations')]
with (R/'legacy_to_stage05_decision.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['mode','historical_feature','decision','justification']);w.writerows(ISSUES)

# A rigorous token to prevent fake approvals: no parameter edits alone can release the run.
preflight={
'format':'CIQ_STAGE05_STRICT_RELEASE_GATE_V1',
'hard_requirements':[
  {'id':'S02_SPATIAL','status':'BLOCKED','evidence_path':None,'sha256':None},
  {'id':'ORDER_POPULATION','status':'BLOCKED','evidence_path':None,'sha256':None},
  {'id':'WEATHER_HOURLY','status':'BLOCKED','evidence_path':None,'sha256':None},
  {'id':'ROAD_OD_NEW','status':'BLOCKED','evidence_path':None,'sha256':None},
  {'id':'FUEL_CONSUMPTION_AND_CARBON','status':'BLOCKED','evidence_path':None,'sha256':None},
  {'id':'DJI_TASK_ENERGY','status':'BLOCKED','evidence_path':None,'sha256':None},
  {'id':'W198_CARGO_TASK_ENERGY','status':'BLOCKED','evidence_path':None,'sha256':None},
  {'id':'COUNTRY_GRID_GAS_HARMONIZED','status':'BLOCKED','evidence_path':None,'sha256':None},
  {'id':'CROSS_BORDER_SCENARIO_STATUS','status':'BLOCKED','evidence_path':None,'sha256':None},
  {'id':'MATCHED_TASK_SMOKE_TEST','status':'BLOCKED','evidence_path':None,'sha256':None}
],
 'approval':'DENY_ALL','auto_run':False,
 'warning':'All hard requirements must have status PASS with an existing readable evidence file whose SHA256 equals the recorded hash. This only reports readiness; it NEVER executes simulations.'
}
(R/'stage05_strict_run_gate_DENY_ALL.json').write_text(json.dumps(preflight,indent=2,ensure_ascii=False),encoding='utf-8')

readme='''# Stage 05 - 统一任务协议、燃油道路基线与双无人机参数来源审计\n\n日期：2026-10-30。状态：MODEL CONTRACT FROZEN / NUMERIC INPUTS HOLD / RUN DENIED。\n\n此包只读使用历史 GitHub commit 4569817b8145efe2ae06f4b21addc1986f971c12 的结果作为证据。没有把历史样本当作新版订单，也没有运行任何模式的新版数值实验。\n\n交付文件：\n- `STAGE05_FORMAL_AUDIT_20261030.docx`：中文审计报告。\n- `records/source_registry.csv`：权威来源与访问日。\n- `records/stage05_parameter_registry.csv`：双机型/燃油/电网参数；`BLOCKED` 的 value 保持空值。\n- `records/stage05_unified_task_protocol.json`：不可变统一任务协议、模式定义与核算口径。\n- `records/legacy_to_stage05_decision.csv`：旧模型保留/禁止迁移判定。\n- `records/stage05_release_gates.csv`：18 项门槛。\n- `records/stage05_strict_run_gate_DENY_ALL.json`：默认绝不放行。\n- `scripts/stage05_release_check.py`：执行只读验收，不产生仿真。\n- `tests/test_stage05_release_check.py`：合成单元测试。\n\n执行：在压缩包解压目录运行 `python scripts/stage05_release_check.py`。输出 JSON 到 `results/stage05_release_result.json`。若缺任何真实输入证据，状态为 HOLD，不允许 M0/M1/M2 计算。\n\nStage 02 的新 QGIS 空间原件未冻结；完成空间输入与源级核验之后，才可考虑独立可复现的任务级 smoke test。绝不可把模拟许可状态写成真实 CAAM/CAAS 授权。\n'''
(BASE/'README_CN.md').write_text(readme,encoding='utf-8')
print('wrote',len(P),'parameters',len(GATES),'gates',len(SOURCES),'sources')
