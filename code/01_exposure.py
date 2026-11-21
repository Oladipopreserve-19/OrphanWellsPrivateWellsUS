"""Private-well users near documented orphaned oil and gas wells, by census block group.

Inputs (data/):
  dowdb/US_orphaned_wells_2026.csv  USGS Documented Orphaned Well Database 2026 (Merrill et al. 2026, doi:10.5066/P13FHBYG)
  REM_map_2010.tif                  USGS domestic-well population 2010, 1 km grid (doi:10.5066/P9FSLU3B)
  blockgroups/cb_2020_us_bg_500k    US Census 2020 cartographic boundary block groups
Run: .venv/bin/python -I code/01_exposure.py
"""
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data"
RADII = [0.5, 1.0, 2.0]   # km

# --- orphaned wells ---
w = pd.read_csv(D / "dowdb/US_orphaned_wells_2026.csv", dtype=str, encoding="utf-8-sig")
n_all = len(w)
w["lat"] = pd.to_numeric(w.latitude, errors="coerce"); w["lon"] = pd.to_numeric(w.longitude, errors="coerce")
w = w[w.lat.between(24, 50) & w.lon.between(-125, -66)].copy()           # conterminous US, valid coordinates
w = w.drop_duplicates(subset=["lat", "lon"])                              # identical coordinates counted once
ras = rasterio.open(D / "REM_map_2010.tif")
wg = gpd.GeoDataFrame(w, geometry=gpd.points_from_xy(w.lon, w.lat), crs="EPSG:4326").to_crs(ras.crs)
wxy = np.c_[wg.geometry.x, wg.geometry.y]
tree_w = cKDTree(wxy)

# --- populated grid cells ---
pop = ras.read(1).astype("float64"); pop[(pop < 0) | ~np.isfinite(pop)] = 0
rr, cc = np.nonzero(pop > 0)
cx, cy = rasterio.transform.xy(ras.transform, rr, cc)
cells = pd.DataFrame({"x": np.asarray(cx), "y": np.asarray(cy), "pop": pop[rr, cc]})
dist, _ = tree_w.query(cells[["x", "y"]].values, k=1)
cells["dist_km"] = dist / 1000
for r in RADII:
    cells[f"near_{r}"] = cells.dist_km <= r

# --- per orphaned well: private-well users within each radius ---
tree_c = cKDTree(cells[["x", "y"]].values)
for r in RADII:
    idx = tree_c.query_ball_point(wxy, r * 1000)
    wg[f"wellusers_{r}km"] = [cells["pop"].values[i].sum() if i else 0.0 for i in idx]

# --- block groups ---
bg = gpd.read_file(D / "blockgroups/cb_2020_us_bg_500k.shp")[["GEOID", "STATEFP", "COUNTYFP", "ALAND", "geometry"]].to_crs(ras.crs)
cpts = gpd.GeoDataFrame(cells, geometry=gpd.points_from_xy(cells.x, cells.y), crs=ras.crs)
cpts = gpd.sjoin(cpts, bg[["GEOID", "geometry"]], how="left", predicate="within").drop(columns="index_right")
wg = gpd.sjoin(wg, bg[["GEOID", "STATEFP", "geometry"]], how="left", predicate="within").drop(columns="index_right")

agg = {"pop": "sum"}
for r in RADII:
    cpts[f"pop_near_{r}"] = cpts["pop"] * cpts[f"near_{r}"]
    agg[f"pop_near_{r}"] = "sum"
b = cpts.groupby("GEOID").agg(agg).rename(columns={"pop": "wellusers_total"})
b["orphan_wells"] = wg.groupby("GEOID").size()
b = b.fillna({"orphan_wells": 0})
b = b.join(bg.set_index("GEOID")[["STATEFP", "COUNTYFP", "ALAND"]])
b["orphan_wells_per_km2"] = b.orphan_wells / (b.ALAND / 1e6)
b["share_near_1km"] = (b["pop_near_1.0"] / b.wellusers_total).where(b.wellusers_total > 0)
b = b.round(3).sort_values("pop_near_1.0", ascending=False)
b.to_csv(D / "blockgroup_exposure.csv")

keep = ["record_key", "state", "county", "type", "status", "lat", "lon", "GEOID"] + [f"wellusers_{r}km" for r in RADII]
pd.DataFrame(wg[keep]).round({f"wellusers_{r}km": 1 for r in RADII}).sort_values("wellusers_1.0km", ascending=False).to_csv(D / "orphanwell_exposure.csv", index=False)

tot = pd.DataFrame([{"radius_km": r, "unique_wellusers": round(cells.loc[cells[f"near_{r}"], "pop"].sum()),
                     "share_of_all_wellusers": round(cells.loc[cells[f"near_{r}"], "pop"].sum() / cells["pop"].sum(), 4),
                     "orphan_wells_with_any": int((wg[f"wellusers_{r}km"] >= 1).sum()),
                     "orphan_wells_100plus": int((wg[f"wellusers_{r}km"] >= 100).sum()),
                     "blockgroups_with_exposed_users": int((b[f"pop_near_{r}"] >= 1).sum())} for r in RADII])
tot.to_csv(D / "summary_totals.csv", index=False)
pd.Series({"wells_in_database": n_all, "conus_unique_locations": len(wg), "grid_total_wellusers": round(pop.sum()),
           "blockgroups": len(bg)}).to_csv(D / "provenance_counts.csv", header=["value"])
print(f"{n_all} wells; {len(wg)} CONUS unique locations"); print(tot.to_string(index=False))
