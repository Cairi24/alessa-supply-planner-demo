"""ALESSA Supply Planner V7 — demostración web con datos 100 % ficticios."""
from __future__ import annotations
import hashlib
import base64
import json
import math
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import quote
import sqlite3
import pandas as pd
import streamlit as st
from engine import DEFAULT_DATE, PROTECTIONS, evaluate, validate_order
from excel_export import full_plan, supplier_order
from cube_loader import load_cube

APP_DIR=Path(__file__).resolve().parent
BASE_DATA=APP_DIR/'data'/'demo_sintetico.json'
DB_PATH=APP_DIR/'compras_aprobadas_local.db'  # No se utiliza en la DEMO web

st.set_page_config(page_title='ALESSA | Supply Planner · Demo Web V9',page_icon='📦',layout='wide',initial_sidebar_state='expanded')
st.markdown('''<style>
:root{--alessa-blue:#0054B9;--alessa-deep:#0B5185;--alessa-yellow:#FFD302;--alessa-red:#EF1E25;--alessa-amber:#FFB504;--alessa-bg:#F5F8FC;}
[data-testid="stAppViewContainer"]{background:var(--alessa-bg);}
[data-testid="stAppViewContainer"]::before{content:"";position:fixed;inset:0 0 auto 0;height:7px;background:linear-gradient(90deg,var(--alessa-blue) 0 49%,var(--alessa-yellow) 49% 77%,var(--alessa-red) 77% 100%);z-index:9999;pointer-events:none;}
[data-testid="stSidebar"]{background:linear-gradient(170deg,#0054B9 0%,#075A9D 55%,#093E71 100%);border-right:6px solid var(--alessa-yellow);}
[data-testid="stSidebar"] *{color:#ffffff;}
[data-testid="stSidebar"] [data-testid="stFileUploader"]{background:rgba(255,255,255,.09);border-radius:12px;padding:9px;border:1px solid rgba(255,211,2,.35);}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"]{background:rgba(255,255,255,.95);}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] *{color:#074880!important;}
[data-testid="stSidebar"] div[role="radiogroup"] label{border-radius:9px;padding:6px 9px;transition:background .2s ease;}
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked){background:#FFD302;box-shadow:inset 5px 0 0 #EF1E25;}
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) *{color:#063B78!important;font-weight:700;}
[data-testid="stMetric"]{border:1px solid #dce6f0;border-top:4px solid #FFD302;border-radius:13px;background:white;padding:12px 16px;box-shadow:0 4px 11px rgba(3,54,106,.04);}
h1,h2,h3{color:#074F93;}
[data-testid="stDataFrame"],[data-testid="stDataEditor"]{border:1px solid #d2dfec;border-radius:10px;overflow:hidden;}
.stButton>button[kind="primary"]{background:#EF1E25!important;border-color:#EF1E25!important;color:#ffffff!important;font-weight:700!important;}
.stButton>button[kind="primary"]:hover{background:#C90A17!important;border-color:#C90A17!important;}
.stDownloadButton>button{background:#FFD302!important;border:1px solid #E7B900!important;color:#063F7D!important;font-weight:700!important;}
.stDownloadButton>button:hover{background:#FFC400!important;border-color:#D4A900!important;}
.stLinkButton>a{border-color:#0054B9!important;color:#0054B9!important;}
[data-baseweb="select"]:focus-within,[data-baseweb="input"]:focus-within{outline:2px solid #FFD302!important;outline-offset:1px;}
.brand-box{display:flex;align-items:center;gap:10px;padding:12px 0 16px;border-bottom:3px solid #FFD302;}
.brand-box img{width:92px;height:92px;object-fit:cover;border-radius:9px;border:2px solid #FFD302;box-shadow:0 3px 10px rgba(0,0,0,.16);}
.brand-box .brand-title{font-size:1.24rem;font-weight:800;color:#ffffff;line-height:1.1;}
.brand-box .brand-sub{font-size:.69rem;color:#ffe274;letter-spacing:.055em;line-height:1.5;}
.brand-hero{background:linear-gradient(112deg,#064d91 0%,#0054b9 65%,#0b67aa 100%);border-radius:16px 16px 0 0;padding:21px 26px 19px;color:#fff;box-shadow:0 9px 24px rgba(0,74,158,.10);display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:0;}
.brand-hero h1{font-size:1.54rem;font-weight:780;margin:0;color:#fff;line-height:1.3;}
.brand-hero p{font-size:.88rem;color:#dcefff;margin:5px 0 0;}
.brand-hero .hero-mark{color:#0054b9;background:#FFD302;border:2px solid #EF1E25;border-radius:18px;font-weight:850;font-size:.75rem;white-space:nowrap;padding:9px 13px;}
.brand-stripe{height:10px;border-radius:0 0 12px 12px;background:linear-gradient(90deg,#FFD302 0 74%,#FFB504 74% 86%,#EF1E25 86% 100%);margin-bottom:20px;}
.brand-section{display:inline-flex;align-items:center;gap:8px;font-weight:750;color:#054A8A;margin:8px 0 10px 0;}
.brand-section::before{content:"";width:6px;height:20px;border-radius:3px;background:#EF1E25;}
.brand-chip{display:inline-block;border-radius:999px;background:#FFF3B0;color:#074880;border:1px solid #F5C500;font-size:.76rem;padding:5px 11px;font-weight:700;}
@media(max-width:800px){.brand-hero h1{font-size:1.14rem}.brand-hero{padding:15px}.brand-hero .hero-mark{font-size:.65rem;padding:6px 8px}}

/* V7: legibilidad sobre fondos blancos y azul institucional */
[data-testid="stAppViewContainer"]{color:#153857!important;}
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] p,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] label,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] [data-testid="stWidgetLabel"] *,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] [data-testid="stCaptionContainer"] *,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] [data-testid="stMetricLabel"] *,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] [data-testid="stMetricValue"] *,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] [data-testid="stMarkdownContainer"] li{color:#153857!important;opacity:1!important;}
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] [data-baseweb="select"] > div,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] [data-baseweb="input"] > div,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] [data-baseweb="base-input"] {background:#ffffff!important;border-color:#aabdd0!important;color:#153857!important;}
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] input,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] [data-baseweb="select"] span,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] [data-baseweb="select"] div{color:#153857!important;-webkit-text-fill-color:#153857!important;}
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] input::placeholder{color:#61768b!important;opacity:1!important;}
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] [data-testid="stMetric"]{background:#ffffff!important;}
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] [data-testid="stMetric"] label,
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] [data-testid="stMetric"] [data-testid="stMetricValue"]{color:#123d64!important;opacity:1!important;}
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] [data-testid="stAlert"] p{color:inherit!important;}
[data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"] [data-testid="stDataEditor"]{color:#153857;}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] *{color:#fff!important;}
[data-testid="stSidebar"] [data-baseweb="select"] *,[data-testid="stSidebar"] input{color:#123d64!important;}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] *{color:#e3eeff!important;}
/* El azul, amarillo y rojo son parte del diseño, no solo estados. */
.brand-hero p{color:#e8f4ff!important}.brand-hero h1{color:#fff!important}
.stDownloadButton>button p{color:#063F7D!important}
.stButton>button[kind="primary"] p{color:#fff!important}
</style>''',unsafe_allow_html=True)

