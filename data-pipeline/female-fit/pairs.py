from common import *
ORD=['First','Second','Third','Fourth','Fifth','Sixth','Seventh','Eighth','Ninth','Tenth','Eleventh','Twelfth']
def S(side):return 'Left' if side=='L' else 'Right'
STRUCT=[]  # (name, male pred, female pred, mode)
STRUCT.append(('C1',en(r'^Atlas$'),en(r'^vertebral bone 1$'),'sim'))
STRUCT.append(('C2',en(r'^Axis$'),en(r'^vertebral bone 2$'),'sim'))
for k in range(3,8):STRUCT.append((f'C{k}',en(rf'^{ORD[k-1]} cervical vertebra$'),en(rf'^mammalian cervical vertebra {k}$'),'sim'))
for k in range(1,13):STRUCT.append((f'T{k}',en(rf'^{ORD[k-1]} thoracic vertebra$'),en(rf'^thoracic vertebra {k}$'),'sim'))
for k in range(1,6):STRUCT.append((f'L{k}',en(rf'^{ORD[k-1]} lumbar vertebra$'),en(rf'^lumbar vertebra {k}$'),'sim'))
STRUCT.append(('sacrum',en(r'^Sacrum$'),en(r'^fused sacrum$'),'sim'))
for sd,sg in [('L','_L$'),('R','_R$')]:
    s=S(sd)
    STRUCT.append((f'hip{sd}',en(rf'^{s} hip bone$'),lambda p,sg=sg:bool(re.search(r'(ilium|ischium|pubis)_compact_bone'+sg,p['id'])),'sim'))
    for b in ['femur','tibia','fibula','patella']:STRUCT.append((f'{b}{sd}',en(rf'^{s} {b}$'),en(rf'^{s} {b}$'),'sim'))
    STRUCT.append((f'eye{sd}',en(rf'^{s} (sclera|cornea)$'),lambda p,sg=sg:bool(re.search(r'(sclera|cornea)'+sg,p['id'])),'sim'))
    STRUCT.append((f'brain{sd}',en(rf'white matter of {s.lower()} cerebral hemisphere'),lambda p,sg=sg:bool(re.search(r'white_matter_of_forebrain'+sg,p['id'])),'aff'))
    sgn=1 if sd=='L' else -1
    cx=lambda p:(p['bounds'][0][0]+p['bounds'][1][0])/2
    STRUCT.append((f'lung{sd}',lambda p,sgn=sgn:p['en'].startswith('Parenchyma of') and 'bronchopulmonary' in p['en'] and cx(p)*sgn>0,lambda p,sgn=sgn:p['system']=='respiratory' and 'bronchopulmonary seg' in p['en'].lower() and cx(p)*sgn>-0.005,'aff'))
    STRUCT.append((f'kidney{sd}',en(rf'^{s} kidney$'),lambda p,sg=sg:bool(re.search(r'outer_cortex_of_kidney'+sg,p['id'])),'aff'))
STRUCT.append(('larynx',en(r'^(Thyroid|Cricoid) cartilage$'),en(r'^(thyroid|cricoid) cartilage$'),'sim'))
STRUCT.append(('trachea',en(r'^Trachea$'),en(r'^trachea$'),'aff'))
STRUCT.append(('heart',en(r'^Wall of ventricle$'),en(r'^heart (left|right) ventricle$'),'aff'))
if __name__=='__main__':
    for n,mp,fp,mode in STRUCT:
        a=[p['en'] for p in MA['parts'] if mp(p)];b=[p['en'] for p in FA['parts'] if fp(p)]
        print(n,len(a),len(b),a[:3],b[:3])
