from arms import *
from scipy.interpolate import RBFInterpolator
ARMS=pickle.load(open('arms.pkl','rb'))
HAND=r'(scaphoid|lunate|triquetral|pisiform|trapezium|trapezoid|capitate|hamate|metacarpal|finger|thumb|sesamoid bone of hand)'
def arm_seg(p):
    e=p['en'].lower()
    if re.search(r'humerus$',e):return 0
    if re.search(r'(radius|ulna)$',e):return 1
    if p['system']=='skeletal' and re.search(HAND,e):return 2
    return -1
def prewarp(v,part=None):
    """Глобальное подобие + постановка рук мужской модели в позу женской."""
    out=apply(G0,v)
    for sd,side in (('L',1),('R',-1)):
        x,J=ARMS[sd];m=armm(MG,v,side)
        seg=arm_seg(part) if part is not None else -1
        if seg>=0:
            cx=(part['bounds'][0][0]+part['bounds'][1][0])/2
            if cx*side<=0:continue
            w=np.zeros((len(v),3));w[:,seg]=1;m=np.ones(len(v))
        else:
            if m.max()<=0:continue
            w=weights(out,J)
        out=pose(x,out,J,w,m)
    return out