@st.cache_data(show_spinner='Leyendo la información del cubo desde Excel…')
def parse_excel(content:bytes):
    # El lector espera las 7 hojas originales en el mismo orden y el corte del piloto.
    with NamedTemporaryFile(suffix='.xlsx',delete=False) as f:
        f.write(content)
        path=f.name
    try:
        return load_cube(path)
    finally:
        Path(path).unlink(missing_ok=True)

@st.cache_data
def load_demo():
    return json.loads(BASE_DATA.read_text(encoding='utf-8'))

def save_approval(supplier,source_hash,scenario,cover,unit,with_pending,lines):
    # Demostración web: NO guarda aprobaciones en disco ni en una base compartida.
    # La aprobación solo existe en session_state del visitante actual.
    return None

def fmt(n):return f'{int(n):,}'.replace(',','.')

def init_state(source_hash):
    if st.session_state.get('active_source')!=source_hash:
        st.session_state.active_source=source_hash
        st.session_state.manual={}
        st.session_state.cover_overrides={}
        st.session_state.approved=None

with st.sidebar:
    logo_path=APP_DIR/'alessa_logo.png'
    if logo_path.exists():
        st.markdown("<div class='brand-box'><img src='data:image/png;base64,%s'/><div><div class='brand-title'>ALESSA</div><div class='brand-sub'>SUPPLY PLANNER · DEMO WEB V9</div></div></div>" % base64.b64encode(logo_path.read_bytes()).decode('ascii'), unsafe_allow_html=True)
    else:
        st.markdown('## 📦 ALESSA')
        st.caption('SUPPLY PLANNER · DEMO WEB V9')
    st.divider()
    page=st.radio('Módulo', ['📋 Plan de compras','🚨 Alertas','📈 Forecast','📁 Datos'],label_visibility='collapsed')
    st.divider()
    st.markdown('**Origen de información**')
    st.info('DEMO PÚBLICA · DATOS FICTICIOS. No cargues datos comerciales ni de proveedores reales.')
    source_hash='DEMO_SINTETICA_V9'
    data=load_demo()
    init_state(source_hash)
    st.success('Demostración lista · 36 SKU ficticios')
    st.caption('La carga de archivos está deshabilitada para evitar exponer información empresarial.')

