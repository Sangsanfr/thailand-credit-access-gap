"""Keep D2 only (drop the D1 web month) and fix the source gaps found during validation.
Usage: python clean_d2.py <district_monthly_D2_D1.csv> <out_csv>"""
import sys, pandas as pd
src, out = sys.argv[1], sys.argv[2]
df = pd.read_csv(src, dtype={'amphoe_code': str, 'prov_code': str}, encoding='utf-8-sig')
df = df[df.source == 'D2'].copy()

dep_parts = ['dep_demand', 'dep_savings', 'dep_time', 'dep_pn', 'dep_ncd', 'dep_other']
loan_parts = ['loan_overdraft', 'loan_loans', 'loan_bills_other']
vis = df.is_suppressed == 0
df['dep_total_imputed'] = 0
df['data_gap'] = 0
# total missing but components present -> rebuild total from components
m = vis & df.dep_total.isna() & df[dep_parts].notna().any(axis=1)
df.loc[m, 'dep_total'] = df.loc[m, dep_parts].fillna(0).sum(axis=1); df.loc[m, 'dep_total_imputed'] = 1
m = vis & df.loan_total.isna() & df[loan_parts].notna().any(axis=1)
df.loc[m, 'loan_total'] = df.loc[m, loan_parts].fillna(0).sum(axis=1); df.loc[m, 'dep_total_imputed'] += 2
# row listed in the report but completely empty -> keep blank, flag
df.loc[vis & df.dep_total.isna() & df.loan_total.isna(), 'data_gap'] = 1
df['ldr_pct'] = (df.loan_total / df.dep_total * 100).round(2)
df = df.drop(columns='source')
df.to_csv(out, index=False, encoding='utf-8-sig')
print(df.shape, '| months', df.period.nunique(), df.period.min(), '->', df.period.max(),
      '| imputed', (df.dep_total_imputed > 0).sum(), '| gaps', df.data_gap.sum())
