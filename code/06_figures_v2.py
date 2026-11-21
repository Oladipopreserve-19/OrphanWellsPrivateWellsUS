"""Multi-panel figures (v2) for the extended Preprint 12. Run: .venv/bin/python -I code/06_figures_v2.py"""
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
plt.rcParams.update({"font.size": 8.5, "font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False,
                     "savefig.dpi": 300, "axes.titlesize": 9, "axes.titleweight": "bold", "axes.titlelocation": "left"})
BLUE, ORANGE, GREEN, GREY = "#0072B2", "#D55E00", "#009E73", "#999999"

w = pd.read_csv(D / "orphanwell_exposure.csv", dtype={"GEOID": str})
b = pd.read_csv(D / "blockgroup_exposure.csv", dtype={"GEOID": str, "STATEFP": str})
st = pd.read_csv(D / "summary_by_state.csv")
ras = rasterio.open(D / "REM_map_2010.tif")

# ---------- Fig 1: (a) map, (b) states ----------
pop = ras.read(1).astype(float); pop[(pop < 0) | ~np.isfinite(pop)] = 0
rr, cc = np.nonzero(pop > 0); cx, cy = rasterio.transform.xy(ras.transform, rr, cc); cx, cy = np.asarray(cx), np.asarray(cy)
wg = gpd.GeoDataFrame(w, geometry=gpd.points_from_xy(w.lon, w.lat), crs="EPSG:4326").to_crs(ras.crs)
dist, _ = cKDTree(np.c_[wg.geometry.x, wg.geometry.y]).query(np.c_[cx, cy]); near = dist <= 1000
ext = [ras.bounds.left, ras.bounds.right, ras.bounds.bottom, ras.bounds.top]
fig = plt.figure(figsize=(7.2, 6.4))
ax = fig.add_axes([0.0, 0.36, 0.92, 0.62])
ctry = gpd.read_file(D / "naturalearth/countries/ne_50m_admin_0_countries.shp").to_crs(ras.crs)
sts = gpd.read_file(D / "naturalearth/states/ne_50m_admin_1_states_provinces_lakes.shp")
sts = sts[sts.adm0_a3 == "USA"].to_crs(ras.crs)
ctry[ctry.ADM0_A3.isin(["CAN", "MEX"])].plot(ax=ax, color="#f2f2f2", edgecolor="#9a9a9a", lw=0.4, zorder=0)
ax.imshow(np.where(pop > 0, 1, np.nan), extent=ext, cmap="Greys", vmin=0, vmax=5, interpolation="nearest", zorder=1)
sts.boundary.plot(ax=ax, color="#b0b0b0", lw=0.25, zorder=2)
ctry[ctry.ADM0_A3 == "USA"].boundary.plot(ax=ax, color="#666666", lw=0.5, zorder=2)
for txt, (lx, ly) in {"CANADA": (-1.2e6, 3.05e6), "MEXICO": (-0.75e6, 0.55e6), "Pacific Ocean": (-2.42e6, 1.35e6),
                      "Atlantic Ocean": (2.05e6, 0.5e6), "Gulf of Mexico": (0.45e6, 0.42e6)}.items():
    ax.text(lx, ly, txt, fontsize=6.5, color="#555555", style="normal" if txt.isupper() else "italic", ha="center", zorder=5, rotation=80 if txt.startswith("Pacific") else 0)
x0, y0 = -2.3e6, 0.75e6
ax.plot([x0, x0 + 5e5], [y0, y0], color="black", lw=1.5, zorder=6); ax.text(x0 + 2.5e5, y0 + 4e4, "500 km", fontsize=6.5, ha="center", zorder=6)
ax.annotate("N", xy=(x0 + 9e4, y0 + 4.6e5), xytext=(x0 + 9e4, y0 + 1.7e5), ha="center", fontsize=7, fontweight="bold",
            arrowprops=dict(arrowstyle="-|>", color="black", lw=1), zorder=6)
