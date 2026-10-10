"""Сборка атласа v2: геометрия BodyParts3D 4.3 высокой детализации + сжатие meshoptimizer."""
import json, numpy as np, re, gzip, base64, ctypes, sys, os, collections
sys.path.insert(0, '/tmp/claude-0/-home-claude/cbf11d43-6187-53a1-be7c-766797224c02/scratchpad')
from rename import ru_name
SRC = '/root/atlas-site-v4-backup/models/'      # текущий опубликованный атлас (имена, системы, понятия, схемы нервов)
OUT = '/home/claude/atlas-site/models/'
lib = ctypes.CDLL('/root/dl/libmeshopt.so')
for f in ['meshopt_encodeVertexBufferBound', 'meshopt_encodeVertexBuffer', 'meshopt_encodeIndexBufferBound', 'meshopt_encodeIndexBuffer', 'meshopt_optimizeVertexFetch']:
    getattr(lib, f).restype = ctypes.c_size_t
lib.meshopt_optimizeVertexCache.restype = None
P = lambda a: a.ctypes.data_as(ctypes.c_void_p)

A = json.load(open(SRC + 'atlas.json'))
mj = json.load(open('/root/dl/match.json'))
M = {m['fj'] + '_' + m['bp']: m for m in json.load(open('/root/dl/meshes.json'))}

# ---------- старая геометрия ----------
_old = {}
def old_chunk(i):
    if i not in _old:
        c = A['chunks'][i]; _old[i] = gzip.decompress(base64.b64decode(open(SRC + c['gzip'].split('/')[-1]).read()))
    return _old[i]
def old_geo(p):
    b = old_chunk(p['chunk'])
    v = np.frombuffer(b, np.float32, p['vertexCount'] * 3, p['positions']).reshape(-1, 3).copy()
    i = np.frombuffer(b, np.uint32, p['indexCount'], p['indices']).copy()
    return v, i
def new_geo(key):
    d = np.load(f'/root/dl/cache/{key}.npz'); return d['v'].astype(np.float32), d['i'].astype(np.uint32)

# ---------- какие схемы нервов заменяются настоящими моделями ----------
SUPERSEDED = {'spinal_cord', 'cauda_equina', 'cervical_plexus', 'brachial_plexus', 'median', 'median_digital', 'ulnar', 'radial',
              'musculocutaneous', 'axillary', 'vagus', 'recurrent_laryngeal', 'phrenic', 'facial', 'facial_branches',
              'trigeminal', 'trigeminal_v2', 'trigeminal_v3', 'hypoglossal', 'accessory'}
