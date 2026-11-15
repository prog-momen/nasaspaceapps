import concurrent.futures, datetime, hashlib, json, pathlib, re, ssl, time, urllib.request, urllib.error
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

ROOT=pathlib.Path(__file__).resolve().parent
ROOT.mkdir(exist_ok=True)
# Public, unauthenticated research only. The bundled Python cannot validate the
# workstation's network certificate chain. Each evidence record states this.
CTX=ssl._create_unverified_context()
class Extract(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.text=[]; self.current=None; self.skip=0
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in ('script','style'): self.skip+=1
        if tag=='a': self.current=[a.get('href',''),'']
    def handle_endtag(self,tag):
        if tag in ('script','style'): self.skip=max(0,self.skip-1)
        if tag=='a' and self.current: self.links.append(self.current); self.current=None
    def handle_data(self,d):
        if not self.skip:
            self.text.append(d)
            if self.current:self.current[1]+=d

def fetch(key,url,limit=8_000_000):
    t=time.monotonic(); rec={'id':key,'url':url,'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tls_validation':False}
    try:
        headers={'User-Agent':'EarthTrend-Research/1.0','Accept':'*/*'}
        if 'api.spaceappschallenge.org/graphql' in url:headers['apollo-require-preflight']='true'
        req=urllib.request.Request(url,headers=headers)
        try:r=urllib.request.urlopen(req,context=CTX,timeout=40)
        except urllib.error.HTTPError as e:r=e
        data=r.read(limit); rec.update(status=r.status,final_url=r.url,bytes=len(data),content_type=r.headers.get('Content-Type'),sha256=hashlib.sha256(data).hexdigest())
        (ROOT/(key+'.raw')).write_bytes(data)
        txt=data.decode('utf-8','replace'); p=Extract();p.feed(txt)
        rec['links']=[{'url':urljoin(r.url,h),'label':re.sub(r'\s+',' ',label).strip()} for h,label in p.links]
        (ROOT/(key+'.txt')).write_text('\n'.join(t.strip() for t in p.text if t.strip()) if '<html' in txt.lower() else txt,encoding='utf-8')
    except Exception as e:rec['error']=str(e)
    rec['elapsed_seconds']=round(time.monotonic()-t,3)
    (ROOT/(key+'.json')).write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding='utf-8')
    return rec

if __name__=='__main__':
    r=fetch('challenges_2026','https://www.spaceappschallenge.org/2026/challenges/')
    print(json.dumps({k:v for k,v in r.items() if k!='links'},ensure_ascii=False))
    links={a['url']:a['label'] for a in r.get('links',[]) if '/2026/challenges/' in a['url'] and a['url'].rstrip('/')!='https://www.spaceappschallenge.org/2026/challenges'}
    print(json.dumps(links,ensure_ascii=False,indent=2))
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        jobs=[ex.submit(fetch,'challenge_'+url.rstrip('/').split('/')[-1],url) for url in links]
        for j in concurrent.futures.as_completed(jobs):
            d=j.result();print(d['id'],d.get('status'),d.get('bytes'),d.get('error',''))
