"""
Geometry helpers without GDAL/shapely: read the HDX/OCHA admin shapefiles with pyshp, build Queen contiguity
from shared vertices (with a small snapping tolerance), and draw polygons with matplotlib.

Queen contiguity = two areas are neighbours if their boundaries share at least one point.
"""
import os, sys
import numpy as np
from scipy.spatial import cKDTree

_VENDOR = os.path.join(os.path.dirname(__file__), '..', 'vendor', 'pyshp', 'src')
if os.path.isdir(_VENDOR):
    sys.path.insert(0, _VENDOR)
import shapefile  # pyshp (pure python)


def read_polygons(path, key_field):
    """Return {key: [ring ndarray (n,2), ...]} and {key: record dict}. key_field e.g. 'adm2_pcode'."""
    r = shapefile.Reader(path, encoding='utf-8')
    geoms, recs = {}, {}
    for sr in r.iterShapeRecords():
        s, rec = sr.shape, sr.record.as_dict()
        pts = np.asarray(s.points, float)
        parts = list(s.parts) + [len(pts)]
        rings = [pts[parts[i]:parts[i + 1]] for i in range(len(parts) - 1)]
        k = rec[key_field]
        geoms.setdefault(k, []).extend(rings)
        recs[k] = rec
    return geoms, recs


def snap_rings(rings, grid):
    """Simplify for drawing: snap vertices to a grid and drop repeats. Shared borders snap identically on
    both sides, so no gaps or slivers appear between neighbours. Rings that collapse are dropped."""
    out = []
    for ring in rings:
        q = np.round(ring / grid) * grid
        keep = np.r_[True, np.any(np.diff(q, axis=0) != 0, axis=1)]
        q = q[keep]
        if len(q) >= 4:
            out.append(q)
    return out


def queen_pairs(geoms, tol=2e-5):
    """Neighbour pairs (key_a, key_b) for areas whose boundaries come within `tol` degrees (~2 m)."""
    keys = list(geoms)
    pts, ids = [], []
    for i, k in enumerate(keys):
        p = np.unique(np.round(np.vstack(geoms[k]), 7), axis=0)
        pts.append(p); ids.append(np.full(len(p), i))
    pts, ids = np.vstack(pts), np.concatenate(ids)
    tree = cKDTree(pts)
    pr = tree.query_pairs(tol, output_type='ndarray')
    a, b = ids[pr[:, 0]], ids[pr[:, 1]]
    m = a != b
    ab = np.unique(np.sort(np.c_[a[m], b[m]], axis=1), axis=0)
    return {(keys[i], keys[j]) for i, j in ab}, (pts, ids, keys)


def nearest_other(key, geoms, cache):
    """Area whose boundary is closest to `key` (used to give islands one neighbour)."""
    pts, ids, keys = cache
    i = keys.index(key)
    mine, other = pts[ids == i], ids != i
    tree = cKDTree(pts[other])
    d, j = tree.query(mine[:: max(1, len(mine) // 2000)])
    return keys[ids[other][j[np.argmin(d)]]], float(d.min())


def neighbours_from_pairs(pairs, keys):
    nb = {k: set() for k in keys}
    for a, b in pairs:
        if a in nb and b in nb:
            nb[a].add(b); nb[b].add(a)
    return nb


def aggregate_neighbours(nb_fine, member_of):
    """Contiguity between groups of fine areas: groups are neighbours if any members are."""
    groups = set(member_of.values())
    nb = {g: set() for g in groups}
    for a, ns in nb_fine.items():
        ga = member_of.get(a)
        if ga is None:
            continue
        for b in ns:
            gb = member_of.get(b)
            if gb is not None and gb != ga:
                nb[ga].add(gb)
    return nb


def knn_neighbours(xy, keys, k):
    """k nearest neighbours by centroid (great-circle approximated with cos(lat) scaling)."""
    xy = np.asarray(xy, float).copy()
    xy[:, 0] *= np.cos(np.deg2rad(xy[:, 1].mean()))
    _, j = cKDTree(xy).query(xy, k + 1)
    return {keys[i]: {keys[t] for t in j[i, 1:]} for i in range(len(keys))}


def ring_area_centroid(rings):
    """Area-weighted centroid of a multipolygon given as outer rings (holes are rare here and ignored)."""
    A = cx = cy = 0.0
    for r in rings:
        x, y = r[:, 0], r[:, 1]
        c = x[:-1] * y[1:] - x[1:] * y[:-1]
        a = c.sum() / 2
        if a == 0:
            continue
        A += a; cx += ((x[:-1] + x[1:]) * c).sum() / 6; cy += ((y[:-1] + y[1:]) * c).sum() / 6
    return (cx / A, cy / A) if A else tuple(np.vstack(rings).mean(0))
