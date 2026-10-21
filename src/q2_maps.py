"""Maps and chart for Q2. Usage: python q2_maps.py <q2_dir> <panels_dir> <geo_dir> <fig_dir>"""
import sys, os, json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch, Patch, Rectangle
from matplotlib.collections import PatchCollection

Q, P, G, F = sys.argv[1:5]
os.makedirs(F, exist_ok=True)

SURF, INK, INK2, MUTED, GRID = '#fcfcfb', '#0b0b0b', '#52514e', '#8a8984', '#e4e3df'
S1, S2, S3 = '#2a78d6', '#eb6834', '#1baf7a'
BLUE = ['#b7d3f6', '#86b6ef', '#3987e5', '#1c5cab', '#0d366b']           # reference sequential steps 150-700
ORANGE = ['#fbd9c8', '#f5ac88', '#eb6834', '#c24d1f', '#8a3412']         # second sequential context
LISA_C = {'HH': '#184f95', 'HL': '#6da7ec', 'LL': '#c93837', 'LH': '#ee8885', 'ns': '#ebeae6'}
plt.rcParams.update({'font.family': ['Loma', 'DejaVu Sans'], 'font.size': 11, 'figure.facecolor': SURF,
                     'axes.facecolor': SURF, 'savefig.facecolor': SURF, 'text.color': INK})
SRC = 'ที่มา: ธนาคารแห่งประเทศไทย (FI_CB_011, cb_t3T-district), กรมการปกครอง, OCHA/HDX (ขอบเขตการปกครอง) · คำนวณโดยผู้เขียน'
ASPECT = 1 / np.cos(np.deg2rad(13.0))


def load(path):
    gj = json.load(open(path, encoding='utf-8'))
    return {f['properties']['id']: (f['properties'], [np.array(p[0]) for p in f['geometry']['coordinates']])
            for f in gj['features']}


def path_of(rings):
    verts, codes = [], []
    for r in rings:
        verts.append(r); codes += [Path.MOVETO] + [Path.LINETO] * (len(r) - 2) + [Path.CLOSEPOLY]
    return Path(np.vstack(verts), codes)


def draw(ax, geoms, color_of, edge=SURF, lw=0.4, z=1):
    patches, cols = [], []
    for k, (_, rings) in geoms.items():
        c = color_of(k)
        if c is None:
            continue
        patches.append(PathPatch(path_of(rings))); cols.append(c)
    ax.add_collection(PatchCollection(patches, facecolors=cols, edgecolors=edge, linewidths=lw, zorder=z))


def outline(ax, geoms, color=INK2, lw=0.6, z=3):
    ax.add_collection(PatchCollection([PathPatch(path_of(r)) for _, r in geoms.values()], facecolors='none',
                                      edgecolors=color, linewidths=lw, zorder=z))


def setup(ax, title=None, xlim=(97.25, 105.75), ylim=(5.5, 20.6)):
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_aspect(ASPECT); ax.axis('off')
    if title:
        ax.set_title(title, loc='left', fontsize=12.5, fontweight='bold', color=INK, pad=6)


def centroid(rings):
    r = max(rings, key=len)
    return r[:, 0].mean(), r[:, 1].mean()


def label(ax, geoms, k, text=None, dx=0, dy=0, ha='center', size=8.5):
    x, y = centroid(geoms[k][1])
    ax.annotate(text or geoms[k][0]['name_th'], (x, y), xytext=(x + dx, y + dy), fontsize=size, color=INK, ha=ha,
                va='center', zorder=6, arrowprops=dict(arrowstyle='-', color=INK2, lw=0.6) if (dx or dy) else None)


def classed(values, breaks, colors):
    idx = np.digitize(values, breaks)
    return {k: colors[i] for k, i in zip(values.index, idx)}


