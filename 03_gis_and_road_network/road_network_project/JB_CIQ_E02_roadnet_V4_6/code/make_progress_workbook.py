from artifact_tool import Workbook, SpreadsheetFile
import pathlib,csv
root=pathlib.Path(__file__).resolve().parents[1]
wb=Workbook.create()

def rows(path):
 with open(path,encoding='utf-8-sig',newline='') as f:return list(csv.reader(f))

def add_sheet(name, matrix, widths=None):
 sh=wb.worksheets.add(name)
 if not matrix:return sh
 ncol=max(len(x) for x in matrix)
 matrix=[r+['']*(ncol-len(r)) for r in matrix]
 sh.get_range_by_indexes(0,0,len(matrix),ncol).values=[[None if c=='' else convert(c) for c in r] for r in matrix]
 h=sh.get_range_by_indexes(0,0,1,ncol)
 h.format={'fill':'#123B5D','font':{'bold':True,'color':'#FFFFFF'},'row_height':26,'wrap_text':True}
 sh.freeze_panes.freeze_rows(1)
 for i in range(ncol):
  col=chr(65+i) if i<26 else 'A'+chr(65+i-26)
  sh.get_range(f'{col}:{col}').format.column_width=widths[i] if widths and i<len(widths) else (20 if i==0 else 23)
 return sh

def convert(s):
 if isinstance(s,str):
  if s.isdecimal() and len(s)<10:return int(s)
  try:
   v=float(s)
   if -1e8<v<1e8 and any(ch in s for ch in '.eE'):return v
  except:pass
 return s

add_sheet('验收看板',[
 ['项目','当前状态','数据/证据','放行条件'],
 ['E01交通清洗','基础完成，历史来源限制留档','345节点；2026-05-01至09-30；1,266,840节点小时','本期不重复检查9月'],
 ['E02-1 地理点位','通过预检','19个地域参考点；345节点坐标完整','地块与起降准入仍未知'],
 ['E02-2 道路源','未取得','OSM下载端点当前DNS不可达','下载真实OSM并保存元数据/哈希'],
 ['E02-3 网络方向','程序测试通过','合成数据单行线逆行排除测试通过','使用真实OSM后需额外检查转向限制'],
 ['E02-4 FCD道路匹配','等待路网','实际方向未知；匹配程序会只导出候选','所有正式用于速度标定的样本有方向证据'],
 ['E02-5 路由OD','只有参考OD 128方向对','A:56，B:72；不包含CIQ本体','真实路网/独立导航证据/真实D1D2订单'],
 ['E03天气','用户并行下载','ERA5/NASA文件未在本包校验','入库后按E03标准单独验收'],
 ['E04联合数据','未开始','道路与气象键已定义','E02/E03验收后统一时间空间键']
 ],[22,28,43,44])
add_sheet('19地点初筛',rows(root/'outputs'/'01_site_scope_audit.csv'),[13,10,42,20,20,25,38,34])
add_sheet('345点范围',rows(root/'outputs'/'02_345node_scope_audit.csv'),[14,11,19,19,22,20,20])
add_sheet('OD参考对128',rows(root/'outputs'/'03_reference_OD_pairs_NOT_ORDERS.csv'),[10,18,18,35,35,18,35,26])
add_sheet('E02证据缺口',rows(root/'docs'/'E02_验收与下一阶段任务.csv'),[15,36,48,64,20,20])
check=wb.inspect({'kind':'table','range':'验收看板!A1:D9','include':'values','table_max_rows':10,'table_max_cols':4})
print(str(check.ndjson)[:1600])
path=root/'JB_CIQ_E02_路网建设与证据验收_V4.6.xlsx'
SpreadsheetFile.export_xlsx(wb).save(str(path))
print('EXPORTED',path,path.stat().st_size)
