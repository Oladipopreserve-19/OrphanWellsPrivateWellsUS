"""Summaries and figures for Preprint 12. Run: .venv/bin/python -I code/02_summary_figures.py"""
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import rasterio
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
D, F = ROOT / "data", ROOT / "figures"
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "savefig.dpi": 300})
FIPS = {"01": "AL", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "17": "IL", "18": "IN", "20": "KS", "21": "KY", "22": "LA",
        "26": "MI", "28": "MS", "29": "MO", "30": "MT", "31": "NE", "32": "NV", "35": "NM", "36": "NY", "38": "ND", "39": "OH",
        "40": "OK", "42": "PA", "47": "TN", "48": "TX", "49": "UT", "54": "WV", "56": "WY", "51": "VA", "13": "GA", "12": "FL"}
b = pd.read_csv(D / "blockgroup_exposure.csv", dtype={"GEOID": str, "STATEFP": str, "COUNTYFP": str})
w = pd.read_csv(D / "orphanwell_exposure.csv", dtype={"GEOID": str})
b["state"] = b.STATEFP.map(FIPS).fillna(b.STATEFP)

# by state (exposed users within 1 km, from block groups; block groups never overlap, so no double counting)
st = b.groupby("state").agg(blockgroups_exposed=("pop_near_1.0", lambda s: int((s >= 1).sum())),
                            wellusers_within_1km=("pop_near_1.0", "sum"), wellusers_within_2km=("pop_near_2.0", "sum"),
                            orphan_wells=("orphan_wells", "sum"))
st = st[st.orphan_wells > 0].sort_values("wellusers_within_1km", ascending=False).round(0)
st.to_csv(D / "summary_by_state.csv")

# concentration across block groups
e = b[b["pop_near_1.0"] >= 1].sort_values("pop_near_1.0", ascending=False)
cum = e["pop_near_1.0"].cumsum() / e["pop_near_1.0"].sum()
n50, n80 = int((cum < 0.5).sum()) + 1, int((cum < 0.8).sum()) + 1
conc = pd.Series({"exposed_blockgroups": len(e), "bg_for_50pct": n50, "bg_for_80pct": n80,
                  "median_exposed_per_bg": round(e["pop_near_1.0"].median(), 1),
                  "bg_majority_users_exposed": int((b.share_near_1km >= 0.5).sum()),
                  "bg_majority_and_100plus": int(((b.share_near_1km >= 0.5) & (b["pop_near_1.0"] >= 100)).sum())})
conc.to_csv(D / "summary_concentration.csv", header=["value"])
top = b.head(20)[["GEOID", "state", "wellusers_total", "pop_near_1.0", "share_near_1km", "orphan_wells"]]
top.to_csv(D / "top20_blockgroups.csv", index=False)
wq = w["wellusers_1.0km"].describe(percentiles=[.5, .75, .9, .99]).round(1)
wq.to_csv(D / "summary_per_orphanwell.csv", header=["wellusers_within_1km"])

# Fig 1: map of 1 km cells with private-well users within 1 km of an orphaned well
ras = rasterio.open(D / "REM_map_2010.tif"); pop = ras.read(1).astype(float); pop[(pop < 0) | ~np.isfinite(pop)] = 0
rr, cc = np.nonzero(pop > 0); cx, cy = rasterio.transform.xy(ras.transform, rr, cc); cx, cy = np.asarray(cx), np.asarray(cy)
wl = gpd.GeoDataFrame(w, geometry=gpd.points_from_xy(w.lon, w.lat), crs="EPSG:4326").to_crs(ras.crs)
dist, _ = cKDTree(np.c_[wl.geometry.x, wl.geometry.y]).query(np.c_[cx, cy])
near = dist <= 1000
ext = [ras.bounds.left, ras.bounds.right, ras.bounds.bottom, ras.bounds.top]
fig, ax = plt.subplots(figsize=(7.5, 4.6))
ax.imshow(np.where(pop > 0, 1, np.nan), extent=ext, cmap="Greys", vmin=0, vmax=4, interpolation="nearest")
ax.scatter(wl.geometry.x, wl.geometry.y, s=0.05, color="#555555", lw=0)
sc = ax.scatter(cx[near], cy[near], c=np.log10(pop[rr, cc][near]), s=0.6, cmap="inferno_r", vmin=0, vmax=2.5, lw=0)
cb = fig.colorbar(sc, ax=ax, shrink=0.7, ticks=[0, 1, 2]); cb.ax.set_yticklabels(["1", "10", "100"]); cb.set_label("Private-well users per km² (cells within 1 km of an orphaned well)")
ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3]); ax.set_axis_off()
fig.tight_layout(); fig.savefig(F / "fig1_map.png"); plt.close(fig)

# Fig 2: by state
s15 = st.head(15)[::-1]
fig, ax = plt.subplots(figsize=(5, 3.6))
ax.barh(s15.index, s15.wellusers_within_1km / 1000, color="#0072B2")
ax.set_xlabel("Private-well users within 1 km of an orphaned well (thousands)")
fig.tight_layout(); fig.savefig(F / "fig2_states.png"); plt.close(fig)

# Fig 3: concentration curve across block groups
fig, ax = plt.subplots(figsize=(4.2, 3.2))
ax.plot(np.arange(1, len(cum) + 1) / len(cum) * 100, cum.values * 100, color="#D55E00")
ax.axhline(50, color="grey", ls=":", lw=1)
ax.set(xlabel="Exposed block groups, ranked (% of total)", ylabel="Cumulative share of exposed users (%)")
fig.tight_layout(); fig.savefig(F / "fig3_concentration.png"); plt.close(fig)

# Fig 4: distribution per orphaned well at three radii
fig, ax = plt.subplots(figsize=(4.5, 3.2))
for r, c in [("0.5", "#E69F00"), ("1.0", "#0072B2"), ("2.0", "#009E73")]:
    v = np.sort(w[f"wellusers_{r}km"].values); ax.plot(v + 1, np.linspace(0, 1, len(v)), color=c, label=f"within {r} km")
ax.set(xscale="log", xlabel="Private-well users + 1 (log scale)", ylabel="Fraction of orphaned wells"); ax.legend(frameon=False)
fig.tight_layout(); fig.savefig(F / "fig4_perwell.png"); plt.close(fig)

pd.set_option("display.width", 160)
print(st.head(12)); print(conc); print(wq); print(top.to_string(index=False))
