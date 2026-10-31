from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from pathlib import Path
import json,csv
root=Path(__file__).resolve().parent
path=root/'STAGE05_FORMAL_AUDIT_20261030.docx'
D=Document(); section=D.sections[0];section.top_margin=Cm(2.1);section.bottom_margin=Cm(1.9);section.left_margin=Cm(2.3);section.right_margin=Cm(2.1)
styles=D.styles
normal=styles['Normal']; normal.font.name='Times New Roman';normal.font.size=Pt(9.1);normal.font.color.rgb=RGBColor(0,0,0);normal._element.rPr.rFonts.set(qn('w:eastAsia'),'Noto Sans CJK SC');normal.paragraph_format.space_after=Pt(4.5)
for name,size in [('Title',17),('Heading 1',12),('Heading 2',10)]:
 s=styles[name];s.font.name='Times New Roman';s.font.size=Pt(size);s.font.bold=True;s.font.color.rgb=RGBColor(0,0,0);s._element.rPr.rFonts.set(qn('w:eastAsia'),'Noto Sans CJK SC')
 s.paragraph_format.space_after=Pt(6)
header=section.header.paragraphs[0];header.text='CIQ DRONE LOGISTICS  |  SCI EVIDENCE CHAIN  |  STAGE 05';header.alignment=WD_ALIGN_PARAGRAPH.RIGHT;header.style='Normal';header.runs[0].font.size=Pt(8);header.runs[0].font.color.rgb=RGBColor(0,0,0)
footer=section.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.RIGHT
footer.add_run('STAGE 05 — AUDIT COPY    |    2026-10-30    |    PAGE ')
fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');footer._p.append(fld)

def title(t):
 p=D.add_paragraph()
 r=p.add_run(t);r.bold=True;r.font.size=Pt(15);r.font.color.rgb=RGBColor(0,0,0)
 p.paragraph_format.space_after=Pt(10)
def h(t,l=1): D.add_heading(t,l)
def p(t):D.add_paragraph(t)
def table(headers,rows,widths=None):
 t=D.add_table(rows=1, cols=len(headers)); t.style='Table Grid';t.alignment=WD_TABLE_ALIGNMENT.CENTER
 for i,x in enumerate(headers):
  t.rows[0].cells[i].text=str(x)
  for run in t.rows[0].cells[i].paragraphs[0].runs:run.bold=True
 for row in rows:
  for c,text in zip(t.add_row().cells,row):
   c.text=str(text)
   c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
 for tr in t.rows:
  for c in tr.cells:
   for para in c.paragraphs:
    para.paragraph_format.space_after=Pt(1)
    for run in para.runs:run.font.size=Pt(8)
 # prevent split table rows
 for tr in t.rows:
  pPr=tr._tr.get_or_add_trPr();no=OxmlElement('w:cantSplit');pPr.append(no)
 D.add_paragraph('')