def legend_classes(ax, labels, colors, title, x=0.02, y=0.30):
    ax.text(x, y + 0.035, title, transform=ax.transAxes, fontsize=9.5, color=INK2, va='bottom')
    for i, (lab, c) in enumerate(zip(labels, colors)):
        yy = y - i * 0.035
        ax.add_patch(Rectangle((x, yy - 0.012), 0.05, 0.024, transform=ax.transAxes, color=c, ec=SURF, lw=0.5))
        ax.text(x + 0.065, yy, lab, transform=ax.transAxes, fontsize=9, color=INK, va='center')


LISA_LAB = [('HH', 'สูง ล้อมรอบด้วยสูง'), ('LL', 'ต่ำ ล้อมรอบด้วยต่ำ'), ('HL', 'สูง แต่รอบข้างต่ำ'),
            ('LH', 'ต่ำ แต่รอบข้างสูง'), ('ns', 'ไม่มีนัยสำคัญ (p ≥ 0.05)')]

prov = load(f'{G}/province_h_simplified.geojson')
h = pd.read_csv(f'{P}/province_panel_harmonised.csv', dtype={'prov_code_h': str}, encoding='utf-8-sig')
lis = pd.read_csv(f'{Q}/q2_lisa_province.csv', dtype={'prov_code_h': str}, encoding='utf-8-sig')
mor = pd.read_csv(f'{Q}/q2_moran_by_year.csv', encoding='utf-8-sig')

# ---------------------------------------------------------------- M1 choropleths 2568
d = h[h.year_be == 2568].set_index('prov_code_h')
lb, db = [25e3, 35e3, 50e3, 80e3], [40e3, 60e3, 80e3, 120e3]
fig, axs = plt.subplots(1, 2, figsize=(12, 10.4))
for ax, col, br, ramp, ttl, unit in [
        (axs[0], 'loan_pc_dec', lb, BLUE, 'สินเชื่อต่อหัว', 'บาทต่อคน'),
        (axs[1], 'dep_pc_dec', db, ORANGE, 'เงินฝากต่อหัว', 'บาทต่อคน')]:
    cm = classed(d[col], br, ramp)
    draw(ax, prov, lambda k: cm.get(k))
    setup(ax, ttl)
    labs = [f'ต่ำกว่า {br[0]/1e3:.0f},000'] + [f'{a/1e3:.0f},000–{b/1e3:.0f},000' for a, b in zip(br, br[1:])] + \
           [f'{br[-1]/1e3:.0f},000 ขึ้นไป']
    cnt = np.bincount(np.digitize(d[col], br), minlength=5)
    legend_classes(ax, [f'{l}  ({n} พื้นที่)' for l, n in zip(labs, cnt)], ramp, unit, x=0.60, y=0.27)
    ex = d[col].drop('10')
    lo, hi = ex.idxmin(), ex.idxmax()
    hx = centroid(prov[hi][1])[0]
    label(ax, prov, hi, f'{prov[hi][0]["name_th"]} {d.loc[hi, col]:,.0f}', dx=97.4 - hx if hx < 99 else -1.6,
          dy=-1.7 if hx < 99 else -0.2, ha='left' if hx < 99 else 'right')
    lx, ly, lha = (1.6, -0.3, 'left') if centroid(prov[lo][1])[0] < 103 else (-0.4, -2.2, 'right')
    label(ax, prov, lo, f'{prov[lo][0]["name_th"]} {d.loc[lo, col]:,.0f}', dx=lx, dy=ly, ha=lha)
    label(ax, prov, '10', f'กรุงเทพฯ* {d.loc["10", col]:,.0f}', dx=-2.0, dy=0.9, ha='right')
fig.suptitle('เงินฝากต่อหัวต่ำเกือบทั้งภาคอีสาน ส่วนสินเชื่อต่อหัวกระจายเป็นหย่อม จังหวัดศูนย์กลางสูงกว่ารอบข้าง',
             x=0.02, ha='left', fontsize=15, fontweight='bold', y=0.985)
