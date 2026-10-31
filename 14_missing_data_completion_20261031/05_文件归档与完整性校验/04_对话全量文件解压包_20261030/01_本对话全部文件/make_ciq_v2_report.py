from pathlib import Path
import csv,json
from docx import Document
from docx.shared import Inches,Cm,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
root=Path('/mnt/data/CIQ_V2_Carbon_First_Experiment_Plan_20261030')
out=root/'CIQ_V2_20261030_SCI_Experiment_Execution_Plan.docx'

def set_font(run,size=9,bold=None,color=None):
    run.font.name='Noto Sans CJK SC';run.font.size=Pt(size)
    if bold is not None:run.bold=bold
    if color is not None:run.font.color.rgb=RGBColor(*color)
    rpr=run._element.get_or_add_rPr(); rf=rpr.rFonts
    if rf is None:rf=OxmlElement('w:rFonts');rpr.insert(0,rf)
    rf.set(qn('w:eastAsia'),'Noto Sans CJK SC')

def addp(txt='',boldprefix='',style=None,space=5):
    p=doc.add_paragraph(style=style)
    if boldprefix and txt.startswith(boldprefix):set_font(p.add_run(boldprefix),9,bold=True);set_font(p.add_run(txt[len(boldprefix):]),9)
    else:set_font(p.add_run(txt),9)
    p.paragraph_format.space_after=Pt(space)
    return p

def title(s,l=1):
    h=doc.add_heading(s,level=l)
    h.paragraph_format.space_before=Pt(11 if l==1 else 7)
    h.paragraph_format.space_after=Pt(5)
    for run in h.runs:set_font(run,13 if l==1 else 10,bold=True,color=(18,45,68))
    return h

def table(headers,rows,widths=None):
    t=doc.add_table(rows=1, cols=len(headers));t.style='Table Grid';t.alignment=WD_TABLE_ALIGNMENT.CENTER
    for j,h in enumerate(headers):
        cell=t.rows[0].cells[j];cell.text='';set_font(cell.paragraphs[0].add_run(str(h)),8,bold=True,color=(18,45,68))
    for row in rows:
        cells=t.add_row().cells
        for j,val in enumerate(row):
            cells[j].text='';p=cells[j].paragraphs[0];p.paragraph_format.space_after=Pt(0)
            set_font(p.add_run(str(val)),7.7)
            cells[j].vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
    if widths:
        for row in t.rows:
            for cell,w in zip(row.cells,widths):cell.width=Cm(w)
    doc.add_paragraph().paragraph_format.space_after=Pt(1)
    return t

doc=Document();sec=doc.sections[0];sec.page_height=Cm(29.7);sec.page_width=Cm(21)
sec.top_margin=Cm(2.1);sec.bottom_margin=Cm(1.7);sec.left_margin=Cm(2.0);sec.right_margin=Cm(1.9)
styles=doc.styles
styles['Normal'].font.name='Noto Sans CJK SC';styles['Normal'].font.size=Pt(9)
styles['Normal'].paragraph_format.line_spacing=1.16
# header/footer
head=sec.header.paragraphs[0];head.alignment=WD_ALIGN_PARAGRAPH.RIGHT
set_font(head.add_run('CIQ 低碳地空协同物流 · V2 研究实施方案'),8,color=(100,110,120))
footer=sec.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
set_font(footer.add_run('Planning release · 2026-10-30 · Not an experimental result'),8,color=(100,110,120))

t=doc.add_paragraph();t.alignment=WD_ALIGN_PARAGRAPH.CENTER
set_font(t.add_run('CIQ 无人机物流 SCI 研究'),16,bold=True,color=(18,45,68))
t=doc.add_paragraph();t.alignment=WD_ALIGN_PARAGRAPH.CENTER
set_font(t.add_run('V2 剩余实验路线图与节点交付规范'),14,bold=True,color=(18,45,68))
t=doc.add_paragraph();t.alignment=WD_ALIGN_PARAGRAPH.CENTER
set_font(t.add_run('统一围绕汽油车基线、M1/M2 混合物流和运营碳减排'),10,bold=True)
addp('版本：V2_PLAN_20261030  |  历史 GitHub commit：4569817b8145efe2ae06f4b21addc1986f971c12  |  当前状态：PLANNING / MAIN RUN HOLD',space=8)

