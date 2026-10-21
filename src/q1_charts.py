"""Static PNG charts for Q1. Usage: python q1_charts.py <q1_dir> <panels_dir> <fig_dir>"""
import sys, os
import numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

Q, P, F = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(F, exist_ok=True)

# ---- tokens (reference palette, light mode)
SURF, INK, INK2, MUTED, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#8a8984', '#e4e3df'
S1, S2, S3, S4, S5 = '#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4'
OTHER = '#c3c2b7'
plt.rcParams.update({
    'font.family': ['Loma', 'DejaVu Sans'], 'font.size': 11, 'figure.facecolor': SURF, 'axes.facecolor': SURF,
    'savefig.facecolor': SURF, 'axes.edgecolor': GRID, 'axes.labelcolor': INK2, 'xtick.color': INK2,
    'ytick.color': INK2, 'text.color': INK, 'axes.spines.top': False, 'axes.spines.right': False,
    'axes.spines.left': False, 'axes.grid': True, 'axes.grid.axis': 'y', 'grid.color': GRID, 'grid.linewidth': 0.8,
    'xtick.major.size': 0, 'ytick.major.size': 0, 'lines.linewidth': 2})
SRC = 'ที่มา: ธนาคารแห่งประเทศไทย (FI_CB_011), กรมการปกครอง · คำนวณโดยผู้เขียน'


def frame(ax, title, subtitle):
    ax.set_title(title, loc='left', fontsize=15, fontweight='bold', color=INK, pad=28)
    ax.text(0, 1.02, subtitle, transform=ax.transAxes, fontsize=10.5, color=INK2, va='bottom')


def breaks(ax, ymax, compact=False):
    """Data breaks (bookkeeping changes, not economics). Left label right-aligned, right label left-aligned."""
    if compact:
        for x, ha, dx in ((2558, 'right', -0.2), (2561, 'left', 0.2)):
            ax.axvline(x, color=MUTED, lw=1, ls=(0, (3, 3)), zorder=1)
            ax.text(x + dx, ymax, f'รอยต่อข้อมูล {x}', fontsize=8.5, color=MUTED, va='bottom', ha=ha)
        return
    for x, lab, ha, dx in [(2558, 'รอยต่อข้อมูล ม.ค. 2558:\nย้ายสินเชื่อเช่าซื้อไปบันทึก\nที่สำนักงานใหญ่', 'right', -0.2),
                           (2561, 'รอยต่อข้อมูล 2561:\nย้ายสินเชื่อจากสำนักงาน\nใหญ่กลับไปที่สาขา', 'left', 0.2)]:
        ax.axvline(x, color=MUTED, lw=1, ls=(0, (3, 3)), zorder=1)
        ax.text(x + dx, ymax, lab, fontsize=8.5, color=MUTED, va='top', ha=ha, linespacing=1.3)


def be_axis(ax):
    ax.set_xticks(range(2548, 2569, 2))


ineq = pd.read_csv(f'{Q}/q1_inequality_by_year.csv', encoding='utf-8-sig')
reg = pd.read_csv(f'{Q}/q1_region_flows.csv', encoding='utf-8-sig')
lat = pd.read_csv(f'{Q}/q1_ldr_latest.csv', dtype={'prov_code_h': str}, encoding='utf-8-sig')

