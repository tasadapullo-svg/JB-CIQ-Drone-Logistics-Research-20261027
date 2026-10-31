#!/usr/bin/env python3
from pathlib import Path
import re
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

R=Path(__file__).resolve().parents[1]
text=(R/'STAGE04_FORMAL_AUDIT_20261030.md').read_text(encoding='utf-8')
lines=text.splitlines()
doc=Document();s=doc.sections[0]
s.top_margin=Inches(.75);s.bottom_margin=Inches(.68);s.left_margin=Inches(.73);s.right_margin=Inches(.73)
s.header_distance=Inches(.34);s.footer_distance=Inches(.33)
normal=doc.styles['Normal'];normal.font.name='Noto Sans CJK SC';normal.font.size=Pt(9)
normal.font.color.rgb=RGBColor(32,41,53);normal.paragraph_format.space_after=Pt(5)
normal.paragraph_format.line_spacing=1.18
for typ,sz in [('Title',17),('Heading 1',11.8),('Heading 2',10.5)]:
    st=doc.styles[typ];st.font.name='Noto Sans CJK SC';st.font.size=Pt(sz);st.font.bold=True;st.font.color.rgb=RGBColor(33,50,75)
    st.paragraph_format.space_before=Pt(12 if typ!='Title' else 0);st.paragraph_format.space_after=Pt(6)

header=s.header.paragraphs[0];header.text='CIQ UAV LOGISTICS SCI  |  EVIDENCE & REPRODUCIBILITY AUDIT'
header.alignment=WD_ALIGN_PARAGRAPH.RIGHT
for run in header.runs:run.font.name='Arial';run.font.size=Pt(7);run.font.color.rgb=RGBColor(93,103,114)
footer=s.footer.paragraphs[0];footer.text='Historical audit only  •  No recalculation authorization  •  2026-10-30'
footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
for run in footer.runs:run.font.size=Pt(7);run.font.color.rgb=RGBColor(100,110,115)

def add_md(p,text):
    # lightweight inline bold + links rendering
    items=re.split(r'(\*\*.*?\*\*|\[.*?\]\(https?://[^)]+\)|`[^`]+`)',text)
    for seg in items:
        if seg.startswith('**') and seg.endswith('**'):
            r=p.add_run(seg[2:-2]);r.bold=True
        elif seg.startswith('`') and seg.endswith('`'):
            r=p.add_run(seg[1:-1]);r.font.name='Consolas';r.font.size=Pt(7.8)
        elif seg.startswith('[') and '](' in seg:
            label=seg[1:seg.index('](')];r=p.add_run(label);r.underline=True
        else:p.add_run(seg.replace('  ',' '))

def set_border(cell):
    tcPr=cell._tc.get_or_add_tcPr()
    sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'F1F3F6');tcPr.append(sh)

i=0
while i<len(lines):
    line=lines[i].strip()
    if not line:i+=1;continue
    if line.startswith('|'):
        rows=[]
        while i<len(lines) and lines[i].strip().startswith('|'):
            cells=[c.strip() for c in lines[i].strip().strip('|').split('|')]
            if not all(re.fullmatch(r':?-{3,}:?',v or 'x') for v in cells):rows.append(cells)
            i+=1
        if not rows:continue
        table=doc.add_table(rows=len(rows),cols=max(map(len,rows)));table.style='Table Grid';table.alignment=WD_TABLE_ALIGNMENT.CENTER
        table.autofit=True
        for ri,cells in enumerate(rows):
            for ci,c in enumerate(cells):
                cell=table.cell(ri,ci);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
                p=cell.paragraphs[0];p.paragraph_format.space_after=Pt(1)
                add_md(p,c)
                for run in p.runs:run.font.size=Pt(7.1 if len(rows[0])>=6 else 7.9)
                if ri==0:
                    set_border(cell)
                    for run in p.runs:run.bold=True
        doc.add_paragraph('').paragraph_format.space_after=Pt(0)
        continue
    if line.startswith('# '):
        doc.add_paragraph(line[2:],style='Title');i+=1;continue
    if line.startswith('## '):
        doc.add_paragraph(line[3:],style='Heading 1');i+=1;continue
    if line.startswith('### '):
        doc.add_paragraph(line[4:],style='Heading 2');i+=1;continue
    if re.match(r'^\d+\. ',line):
        p=doc.add_paragraph(style='List Number');add_md(p,re.sub(r'^\d+\. ','',line));i+=1;continue
    if line.startswith('- '):
        p=doc.add_paragraph(style='List Bullet');add_md(p,line[2:]);i+=1;continue
    if line.startswith('**') and line.endswith('  '):line=line[:-2]
    p=doc.add_paragraph();add_md(p,line)
    i+=1

out=R/'STAGE04_FORMAL_AUDIT_20261030.docx'
doc.save(out);print('DOCX:',out,'size',out.stat().st_size)
