"""Extended analyses for Preprint 12:
  A. exposure by principal aquifer (rock type and named aquifer system)
  B. exposure by well type
  C. positional-uncertainty Monte Carlo (random jitter of well coordinates)
  D. county ranking
Run: .venv/bin/python -I code/04_extended.py
"""
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data"
rng = np.random.default_rng(20261121)

ras = rasterio.open(D / "REM_map_2010.tif")
pop = ras.read(1).astype("float64"); pop[(pop < 0) | ~np.isfinite(pop)] = 0
rr, cc = np.nonzero(pop > 0)
cx, cy = rasterio.transform.xy(ras.transform, rr, cc)
cells = pd.DataFrame({"x": np.asarray(cx), "y": np.asarray(cy), "pop": pop[rr, cc]})

w = pd.read_csv(D / "orphanwell_exposure.csv", dtype={"GEOID": str})
wg = gpd.GeoDataFrame(w, geometry=gpd.points_from_xy(w.lon, w.lat), crs="EPSG:4326").to_crs(ras.crs)
wxy = np.c_[wg.geometry.x, wg.geometry.y]
d0, _ = cKDTree(wxy).query(cells[["x", "y"]].values)
cells["near1"] = d0 <= 1000

# ---- A. principal aquifers ----
aq = gpd.read_file(D / "aquifers/us_aquifers.shp").to_crs(ras.crs)[["ROCK_NAME", "AQ_NAME", "geometry"]]
cp = gpd.GeoDataFrame(cells, geometry=gpd.points_from_xy(cells.x, cells.y), crs=ras.crs)
cp = gpd.sjoin(cp, aq, how="left", predicate="within").drop(columns="index_right")
cp = cp[~cp.index.duplicated(keep="first")]
cp["ROCK_NAME"] = cp.ROCK_NAME.fillna("Outside principal aquifers"); cp["AQ_NAME"] = cp.AQ_NAME.fillna("None")
wa = gpd.sjoin(wg, aq, how="left", predicate="within").drop(columns="index_right")
wa = wa[~wa.index.duplicated(keep="first")]
wa["ROCK_NAME"] = wa.ROCK_NAME.fillna("Outside principal aquifers"); wa["AQ_NAME"] = wa.AQ_NAME.fillna("None")

def by(col):
    e = cp[cp.near1].groupby(col)["pop"].sum().rename("exposed_users_1km")
    t = cp.groupby(col)["pop"].sum().rename("all_wellusers")
    n = wa.groupby(col).size().rename("orphan_wells")
    out = pd.concat([n, e, t], axis=1).fillna(0)
    out["share_exposed"] = out.exposed_users_1km / out.all_wellusers
    return out.sort_values("exposed_users_1km", ascending=False).round(3)
by("ROCK_NAME").to_csv(D / "ext_by_rocktype.csv")
by("AQ_NAME").head(20).to_csv(D / "ext_by_aquifer_top20.csv")

# ---- B. well type ----
t = w["type"].fillna("").str.strip().str.lower()
w["type_class"] = np.select(
    [t.isin(["oil", "o"]) | t.str.startswith("oil well"), t.isin(["gas", "g"]) | t.str.startswith("gas well"),
     t.str.contains("oil") & t.str.contains("gas"), t.str.contains("inject|disposal|swd|water|storage|service"),
     t.str.contains("dry")],
    ["Oil", "Gas", "Oil and gas", "Injection/service", "Dry hole"], default="Other or unknown")
wt = w.groupby("type_class").agg(wells=("record_key", "size"), median_users_1km=("wellusers_1.0km", "median"),
                                 wells_100plus=("wellusers_1.0km", lambda s: int((s >= 100).sum()))).sort_values("wells", ascending=False)
wt.to_csv(D / "ext_by_welltype.csv")

# ---- C. positional uncertainty Monte Carlo ----
# Each well displaced in a random direction by a distance drawn from a half-normal with scale sigma.
mc = []
for sigma in [100, 250, 500]:
    tots = []
    for k in range(20):
        ang = rng.uniform(0, 2 * np.pi, len(wxy)); dist = np.abs(rng.normal(0, sigma, len(wxy)))
        j = wxy + np.c_[np.cos(ang) * dist, np.sin(ang) * dist]
        dk, _ = cKDTree(j).query(cells[["x", "y"]].values)
        tots.append(cells["pop"].values[dk <= 1000].sum())
    tots = np.array(tots)
    mc.append({"sigma_m": sigma, "runs": len(tots), "mean": round(tots.mean()), "p2_5": round(np.percentile(tots, 2.5)),
               "p97_5": round(np.percentile(tots, 97.5)), "baseline": round(cells.loc[cells.near1, "pop"].sum())})
pd.DataFrame(mc).to_csv(D / "ext_uncertainty.csv", index=False)

# ---- D. counties ----
b = pd.read_csv(D / "blockgroup_exposure.csv", dtype={"GEOID": str, "STATEFP": str, "COUNTYFP": str})
b["county_fips"] = b.STATEFP + b.COUNTYFP
cty = b.groupby("county_fips").agg(exposed_1km=("pop_near_1.0", "sum"), orphan_wells=("orphan_wells", "sum"),
                                   wellusers=("wellusers_total", "sum")).sort_values("exposed_1km", ascending=False)
cty["share"] = cty.exposed_1km / cty.wellusers
names = w.dropna(subset=["GEOID"]).assign(county_fips=lambda d: d.GEOID.str[:5]).groupby("county_fips")[["state", "county"]].first()
cty = cty.join(names).round(3); cty.head(25).to_csv(D / "ext_top_counties.csv")
counties_for_half = int((cty.exposed_1km.cumsum() / cty.exposed_1km.sum() < 0.5).sum()) + 1

pd.set_option("display.width", 180)
print(by("ROCK_NAME")); print(by("AQ_NAME").head(10)); print(wt); print(pd.DataFrame(mc)); print(cty.head(10))
print("counties holding half of exposed users:", counties_for_half, "of", int((cty.exposed_1km >= 1).sum()))
