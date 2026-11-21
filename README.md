# Orphaned oil and gas wells and private-well groundwater (USA)

A national, census block group screen of how many people on private domestic wells live near documented orphaned oil and gas wells in the conterminous United States, with aquifer, demographic, uncertainty and database-change analyses.

**Author:** Preserve Oluwadimimu Oladipo, University of Ilorin · ORCID [0009-0008-3770-1704](https://orcid.org/0009-0008-3770-1704)
**Preprint:** [link to be added when posted on EarthArXiv]

## Main results (2010 private-well population, 125,425 orphaned well locations)

| Radius | Private-well users (counted once) | Share of all private-well users |
|---|---|---|
| 0.5 km | 318,531 | 0.9% |
| 1 km | 822,685 | 2.2% |
| 2 km | 1,833,573 | 4.9% |

* Ohio and Pennsylvania hold 58% of users within 1 km; the Pennsylvanian and Mississippian sandstone aquifers hold 59%.
* Half of the exposed users live in 826 of 8,900 exposed census block groups and in 42 of 1,029 counties.
* 902 high-concern block groups have most of their private-well users, and at least 100 people, within 1 km of an orphaned well.
* Exposed block groups are far more rural (median 29 vs 274 people per km²) and lower in income than other well-dependent block groups in the same states.
* The 1 km total changes by less than 5% when well locations are randomly displaced by up to 500 m, and by 2.9% between the 2022 and 2026 database releases.

These are counts of people who could be affected, not of contamination.

## Reproduce

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Download into `data/`:

* USGS Documented Orphaned Well Database 2026, https://doi.org/10.5066/P13FHBYG → `data/dowdb/US_orphaned_wells_2026.csv`
* USGS 2022 orphaned well dataset, https://doi.org/10.5066/P91PJETI → `data/dow2022/US_orphaned_wells.shp`
* USGS domestic-well population 2010 (REM), https://doi.org/10.5066/P9FSLU3B → `data/REM_map_2010.tif`
* USGS principal aquifers, https://doi.org/10.5066/P9Y2HOUJ → `data/aquifers/us_aquifers.shp`
* US Census 2020 block groups, `cb_2020_us_bg_500k.zip` → `data/blockgroups/`
* ACS 2018–2022 block group geodatabase, `ACS_2022_5YR_BG.gdb.zip` → `data/acs/`
* Natural Earth 1:50m countries and states (map only) → `data/naturalearth/`

Then run in order:

```bash
.venv/bin/python -I code/01_exposure.py          # exposure by well and block group
.venv/bin/python -I code/02_summary_figures.py   # state and concentration summaries
.venv/bin/python -I code/04_extended.py          # aquifers, well type, uncertainty, counties
.venv/bin/python -I code/05_demographics.py      # ACS comparison
.venv/bin/python -I code/07_change_2022_2026.py  # 2022 vs 2026 releases
.venv/bin/python -I code/06_figures_v2.py        # figures
```

`03_build_documents.py` and `08_build_HJ.py` build the manuscript files and are not needed to reproduce the results.

## Contents

* `code/` analysis scripts
* `data/full_tables.zip` contains three large tables:
  * `blockgroup_exposure.csv` every block group: private-well users, exposed users at 0.5, 1 and 2 km, share exposed, orphaned wells
  * `orphanwell_exposure.csv` every orphaned well location: private-well users within 0.5, 1 and 2 km
  * `ext_demographics_bg.csv` ACS variables and exposure class for each block group
* `data/ext_*.csv`, `data/summary_*.csv` results tables (aquifers, well type, counties, demographics, uncertainty, change)
* `figures/` figures 1 to 6 (300 dpi)

## Data and licence

Inputs are public US government data (USGS, US Census Bureau) and Natural Earth (public domain); they are not redistributed here. Code: MIT licence. Results tables and figures: CC BY 4.0.

## Use of AI tools

Claude (Anthropic) assisted with writing code and text. The author designed the study, chose the criteria and checked all results.