ax.scatter(wg.geometry.x, wg.geometry.y, s=0.04, color="#444444", lw=0)
sc = ax.scatter(cx[near], cy[near], c=np.log10(pop[rr, cc][near]), s=0.5, cmap="inferno_r", vmin=0, vmax=2.5, lw=0)
ax.set_xlim(ext[0] - 1.5e5, ext[1] + 2.0e5); ax.set_ylim(ext[2] + 1.5e5, ext[3] + 1.0e5); ax.set_axis_off(); fig.text(0.02, 0.96, "a", fontweight="bold", fontsize=9)
cax = fig.add_axes([0.80, 0.45, 0.015, 0.25]); cb = fig.colorbar(sc, cax=cax, ticks=[0, 1, 2]); cb.ax.set_yticklabels(["1", "10", "100"])
cb.set_label("Private-well users per km²\nwithin 1 km of an orphaned well", fontsize=7)
ax2 = fig.add_axes([0.12, 0.08, 0.38, 0.25]); s15 = st.head(12)[::-1]
ax2.barh(s15.state, s15.wellusers_within_1km / 1000, color=BLUE); ax2.set_xlabel("Users within 1 km (thousands)"); ax2.set_title("b", loc="left")
ax3 = fig.add_axes([0.60, 0.08, 0.36, 0.25]); s2 = st.head(12)
ax3.scatter(s2.orphan_wells / 1000, s2.wellusers_within_1km / 1000, color=ORANGE, s=14)
for _, r in s2.iterrows(): ax3.annotate(r.state, (r.orphan_wells / 1000, r.wellusers_within_1km / 1000), fontsize=6.5, xytext=(3, 2), textcoords="offset points")
ax3.set(xlabel="Orphaned wells (thousands)", ylabel="Users within 1 km (thousands)"); ax3.set_title("c", loc="left")
fig.savefig(F / "v2_fig1_map_states.png"); plt.close(fig)

# ---------- Fig 2: (a) per-well CDF, (b) block-group concentration, (c) share exposed histogram ----------
fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.5))
for r, c in [("0.5", "#E69F00"), ("1.0", BLUE), ("2.0", GREEN)]:
    v = np.sort(w[f"wellusers_{r}km"].values); axs[0].plot(v + 1, np.linspace(0, 1, len(v)), color=c, label=f"{r} km")
axs[0].set(xscale="log", xlabel="Users near a well + 1", ylabel="Fraction of wells"); axs[0].legend(frameon=False, fontsize=7); axs[0].set_title("a")
e = b[b["pop_near_1.0"] >= 1].sort_values("pop_near_1.0", ascending=False); cum = e["pop_near_1.0"].cumsum() / e["pop_near_1.0"].sum()
axs[1].plot(np.arange(1, len(cum) + 1) / len(cum) * 100, cum * 100, color=ORANGE); axs[1].axhline(50, color=GREY, ls=":", lw=1)
axs[1].set(xlabel="Exposed block groups, ranked (%)", ylabel="Cumulative exposed users (%)"); axs[1].set_title("b")
axs[2].hist(b.share_near_1km.dropna()[b["pop_near_1.0"] >= 1] * 100, bins=20, color=BLUE)
axs[2].set(xlabel="Share of block group's well users exposed (%)", ylabel="Block groups"); axs[2].set_title("c")
fig.tight_layout(); fig.savefig(F / "v2_fig2_distribution.png"); plt.close(fig)

