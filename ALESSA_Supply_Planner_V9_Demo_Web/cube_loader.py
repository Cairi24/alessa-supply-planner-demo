from __future__ import annotations
import sys,math,re,statistics,json,calendar
from collections import defaultdict,Counter
from datetime import date,timedelta,datetime
from cube_reader import Reader

HOLIDAYS={date(2026,11,20),date(2026,12,25),date(2027,1,1),date(2027,2,8),date(2027,2,9),date(2027,3,26),date(2027,4,30),date(2027,5,24),date(2027,8,9),date(2027,10,8),date(2027,11,1),date(2027,11,2)}
START=date(2026,11,6);LAST_COMPLETE=date(2026,10,1);HORIZON=date(2027,12,1)
FACTOR=1.30;COVER_MONTHS=4
ORIGINS={'China':(45,55),'Vietnam':(45,55),'Perú':(30,10),'Colombia':(30,15),'Panamá':(30,15),'Brasil':(30,30),'Europa':(30,45),'Egipto':(30,45),'Turquía':(30,45),'Ecuador':(0,0)}
ALIASES={'peru':'Perú','brazil':'Brasil','brasil':'Brasil','colombia':'Colombia','china':'China','turkey':'Turquía','turquia':'Turquía','türkiye':'Turquía','vietnam':'Vietnam','panama':'Panamá','panamá':'Panamá','egypt':'Egipto','egipto':'Egipto','local':'Ecuador','ecuador':'Ecuador','europa':'Europa'}
PACK_BASE={'GG':1728,'G':144,'D':12,'C':100,'M':1000,'U':1}
FAIRS={1,3,8,10}

def months_between(start,end):
 d=date(start.year,start.month,1)
 while d<=end:
  yield d
  d=date(d.year+(d.month==12),d.month%12+1,1)

def excel_date(x):
 try:return date(1899,12,30)+timedelta(days=int(float(x)))
 except:return None

def add_workdays(d,n):
 while n>0:
  d+=timedelta(days=1)
  if d.weekday()<5 and d not in HOLIDAYS:n-=1
 return d

def add_months(d,n):
 y=d.year+(d.month-1+n)//12;m=(d.month-1+n)%12+1
 return date(y,m,min(d.day,calendar.monthrange(y,m)[1]))

def month_demand_forecast(forecast,s,e):
 tot=0.; curr=date(s.year,s.month,1)
 while curr<e:
  nxt=add_months(curr,1)
  active_beg=max(curr,s);active_end=min(nxt,e)
  if active_end>active_beg:
   tot+=float(forecast.get(curr,0))*(active_end-active_beg).days/(nxt-curr).days
  curr=nxt
 return tot

def normalize_country(raw):
 if not raw:return ''
 return ALIASES.get(str(raw).strip().lower(),str(raw).strip())

def parse_pack(raw):
 s=str(raw or '').strip().upper().replace(' ','')
 m=re.fullmatch(r'(GG|G|D|C|M|U)(\d*)',s)
 if not m:return 0
 return PACK_BASE[m.group(1)]*int(m.group(2) or '1')

def clip(v,lower,upper):return min(upper,max(lower,v))
def avg(v):return sum(v)/len(v) if v else 0.

def weights_mean(dat, weights):
 w=[(v,weights.get(y,0)) for y,v in dat if weights.get(y,0)>0]
 return sum(v*wt for v,wt in w)/sum(wt for v,wt in w) if w else 0

