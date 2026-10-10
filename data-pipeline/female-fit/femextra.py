"""Дополнения женской модели: скелет и мышцы из BodyParts3D, подогнанные под женское тело; беременность внутри тела."""
from preg2 import *
from chooser import transplant
MC={c['id']:c for c in MA['concepts']}
extra=[];concepts={};variant={};normal_only=set();renames={}
def addc(cid,name,en,el,desc=None,**kw):
    c=concepts.setdefault(cid,dict(id=cid,name=name,en=en,elements=[],**kw))
    if desc:c['desc']=desc
    for e in el:
        if e not in c['elements']:c['elements'].append(e)
moved=lambda a,b:np.abs(a-b).max()>0.002
# 1. скелет, мышцы, связки
for p in MA['parts']:
    if p['id'] not in res:continue
    v,i=res[p['id']];v=v.astype(np.float64);nid='F-M-'+p['id']
    mc=MC.get(p['conceptId'],{});cid='M:'+p['conceptId']
    rec=dict(id=nid,name=p['name'],en=p['en'],conceptId=cid,system=p['system'],adapted=True)
    extra.append(dict(rec=rec,v=v,i=i));addc(cid,mc.get('name',p['name']),mc.get('en',p['en']),[nid],mc.get('desc'),adapted=True)
    if p['system']!='skeletal':
        d,_=deform(v)
        if moved(d,v):variant[nid]=d
# 2. собственные части женской модели
UT=re.compile(r'^(body of uterus|Fundus of uterus|(Anterior|Posterior) wall of uterus|cornua|Lower uterine segment|internal cervical os|uterine cavity|endometrium|myometrium)$',re.I)
for p in FA['parts']:
    if p['system'] in('skeletal','pregnancy'):continue
    if UT.search(p['en']):normal_only.add('F-'+p['id'][2:] if False else p['id']);continue
    v=G(FA,p);d,_=deform(v)
    if moved(d,v):variant[p['id']]=None
# 3. беременность: плацента, пуповина и схема матки
preg=[p['id'] for p in FA['parts'] if p['system']=='pregnancy']
ev,ei=ellipsoid_mesh()
extra.append(dict(rec=dict(id='F-preg-uterus',name='Матка при беременности',en='Gravid uterus (schematic)',conceptId='F:gravid-uterus',system='pregnancy',schematic=True),v=ev,i=ei))
addc('F:gravid-uterus','Матка при беременности','Gravid uterus',['F-preg-uterus'],
     'Матка во второй половине беременности: дно поднимается примерно до уровня пупка, полость занимают плод, околоплодные воды и плацента. Шейка остаётся внизу и держит плод в полости матки до родов.',schematic=True)
# 4. таз: понятные названия
PEL={'ilium':('Подвздошная кость','Губчатое вещество подвздошной кости','ilium'),'ischium':('Седалищная кость','Губчатое вещество седалищной кости','ischium'),'pubis':('Лобковая кость','Губчатое вещество лобковой кости','pubis')}
for p in FA['parts']:
    m=re.match(r'F-VH_F_(ilium|ischium|pubis)_(compact|spongy)_bone_([LR])$',p['id'])
    if not m:continue
    b,kind,sd=m.groups();sfx=' (лев.)' if sd=='L' else ' (прав.)';nm=(PEL[b][0] if kind=='compact' else PEL[b][1])+sfx
    renames[p['id']]=dict(name=nm,en=f"{'Left' if sd=='L' else 'Right'} {PEL[b][2]}"+('' if kind=='compact' else ' (spongy bone)'),conceptId=f'F:{b}_{sd}')
    addc(f'F:{b}_{sd}',PEL[b][0]+sfx,f"{'Left' if sd=='L' else 'Right'} {PEL[b][2]}",[p['id']])
    addc(f'F:hip_{sd}','Тазовая кость'+sfx,f"{'Left' if sd=='L' else 'Right'} hip bone",[p['id']],
         'Тазовая кость образуется сращением подвздошной, седалищной и лобковой костей. Вместе с крестцом образует таз; у женщин таз шире и ниже, а его полость округлее — это важно для родов.')
print('extra',len(extra),'variants',len(variant),'normal only',sorted(normal_only),'concepts',len(concepts))
pickle.dump(dict(extra=extra,variant=variant,normal_only=normal_only,renames=renames,concepts=list(concepts.values()),preg=preg),open('femextra.pkl','wb'))
