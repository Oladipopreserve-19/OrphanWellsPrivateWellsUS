"""Build the preprint (Word + PDF, figures embedded) and the Science of the Total Environment package
(double-spaced line-numbered manuscript, highlights, graphical abstract, TIFF figures, cover letter).
Tables are plain: thin black borders, no shading, no bold header row.
Usage: .venv/bin/python -I code/03_build_documents.py <project_root>
"""
import re, sys, base64, subprocess, json
from pathlib import Path
import markdown
from PIL import Image
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(sys.argv[1]).resolve()
cfg = json.loads((ROOT / "draft/build.json").read_text())
MD = (ROOT / "draft" / cfg["manuscript"]).read_text()
FIGS = [ROOT / "figures" / f for f in cfg["figures"]]

def runs(par, s):
    for part in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", s):
        if part.startswith("**"): par.add_run(part[2:-2]).bold = True
        elif part.startswith("*") and len(part) > 1: par.add_run(part[1:-1]).italic = True
        else: par.add_run(part)

def new_doc(double, line_numbers):
    d = Document()
    st = d.styles["Normal"]; st.font.name = "Times New Roman"; st.font.size = Pt(12)
    st.paragraph_format.line_spacing_rule = WD_LINE_SPACING.DOUBLE if double else WD_LINE_SPACING.SINGLE
    for h in ("Title", "Heading 1", "Heading 2"):
        hs = d.styles[h]; hs.font.name = "Times New Roman"; hs.font.color.rgb = None
    if line_numbers:
        ln = OxmlElement("w:lnNumType"); ln.set(qn("w:countBy"), "1"); ln.set(qn("w:restart"), "continuous")
        d.sections[0]._sectPr.append(ln)
    fp = d.sections[0].footer.paragraphs[0]
    for t, txt in [("begin", None), (None, "PAGE"), ("end", None)]:
        r = fp.add_run()
        if t: fc = OxmlElement("w:fldChar"); fc.set(qn("w:fldCharType"), t); r._r.append(fc)
        else: it = OxmlElement("w:instrText"); it.text = txt; r._r.append(it)
    return d

def write_docx(path, double, line_numbers, embed_figs):
    doc = new_doc(double, line_numbers)
    lines, i = MD.splitlines(), 0
    while i < len(lines):
        l = lines[i]
        if l.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                if not re.match(r"^\|[-| ]+\|$", lines[i]): rows.append([c.strip() for c in lines[i].strip("|").split("|")])
                i += 1
            t = doc.add_table(rows=len(rows), cols=len(rows[0])); t.style = "Table Grid"
            for r, row in enumerate(rows):
                for c, v in enumerate(row):
                    cell = t.cell(r, c); cell.text = v
                    p = cell.paragraphs[0]; p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
                    for rn in p.runs: rn.font.size = Pt(10)
            continue
        if l.startswith("# "): doc.add_heading(l[2:], 0)
        elif l.startswith("## "): doc.add_heading(l[3:], 1)
        elif l.startswith("### "): doc.add_heading(l[4:], 2)
        elif l.strip():
            m = re.match(r"^Fig\. (\d)\.", l)
            if m and embed_figs: doc.add_picture(str(FIGS[int(m.group(1)) - 1]), width=Cm(15))
            runs(doc.add_paragraph(), l.rstrip())
        i += 1
    doc.save(path)

# ---- preprint: single-spaced Word + PDF with figures ----
pre = ROOT / "draft"
write_docx(pre / cfg["preprint_name"] + ".docx" if False else pre / f'{cfg["preprint_name"]}.docx', False, False, True)
def embed(m):
    n = int(m.group(1)); b = base64.b64encode(FIGS[n - 1].read_bytes()).decode()
    return f'<img src="data:image/png;base64,{b}" style="width:100%;max-width:16cm"/>\n\nFig. {n}.'
html_md = re.sub(r"^Fig\. (\d)\.", embed, MD, flags=re.M)
body = markdown.markdown(html_md, extensions=["tables"])
css = """body{font-family:'Times New Roman',serif;font-size:11pt;line-height:1.45;max-width:17cm;margin:auto}
h1{font-size:16pt}h2{font-size:12.5pt;margin-top:1.3em}h3{font-size:11.5pt;font-style:italic;font-weight:normal}
table{border-collapse:collapse;font-size:9.5pt;margin:.5em 0}td,th{border:1px solid #000;padding:2px 6px;font-weight:normal;text-align:left}
img{display:block;margin:1em auto .2em}@page{size:A4;margin:2cm}"""
html = pre / "tmp.html"; html.write_text(f"<!doctype html><meta charset='utf-8'><title>preprint</title><style>{css}</style>{body}")
subprocess.run(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--headless", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={pre / (cfg['preprint_name'] + '.pdf')}", html.as_uri()], check=True, capture_output=True)
html.unlink()

# ---- STOTEN package ----
out = ROOT / "submission_STOTEN"; out.mkdir(exist_ok=True)
write_docx(out / "Manuscript.docx", True, True, False)
h = new_doc(False, False); h.add_heading("Highlights", 1)
for line in cfg["highlights"]:
    assert len(line) <= 85, (len(line), line)
    h.add_paragraph(line, style="List Bullet")
h.save(out / "Highlights.docx")
for n, f in enumerate(FIGS, 1):
    Image.open(f).convert("RGB").save(out / f"Fig{n}.tif", dpi=(300, 300), compression="tiff_lzw")
c = new_doc(False, False)
for p in cfg["cover_letter"]: c.add_paragraph(p)
c.save(out / "Cover letter.docx")
print("built:", sorted(p.name for p in out.iterdir()), cfg["preprint_name"])
