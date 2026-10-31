"""Conditionally simulate mission flight electricity; never validates aircraft-specific performance.

All inputs (cruise power, battery, wind, durations) are explicit scenario variables.
Actual release for carbon calculations requires independently evidenced aircraft performance
and time-indexed weather; this code by itself cannot grant approval.
"""
from __future__ import annotations
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class AircraftScenario:
    payload_limit_kg: float
    nominal_battery_kwh: float
    usable_battery_fraction: float
    reserve_fraction_of_usable: float
    charging_efficiency: float
    airspeed_mps: float
    loaded_cruise_kw: float
    empty_cruise_kw: float
    launch_and_landing_kwh: float

    def validate(self):
        for k in ('payload_limit_kg','nominal_battery_kwh','airspeed_mps',
                  'loaded_cruise_kw','empty_cruise_kw','charging_efficiency'):
            v=getattr(self,k)
            if not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0:
                raise ValueError('Positive finite aircraft scenario parameter required: '+k)
        for k in ('usable_battery_fraction','reserve_fraction_of_usable','charging_efficiency'):
            v=getattr(self,k)
            if not (0<v<1): raise ValueError('Fraction must be strictly within (0,1): '+k)
        if not math.isfinite(self.launch_and_landing_kwh) or self.launch_and_landing_kwh<0:
            raise ValueError('Invalid launch and landing energy')


@dataclass(frozen=True)
class Leg:
    path_length_km: float
    payload_kg: float
    along_wind_mps: float | None
    wind_time_evidence: str
    route_evidence: str


def calculate_scenario_mission(legs:list[Leg], specs:AircraftScenario)->dict:
    """Return scenario only. Never confuse geometry with legally usable route.

    Wind from actual event time must be independently verified; test markers are permitted
    only for fixture QA and cannot claim actual meteorological conditions.
    """
    specs.validate()
    if not legs: raise ValueError('No legs; HOLD')
    output=[]
    for leg in legs:
        if not math.isfinite(leg.path_length_km) or leg.path_length_km<0:
            raise ValueError('Invalid path length')
        if not math.isfinite(leg.payload_kg) or leg.payload_kg<0 or leg.payload_kg>specs.payload_limit_kg:
            raise ValueError('Payload outside capacity')
        if leg.along_wind_mps is None or not math.isfinite(leg.along_wind_mps):
            raise ValueError('Missing event-time weather; HOLD')
        if leg.wind_time_evidence not in ('EVENT_TIME_OBSERVED','TEST_FIXTURE_ONLY'):
            raise ValueError('Weather time has not been validated')
        if leg.route_evidence not in ('CONDITIONAL_GEOMETRY','ACCEPTED_FLIGHT_CORRIDOR'):
            raise ValueError('Unknown route evidence')
        ground_speed=specs.airspeed_mps+leg.along_wind_mps
        if ground_speed<=0: raise ValueError('Headwind groundspeed nonpositive')
        time_hours=leg.path_length_km*1000/ground_speed/3600
        power=specs.loaded_cruise_kw if leg.payload_kg>0 else specs.empty_cruise_kw
        output.append({'flight_hours':time_hours,'battery_energy_kwh':time_hours*power})
    battery_kwh=sum(x['battery_energy_kwh'] for x in output)+specs.launch_and_landing_kwh
    usable_kwh=specs.nominal_battery_kwh*specs.usable_battery_fraction
    energy_before_reserve=usable_kwh*(1-specs.reserve_fraction_of_usable)
    grid_kwh=battery_kwh/specs.charging_efficiency
    return {
        'release_status':'CONDITIONAL_MODEL_UNVALIDATED',
        'segments':len(legs),'flight_minutes':sum(x['flight_hours'] for x in output)*60,
        'battery_mission_kwh_assumed':battery_kwh,'grid_recharge_kwh_assumed':grid_kwh,
        'usable_battery_kwh_assumed':usable_kwh,'reserve_adjusted_budget_kwh_assumed':energy_before_reserve,
        'conditional_energy_budget_pass':battery_kwh<=energy_before_reserve,
        'has_real_event_time_weather':all(x.wind_time_evidence=='EVENT_TIME_OBSERVED' for x in legs),
        'has_accepted_corridor':all(x.route_evidence=='ACCEPTED_FLIGHT_CORRIDOR' for x in legs),
        'notice':'Inputs are SCENARIO assumptions; no calibrated model-specific cruise power; NOT validated carbon savings.'
    }
