import json,re,numpy as np
from scipy.spatial import cKDTree
from dec import geom,M
MA=json.load(open(M+'atlas.json'));FA=json.load(open('/root/rg/fbase/atlas-female.json'));FA['_base']='/root/rg/fbase/'
_cache={}
def G(A,p,idx=False):
    k=(id(A),p['id'],idx)
    if k not in _cache:_cache[k]=geom(A,p,idx)
    return _cache[k]
def pts(A,pred,maxn=None,seed=0):
    ps=[p for p in A['parts'] if pred(p)]
    if not ps:return np.zeros((0,3))
    v=np.concatenate([G(A,p) for p in ps])
    if maxn and len(v)>maxn:v=v[np.random.default_rng(seed).choice(len(v),maxn,replace=False)]
    return v
def en(rx,sys=None):
    r=re.compile(rx,re.I);return lambda p:bool(r.search(p.get('en',''))) and (sys is None or p['system'] in sys)
def umeyama(src,dst,scale=True):
    ms,md=src.mean(0),dst.mean(0);s0,d0=src-ms,dst-md
    U,S,Vt=np.linalg.svd(d0.T@s0/len(src));D=np.eye(3)
    if np.linalg.det(U)*np.linalg.det(Vt)<0:D[2,2]=-1
    R=U@D@Vt;c=(S*np.diag(D)).sum()/((s0**2).sum()/len(src)) if scale else 1.0
    return c,R,md-c*R@ms
def affine_fit(src,dst):
    X=np.c_[src,np.ones(len(src))];W,*_=np.linalg.lstsq(X,dst,rcond=None);return W
def icp(src,dst,mode='sim',iters=40):
    """Регистрирует src на dst; возвращает функцию преобразования."""
    tree=cKDTree(dst);cur=src.copy()
    T=lambda x:x
    c,R,t=umeyama(src,dst[tree.query(src)[1]]) if False else (1,np.eye(3),dst.mean(0)-src.mean(0))
    A=np.eye(4);A[:3,3]=t
    for k in range(iters):
        cur=src@A[:3,:3].T+A[:3,3]
        d,i=tree.query(cur);m=d<np.percentile(d,90)+1e-9
        # обратные соответствия для симметрии
        tree2=cKDTree(cur);d2,i2=tree2.query(dst)
        S=np.r_[src[m],src[i2]];D=np.r_[dst[i[m]],dst]
        if mode=='aff':
            W=affine_fit(S,D);A=np.eye(4);A[:3,:3]=W[:3].T;A[:3,3]=W[3]
        else:
            c,R,t=umeyama(S,D,mode=='sim');A=np.eye(4);A[:3,:3]=c*R;A[:3,3]=t
    cur=src@A[:3,:3].T+A[:3,3];d,_=tree.query(cur)
    return A,float(np.median(d))
def apply(A,x):return x@A[:3,:3].T+A[:3,3]
