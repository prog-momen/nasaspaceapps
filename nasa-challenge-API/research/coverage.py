from parse_challenges import *
from urllib.parse import urlencode

query='query Challenges($event: EncodedID, $first: Int!) { challenges(event:$event, first:$first) { totalCount edges { node { id title meta { relativeUrl } } } pageInfo { hasNextPage } } }'
url='https://api.spaceappschallenge.org/graphql?'+urlencode({'query':query,'variables':json.dumps({'event':'aWQ6NA==','first':100})})
r=fetch('official_challenges_graphql',url)
print(r.get('status'),flush=True)
data=json.loads((ROOT/'official_challenges_graphql.raw').read_bytes())
if 'errors' in data:print(data);raise SystemExit(1)
nodes=[e['node'] for e in data['data']['challenges']['edges']]
print(json.dumps(data,ensure_ascii=False,indent=2),flush=True)
from collect import batch
batch([('challenge_'+n['meta']['relativeUrl'].strip('/').split('/')[-1],urljoin('https://www.spaceappschallenge.org',n['meta']['relativeUrl'])+'?tab=resources') for n in nodes])
coverage=[]; inventory={}
for n in nodes:
    slug=n['meta']['relativeUrl'].strip('/').split('/')[-1];key='challenge_'+slug
    parse(key)
    links=json.loads((ROOT/(key+'_resources.json')).read_text(encoding='utf-8'))
    coverage.append({'id':slug,'title':n['title'],'url':urljoin('https://www.spaceappschallenge.org',n['meta']['relativeUrl']),'resource_count':len(links),'resources':links})
    for href,label in links:
        norm=href.rstrip('/')
        inventory.setdefault(norm,{'url':href,'labels':[],'challenges':[]})
        if label not in inventory[norm]['labels']:inventory[norm]['labels'].append(label)
        if slug not in inventory[norm]['challenges']:inventory[norm]['challenges'].append(slug)
(ROOT/'coverage.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'resource_inventory.json').write_text(json.dumps(list(inventory.values()),ensure_ascii=False,indent=2),encoding='utf-8')
print('TOTAL',len(nodes),'UNIQUE',len(inventory))
