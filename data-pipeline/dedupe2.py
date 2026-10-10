import json,numpy as np,re,collections
from scipy.spatial import cKDTree
from classify import system_of
mj=json.load(open('match.json'))
A=json.load(open('/home/claude/atlas-site/models/atlas.json'))
sysof={p['id']:p['system'] for p in A['parts']}
M={m['fj']+'_'+m['bp']:m for m in json.load(open('meshes.json'))}
# все кандидаты: заново из match.py (до первой чистки)
import subprocess
grp=lambda s:{'arterial':'vessel','venous':'vessel','cardiac':'vessel'}.get(s,s)
pts=collections.defaultdict(list)
for pid,k in mj['match'].items(): pts[grp(sysof[pid])].append(np.load(f'cache/{k}.npz')['v'])
T={g:cKDTree(np.concatenate(v)) for g,v in pts.items()}
keep=[];drop=[];unk=[]
for k in mj['new_all']:
    s=system_of(M[k]['name'])
    if s is None: unk.append(M[k]['name']); s='connective'
    v=np.load(f'cache/{k}.npz')['v']
    t=T.get(grp(s))
    frac=0.0
    if t is not None:
        d,_=t.query(v,distance_upper_bound=0.001); frac=float(np.isfinite(d).mean())
    (drop if frac>0.7 and not re.search('nucleus|preoptic',M[k]['name'],re.I) else keep).append((k,M[k]['name'],s,round(frac,2)))
print('keep',len(keep),'drop',len(drop),'unclassified',sorted(set(unk)))
open('drop.txt','w').write('\n'.join(f'{x[1]} [{x[2]}] {x[3]}' for x in drop))
mj['new']=[k for k,_,_,_ in keep]; mj['newsys']={k:s for k,_,s,_ in keep}
json.dump(mj,open('match.json','w'))
names=sorted({re.sub(r'\s+',' ',re.sub(r'\b(left|right)\b','',M[k]['name'].lower())).strip() for k in mj['new']})
open('newnames.txt','w').write('\n'.join(names)); print('names',len(names),'tris',sum(len(np.load(f'cache/{k}.npz')['i'])//3 for k in mj['new']))
