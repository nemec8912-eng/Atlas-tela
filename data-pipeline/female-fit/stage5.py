from final import *
from chooser import transplant
import time
t=time.time();res={};flips=0;tot=0;rows=[]
T=[p for p in MA['parts'] if transplant(p)]
for p in T:
    v,i=G(MA,p,True);pw=prewarp(v,p);w=Wf(pw);tri=i.reshape(-1,3)
    n0=np.cross(pw[tri[:,1]]-pw[tri[:,0]],pw[tri[:,2]]-pw[tri[:,0]]);n1=np.cross(w[tri[:,1]]-w[tri[:,0]],w[tri[:,2]]-w[tri[:,0]])
    bad=(n0*n1).sum(1)<0;flips+=bad.sum();tot+=len(tri)
    if bad.sum()>20:rows.append((bad.sum(),round(bad.mean()*100,1),p['en']))
    res[p['id']]=(w.astype(np.float32),i)
print('flipped',flips,'of',tot,round(time.time()-t),'s')
for r in sorted(rows,key=lambda r:-r[0])[:15]:print(r)
pickle.dump(res,open('warped.pkl','wb'))
