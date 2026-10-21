"""
Step 1: build dim_area, province_panel and district_panel (annual, 2548-2568).

  * stock variables (deposits, loans, offices): value at December (`*_dec`) and 12-month average (`*_avg12`)
  * Bangkok = BOT row "อื่น ๆ" under กรุงเทพมหานคร (Bangkok branches EXCLUDING head offices);
    the head-office row is kept separately as prov_code 'HQ' (not attributable to any area)
  * Bueng Kan (38) was split from Nong Khai (43) in 2554 and only appears in D3 from 2556:
    `prov_code_h` merges 38 into 43 so every year has the same 75 areas (+ Bangkok = 76 units)

Usage: python build_panels.py <project_raw_dir> <district_monthly_D2.csv> <out_dir>
"""
import sys, os, glob, re
import pandas as pd, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from parse_bot import read_bot_wide

RAW, D2_CSV, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)
Y0, Y1 = 2548, 2568
SERIES_RANK = {'FI_CB_011_S1': 1, 'FI_CB_011_S2': 2, 'FI_CB_011_S3': 3, 'FI_CB_011_S4': 4, 'FI_CB_011_S5': 5}

# ---------------------------------------------------------------- 1.1 dim_area
adm1 = pd.read_excel(f'{RAW}/D7/tha_admin_boundaries.xlsx', sheet_name='tha_admin1', dtype=str)
adm2 = pd.read_excel(f'{RAW}/D7/tha_admin_boundaries.xlsx', sheet_name='tha_admin2', dtype=str)
pop = pd.read_csv(f'{RAW}/D6/dopa_population_amphoe_2548-2568.csv', dtype={'amphoe_code': str, 'prov_code': str},
                  encoding='utf-8-sig')

prov = adm1[['adm1_pcode', 'adm1_name1', 'adm1_name', 'area_sqkm']].rename(columns={
    'adm1_name1': 'prov_name_th', 'adm1_name': 'prov_name_en', 'area_sqkm': 'prov_area_sqkm'})
prov['prov_code'] = prov.adm1_pcode.str[2:]
prov['prov_code_h'] = prov.prov_code.replace({'38': '43'})

# BOT region of each province, read from the D3 hierarchy (S4 uses the 4 BOT regions + Bangkok)
d3 = pd.concat([read_bot_wide(f).assign(series=os.path.basename(f)[3:15]) for f in sorted(glob.glob(f'{RAW}/D3/*.XLSX'))])
s4 = d3[(d3.series == 'FI_CB_011_S4')].drop_duplicates('row').sort_values('row')
region, reg_map = None, {}
for _, r in s4.iterrows():
    a = r.area.replace('จังหวัด', '').strip()
    if r.indent == 0:
        region = 'กรุงเทพมหานคร' if 'กรุงเทพ' in a else a
    else:
        reg_map[a] = region
reg_map['กรุงเทพมหานคร'] = 'กรุงเทพมหานคร'
prov['region_bot'] = prov.prov_name_th.map(reg_map)
assert prov.region_bot.notna().all(), prov[prov.region_bot.isna()]

dist = adm2[['adm2_pcode', 'adm2_name1', 'adm2_name', 'adm1_pcode', 'area_sqkm']].rename(columns={
    'adm2_name1': 'amphoe_name_th', 'adm2_name': 'amphoe_name_en', 'area_sqkm': 'amphoe_area_sqkm'})
dist['amphoe_code'] = dist.adm2_pcode.str[2:]
dist['prov_code'] = dist.adm1_pcode.str[2:]
dist = dist.merge(prov[['prov_code', 'prov_code_h', 'prov_name_th', 'region_bot']], on='prov_code')

