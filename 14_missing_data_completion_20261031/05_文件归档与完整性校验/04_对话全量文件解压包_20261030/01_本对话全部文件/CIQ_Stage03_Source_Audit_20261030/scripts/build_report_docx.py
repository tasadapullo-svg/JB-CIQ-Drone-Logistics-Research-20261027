from pathlib import Path
import re
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'STAGE03_SOURCE_AUDIT_20261030.md'
out=ROOT/'STAGE03_SOURCE_AUDIT_20261030.docx'
text=source.read_text(encoding='utf-8')
doc=Document()
sec=doc.sections[0];sec.top_margin=Inches(.72);sec.bottom_margin=Inches(.7);sec.left_margin=Inches(.78);sec.right_margin=Inches(.78)
sec.header_distance=Inches(.4);sec.footer_distance=Inches(.4)
style=doc.styles['Normal'];style.font.name='Times New Roman';style.font.size=Pt(9.1);style.font.color.rgb=RGBColor(0,0,0)
style.paragraph_format.space_after=Pt(4);style.paragraph_format.line_spacing=1.13
for s,size,before,after in [('Title',16,0,9),('Heading 1',12,12,5),('Heading 2',10.5,8,3)]:
 st=doc.styles[s];st.font.name='Times New Roman';st.font.size=Pt(size);st.font.bold=True;st.font.color.rgb=RGBColor(0,0,0);st.paragraph_format.space_before=Pt(before);st.paragraph_format.space_after=Pt(after)


def set_east_asia(run):
    rpr=run._element.get_or_add_rPr();fonts=rpr.rFonts
    if fonts is None:
        fonts=OxmlElement('w:rFonts');rpr.insert(0,fonts)
    fonts.set(qn('w:eastAsia'),'Noto Serif CJK SC')

def inline(p,raw):
    # simplified markdown spans; links converted to text (URL retained for evidence trace)
    raw=re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)',r'\1 (\2)',raw)
    parts=re.split(r'(\*\*[^*]+\*\*|`[^`]+`)',raw)
    for item in parts:
        if not item:continue
        bold=item.startswith('**') and item.endswith('**')
        code=item.startswith('`') and item.endswith('`')
        val=item[2:-2] if bold else item[1:-1] if code else item
        run=p.add_run(val);run.bold=bold
        if code:run.font.name='Consolas';run.font.size=Pt(8.2)
        set_east_asia(run)


def table_from_lines(lines):
    data=[]
    for x in lines:
        cells=[t.strip().replace('**','').replace('`','') for t in x.strip().strip('|').split('|')]
        if all(re.fullmatch(r':?-+:?',t or '') for t in cells):continue
        data.append(cells)
    if not data:return
    n=max(map(len,data));tbl=doc.add_table(rows=len(data),cols=n)
    tbl.style='Table Grid';tbl.alignment=WD_TABLE_ALIGNMENT.CENTER
    for i,rr in enumerate(data):
        for j,val in enumerate(rr):
            cell=tbl.cell(i,j);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            cell.text=''
            pp=cell.paragraphs[0];pp.paragraph_format.space_after=Pt(1);pp.paragraph_format.space_before=Pt(1)
            if i==0: pp.paragraph_format.keep_with_next=True
            run=pp.add_run(val);run.font.size=Pt(8);run.bold=(i==0);set_east_asia(run)
            if i==0:
                tcPr=cell._tc.get_or_add_tcPr();shd=OxmlElement('w:shd');shd.set(qn('w:fill'),'EDF0F4');tcPr.append(shd)
    p=doc.add_paragraph();p.paragraph_format.space_after=Pt(2)

lines=text.splitlines();i=0
while i<len(lines):
    s=lines[i].strip()
    if not s:i+=1;continue
    if s.startswith('|'):
        rows=[]
        while i<len(lines) and lines[i].strip().startswith('|'):
            rows.append(lines[i]);i+=1
        table_from_lines(rows);continue
    if s.startswith('# '):
        p=doc.add_paragraph(style='Title');inline(p,s[2:]);i+=1;continue
    if s.startswith('## '):
        p=doc.add_paragraph(style='Heading 1');p.paragraph_format.keep_with_next=True;inline(p,s[3:]);i+=1;continue
    if s.startswith('### '):
        p=doc.add_paragraph(style='Heading 2');p.paragraph_format.keep_with_next=True;inline(p,s[4:]);i+=1;continue
    if s.startswith('- '):
        p=doc.add_paragraph(style='List Bullet');inline(p,s[2:]);i+=1;continue
    m=re.match(r'^\d+\.\s+(.*)$',s)
    if m:
        p=doc.add_paragraph(style='List Number');inline(p,m.group(1));i+=1;continue
    if s.startswith('> '):
        p=doc.add_paragraph();p.paragraph_format.left_indent=Inches(.2);inline(p,s[2:]);i+=1;continue
    p=doc.add_paragraph();inline(p,s)
    i+=1

head=sec.header.paragraphs[0];head.alignment=WD_ALIGN_PARAGRAPH.RIGHT
r=head.add_run('CIQ UAV LOGISTICS  |  STAGE 03  |  SOURCE AUDIT');r.font.name='Times New Roman';r.font.size=Pt(7.5)
foot=sec.footer.paragraphs[0];foot.alignment=WD_ALIGN_PARAGRAPH.RIGHT
r=foot.add_run('2026-10-30   •   HOLD / NOT RELEASED');r.font.size=Pt(7.5)
doc.core_properties.title='Stage03 Source Evidence Audit — CIQ UAV Logistics'
doc.core_properties.subject='Historical meteorological QA, road-model and carbon-input boundaries'
doc.save(out)
print(out)
