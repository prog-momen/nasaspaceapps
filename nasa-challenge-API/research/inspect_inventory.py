from crawl_sources import *
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode
import sys
sys.stdout.reconfigure(encoding='utf8')
def norm(url):
    p=urlsplit(url);q=[(k,v) for k,v in parse_qsl(p.query,keep_blank_values=True) if not k.startswith('utm_')]
    host=p.netloc.lower().removeprefix('www.')
    path=p.path.rstrip('/')
    if host=='search.earthdata.nasa.gov' and path in ('','/search'):path=''
    if host=='worldview.earthdata.nasa.gov' and path=='/index.html':path=''
    return urlunsplit(('https',host,path,urlencode(q),p.fragment))
coverage=json.loads((ROOT/'coverage.json').read_text(encoding='utf8'))
inv={}
for i,c in enumerate(coverage,1):
    c['number']=i
    print(i,c['title'],c['resource_count'])
    for url,label in c['resources']:
        key=norm(url)
        obj=inv.setdefault(key,{'url':url,'normalized_url':key,'labels':[],'challenges':[],'source_urls':[]})
        if label not in obj['labels']:obj['labels'].append(label)
        if i not in obj['challenges']:obj['challenges'].append(i)
        if c['url']+'?tab=resources' not in obj['source_urls']:obj['source_urls'].append(c['url']+'?tab=resources')
for i,obj in enumerate(inv.values(),1):
    obj['id']='R%03d'%i
    print(obj['id'],'; '.join(obj['labels']),'|',obj['normalized_url'],'|',obj['challenges'])
(ROOT/'inventory_normalized.json').write_text(json.dumps(list(inv.values()),ensure_ascii=False,indent=2),encoding='utf8')
(ROOT/'coverage_numbered.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2),encoding='utf8')
print('unique',len(inv),'occurrences',sum(c['resource_count'] for c in coverage))