# Bueng Kan crosswalk: old Nong Khai codes (43xx, 2548-2553) -> current Bueng Kan codes (38xx), matched by name
old = pop[pop.amphoe_code.str.startswith('43') & ~pop.amphoe_code.isin(dist.amphoe_code)].drop_duplicates('amphoe_code')
nm = lambda s: re.sub(r'^(อำเภอ|เขต)', '', s).strip().replace('เมืองบึงกาฬ', 'บึงกาฬ')  # became the capital district
bk = dist[dist.prov_code == '38'].assign(key=lambda d: d.amphoe_name_th.map(nm))
xwalk = old.assign(key=old.amphoe_name.map(nm)).merge(bk[['key', 'amphoe_code']], on='key', suffixes=('_old', '_new'))
assert len(xwalk) == len(old), 'unmatched Bueng Kan code'
xwalk = xwalk[['amphoe_code_old', 'amphoe_code_new', 'amphoe_name']]
dist.to_csv(f'{OUT}/dim_district.csv', index=False, encoding='utf-8-sig')
prov.drop(columns='adm1_pcode').to_csv(f'{OUT}/dim_province.csv', index=False, encoding='utf-8-sig')
xwalk.to_csv(f'{OUT}/crosswalk_buengkan_codes.csv', index=False, encoding='utf-8-sig')

# ---------------------------------------------------------------- 1.2 province_panel
FIELD = {'รวมเงินรับฝาก': 'dep', 'รวมเงินฝาก': 'dep', 'รวมเงินให้สินเชื่อ': 'loan', 'จำนวนสำนักงาน': 'offices'}
x = d3[d3.field.isin(FIELD)].copy()
x['var'] = x.field.map(FIELD)
x['name'] = x.area.str.replace('จังหวัด', '', regex=False).str.replace(r'\s*\d/$', '', regex=True).str.strip()
# label each row: HQ, Bangkok-excl-HQ ("อื่น ๆ" right under Bangkok), or a province
x['prov_code'] = x.name.map(prov.set_index('prov_name_th').prov_code)
x.loc[x.name == 'สำนักงานใหญ่', 'prov_code'] = 'HQ'
x.loc[x.name == 'อื่น ๆ', 'prov_code'] = '10'          # Bangkok excluding head offices
x.loc[x.name == 'กรุงเทพมหานคร', 'prov_code'] = 'BKK_TOTAL'
x = x[x.prov_code.notna()]
# one value per (month, area, var): newest series wins (= new loan basis in overlaps, like D2)
x['rank'] = x.series.map(SERIES_RANK)
x = x.sort_values('rank').drop_duplicates(['year_be', 'month', 'prov_code', 'var'], keep='last')
m = x.pivot_table(index=['year_be', 'month', 'prov_code'], columns='var', values='value', aggfunc='first').reset_index()
m = m[(m.year_be >= Y0) & (m.year_be <= Y1)]

# check: Bangkok total == HQ + Bangkok-excl-HQ, and national total
chk = m.pivot_table(index=['year_be', 'month'], columns='prov_code', values='dep')
assert (chk['BKK_TOTAL'] - chk['HQ'] - chk['10']).abs().max() <= 2
m = m[m.prov_code != 'BKK_TOTAL']
# Bueng Kan rows that are all-NaN before 2556 -> drop (its money is inside Nong Khai then)
m = m[~((m.prov_code == '38') & m.dep.isna())]

def annual(df, keys):
    g = df.groupby(keys + ['year_be'])
    dec = df[df.month == 12].set_index(keys + ['year_be'])[['dep', 'loan', 'offices']].add_suffix('_dec')
    avg = g[['dep', 'loan', 'offices']].mean().add_suffix('_avg12')
    n = g.size().rename('n_months')
    out = dec.join(avg, how='outer').join(n).reset_index()
    out.loc[out.n_months < 12, ['dep_avg12', 'loan_avg12', 'offices_avg12']] = np.nan
    return out