def pforecast(vals,first,channel,nov_qty=0):
 # vals: date(month) -> positive-only sale qty, 2024-01..2026-10
 if first is None:return {},'SIN VENTAS',0
 start_m=date(first.year,first.month,1)
 if start_m>LAST_COMPLETE:
  # no monthly full history: cold start requires explicit review
  monthly_nov=nov_qty*calendar.monthrange(2026,11)[1]/5
  base=monthly_nov*0.55  # strongly penalized due thin evidence
  return {m:round(base,2) for m in months_between(date(2026,11,1),HORIZON)},'NUEVO / NOV PARCIAL',base
 active=[m for m in months_between(start_m,LAST_COMPLETE)]
 full_12=[m for m in active if m>=date(2025,11,1)]
 full_6=[m for m in active if m>=date(2026,5,1)]
 full_3=[m for m in active if m>=date(2026,8,1)]
 months_pos=sum(float(vals.get(m,0))>0 for m in active)
 last_positive=max((m for m in active if vals.get(m,0)>0), default=None)
 active_recent=last_positive is not None and last_positive>=date(2025,11,1)
 if channel=='Retail':
  pp=[vals.get(m,0) for m in full_12 if vals.get(m,0)>0]
  med=statistics.median(pp) if pp else 0
  # retail one-off spikes moderated; channel wholesale untouched
  cap=max(med*2.8,1) if pp else 0
  v=lambda m: min(vals.get(m,0),cap) if cap>0 else 0
  r6=avg([v(m) for m in full_6]);r12=avg([v(m) for m in full_12]);baseline=0.60*r6+0.40*r12
  if len(full_3)==3 and len(full_6)>=6:
   last3=avg([v(m) for m in full_3]);prev3=avg([v(m) for m in full_6[:3]])
   if prev3>0:baseline*=clip((last3/prev3)**0.18,0.85,1.17)
  seasonal={}
  for mt in range(1,13):
   samples=[]
   for y in (2024,2025,2026):
    m=date(y,mt,1)
    if m<start_m or m>LAST_COMPLETE:continue
    year_active=[a for a in active if a.year==y]
    year_mean=avg([v(x) for x in year_active])
    if year_mean>0:samples.append((y,v(m)/year_mean))
   observed=weights_mean(samples,{2024:.2,2025:.35,2026:.45}) if samples else 1.0
   seasonal[mt]=clip(1+0.5*(observed-1),0.65,1.6)
  model='Retail robusto / estacional'
  out={m:round(max(0,baseline*seasonal[m.month]),2) for m in months_between(date(2026,11,1),HORIZON)}
 else:
  nonfair6=[m for m in full_6 if m.month not in FAIRS]
  nonfair12=[m for m in full_12 if m.month not in FAIRS]
  nonfair6_mean=avg([vals.get(m,0) for m in nonfair6]);nonfair12_mean=avg([vals.get(m,0) for m in nonfair12])
  baseline=.65*nonfair6_mean+.35*nonfair12_mean
  seasonal={}
  for mt in range(1,13):
   samples=[]
   for y in (2024,2025,2026):
    m=date(y,mt,1)
    if m<start_m or m>LAST_COMPLETE:continue
    active_nonfair=[a for a in active if a.year==y and a.month not in FAIRS]
    annual_base=avg([vals.get(a,0) for a in active_nonfair])
    if annual_base>0:samples.append((y,vals.get(m,0)/annual_base))
   seasonal[mt]=clip(1+.48*(weights_mean(samples,{2024:.20,2025:.35,2026:.45})-1),.65,2.0) if samples else 1.0
  # wholesale fairs preserve historical named-month pulses, with no outlier cap
  out={}
  for m in months_between(date(2026,11,1),HORIZON):
   if m.month in FAIRS:
    fair_obs=[]
    for year in (2024,2025,2026):
     hm=date(year,m.month,1)
     if hm>=start_m and hm<=LAST_COMPLETE:fair_obs.append((year,vals.get(hm,0)))
    historical_fair=weights_mean(fair_obs,{2024:.18,2025:.32,2026:.5}) if fair_obs else 0
    value=max(historical_fair,baseline*seasonal[m.month])
   else:value=baseline*seasonal[m.month]
   out[m]=round(max(0,value),2)
  model='Mayorista: ferias explícitas'
 if not active_recent:model+=' / sin venta reciente'
 if len(active)<8:model+=' / historial corto'
 return out,model,baseline



