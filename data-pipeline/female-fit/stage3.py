from warp import *
import time
t0=time.time()
rng=np.random.default_rng(7)
def sample(v,n):return v if len(v)<=n else v[rng.choice(len(v),n,replace=False)]
src=[];dst=[];wt=[]
for n,mp,fp,mode in STRUCT:
    ps=[p for p in MA['parts'] if mp(p)]
    a=np.concatenate([prewarp(G(MA,p),p) for p in ps]);b=pts(FA,fp)
    A,err=icp(sample(a,4000),sample(b,6000),mode)
    s=sample(a,120);src.append(s);dst.append(apply(A,s));wt+= [n]*len(s)
    print(n,mode,'icp med cm',round(err*100,2),'shift cm',round(np.linalg.norm(apply(A,a).mean(0)-a.mean(0))*100,1))
HA=pickle.load(open('headA.pkl','rb'))
sk=np.concatenate([prewarp(G(MA,p),p) for p in MA['parts'] if re.search(r'^(Left |Right )?(parietal|occipital|frontal|temporal|sphenoid) bone$',p['en'])])
sk=sample(sk,900);src.append(sk);dst.append(apply(HA,sk))
Ssrc=np.concatenate(src);Sdst=np.concatenate(dst)
def scalp(p):return (p[:,1]>1.50)&(p[:,2]<0.0)
# кожа
ms=np.load('skin.npy');mw=np.concatenate([prewarp(ms[i:i+20000]) for i in range(0,len(ms),20000)])
fs=np.load('fskin.npy')
def breast(p):return (np.abs(p[:,0]+0.006)>0.0)&(np.abs(p[:,0]+0.006)<0.16)&(p[:,1]>1.12)&(p[:,1]<1.34)&(p[:,2]>-0.04)
fsel=fs[~breast(fs)]
idx=rng.choice(len(ms),4000,replace=False);m0=ms[idx];mwi=mw[idx]
fidx=rng.choice(len(fsel),4000,replace=False);f0=fsel[fidx]
cur=mwi.copy()
for it,smooth in enumerate([1e-2,3e-3,1e-3,3e-4]):
    d,i=cKDTree(fsel).query(cur);ok=(d<0.06)&~breast(cur)&~scalp(mwi)
    d2,i2=cKDTree(cur).query(f0);ok2=(d2<0.06)&~scalp(f0)
    S1=np.r_[Ssrc,mwi[ok],mwi[i2[ok2]]];D1=np.r_[Sdst,fsel[i[ok]],f0[ok2]]
    # прореживание дубликатов
    _,u=np.unique(np.round(S1/0.004).astype(int),axis=0,return_index=True);S1,D1=S1[u],D1[u]
    rbf=RBFInterpolator(S1,D1-S1,kernel='thin_plate_spline',smoothing=smooth*len(S1)/1000)
    cur=mwi+rbf(mwi)
    dd,_=cKDTree(fsel).query(cur[~breast(cur)]);sd,_=cKDTree(Sdst).query(Ssrc+rbf(Ssrc))
    print('iter',it,'pairs',len(S1),'skin med/95 cm',np.round(np.percentile(dd,[50,95])*100,2),'struct med cm',round(np.median(np.linalg.norm(Ssrc+rbf(Ssrc)-Sdst,axis=1))*100,2),round(time.time()-t0),'s')
pickle.dump((S1,D1-S1,smooth*len(S1)/1000),open('rbf.pkl','wb'))