title('1. 科学目标与本轮最终结论口径')
addp('核心目标：在马来西亚—新加坡 CIQ 研究场景，以同一批冻结合成配送任务，比较汽油车纯道路模式 M0、固定接驳 M1、车辆—无人机同步协同 M2，判断在天气、道路拥堵、成本和服务约束下是否存在可复现的最低运营碳排放方案。')
table(['RQ','要回答的论文问题','能发布的证据'],[
['RQ1 选址与网络','哪些候选节点和连接在地理、任务、技术和监管筛查上具备条件性适用性？','完整新版 QGIS 节点/连接、接地道路、空域状态及证据分级'],
['RQ2 运营效率','什么时间/交通/风雨条件下地空协同较汽油车更快或更可靠？','相同订单 M0/M1/M2 逐单准时、完成、门到门时长、兜底状态'],
['RQ3 净减排与成本','满足服务和成本限制时，M1/M2 或机型配比能否降低运营 CO2？','汽油燃油账、充电国别碳账、成本与 Pareto 可行性/不确定性']],[2.5,7.0,7.7])
addp('不允许的表述：历史电动车+通用无人机情景减少排放 = 真实汽油车与两款实际机型净减排已验证；几何候选航段 = 获批商业飞行航线。',space=7)

title('2. 完整实验阶段、节点交付与先后依赖')
rows=[
['V2-S06','三分区 QGIS 与节点/航路/地理证据冻结','RQ1','节点/连接/ID 对照/空域排除 + SHA256'],
['V2-S07','合成订单—小时天气—有向道路/CIQ 时间对齐','RQ1–2','统一任务 ID/道路与天气联合表/质量复核'],
['V2-S08','汽油配送车 M0 基线与油耗模型','RQ2–3','汽油车次、油耗、成本、TTW CO2 台账'],
['V2-S09','DJI 与 Wingcopter 任务能耗与风雨筛查','RQ1–3','两款机型任务电耗区间、禁飞/回退原因'],
['V2-S10','M0/M1/M2 对照运行（5 类主模式）','RQ2–3','完整事件、车次和逐订单模式结果'],
['V2-S11','汽油+充电运营碳账与低碳约束优化','RQ3','同服务碳成本对照、可行 Pareto 前沿'],
['V2-S12','30 种子统计、联合敏感性、SCI Fig.3–7','RQ1–3','统计区间、图件源表、独立复算日志']]
table(['阶段','实验节点','RQ','每个节点最少产物'],rows,[2.2,6.1,1.6,7.3])
addp('工作可并行：完成 V2-S07 后，汽油车 M0 标定（S08）与双机任务能耗证据（S09）可并行推进；但 S10 主仿真必须同时通过两者与空间门槛。')

title('3. 五组主实验（统一任务、统一比较）')
addp('EXP00：汽油车 M0（主对照）；EXP01：汽油接驳 + DJI FlyCart 30 的 M1；EXP02：汽油接驳 + Wingcopter 198 Cargo 的 M1。')
addp('EXP03：汽油车 + DJI 同步会合的 M2；EXP04：汽油车 + Wingcopter 同步会合的 M2。五组使用完全相同的任务 ID、交通和气象记录。')
addp('附加情景：柴油 M0 参考；天气/拥堵压力测试；燃油、UAV 能耗和成本上限联合不确定性；跨境仅独立分层且不得从旧本地 OD 推导。优先使用 Stage6 的 29,842 条合成订单（30种子×5日），但只有新版空间逐条成功映射且任务总体再冻结后才可运行。')

