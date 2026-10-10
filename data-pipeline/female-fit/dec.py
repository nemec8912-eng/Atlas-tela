import json,base64,gzip,numpy as np,functools
M='/home/claude/atlas-site/models/'
@functools.lru_cache(None)
def chunk(name,base=None):
    return np.frombuffer(gzip.decompress(base64.b64decode(open((base or M)+name.split('/')[-1]).read())),np.uint8) if base else np.frombuffer(gzip.decompress(base64.b64decode(open(M+name.split('/')[-1]).read())),np.uint8)
def varints(b,o,n):
    # decode n varints starting at offset o (vectorized)
    seg=b[o:o+n*5]
    ends=np.nonzero((seg&128)==0)[0][:n]
    starts=np.concatenate([[0],ends[:-1]+1])
    vals=np.zeros(n,np.int64)
    maxlen=int((ends-starts).max())+1 if n else 0
    for k in range(maxlen):
        idx=starts+k;ok=idx<=ends
        vals[ok]|=(seg[idx[ok]].astype(np.int64)&127)<<(7*k)
    return vals,o+int(ends[-1])+1 if n else o
def geom(A,p,idx=False):
    b=chunk(A['chunks'][p['chunk']]['url'],A.get('_base'));vc=p['vertexCount'];lx,ly,lz,ext=p['q']
    pos=np.zeros((vc,3));o=p['ev']
    for c in range(3):
        z,o=varints(b,o,vc);d=np.where(z%2,-(z+1)//2,z//2);pos[:,c]=np.cumsum(d)*ext/65535+[lx,ly,lz][c]
    if not idx:return pos
    x,_=varints(b,p['ei'],p['indexCount'])
    out=np.zeros(len(x),np.int64);hw=0
    # sequential high-watermark decode
    xl=x.tolist();res=[0]*len(xl)
    for n,v in enumerate(xl):
        val=hw-v;res[n]=val
        if val==hw:hw+=1
    return pos,np.array(res,np.uint32)
