from warp import *
S1,D,sm=pickle.load(open('rbf.pkl','rb'))
rbf=RBFInterpolator(S1,D,kernel='thin_plate_spline',smoothing=sm)
T1=S1+D
def affine_region(mask):
    X=np.c_[S1[mask],np.ones(mask.sum())];Wm,*_=np.linalg.lstsq(X,T1[mask],rcond=None)
    print('affine det',np.linalg.det(Wm[:3]).round(3),'n',mask.sum(),'rms cm',round(np.sqrt(((X@Wm-T1[mask])**2).sum(1).mean())*100,2))
    return Wm
_A=pickle.load(open('headA.pkl','rb'));HEAD=np.r_[_A[:3,:3].T,_A[:3,3][None]]
FOOT={s:affine_region((S1[:,1]<0.13)&(S1[:,0]*s>0)) for s in (1,-1)}
def ss_(a,b,x):return ss(a,b,x)
def Wf(v):
    out=[]
    for k in range(0,len(v),20000):
        c=v[k:k+20000];t=c+rbf(c)
        X=np.c_[c,np.ones(len(c))]
        pass
        for s,Wm in FOOT.items():
            af=(1-ss_(0.07,0.11,c[:,1]))*(c[:,0]*s>0);t=t*(1-af[:,None])+(X@Wm)*af[:,None]
        out.append(t)
    return np.concatenate(out)