fig.text(0.02, 0.945, 'ยอดคงค้างของธนาคารพาณิชย์ ณ ธ.ค. 2568 ÷ ประชากรตามทะเบียน · '
         'บึงกาฬรวมกับหนองคาย · *กรุงเทพฯ ไม่รวมสำนักงานใหญ่', fontsize=10.5, color=INK2)
fig.text(0.02, 0.012, SRC, fontsize=8, color=MUTED)
fig.subplots_adjust(left=0.01, right=0.99, top=0.895, bottom=0.03, wspace=0.02)
fig.savefig(f'{F}/q2_m1_choropleth_2568.png', dpi=200); plt.close(fig)

# ---------------------------------------------------------------- M2 LISA province, 2x2
panels = [('log_loan_pc', 2548, 'สินเชื่อต่อหัว · 2548'), ('log_loan_pc', 2568, 'สินเชื่อต่อหัว · 2568'),
          ('log_dep_pc', 2568, 'เงินฝากต่อหัว · 2568'), ('ldr_dec', 2568, 'LDR (สินเชื่อ ÷ เงินฝาก) · 2568')]
fig, axs = plt.subplots(2, 2, figsize=(12, 19))
for ax, (v, y, ttl) in zip(axs.ravel(), panels):
    x = lis[(lis.variable == v) & (lis.year_be == y) & (lis.scope == 'all')].set_index('prov_code_h')
    draw(ax, prov, lambda k: LISA_C[x.cluster.get(k, 'ns')])
    cnt = x.cluster.value_counts()
    I = mor[(mor.variable == v) & (mor.year_be == y) & (mor.scope == 'all') & (mor.weights == 'queen')].moran_I.iloc[0]
    setup(ax, ttl)
    ax.text(0.0, 0.985, f"Moran's I = {I:.2f} · สูง-สูง {cnt.get('HH', 0)} · ต่ำ-ต่ำ {cnt.get('LL', 0)} จังหวัด",
            transform=ax.transAxes, fontsize=9.5, color=INK2, va='top')
    for k in x.index[x.cluster.isin(['HL', 'LH'])]:
        label(ax, prov, k, size=8)
for k, dx, dy, ha in [('49', 1.3, 0.4, 'left'), ('96', 1.3, 0.1, 'left')]:
    label(axs[0, 1], prov, k, dx=dx, dy=dy, ha=ha, size=8)
for ax in axs.ravel():
    label(ax, prov, '10', 'กรุงเทพฯ', dx=-1.8, dy=0.6, ha='right', size=8)
handles = [Patch(color=LISA_C[c], label=t) for c, t in LISA_LAB]
fig.legend(handles=handles, loc='upper left', bbox_to_anchor=(0.015, 0.952), ncol=5, frameon=False, fontsize=10,
           handlelength=1.6, columnspacing=1.6)
fig.suptitle('กลุ่มจังหวัดที่สินเชื่อต่อหัวต่ำในอีสานหดเล็กลงมาก แต่กลุ่มเงินฝากต่ำยังเกาะกันเกือบทั้งภาค',
             x=0.02, ha='left', fontsize=15, fontweight='bold', y=0.985)
fig.text(0.02, 0.962, 'Local Moran\'s I (LISA) · เพื่อนบ้าน = จังหวัดที่มีเขตแดนติดกัน · 9,999 permutations · '
         'สินเชื่อและเงินฝากต่อหัวใช้ค่า log · บึงกาฬรวมกับหนองคาย', fontsize=10.5, color=INK2)
fig.text(0.02, 0.008, SRC, fontsize=8, color=MUTED)
fig.subplots_adjust(left=0.01, right=0.99, top=0.905, bottom=0.02, wspace=0.03, hspace=0.07)
fig.savefig(f'{F}/q2_m2_lisa_province.png', dpi=170); plt.close(fig)

# ---------------------------------------------------------------- C4 Moran's I over time
fig, ax = plt.subplots(figsize=(10, 5.6))
for s in ['top', 'right', 'left']:
    ax.spines[s].set_visible(False)
