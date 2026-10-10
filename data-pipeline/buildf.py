"""Женская модель: Human Reference Atlas, United Female v1.5 (CC BY 4.0) → формат атласа vq1 (две детализации)."""
import json, numpy as np, re, gzip, base64, ctypes, sys, os, collections
sys.path.insert(0, '/tmp/claude-0/-home-claude/cbf11d43-6187-53a1-be7c-766797224c02/scratchpad')
from rename import ru_name, tr, norm
SRC = '/root/female/'; OUT = '/home/claude/atlas-site/models/'
lib = ctypes.CDLL('/root/dl/libmeshopt.so')
for f in ['meshopt_optimizeVertexFetch', 'meshopt_simplify', 'meshopt_generateVertexRemap']: getattr(lib, f).restype = ctypes.c_size_t
lib.meshopt_optimizeVertexCache.restype = None
P = lambda a: a.ctypes.data_as(ctypes.c_void_p)
A = json.load(open(SRC + 'atlas-female.json'))
bins = [open(SRC + c['url'].split('/')[-1], 'rb').read() for c in A['chunks']]

def fprep(n):
    n = n.strip()
    m = re.match(r'^(.*?)\s*\((left|right)\)$', n, re.I)
    if m: n = ('Left ' if m.group(2).lower() == 'left' else 'Right ') + m.group(1)
    n = re.sub(r'^(?:L|l) (lung)', r'Left \1', n); n = re.sub(r'^(?:R|r) (lung)', r'Right \1', n)
    m = re.match(r'^(.*?)\s+([LlRr])1?$', n)
    if m and len(m.group(1)) > 2: n = ('Left ' if m.group(2) in 'Ll' else 'Right ') + m.group(1)
    m = re.match(r'^(allen brain hemisphere) ([lr])$', n, re.I)
    if m: n = ('Left ' if m.group(2).lower() == 'l' else 'Right ') + m.group(1)
    return n
SKIP = re.compile(r'enthesis|perichondular surface|distal-most point', re.I)
def system_of(p):
    s = p['system']; n = p['name'].lower()
    if s == 'integumentary': return 'skin' if 'skin' in n else 'mammary'
    if s == 'pregnancy': return 'pregnancy'
    return s

def geo(p):
    b = bins[p['chunk']]
    v = np.frombuffer(b, np.float32, p['vertexCount'] * 3, p['positions']).reshape(-1, 3).copy()
    i = np.frombuffer(b, np.uint32, p['indexCount'], p['indices']).copy()
    return v, i