REAL_ROOTS = {'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'T1', 'T2'}
def ru_key(p): return p['conceptId'][3:] if p['conceptId'].startswith('RU-') else None
def drop_ru(p):
    k = ru_key(p)
    if k in SUPERSEDED: return True
    if p['conceptId'] == 'FMA7647' and p['id'].startswith('RU-'): return True  # схема спинного мозга
    m = re.search(r'Spinal nerve (\w+)$', p['en'])
    if m and m.group(1) in REAL_ROOTS: return True
    m = re.search(r'Intercostal nerve (T\d+)$', p['en'])
    if m and m.group(1) in ('T1', 'T2'): return True
    return False

parts = []  # (record, v, i)
dropped = set()
for p in A['parts']:
    rec = {k: p[k] for k in ('id', 'name', 'en', 'conceptId', 'system') if k in p}
    if p.get('schematic'): rec['schematic'] = True
    if p['id'].startswith('RU-'):
        if drop_ru(p): dropped.add(p['id']); continue
        v, i = old_geo(p)
    elif p['id'] in mj['match']:
        v, i = new_geo(mj['match'][p['id']])
    else:
        v, i = old_geo(p)
    parts.append([rec, v, i])
print('old parts kept', len(parts), 'schematic dropped', len(dropped))

# ---------- новые детали из 4.3 ----------
fma2obj = collections.defaultdict(set)
for line in open('/root/dl/body_parts_3d_api/metadata/FMA2Obj.txt'):
    if line.startswith('#') or '\t' not in line: continue
    f, rel, objs = line.rstrip('\n').split('\t')[:3]
    for o in objs.split('+'): fma2obj[o.strip()].add(f)
concepts = {c['id']: c for c in A['concepts']}
newconcept = {}
def norm(n): return re.sub(r'\s+', ' ', re.sub(r'\b(left|right)\b', '', n.lower())).strip()
def slug(n): return 'RN-' + re.sub(r'[^a-z0-9]+', '-', norm(n)).strip('-')
def add_new(pid, en, system, v, i, mirrored=False, fj=None):
    rec = dict(id=pid, name=ru_name(en), en=en, system=system)
    cid = slug(en)
    c = newconcept.setdefault(cid, dict(id=cid, name=re.sub(r' \((лев|прав)\.\)$', '', ru_name(en)), en=norm(en), elements=[]))
    c['elements'].append(pid); rec['conceptId'] = cid
    if mirrored: rec['mirrored'] = True
    if fj:
        for f in fma2obj.get(fj, ()):
            if f in concepts and pid not in concepts[f]['elements']: concepts[f]['elements'].append(pid)
    parts.append([rec, v, i])
newkeys = mj['new']
names_present = {r['en'].lower() for r, _, _ in parts} | {M[k]['name'].lower() for k in newkeys}
for k in newkeys:
    m = M[k]; v, i = new_geo(k); s = mj['newsys'][k]
    add_new('B43-' + k, m['name'], s, v, i, fj=m['fj'])
    # зеркальная копия для нервов, смоделированных только слева
    if s == 'nervous' and re.search(r'\bleft\b', m['name'], re.I):
        twin = re.sub(r'\bleft\b', 'right', re.sub(r'\bLeft\b', 'Right', m['name']))
        if twin.lower() not in names_present:
            mv = v.copy(); mv[:, 0] *= -1
            t = i.reshape(-1, 3)[:, [0, 2, 1]].reshape(-1).copy()
            add_new('B43M-' + k, twin, s, mv, t, mirrored=True)
print('total parts', len(parts))

# ---------- описания для настоящих нервов (перенос со схем) ----------
DESC = {c['id'][3:]: c.get('desc') for c in A['concepts'] if c['id'].startswith('RU-') and c.get('desc')}
NEWDESC = {'median nerve': 'median', 'ulnar nerve': 'ulnar', 'radial nerve': 'radial', 'musculocutaneous nerve': 'musculocutaneous',
           'axillary nerve': 'axillary', 'trunk of vagus nerve': 'vagus', 'trunk of recurrent laryngeal nerve': 'recurrent_laryngeal',
           'trunk of phrenic nerve': 'phrenic', 'trunk of facial nerve': 'facial', 'trunk of trigeminal nerve': 'trigeminal',
           'trunk of hypoglossal nerve': 'hypoglossal', 'trunk of accessory nerve': 'accessory'}
for c in newconcept.values():
    k = NEWDESC.get(c['en'])
    if k and DESC.get(k): c['desc'] = DESC[k]
EXTRA = {
 'superior sagittal sinus': 'Крупный венозный канал в твёрдой мозговой оболочке вдоль верхнего края серпа большого мозга. Собирает кровь от коры и спинномозговую жидкость.',
 'falx cerebri': 'Серповидная складка твёрдой мозговой оболочки между полушариями большого мозга.',
 'lobe of thyroid gland': 'Щитовидная железа вырабатывает гормоны, регулирующие обмен веществ, рост и теплопродукцию. Две доли соединены перешейком.',
 'isthmus of thyroid gland': 'Перешеек соединяет правую и левую доли щитовидной железы перед трахеей.',
 'superior parathyroid gland': 'Паращитовидные железы — четыре маленькие железы на задней поверхности щитовидной. Их гормон регулирует уровень кальция в крови.',
 'inferior parathyroid gland': 'Паращитовидные железы — четыре маленькие железы на задней поверхности щитовидной. Их гормон регулирует уровень кальция в крови.',
 'cauda equina': 'Пучок корешков поясничных и крестцовых спинномозговых нервов ниже окончания спинного мозга. Назван за сходство с конским хвостом.',
 'external jugular vein': 'Поверхностная вена шеи, хорошо видна под кожей при напряжении. Собирает кровь от кожи головы и лица.',
 'substantia nigra': 'Ядро среднего мозга, клетки которого вырабатывают дофамин. Их гибель лежит в основе болезни Паркинсона.',
 'red nucleus': 'Ядро среднего мозга, участвующее в координации движений.',
 'olfactory nerve': 'I пара черепных нервов — проводит запахи от слизистой носа в мозг.',
 'glossopharyngeal nerve': 'IX пара черепных нервов — вкус задней трети языка, чувствительность глотки, слюноотделение околоушной железы.',
 'vestibulocochlear nerve': 'VIII пара черепных нервов — проводит сигналы слуха и равновесия из внутреннего уха.',
 'abducens nerve': 'VI пара черепных нервов — управляет латеральной прямой мышцей глаза, отводящей взгляд в сторону.',
}
for c in newconcept.values():
    if c['en'] in EXTRA and not c.get('desc'): c['desc'] = EXTRA[c['en']]

# ---------- понятия ----------
ids = {r['id'] for r, _, _ in parts}
for c in concepts.values(): c['elements'] = [e for e in c['elements'] if e in ids]
# настоящий спинной мозг — в понятие «Спинной мозг»
sc = concepts.get('FMA7647')
real_sc = [r['id'] for r, _, _ in parts if r['en'].lower() == 'neural tissue of spinal cord']
if sc is not None:
    sc['elements'] = real_sc + [e for e in sc['elements'] if e not in real_sc]
    for r, _, _ in parts:
        if r['id'] in real_sc: r['conceptId'] = 'FMA7647'
# периферическая нервная система
periph = concepts.get('RU-peripheral')
if periph is not None:
    periph['elements'] = [r['id'] for r, _, _ in parts if r['system'] == 'nervous' and (r['id'].startswith('RU-') or (r['id'].startswith('B43') and re.search('nerve|plexus|ganglion|ansa|cauda', r['en'], re.I)))]
    periph['desc'] = 'Нервы, соединяющие головной и спинной мозг с телом: спинномозговые и черепные нервы, их сплетения и вегетативный симпатический ствол.'
# группа «Плечевое сплетение»
bp = [r['id'] for r, _, _ in parts if 'brachial nerve plexus' in r['en'].lower()]
if bp: newconcept['RN-brachial-plexus'] = dict(id='RN-brachial-plexus', name='Плечевое сплетение', en='brachial plexus', elements=bp,
        desc='Сеть нервов, образованная передними ветвями C5–T1. Корешки сливаются в верхний, средний и нижний стволы, затем в латеральный, медиальный и задний пучки, из которых выходят все нервы руки.')
for nv in ('vagus', 'phrenic', 'facial', 'trigeminal', 'hypoglossal', 'accessory', 'recurrent laryngeal'):
    concepts.pop('RU-' + nv.replace(' ', '_'), None)
allc = [c for c in concepts.values() if c['elements']] + list(newconcept.values())
for p in allc:
    if p['id'].startswith('RU-') and not any(e in ids for e in p['elements']): pass
for r, _, _ in parts:  # conceptId должен существовать
    if r['conceptId'] not in {c['id'] for c in allc}:
        cid = slug(r['en']); c = newconcept.get(cid)
        if c is None:
            c = dict(id=cid, name=re.sub(r' \((лев|прав)\.\)$', '', r['name']), en=norm(r['en']), elements=[]); newconcept[cid] = c; allc.append(c)
        if r['id'] not in c['elements']: c['elements'].append(r['id'])
        r['conceptId'] = cid

# ---------- кодирование ----------
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
    d = np.diff(q, axis=0, prepend=np.zeros((1, 3), np.int64))
    z = (d << 1) ^ (d >> 63)
    ev = b''.join(varint(z[:, c]) for c in range(3))
    hw = np.concatenate([[0], np.maximum.accumulate(i)[:-1] + 1])
    di = hw - i
    assert (di >= 0).all()
    ei = varint(di)
    dq = q.astype(np.float64) / 65535 * ext + lo
    return ev, ei, len(v), len(i), [float(x) for x in lo] + [ext], dq

for f in os.listdir(OUT):
    if f.endswith('.txt') or f == 'atlas.json': os.remove(OUT + f)
chunks = []; buf = bytearray(); out_parts = []; tri = 0; ci = 0
def flush():
    global buf, ci
    if not buf: return
    gz = gzip.compress(bytes(buf), 9); name = f'models/geo-{ci}.bin.gz.txt'
    open(OUT + f'geo-{ci}.bin.gz.txt', 'w').write(base64.b64encode(gz).decode())
    chunks.append(dict(url=name, bytes=len(buf), gzip=name, gzipBytes=len(gz))); buf = bytearray(); ci += 1
order = sorted(range(len(parts)), key=lambda k: (parts[k][0]['system'], parts[k][0]['id']))
for k in order:
    rec, v, i = parts[k]
    ev, ei, nv, ni, q, dq = encode(v, i)
    off_v = len(buf); buf += ev
    off_i = len(buf); buf += ei
    rec.update(chunk=ci, ev=off_v, evb=len(ev), ei=off_i, eib=len(ei), vertexCount=nv, indexCount=ni, q=q,
               bounds=[[round(float(x), 6) for x in dq.min(0)], [round(float(x), 6) for x in dq.max(0)]])
    out_parts.append(rec); tri += ni // 3
    if len(buf) > 2_400_000: flush()
flush()
pos = {r['id']: n for n, r in enumerate(out_parts)}
atlas = dict(version='BodyParts3D 4.3 (детализация ×2) + русская версия', codec='vq1', sex='male',
             source=A.get('source'), parts=out_parts, chunks=chunks, triangles=tri,
             concepts=[{k: c[k] for k in ('id', 'name', 'en', 'elements', 'desc', 'schematic') if k in c} for c in allc if c['elements']])
json.dump(atlas, open(OUT + 'atlas.json', 'w'), ensure_ascii=False, separators=(',', ':'))
tot = sum(c['gzipBytes'] for c in chunks)
print('parts', len(out_parts), 'concepts', len(atlas['concepts']), 'tri', tri, 'chunks', len(chunks), 'gz MB', round(tot / 1e6, 1), 'b64 MB', round(tot * 4 / 3 / 1e6, 1))
print(collections.Counter(r['system'] for r in out_parts))