pp = annual(m, ['prov_code'])
# sector shares of loans (D4), December, ISIC Rev.4 from 2556
d4 = pd.concat([read_bot_wide(f).assign(series=os.path.basename(f)) for f in sorted(glob.glob(f'{RAW}/D4/FI_CB_087_S*.XLSX'))])
d4 = d4[d4.month == 12].copy()
d4['name'] = d4.area.str.replace('จังหวัด', '', regex=False).str.strip()
d4['prov_code'] = d4.name.map(prov.set_index('prov_name_th').prov_code)
d4 = d4[d4.prov_code.notna()].sort_values('series').drop_duplicates(['year_be', 'prov_code', 'field'], keep='last')
SECT = {'การเกษตร การป่าไม้ และการประมง': 'agri', 'การผลิต': 'manuf',
        'การขายส่งและการขายปลีก การซ่อมยานยนต์และจักรยานยนต์': 'trade', 'การอุปโภคบริโภคส่วนบุคคล': 'personal',
        'กิจกรรมอสังหาริมทรัพย์': 'realestate', 'การบริการ': 'services', 'รวมทั้งสิ้น': 'total'}
s = d4[d4.field.isin(SECT)].assign(sec=lambda d: d.field.map(SECT)).pivot_table(
    index=['year_be', 'prov_code'], columns='sec', values='value', aggfunc='first')
shares = s.drop(columns='total').div(s['total'], axis=0).add_prefix('loan_share_').reset_index()
# D4 Bangkok row includes head offices -> shares for prov 10 are not comparable; blank them
shares.loc[shares.prov_code == '10', [c for c in shares if c.startswith('loan_share_')]] = np.nan
pp = pp.merge(shares, on=['year_be', 'prov_code'], how='left')

ppop = pop.groupby(['year_be', 'prov_code'], as_index=False).agg(population=('population', 'sum'), houses=('houses', 'sum'))
# outer: keeps Bueng Kan population in 2554-2555 even though D3 still reports its money inside Nong Khai
pp = pp.merge(ppop, on=['year_be', 'prov_code'], how='outer')
pp = pp.merge(prov[['prov_code', 'prov_code_h', 'prov_name_th', 'prov_name_en', 'region_bot']], on='prov_code', how='left')
pp.loc[pp.prov_code == 'HQ', ['prov_name_th', 'region_bot']] = ['สำนักงานใหญ่ธนาคารพาณิชย์', 'HQ']
for b in ['dec', 'avg12']:
    pp[f'ldr_{b}'] = pp[f'loan_{b}'] / pp[f'dep_{b}'] * 100
    pp[f'loan_pc_{b}'] = pp[f'loan_{b}'] * 1e6 / pp.population           # baht per person
    pp[f'dep_pc_{b}'] = pp[f'dep_{b}'] * 1e6 / pp.population
    pp[f'net_outflow_{b}'] = pp[f'dep_{b}'] - pp[f'loan_{b}']             # MB, >0 = savings leave the area
pp['offices_per_100k'] = pp.offices_dec / pp.population * 1e5
pp['year_ce'] = pp.year_be - 543
pp['is_buengkan_split'] = (pp.prov_code == '38').astype(int)

# harmonised version: Bueng Kan merged into Nong Khai -> same 75 areas + Bangkok every year
num = ['dep_dec', 'loan_dec', 'offices_dec', 'dep_avg12', 'loan_avg12', 'offices_avg12', 'population', 'houses']
h = pp[pp.prov_code != 'HQ'].groupby(['year_be', 'prov_code_h'], as_index=False)[num].sum(min_count=1)
h = h.merge(prov[prov.prov_code == prov.prov_code_h][['prov_code_h', 'prov_name_th', 'region_bot']], on='prov_code_h')
h.loc[h.prov_code_h == '43', 'prov_name_th'] = 'หนองคาย+บึงกาฬ'
for b in ['dec', 'avg12']:
    h[f'ldr_{b}'] = h[f'loan_{b}'] / h[f'dep_{b}'] * 100
    h[f'loan_pc_{b}'] = h[f'loan_{b}'] * 1e6 / h.population
    h[f'dep_pc_{b}'] = h[f'dep_{b}'] * 1e6 / h.population
    h[f'net_outflow_{b}'] = h[f'dep_{b}'] - h[f'loan_{b}']
