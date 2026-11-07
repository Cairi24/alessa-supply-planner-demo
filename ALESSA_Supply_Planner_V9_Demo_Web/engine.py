"""Motor de cotización de compras V5. Recalcula desde forecast mensual base."""
from __future__ import annotations
import calendar
import math
from datetime import date, timedelta

ORIGINS = {
    'China': (45,55), 'Vietnam': (45,55), 'Perú': (30,10),
    'Colombia': (30,15), 'Panamá': (30,15), 'Brasil': (30,30),
    'Europa': (30,45), 'Egipto': (30,45), 'Turquía': (30,45),
    'Ecuador': (0,0)
}
ALIASES={'brazil':'Brasil','brasil':'Brasil','peru':'Perú','colombia':'Colombia',
         'panama':'Panamá','turkey':'Turquía','turquia':'Turquía','vietnam':'Vietnam',
         'china':'China','egypt':'Egipto','egipto':'Egipto','local':'Ecuador',
         'ecuador':'Ecuador','europa':'Europa'}
# Calendario provisional de prueba; validarlo con RRHH/Operaciones.
HOLIDAYS = {date(2026,11,20),date(2026,12,25),date(2027,1,1),date(2027,2,8),
            date(2027,2,9),date(2027,3,26),date(2027,4,30),date(2027,5,24),
            date(2027,8,9),date(2027,10,8),date(2027,11,1),date(2027,11,2)}
PROTECTIONS = {'Base':1.0, 'Moderada':1.15, 'Alta':1.30, 'Máxima':1.45}
DEFAULT_DATE = date(2026,11,6)

def normal_country(raw):
    raw=str(raw or '').strip()
    return ALIASES.get(raw.lower(),raw)

def add_workdays(d,n):
    while n>0:
        d += timedelta(days=1)
        if d.weekday()<5 and d not in HOLIDAYS:n-=1
    return d

def add_months(d,n):
    year=d.year+(d.month-1+n)//12
    month=(d.month-1+n)%12+1
    return date(year,month,min(d.day,calendar.monthrange(year,month)[1]))

def arrival_date(origin,order_date):
    origin=normal_country(origin)
    if origin=='Ecuador':return add_workdays(order_date,10)
    if origin not in ORIGINS:return None
    mfg,transit=ORIGINS[origin]
    return add_workdays(order_date+timedelta(days=mfg+transit),7)

def monthly_forecast(forecasts, sku):
    fc=forecasts.get(str(sku),{})
    out={}
    for k,qty in fc.items():
        try:
            channel,yyyy_mm_dd=k.split('_',1)
            month=date.fromisoformat(yyyy_mm_dd)
        except (ValueError,TypeError):continue
        out[month]=out.get(month,0.)+float(qty or 0)
    return out

def month_demand(fc,start,end):
    if end<=start:return 0.
    total=0.
    current=date(start.year,start.month,1)
    while current<end:
        following=add_months(current,1)
        active_beg=max(current,start)
        active_end=min(following,end)
        if active_end>active_beg:
            total+=max(0.,float(fc.get(current,0)))*(active_end-active_beg).days/(following-current).days
        current=following
    return total

def horizon_check(fc,begin,end):
    if not fc:return False
    earliest=min(fc)
    latest=max(fc)
    return begin>=earliest and end<=add_months(latest,1)

def as_int(n):
    try:return int(round(float(n)))
    except (ValueError,TypeError):return 0

def round_to_pack(amount,pack):
    if pack<=0:return 0
    return math.ceil(max(0,amount)/pack)*pack

def evaluate(data,order_date=DEFAULT_DATE,coverage=4,unit='Meses',protection='Alta',with_pending=True,coverage_overrides=None):
    """Return row dicts recalculated from the unchanged base forecast.

    Monetary stock/price is not represented. No known delivery date for pending POs.
    """
    coverage_overrides=coverage_overrides or {}
    factor=PROTECTIONS[protection]
    res=[]
    for p in data['rows']:
        p=p.copy();sku=str(p['sku']);pack=as_int(p.get('pack'))
        fc=monthly_forecast(data['forecasts'],sku)
        amount=coverage_overrides.get(sku,coverage)
        try:amount=float(amount)
        except (ValueError,TypeError):amount=0
        amount=max(0.,amount)
        arrived=arrival_date(p.get('country'),order_date)
        if unit=='Días':
            end=arrived+timedelta(days=amount) if arrived else None
        else:
            full=int(amount)
            remainder=amount-full
            end=(add_months(arrived,full)+timedelta(days=round(30*remainder))) if arrived else None
        adequate=bool(arrived and end and horizon_check(fc,order_date,end))
        lead=month_demand(fc,order_date,arrived) if adequate else 0.
        cover=month_demand(fc,arrived,end) if adequate else 0.
        eligible=p.get('status')=='ELEGIBLE' and float(p.get('months_inv') or 0)<6 and pack>0
        # No auto suggestion if forecast horizon does not cover the target period.
        suggested=round_to_pack((lead+cover)*factor -as_int(p.get('stock'))-(as_int(p.get('pending')) if with_pending else 0),pack) if (adequate and eligible) else 0
        scenario_without=round_to_pack((lead+cover)*factor -as_int(p.get('stock')),pack) if (adequate and eligible) else 0
        risk='RIESGO' if adequate and as_int(p.get('stock'))<lead*factor and p.get('status')=='ELEGIBLE' else 'SIN RIESGO' if adequate else 'REVISAR'
        p.update({'country':normal_country(p.get('country')),'arrival':arrived.isoformat() if arrived else '',
                  'coverage_end':end.isoformat() if end else '', 'coverage_value':amount,'coverage_unit':unit,
                  'horizon_ok':adequate,'lead_demand_calc':round(lead,2),'cover_demand_calc':round(cover,2),
                  'suggested':suggested,'suggested_without':scenario_without,
                  'risk':risk,'pack':pack,'factor':factor})
        res.append(p)
    res.sort(key=lambda x:(float(x.get('months_inv') or 0),str(x['sku'])))
    return res

def validate_order(rows,qty_by_sku):
    """Reject non-integer, negative or non-pack-multiple purchase amounts."""
    errors=[]
    for p in rows:
        sku=str(p['sku']);raw=qty_by_sku.get(sku,p['suggested'])
        try:
            f=float(raw)
            valid=math.isfinite(f) and f>=0 and f.is_integer() and int(f)%int(p['pack'])==0 if p['pack'] else f==0
        except (TypeError,ValueError,ZeroDivisionError):valid=False
        if not valid:errors.append(sku)
    return errors
