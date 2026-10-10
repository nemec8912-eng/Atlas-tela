import json, numpy as np, re, glob, collections, gzip, base64
M = json.load(open('/root/dl/meshes.json'))
A = json.load(open('/home/claude/atlas-site/models/atlas.json'))
for m in M:
    d = np.load(f"/root/dl/cache/{m['fj']}_{m['bp']}.npz"); v = d['v']
    m['lo'] = v.min(0); m['hi'] = v.max(0); m['nv'] = len(v); m['tri'] = len(d['i']) // 3
def iou(lo1, hi1, lo2, hi2):
    a = np.maximum(lo1, lo2); b = np.minimum(hi1, hi2); inter = np.prod(np.clip(b - a, 0, None))
    v1 = np.prod(hi1 - lo1); v2 = np.prod(hi2 - lo2)
    return inter / (v1 + v2 - inter + 1e-12)
old = [p for p in A['parts'] if not p['id'].startswith('RU-')]
for p in old: p['_lo'] = np.array(p['bounds'][0]); p['_hi'] = np.array(p['bounds'][1])
byname = collections.defaultdict(list)
for m in M: byname[m['name'].lower()].append(m)
match = {}; used = set()
# 1) по имени + положению
for p in old:
    best = None; bs = 0
    for m in byname.get(p['en'].lower(), []):
        if m['fj'] + m['bp'] in used: continue
        s = iou(p['_lo'], p['_hi'], m['lo'], m['hi'])
        if s > bs: bs, best = s, m
    if best is not None and bs > 0.5:
        match[p['id']] = best; used.add(best['fj'] + best['bp'])
print('upgraded by name', len(match), 'of', len(old))
# 2) остальные старые — по положению среди любых имён (переименования 4.0→4.3)
rest_old = [p for p in old if p['id'] not in match]
for p in rest_old:
    best = None; bs = 0
    for m in M:
        if m['fj'] + m['bp'] in used: continue
        s = iou(p['_lo'], p['_hi'], m['lo'], m['hi'])
        if s > bs: bs, best = s, m
    if best is not None and bs > 0.85:
        match[p['id']] = best; used.add(best['fj'] + best['bp'])
print('upgraded total', len(match), 'kept old geometry', len(old) - len(match))
# 3) новые 4.3 сетки, не дублирующие старые
nn = lambda x: re.sub(r'\s+', ' ', re.sub(r'\b(left|right)\b', '', x.lower())).strip()
for m in M:
    if m['fj'] + m['bp'] in used: continue
    for p in old:
        if nn(p['en']) == nn(m['name']) and iou(p['_lo'], p['_hi'], m['lo'], m['hi']) > 0.3:
            used.add(m['fj'] + m['bp'])
            if p['id'] not in match: match[p['id']] = m
            break
print('after same-name pass upgraded', len(match))
new = []
for m in M:
    if m['fj'] + m['bp'] in used: continue
    dup = None
    for p in old:
        if iou(p['_lo'], p['_hi'], m['lo'], m['hi']) > 0.7: dup = p; break
    if dup is not None: continue
    new.append(m)
# дубли среди новых
uniq = []
for m in new:
    if any(iou(u['lo'], u['hi'], m['lo'], m['hi']) > 0.9 and u['name'].lower() == m['name'].lower() for u in uniq): continue
    uniq.append(m)
print('new meshes', len(uniq), 'tris', sum(m['tri'] for m in uniq))
names = sorted({re.sub(r'\s+', ' ', re.sub(r'\b(left|right)\b', '', m['name'].lower())).strip() for m in uniq})
print('new unique names', len(names))
open('/root/dl/newnames.txt', 'w').write('\n'.join(names))
json.dump(dict(match={k: v['fj'] + '_' + v['bp'] for k, v in match.items()}, new=[m['fj'] + '_' + m['bp'] for m in uniq], new_all=[m['fj'] + '_' + m['bp'] for m in uniq]), open('/root/dl/match.json', 'w'))
print('tris upgraded', sum(v['tri'] for v in match.values()))
