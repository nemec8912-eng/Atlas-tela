import json,os
D='/home/claude/atlas-site/models/'
a=json.load(open(D+'atlas.json')); lo=json.load(open(D+'atlas-lo.json'))
L={p['id']:p for p in lo['parts']}
for p in a['parts']:
    q=L[p['id']]; p['lo']=[q['chunk'],q['ev'],q['evb'],q['ei'],q['eib'],q['vertexCount'],q['indexCount']]+q['q']
a['lowChunks']=lo['chunks']; a['lowTriangles']=lo['triangles']
json.dump(a,open(D+'atlas.json','w'),ensure_ascii=False,separators=(',',':')); os.remove(D+'atlas-lo.json')
print('merged lo',len(L),'lowTri',lo['triangles'])
