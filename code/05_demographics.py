"""Demographics of exposed block groups (ACS 2022 5-year, block group level).
Compares block groups with private-well users within 1 km of an orphaned well against all other block
groups that have private-well users, within the same states. Run: .venv/bin/python -I code/05_demographics.py"""
from pathlib import Path
import numpy as np
import pandas as pd
import pyogrio
from scipy.stats import mannwhitneyu

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data"; G = D / "acs/ACS_2022_5YR_BG.gdb"

def layer(name, cols):
    df = pyogrio.read_dataframe(G, layer=name, columns=["GEOIDFQ"] + cols, read_geometry=False)
    df["GEOID"] = df.GEOIDFQ.str[-12:]
    return df.drop(columns="GEOIDFQ").set_index("GEOID")

acs = layer("X01_AGE_AND_SEX", ["B01003_E001"]).join(layer("X19_INCOME", ["B19013_E001"])) \
    .join(layer("X03_HISPANIC_OR_LATINO_ORIGIN", ["B03002_E001", "B03002_E003"])) \
    .join(layer("X17_POVERTY", ["C17002_E001", "C17002_E002", "C17002_E003"]))
acs["median_income"] = acs.B19013_E001.where(acs.B19013_E001 > 0)
acs["pct_poverty"] = 100 * (acs.C17002_E002 + acs.C17002_E003) / acs.C17002_E001.replace(0, np.nan)
acs["pct_minority"] = 100 * (1 - acs.B03002_E003 / acs.B03002_E001.replace(0, np.nan))

b = pd.read_csv(D / "blockgroup_exposure.csv", dtype={"GEOID": str, "STATEFP": str}).set_index("GEOID")
b = b[b.wellusers_total >= 1].join(acs, how="left")
b["density_per_km2"] = b.B01003_E001 / (b.ALAND / 1e6)
states = b.loc[b["pop_near_1.0"] >= 1, "STATEFP"].unique()
b = b[b.STATEFP.isin(states)]
b["group"] = np.where(b["pop_near_1.0"] >= 1, "Exposed", "Not exposed")
b["high_concern"] = (b.share_near_1km >= 0.5) & (b["pop_near_1.0"] >= 100)

rows = []
for var, lab in [("median_income", "Median household income (USD)"), ("pct_poverty", "Population below poverty line (%)"),
                 ("pct_minority", "Population other than non-Hispanic white (%)"), ("density_per_km2", "Population density (per km²)")]:
    ex, ne, hc = b.loc[b.group == "Exposed", var].dropna(), b.loc[b.group == "Not exposed", var].dropna(), b.loc[b.high_concern, var].dropna()
    p = mannwhitneyu(ex, ne).pvalue
    rows.append({"variable": lab, "exposed_median": round(ex.median(), 1), "not_exposed_median": round(ne.median(), 1),
                 "high_concern_median": round(hc.median(), 1), "n_exposed": len(ex), "n_not_exposed": len(ne),
                 "n_high_concern": len(hc), "mann_whitney_p": float(f"{p:.2e}")})
res = pd.DataFrame(rows); res.to_csv(D / "ext_demographics.csv", index=False)
b[["group", "high_concern", "median_income", "pct_poverty", "pct_minority", "density_per_km2"]].to_csv(D / "ext_demographics_bg.csv")
pd.set_option("display.width", 200); print(res.to_string(index=False)); print("states compared:", len(states))
