"""S07->S09 event-time weather adapter. No false weather interpolation.

Requires time interval UTC and validated source status. Missing or discontinuous
hours are hard failures, not silently replaced with dry or calm conditions.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import math

@dataclass(frozen=True)
class WeatherHour:
    grid_id: str
    start_utc: datetime
    end_utc: datetime
    wind_speed_mps: float
    wind_from_deg: float
    gust_mps: float
    rain_mm: float
    evidence: str

    def validate(self):
        if not self.grid_id or self.start_utc.tzinfo is None or self.end_utc.tzinfo is None:
            raise ValueError('Weather grid and timezone-aware UTC intervals required')
        if self.end_utc <= self.start_utc or (self.end_utc-self.start_utc).total_seconds()!=3600:
            raise ValueError('Hourly weather must specify 3600s interval')
        if self.start_utc.utcoffset().total_seconds()!=0 or self.end_utc.utcoffset().total_seconds()!=0:
            raise ValueError('Use UTC timestamps, not local timestamps')
        for x in (self.wind_speed_mps,self.gust_mps,self.rain_mm,self.wind_from_deg):
            if not math.isfinite(x):raise ValueError('No NaN in verified meteorology')
        if self.wind_speed_mps<0 or self.gust_mps<0 or self.rain_mm<0 or not (0<=self.wind_from_deg<360):
            raise ValueError('Invalid weather physical values')
        if self.evidence!='VERIFIED_INPUT_SOURCE_AND_TIME':
            raise ValueError('Unverified weather source: HOLD')

def weather_for_event(grid_id:str,start_utc:datetime,end_utc:datetime,records:list[WeatherHour]):
    if start_utc.tzinfo is None or end_utc.tzinfo is None or end_utc<=start_utc:
        raise ValueError('Timezone-aware event interval required')
    coverage=[]
    for w in records:
        if w.grid_id!=grid_id:continue
        w.validate()
        a=max(start_utc,w.start_utc);b=min(end_utc,w.end_utc)
        if b>a:coverage.append((a,b,w))
    coverage.sort(key=lambda x:x[0])
    cursor=start_utc
    for a,b,_ in coverage:
        if a!=cursor:raise ValueError('Weather event has gap or overlapping interval: HOLD')
        cursor=b
    if cursor!=end_utc:raise ValueError('Weather event has uncovered minutes: HOLD')
    return [(x[2],(x[1]-x[0]).total_seconds()) for x in coverage]

def along_track_wind_mps(wind_speed_mps:float,wind_from_deg:float,track_bearing_deg:float)->float:
    if not all(map(math.isfinite,(wind_speed_mps,wind_from_deg,track_bearing_deg))):
        raise ValueError('Nonfinite wind vector')
    if wind_speed_mps<0:raise ValueError('Negative wind')
    # Meteorological direction: wind from 0° is blowing southward.
    blowing_toward_deg=(wind_from_deg+180)%360
    return wind_speed_mps*math.cos(math.radians(blowing_toward_deg-track_bearing_deg))