h['offices_per_100k'] = h.offices_dec / h.population * 1e5
h['year_ce'] = h.year_be - 543

cols = ['year_be', 'year_ce', 'prov_code', 'prov_code_h', 'prov_name_th', 'prov_name_en', 'region_bot', 'population',
        'dep_dec', 'loan_dec', 'offices_dec', 'ldr_dec', 'loan_pc_dec', 'dep_pc_dec', 'net_outflow_dec',
        'dep_avg12', 'loan_avg12', 'offices_avg12', 'ldr_avg12', 'loan_pc_avg12', 'dep_pc_avg12', 'net_outflow_avg12',
        'n_months', 'offices_per_100k'] + [c for c in pp if c.startswith('loan_share_')] + ['is_buengkan_split']
pp[cols].sort_values(['year_be', 'prov_code']).to_csv(f'{OUT}/province_panel.csv', index=False, encoding='utf-8-sig')
h.sort_values(['year_be', 'prov_code_h']).to_csv(f'{OUT}/province_panel_harmonised.csv', index=False, encoding='utf-8-sig')

# ---------------------------------------------------------------- 1.3 district_panel (December)
d2 = pd.read_csv(D2_CSV, dtype={'amphoe_code': str, 'prov_code': str}, encoding='utf-8-sig')
d2 = d2[(d2.month == 12) & (d2.is_hq == 0) & (d2.is_suppressed == 0) & (d2.data_gap == 0) & d2.year_be.between(Y0, Y1)]
d2 = d2.rename(columns={'dep_total': 'dep_dec', 'loan_total': 'loan_dec', 'offices': 'offices_dec'})
d2['prov_code_h'] = d2.prov_code.replace({'38': '43'})
vis = d2[['year_be', 'prov_code_h', 'amphoe_code', 'amphoe_name', 'dep_dec', 'loan_dec', 'offices_dec']]
vis = vis.merge(pop[['year_be', 'amphoe_code', 'population']], on=['year_be', 'amphoe_code'], how='left')
assert vis.population.notna().all()

ph = h[['year_be', 'prov_code_h', 'dep_dec', 'loan_dec', 'offices_dec', 'population']]
sv = vis.groupby(['year_be', 'prov_code_h'], as_index=False)[['dep_dec', 'loan_dec', 'offices_dec', 'population']].sum()
nvis = vis.groupby(['year_be', 'prov_code_h']).size().rename('n_visible')
pop_h = pop.assign(prov_code_h=pop.prov_code.replace({'38': '43'}))
ndist = pop_h.groupby(['year_be', 'prov_code_h']).size().rename('n_districts')
rest = ph.merge(sv, on=['year_be', 'prov_code_h'], how='left', suffixes=('', '_vis')).fillna({'dep_dec_vis': 0, 'loan_dec_vis': 0, 'offices_dec_vis': 0, 'population_vis': 0})
for c in ['dep_dec', 'loan_dec', 'offices_dec', 'population']:
    rest[c] = rest[c] - rest[f'{c}_vis']
rest = rest.join(nvis, on=['year_be', 'prov_code_h']).join(ndist, on=['year_be', 'prov_code_h'])
rest['n_visible'] = rest.n_visible.fillna(0).astype(int)
rest['n_hidden_districts'] = rest.n_districts - rest.n_visible
# tiny negatives = rounding between the two BOT reports -> 0; a real negative (D2 > D3) = inconsistent -> blank + flag
small = 0.01 * rest[['dep_dec_vis', 'loan_dec_vis']].max(axis=1)
bad = (rest.dep_dec < -small) | (rest.loan_dec < -small)
rest['rest_negative_clipped'] = bad.astype(int)
for c in ['dep_dec', 'loan_dec', 'offices_dec']:
    rest[c] = rest[c].clip(lower=0)
