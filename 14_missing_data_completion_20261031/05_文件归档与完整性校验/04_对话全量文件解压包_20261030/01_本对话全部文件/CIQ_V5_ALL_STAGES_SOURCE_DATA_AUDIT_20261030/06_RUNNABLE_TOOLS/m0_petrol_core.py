"""S08 petrol vehicle energy / cost ledger.

Method implementation, not a calibrated model and not a source of empirical
vehicle fuel rates. Accepts ONLY physically routed and audited road legs.
All distances must be driving path distances, NEVER straight-line UAV links.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
import math

@dataclass(frozen=True)
class PetrolParameters:
    litres_per_100km: float
    density_kg_per_litre: float
    net_calorific_value_MJ_per_kg: float
    ttw_co2_kg_per_TJ: float
    petrol_MYR_per_litre: float
    driver_MYR_per_hour: float
    idling_litres_per_hour: float | None = None
    cruising_rate_includes_idling: bool = True
    wtt_kgco2e_per_litre: float | None = None

    def validate(self) -> None:
        required={
            'litres_per_100km':self.litres_per_100km,
            'density_kg_per_litre':self.density_kg_per_litre,
            'net_calorific_value_MJ_per_kg':self.net_calorific_value_MJ_per_kg,
            'ttw_co2_kg_per_TJ':self.ttw_co2_kg_per_TJ,
            'petrol_MYR_per_litre':self.petrol_MYR_per_litre,
            'driver_MYR_per_hour':self.driver_MYR_per_hour,
        }
        for k,v in required.items():
            if not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0:
                raise ValueError(f'{k}: positive finite evidenced value required')
        if self.idling_litres_per_hour is not None:
            if not math.isfinite(self.idling_litres_per_hour) or self.idling_litres_per_hour<0:
                raise ValueError('idling_litres_per_hour invalid')
        if self.wtt_kgco2e_per_litre is not None and self.wtt_kgco2e_per_litre<0:
            raise ValueError('WTT factor invalid')

@dataclass(frozen=True)
class RoadLeg:
    leg_id: str
    trip_id: str
    vehicle_id: str
    road_distance_km: float
    driving_minutes: float
    stationary_minutes: float
    evidence_status: str
    road_graph_sha256: str
    served_task_ids: tuple[str,...] = ()

    def validate(self)->None:
        if not all([self.leg_id,self.trip_id,self.vehicle_id,self.road_graph_sha256]):
            raise ValueError('physical leg identifiers and graph hash required')
        if self.evidence_status != 'ACCEPTED_DIRECTED_ROAD':
            raise ValueError('No accepted directed-road evidence; HOLD')
        for n in ('road_distance_km','driving_minutes','stationary_minutes'):
            x=getattr(self,n)
            if not isinstance(x,(int,float)) or not math.isfinite(x) or x<0:
                raise ValueError(f'{n} must be nonnegative finite')
        if self.road_distance_km>0 and self.driving_minutes<=0:
            raise ValueError('driving minutes zero for positive road distance')


def co2_kg_per_litre(params:PetrolParameters)->float:
    """density kg/L * NCV MJ/kg * IPCC factor kgCO2/TJ / 1e6 MJ/TJ"""
    params.validate()
    return params.density_kg_per_litre*params.net_calorific_value_MJ_per_kg*params.ttw_co2_kg_per_TJ/1_000_000


def assess_physical_trip_ledger(legs:Iterable[RoadLeg],params:PetrolParameters)->dict:
    """Count every physical driving leg ONCE, never divide mileage per order.

    Shared-trip allocation to deliveries is a separate downstream operation;
    avoid double-counting by keeping totals at the physical leg level.
    """
    params.validate()
    seen=set(); trip_ids=set(); n=0; kms=mins=stationary=0.0
    task_ids=set(); repeated_task_leg_counts=0
    for leg in legs:
        leg.validate()
        if leg.leg_id in seen: raise ValueError(f'duplicate physical leg ID: {leg.leg_id}')
        seen.add(leg.leg_id);trip_ids.add(leg.trip_id);n+=1
        kms+=leg.road_distance_km;mins+=leg.driving_minutes;stationary+=leg.stationary_minutes
        for task_id in leg.served_task_ids:
            if task_id in task_ids: repeated_task_leg_counts+=1
            task_ids.add(task_id)
    if n==0: raise ValueError('Empty physical trip ledger: HOLD')
    driving_litres=kms*params.litres_per_100km/100
    # Two mutually exclusive methods to avoid applying two sources of the same idling fuel.
    if params.cruising_rate_includes_idling:
        if stationary and params.idling_litres_per_hour not in (None,0):
            raise ValueError('Idling double count risk: set cruising_rate_includes_idling=False')
        idling_litres=0.0
    else:
        if stationary and params.idling_litres_per_hour is None:
            raise ValueError('Idling parameter unavailable for stationary minutes')
        idling_litres=stationary/60*(params.idling_litres_per_hour or 0)
    litres=driving_litres+idling_litres
    co2_ttw=litres*co2_kg_per_litre(params)
    labor_hours=(mins+stationary)/60
    result={
        'status':'METHOD_ONLY_EVIDENCE_DEPENDS_ON_INPUTS',
        'physical_road_legs':n,'distinct_trip_ids':len(trip_ids),
        'road_km_physical_total':kms,'driving_minutes_physical_total':mins,
        'stationary_minutes_physical_total':stationary,
        'fuel_litres_total':litres,'fuel_litres_driving':driving_litres,
        'fuel_litres_idling':idling_litres,'co2_ttw_kg':co2_ttw,
        'cost_fuel_MYR':litres*params.petrol_MYR_per_litre,
        'cost_driver_MYR':labor_hours*params.driver_MYR_per_hour,
        'cost_fuel_and_driver_MYR':litres*params.petrol_MYR_per_litre+labor_hours*params.driver_MYR_per_hour,
        'tasks_mentioned_on_legs_unique':len(task_ids),
        'tasks_referenced_on_multiple_legs':repeated_task_leg_counts,
        'accounting_rule':'physical_legs_count_once; repeats of task_id do NOT multiply fuel',
        'co2_boundary':'PETROL_TTW_CO2_ONLY_NOT_LCA'
    }
    if params.wtt_kgco2e_per_litre is not None:
        result['fuel_wtw_kgco2e_illustrative']=co2_ttw+litres*params.wtt_kgco2e_per_litre
        result['fuel_wtw_note']='Gases and scope for TTW factor should be aligned before reporting WTW CO2e'
    return result