def simplify(v, i, ratio, err=0.002):
    target = max(720, int(len(i) * ratio) // 3 * 3)
    if target >= len(i): return v, i
    dst = np.zeros(len(i), np.uint32); e = ctypes.c_float(0)
    n = lib.meshopt_simplify(P(dst), P(np.ascontiguousarray(i)), ctypes.c_size_t(len(i)), P(np.ascontiguousarray(v)), ctypes.c_size_t(len(v)), ctypes.c_size_t(12), ctypes.c_size_t(target), ctypes.c_float(err), ctypes.c_uint(0), ctypes.byref(e))
    return v, dst[:n].copy()
def varint(a):
    a = np.asarray(a, np.uint64)
    if len(a) == 0: return b''
    groups = np.stack([(a >> np.uint64(7 * k)) & np.uint64(0x7f) for k in range(5)], 1).astype(np.uint8)
    nb = np.ones(len(a), np.int64)
    for k in range(1, 5): nb += (a >= np.uint64(1 << (7 * k))).astype(np.int64)
    cont = (np.arange(5)[None, :] < (nb[:, None] - 1)).astype(np.uint8) << 7
    keep = np.arange(5)[None, :] < nb[:, None]
    return (groups | cont)[keep].tobytes()
def encode(v, i):
    i = np.ascontiguousarray(i, np.uint32)
    o = np.zeros_like(i); lib.meshopt_optimizeVertexCache(P(o), P(i), ctypes.c_size_t(len(i)), ctypes.c_size_t(len(v))); i = o
    vv = np.ascontiguousarray(v.copy()); ii = np.ascontiguousarray(i.copy())
    n = lib.meshopt_optimizeVertexFetch(P(vv), P(ii), ctypes.c_size_t(len(ii)), P(np.ascontiguousarray(v)), ctypes.c_size_t(len(v)), ctypes.c_size_t(12))
    v = vv[:n]; i = ii.astype(np.int64)
    lo = v.min(0); ext = float((v.max(0) - lo).max()) or 1e-6
    q = np.clip(np.round((v - lo) / ext * 65535), 0, 65535).astype(np.int64)
    d = np.diff(q, axis=0, prepend=np.zeros((1, 3), np.int64)); z = (d << 1) ^ (d >> 63)
    ev = b''.join(varint(z[:, c]) for c in range(3))
    hw = np.concatenate([[0], np.maximum.accumulate(i)[:-1] + 1]); di = hw - i
    assert (di >= 0).all()
    dq = q.astype(np.float64) / 65535 * ext + lo
    return ev, varint(di), len(v), len(i), [float(x) for x in lo] + [ext], dq

def ru(en):
    try: return ru_name(en)
    except KeyError:
        k = norm(en.lower()).replace(' ()', '').strip()
        base = tr.get(k)
        if base is None: return None
        base = base[0].upper() + base[1:]
        if re.search(r'\bleft\b', en, re.I): base += ' (лев.)'
        elif re.search(r'\bright\b', en, re.I): base += ' (прав.)'
        return base

parts = []; missing = set()
for p in A['parts']:
    if SKIP.search(p['name']): continue
    en = fprep(p['name']); name = ru(en)
    if name is None: missing.add(en); continue
    v, i = geo(p)
    parts.append(dict(rec=dict(id='F-' + p['id'], name=name, en=en, conceptId=p['conceptId'], system=system_of(p)), v=v, i=i))
print('parts', len(parts), 'missing names', sorted(missing)[:20])
ids = {x['rec']['id'] for x in parts}; byold = {x['rec']['id'][2:]: x['rec']['id'] for x in parts}
concepts = []
for c in A['concepts']:
    el = [byold[e] for e in c['elements'] if e in byold]
    if not el: continue
    en = fprep(c['name']); name = ru(en)
    if name is None: continue
    concepts.append(dict(id=c['id'], name=re.sub(r' \((лев|прав)\.\)$', '', name) if not re.search(r'\b(left|right)\b', en, re.I) else name, en=en, elements=el))
cid = {c['id'] for c in concepts}
for x in parts:
    r = x['rec']
    if r['conceptId'] not in cid:
        concepts.append(dict(id=r['conceptId'] + '#' + r['id'], name=r['name'], en=r['en'], elements=[r['id']])); r['conceptId'] = concepts[-1]['id']; cid.add(r['conceptId'])
    elif r['id'] not in next(c for c in concepts if c['id'] == r['conceptId'])['elements']:
        next(c for c in concepts if c['id'] == r['conceptId'])['elements'].append(r['id'])
# дополнения: скелет и мышцы, подогнанные из BodyParts3D; беременность внутри тела
import pickle
X=pickle.load(open('/root/rg/femextra.pkl','rb'))
sys.path.insert(0,'/root/rg');import os;_cwd=os.getcwd();os.chdir('/root/rg');from preg2 import deform,place;os.chdir(_cwd)
byid={x['rec']['id']:x for x in parts}
for pid,r in X['renames'].items():
    rec=byid[pid]['rec'];old=rec['conceptId']
    for c in concepts:
        if c['id']==old and pid in c['elements']:c['elements'].remove(pid)
    rec.update(r)
concepts=[c for c in concepts if c['elements']]
for pid in X['normal_only']:byid[pid]['rec']['when']='normal'
for pid in X['preg']:byid[pid]['v']=place(byid[pid]['v'].astype(np.float64)).astype(np.float32)
for e in X['extra']:parts.append(dict(rec=dict(e['rec']),v=np.ascontiguousarray(e['v'],np.float32),i=np.ascontiguousarray(e['i'],np.uint32)));byid[e['rec']['id']]=parts[-1]
cmap={c['id']:c for c in concepts}
for c in X['concepts']:
    if c['id'] in cmap:cmap[c['id']]['elements']+= [e for e in c['elements'] if e not in cmap[c['id']]['elements']]
    else:concepts.append(dict(c));cmap[c['id']]=concepts[-1]
for pid,v in X['variant'].items():
    base=byid[pid]
    if v is None:v=deform(base['v'].astype(np.float64))[0].astype(np.float32)
    base['rec']['when']='normal';r=dict(base['rec']);r['id']=pid+'~p';r['when']='pregnant'
    parts.append(dict(rec=r,v=np.ascontiguousarray(v,np.float32),i=base['i']));cmap[r['conceptId']]['elements'].append(r['id'])
# описания
pats = [(re.compile(l.split('\t', 1)[0]), l.rstrip('\n').split('\t', 1)[1]) for l in open('/root/dl/desc.tsv', encoding='utf8') if '\t' in l]
nz = lambda x: norm((x or '').lower()).replace(' ()', '').strip()
for c in concepts:
    if c.get('desc'):continue
    n = nz(c['en'])
    for r, d in pats:
        if r.fullmatch(n): c['desc'] = d; break

def write(level, ratio):
    pfx = 'geo-f-lo-' if level == 'lo' else 'geo-f-'
    for f in os.listdir(OUT):
        if f.startswith(pfx) and (level == 'lo' or not f.startswith('geo-f-lo-')): os.remove(OUT + f)
    chunks = []; buf = bytearray(); ci = 0; tri = 0; out = {}
    def flush():
        nonlocal buf, ci
        if not buf: return
        gz = gzip.compress(bytes(buf), 9); name = f'models/{pfx}{ci}.bin.gz.txt'
        open(OUT + f'{pfx}{ci}.bin.gz.txt', 'w').write(base64.b64encode(gz).decode())
        chunks.append(dict(url=name, bytes=len(buf), gzip=name, gzipBytes=len(gz))); buf = bytearray(); ci += 1
    for x in sorted(parts, key=lambda x: (x['rec']['system'], x['rec']['id'])):
        v, i = (x['v'], x['i']) if ratio >= 1 else simplify(x['v'], x['i'], ratio)
        ev, ei, nv, ni, q, dq = encode(v, i)
        ov = len(buf); buf += ev; oi = len(buf); buf += ei
        out[x['rec']['id']] = dict(chunk=ci, ev=ov, evb=len(ev), ei=oi, eib=len(ei), vertexCount=nv, indexCount=ni, q=q,
                                   bounds=[[round(float(t), 6) for t in dq.min(0)], [round(float(t), 6) for t in dq.max(0)]])
        tri += ni // 3
        if len(buf) > 2_400_000: flush()
    flush(); return chunks, out, tri
hc, ho, htri = write('hi', 1.0)
lc, lo, ltri = write('lo', 0.45)
out_parts = []
for x in sorted(parts, key=lambda x: (x['rec']['system'], x['rec']['id'])):
    r = dict(x['rec']); h = ho[r['id']]; l = lo[r['id']]; r.update(h)
    r['lo'] = [l['chunk'], l['ev'], l['evb'], l['ei'], l['eib'], l['vertexCount'], l['indexCount']] + l['q']
    out_parts.append(r)
atlas = dict(version='Human Reference Atlas, United Female v1.5', codec='vq1', sex='female', parts=out_parts, chunks=hc, triangles=htri,
             lowChunks=lc, lowTriangles=ltri, concepts=concepts)
json.dump(atlas, open(OUT + 'atlas-female.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print('female parts', len(out_parts), 'concepts', len(concepts), 'tri hi', htri, 'lo', ltri,
      'hi MB', round(sum(c['gzipBytes'] for c in hc) * 4 / 3 / 1e6, 1), 'lo MB', round(sum(c['gzipBytes'] for c in lc) * 4 / 3 / 1e6, 1))
print(collections.Counter(p['system'] for p in out_parts))
C = {c['id']: c for c in concepts}; print('with desc', sum(1 for p in out_parts if C[p['conceptId']].get('desc')))