rest.loc[bad, ['dep_dec', 'loan_dec', 'offices_dec']] = np.nan
rest = rest[rest.n_hidden_districts > 0]                    # provinces with every district visible have no rest unit
rest['area_id'] = rest.prov_code_h + '_REST'
rest['area_type'] = 'rest_of_province'
rest['amphoe_name'] = 'อำเภออื่น ๆ (ไม่เปิดเผย) ' + rest.n_hidden_districts.astype(str) + ' อำเภอ'
vis = vis.assign(area_id=vis.amphoe_code, area_type='district', n_hidden_districts=0, rest_negative_clipped=0)
dp = pd.concat([vis, rest[[c for c in vis.columns if c in rest.columns]]], ignore_index=True)
dp = dp.merge(prov[prov.prov_code == prov.prov_code_h][['prov_code_h', 'region_bot']], on='prov_code_h')
dp['ldr_dec'] = dp.loan_dec / dp.dep_dec * 100
dp['loan_pc_dec'] = dp.loan_dec * 1e6 / dp.population
dp['dep_pc_dec'] = dp.dep_dec * 1e6 / dp.population
dp['offices_per_100k'] = dp.offices_dec / dp.population * 1e5
dp['year_ce'] = dp.year_be - 543
dp = dp[['year_be', 'year_ce', 'area_id', 'area_type', 'prov_code_h', 'region_bot', 'amphoe_code', 'amphoe_name',
         'n_hidden_districts', 'population', 'dep_dec', 'loan_dec', 'offices_dec', 'ldr_dec', 'loan_pc_dec',
         'dep_pc_dec', 'offices_per_100k', 'rest_negative_clipped']]
dp.sort_values(['year_be', 'prov_code_h', 'area_type', 'area_id']).to_csv(f'{OUT}/district_panel.csv', index=False,
                                                                           encoding='utf-8-sig')

# ---------------------------------------------------------------- validation report
rep = []
tot = dp.groupby(['year_be', 'prov_code_h'])[['dep_dec', 'loan_dec', 'population']].sum()
cmp = tot.join(h.set_index(['year_be', 'prov_code_h'])[['dep_dec', 'loan_dec', 'population']], rsuffix='_prov')
for c in ['dep_dec', 'loan_dec', 'population']:
    rel = ((cmp[c] - cmp[f'{c}_prov']).abs() / cmp[f'{c}_prov'])
    rep.append((f'district_panel sum vs province ({c}): province-years off by >0.1%', int((rel > 0.001).sum())))
nat = m[m.month == 12].groupby('year_be').dep.sum()
d3tot = d3[d3.area.str.contains('รวมทั้งสิ้น') & d3.field.isin(['รวมเงินรับฝาก', 'รวมเงินฝาก']) & (d3.month == 12)] \
    .assign(rank=lambda d: d.series.map(SERIES_RANK)).sort_values('rank').drop_duplicates('year_be', keep='last').set_index('year_be').value
rep.append(('province_panel (incl HQ) == national total, max abs diff', float((nat - d3tot.reindex(nat.index)).abs().max())))
rep.append(('province_panel population == DOPA national, max abs diff',
            float((pp[pp.prov_code != 'HQ'].groupby('year_be').population.sum() - pop.groupby('year_be').population.sum()).abs().max())))
rep.append(('rest units clipped at 0 (count)', int(rest.rest_negative_clipped.sum())))
rep.append(('province-years in harmonised panel', len(h)))
rep.append(('district_panel rows / visible districts / rest units', f'{len(dp)} / {(dp.area_type=="district").sum()} / {(dp.area_type!="district").sum()}'))
pd.DataFrame(rep, columns=['check', 'result']).to_csv(f'{OUT}/_validation_step1.csv', index=False, encoding='utf-8-sig')
for r in rep: print(f'{r[0]:70s} {r[1]}')