title('Stage 05｜任务协议与燃油、双无人机参数审计')
p('CIQ 无人机物流 SCI 研究  |  正式版本：S05-AUDIT-v1  |  审计日期：2026-10-30  |  亚洲/吉隆坡')
p('审计裁定：PROTOCOL FROZEN / NUMERICAL PARAMETERS HOLD / MAIN EXPERIMENT DENIED')
h('1. 执行摘要')
p('本阶段没有启动 M0/M1/M2 运营仿真。以 GitHub 固定历史提交 4569817b8145efe2ae06f4b21addc1986f971c12 为只读证据基线，检查旧 Stage 6 计算公式与 Stage 8 F0/F1 机型文献，再核实制造商、IPCC、马来西亚和新加坡能源/航空机构的公开资料。')
p('已冻结：统一合成任务定义、同一订单/期限/负荷比较、三种模式服务边界、燃油 TTW 与电力核算的分类方法、缺失数据与禁止推断规则。已整理 42 项参数（其中 27 项 BLOCKED）、18 项释放门槛，以及只读检查程序；10 项合成自动测试通过。尚未冻结：油耗实测曲线、两机型的任务级能耗、成本定额、跨境许可及正式三分区网络。')
h('2. 研究对象与可比任务协议')
table(['项目','统一规则与科学意义'],[
('研究空间','柔佛新山—新加坡 CIQ；新区 A/B/C 以最终验收的 QGIS 多图层工程为准，不能以旧 19 点代替。'),
('任务基本单位','一个冻结的合成货运任务（task_id、种子、释放时刻、期限、重量、起终点、国家、区域）。所有模式保持一致。'),
('样本隔离','Stage 2 的 918,000 条工程重采样与 Stage 6 的 29,842 条合成任务不相加，也不视为独立实测订单。'),
('同服务基准','主比较为统一任务集合上的结果；同时报告 matched eligible cohort 与全样本不可评价率，禁止只取成功订单。'),
('跨境定义','依起终点所在国家与实际路线识别，而不是依据区域名称推断；旧 128 OD 全标记为非跨境。'),
('结果限制','可研究条件性场景的时间、成本和排放；不得宣称真实已批准的无人机跨境运输或实际节时减排。')])
h('3. 三模式冻结定义')
table(['模式','标准构型','需要计入的运营活动'],[
('M0','仅地面：汽油乘用车或柴油厢式车作为两个独立燃油基准情景','去程、回程、停车/等待、调头和库区再定位；边境等待单列；容量与服务等级匹配。'),
('M1','固定节点地面接驳 + 站点转运 + UAV 配送','集货/干线/前置节点、装卸与排队、起降、带载航程、空载回程、充电、失败后地面回退。'),
('M2','车辆–无人机协同发射、会合与回收','车辆路径与 UAV 并发，真实时序一致性，会合等待与回收，电池准备与车辆行驶共享里程仅计一次。')])
p('每个任务输出一个互斥的状态枚举：ON_TIME、LATE、FALLBACK_GROUND、WEATHER_BLOCKED、ROAD_UNREACHABLE、REGULATORY_UNVERIFIED、INPUT_MISSING 或 NOT_EVALUABLE（具体模型应再定唯一状态优先级）。未知值保持 NULL，不填 0。')
h('4. 双无人机官方参数核查')
table(['参数','DJI FlyCart 30（双 DB2000）','Wingcopter 198 Cargo'],[
('最大载荷','30 kg（双电池构型）','4.7 kg'),
('标称最大航程','满载 16 km；空载 28 km；无风等测试工况','up to 92 km；载荷与储备条件不明'),
('风阻标注','12 m/s','up to 18 m/s'),
('电池名义能量','1.9844 kWh/块 × 2 = 3.9688 kWh','未从 Cargo 官方页取得'),
('逐任务 kWh','未标定；禁止从最大航程倒推','未标定；不能借用通用 198 94 km'),
('放行类别','公开技术筛查通过；绝对排放计算阻断','公开技术筛查通过；绝对排放计算阻断')])
p('制造商公布的抗风数据只属于其适用工况，不等于降雨阈值、可用电量、安全储备、载重-风场-功率曲线或实际飞行许可。缺失参数不得以 Stage 6 Generic UAV 的 470 W、0.70 kWh 电池及 4 km 航段替代。来源：SRC01、SRC02。')
h('5. 燃油汽车基线：核算方法冻结，油耗数值不冻结')
p('对同一运输任务分别采用汽油乘用车与柴油厢式车情景，并注明容量、装载率、车辆来源、道路工况和燃料配比。使用 IPCC 2006 Tier 1 CO₂ 因子作为备选方法：汽油 69,300 kg CO₂/TJ、柴油 74,100 kg CO₂/TJ。实际 L/100 km、燃油密度（kg/L）与净热值（MJ/kg）未充分取得，因此不得报告有效 kg CO₂/订单。')
p('燃油消耗（L）= 经验证路线里程（km）× 经验证燃油率（L/100 km）÷100 + 不与前项重复的独立怠速燃油（L）。TTW CO₂（kg）= 消耗燃油（L）× 密度（kg/L）× NCV（MJ/kg）÷1,000,000（TJ/MJ）× EF（kg CO₂/TJ）。')
p('IPCC 燃油 TTW CO₂ 不含油井到油箱（WTT）排放。CH₄/N₂O 转换至 CO₂e 须另有对应燃料和车型排放因子及 GWP，不可未经说明把 CO₂ 结果直接改写为 CO₂e。来源：SRC03、SRC07。')
h('6. 电网因子与一致的碳核算边界')
table(['供应地区','公开因子','允许解释 / 禁止用法'],[
('马来西亚半岛','2024 暂定：0.740 kg CO₂e/kWh','参考值，不是 2026 实测；不能自动代表新加坡充电。'),
('新加坡','2024：0.402 kg CO₂/kWh','CO₂-only 值；不可直接与 MY 的 CO₂e 相加成严格的统一 CO₂e 总量。')])
p('主分析建议采用地域一致、气体种类一致的“运营 CO₂”或补齐各地区完整温室气体因子后采用“运营 CO₂e”；在此之前仅允许分国及分种类展示，不发布整体净减排百分比。电力排放按充电发生地分摊，不按配送目的地或起飞地点推断。充电墙端能耗应包含已验证的充电损耗及辅助用电，禁止将名义电池容量当作已消耗电量。来源：SRC04、SRC05、SRC06。')
h('7. 旧 Stage 6 公式的实际冲突')
p('已读取的历史脚本 run_stage6.py （Git blob SHA：1bbf7864ee9546b781f048d515c5d756da8752）将车辆里程乘以 0.23 kWh/km，并将车辆用电与无人机用电一起乘 0.740 kg CO₂e/kWh；这属于纯电地面车和 Generic UAV 情景，不能用作燃油汽车 TTW 基准。其 weather_ok 按订单释放小时判定，并在反向道路缺失时将前向距离/时间乘 2；这两项均须重新设计。')
p('原 Stage 8 F0/F1 审计已经确认 19/19 参考位置不是获准起降站，并强调 DJI/Wingcopter 不能直接从厂家最大航程得到实际任务能耗。新版输入须记录坐标系/版本哈希、道路端点合法性、限飞/待审批状态及两国边境边界。')
h('8. 监管与跨境场景')
p('CAAM 的 UAS 审批机制区分不同作业类型，包含 Special UAS Project 等途径；新加坡 CAAS 明确跨境 UA 飞行需相应跨境许可，商业作业还可能涉及 Operator Permit 与 Activity Permit。当前仓库未提供任何项目跨境飞行许可，因此实际部署状态必须为 NOT_AUTHORIZED / PERMIT_UNVERIFIED，不能把“情景可飞”当作“合规可飞”。可另设“监管允许的反事实情景”进行论文条件性敏感性分析，但图表中必须明确标注是假设而非获批运营。来源：SRC08–SRC10。')
h('9. Release gates：进入数值实验之前必须补齐')
table(['门槛组','本轮结果','最低通过证据'],[
('G01–G03 空间/任务','BLOCKED','完整三分区 QGIS、跨境识别、统一任务数据与哈希'),
('G04、G13 同任务/同服务协议','PROTOCOL FROZEN','真实输入下逐任务匹配与容量、回退、返回路径测试'),
('G05–G07 道路/天气','BLOCKED','新版有向 OD、口岸等待场景、实际起飞时段气象'),
('G08–G10 能耗/油耗','BLOCKED','两机型任务能耗及两类燃油车有来源油耗曲线'),
('G11 TTW CO₂ 方法','METHOD FROZEN','有来源燃油密度、净热值、车队参数'),
('G12 气体一致的电网因子','BLOCKED','同气体 CO₂ / CO₂e 因子与充电地点'),
('G14–G16 成本/空域/重跑','BLOCKED','成本/许可边界明确、依赖复现'),
('G17 核算层级','PROTOCOL FROZEN','运行时分开运营、上游与资产账'),
('G18 独立 smoke test','BLOCKED','真实冻结数据下的同任务核对报告')])
h('10. 结论与下一步')
p('审计最终裁定：S05-METHOD-PASS；S05-PARAMETERS-HOLD；S05-RUN-DENIED。本阶段已把“研究方法冻结”和“可运行参数冻结”严格分开。首要工作不是扩展实验矩阵，而是将最新版 QGIS 三分区坐标/道路图层和实际能耗/油耗来源接入审计文件；取得和哈希验证后，再逐订单开展小样本 smoke test，核对所有模式服务完整性与排放账，然后才有条件启动正式多种子实验。')
h('附录 A. 权威证据与可追溯位置')
p('制造商：SRC01 DJI FlyCart 30 官方规格；SRC02 Wingcopter 198 Cargo 货运型号规格。方法：SRC03 IPCC 2006 道路移动燃烧；SRC07 GHG Protocol。')
p('电网：SRC04 马来西亚能源委员会 2024 暂定半岛电网因子；SRC05/SRC06 新加坡 NCCS/EMA 2024 电网 CO₂ 因子。监管：SRC08 CAAM；SRC09/SRC10 CAAS 跨境与商业无人机许可。')
p('上述 URL、核验日期、具体来源条件以及 GitHub 固定提交/Blob SHA 见 records/source_registry.csv；每项参数的状态、单位及阻断说明见 records/stage05_parameter_registry.csv。')
D.save(path)
print(path)
