import json,re,sys
S='/tmp/claude-0/-home-claude/cbf11d43-6187-53a1-be7c-766797224c02/scratchpad/'
tr={}
for i in range(1,8):
    for l in open(f'{S}ru{i}.tsv',encoding='utf8'):
        l=l.rstrip('\n')
        if l: en,ru=l.split('\t'); tr[en]=ru
def norm(n): return re.sub(r'\s+',' ',re.sub(r'\b(left|right)\b','',n)).strip()
G={'left':('левой','левого','Левая','левая'),'right':('правой','правого','Правая','правая')}
# (англ. шаблон, функция замены в русском тексте)
def gen(phrase):  # женский род, родительный падеж
    return lambda ru,sd: ru.replace(phrase, f'{G[sd][0]} {phrase}',1) if phrase in ru else None
def nom(phrase):  # именительный в начале
    def f(ru,sd):
        if ru.lower().startswith(phrase.lower()): return f'{G[sd][2]} {phrase}'+ru[len(phrase):]
        return None
    return f
def masc(phrase):
    return lambda ru,sd: ru if G[sd][1] in ru else (ru.replace(phrase, f'{G[sd][1]} {phrase}',1) if phrase in ru else None)
def pre_adj(word_f):
    def f(ru,sd):
        adj={'left':'Левая','right':'Правая'}[sd]
        return adj+' '+ru[0].lower()+ru[1:]
    return f
RULES=[
 (r'^(left|right) lobe branch of',[lambda ru,sd: ru.replace('Долевая ветвь','Ветвь',1)+f' к {G[sd][0]} доле печени' if ru.startswith('Долевая ветвь') else None]),
 (r'^(left|right) (?:anterior |posterior )?cusp of',[pre_adj('f')]),
 (r'^(left|right) conus artery',[pre_adj('f')]),
 (r'\b(left|right) coronary artery',[nom('коронарная артерия'),gen('коронарной артерии')]),
 (r'\b(left|right) posterior interventricular artery',[gen('задней межжелудочковой артерии')]),
 (r'\b(left|right) ventricle',[masc('желудочка')]),
 (r'\b(left|right) atrium',[masc('предсердия')]),
 (r'\b(left|right) hepatic artery',[nom('печёночная артерия'),gen('печёночной артерии')]),
 (r'\b(left|right) hepatic vein',[nom('печёночная вена'),gen('печёночной вены')]),
 (r'\b(left|right) hepatic biliary tree',[lambda ru,sd: ru.replace('желчного дерева печени',f'желчного дерева {G[sd][0]} доли печени',1) if 'желчного дерева печени' in ru else (ru.replace('желчного дерева',f'желчного дерева {G[sd][0]} доли печени',1) if 'желчного дерева' in ru else None)]),
 (r'\b(left|right) portal vein',[lambda ru,sd: ru.replace('воротной вены',f'{G[sd][0]} ветви воротной вены',1) if 'воротной вены' in ru else None]),
 (r'\b(left|right) colic (artery|vein)',[nom('ободочная артерия'),nom('ободочная вена'),gen('ободочной артерии'),gen('ободочной вены')]),
 (r'\b(left|right) gastric (artery|vein)',[nom('желудочная артерия'),nom('желудочная вена'),gen('желудочной артерии')]),
 (r'\b(left|right) gastro-?epiploic (artery|vein)',[nom('желудочно-сальниковая артерия'),nom('желудочно-сальниковая вена')]),
 (r'\b(left|right) marginal vein',[nom('краевая вена')]),
 (r'\b(left|right) duct of caudate lobe',[lambda ru,sd: ru.replace('Проток',f'{G[sd][2].capitalize()} проток'.replace('Левая','Левый').replace('Правая','Правый'),1)]),
]
def ru_name(en):
    base=tr[norm(en.lower())]; base=base[0].upper()+base[1:]
    used=[]
    for pat,fs in RULES:
        m=re.search(pat,en,re.I)
        if not m: continue
        sd=m.group(1).lower()
        for f in fs:
            r=f(base,sd)
            if r: base=r[0].upper()+r[1:]; used.append(m.start()); break
    first=re.match(r'^(left|right)\b',en,re.I)
    others=[m for m in re.finditer(r'\b(left|right)\b',en,re.I) if not any(abs(m.start()-u)<2 for u in used)]
    # суффикс стороны тела: первое оставшееся слово left/right, если оно не относится к органу
    if others:
        sd=others[0].group(1).lower()
        # «First right anterior branch …» внутри сердца — это не сторона тела
        if used and not first: return base
        base+=' (лев.)' if sd=='left' else ' (прав.)'
    return base
if __name__=='__main__':
    for p in sys.argv[1:]:
        a=json.load(open(p)); ch=0
        for x in a['parts']+a['concepts']:
            if x['id'].startswith('RU-') or 'en' not in x: continue
            n=ru_name(x['en'])
            if n!=x['name']: ch+=1; x['name']=n
        json.dump(a,open(p,'w'),ensure_ascii=False,separators=(',',':')); print(p,'changed',ch)