# ---------------------------------------------------------------- C1 Gini over time (ex-Bangkok)
d = ineq[(ineq.scope == 'ex_bkk') & (ineq.basis == 'dec')]
r = ineq[(ineq.scope == 'ex_bkk') & (ineq.basis == 'avg12')]
fig, ax = plt.subplots(figsize=(10, 5.6))
ax.plot(d.year_be, d.gini_dep_pc, color=S2, marker='o', ms=4, zorder=3)
ax.plot(d.year_be, d.gini_loan_pc, color=S1, marker='o', ms=4, zorder=3)
ax.plot(r.year_be, r.gini_loan_pc, color=S1, lw=1, ls=(0, (2, 2)), zorder=2)
ax.set_ylim(0.40, 0.49); ax.set_xlim(2547.5, 2573.2)
breaks(ax, 0.4885)
last = d.iloc[-1]
ax.text(2568.4, last.gini_dep_pc, f'เงินฝากต่อหัว  {last.gini_dep_pc:.3f}', color=INK, va='center', fontsize=10)
ax.text(2568.4, last.gini_loan_pc, f'สินเชื่อต่อหัว  {last.gini_loan_pc:.3f}', color=INK, va='center', fontsize=10)
ax.text(2568.4, last.gini_loan_pc - 0.005, 'เส้นประ = ค่าเฉลี่ย 12 เดือน', color=MUTED, va='center', fontsize=8.5)
first = d.iloc[0]
ax.annotate(f'{first.gini_loan_pc:.3f}', (first.year_be, first.gini_loan_pc), xytext=(0, -15), textcoords='offset points',
            fontsize=9, color=INK2, ha='center')
lo = d.loc[d.gini_loan_pc.idxmin()]
ax.annotate(f'ต่ำสุด {lo.gini_loan_pc:.3f}', (lo.year_be, lo.gini_loan_pc), xytext=(0, -16), textcoords='offset points',
            fontsize=9, color=INK2, ha='center')
ax.set_ylabel('Gini (0 = เท่ากันทุกจังหวัด)')
be_axis(ax)
frame(ax, 'ในรอบ 20 ปี ความเหลื่อมล้ำของสินเชื่อต่อหัวแทบไม่ลดลง ส่วนเงินฝากกลับเพิ่มขึ้นตั้งแต่ 2564',
      'ค่า Gini ระหว่าง 75 พื้นที่ (76 จังหวัด รวมบึงกาฬกับหนองคาย ไม่รวมกรุงเทพฯ) · ยอดคงค้าง ณ ธ.ค. · ธนาคารพาณิชย์เท่านั้น')
fig.text(0.01, 0.01, SRC, fontsize=8, color=MUTED)
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(f'{F}/q1_c1_gini_trend.png', dpi=200); plt.close(fig)

# ---------------------------------------------------------------- C2 LDR by region
regs = [('ภาคตะวันออกเฉียงเหนือ', 'ตะวันออกเฉียงเหนือ', S1), ('ภาคใต้', 'ใต้', S2), ('ภาคเหนือ', 'เหนือ', S3),
        ('ภาคกลาง', 'กลาง', S4), ('กรุงเทพมหานคร', 'กรุงเทพฯ (ไม่รวมสนญ.)', S5)]
fig, ax = plt.subplots(figsize=(10, 5.6))
ax.axhline(100, color=INK2, lw=1, zorder=1)
ax.text(2568.4, 101.5, '100% = สินเชื่อเท่ากับเงินฝาก', fontsize=9, color=INK2)
ends = []
for key, lab, c in regs:
    x = reg[reg.region_bot == key].sort_values('year_be')
    ax.plot(x.year_be, x.ldr_dec, color=c, zorder=3)
    ends.append((x.ldr_dec.iloc[-1], lab, c))
ends.sort(); ys = []
for v, lab, c in ends:                                   # nudge end labels apart (>= 4.5 pts)
    y = v if not ys or v - ys[-1] >= 4.5 else ys[-1] + 4.5
    ys.append(y); ax.text(2568.4, y, f'{lab}  {v:.0f}%', color=INK, va='center', fontsize=10)
    ax.plot([2568.05, 2568.3], [v, y], color=c, lw=1)
ax.set_xlim(2547.5, 2573.5); ax.set_ylim(35, 140); be_axis(ax)
breaks(ax, 136, compact=True)
ax.set_ylabel('สินเชื่อ ÷ เงินฝาก (%)')
frame(ax, 'ตั้งแต่ 2563 ทุกภาคมี LDR ลดลงต่อเนื่อง และปี 2568 ทุกภาคต่ำกว่า 100%',
      'อัตราส่วนสินเชื่อต่อเงินฝาก (LDR) ของธนาคารพาณิชย์รายภาค · ต่ำกว่า 100% = เงินออมของพื้นที่ถูกนำไปปล่อยกู้ที่อื่น')
