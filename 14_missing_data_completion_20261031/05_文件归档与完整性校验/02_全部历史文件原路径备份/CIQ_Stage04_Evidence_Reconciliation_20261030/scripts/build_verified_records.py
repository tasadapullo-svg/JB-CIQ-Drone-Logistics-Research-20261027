#!/usr/bin/env python3
"""Materialize human-reviewed subset of returned GitHub connector evidence.
NOT a replacement for cloning and hashing full source CSVs.
"""
from pathlib import Path
import csv,json
p=Path(__file__).resolve().parents[1]/'records';p.mkdir(parents=True,exist_ok=True)
A=[f'A05_A{i:02d}' for i in [1,2,3,4,6,7,8]]
B=['B01_B02','B01_B07']+[f'B02_B{i:02d}' for i in [1,3,4,5,6,7,8,9]]+[
 f'B{i:02d}_B{j:02d}' for i in [3,4,5,6] for j in [2,7]
]+[f'B07_B{i:02d}' for i in [1,2,3,4,5,6,8,9]]+[
 f'B{i:02d}_B{j:02d}' for i in [8,9] for j in [2,7]
]
assert len(A)==7 and len(B)==30 and len(set(A+B))==37
rr=[]
for ident in A+B:
 area=ident[0];cat='SNAP_FAILURE' if area=='A' else 'DATA_GAP'
 rr.append(dict(od_id=ident,area=area,diagnostic_category=cat,
 diagnostic_subcause='NEAREST_NODE_ON_DIRECTIONALLY_INCOMPATIBLE_LANE_OR_SINK' if area=='A' else 'REFERENCE_ANCHOR_GT_100M_FROM_OSM_ROAD_EDGE_ACCESS_NOT_ESTABLISHED',
 candidate_route_found='True',repair_applied='False',
 residual_exception='ACCESS_DIRECTION_TURN_BOUNDARY_UNVERIFIED',
 data_state='DIAGNOSTIC_CANDIDATE_NOT_VERIFIED_REPAIR',
 source_path='outputs/stage2_20261027/od_route_repair_log.csv',
 source_git_blob_sha1='6f1cee1b994959e327eaeecf1708fb7efada1b0d',
 source_lineage='connector_returned_source_rows_2026-10-30'))
with (p/'verified_historical_37_unapplied_OD_exceptions.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=rr[0].keys());w.writeheader();w.writerows(rr)
weather=[]
months={'05':(2976,2980,2976,0.0277,0.2819,'PARTIAL'),
 '06':(2880,2884,2880,0.0319,0.5402,'NOT_REQUESTED'),
 '07':(2976,2980,2976,0.0256,0.6823,'NOT_REQUESTED'),
 '08':(2976,2980,2976,0.0875,0.7674,'NOT_REQUESTED'),
 '09':(2880,2884,2880,0.1324,0.6730,'NOT_REQUESTED')}
for m,(main,era,nasa,rain,wind,nea) in months.items():
 weather.append(dict(month='2026-'+m,weather_hourly_reported=main,era5_rows_reported=era,nasa_rows_reported=nasa,
 era5_returned_unique_grid_cells=2,era5_reference_points=4,
 era5_grid_duplicate_pattern='CW_MY= CW_SG=SL_SG (1.5,103.75); SL_MY (1.5,103.5)',
 nasa_returned_unique_grid_cells=4,reported_rain_correlation=rain,reported_wind_correlation=wind,
 nea_status=nea,individual_hourly_values_recalculated='NO',
 source_path='data/weather_2026/processed/final_verification_summary.json',source_git_blob_sha1='85845782a5f5cdbb4fa49737bb6e63aaa6dc06c7'))
with (p/'verified_historical_weather_grid_and_QC.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=weather[0].keys());w.writeheader();w.writerows(weather)
summary={
 'audit':'STAGE04_HISTORICAL_ROAD_WEATHER_STRUCTURAL_RECONCILIATION',
 'sources':{
  'repository':'tasadapullo-svg/JB-CIQ-Drone-Logistics-Research-20261027',
  'commit':'4569817b8145efe2ae06f4b21addc1986f971c12',
  'road_diagnostics':{'path':'outputs/stage2_20261027/od_connectivity_diagnostics.csv','git_blob_sha1':'c144da04db6fed8df228accb776b07d5493972d9','line_rows_parsed':128},
  'road_repairs':{'path':'outputs/stage2_20261027/od_route_repair_log.csv','git_blob_sha1':'6f1cee1b994959e327eaeecf1708fb7efada1b0d','line_rows_parsed':37},
  'road_gates':{'path':'outputs/stage2_20261027/stage2_gates.json','git_blob_sha1':'63a6fb3a1ea21b85306e0a2b1a06869810515140'},
  'weather_qc':{'path':'data/weather_2026/processed/final_verification_summary.json','git_blob_sha1':'85845782a5f5cdbb4fa49737bb6e63aaa6dc06c7','type':'PRECOMPUTED_QC_METADATA_NOT_HOURLY_RAW'}},
 'road_results':{'od_total':128,'A_total':56,'B_total':72,'routable_original':91,
 'unroutable_original':37,'A_exceptions':7,'B_exceptions':30,'diagnostic_candidate_routes_found':37,
 'applied_repairs':0,'cross_border_od':0,'diagnostic_category':{'NONE_EXISTING_ROUTE':91,'SNAP_FAILURE':7,'DATA_GAP':30}},
 'road_stage2_gate_summary':{'G2_OD_STATUS':'PASS_DIAGNOSTIC_ONLY','G3_ROAD_INTERNAL':'BLOCKED','G4_CIQ_SEPARATION':'PASS_ONLY_OLD_DOMESTIC_TASK_SCOPE','G5_EXTERNAL_CALIBRATION':'BLOCKED'},
 'weather_results':{'period':'2026-05 through 2026-09','reference_point_count':4,'unique_ERA5_returned_grids_each_month':2,'unique_NASA_returned_grids_each_month':4,
 'five_month_total_reported_hourly_rows':14688,'NEA_06_09':'NOT_REQUESTED','NEA_05':'PARTIAL',
 'hourly_raw_values_independently_recomputed':False},
 'scientific_release':{'spatial_three_zone_inputs_frozen':False,'new_road_OD_rebuilt':False,'weather_real_task_exposure_verified':False,'fuel_vehicle_and_uav_operational_carbon_recalculated':False,'status':'HOLD'},
 'interpretation':'Connector lines re-counted for historical OD and repair records. Weather results are precomputed historical QC metadata. Not an independent full-source SHA256 or new numerical simulation.'
}
(p/'STAGE04_connector_verified_evidence.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
print('wrote',len(rr),'OD exceptions and',len(weather),'monthly QC records')