ax.spines['bottom'].set_color(GRID); ax.grid(axis='y', color=GRID, lw=0.8); ax.tick_params(length=0, colors=INK2)
series = [('log_dep_pc', 'เงินฝากต่อหัว', S2), ('ldr_dec', 'LDR', S3), ('log_loan_pc', 'สินเชื่อต่อหัว', S1)]
for v, lab, c in series:
    m = mor[(mor.variable == v) & (mor.scope == 'all') & (mor.weights == 'queen')].sort_values('year_be')
    ax.plot(m.year_be, m.moran_I, color=c, lw=2, marker='o', ms=3.5, zorder=3)
    ax.text(2568.4, m.moran_I.iloc[-1], f'{lab}  {m.moran_I.iloc[-1]:.2f}', color=INK, va='center', fontsize=10)
m = mor[(mor.variable == 'log_loan_pc') & (mor.scope == 'all') & (mor.weights == 'queen')].set_index('year_be')
ax.annotate(f'{m.moran_I[2548]:.2f}', (2548, m.moran_I[2548]), xytext=(0, 9), textcoords='offset points',
            ha='center', fontsize=9, color=INK2)
for x, ha, dx in ((2558, 'right', -0.2), (2561, 'left', 0.2)):
    ax.axvline(x, color=MUTED, lw=1, ls=(0, (3, 3)), zorder=1)
    ax.text(x + dx, 0.705, f'รอยต่อข้อมูล {x}', fontsize=8.5, color=MUTED, va='bottom', ha=ha)
ax.axhline(0, color=INK2, lw=1)
ax.text(2547.6, 0.012, '0 = กระจายแบบสุ่ม ไม่เกาะกลุ่ม', fontsize=8.5, color=INK2)
ax.set_xlim(2547.5, 2572.6); ax.set_ylim(-0.02, 0.74); ax.set_xticks(range(2548, 2569, 2))
ax.set_ylabel("Moran's I (ยิ่งสูง ยิ่งเกาะกลุ่ม)", color=INK2)
ax.set_title('เงินฝากเกาะกลุ่มตามพื้นที่ชัดที่สุด ส่วนสินเชื่อต่อหัวเกาะกลุ่มน้อยลงในช่วง 2548–2556 แล้วทรงตัว',
             loc='left', fontsize=14, fontweight='bold', pad=28)
ax.text(0, 1.02, "Global Moran's I ระหว่าง 76 พื้นที่ (รวมกรุงเทพฯ ไม่รวมสำนักงานใหญ่) · เพื่อนบ้าน = จังหวัดที่มีเขตแดนติดกัน · "
        'ทุกปี p < 0.01', transform=ax.transAxes, fontsize=10.5, color=INK2, va='bottom')
fig.text(0.01, 0.01, SRC, fontsize=8, color=MUTED)
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(f'{F}/q2_c4_moran_trend.png', dpi=200); plt.close(fig)

# ---------------------------------------------------------------- M3 district-level LISA 2568 (hub and spoke)
dist = load(f'{G}/district_adm2_simplified.geojson')
unit = pd.read_csv(f'{G}/district_units_2568.csv', dtype=str, encoding='utf-8-sig').set_index('adm2_pcode').unit_id
dl = pd.read_csv(f'{Q}/q2_lisa_district.csv', dtype={'area_id': str, 'prov_code_h': str}, encoding='utf-8-sig')
x = dl[(dl.year_be == 2568) & (dl.variable == 'log_loan_pc')].set_index('area_id')
col = lambda k: LISA_C[x.cluster.get(unit.get(k), 'ns')] if unit.get(k) in x.index else '#ffffff'
# merge adm2 polygons into analysis units so hidden districts read as one block
ugeo = {}
for k, (pr, rings) in dist.items():
    ugeo.setdefault(unit[k], ({}, []))[1].extend(rings)
