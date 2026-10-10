"""Беременность: схема матки ~24–26 нед., плацента на задней стенке, смещение органов и брюшной стенки."""
from common import *
import pickle
res=pickle.load(open('warped.pkl','rb'))
cerv=np.array([-0.011,0.822,-0.066]);fund=np.array([-0.007,1.06,0.05])
U=(fund-cerv);L=np.linalg.norm(U);U/=L
X=np.array([1.,0,0]);X-=U*(U@X);X/=np.linalg.norm(X);Wv=np.cross(X,U)   # Wv — вперёд
if Wv[2]<0:Wv=-Wv
C=(cerv+fund)/2+Wv*0.012;AX=np.array([0.095,L/2,0.08])   # полуоси: X, вдоль U, вперёд
R=np.stack([X,U,Wv])   # строки — оси
def loc(p):return ((p-C)@R.T)/AX
def glob(q):return (q*AX)@R+C
_post=np.concatenate([G(FA,p) for p in FA['parts'] if p['system']=='skeletal' or re.search(r'descending aorta|abdominal aorta|inferior vena cava|common iliac',p['en'],re.I)])
_post=_post[np.abs(_post[:,0]-C[0])<0.07]
_yb=np.arange(0.70,1.20,0.01);_zl=np.array([(_post[np.abs(_post[:,1]-y)<0.008][:,2].max() if (np.abs(_post[:,1]-y)<0.008).any() else -0.2) for y in _yb])
from scipy.ndimage import maximum_filter1d
_zl=maximum_filter1d(_zl,5)+0.012
def zlim(p):
    z=np.interp(p[:,1],_yb,_zl);wx=np.clip(1-(np.abs(p[:,0]-C[0])-0.04)/0.06,0,1)
    return z*wx+(-1)*(1-wx)
def ellipsoid_mesh(nu=72,nv=48):
    th=np.linspace(0,np.pi,nv);ph=np.linspace(0,2*np.pi,nu,endpoint=False)
    T,P=np.meshgrid(th,ph,indexing='ij')
    q=np.stack([np.sin(T)*np.cos(P),np.cos(T),np.sin(T)*np.sin(P)],-1).reshape(-1,3)
    # шейка внизу: слегка сужаем нижний полюс
    q[:,0]*=1-0.25*np.clip(-q[:,1],0,1)**2;q[:,2]*=1-0.25*np.clip(-q[:,1],0,1)**2
    v=glob(q);zl=zlim(v);v[:,2]=np.maximum(v[:,2],zl);idx=[]
    for i in range(nv-1):
        for j in range(nu):
            a=i*nu+j;b=i*nu+(j+1)%nu;c=(i+1)*nu+j;d=(i+1)*nu+(j+1)%nu
            idx+=[a,c,b,b,c,d]
    return v,np.array(idx,np.uint32)
# --- плацента и пуповина
PL=[p for p in FA['parts'] if p['system']=='pregnancy']
allv=np.concatenate([G(FA,p) for p in PL]);disc=np.concatenate([G(FA,p) for p in PL if not re.search('umbilical',p['en'])])
c0=disc.mean(0);_,_,vt=np.linalg.svd(disc-c0,full_matrices=False);n=vt[2]
cord=np.concatenate([G(FA,p) for p in PL if re.search('umbilical cord',p['en'])]).mean(0)
if (cord-c0)@n<0:n=-n            # n — плодовая сторона
att=glob(np.array([0,0.45,-1])/np.linalg.norm([0,0.45,-1]))   # задне-верхняя стенка
nin=C-att;nin/=np.linalg.norm(nin)
from scipy.spatial.transform import Rotation as Rot
rot,_=Rot.align_vectors([nin],[n]);Rm=rot.as_matrix()
SC=0.62
th=((disc-c0)@n).max()*SC
def place(v):return ((v-c0)*SC)@Rm.T+att+nin*(0.008)
# --- поле деформации для беременного тела
def push_out(p,margin=0.012):
    q=loc(p);r=np.linalg.norm(q,axis=1)
    lim=1+margin/AX.min()
    ins=r<lim
    ins&=p[:,2]>zlim(p)
    q2=q.copy();q2[ins]=q[ins]/np.maximum(r[ins,None],1e-6)*lim
    out=glob(q2);back=ins&(out[:,2]<zlim(p));out[back,2]=zlim(p)[back]
    return out,ins
fs=np.load('fskin.npy')
def front_need():
    # сколько не хватает коже спереди до стенки матки + 3 см
    q=np.stack(np.meshgrid(np.linspace(-1,1,41),np.linspace(-1,1,41),indexing='ij'),-1).reshape(-1,2)
    q=q[(q**2).sum(1)<1];z=np.sqrt(1-(q**2).sum(1));e=glob(np.c_[q[:,0],q[:,1],z])
    tree=cKDTree(fs[:,:2]);need=[]
    for pnt in e:
        idx=tree.query_ball_point(pnt[:2],0.01);s=fs[idx];s=s[s[:,2]>C[2]]
        if len(s):need.append(pnt[2]+0.03-s[:,2].max())
    return max(0,max(need))
A=front_need();print('bump cm',round(A*100,1))
BX,BY,SX,SY=C[0],C[1]+0.01,0.13,0.13
def bump(p):
    w=np.exp(-((p[:,0]-BX)/SX)**2-((p[:,1]-BY)/SY)**2)*np.clip((p[:,2]-(C[2]-0.02))/0.06,0,1)
    out=p.copy();out[:,2]+=A*1.15*w;return out,w>0.02
def deform(p):
    b,mb=bump(p);q,mi=push_out(b);return q,(mb|mi)
