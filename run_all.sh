#!/usr/bin/env bash
# Rebuild everything from the raw files, in order.
# Run from the repository root:  bash run_all.sh
# Needs: Python 3 + requirements.txt, LibreOffice (soffice) for step 0,
#        and the OCHA shapefiles in data/raw/D7/shp/ for steps 4–5.
set -euo pipefail

RAW=data/raw

# 0) Convert the old D2 .xls files to .xlsx (the parser reads .xlsx only)
mkdir -p d2_xlsx
soffice --headless --convert-to xlsx --outdir d2_xlsx "$RAW"/D2/cb_t3T-district*.xls
cp "$RAW"/D2/cb_t3T-district*.xlsx d2_xlsx/

# 1) D2 -> district x month table in the D1 layout
python src/build_district.py d2_xlsx "$RAW"/D1/D1_2569-08_visible_rows.txt "$RAW"/D1/D1_2569-08_suppressed_codes.txt \
       "$RAW"/D6/dopa_population_amphoe_2548-2568.csv processed
python src/clean_d2.py processed/district_monthly_D2_D1.csv processed/district_monthly_D2.csv

# 2) Annual panels (province + district)
python src/build_panels.py "$RAW" processed/district_monthly_D2.csv processed/panels

# 3) Q1 inequality
python src/q1_inequality.py processed/panels outputs/q1
python src/q1_charts.py outputs/q1 processed/panels outputs/q1/fig

# 4) Q2 spatial clustering (first run takes 3–4 minutes: reads the 103 MB district shapefile)
python src/q2_spatial.py "$RAW"/D7/shp processed/panels outputs/q2 processed/geo
python src/q2_maps.py outputs/q2 processed/panels processed/geo outputs/q2/fig

# 5) JSON data for the dashboard
python src/dash_data.py . processed/geo/_adm2_cache.pkl "$RAW"/D7/shp dashboard/data
