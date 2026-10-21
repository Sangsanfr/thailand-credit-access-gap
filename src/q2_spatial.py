"""
Q2: Is low credit access spatially clustered?

Units
  province : 76 harmonised provinces (Bueng Kan merged into Nong Khai) + Bangkok excl. head office
  district : districts BOT shows (more than 4 commercial banks) + one "rest of province" unit per province
             made of the districts BOT hides (geometry = union of the hidden districts)
Weights
  queen    : areas that share at least one boundary point (from D7 tha_admin2, topology is exact);
             islands with no land neighbour get their nearest area (Phuket at province level; 6 island districts)
  knn6     : 6 nearest centroids (robustness)
Stats
  Global Moran's I (row-standardised W, 9,999 permutations) and local Moran's I (LISA, conditional permutation,
  9,999 draws). LISA classes at p < 0.05; a Benjamini-Hochberg FDR flag is stored too.

Usage: python q2_spatial.py <shp_dir> <panels_dir> <out_dir> <geo_out_dir>
"""
import sys, os, json, pickle
import numpy as np, pandas as pd
from scipy import sparse
sys.path.insert(0, os.path.dirname(__file__))
from geo_utils import (read_polygons, queen_pairs, neighbours_from_pairs, aggregate_neighbours, knn_neighbours,
                       ring_area_centroid, snap_rings)
from scipy.spatial import cKDTree

SHP, P, OUT, GEO = sys.argv[1:5]
for d in (OUT, GEO):
    os.makedirs(d, exist_ok=True)
PERM, SEED = 9999, 20251231
CACHE = os.path.join(GEO, '_adm2_cache.pkl')

# ------------------------------------------------------------------ geometry + fine-level contiguity
if os.path.exists(CACHE):
    g2, r2, pairs, cache = pickle.load(open(CACHE, 'rb'))
else:
    g2, r2 = read_polygons(os.path.join(SHP, 'tha_admin2'), 'adm2_pcode')
    pairs, cache = queen_pairs(g2, tol=2e-5)
    pickle.dump((g2, r2, pairs, cache), open(CACHE, 'wb'))
nb2 = neighbours_from_pairs(pairs, list(g2))
pd.DataFrame(sorted(pairs), columns=['adm2_pcode_a', 'adm2_pcode_b']).to_csv(
    f'{GEO}/queen_pairs_adm2.csv', index=False)

dimd = pd.read_csv(f'{P}/dim_district.csv', dtype=str, encoding='utf-8-sig')
dimp = pd.read_csv(f'{P}/dim_province.csv', dtype=str, encoding='utf-8-sig')
code_of = dict(zip(dimd.adm2_pcode, dimd.amphoe_code))
provh_of = dict(zip(dimd.adm2_pcode, dimd.prov_code_h))
pts, ids, keys = cache
pt_key = np.array(keys)[ids]                       # adm2 pcode of every boundary vertex


