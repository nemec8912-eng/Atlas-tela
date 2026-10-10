import json,gzip,numpy as np,re
D='/root/human-atlas/public/models/'
A=json.load(open(D+'atlas.json'))
_ch={}
def chunk(i):
    if i not in _ch: _ch[i]=open(D+f'body-{i}.bin','rb').read()
    return _ch[i]
def verts(p):
    b=chunk(p['chunk']); return np.frombuffer(b,np.float32,p['vertexCount']*3,p['positions']).reshape(-1,3)
def find(pat):
    r=re.compile(pat,re.I); return [p for p in A['parts'] if r.search(p['en'])]
def V(pat):
    ps=find(pat); return np.concatenate([verts(p) for p in ps]) if ps else None

def centerline(v,n=12,axis=None):
    """Средняя линия облака точек: срезы вдоль главной оси."""
    c=v.mean(0)
    if axis is None:
        u,s,vt=np.linalg.svd(v-c,full_matrices=False); axis=vt[0]
    axis=np.asarray(axis,float); axis/=np.linalg.norm(axis)
    t=(v-c)@axis; lo,hi=np.percentile(t,1),np.percentile(t,99)
    pts=[]
    for a,b in zip(np.linspace(lo,hi,n+1)[:-1],np.linspace(lo,hi,n+1)[1:]):
        m=(t>=a)&(t<=b)
        if m.sum()>2: pts.append(v[m].mean(0))
    pts=np.array(pts)
    if pts[0][1]<pts[-1][1]: pts=pts[::-1]  # сверху вниз
    return pts
def canal_center(p):
    """Центр позвоночного канала позвонка: самый большой зазор по z у средней линии."""
    v=verts(p); m=np.abs(v[:,0])<0.006
    if m.sum()<6: return None
    z=np.sort(v[m,2]); g=np.diff(z); i=g.argmax()
    if g[i]<0.006: return None
    y=v[m,1].mean()
    return np.array([0.0,y,(z[i]+z[i+1])/2]), g[i]

def canal2(p):
    v=verts(p); m=np.abs(v[:,0])<0.007
    zf,zb=v[:,2].max(),v[:,2].min(); L=zf-zb
    z=np.sort(v[m,2]); z=z[(z<zf-0.2*L)&(z>zb+0.25*L)]
    if len(z)<4: return np.array([0,v[:,1].mean(),zf-0.42*L])
    g=np.diff(z); i=g.argmax()
    return np.array([0,v[m,1].mean(),(z[i]+z[i+1])/2])
VERT=[p for p in A['parts'] if re.search(r'(cervical|thoracic|lumbar) vertebra$|^atlas$|^axis$',p['en'],re.I)]
VERT=sorted(VERT,key=lambda p:-p['bounds'][1][1])
def spine_line():
    pts=np.array([canal2(p) for p in VERT])
    # сглаживание выбросов: медиана по соседям
    z=pts[:,2].copy()
    for i in range(len(z)):
        z[i]=np.median(pts[max(0,i-2):i+3,2])
    pts[:,2]=z; return pts