ucol = lambda u: LISA_C[x.cluster.get(u, 'ns')] if u in x.index else '#ffffff'

fig = plt.figure(figsize=(12, 11.2))
ax = fig.add_axes([0.0, 0.03, 0.56, 0.86])
draw(ax, ugeo, ucol, edge=SURF, lw=0.25)
outline(ax, prov, color=INK2, lw=0.45)
setup(ax)
ax.add_patch(Rectangle((99.9, 13.35), 1.25, 0.95, fill=False, ec=INK, lw=0.8, zorder=7))
ax2 = fig.add_axes([0.53, 0.40, 0.46, 0.49])
draw(ax2, ugeo, ucol, edge=SURF, lw=0.4)
outline(ax2, prov, color=INK2, lw=0.8)
setup(ax2, xlim=(99.9, 101.15), ylim=(13.35, 14.3))
ax2.set_title('ขยาย: กรุงเทพฯ และปริมณฑล', loc='left', fontsize=10.5, color=INK2, pad=4)
for s in ax2.spines.values():
    s.set_visible(True); s.set_color(INK); s.set_linewidth(0.8)
ax2.axis('on'); ax2.set_xticks([]); ax2.set_yticks([])

cnt = x.groupby('cluster').agg(n=('value', 'size'), pop=('population', 'sum'))
tot = x.population.sum()
lines = []
for c, t in LISA_LAB:
    if c in cnt.index:
        lines.append((c, t, int(cnt.loc[c, 'n']), cnt.loc[c, 'pop'] / tot * 100))
yy = 0.34
fig.text(0.585, yy + 0.02, 'กลุ่ม (จำนวนหน่วย · สัดส่วนประชากร)', fontsize=10, color=INK2)
for i, (c, t, n, s) in enumerate(lines):
    y0 = yy - i * 0.032
    fig.patches.append(Rectangle((0.585, y0 - 0.009), 0.022, 0.018, transform=fig.transFigure, color=LISA_C[c]))
    fig.text(0.615, y0, f'{t}   {n} หน่วย · {s:.0f}%', fontsize=10, color=INK, va='center')
hl = x[x.cluster == 'HL']
n_muang = hl.amphoe_name.fillna('').str.startswith('เมือง').sum()
fig.text(0.585, 0.15, f'สีฟ้าอ่อน {len(hl)} หน่วยคือ "เกาะสินเชื่อ" — {n_muang} หน่วยเป็นอำเภอเมืองของจังหวัด\n'
         'ที่ล้อมรอบด้วยอำเภอซึ่งสินเชื่อต่อหัวต่ำ', fontsize=10, color=INK, linespacing=1.5)
fig.text(0.585, 0.085, 'หน่วยวิเคราะห์: อำเภอที่ ธปท. เปิดเผย (มีธนาคารพาณิชย์มากกว่า 4 แห่ง)\n'
         '+ "อำเภออื่น ๆ" ของแต่ละจังหวัดรวมเป็น 1 หน่วย · พื้นที่สีขาว = ไม่มีสินเชื่อ',
         fontsize=8.8, color=INK2, linespacing=1.5)
fig.suptitle('ระดับอำเภอ: สินเชื่อกระจุกที่อำเภอเมือง ส่วนอำเภอรอบนอกเป็นกลุ่มสินเชื่อต่ำผืนใหญ่',
             x=0.02, ha='left', fontsize=15, fontweight='bold', y=0.975)
fig.text(0.02, 0.935, f"LISA ของสินเชื่อต่อหัว (log) ธ.ค. 2568 · {len(x)} หน่วย · เพื่อนบ้าน = เขตแดนติดกัน · "
         '999 permutations · p < 0.05', fontsize=10.5, color=INK2)
fig.text(0.02, 0.01, SRC, fontsize=8, color=MUTED)
fig.savefig(f'{F}/q2_m3_lisa_district_2568.png', dpi=200); plt.close(fig)
print('saved maps to', F)
