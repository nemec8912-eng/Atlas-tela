import json,re,collections
p='/home/claude/atlas-site/models/atlas.json'; a=json.load(open(p))
fix=[(r'^(left|right) (fibularis (brevis|longus|tertius)|tibialis (anterior|posterior)|levator scapulae|subscapularis)$','muscular'),
     (r'iliotibial tract','connective'),(r'papillary muscle','cardiac'),(r'inferior nasal concha','skeletal'),
     (r'^(left |right )?(arytenoid|corniculate|cuneiform) cartilage$|^cricoid cartilage$|^thyroid cartilage$','respiratory')]
n=collections.Counter()
for x in a['parts']:
    for pat,s in fix:
        if re.search(pat,x['en'],re.I) and x['system']!=s: n[s]+=1; x['system']=s
json.dump(a,open(p,'w'),ensure_ascii=False,separators=(',',':')); print('fixed',dict(n))
a=json.load(open(p)); k=0
for x in a['parts']:
    if re.match(r'hepatovenous segment',x['en'],re.I):
        x['system']='digestive'; x['name']=x['name'].replace(' (венозный)',''); k+=1
    if x['id'].startswith('RU-'):
        m=re.match(r'^(Left |Right )(\w)(.*)$',x['en'])
        if m: x['en']=m.group(1)+m.group(2).lower()+m.group(3)
for c in a['concepts']:
    c['name']=c['name'].replace(' (венозный)','')
json.dump(a,open(p,'w'),ensure_ascii=False,separators=(',',':')); print('liver segments',k)
a=json.load(open(p))
byname={}
for c in a['concepts']:
    if not c['id'].startswith('RN-'): byname.setdefault(c['name'],c)
merged=0; keep=[]; repoint={}
for c in a['concepts']:
    if c['id'].startswith('RN-') and c['name'] in byname:
        t=byname[c['name']]
        t['elements']+= [e for e in c['elements'] if e not in t['elements']]
        if c.get('desc') and not t.get('desc'): t['desc']=c['desc']
        repoint[c['id']]=t['id']; merged+=1
    else: keep.append(c)
a['concepts']=keep
for x in a['parts']:
    if x['conceptId'] in repoint: x['conceptId']=repoint[x['conceptId']]
json.dump(a,open(p,'w'),ensure_ascii=False,separators=(',',':')); print('merged concepts',merged)
a=json.load(open(p))
REN={'trunk of vagus nerve':('Блуждающий нерв','vagus nerve'),'trunk of phrenic nerve':('Диафрагмальный нерв','phrenic nerve'),
 'trunk of recurrent laryngeal nerve':('Возвратный гортанный нерв','recurrent laryngeal nerve'),'trunk of facial nerve':('Лицевой нерв','facial nerve'),
 'trunk of trigeminal nerve':('Тройничный нерв','trigeminal nerve'),'trunk of hypoglossal nerve':('Подъязычный нерв','hypoglossal nerve'),
 'trunk of accessory nerve':('Добавочный нерв','accessory nerve')}
r=0
for c in a['concepts']:
    if c.get('en') in REN: c['name'],c['en']=REN[c['en']]; r+=1
json.dump(a,open(p,'w'),ensure_ascii=False,separators=(',',':')); print('renamed nerve concepts',r)
a=json.load(open(p))
pats=[]
for line in open('/root/dl/desc.tsv',encoding='utf8'):
    line=line.rstrip('\n')
    if '\t' in line:
        k,v=line.split('\t',1); pats.append((re.compile(k),v))
nz=lambda x:re.sub(r'\s+',' ',re.sub(r'\b(left|right)\b','',(x or '').lower())).strip()
added=0
for c in a['concepts']:
    if c.get('desc'): continue
    n=nz(c.get('en'))
    for r,v in pats:
        if r.fullmatch(n): c['desc']=v; added+=1; break
C={c['id']:c for c in a['concepts']}
cov=sum(1 for x in a['parts'] if C[x['conceptId']].get('desc'))
json.dump(a,open(p,'w'),ensure_ascii=False,separators=(',',':')); print('desc added',added,'parts with own description',cov,'of',len(a['parts']))
