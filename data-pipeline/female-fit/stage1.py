# Глобальное подобие мужской модели к женской по центрам соответствующих структур
from pairs import *
import pickle
src=[];dst=[];names=[]
for n,mp,fp,mode in STRUCT:
    a=pts(MA,mp);b=pts(FA,fp)
    if len(a)==0 or len(b)==0:print('skip',n);continue
    src.append(a.mean(0));dst.append(b.mean(0));names.append(n)
src=np.array(src);dst=np.array(dst)
c,R,t=umeyama(src,dst)
res=np.linalg.norm((src@(c*R).T+t)-dst,axis=1)
print('scale',c,'t',t.round(3),'R',np.degrees(np.arccos((np.trace(R)-1)/2)))
for n,r in zip(names,res):print(n,round(r*100,1),'cm')
G0=np.eye(4);G0[:3,:3]=c*R;G0[:3,3]=t
pickle.dump(G0,open('G0.pkl','wb'))
