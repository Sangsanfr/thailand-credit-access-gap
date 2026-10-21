"""Build the rows behind the dashboard as one script file, <out_dir>/data.js (window.CG_DATA).
A script file rather than JSON, so dashboard/index.html also works when opened straight from disk.
Usage: python dash_data.py <project_dir> <adm2_cache.pkl> <shp_dir> <out_dir>"""
import sys, os, json, pickle
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from geo_utils import read_polygons

PRJ, CACHE, SHP, OUT = sys.argv[1:5]
os.makedirs(OUT, exist_ok=True)
K, LON0, LAT0, COS = 50.0, 97.3, 20.5, np.cos(np.deg2rad(13.0))


ALL = {}


def dump(name, rows):
    ALL[name] = rows
    print(f'{name}: {len(rows)} rows')


def rnd(df, digits):
    df = df.copy()
    for c, d in digits.items():
        df[c] = df[c].round(d)
    return df


def records(df):
    return json.loads(df.to_json(orient='records', force_ascii=False))


# ---------------------------------------------------------------- tables
h = pd.read_csv(f'{PRJ}/processed/panels/province_panel_harmonised.csv', dtype={'prov_code_h': str}, encoding='utf-8-sig')
p = h[['year_be', 'prov_code_h', 'prov_name_th', 'region_bot', 'population', 'dep_dec', 'loan_dec', 'ldr_dec',
       'loan_pc_dec', 'dep_pc_dec', 'offices_per_100k', 'net_outflow_dec']]
p = rnd(p, {'ldr_dec': 2, 'loan_pc_dec': 0, 'dep_pc_dec': 0, 'offices_per_100k': 2})
p['key'] = p.year_be.astype(str) + '-' + p.prov_code_h
dump('prov_year', records(p))

q = pd.read_csv(f'{PRJ}/outputs/q1/q1_inequality_by_year.csv', encoding='utf-8-sig')
q = q[['year_be', 'basis', 'scope', 'n_areas', 'gini_loan_pc', 'gini_loan_pc_popw', 'gini_dep_pc', 'gini_dep_pc_popw',
       'theil_loan_pc', 'theil_between_share', 'p90_p10_loan_pc', 'ldr_median', 'n_ldr_above_100', 'loan_pc_median']]
dump('ineq_year', records(rnd(q, {c: 4 for c in q.columns if q[c].dtype == float})))

c = pd.read_csv(f'{PRJ}/outputs/q1/q1_convergence.csv', encoding='utf-8-sig')
dump('convergence', records(rnd(c, {'beta_slope': 3, 'se': 3, 't': 2, 'r2': 3, 'mean_growth_pct_pa': 2})))

r = pd.read_csv(f'{PRJ}/outputs/q1/q1_region_flows.csv', encoding='utf-8-sig')
dump('region_flows', records(rnd(r, {'ldr_dec': 2, 'loan_pc_dec': 0, 'dep_pc_dec': 0})))

m = pd.read_csv(f'{PRJ}/outputs/q2/q2_moran_by_year.csv', encoding='utf-8-sig')
dump('moran_year', records(rnd(m[['year_be', 'variable', 'scope', 'weights', 'n', 'moran_I', 'z_sim', 'p_sim']],
                                {'moran_I': 4, 'z_sim': 2})))

lp = pd.read_csv(f'{PRJ}/outputs/q2/q2_lisa_province.csv', dtype={'prov_code_h': str}, encoding='utf-8-sig')
lp = lp[lp.scope == 'all'][['year_be', 'variable', 'prov_code_h', 'cluster', 'p_sim', 'sig_fdr']]
lp['key'] = lp.year_be.astype(str) + '-' + lp.variable + '-' + lp.prov_code_h
dump('lisa_prov', records(lp))

ld = pd.read_csv(f'{PRJ}/outputs/q2/q2_lisa_district.csv', dtype={'area_id': str, 'prov_code_h': str},
                 encoding='utf-8-sig')
ld = ld[ld.year_be == 2568].copy()
ld['amphoe_name'] = ld.amphoe_name.fillna('')
ld['real_value'] = np.where(ld.variable == 'ldr_dec', ld.value, np.exp(ld.value)).round(1)
ld['key'] = ld.variable + '-' + ld.area_id
ld = ld[['key', 'variable', 'area_id', 'area_type', 'amphoe_name', 'prov_name_th', 'region_bot', 'population',
         'real_value', 'cluster', 'p_sim', 'sig_fdr']]
dump('lisa_dist', records(ld))


# ---------------------------------------------------------------- shapes as SVG path strings
def ring_path(ring, grid):
    q = np.round(ring / grid) * grid
    keep = np.r_[True, np.any(np.diff(q, axis=0) != 0, axis=1)]
    q = q[keep]
    if len(q) < 4:
        return None, 0
    x = np.round((q[:, 0] - LON0) * COS * K, 1); y = np.round((LAT0 - q[:, 1]) * K, 1)
    area = abs(np.sum(x[:-1] * y[1:] - x[1:] * y[:-1])) / 2
    return 'M' + 'L'.join(f'{a:g},{b:g}' for a, b in zip(x[:-1], y[:-1])) + 'Z', area


def path_of(rings, grid, min_area):
    parts = [ring_path(rg, grid) for rg in rings]
    parts = [pp for pp in parts if pp[0]]
    if not parts:
        return ''
    big = [pp for pp in parts if pp[1] >= min_area] or [max(parts, key=lambda t: t[1])]
    return ''.join(pp[0] for pp in big)


g1, _ = read_polygons(os.path.join(SHP, 'tha_admin1'), 'adm1_pcode')
names = h.drop_duplicates('prov_code_h').set_index('prov_code_h')[['prov_name_th', 'region_bot']]
prov = {}
for k, rings in g1.items():
    prov.setdefault('43' if k == 'TH38' else k[2:], []).extend(rings)
dump('geo_prov', [{'prov_code_h': g, 'prov_name_th': names.prov_name_th[g], 'd': path_of(rs, 0.012, 0.6)}
                  for g, rs in sorted(prov.items())])

g2, r2, _, _ = pickle.load(open(CACHE, 'rb'))
unit = pd.read_csv(f'{PRJ}/processed/geo/district_units_2568.csv', dtype=str, encoding='utf-8-sig') \
    .set_index('adm2_pcode').unit_id
units = {}
for k, rings in g2.items():
    units.setdefault(unit[k], []).extend(rings)
dump('geo_dist', [{'unit_id': u, 'd': path_of(rs, 0.008, 0.15)} for u, rs in sorted(units.items())])

path = f'{OUT}/data.js'
with open(path, 'w', encoding='utf-8') as f:
    f.write('// Generated by src/dash_data.py — rows behind the dashboard. Do not edit by hand.\n')
    f.write('window.CG_DATA = ' + json.dumps(ALL, ensure_ascii=False, separators=(',', ':')) + ';\n')
print(f'wrote {path}: {os.path.getsize(path)/1e6:.1f} MB')
