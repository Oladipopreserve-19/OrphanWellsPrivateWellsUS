"""Change in private-well exposure between the 2022 orphaned-well dataset (Grove and Merrill 2022)
and the 2026 database (Merrill et al. 2026). Wells are matched between releases when locations lie
within 100 m of each other. Run: .venv/bin/python -I code/07_change_2022_2026.py"""
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data"
ras = rasterio.open(D / "REM_map_2010.tif")
pop = ras.read(1).astype("float64"); pop[(pop < 0) | ~np.isfinite(pop)] = 0
rr, cc = np.nonzero(pop > 0); cx, cy = rasterio.transform.xy(ras.transform, rr, cc)
cxy = np.c_[np.asarray(cx), np.asarray(cy)]; cpop = pop[rr, cc]

def load(gdf):
    g = gdf.to_crs("EPSG:4326")
    g = g[g.geometry.notna() & ~g.geometry.is_empty]
    g = g[g.geometry.y.between(24, 50) & g.geometry.x.between(-125, -66)]
    g = g.assign(lon=g.geometry.x.round(6), lat=g.geometry.y.round(6)).drop_duplicates(["lon", "lat"]).to_crs(ras.crs)
    return g

w22 = gpd.read_file(D / "dow2022/US_orphaned_wells.shp")
n22_all = len(w22); w22 = load(w22)
w26 = pd.read_csv(D / "orphanwell_exposure.csv")
w26 = load(gpd.GeoDataFrame(w26, geometry=gpd.points_from_xy(w26.lon, w26.lat), crs="EPSG:4326"))
x22, x26 = np.c_[w22.geometry.x, w22.geometry.y], np.c_[w26.geometry.x, w26.geometry.y]

def exposed(xy, r=1000):
    d, _ = cKDTree(xy).query(cxy); return d <= r

e22, e26 = exposed(x22), exposed(x26)
d26, _ = cKDTree(x22).query(x26); new26 = d26 > 100          # 2026 wells with no 2022 well within 100 m
d22, _ = cKDTree(x26).query(x22); gone22 = d22 > 100         # 2022 wells absent from 2026 (plugged, reclassified or relocated)

# exposure attributable only to new wells: cells near a new well and not near any 2022 well
only_new = exposed(x26[new26]) & ~e22
lost = e22 & ~e26

w26["is_new"] = new26
w26["state"] = w26.state.fillna("")
by_state = w26.groupby("state").agg(wells_2026=("is_new", "size"), new_wells=("is_new", "sum")).sort_values("new_wells", ascending=False)
by_state.to_csv(D / "ext_change_by_state.csv")

res = pd.Series({
    "wells_2022_in_release": n22_all, "wells_2022_conus_unique": len(w22),
    "wells_2026_conus_unique": len(w26),
    "wells_2026_new_vs_2022": int(new26.sum()), "wells_2022_absent_in_2026": int(gone22.sum()),
    "exposed_users_1km_2022": round(cpop[e22].sum()), "exposed_users_1km_2026": round(cpop[e26].sum()),
    "users_exposed_only_by_new_wells": round(cpop[only_new].sum()),
    "users_no_longer_exposed": round(cpop[lost].sum()),
})
res.to_csv(D / "ext_change_2022_2026.csv", header=["value"])
print(res.to_string()); print(by_state.head(10))
