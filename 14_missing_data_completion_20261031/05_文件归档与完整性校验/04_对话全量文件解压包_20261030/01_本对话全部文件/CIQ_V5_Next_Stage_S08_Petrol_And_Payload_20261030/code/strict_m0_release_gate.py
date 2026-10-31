"""S08 strict evidence gate. No fictional numbers; no manual pass of missing inputs."""
from pathlib import Path
import csv,json,hashlib,datetime
root=Path(__file__).resolve().parents[1]
raw=root/'inputs'
out=root/'qa'
param=json.loads((raw/'M0_PETROL_PARAMETERS_REQUIRED_NOT_YET_SOURCED.json').read_text())
legs=raw/'M0_PHYSICAL_TRIP_LEGS_REQUIRED_SCHEMA.csv'
with legs.open(newline='') as f: n=max(sum(1 for _ in csv.reader(f))-1,0)
req=('vehicle_definition','litres_per_100km','density_kg_per_litre','net_calorific_value_MJ_per_kg','petrol_MYR_per_litre','driver_MYR_per_hour','cruising_rate_includes_idling')
missing=[x for x in req if param.get(x) is None]
result={
 'status':'HOLD' if missing or n==0 else 'MANUAL_AUDIT_REQUIRED',
 'frozen_V5_spatial_reference':'sha256:0d19633630b6f12525ad9bd776bbf966ec1e8a46520bd8bc3d904013b02dce74',
 'missing_fuel_and_cost_params':missing,'accepted_physical_trip_legs_in_local_input':n,
 'road_graph_accepted':'NOT_EVIDENCED','weather_2026_05_09_numeric_join':'NOT_EVIDENCED',
 'full_main_M0_run':'HOLD','five_mode_comparison':'HOLD',
 'note':'The IPCC 69300 factor alone cannot calculate gasoline CO2 per litre; density & NCV are mandatory. No price or time model without sourced parameters. Never substitute straight-line distance.'}
out.mkdir(exist_ok=True)
(out/'S08_STRICT_PETROL_M0_RELEASE_GATE.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(result,indent=2,ensure_ascii=False))
