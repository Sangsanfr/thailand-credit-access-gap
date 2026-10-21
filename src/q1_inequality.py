"""
Q1: How unequal is commercial-bank credit across provinces, and is the gap widening or narrowing?

Input : province_panel_harmonised.csv (75 areas + Bangkok-excl-HQ = 76 units, Bueng Kan merged into Nong Khai, 2548-2568)
Output: q1_inequality_by_year.csv, q1_convergence.csv, q1_region_flows.csv, q1_ldr_latest.csv
Usage : python q1_inequality.py <panels_dir> <out_dir>
"""
import sys, os
import numpy as np, pandas as pd

P, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
h = pd.read_csv(f'{P}/province_panel_harmonised.csv', dtype={'prov_code_h': str}, encoding='utf-8-sig')
BREAK_YEAR = 2558   # Jan 2558: some banks moved hire-purchase car loans from branches to head office


def gini(x, w=None):
    """Gini coefficient; with weights w = population-weighted (each person gets the area's per-capita value)."""
    x = np.asarray(x, float); w = np.ones_like(x) if w is None else np.asarray(w, float)
    o = np.argsort(x); x, w = x[o], w[o]
    cw = np.cumsum(w) / w.sum(); cxw = np.cumsum(x * w) / (x * w).sum()
    return 1 - np.sum((cw - np.r_[0, cw[:-1]]) * (cxw + np.r_[0, cxw[:-1]]))


def theil_decomp(y_pc, pop, group):
    """Population-weighted Theil T of a per-capita variable, split into between-group and within-group parts."""
    df = pd.DataFrame({'y': y_pc, 'n': pop, 'g': group})
    Y, N = (df.y * df.n).sum(), df.n.sum(); mu = Y / N
    s = df.y * df.n / Y                                    # each area's share of the total
    total = np.sum(s * np.log(df.y / mu))
    g = df.groupby('g').apply(lambda d: pd.Series({'Y': (d.y * d.n).sum(), 'N': d.n.sum()}), include_groups=False)
    sg = g.Y / Y; mug = g.Y / g.N
    between = np.sum(sg * np.log(mug / mu))
    return total, between, total - between


rows = []
for basis in ['dec', 'avg12']:
    for scope in ['all', 'ex_bkk']:
        d0 = h if scope == 'all' else h[h.prov_code_h != '10']
        for y, d in d0.groupby('year_be'):
            d = d.dropna(subset=[f'loan_pc_{basis}', f'dep_pc_{basis}', 'population'])
            lp, dp, pop = d[f'loan_pc_{basis}'], d[f'dep_pc_{basis}'], d.population
            t, tb, tw = theil_decomp(lp, pop, d.region_bot)
            rows.append({
                'year_be': y, 'year_ce': y - 543, 'basis': basis, 'scope': scope, 'n_areas': len(d),
                'gini_loan_pc': gini(lp), 'gini_loan_pc_popw': gini(lp, pop),
                'gini_dep_pc': gini(dp), 'gini_dep_pc_popw': gini(dp, pop),
                'cv_loan_pc': lp.std() / lp.mean(), 'sd_log_loan_pc': np.log(lp).std(),
                'p90_p10_loan_pc': lp.quantile(.9) / lp.quantile(.1), 'max_min_loan_pc': lp.max() / lp.min(),
                'theil_loan_pc': t, 'theil_between_region': tb, 'theil_within_region': tw,
                'theil_between_share': tb / t,
                'ldr_median': d[f'ldr_{basis}'].median(),
                'ldr_p25': d[f'ldr_{basis}'].quantile(.25), 'ldr_p75': d[f'ldr_{basis}'].quantile(.75),
                'n_ldr_below_70': int((d[f'ldr_{basis}'] < 70).sum()),
                'n_ldr_above_100': int((d[f'ldr_{basis}'] > 100).sum()),
                'loan_pc_mean': lp.mean(), 'loan_pc_median': lp.median()})
ineq = pd.DataFrame(rows)
ineq.to_csv(f'{OUT}/q1_inequality_by_year.csv', index=False, encoding='utf-8-sig')

# beta-convergence: do provinces that started with less credit per person grow faster? (ex-Bangkok)
conv = []
for (a, b) in [(2548, 2557), (2559, 2568), (2548, 2568)]:
    d = h[h.prov_code_h != '10'].pivot_table(index='prov_code_h', columns='year_be', values='loan_pc_dec')[[a, b]].dropna()
    x = np.log(d[a]); g = (np.log(d[b]) - np.log(d[a])) / (b - a) * 100     # % per year
    X = np.c_[np.ones(len(x)), x]; beta, *_ = np.linalg.lstsq(X, g, rcond=None)
    resid = g - X @ beta; se = np.sqrt(resid @ resid / (len(x) - 2) / np.sum((x - x.mean()) ** 2))
    r2 = 1 - resid @ resid / np.sum((g - g.mean()) ** 2)
    conv.append({'period': f'{a}-{b}', 'n': len(d), 'beta_slope': beta[1], 'se': se, 't': beta[1] / se, 'r2': r2,
                 'mean_growth_pct_pa': g.mean(), 'crosses_break_2558': a < BREAK_YEAR <= b})
pd.DataFrame(conv).to_csv(f'{OUT}/q1_convergence.csv', index=False, encoding='utf-8-sig')

# where does the money go? net deposit surplus (deposits - loans) by region, December
reg = h.groupby(['year_be', 'region_bot'], as_index=False)[['dep_dec', 'loan_dec', 'population']].sum()
reg['net_outflow_dec'] = reg.dep_dec - reg.loan_dec
reg['ldr_dec'] = reg.loan_dec / reg.dep_dec * 100
reg['loan_pc_dec'] = reg.loan_dec * 1e6 / reg.population
reg['dep_pc_dec'] = reg.dep_dec * 1e6 / reg.population
reg.to_csv(f'{OUT}/q1_region_flows.csv', index=False, encoding='utf-8-sig')

latest = h[h.year_be == h.year_be.max()].sort_values('ldr_dec')
latest[['prov_code_h', 'prov_name_th', 'region_bot', 'population', 'dep_dec', 'loan_dec', 'ldr_dec', 'loan_pc_dec',
        'dep_pc_dec', 'offices_per_100k', 'net_outflow_dec']].to_csv(f'{OUT}/q1_ldr_latest.csv', index=False,
                                                                    encoding='utf-8-sig')

# console summary
show = ineq[(ineq.basis == 'dec')].pivot_table(index='year_be', columns='scope',
        values=['gini_loan_pc', 'gini_dep_pc', 'theil_between_share', 'sd_log_loan_pc', 'ldr_median', 'n_ldr_above_100'])
pd.set_option('display.width', 250)
print(show.round(3).to_string())
print(pd.DataFrame(conv).round(3).to_string(index=False))
r = ineq[(ineq.scope == 'ex_bkk')].pivot_table(index='year_be', columns='basis', values='gini_loan_pc')
print('\nrobustness dec vs avg12 (ex-BKK gini loan pc): max abs diff', round((r.dec - r.avg12).abs().max(), 4))
print(reg[reg.year_be.isin([2548, 2558, 2568])].round(1).to_string(index=False))
