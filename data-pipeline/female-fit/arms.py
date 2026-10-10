from pairs import *
import pickle,sys
sys.path.insert(0,'.')
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation as Rot
G0=pickle.load(open('G0.pkl','rb'))
def ss(a,b,x):t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
MG=dict(armY=[.6,.98,1.0,1.1,1.2,1.3,1.46,1.6],armX=[.19,.19,.168,.158,.165,.16,.15,.15],armMinY=.6,armMaxY=1.46)
FG=dict(armY=[.7,.8,.9,1.0,1.1,1.2,1.42,1.6],armX=[.29,.28,.25,.2,.168,.155,.15,.15],armMinY=.7,armMaxY=1.42)
def armm(g,p,side,m=.012):
    x,y=p[:,0],p[:,1];xb=np.interp(y,g['armY'],g['armX'])
    return ss(-m,m,side*x-xb)*ss(g['armMinY']-m,g['armMinY']+m,y)*(1-ss(g['armMaxY']-m,g['armMaxY']+m,y))
def joints(sd):
    s=S(sd);hum=G(MA,next(p for p in MA['parts'] if p['en']==f'{s} humerus'))
    rad=G(MA,next(p for p in MA['parts'] if p['en']==f'{s} radius'));uln=G(MA,next(p for p in MA['parts'] if p['en']==f'{s} ulna'))
    top=hum[hum[:,1]>hum[:,1].max()-.04];med=top[np.abs(top[:,0])<np.median(np.abs(top[:,0]))]
    Sh=med.mean(0);E=hum[hum[:,1]<hum[:,1].min()+.03].mean(0)
    W=(rad[rad[:,1]<rad[:,1].min()+.015].mean(0)+uln[uln[:,1]<uln[:,1].min()+.015].mean(0))/2
    return [apply(G0,x[None])[0] for x in (Sh,E,W)]
def weights(p,J,b=.025):
    Sh,E,W=J;dU=(E-Sh)/np.linalg.norm(E-Sh);dF=(W-E)/np.linalg.norm(W-E)
    wf=ss(-b,b,(p-E)@dU);wh=ss(-b,b,(p-W)@dF)
    return np.c_[1-wf,wf*(1-wh),wf*wh]
def pose(params,p,J,w,m):
    Sh,E,W=J
    Rs=Rot.from_rotvec(params[0:3]).as_matrix();ts=params[3:6];Re=Rot.from_rotvec(params[6:9]).as_matrix();Rw=Rot.from_rotvec(params[9:12]).as_matrix()
    Tu=lambda x:(x-Sh)@Rs.T+Sh+ts
    pf=(p-E)@Re.T+E;ph=(((p-W)@Rw.T+W)-E)@Re.T+E
    out=w[:,0:1]*Tu(p)+w[:,1:2]*Tu(pf)+w[:,2:3]*Tu(ph)
    return (1-m)[:,None]*p+m[:,None]*out
def fit(sd):
    side=1 if sd=='L' else -1
    msk=apply(G0,np.load('skin.npy'));mo=np.load('skin.npy')
    mm=armm(MG,mo,side);sel=(mm>.5)&(msk[:,1]<1.30)
    J=joints(sd);P=msk[sel];w=weights(P,J);m=np.ones(len(P))
    fs=np.load('fskin.npy');fm=armm(FG,fs,side);Fp=fs[(fm>.5)&(fs[:,1]<1.30)]
    rng=np.random.default_rng(1);P2=P[rng.choice(len(P),min(3000,len(P)),replace=False)];w2=weights(P2,J);m2=np.ones(len(P2))
    Fp2=Fp[rng.choice(len(Fp),min(3000,len(Fp)),replace=False)];tree=cKDTree(Fp2)
    def f(x):
        Q=pose(x,P2,J,w2,m2);d1,_=tree.query(Q);d2,_=cKDTree(Q).query(Fp2)
        return np.mean(np.minimum(d1,.05)**2)+np.mean(np.minimum(d2,.05)**2)+1e-5*np.sum(x**2)
    x0=np.zeros(12);best=minimize(f,x0,method='Powell',options=dict(maxiter=20000,xtol=1e-4,ftol=1e-9))
    x=best.x;print(sd,'loss',f(x0),'->',best.fun,'rms cm',np.sqrt(best.fun/2)*100)
    print(' shoulder rot deg',np.degrees(np.linalg.norm(x[0:3])).round(1),'t',x[3:6].round(3),'elbow',np.degrees(x[6:9]).round(1),'wrist',np.degrees(x[9:12]).round(1))
    return x,J
if __name__=='__main__':
    out={}
    for sd in 'LR':out[sd]=fit(sd)
    pickle.dump(out,open('arms.pkl','wb'))