title('4. 关键实验计算规则')
addp('公平性：五模式全部使用同一 task_population_id、task_id、seed、载重、释放时间、目的地、期限；无人机禁飞或故障须保留订单并记真实地面兜底延时，不允许只比较 UAV 成功订单。')
addp('道路：车辆去程、空驶、回程、转运、排队和怠速计入；同一物理车辆车次只记一次，车次共享成本和排放另做明示分摊。')
addp('碳：运营主口径按燃油车 TTW CO2 + 境内真实充电地电网 CO2 计；没有气体口径兼容的 MY/SG 电网因子时先分账展示，不把 CO2 与 CO2e 混加。禁止将最大航程折算为 UAV 每公里耗电。')
addp('最低碳最优：只在服务量、准时率、成本约束全部满足的情景里求最小碳；若不存在可行解，应明示 INFEASIBLE。资产制造和燃油上游排放另列敏感性，不混入运营 TTW 主值。')
addp('统计：原则上以 30 个冻结随机种子为配对重复单位；订单数和三模式输出行不是独立样本。固定五日结果不代表五个月逐日数据。')

title('5. 17 项释放门槛与当前真实状态')
addp('门槛分类：S06 空间和 airspace；S07 任务/风雨/道路；S08 汽油基线；S09 两机能耗；S10 状态机小样本与全量；S11 完整碳账/成本与最优；S12 独立复现与 SCI 图表。全包 `control/MASTER_RELEASE_GATES.csv` 逐项列出。')
addp('现状：17 项全部 BLOCKED（这是“尚未取得或通过新实验依据”，不是历史研究失败）。当前最新三分区 QGIS 主工程/依赖未在本次访问中取得；汽油车油耗模型和两机实际任务功耗也未冻结。因此本包没有生成任何“新计算的时间、成本、碳减排数值”。')

title('6. 交付结构与 GitHub 存档')
addp('建议路径：11_v2_carbon_first_experiments/（不覆盖历史 10_experiment_results/）。每个 V2-S06…V2-S12 目录均已包含：README_CN.md（步骤）；STAGE_CONTRACT.json（输入输出）；INPUT_REGISTER.csv；QA_GATES.csv；OUTPUT_REGISTER.csv；template_inputs/；release_record.json；outputs/PRECHECK_RESULT.json。')
addp('独立工具：tools/verify_stage.py、validate_paired_results.py、audit_trip_ledger.py、generate_sha256_manifest.py。模板仅含列名，不能当真实输入。另提供每个阶段可单独下载 ZIP 和一个总 ZIP。')
addp('第一项实操：上传/导出最新 QGIS 三分区原件及依赖；冻结 S06；同时收集汽油车实际车型油耗与两机 task-level 能耗文献或运营区间，但不要先跑 M0/M1/M2。')

title('7. 主要来源（用于审计，不意味着参数已标定）')
refs=[
('DJI FlyCart 30 specs','https://www.dji.com/flycart-30/specs'),
('Wingcopter 198 Cargo','https://wsd.wingcopter.com/w198-cargo'),
('IPCC 2006 Guidelines, Energy / Mobile Combustion','https://www.ipcc-nggip.iges.or.jp/public/2006gl/vol2'),
('Malaysia Electricity GEF provisional 2024','https://myenergystats.st.gov.my/documents/d/guest/grid-emission-factor-gef-in-malaysia-2022-2024-provisional-'),
('CAAM UAS requirements','https://www.caam.gov.my/public/unmanned-aircraft-system-uas/'),
('CAAS Unmanned Aircraft requirements and cross-border advisory','https://www.caas.gov.sg/resources/regulatory-requirements-and-guidelines/unmanned-aircraft/')]
for n,u in refs:addp(n+' — '+u,space=2)

doc.save(out)
print(out)
