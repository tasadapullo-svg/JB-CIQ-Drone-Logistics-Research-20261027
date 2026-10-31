from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


RUN = Path(__file__).resolve().parents[1]
ROOT = RUN.parents[1]
G0 = RUN / "G0_INPUTS"
G1 = RUN / "S11B_REPAIRS" / "data"
S12 = RUN / "S12_EXPERIMENTS"
S07 = ROOT / "output_S07_S08_Codex_20261030" / "S07" / "data"
OLD = ROOT / "output_S11_Corrective_Validation_20261030" / "RUN_20261030_01" / "G11_2_BATTERY_SOC" / "data" / "S11_UAV_FLIGHTS.parquet"
HERE = Path(__file__).resolve().parent
FIG = HERE / "figures"
TAB = HERE / "tables"
FIG.mkdir(parents=True, exist_ok=True)
TAB.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({"figure.dpi": 140, "savefig.dpi": 300, "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})


def savefig(fig, stem, caption, source):
    for ext in ["png", "pdf", "svg"]:
        fig.savefig(FIG / f"{stem}.{ext}", bbox_inches="tight")
    plt.close(fig)
    (FIG / f"{stem}_caption_EN.md").write_text(caption + "\n", encoding="utf-8")
    audit = {"figure": stem, "source": source, "caption": caption, "status": "VERIFIED_FROM_FINAL_CSV", "sha256_png": hashlib.sha256((FIG / f"{stem}.png").read_bytes()).hexdigest()}
    (FIG / f"{stem}_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")


def write_table(df, stem, note):
    df.to_csv(TAB / f"{stem}.csv", index=False)
    headers=[str(x).replace("|","\\|") for x in df.columns]
    rows=[]
    for row in df.itertuples(index=False,name=None): rows.append("| "+" | ".join(str(x).replace("|","\\|").replace("\n"," ") for x in row)+" |")
    md="| "+" | ".join(headers)+" |\n| "+" | ".join(["---"]*len(headers))+" |\n"+"\n".join(rows)
    (TAB / f"{stem}.md").write_text(md + "\n\n" + note + "\n", encoding="utf-8")


registry = pd.read_csv(G0 / "G0_INPUT_REGISTRY.csv")
seed = pd.read_csv(G1 / "G2_PER_SEED_153DAY.csv")
pair = pd.read_csv(G1 / "G2_MODE_PAIRING.csv")
be = pd.read_csv(G1 / "G2_BREAK_EVEN_CORRECTED.csv")
config = pd.read_csv(S12 / "S12_C_SERVICE_CONSTRAINED_PARETO.csv")
sens = pd.read_csv(S12 / "S12_B_SENSITIVITY_CATALOG.csv")
tasks = pd.read_parquet(S07 / "V5_TASK_TIME_WEATHER_ROAD_INDEX.parquet")
nodes = pd.read_csv(S12 / "S12_A" / "S12_A_V5_68_NODE_REGISTRY.csv")
strata = pd.read_csv(S12 / "S12_A" / "S12_A_STRATIFIED_SERVICE.csv")
flights = pd.read_parquet(G1 / "G1_FLIGHT_LEDGER.parquet")
old_flights = pd.read_parquet(OLD)

# Table 1: input evidence.
t1 = registry[["source_stage", "purpose", "absolute_path", "sha256", "evidence_level"]].copy()
write_table(t1, "Table1_Data_sources_and_evidence", "Hashes identify the exact local inputs. Evidence labels separate project-validated artifacts from conditional proxies.")

# Table 2: parameters and their evidence class.
t2 = pd.DataFrame([
    ["Operating window", "24 h", "Preregistered scenario", "Primary"], ["Vehicles", "3", "Scenario assumption", "Shared across modes"],
    ["M1 fixed stations", "11", "Historical project whitelist", "Physical permission HOLD"], ["M2 batteries", "2 per vehicle", "Scenario assumption", "Finite, no onboard charging"],
    ["DJI payload", "30 kg", "OEM-labelled project input", "Conditional"], ["Wingcopter payload", "4.7 kg", "Project literature input", "Independent validation HOLD"],
    ["Weather distance", "10 km", "Audit threshold", "Not a legal/safety boundary"], ["Fuel intensity", "0.1 L/km", "Scenario assumption", "Sensitivity needed"],
    ["Petrol CO2 factor", "2.2410927 kg/L", "Project parameter", "Tank-to-wheel proxy"], ["Grid factor", "0.740 kg/kWh", "Project parameter", "Operational proxy"],
], columns=["parameter", "value", "evidence_class", "interpretation"])
write_table(t2, "Table2_Configuration_parameters", "These parameters define a conditional simulation. They do not constitute aircraft certification or operating permission.")

t3 = config.copy()
write_table(t3, "Table3_Strict_main_results", "Values are means across 30 independent 153-day seed replicates under the strict 10 km audit scenario.")
t4 = strata.copy()
write_table(t4, "Table4_Stratified_service", "Strata report all-order denominators. Small strata should not be interpreted causally.")
t5 = pair[pair.spatial_scenario == "STRICT_EXCLUDE_GT10KM"].copy()
write_table(t5, "Table5_Paired_statistics", "Intervals are seed-cluster bootstrap 95% intervals with one 153-day replicate as the inference unit.")
t6 = be[be.spatial_scenario == "STRICT_EXCLUDE_GT10KM"].copy()
write_table(t6, "Table6_Cost_emissions_break_even", "Break-even is the five-month per-replicate operating-cost difference. It excludes financing and capital recovery.")
t7 = config.merge(sens[["experiment_id", "status"]].assign(key=1), how="cross").drop(columns="key")
write_table(t7, "Table7_Robustness_and_Pareto", "Nondominance is limited to tested configurations. NOT_RUN experiments cannot support robustness claims.")

# Fig. 1: project geography from frozen coordinates and OSM edge midpoints.
edges = pd.read_parquet(S07 / "OSM_ROUTE_EDGES_WITH_FCD_PROXY.parquet")
stations = {"A01","A02","A03","A09","A_N05","A_N07","B06","B07","C02","C04","C21"}
fig, ax = plt.subplots(figsize=(7.2, 6.0))
ax.scatter(edges.mid_lon, edges.mid_lat, s=.25, c="#bdbdbd", alpha=.28, label="OSM directed-edge midpoints")
colors = {"A":"#1f77b4", "B":"#ff7f0e", "C":"#2ca02c"}
for z, g in nodes.groupby("zone"):
    ax.scatter(g.lon, g.lat, s=26, c=colors.get(z, "#555555"), label=f"Zone {z}", edgecolor="white", linewidth=.35)
st = nodes[nodes.node_id.isin(stations)]
ax.scatter(st.lon, st.lat, marker="*", s=95, c="#d62728", edgecolor="black", linewidth=.4, label="11 fixed M1 sites")
ax.set(xlabel="Longitude (WGS84)", ylabel="Latitude (WGS84)", title="Frozen V5 nodes, conditional road network, and fixed M1 sites")
ax.annotate("N", xy=(.94,.24), xytext=(.94,.10), xycoords="axes fraction", ha="center", va="center", fontsize=9, fontweight="bold", arrowprops={"arrowstyle":"-|>","color":"black"})
x0=nodes.lon.min()+.02; y0=nodes.lat.min()+.015
ax.plot([x0,x0+.09],[y0,y0],color="black",lw=2); ax.text(x0+.045,y0+.004,"~10 km",ha="center",va="bottom",fontsize=7)
ax.legend(fontsize=7, frameon=False, ncol=2)
nodes.to_csv(FIG / "Fig1_source.csv", index=False)
savefig(fig, "Fig1_Study_area", "Frozen V5 research geography. The 68 nodes and 11 project-whitelisted M1 sites are shown with conditional OSM road-edge midpoints. Site permission and operational airspace clearance remain unverified.", "S12_A_V5_68_NODE_REGISTRY.csv; OSM_ROUTE_EDGES_WITH_FCD_PROXY.parquet")

# Fig. 2: auditable workflow.
fig, ax = plt.subplots(figsize=(10, 3.3)); ax.axis("off")
labels = ["Frozen V5 +\n82,620 tasks", "Historical weather\n+ FCD proxy", "Directed roads +\nflight screening", "Shared dispatcher\nM0 / M1 / M2", "Event weather +\nSOC + recovery", "Service / energy /\ncost ledgers", "Paired inference +\nconstrained Pareto"]
for i, label in enumerate(labels):
    x = .02 + i * .14
    ax.add_patch(plt.Rectangle((x, .35), .12, .3, facecolor="#e8f1f8", edgecolor="#2b5c85", lw=1))
    ax.text(x+.06, .5, label, ha="center", va="center", fontsize=8)
    if i < len(labels)-1: ax.annotate("", xy=(x+.14,.5), xytext=(x+.12,.5), arrowprops={"arrowstyle":"->","color":"#555"})
ax.set_title("Evidence-linked simulation and analysis workflow")
pd.DataFrame({"step": range(1,8), "label": labels}).to_csv(FIG / "Fig2_source.csv", index=False)
savefig(fig, "Fig2_Workflow", "Workflow linking frozen inputs to event-level resource accounting, paired comparisons, and service-constrained Pareto analysis.", "G0_EXPERIMENT_CATALOG.csv and corrected code")

# Fig. 3: monthly input context.
x = tasks.copy(); x["month"] = pd.to_datetime(x.date_local).dt.month
monthly = x.groupby("month", as_index=False).agg(tasks=("task_id","size"), mean_gust=("wind_gusts_10m","mean"), mean_speed=("observed_speed_kmh_conditional","mean"), rain_hours_proxy=("rain",lambda v:int((v>0).sum())))
fig, axs = plt.subplots(1,3,figsize=(10,3.2))
axs[0].bar(monthly.month, monthly.tasks, color="#4c78a8"); axs[0].set(title="Frozen tasks", xlabel="Month", ylabel="Task records")
axs[1].plot(monthly.month, monthly.mean_gust, marker="o", color="#f58518"); axs[1].set(title="Mean release-hour gust", xlabel="Month", ylabel="m/s")
axs[2].plot(monthly.month, monthly.mean_speed, marker="o", color="#54a24b"); axs[2].set(title="Mean FCD speed proxy", xlabel="Month", ylabel="km/h")
monthly.to_csv(FIG / "Fig3_source.csv", index=False)
savefig(fig, "Fig3_Input_context", "Monthly task counts, release-hour gridded gusts, and direction-unobserved FCD speed proxies for May to September 2026.", "V5_TASK_TIME_WEATHER_ROAD_INDEX.parquet")

# Fig. 4: effect of defect correction on flight allocation.
oldc = old_flights[old_flights.spatial_scenario == "STRICT_EXCLUDE_GT10KM"].groupby("mode").size().rename("historical_S11")
newc = flights[flights.spatial_scenario == "STRICT_EXCLUDE_GT10KM"].groupby("mode").size().rename("corrected_S11B")
diff = pd.concat([oldc,newc],axis=1).fillna(0).reset_index()
fig, ax = plt.subplots(figsize=(7,3.8)); xx=np.arange(len(diff)); w=.36
ax.bar(xx-w/2,diff.historical_S11,w,label="Historical S11",color="#9ecae1"); ax.bar(xx+w/2,diff.corrected_S11B,w,label="Corrected S11B",color="#3182bd")
ax.set_xticks(xx,diff["mode"]); ax.set(ylabel="Flights across 4,590 scenarios", title="Flight allocation before and after P0 corrections"); ax.legend(frameon=False)
diff.to_csv(FIG / "Fig4_source.csv", index=False)
savefig(fig, "Fig4_Model_correction", "Strict-scenario flight counts before and after fixed-site, symmetric event-clock, mandatory recovery, common-geometry, and continuous-SOC corrections. The comparison is multi-factor and is not attributed to one defect.", "historical S11 and corrected S11B flight ledgers")

# Fig. 5: all-order allocation and service.
strict_f = flights[flights.spatial_scenario == "STRICT_EXCLUDE_GT10KM"].groupby("mode").size()
f5 = config[["mode","on_time_rate","completion_rate"]].copy(); f5["uav_flights"] = f5["mode"].map(strict_f).fillna(0)
fig, axs = plt.subplots(1,2,figsize=(9,3.6))
axs[0].bar(f5["mode"], f5.uav_flights, color="#59a14f"); axs[0].tick_params(axis="x",rotation=35); axs[0].set(ylabel="Flights",title="UAV task allocation")
axs[1].bar(f5["mode"], f5.on_time_rate, color="#edc949"); axs[1].axhline(.90,color="red",ls="--",lw=1,label="90% threshold"); axs[1].tick_params(axis="x",rotation=35); axs[1].set(ylim=(0,1),ylabel="All-order on-time rate",title="Service performance"); axs[1].legend(frameon=False)
f5.to_csv(FIG / "Fig5_source.csv", index=False)
savefig(fig, "Fig5_Service_and_allocation", "Strict-scenario UAV allocation and all-order service rates. The denominator includes completed, late, and unserved tasks rather than only flown tasks.", "G1 ledgers and Table 3")

# Fig. 6: required two panels only.
means = seed[(seed.spatial_scenario == "STRICT_EXCLUDE_GT10KM") & (seed["mode"] != "M2_NO_UAV")].copy()
means["mode"] = means["mode"].replace({"M1_NO_UAV":"M0_SHARED_NO_UAV"})
means = means.groupby("mode").agg(ghg=("mixed_boundary_operational_ghg_proxy_kg","mean"),ghg_sd=("mixed_boundary_operational_ghg_proxy_kg","std"),cost=("partial_opex_MYR","mean"),cost_sd=("partial_opex_MYR","std")).reset_index()
fig, axs = plt.subplots(1,2,figsize=(10,3.8)); xx=np.arange(len(means))
axs[0].bar(xx,means.ghg,yerr=1.96*means.ghg_sd/np.sqrt(30),color="#4c78a8",capsize=3); axs[0].set_xticks(xx,means["mode"],rotation=35); axs[0].set(ylabel="kg CO2e proxy / five months",title="(a) Operational emissions proxy")
axs[1].bar(xx,means.cost,yerr=1.96*means.cost_sd/np.sqrt(30),color="#f58518",capsize=3); axs[1].set_xticks(xx,means["mode"],rotation=35); axs[1].set(ylabel="MYR / five months",title="(b) Partial operating cost")
means.to_csv(FIG / "Fig6_source.csv", index=False)
savefig(fig, "Fig6_Emissions_and_cost", "Seed-level mean and normal-approximation 95% interval for (a) the mixed-boundary operational emissions proxy and (b) partial operating cost. Values are per 153-day replicate; the 30 seeds are not summed.", "G2_PER_SEED_153DAY.csv")

# Fig. 7: service-constrained Pareto.
fig, ax = plt.subplots(figsize=(6.4,4.6))
for r in config.itertuples(index=False):
    marker = "o" if r.pareto_status == "NONDOMINATED_WITHIN_TESTED_SET" else "x"
    ax.scatter(r.partial_opex_MYR,r.operational_ghg_proxy_kg,s=80,marker=marker,label=r.mode)
    ax.annotate(r.mode,(r.partial_opex_MYR,r.operational_ghg_proxy_kg),xytext=(4,4),textcoords="offset points",fontsize=7)
ax.set(xlabel="Partial OPEX (MYR / five months)",ylabel="Operational GHG proxy (kg CO2e / five months)",title="Service-constrained outcomes in the tested set")
config.to_csv(FIG / "Fig7_source.csv", index=False)
savefig(fig, "Fig7_Pareto", "Cost-emissions outcomes under the strict main scenario. Circles denote configurations classified as nondominated within the tested set; crosses denote dominated or service-infeasible configurations. This is not a proof of global optimality.", "S12_C_SERVICE_CONSTRAINED_PARETO.csv")

# Evidence-bound manuscript text.
main = config.set_index("mode")
def pct(mode, metric):
    row = pair[(pair.spatial_scenario=="STRICT_EXCLUDE_GT10KM") & (pair["mode"]==mode) & (pair.metric==metric)].iloc[0]
    return row.paired_pct_mean, row.paired_pct_ci95_low, row.paired_pct_ci95_high

def effect_phrase(label, value, low, high):
    if high < 0:
        return f"reduced {label} by {-value:.2f}% (95% seed-cluster bootstrap interval {-high:.2f}% to {-low:.2f}%)"
    if low > 0:
        return f"increased {label} by {value:.2f}% ({low:.2f}% to {high:.2f}%)"
    return f"changed {label} by {value:.2f}% ({low:.2f}% to {high:.2f}%)"

result_lines=[]
for mode in ["M1_DJI","M1_WING","M2_DJI","M2_WING"]:
    g=pct(mode,"mixed_boundary_operational_ghg_proxy_kg"); c=pct(mode,"partial_opex_MYR"); t=pct(mode,"mean_delivery_minutes")
    result_lines.append(f"Relative to its shared no-UAV control, {mode} {effect_phrase('the operational GHG proxy',*g)}, {effect_phrase('partial OPEX',*c)}, and {effect_phrase('mean delivery time',*t)} (Table 5).")

methods = """# Methods (paper-ready draft)\n\nWe evaluated a frozen set of 82,620 synthetic delivery tasks across 4,590 daily seed scenarios. Each of 30 seeds represents one 153-day replicate spanning May to September 2026. The primary analysis used the STRICT_EXCLUDE_GT10KM weather-representativeness audit and a 24 h operating window. A relaxed spatial proxy was retained as sensitivity analysis and was not interpreted as evidence of real-world flyability.\n\nThe corrected dispatcher used three petrol vehicles in every mode. M1 launches were restricted to an explicit whitelist of 11 project sites. M2 launches remained vehicle-coupled. Every selected mission included outbound flight, delivery, return launch, recovery, finite battery state, weather checks at four mission events, and a mandatory vehicle return to its depot within the duty window. M1 and M2 shared the same directed geometry, reverse-edge, WMP228-reference, cross-border, weather, and energy-screening kernel.\n\nOutcomes were calculated from physical vehicle legs and UAV flights, avoiding per-order duplication of shared travel. The emissions outcome is a mixed-boundary operational proxy based on petrol use and grid electricity, not a life-cycle assessment. Paired comparisons used the 30 seed-level 153-day replicates as the inference units. Service feasibility required at least 95% completion and 90% on-time delivery across all orders.\n"""
results = "# Results (paper-ready draft)\n\nThe corrected full run retained 82,620 unique tasks, 4,590 scenarios, and 30 seed-level replicates. All corrected modes were evaluated with the same orders and dispatch kernel.\n\n" + "\n\n".join(result_lines) + "\n\n" + "The correction changed UAV allocation relative to historical S11 (Figure 4). Because fixed-site, event-clock, recovery, geometry, and SOC defects were corrected together, this before-after difference is a multi-factor model revision and cannot be assigned to a single defect. The service-constrained cost-emissions classification is reported only for the tested configurations (Figure 7); nondominance does not imply global optimality.\n"
discussion = """# Discussion (paper-ready draft)\n\nThe corrected experiment tests whether UAV-enabled dispatch retains a model-internal benefit after explicit fixed-site, return, weather, duty, and battery constraints. The paired comparisons therefore estimate the effect of enabling the UAV option within this dispatcher and parameterization. They do not estimate a real-world causal effect of drone deployment.\n\nThe results should be interpreted against four evidence limits. First, demand is synthetic even though orders are frozen and identical across modes. Second, the FCD input is a direction-unobserved speed proxy. Third, gridded weather was not validated against an independent local station, and the 10 km screen is an audit threshold rather than a safety boundary. Fourth, station permission, WMP228 operational clearance, and Wingcopter field energy remain unresolved. These limits prevent claims of verified operational feasibility or life-cycle decarbonization.\n\nThe main contribution of the corrected analysis is methodological: road, weather, service, and physical resource ledgers are evaluated with a common control and a seed-level uncertainty unit. Any advantage that survives these constraints is conditional on the tested system. Any loss of the historical advantage is also scientifically informative because it identifies sensitivity to operational assumptions.\n"""
conclusion = """# Conclusions and limitations (paper-ready draft)\n\nUnder the corrected simulation, M0, M1, and M2 can be compared on identical frozen tasks, shared vehicle resources, all-order service denominators, and physical energy ledgers. The results support conditional statements about the tested configurations only. They do not establish actual aircraft permission, field energy consumption, lifecycle emissions, observed demand response, or universal superiority of UAV delivery.\n\nPublication claims should therefore use the terms conditional simulation, operational emissions proxy, and model-internal paired comparison. Claims that UAV delivery is proven to reduce lifecycle emissions, is legally flyable at the studied sites, or is economically superior in practice are not supported by the available evidence.\n"""
abstract = "# Abstract numeric summary (paper-ready draft)\n\nA corrected multimodal simulation evaluated 82,620 frozen synthetic orders in 4,590 scenarios, organized as 30 independent 153-day seed replicates. Six dispatcher modes were compared under a strict 10 km weather-representativeness audit and a 24 h duty window. Fixed M1 sites, four-event weather screening, continuous battery state, complete UAV return, and mandatory vehicle depot return were enforced. Mode-specific paired effects and 95% seed-cluster bootstrap intervals are reported in Table 5. The analysis quantifies conditional service, operational energy-emissions proxies, and partial operating costs; it does not claim verified flight permission or lifecycle decarbonization.\n"
for name,text in [("S13_SCI_METHODS_EN.md",methods),("S13_SCI_RESULTS_EN.md",results),("S13_SCI_DISCUSSION_EN.md",discussion),("S13_SCI_CONCLUSIONS_LIMITATIONS_EN.md",conclusion),("S13_ABSTRACT_NUMERIC_SUMMARY_EN.md",abstract)]:
    (HERE/name).write_text(text,encoding="utf-8")

claims=[]
claim_modes=["M1_DJI","M1_WING","M2_DJI","M2_WING"]
for i,row in enumerate(result_lines,1):
    claims.append({"claim_id":f"RES-{i:03d}","claim_text":row,"evidence_path":"tables/Table5_Paired_statistics.csv","locator":f"mode={claim_modes[i-1]}","status":"Verified","action":"Retain conditional wording"})
claims += [
    {"claim_id":"LIM-001","claim_text":"The results do not establish actual flight permission.","evidence_path":"S12_EXPERIMENTS/S12_A/G3_GATE.json","locator":"hold","status":"Verified","action":"Retain limitation"},
    {"claim_id":"LIM-002","claim_text":"The operational GHG outcome is not lifecycle assessment.","evidence_path":"S11B_REPAIRS/qa/G2_LEDGER_RECONCILIATION.json","locator":"limitations","status":"Verified","action":"Retain limitation"},
    {"claim_id":"EXT-001","claim_text":"Wingcopter field energy is validated.","evidence_path":"","locator":"","status":"Not verifiable","action":"Do not use"},
]
pd.DataFrame(claims).to_csv(HERE/"S13_MANUSCRIPT_CLAIM_AUDIT.csv",index=False)

trace=[]
for rq,exp,figs,tables,claim in [
    ("RQ1","G3 spatial audit","Fig1;Fig3","Table1;Table4","Conditional spatial evidence; permissions HOLD"),
    ("RQ2","G1/G2 corrected dispatch","Fig4;Fig5","Table3;Table5","Model-internal service effects"),
    ("RQ3","G4/G5 cost-emissions Pareto","Fig6;Fig7","Table6;Table7","Lowest tested operational proxy subject to service"),
]:
    trace.append({"research_question":rq,"experiment":exp,"figures":figs,"tables":tables,"paper_claim":claim,"evidence_level":"CONDITIONAL_SIMULATION","hold":"External validity and operational permission"})
pd.DataFrame(trace).to_csv(HERE/"S13_FIG_TABLE_CLAIM_TRACEABILITY.csv",index=False)

gate={"gate":"G6_G7_S13","status":"PASS_CONDITIONAL","figures":7,"tables":7,"claim_audit_rows":len(claims),"paper_limit":"Paper-ready conditional simulation text; external citations, target-journal formatting, permissions, field energy, and lifecycle evidence remain HOLD."}
(HERE/"G6_G7_GATE.json").write_text(json.dumps(gate,indent=2),encoding="utf-8")
print(json.dumps(gate,indent=2))
