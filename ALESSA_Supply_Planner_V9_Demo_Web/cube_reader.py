from zipfile import ZipFile
from xml.etree import ElementTree as ET
import re, collections, json, sys
P='/mnt/data/Ejemplo cubo de solo ventas por sku(5).xlsx'
ns='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
def colnum(s):
 n=0
 for a in re.match('[A-Z]+',s).group():n=n*26+ord(a)-64
 return n-1
class Reader:
 def __init__(self,p):
  self.z=ZipFile(p)
  self.s=[]
  if 'xl/sharedStrings.xml' in self.z.namelist():
   root=ET.fromstring(self.z.read('xl/sharedStrings.xml'))
   for si in root.findall(f'{ns}si'):
    self.s.append(''.join(t.text or '' for t in si.iter(f'{ns}t')))
  print('Shared strings',len(self.s), file=sys.stderr)
 def each(self,i):
  z=self.z
  with z.open(f'xl/worksheets/sheet{i}.xml') as f:
   for event,elem in ET.iterparse(f,events=('end',)):
    if elem.tag!=f'{ns}row':continue
    vals={}
    for cell in elem.findall(f'{ns}c'):
     ref=cell.get('r'); idx=colnum(ref)
     v=cell.find(f'{ns}v')
     if v is None:
      inline=cell.find(f'{ns}is')
      if inline is None:continue
      val=''.join(t.text or '' for t in inline.iter(f'{ns}t'))
     else:
      raw=v.text or ''
      t=cell.get('t')
      if t=='s':val=self.s[int(raw)]
      elif t in ('str','e'):val=raw
      else:
       try:val=float(raw)
       except:val=raw
     vals[idx]=val
    yield int(elem.get('r')),vals
    elem.clear()
if __name__=='__main__':
 r=Reader(P)
 for i in range(1,8):
  print('\n=== SHEET',i,'===')
  ct=0
  for num, data in r.each(i):
   if num<11 or (i in [3,4,7] and num<18): print(num,json.dumps(data,ensure_ascii=False,default=str)[:800])
   ct+=1
  print('ROWS',ct)