def load_cube(source_path):
 r=Reader(source_path)
 inv={}
 for rn,x in r.each(3):
  if rn<=4 or x.get(0)=='Total general' or not x.get(7):continue
  sku=str(x[7]).strip()
  inv[sku]={'sku':sku,'desc':str(x.get(5,'')),'category':str(x.get(4,'')), 'pending':int(round(float(x.get(6) or 0))), 'packstr':str(x.get(8,'')), 'pack':parse_pack(x.get(8,'')), 'ingress':excel_date(x.get(9)), 'months_inv':float(x.get(10) or 0), 'stock':int(round(float(x.get(11) or 0)))}
 origin={}
 for rn,x in r.each(7):
  if rn<=6 or x.get(0)=='Total general' or not x.get(6):continue
  sku=str(x[6]).strip()
  origin[sku]={'country':normalize_country(x.get(7,'')), 'supplier':str(x.get(8) or 'SIN PROVEEDOR').strip()}
 
 daily_info=defaultdict(lambda: {'first':None,'last':None,'nov_pos':0,'negatives':0})
 sales=defaultdict(float); monthly_net=defaultdict(float)
 for index,channel in [(1,'Retail'),(2,'Mayorista')]:
  header_years={};header_days={}
  for rn,x in r.each(index):
   if rn==6:header_years=x;continue
   if rn==7:
    for col,s in x.items():
     if col<11 or col not in header_years or not str(header_years[col]).isdigit():continue
     try:header_days[col]=datetime.strptime(f'{s}-{header_years[col]}','%d-%b-%Y').date()
     except:continue
    continue
   if rn<8 or x.get(0)=='Total general' or not x.get(7):continue
   sku=str(x[7]).strip();info=daily_info[sku]
   for col,value in x.items():
    if col<11 or col not in header_days:continue
    dt=header_days[col];amount=float(value)
    month=date(dt.year,dt.month,1)
    monthly_net[(sku,channel,month)]+=amount
    if amount<=0:
     if amount<0:info['negatives']+=-amount
     continue
    if info['first'] is None or dt<info['first']:info['first']=dt
    if info['last'] is None or dt>info['last']:info['last']=dt
    if month<=LAST_COMPLETE:sales[(sku,channel,month)]+=amount
    elif month==date(2026,11,1):
     sales[(sku,channel,month)]+=amount;info['nov_pos']+=amount
 
 monthset=list(months_between(date(2026,11,1),HORIZON))
 forecasts={};rows=[]
 for sku,v in inv.items():
  data={**v,**origin.get(sku,{'country':'','supplier':'SIN PROVEEDOR'})}
  dates=daily_info.get(sku)
  first=dates['first'] if dates else None
  data['first_sale']=first
  data['last_sale']=dates['last'] if dates else None
  data['sale_nov']=dates['nov_pos'] if dates else 0
  data['returns']=dates['negatives'] if dates else 0
  data['demand_2026_retail']=sum(sales.get((sku,'Retail',date(2026,m,1)),0) for m in range(1,11))
  data['demand_2026_wholesale']=sum(sales.get((sku,'Mayorista',date(2026,m,1)),0) for m in range(1,11))
  fc={};labels=[]
  for channel in ['Retail','Mayorista']:
   val={m:sales.get((sku,channel,m),0) for m in months_between(date(2024,1,1),LAST_COMPLETE)}
   # channel first positive date may differ from sku first; avoids retrospective zeros
   own_first=min((m for m in val if val[m]>0),default=first)
   if own_first is None and dates and dates['nov_pos']>0:own_first=date(2026,11,1)
   prediction,label,base=pforecast(val,own_first,channel,dates['nov_pos'] if dates else 0)
   for m,p in prediction.items():fc[(channel,m)]=p
   labels.append(label)
  data['method']='; '.join(labels)
  future={m:fc.get(('Retail',m),0)+fc.get(('Mayorista',m),0) for m in monthset}
  forecasts[sku]=fc
  c=data['country']
  if c=='Ecuador':arrival=add_workdays(START,10)
  elif c in ORIGINS:
   mfg,transit=ORIGINS[c];arrival=add_workdays(START+timedelta(days=mfg+transit),7)
  else:arrival=None
  data['arrive']=arrival;data['calendar_lead']=(arrival-START).days if arrival else None
  data['ingress_ok']=data['ingress'] is not None and data['ingress']>=date(2025,1,1)
  data['sell_ok']=first is not None
  if not data['sell_ok']:status='SIN VENTA POSITIVA'
  elif not data['ingress_ok']:status='ULTIMO INGRESO ANTES 2025 / SIN FECHA'
  elif not arrival:status='FALTA ORIGEN'
  elif not data['pack']:status='EMPAQUE NO VÁLIDO'
  elif data['supplier']=='SIN PROVEEDOR':status='FALTA PROVEEDOR'
  else:status='ELEGIBLE'
  data['status']=status
  if arrival:
   data['lead_demand']=round(month_demand_forecast(future,START,arrival),2)
   data['cover_demand']=round(month_demand_forecast(future,arrival,add_months(arrival,COVER_MONTHS)),2)
   data['total_demand_base']=round(data['lead_demand']+data['cover_demand'],2)
   data['risk_before_arrival']='RIESGO' if data['stock']<FACTOR*data['lead_demand'] else 'SIN RIESGO TEORICO'
  else:
   data['lead_demand']=0;data['cover_demand']=0;data['total_demand_base']=0;data['risk_before_arrival']='SIN ORIGEN'
  def compute(pending):
   if status!='ELEGIBLE' or data['pack']<=0 or data['months_inv']>=6:return 0
   return math.ceil(max(0,FACTOR*data['total_demand_base']-data['stock']-(data['pending'] if pending else 0))/data['pack'])*data['pack']
  data['suggest_pending']=compute(True);data['suggest_without']=compute(False)
  data['nov_forecast']=future[date(2026,11,1)]
  data['jan_fair_forecast']=future[date(2027,1,1)]
  data['mar_fair_forecast']=future[date(2027,3,1)]
  data['forecast_2027']=sum(future[m] for m in monthset if m.year==2027)
  data['auto_rule']='BAJO 6 MESES' if data['months_inv']<6 else '6 MESES O MAS: SIN REPOSICION AUTOMATICA'
  data['coldstart']=first is not None and (date(first.year,first.month,1)>date(2026,2,1))
  data['priority']=('ALTO' if data['months_inv']<2 else 'MEDIO' if data['months_inv']<6 else 'BAJO') if status=='ELEGIBLE' else 'REVISION'
  rows.append(data)
 
 rows.sort(key=lambda x:(x['months_inv'],x['sku']))
 budget={}
 for rn,x in r.each(4):
  cfg={10:(2026,'Retail','APROBADO'),22:(2026,'Mayorista','APROBADO'),36:(2027,'Retail','EN REVISION'),48:(2027,'Mayorista','EN REVISION')}
  if rn in cfg:
   year,channel,status=cfg[rn]
   for i in range(12):budget[(year,channel,i+1)]=round(float(x.get(i+5,0)),2)
 
 stat={
  'inventario_skus':len(inv),'sku_historical_sales':len([k for k,v in daily_info.items() if v['first']]),
  'eligible':sum(p['status']=='ELEGIBLE' for p in rows),
  'eligible_under6':sum(p['status']=='ELEGIBLE' and p['months_inv']<6 for p in rows),
  'auto_gate_6months':sum(p['status']=='ELEGIBLE' and p['months_inv']>=6 for p in rows),
  'under6_with_buy':sum(p['status']=='ELEGIBLE' and p['months_inv']<6 and p['suggest_pending']>0 for p in rows),
  'qty_with_pending':sum(p['suggest_pending'] for p in rows),
  'qty_without_pending':sum(p['suggest_without'] for p in rows),
  'stock_total':sum(p['stock'] for p in rows), 'pending_total':sum(p['pending'] for p in rows),
  'before_arrival_risks':sum(p['risk_before_arrival']=='RIESGO' and p['status']=='ELEGIBLE' for p in rows),
  'status':dict(Counter(p['status'] for p in rows)),
  'country':dict(Counter(p['country'] for p in rows)),
  'suppliers_with_recommendations':len(set(p['supplier'] for p in rows if p['suggest_pending']>0)),
  'forecast_2027_total':round(sum(p['forecast_2027'] for p in rows),0),
  'plan_2027_total':round(sum(v for (y,c,m),v in budget.items() if y==2027),0),
  'first_dates': [str(min(p['first_sale'] for p in rows if p['first_sale'])),str(max(p['first_sale'] for p in rows if p['first_sale']))],
 }
 supplier_summaries=[]
 for s in sorted(set(x['supplier'] for x in rows)):
  group=[x for x in rows if x['supplier']==s]
  eligible=[x for x in group if x['status']=='ELEGIBLE']
  if not eligible:continue
  supplier_summaries.append({'supplier':s,'sku':len(eligible),'sku_buy':sum(x['suggest_pending']>0 for x in eligible),'total_with':sum(x['suggest_pending'] for x in eligible),'total_without':sum(x['suggest_without'] for x in eligible),'urgent':sum(x['risk_before_arrival']=='RIESGO' for x in eligible),'countries':', '.join(sorted(set(x['country'] for x in eligible)))})
 supplier_summaries.sort(key=lambda x:-x['total_with'])

 return {'stats':stat,'rows':rows,'supplier_summaries':supplier_summaries,'budget':{f'{y}_{c}_{m:02}':v for (y,c,m),v in budget.items()},'forecasts':{sku:{f'{ch}_{m.isoformat()}':val for (ch,m),val in dic.items()} for sku,dic in forecasts.items()}}
