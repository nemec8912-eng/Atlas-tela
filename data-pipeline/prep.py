"""Разбор OBJ BodyParts3D 4.3, сварка вершин, упрощение meshoptimizer, кэш в npz."""
import ctypes, numpy as np, json, os, sys, re
from multiprocessing import Pool
lib = ctypes.CDLL('/root/dl/libmeshopt.so')
lib.meshopt_generateVertexRemap.restype = ctypes.c_size_t
lib.meshopt_simplify.restype = ctypes.c_size_t
lib.meshopt_optimizeVertexFetch.restype = ctypes.c_size_t
RATIO = float(os.environ.get('RATIO', '0.5')); ERR = float(os.environ.get('ERR', '0.001')); MINTRI = 240
OUT = os.environ.get('CACHE', '/root/dl/cache/')
os.makedirs(OUT, exist_ok=True)
P = lambda a: a.ctypes.data_as(ctypes.c_void_p)

def parse(path):
    vs = []; fs = []
    with open(path) as f:
        for line in f:
            if line.startswith('v '):
                x, y, z = map(float, line.split()[1:4]); vs.append((x * .001, z * .001 + .0781112, -y * .001 - .1))
            elif line.startswith('f '):
                face = [int(s.split('/')[0]) - 1 for s in line.split()[1:]]
                for j in range(1, len(face) - 1): fs.append((face[0], face[j], face[j + 1]))
    return np.array(vs, np.float32), np.array(fs, np.uint32).reshape(-1)

def weld(v, idx):
    remap = np.zeros(len(v), np.uint32)
    n = lib.meshopt_generateVertexRemap(P(remap), P(idx), ctypes.c_size_t(len(idx)), P(v), ctypes.c_size_t(len(v)), ctypes.c_size_t(12))
    nv = np.zeros((n, 3), np.float32); nv[remap] = v
    return nv, remap[idx]

def normals(v, idx):
    t = idx.reshape(-1, 3); a, b, c = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
    fn = np.cross(b - a, c - a)
    n = np.zeros_like(v)
    for k in range(3): np.add.at(n, t[:, k], fn)
    l = np.linalg.norm(n, axis=1, keepdims=True); l[l == 0] = 1
    return n / l

def work(item):
    fj, path = item
    out = OUT + fj + '.npz'
    if os.path.exists(out): return fj, None
    v, idx = parse(path)
    if len(idx) == 0: return fj, 'empty'
    v, idx = weld(v, idx)
    # убрать вырожденные треугольники
    t = idx.reshape(-1, 3); ok = (t[:, 0] != t[:, 1]) & (t[:, 1] != t[:, 2]) & (t[:, 0] != t[:, 2]); idx = np.ascontiguousarray(t[ok].reshape(-1))
    full = len(idx) // 3
    target = max(MINTRI * 3, int(len(idx) * RATIO) // 3 * 3)
    if target < len(idx):
        dst = np.zeros(len(idx), np.uint32); err = ctypes.c_float(0)
        n = lib.meshopt_simplify(P(dst), P(idx), ctypes.c_size_t(len(idx)), P(v), ctypes.c_size_t(len(v)), ctypes.c_size_t(12),
                                 ctypes.c_size_t(target), ctypes.c_float(ERR), ctypes.c_uint(0), ctypes.byref(err))
        idx = dst[:n].copy()
    # компактные вершины
    vv = np.ascontiguousarray(v.copy()); ii = np.ascontiguousarray(idx.copy())
    n = lib.meshopt_optimizeVertexFetch(P(vv), P(ii), ctypes.c_size_t(len(ii)), P(v), ctypes.c_size_t(len(v)), ctypes.c_size_t(12))
    vv = vv[:n]
    nn = normals(vv, ii)
    np.savez(out, v=vv, n=nn.astype(np.float32), i=ii, full=np.array([full]))
    return fj, None

if __name__ == '__main__':
    M = json.load(open('/root/dl/meshes.json'))
    items = [(m['fj'] + '_' + m['bp'], '/root/dl/obj/' + m['file'].split('/')[-1]) for m in M]
    with Pool(2) as pool:
        errs = [r for r in pool.imap_unordered(work, items, chunksize=8) if r[1]]
    print('done', len(items), 'errors', errs[:10])
