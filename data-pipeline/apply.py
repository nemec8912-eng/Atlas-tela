import json,re,sys
S=sys.argv[1]; A=sys.argv[2]
names=open(S+'/names.txt').read().split('\n')
tr={}
for i in range(1,7):
    for line in open(f'{S}/ru{i}.tsv',encoding='utf8'):
        line=line.rstrip('\n')
        if not line: continue
        en,ru=line.split('\t'); tr[en]=ru
miss=[n for n in names if n not in tr]; extra=[k for k in tr if k not in set(names)]
print('missing',len(miss),miss[:10]); print('extra',len(extra),extra[:10])
def norm(n): return re.sub(r'\s+',' ',re.sub(r'\b(left|right)\b','',n)).strip()
def ru(n):
    low=n.lower(); base=tr[norm(low)]
    side=' (лев.)' if re.search(r'\bleft\b',low) else ' (прав.)' if re.search(r'\bright\b',low) else ''
    base=base[0].upper()+base[1:]
    return base+side
a=json.load(open(A))
for p in a['parts']: p['en']=p['name']; p['name']=ru(p['name'])
for c in a['concepts']: c['en']=c['name']; c['name']=ru(c['name'])
for ch in a['chunks']:
    ch['url']=ch['url'].lstrip('/'); ch['gzip']=ch['gzip'].lstrip('/')
json.dump(a,open(A,'w'),ensure_ascii=False,separators=(',',':'))
print([p['name'] for p in a['parts'][:6]])