fig.text(0.01, 0.035, 'รอยต่อข้อมูล: ม.ค. 2558 ธนาคารบางแห่งย้ายสินเชื่อเช่าซื้อรถยนต์ไปบันทึกที่สำนักงานใหญ่ · 2561 ย้ายสินเชื่อบางส่วนจากสำนักงานใหญ่กลับไปที่สาขา · กรุงเทพฯ ไม่รวมสำนักงานใหญ่', fontsize=8, color=MUTED)
fig.text(0.01, 0.01, SRC, fontsize=8, color=MUTED)
fig.tight_layout(rect=(0, 0.055, 1, 1)); fig.savefig(f'{F}/q1_c2_ldr_by_region.png', dpi=200); plt.close(fig)

# ---------------------------------------------------------------- C3 LDR vs credit per person, latest year
x = lat[lat.prov_code_h != '10'].copy()
ne = x.region_bot == 'ภาคตะวันออกเฉียงเหนือ'
fig, ax = plt.subplots(figsize=(10, 6.2))
ax.grid(axis='x', color=GRID, lw=0.8)
ax.axhline(100, color=INK2, lw=1, zorder=1)
ax.scatter(x[~ne].loan_pc_dec / 1000, x[~ne].ldr_dec, s=46, color=OTHER, edgecolor=SURF, linewidth=1.5, zorder=2)
ax.scatter(x[ne].loan_pc_dec / 1000, x[ne].ldr_dec, s=56, color=S1, edgecolor=SURF, linewidth=1.5, zorder=3)
ax.set_xscale('log')
ax.set_xticks([10, 20, 50, 100, 200]); ax.set_xticklabels(['10,000', '20,000', '50,000', '100,000', '200,000'])
lab = pd.concat([x.nlargest(2, 'ldr_dec'), x.nsmallest(2, 'ldr_dec'), x.nlargest(3, 'loan_pc_dec'), x.nsmallest(2, 'loan_pc_dec')]).drop_duplicates('prov_code_h')
OFF = {'อำนาจเจริญ': (-6, 6, 'right'), 'ปัตตานี': (6, -12, 'left')}
for _, r in lab.iterrows():
    dx, dy, ha = OFF.get(r.prov_name_th, (6, 4, 'left'))
    ax.annotate(r.prov_name_th, (r.loan_pc_dec / 1000, r.ldr_dec), xytext=(dx, dy), textcoords='offset points',
                fontsize=9, color=INK2, ha=ha)
ax.text(0.02, 0.96, '● ภาคตะวันออกเฉียงเหนือ', color=S1, transform=ax.transAxes, fontsize=10, va='top')
ax.text(0.02, 0.91, '● ภาคอื่น', color=MUTED, transform=ax.transAxes, fontsize=10, va='top')
ax.text(ax.get_xlim()[1], 101.5, 'สินเชื่อ = เงินฝาก', fontsize=9, color=INK2, ha='right')
ax.set_xlabel('สินเชื่อธนาคารพาณิชย์ต่อประชากร 1 คน (บาท, สเกล log)')
ax.set_ylabel('สินเชื่อ ÷ เงินฝาก (%)')
yr = int(lat.prov_code_h.size and 2568)
frame(ax, 'อีสานมี LDR สูงที่สุด แต่สินเชื่อต่อหัวยังอยู่ในกลุ่มล่าง',
      f'75 พื้นที่ (บึงกาฬรวมกับหนองคาย ไม่รวมกรุงเทพฯ) · ธ.ค. {yr} · LDR สูงเพราะเงินฝากน้อย ไม่ได้แปลว่าเข้าถึงสินเชื่อได้มาก')
fig.text(0.01, 0.01, SRC, fontsize=8, color=MUTED)
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(f'{F}/q1_c3_ldr_vs_credit_pc.png', dpi=200); plt.close(fig)
print('saved 3 charts to', F)