st.markdown('''<div class="brand-hero"><div><h1>Planificación inteligente de abastecimiento</h1><p>ALESSA S.A. · Datos ficticios · Retail + Mayorista</p></div><div class="hero-mark">SUPPLY PLANNER · DEMO V9</div></div><div class="brand-stripe"></div>''',unsafe_allow_html=True)
st.warning('DEMOSTRACIÓN WEB · DATOS FICTICIOS · No se almacena información ni se realizan pedidos reales. No subas archivos comerciales.')

if page=='📁 Datos':
    st.subheader('Administración de datos')
    st.info('Esta edición web utiliza exclusivamente datos ficticios. La carga de Excel real estará disponible únicamente en una instalación privada autorizada.')
    c1,c2,c3=st.columns(3)
    c1.metric('SKU con inventario',data['stats']['inventario_skus'])
    c2.metric('SKU elegibles',data['stats']['eligible'])
    c3.metric('SKU con menos de 6 meses',data['stats']['eligible_under6'])
    st.markdown('#### Hojas esperadas')
    st.table(pd.DataFrame({'Hoja':['Cantidad vendida SKU Retail','Cantidad vendida SKU Mayorista',
          'Inventario por SKU','Plan de venta por Sub categoría','Ventas por SKU Retail',
          'Ventas por SKU Mayorista','Frecuencia de compra por sku'],
          'Uso':['Forecast por canal','Forecast por canal','Stock, pendiente y empaque',
          'Presupuesto mensual','Ventas en dólares (consulta)','Ventas en dólares (consulta)',
          'País de fabricación y último proveedor']}))
    st.warning('La estructura actual del lector corresponde a la extracción del cubo de noviembre de 2026. La adaptación a nuevas fechas, columnas y hojas es una tarea pendiente antes de usarlo operativamente.')
    st.caption('No incluye datos reales de ALESSA. No se conectan sistemas corporativos.')
    st.stop()