# ---------- Fig 3: aquifers ----------
rk = pd.read_csv(D / "ext_by_rocktype.csv").sort_values("exposed_users_1km")
aqn = pd.read_csv(D / "ext_by_aquifer_top20.csv"); aqn = aqn[~aqn.AQ_NAME.isin(["Other rocks", "None"])].head(10).sort_values("share_exposed")
fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.9))
axs[0].barh(rk.ROCK_NAME.str.replace(" aquifers", ""), rk.exposed_users_1km / 1000, color=BLUE)
axs[0].set_xlabel("Users within 1 km (thousands)"); axs[0].set_title("a")
axs[1].barh(aqn.AQ_NAME.str.replace(" aquifer system", "").str.replace(" aquifers", "").str.replace(" aquifer", ""), aqn.share_exposed * 100, color=ORANGE)
axs[1].set_xlabel("Share of aquifer's private-well users exposed (%)"); axs[1].set_title("b")
fig.tight_layout(); fig.savefig(F / "v2_fig3_aquifers.png"); plt.close(fig)

# ---------- Fig 4: demographics ----------
dm = pd.read_csv(D / "ext_demographics_bg.csv")
dm["cls"] = np.where(dm.high_concern, "High concern", np.where(dm.group == "Exposed", "Exposed", "Not exposed"))
order = ["Not exposed", "Exposed", "High concern"]; cols = [GREY, BLUE, ORANGE]
fig, axs = plt.subplots(1, 4, figsize=(7.2, 2.6))
for ax, (var, lab, lg) in zip(axs, [("median_income", "Median household\nincome (USD thousands)", False), ("pct_poverty", "Below poverty (%)", False),
                                     ("pct_minority", "Other than non-Hispanic\nwhite (%)", False), ("density_per_km2", "Population per km²", True)]):
    data = [dm.loc[dm.cls == k, var].dropna() / (1000 if var == "median_income" else 1) for k in order]
    bp = ax.boxplot(data, showfliers=False, patch_artist=True, widths=0.6)
    for p, c in zip(bp["boxes"], cols): p.set_facecolor(c); p.set_alpha(0.7)
    for m in bp["medians"]: m.set_color("black")
    ax.set_xticks([1, 2, 3], ["Not\nexposed", "Exposed", "High\nconcern"], fontsize=7); ax.set_ylabel(lab, fontsize=7.5)
    if lg: ax.set_yscale("log")
for a, t in zip(axs, "abcd"): a.set_title(t)
fig.tight_layout(); fig.savefig(F / "v2_fig4_demographics.png"); plt.close(fig)

# ---------- Fig 5: uncertainty and radius ----------
u = pd.read_csv(D / "ext_uncertainty.csv"); tot = pd.read_csv(D / "summary_totals.csv")
fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.6))
axs[0].errorbar(u.sigma_m, u["mean"] / 1000, yerr=[(u["mean"] - u.p2_5) / 1000, (u.p97_5 - u["mean"]) / 1000], fmt="o", color=ORANGE, capsize=3)
axs[0].axhline(u.baseline[0] / 1000, color=BLUE, ls="--", lw=1, label="Reported coordinates")
axs[0].set(xlabel="Positional error scale σ (m)", ylabel="Users within 1 km (thousands)"); axs[0].legend(frameon=False, fontsize=7); axs[0].set_title("a")
axs[1].plot(tot.radius_km, tot.unique_wellusers / 1e6, "o-", color=BLUE)
axs[1].set(xlabel="Radius (km)", ylabel="Private-well users (millions)"); axs[1].set_title("b")
fig.tight_layout(); fig.savefig(F / "v2_fig5_uncertainty.png"); plt.close(fig)

# ---------- Fig 6: counties ----------
ct = pd.read_csv(D / "ext_top_counties.csv").head(20)[::-1]
fig, ax = plt.subplots(figsize=(5.2, 4.2))
ax.barh(ct.county + ", " + ct.state.map({"Pennsylvania": "PA", "Ohio": "OH", "West Virginia": "WV", "New York": "NY", "Kentucky": "KY",
                                          "Indiana": "IN", "Texas": "TX", "Oklahoma": "OK"}).fillna(ct.state), ct.exposed_1km / 1000, color=BLUE)
ax.set_xlabel("Private-well users within 1 km of an orphaned well (thousands)")
fig.tight_layout(); fig.savefig(F / "v2_fig6_counties.png"); plt.close(fig)
print("v2 figures done")
