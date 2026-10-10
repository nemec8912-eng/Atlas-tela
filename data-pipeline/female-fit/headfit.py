from warp import *
mp=lambda p:bool(re.search(r'white matter of (left|right) cerebral hemisphere|^cerebellum$|^(left|right) (sclera|cornea)$',p['en'],re.I))
fp=lambda p:bool(re.search(r'white_matter_of_forebrain|lateral_hemisphere_of_cerebellum|paravermis|cerebellar_vermis|(sclera|cornea)_[LR]$',p['id']))
a=np.concatenate([prewarp(G(MA,p),p) for p in MA['parts'] if mp(p)]);b=pts(FA,fp)
rng=np.random.default_rng(0)
A,err=icp(a[rng.choice(len(a),6000)],b[rng.choice(len(b),8000)],'sim',60)
print('sim scale',np.cbrt(np.linalg.det(A[:3,:3])).round(3),'err cm',err*100)
pickle.dump(A,open('headA.pkl','wb'))