if page=='📈 Forecast':
    st.subheader('Proyección mensual por canal')
    st.caption('Se muestran cantidades base de Retail y Mayorista, sin multiplicadores de protección.')
    vendor_names=sorted({p.get('supplier','SIN PROVEEDOR') for p in data['rows']})
    selected_vendor=st.selectbox('Proveedor', ['Todos']+vendor_names)
    names=[p for p in data['rows'] if selected_vendor=='Todos' or p.get('supplier')==selected_vendor]
    codes={p['sku']:p['desc'] for p in names}
    sku=st.selectbox('SKU', ['Todos']+sorted(codes),format_func=lambda s:'Todos los SKU' if s=='Todos' else f'{s} · {codes[s][:85]}')
    skus=[sku] if sku!='Todos' else list(codes)
    agg={}
    for s in skus:
        for key,val in data['forecasts'].get(s,{}).items():
            channel,month=key.split('_',1)
            if '2027' not in month:continue
            agg.setdefault(month,{'Retail':0,'Mayorista':0})[channel]+=float(val)
    forecast_df=pd.DataFrame([{'Mes':m,'Retail':round(v['Retail']), 'Mayorista':round(v['Mayorista'])}
                              for m,v in sorted(agg.items())])
    if not forecast_df.empty:
        st.bar_chart(forecast_df.set_index('Mes')[['Retail','Mayorista']])
        st.dataframe(forecast_df,hide_index=True,use_container_width=True)
    st.info('Las ferias mayoristas de enero, marzo, agosto y octubre se tratan como eventos estacionales explícitos. El forecast mensual es preliminar y debe contrastarse con ventas reales en un backtest.')
    st.stop()

if page=='🚨 Alertas':
    st.subheader('Alertas de abastecimiento y presupuesto')
    rows=evaluate(data)
    endangered=[p for p in rows if p.get('risk')=='RIESGO' and p.get('status')=='ELEGIBLE' and float(p['months_inv'])<6]
    c1,c2,c3=st.columns(3)
    c1.metric('SKU con riesgo antes de llegada',len(endangered))
    c2.metric('SKU sin venta positiva',sum(p['status']=='SIN VENTA POSITIVA' for p in rows))
    c3.metric('SKU elegibles bajo 6 meses',sum(p['status']=='ELEGIBLE' and float(p['months_inv'])<6 for p in rows))
    st.warning('El riesgo no considera fechas de recepción de pedidos pendientes, porque no están disponibles. El calendario de feriados es provisional.')
    tab1,tab2=st.tabs(['Riesgos por SKU','Presupuesto 2027 · unidades'])
    with tab1:
        risk_df=pd.DataFrame([{'SKU':p['sku'],'Producto':p['desc'],'Proveedor':p['supplier'],
              'Meses Inv':float(p['months_inv']),'Stock':p['stock'],
              'Demanda antes de llegar':p['lead_demand_calc'],'Fecha estimada':p['arrival']}
              for p in endangered]).sort_values('Meses Inv') if endangered else pd.DataFrame()
        st.dataframe(risk_df,hide_index=True,use_container_width=True,height=520)
    with tab2:
        st.caption('Plan 2027 EN REVISIÓN. Comparación orientativa entre presupuesto por subcategoría y forecast de los SKU presentes en INVENTARIO; no representa capacidad real de cumplimiento.')
        agg={}
        for sku,fc in data['forecasts'].items():
            for key,qty in fc.items():
                ch,m=key.split('_',1)
                if m.startswith('2027-'):
                    agg[(ch,m[0:7])]=agg.get((ch,m[0:7]),0)+float(qty)
        compare=[]
        for i in range(1,13):
            month=f'2027-{i:02d}'
            rplan=float(data['budget'].get(f'2027_Retail_{i:02d}',0))
            wplan=float(data['budget'].get(f'2027_Mayorista_{i:02d}',0))
            compare.append({'Mes':month,'Plan Retail':round(rplan),'Forecast Retail':round(agg.get(('Retail',month),0)),
                  'Plan Mayorista':round(wplan),'Forecast Mayorista':round(agg.get(('Mayorista',month),0))})
        st.dataframe(pd.DataFrame(compare),use_container_width=True,hide_index=True)
        st.info('Faltan precio mayorista, inventario valorizado y presupuesto en dólares para el semáforo monetario por subcategoría.')
    st.stop()

