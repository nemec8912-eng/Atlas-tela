from common import *
FEM_HAS_SK=re.compile(r'^(Atlas|Axis|(First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth|Eleventh|Twelfth) (cervical|thoracic|lumbar) vertebra|Sacrum|(Left|Right) (hip bone|femur|tibia|fibula|patella))$')
FEM_HAS_MU=re.compile(r'^(Left|Right) (superior|inferior|medial|lateral) rectus$|^(Left|Right) (superior|inferior) oblique$|^(Left|Right) rectus femoris$',re.I)
MALE_ONLY=re.compile(r'bulbospongios|ischiocavernos|cremaster',re.I)
CONN_OK=re.compile(r'Flexor retinaculum|Interosseous membrane|Linea alba|calcaneal tendon|iliotibial tract|inguinal ligament|long plantar ligament|tendinous arch of levator ani|pterygomandibular raphe|stylohyoid ligament|stylomandibular ligament',re.I)
def transplant(p):
    e=p['en']
    if p['system']=='skeletal':return not FEM_HAS_SK.search(e)
    if p['system']=='muscular':return not FEM_HAS_MU.search(e) and not MALE_ONLY.search(e)
    if p['system']=='connective':return bool(CONN_OK.search(e))
    return False
if __name__=='__main__':
    T=[p for p in MA['parts'] if transplant(p)]
    import collections;print(len(T),collections.Counter(p['system'] for p in T),sum(p['vertexCount'] for p in T))
    print([p['en'] for p in MA['parts'] if p['system']=='muscular' and re.search('perine|sphincter|levator ani|urethr|vagin',p['en'],re.I)])