def fix_islands(nb, member_of):
    """Give every group without a neighbour the group whose boundary is closest."""
    added = []
    grp = np.array([member_of.get(k) for k in pt_key], dtype=object)
    for g, ns in nb.items():
        if ns:
            continue
        mine, other = grp == g, (grp != g) & (grp != None)  # noqa: E711
        tree = cKDTree(pts[other])
        sub = pts[mine][:: max(1, mine.sum() // 3000)]
        d, j = tree.query(sub)
        h = grp[other][j[np.argmin(d)]]
        nb[g].add(h); nb[h].add(g); added.append((g, h, round(float(d.min()) * 111, 1)))
    return added


def w_matrix(nb, order):
    idx = {k: i for i, k in enumerate(order)}
    r, c = [], []
    for k in order:
        for j in nb[k]:
            if j in idx:
                r.append(idx[k]); c.append(idx[j])
    W = sparse.csr_matrix((np.ones(len(r)), (r, c)), shape=(len(order), len(order)))
    deg = np.asarray(W.sum(1)).ravel()
    if (deg == 0).any():
        raise ValueError(f'units without neighbours: {[order[i] for i in np.where(deg == 0)[0]]}')
    return sparse.diags(1 / deg) @ W, deg


# ------------------------------------------------------------------ Moran's I
def moran(x, W, rng, perms=PERM):
    z = x - x.mean(); n = len(z)
    I = n / W.sum() * (z @ (W @ z)) / (z @ z)
    sim = np.empty(perms)
    for p in range(perms):
        zp = rng.permutation(z)
        sim[p] = n / W.sum() * (zp @ (W @ zp)) / (zp @ zp)
    larger = (sim >= I).sum()
    p_sim = (min(larger, perms - larger) + 1) / (perms + 1)
    return I, -1 / (n - 1), (I - sim.mean()) / sim.std(), p_sim


def lisa(x, W, rng, perms=PERM):
    """Local Moran I_i = z_i * sum_j w_ij z_j / m2, conditional permutation pseudo p-values (folded)."""
    z = x - x.mean(); n = len(z); m2 = (z @ z) / n
    lag = W @ z
    Ii = z * lag / m2
    Wd = W.tocsr(); p = np.empty(n)
    for i in range(n):
        row = Wd.getrow(i); w = row.data; k = len(w)
        others = np.delete(z, i)
        draw = np.argsort(rng.random((perms, n - 1)), axis=1)[:, :k]
        sim = z[i] * (others[draw] @ w) / m2
        larger = (sim >= Ii[i]).sum()
        p[i] = (min(larger, perms - larger) + 1) / (perms + 1)
    q = np.select([(z > 0) & (lag > 0), (z < 0) & (lag < 0), (z < 0) & (lag > 0), (z > 0) & (lag < 0)],
                  ['HH', 'LL', 'LH', 'HL'], 'ns')
    return Ii, p, q, lag


def bh_fdr(p, alpha=0.05):
    o = np.argsort(p); n = len(p)
    ok = p[o] <= alpha * np.arange(1, n + 1) / n
    k = np.where(ok)[0].max() + 1 if ok.any() else 0
    sig = np.zeros(n, bool); sig[o[:k]] = True
    return sig


# ------------------------------------------------------------------ province units (harmonised)
member_prov = {k: provh_of[k] for k in g2}
nb_prov = aggregate_neighbours(nb2, member_prov)
isl_prov = fix_islands(nb_prov, member_prov)
cent = {}
for g in set(member_prov.values()):
    rings = [r for k in g2 if member_prov[k] == g for r in g2[k]]
    cent[g] = ring_area_centroid(rings)
prov_order = sorted(nb_prov)
knn_prov = knn_neighbours([cent[g] for g in prov_order], prov_order, 6)
for k, v in list(knn_prov.items()):                # symmetrise
    for j in v:
        knn_prov[j].add(k)
pd.DataFrame([(a, b) for a in prov_order for b in sorted(nb_prov[a]) if a < b], columns=['prov_code_h_a', 'prov_code_h_b']) \
    .to_csv(f'{GEO}/queen_pairs_province_h.csv', index=False)

h = pd.read_csv(f'{P}/province_panel_harmonised.csv', dtype={'prov_code_h': str}, encoding='utf-8-sig')
assert set(h.prov_code_h) == set(prov_order), set(h.prov_code_h) ^ set(prov_order)
h['log_loan_pc'] = np.log(h.loan_pc_dec); h['log_dep_pc'] = np.log(h.dep_pc_dec)
h['log_loan_pc_avg12'] = np.log(h.loan_pc_avg12)
VARS = ['log_loan_pc', 'log_dep_pc', 'ldr_dec', 'offices_per_100k', 'log_loan_pc_avg12']

rng = np.random.default_rng(SEED)
mrows, lrows = [], []
for scope in ['all', 'ex_bkk']:
    order = [g for g in prov_order if scope == 'all' or g != '10']
    Wq, degq = w_matrix(nb_prov, order); Wk, _ = w_matrix(knn_prov, order)
    for y, d in h.groupby('year_be'):
        d = d.set_index('prov_code_h').loc[order]
        for v in VARS:
            x = d[v].to_numpy(float)
            for wname, W in (('queen', Wq), ('knn6', Wk)):
                I, EI, z, ps = moran(x, W, rng, perms=999 if wname == 'knn6' else PERM)
                mrows.append(dict(year_be=y, variable=v, scope=scope, weights=wname, n=len(x), moran_I=I,
                                  expected_I=EI, z_sim=z, p_sim=ps))
            if v in ('log_loan_pc', 'log_dep_pc', 'ldr_dec'):
                Ii, p, q, lag = lisa(x, Wq, rng)
                fdr = bh_fdr(p)
                for j, g in enumerate(order):
                    lrows.append(dict(year_be=y, variable=v, scope=scope, prov_code_h=g, value=x[j],
                                      spatial_lag_z=lag[j], local_I=Ii[j], p_sim=p[j], quadrant=q[j],
                                      cluster=q[j] if p[j] < 0.05 else 'ns', sig_fdr=bool(fdr[j]),
                                      n_neighbours=int(degq[j])))
    print('province scope done:', scope)
mor = pd.DataFrame(mrows)
mor.to_csv(f'{OUT}/q2_moran_by_year.csv', index=False, encoding='utf-8-sig')
names = h.drop_duplicates('prov_code_h').set_index('prov_code_h')[['prov_name_th', 'region_bot']]
lis = pd.DataFrame(lrows).join(names, on='prov_code_h')
lis.to_csv(f'{OUT}/q2_lisa_province.csv', index=False, encoding='utf-8-sig')

# ------------------------------------------------------------------ district units (visible + rest of province)
dp = pd.read_csv(f'{P}/district_panel.csv', dtype={'area_id': str, 'amphoe_code': str, 'prov_code_h': str},
                 encoding='utf-8-sig')
drows, dmor = [], []
pc_of_code = {v: k for k, v in code_of.items()}
for y in (2558, 2568):
    d = dp[dp.year_be == y].copy()
    vis = set(d.loc[d.area_type == 'district', 'area_id'])
    member = {k: (code_of[k] if code_of[k] in vis else f'{provh_of[k]}_REST') for k in g2}
    assert set(member.values()) == set(d.area_id), set(member.values()) ^ set(d.area_id)
    nb = aggregate_neighbours(nb2, member)
    isl = fix_islands(nb, member)
    d = d[d.loan_pc_dec > 0].copy()                # log needs > 0; drop units with no loans booked
    order = sorted(d.area_id)
    W, deg = w_matrix({k: nb[k] & set(order) for k in order}, order)
    d = d.set_index('area_id').loc[order]
    for v, x in (('log_loan_pc', np.log(d.loan_pc_dec)), ('ldr_dec', d.ldr_dec), ('log_dep_pc', np.log(d.dep_pc_dec))):
        x = x.to_numpy(float)
        I, EI, z, ps = moran(x, W, rng, perms=999)
        dmor.append(dict(year_be=y, variable=v, units='visible+rest', weights='queen', n=len(x), moran_I=I,
                         expected_I=EI, z_sim=z, p_sim=ps))
        # robustness: visible districts only (rest units are large aggregates), 6 nearest centroids
        vmask = (d.area_type == 'district').to_numpy()
        vk = [a for a in order if a in vis]
        cen = [ring_area_centroid([r for k in g2 if member[k] == a for r in g2[k]]) for a in vk]
        kn = knn_neighbours(cen, vk, 6)
        for k_, s_ in list(kn.items()):
            for j_ in s_:
                kn[j_].add(k_)
        Wv, _ = w_matrix(kn, vk)
        I, EI, z, ps = moran(x[vmask], Wv, rng, perms=999)
        dmor.append(dict(year_be=y, variable=v, units='visible_only', weights='knn6', n=int(vmask.sum()),
                         moran_I=I, expected_I=EI, z_sim=z, p_sim=ps))
        if v == 'log_loan_pc' or y == 2568:
            Ii, p, q, lag = lisa(x, W, rng, perms=999)
            fdr = bh_fdr(p)
            for j, a in enumerate(order):
                drows.append(dict(year_be=y, variable=v, area_id=a, area_type=d.area_type.iloc[j],
                                  prov_code_h=d.prov_code_h.iloc[j], amphoe_name=d.amphoe_name.iloc[j],
                                  population=d.population.iloc[j], value=x[j], local_I=Ii[j], p_sim=p[j],
                                  quadrant=q[j], cluster=q[j] if p[j] < 0.05 else 'ns', sig_fdr=bool(fdr[j]),
                                  n_neighbours=int(deg[j])))
    pd.Series(member, name='unit_id').rename_axis('adm2_pcode').to_csv(f'{GEO}/district_units_{y}.csv',
                                                                       encoding='utf-8-sig')
    print('district', y, 'units', len(order), 'islands linked', isl)
pd.DataFrame(dmor).to_csv(f'{OUT}/q2_moran_district.csv', index=False, encoding='utf-8-sig')
dl = pd.DataFrame(drows).join(names[['prov_name_th', 'region_bot']], on='prov_code_h')
dl.to_csv(f'{OUT}/q2_lisa_district.csv', index=False, encoding='utf-8-sig')

# ------------------------------------------------------------------ simplified GeoJSON for maps / dashboard
def to_geojson(groups, props, grid, path):
    feats = []
    for g, rings in groups.items():
        rs = snap_rings(rings, grid)
        if not rs:
            continue
        feats.append({'type': 'Feature', 'properties': {'id': g, **props.get(g, {})},
                      'geometry': {'type': 'MultiPolygon',
                                   'coordinates': [[np.round(r, 4).tolist()] for r in rs]}})
    json.dump({'type': 'FeatureCollection', 'features': feats}, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
    return len(feats)


g1, r1 = read_polygons(os.path.join(SHP, 'tha_admin1'), 'adm1_pcode')
prov_rings = {}
for k, rings in g1.items():
    prov_rings.setdefault('43' if k == 'TH38' else k[2:], []).extend(rings)
pprops = {g: {'name_th': names.prov_name_th.get(g), 'region_bot': names.region_bot.get(g)} for g in prov_rings}
print('province geojson features', to_geojson(prov_rings, pprops, 0.004, f'{GEO}/province_h_simplified.geojson'))
dprops = {k: {'amphoe_code': code_of[k], 'prov_code_h': provh_of[k], 'name_th': r2[k]['adm2_name1']} for k in g2}
print('district geojson features',
      to_geojson({k: g2[k] for k in g2}, dprops, 0.002, f'{GEO}/district_adm2_simplified.geojson'))

# ------------------------------------------------------------------ console summary
print('province islands linked:', isl_prov)
print('BKK queen neighbours:', sorted(names.prov_name_th.get(g) for g in nb_prov['10']))
print('mean queen neighbours (province):', np.mean([len(nb_prov[g]) for g in prov_order]).round(2))
s = mor[(mor.weights == 'queen') & (mor.year_be.isin([2548, 2553, 2558, 2563, 2568]))] \
    .pivot_table(index=['variable', 'scope'], columns='year_be', values='moran_I')
print(s.round(3).to_string())
print(pd.DataFrame(dmor).round(3).to_string(index=False))