# ------------ Pantalla principal ------------
st.markdown('<div class="brand-section">Plan de compras por SKU</div>',unsafe_allow_html=True)
st.markdown('<span class="brand-chip">Orden automático · Meses Inv de menor a mayor</span>',unsafe_allow_html=True)
with st.container(border=True):
    r1,r2,r3,r4=st.columns([2.5,2,1.6,1.4])
    providers=sorted({p.get('supplier','SIN PROVEEDOR') for p in data['rows']})
    supplier=r1.selectbox('Proveedor', ['Todos']+providers)
    cats=sorted({p.get('category','SIN SUBCATEGORÍA') for p in data['rows']})
    category=r2.selectbox('Subcategoría', ['Todas']+cats)
    protection=r3.selectbox('Protección',['Alta','Base','Moderada','Máxima'])
    with r4:
        st.markdown('<div style="height:27px"></div>',unsafe_allow_html=True)
        with_pending=st.checkbox('Descontar pendientes',value=True,help='Solo de la necesidad total, sin suponer fecha de llegada')
    r5,r6,r7=st.columns([1,1.2,3.5])
    unit=r5.selectbox('Unidad de cobertura',['Meses','Días'])
    cover=r6.number_input('Cobertura después de llegada',min_value=1,max_value=365 if unit=='Días' else 12,
                          value=120 if unit=='Días' else 4,step=1)
    search=r7.text_input('Buscar SKU o descripción',placeholder='Escribe un código o nombre de producto…')

rows=evaluate(data,order_date=DEFAULT_DATE,coverage=cover,unit=unit,protection=protection,
              with_pending=with_pending,coverage_overrides=st.session_state.cover_overrides)
# V8: filtros para TODAS las columnas de la tabla. Los selectores de Riesgo y
# Elegibilidad usan exactamente las categorías mostradas en el motor.
# Streamlit data_editor no ofrece desplegables dentro de cada encabezado;
# se ubican inmediatamente encima de la tabla editable.
with st.expander('🔎 FILTROS POR COLUMNA · Abrir para seleccionar valores de cada campo', expanded=True):
    st.caption('Elige categorías o introduce un rango. Todos los filtros se combinan. Puedes limpiar todo de una vez.')
    a,b,c,d=st.columns([1,2.2,2,1.2])
    col_sku=a.text_input('SKU',key='f8_sku',placeholder='Buscar código')
    col_desc=b.text_input('Descripción',key='f8_desc',placeholder='Buscar producto')
    col_supplier=c.selectbox('Proveedor',['Todos']+sorted({p['supplier'] for p in rows}),key='f8_supplier')
    col_country=d.selectbox('País',['Todos']+sorted({str(p['country']) for p in rows}),key='f8_country')
    e,f,g,h=st.columns(4)
    col_pack=e.selectbox('Empaque mayor',['Todos']+sorted({int(p['pack']) for p in rows}),key='f8_pack',format_func=lambda v:'Todos' if v=='Todos' else str(v))
    col_risk=f.selectbox('Riesgo',['Todos','RIESGO','SIN RIESGO','REVISAR'],key='f8_risk',format_func=lambda v:{'RIESGO':'Riesgo','SIN RIESGO':'Sin riesgo','REVISAR':'Revisar','Todos':'Todos'}.get(v,v))
    col_status=g.selectbox('Elegibilidad',['Todas']+sorted({str(p['status']) for p in rows}),key='f8_status')
    col_arrival=h.text_input('Llegada estimada',key='f8_arrival',placeholder='AAAA-MM')
    st.markdown('**Rangos numéricos · Deja vacío para no limitar**')
    numeric_fields=[
      ('Meses Inv','months_inv'),('Stock','stock'),('Pendiente','pending'),
      ('Cobertura','coverage_value'),('Sugerido','suggested'),
      ('Bultos sugeridos','suggested_bultos'),('Compra final','purchase_qty'),
      ('Bultos finales','final_bultos')]
    numeric_filters={}
    for offset in (0,4):
        cells=st.columns(4)
        for i,(label,field) in enumerate(numeric_fields[offset:offset+4]):
            with cells[i]:
                st.caption(label)
                left,right=st.columns(2,gap='small')
                lo=left.text_input('Mín.',key='f8_'+field+'_min',placeholder='Mín',label_visibility='collapsed')
                hi=right.text_input('Máx.',key='f8_'+field+'_max',placeholder='Máx',label_visibility='collapsed')
                numeric_filters[field]=(lo,hi)
    if st.button('🧹 Limpiar filtros por columna',key='f8_clear'):
        for key in list(st.session_state):
            if key.startswith('f8_') and key!='f8_clear':del st.session_state[key]
        st.rerun()

