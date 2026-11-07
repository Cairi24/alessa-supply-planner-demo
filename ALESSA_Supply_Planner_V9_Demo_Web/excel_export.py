"""Exportaciones XLSX editables en memoria para la aplicación local."""
from io import BytesIO
import xlsxwriter

COLS=[('sku','Código interno'),('desc','Descripción'),('supplier','Proveedor'),
      ('category','Subcategoría'),('country','País de fabricación'),
      ('months_inv','Meses Inv'),('stock','Inventario actual'),('pending','Compras pendientes'),
      ('pack','Unidades por bulto'),('arrival','Disponibilidad estimada'),
      ('coverage_value','Cobertura solicitada'),('coverage_unit','Unidad de cobertura'),
      ('lead_demand_calc','Demanda hasta llegada'),('cover_demand_calc','Demanda posterior'),
      ('suggested','Compra sugerida'),('purchase_qty','Compra final'),('bultos','Bultos'),
      ('risk','Riesgo antes de llegada'),('status','Elegibilidad')]

def _workbook():
    f=BytesIO()
    w=xlsxwriter.Workbook(f, {'in_memory':True})
    return f,w

def full_plan(rows):
    f,wb=_workbook()
    ws=wb.add_worksheet('PLAN DE COMPRAS')
    head=wb.add_format({'bold':True,'bg_color':'#0054B9','font_color':'#FFFFFF',
                        'text_wrap':True,'valign':'vcenter'})
    inp=wb.add_format({'bg_color':'#FFF3B0','num_format':'#,##0'})
    norm=wb.add_format({'num_format':'#,##0'})
    decimal=wb.add_format({'num_format':'0.00'})
    ws.set_row(0,33)
    ws.set_tab_color('#FFD302')
    for c,(_,label) in enumerate(COLS):ws.write(0,c,label,head)
    for r,p in enumerate(rows,1):
        for c,(name,_) in enumerate(COLS):
            value=p.get(name,'')
            if name in ('sku','desc','supplier','category','country','arrival','coverage_unit','risk','status'):
                ws.write_string(r,c,str(value or ''))
            elif name=='purchase_qty':ws.write_number(r,c,int(value or 0),inp)
            elif name in ('months_inv','lead_demand_calc','cover_demand_calc','coverage_value'):
                ws.write_number(r,c,float(value or 0),decimal)
            else:ws.write_number(r,c,float(value or 0),norm)
    ws.autofilter(0,0,len(rows),len(COLS)-1)
    ws.freeze_panes(1,2)
    ws.set_column(0,0,17)
    ws.set_column(1,1,53)
    ws.set_column(2,4,24)
    ws.set_column(5,len(COLS)-1,19)
    ws.set_column(15,15,20)
    wb.close()
    return f.getvalue()

def supplier_order(rows,qty_by_sku):
    # Exactly 3 columns, without business sensitive planning fields.
    f,wb=_workbook()
    ws=wb.add_worksheet('PEDIDO')
    ws.set_tab_color('#EF1E25')
    ws.set_row(0,30)
    head=wb.add_format({'bold':True,'font_color':'#FFFFFF','bg_color':'#0054B9'})
    num=wb.add_format({'num_format':'#,##0'})
    for c,text in enumerate(['Código interno','Descripción','Cantidad por comprar']):ws.write(0,c,text,head)
    idx=1
    for p in rows:
        qty=int(qty_by_sku.get(str(p['sku']),p['suggested']))
        if qty<=0:continue
        ws.write_string(idx,0,str(p['sku']))
        ws.write_string(idx,1,str(p['desc']))
        ws.write_number(idx,2,qty,num)
        idx+=1
    ws.set_column(0,0,19);ws.set_column(1,1,58);ws.set_column(2,2,23)
    ws.freeze_panes(1,0)
    ws.autofilter(0,0,max(idx-1,0),2)
    wb.close()
    return f.getvalue()
