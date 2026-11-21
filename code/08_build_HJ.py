"""Hydrogeology Journal submission package for Preprint 12.
  Manuscript.docx  single column, double spaced, 2.5 cm margins, page and continuous line numbers,
                   plain tables, figures at the end each followed by its caption
  ESM1.pdf         electronic supplementary material (tables S1 to S7), no line numbers
  Fig1.tif ...     separate figure files
  Cover letter.docx
Run from Preprint12_OrphanWells: .venv/bin/python -I code/08_build_HJ.py
"""
import re, subprocess
from pathlib import Path
import markdown
from PIL import Image
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "submission Hydrogeology Journal"; OUT.mkdir(exist_ok=True)
MD = (ROOT / "draft/manuscript_HJ.md").read_text()
FIGS = [ROOT / "figures" / f for f in ["v2_fig1_map_states.png", "v2_fig2_distribution.png", "v2_fig3_aquifers.png",
                                       "v2_fig4_demographics.png", "v2_fig5_uncertainty.png", "v2_fig6_counties.png"]]

def runs(par, s):
    s = s.replace("<sup>1*</sup>", "¹*")
    for part in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", s):
        if part.startswith("**"): par.add_run(part[2:-2]).bold = True
        elif part.startswith("*") and len(part) > 1 and not part.startswith("*corresponding"): par.add_run(part[1:-1]).italic = True
        else: par.add_run(part)

def page_setup(d, line_numbers):
    for s in d.sections:
        s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Cm(2.5)
    st = d.styles["Normal"]; st.font.name = "Times New Roman"; st.font.size = Pt(12)
    st.paragraph_format.line_spacing_rule = WD_LINE_SPACING.DOUBLE
    for h in ("Title", "Heading 1", "Heading 2", "Heading 3"):
        hs = d.styles[h]; hs.font.name = "Times New Roman"; hs.font.color.rgb = None; hs.font.size = Pt(14 if h == "Title" else 12)
    sect = d.sections[0]._sectPr
    if line_numbers:
        ln = OxmlElement("w:lnNumType"); ln.set(qn("w:countBy"), "1"); ln.set(qn("w:restart"), "continuous"); sect.append(ln)
    pg = OxmlElement("w:pgNumType"); sect.append(pg)
    fp = d.sections[0].footer.paragraphs[0]
    for t, txt in [("begin", None), (None, "PAGE"), ("end", None)]:
        r = fp.add_run()
        if t: fc = OxmlElement("w:fldChar"); fc.set(qn("w:fldCharType"), t); r._r.append(fc)
        else: it = OxmlElement("w:instrText"); it.text = txt; r._r.append(it)

doc = Document(); page_setup(doc, True)
text, figcaps = MD.split("## Figure captions")
lines, i = text.splitlines(), 0
while i < len(lines):
    l = lines[i]
    if l.startswith("|"):
        rows = []
        while i < len(lines) and lines[i].startswith("|"):
            if not re.match(r"^\|[-:| ]+\|$", lines[i]): rows.append([c.strip() for c in lines[i].strip("|").split("|")])
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
    elif l.strip(): runs(doc.add_paragraph(), l.rstrip().rstrip("\\").rstrip())
    i += 1
doc.add_page_break(); doc.add_heading("Figures", 1)
for cap in [c for c in figcaps.strip().split("\n\n") if c.strip()]:
    n = int(re.match(r"\*\*Fig\. (\d)\*\*", cap.strip()).group(1))
    doc.add_picture(str(FIGS[n - 1]), width=Cm(16))
    runs(doc.add_paragraph(), cap.strip())
doc.save(OUT / "Manuscript.docx")

# separate TIFFs
for n, f in enumerate(FIGS, 1):
    Image.open(f).convert("RGB").save(OUT / f"Fig{n}.tif", dpi=(300, 300), compression="tiff_lzw")

# ESM1.pdf (no line numbers), with required header
si = (ROOT / "draft/supporting_information.md").read_text()
si_body = si.split("Preserve Oluwadimimu Oladipo", 1)[1]
header = ("# Electronic supplementary material – Hydrogeology Journal\n\n"
          "**Orphaned oil and gas wells and private-well groundwater: a census block group exposure screen for the United States**\n\n"
          "Preserve Oluwadimimu Oladipo\n\nDepartment of Geology and Mineral Sciences, University of Ilorin, Ilorin, Kwara State, Nigeria. "
          "Email: oladipopreserve@gmail.com\n")
html = markdown.markdown(header + si_body, extensions=["tables"])
css = """body{font-family:'Times New Roman',serif;font-size:10.5pt;line-height:1.35;max-width:17.5cm;margin:auto}
h1{font-size:13pt}table{border-collapse:collapse;font-size:8.5pt;margin:.4em 0 1.2em}
td,th{border:1px solid #000;padding:2px 5px;font-weight:normal;text-align:left}@page{size:A4;margin:2cm}"""
tmp = OUT / "tmp.html"; tmp.write_text(f"<!doctype html><meta charset='utf-8'><title>ESM1</title><style>{css}</style>{html}")
subprocess.run(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--headless", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={OUT / 'ESM1.pdf'}", tmp.as_uri()], check=True, capture_output=True)
tmp.unlink()

# cover letter
c = Document(); [setattr(s, a, Cm(2.5)) for s in c.sections for a in ("left_margin", "right_margin", "top_margin", "bottom_margin")]
c.styles["Normal"].font.name = "Times New Roman"; c.styles["Normal"].font.size = Pt(12)
for p in [
    "21 November 2026",
    "The Executive Editor\nHydrogeology Journal",
    "Dear Editor,",
    "Please consider the enclosed manuscript, “Orphaned oil and gas wells and private-well groundwater: a census block group exposure screen for the United States”, for publication as a Paper in Hydrogeology Journal.",
    "Unplugged orphaned oil and gas wells can act as pathways that let gas and brine reach fresh groundwater, and households drinking untreated water from private domestic wells are the least protected receptors. A recent national study placed documented orphaned wells within US aquifers; this manuscript adds the people. Combining the USGS Documented Orphaned Well Database 2026 with the national grid of domestic-well users, census block groups, principal aquifer maps and census demographics, it estimates that about 823,000 private-well users live within 1 km of a documented orphaned well. Exposure is concentrated in the Pennsylvanian and Mississippian sandstone aquifers of the Appalachian Basin, half of the exposed users live in 826 block groups, and the exposed communities are markedly rural and lower in income. The totals are robust to well-location errors and to changes between database releases.",
    "The study is directly relevant to groundwater protection and rural water supply, and it provides block group and per-well rankings that plugging and private-well testing programmes can use. All inputs are public, and the code and results are openly archived. A preprint will be posted on EarthArXiv.",
    "The manuscript is original, has not been published previously and is not under consideration elsewhere. The author declares no conflicts of interest. The use of a large language model to assist with code and drafting is documented in the Methods section, as the journal requires.",
    "Thank you for your consideration.",
    "Yours sincerely,\n\nPreserve Oluwadimimu Oladipo\nDepartment of Geology and Mineral Sciences, University of Ilorin, Nigeria\noladipopreserve@gmail.com · ORCID 0009-0008-3770-1704",
]:
    c.add_paragraph(p)
c.save(OUT / "Cover letter.docx")
print(sorted(p.name for p in OUT.iterdir()))