def _parse_boundary(value):
    if not str(value).strip():return None
    try:return float(str(value).strip().replace(',','.'))
    except ValueError:return None

def _value_for_filter(p,field):
    if field=='suggested_bultos':return p['suggested']//p['pack'] if p['pack'] else 0
    if field=='purchase_qty':return int(st.session_state.manual.get(p['sku'],p['suggested']))
    if field=='final_bultos':
        q=int(st.session_state.manual.get(p['sku'],p['suggested']))
        return q/p['pack'] if p['pack'] else 0
    return p[field]

filtered=[p for p in rows if (supplier=='Todos' or p['supplier']==supplier)
          and (category=='Todas' or p['category']==category)
          and (not search or search.lower() in (p['sku']+' '+p['desc']).lower())
          and (not col_sku or col_sku.lower() in str(p['sku']).lower())
          and (not col_desc or col_desc.lower() in str(p['desc']).lower())
          and (col_supplier=='Todos' or p['supplier']==col_supplier)
          and (col_country=='Todos' or str(p['country'])==col_country)
          and (col_pack=='Todos' or int(p['pack'])==col_pack)
          and (col_risk=='Todos' or p['risk']==col_risk)
          and (col_status=='Todas' or p['status']==col_status)
          and (not col_arrival or col_arrival.lower() in str(p['arrival']).lower())
          and all(((_parse_boundary(lo) is None or float(_value_for_filter(p,k))>=_parse_boundary(lo))
                   and (_parse_boundary(hi) is None or float(_value_for_filter(p,k))<=_parse_boundary(hi)))
                  for k,(lo,hi) in numeric_filters.items())]

filter_active=bool(col_sku or col_desc or col_arrival or col_supplier!='Todos' or col_country!='Todos'
                   or col_pack!='Todos' or col_risk!='Todos' or col_status!='Todas'
                   or any(lo.strip() or hi.strip() for lo,hi in numeric_filters.values()))
# Meses Inv ascending is the sole default sort criterion.
filtered.sort(key=lambda p:(float(p['months_inv']),p['sku']))
manual=st.session_state.manual
for p in filtered:
    p['purchase_qty']=int(manual.get(p['sku'],p['suggested']))
    p['bultos']=p['purchase_qty']//p['pack'] if p['pack'] else 0

k1,k2,k3,k4=st.columns(4)
k1.metric('SKU visibles',fmt(len(filtered)))
k2.metric('Compra final · unidades',fmt(sum(p['purchase_qty'] for p in filtered)))
k3.metric('SKU con compra',fmt(sum(p['purchase_qty']>0 for p in filtered)))
k4.metric('SKU bajo 6 meses',fmt(sum(float(p['months_inv'])<6 for p in filtered)))

st.markdown('<div class="brand-section">Tabla editable · Plan de compras</div>',unsafe_allow_html=True)
st.caption('Usa el bloque «FILTROS POR COLUMNA» encima de la tabla para seleccionar Riesgo, Sin riesgo o Revisar y los valores de las demás columnas. Edita «Cobertura» y «Compra final» directamente en las celdas. Se mantienen visibles la sugerencia original, el stock, la fecha de llegada y los bultos. Las compras finales deben respetar el empaque mayor.')
view=pd.DataFrame([{
    'SKU':p['sku'],'Descripción':p['desc'],'Proveedor':p['supplier'],
    'País':p['country'],'Empaque mayor':int(p['pack']),
    'Meses Inv ↑':float(p['months_inv']),'Stock':int(p['stock']),
    'Pendiente':int(p['pending']),
    'Llegada estimada':p['arrival'],'Cobertura':float(p['coverage_value']),
    'Sugerido':int(p['suggested']),'Bultos sugeridos':int(p['suggested']//p['pack'] if p['pack'] else 0),
    'Compra final':int(p['purchase_qty']),'Bultos finales':int(p['bultos']),
    'Riesgo':p['risk'],'Elegibilidad':p['status']
} for p in filtered])
key_params=json.dumps([source_hash,supplier,category,search,protection,unit,cover,with_pending, sorted((k,str(v)) for k,v in st.session_state.items() if k.startswith('f8_'))],ensure_ascii=False)
widget_key='editor_'+hashlib.md5(key_params.encode()).hexdigest()[:16]
modified=st.data_editor(
    view, hide_index=True, use_container_width=True,height=490,
    column_order=list(view.columns),
    disabled=[c for c in view.columns if c not in ('Cobertura','Compra final')],
    column_config={
        'SKU':st.column_config.TextColumn('SKU',width='small'),
        'Descripción':st.column_config.TextColumn('Descripción',width='large'),
        'Meses Inv ↑':st.column_config.NumberColumn('Meses Inv ↑',format='%.2f'),
        'Compra final':st.column_config.NumberColumn('Compra final ✎',min_value=0,step=1,format='%d'),
        'Cobertura':st.column_config.NumberColumn(f'Cobertura ({unit}) ✎',min_value=0.0,step=1.0),
        'Sugerido':st.column_config.NumberColumn('Sugerido',format='%d'),
        'Bultos sugeridos':st.column_config.NumberColumn('Bultos sugeridos',format='%d'),
        'Bultos finales':st.column_config.NumberColumn('Bultos finales',format='%d')
    },key=widget_key
)
changed_cover=False
changed_qty=False
if len(modified):
    for rec in modified.to_dict('records'):
        sku=str(rec['SKU']);original=next((p for p in filtered if p['sku']==sku),None)
        if original is None:continue
        try:raw_cover=float(rec['Cobertura'])
        except (ValueError,TypeError):raw_cover=float(original['coverage_value'])
        if math.isfinite(raw_cover) and raw_cover>=0 and raw_cover!=float(original['coverage_value']):
            st.session_state.cover_overrides[sku]=raw_cover
            changed_cover=True
        try:raw_qty=float(rec['Compra final'])
        except (ValueError,TypeError):continue
        if math.isfinite(raw_qty) and raw_qty>=0 and raw_qty.is_integer() and int(raw_qty)!=original['purchase_qty']:
            st.session_state.manual[sku]=int(raw_qty)
            changed_qty=True
    if changed_cover or changed_qty:st.rerun()

# Update approval state from quantities; approval tied to current exact order, not mutable result.
for p in filtered:
    p['purchase_qty']=int(st.session_state.manual.get(p['sku'],p['suggested']))
    p['bultos']=p['purchase_qty']//p['pack'] if p['pack'] else 0
errors=validate_order(filtered,{p['sku']:p['purchase_qty'] for p in filtered})
if errors:st.error(f'Corrige las cantidades de estos SKU a múltiplos del empaque mayor: {", ".join(errors[:14])}'+('…' if len(errors)>14 else ''))

snapshot=[{'sku':p['sku'],'desc':p['desc'],'quantity':p['purchase_qty']} for p in filtered if p['purchase_qty']>0]
approval_context={'source':source_hash,'supplier':supplier,'scenario':protection,'unit':unit,'coverage':cover,'with_pending':with_pending,'overrides':st.session_state.cover_overrides,'lines':snapshot}
order_digest=hashlib.sha256(json.dumps(approval_context,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
is_approved=(st.session_state.approved or {}).get('hash')==order_digest and (st.session_state.approved or {}).get('supplier')==supplier
c1,c2=st.columns([1.2,1.3])
with c1:
    st.download_button('⬇️ Exportar plan interno Excel editable',data=full_plan(filtered),
                       file_name='ALESSA_Plan_Compras_Editable.xlsx',
                       mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',use_container_width=True)
with c2:
    can_approve=(supplier!='Todos' and category=='Todas' and not search and not errors and len(snapshot)>0 and not filter_active)
    if st.button('✅ Aprobar pedido de este proveedor',type='primary',disabled=not can_approve or is_approved,use_container_width=True):
        save_approval(supplier,source_hash,protection,cover,unit,with_pending,snapshot)
        st.session_state.approved={'supplier':supplier,'hash':order_digest,'lines':snapshot}
        st.rerun()
if supplier=='Todos':st.caption('Para aprobar el pedido, selecciona un proveedor concreto. El plan interno puede exportarse con todos los proveedores.')
elif not can_approve and len(snapshot)>0:st.caption('Para aprobar el pedido completo, borra los filtros por columna y selecciona todas las subcategorías. Evitamos aprobar pedidos parciales por accidente.')

if is_approved:
    st.success(f'Pedido ficticio de {supplier} aprobado en esta sesión · {len(snapshot)} SKU · {fmt(sum(s["quantity"] for s in snapshot))} unidades')
    a,b,c=st.columns(3)
    with a:
        st.download_button('⬇️ Descargar pedido Excel (3 columnas)',
                           data=supplier_order(filtered,{p['sku']:p['purchase_qty'] for p in filtered}),
                           file_name='Pedido_'+''.join(ch if ch.isalnum() else '_' for ch in supplier)[:60]+'.xlsx',
                           mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',use_container_width=True)
    with b:
        subject=quote('Pedido de compra - '+supplier)
        body=quote('Estimados:\n\nAdjunto pedido de compra para su revisión.\n\nSaludos cordiales.')
        st.info('Correo deshabilitado en DEMO')
    with c:
        st.info('Outlook deshabilitado en DEMO')
    st.caption('DEMO: el correo no contiene adjuntos ni se envía automáticamente. No utilices esta opción para pedidos reales.')
else:
    st.caption('Demo web: las aprobaciones solo se conservan en esta sesión del navegador. No se registra ni envía ningún pedido real.')

with st.expander('ℹ️ Criterios y limitaciones del cálculo'):
    st.markdown('''- El modelo calcula **demanda hasta la llegada + demanda durante la cobertura solicitada**; descuenta inventario actual y, opcionalmente, pendientes sin fecha.
- La reposición automática aplica solo a SKU con **ventas positivas**, último ingreso desde **01/01/2025**, país/proveedor/empaque válidos y **Meses Inv menor a 6**.
- La nacionalización de importaciones suma **7 días hábiles**; compras locales: **10 días hábiles**. Los feriados son provisionales y no incluyen todas las excepciones empresariales/locales.
- Los niveles de protección son **factores orientativos** (Base 1,00; Moderada 1,15; Alta 1,30; Máxima 1,45); **no son percentiles calibrados**.
- El forecast disponible actualmente cubre **noviembre 2026 a diciembre 2027**. Si no alcanza el plazo solicitado, el SKU se marca para revisión y no se recomienda automáticamente.
- El lector de Excel se desarrolló para la **estructura concreta** del archivo piloto (7 hojas y esquema del cubo); nuevas extracciones pueden requerir un adaptador adicional.
- No calcula impuestos ni costos; las alertas monetarias por subcategoría esperan precio mayorista e inventario valorizado. No existen fechas de llegada para compras pendientes.''')
