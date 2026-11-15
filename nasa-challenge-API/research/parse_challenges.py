from crawl_sources import *
import sys
sys.stdout.reconfigure(encoding='utf-8')

def rsc(raw):
    chunks=[]
    for match in re.finditer(r'self\.__next_f\.push\((\[.*?\])\)</script>',raw,re.S):
        try:
            arr=json.loads(match.group(1))
            if len(arr)>1 and isinstance(arr[1],str): chunks.append(arr[1])
        except Exception:pass
    return '\n'.join(chunks)

def parse(key):
    raw=(ROOT/(key+'.raw')).read_text(encoding='utf-8')
    decoded=rsc(raw)
    (ROOT/(key+'_decoded.txt')).write_text(decoded,encoding='utf-8')
    field=re.search(r'"resourcesTabContent":("(?:\\.|[^"\\])*")',decoded)
    if not field: raise ValueError('Resource field missing: '+key)
    value=json.loads(field.group(1))
    if value.startswith('$'):
        resource=re.search(r'(?:^|\n)'+re.escape(value[1:])+r':T[0-9a-f]+,\n?(.*?)(?=\n[0-9a-f]+:|$)',decoded,re.S)
        if not resource:raise ValueError('Resource payload missing: '+key)
        value=resource.group(1)
    (ROOT/(key+'_resources.html')).write_text(value,encoding='utf-8')
    p=Extract();p.feed(value)
    (ROOT/(key+'_resources.txt')).write_text('\n'.join(p.text),encoding='utf-8')
    (ROOT/(key+'_resources.json')).write_text(json.dumps(p.links,ensure_ascii=False,indent=2),encoding='utf-8')
    print(key, json.dumps(p.links,ensure_ascii=False,indent=2))

if __name__=='__main__':
    parse('trend')
    s=fetch('sitemap','https://www.spaceappschallenge.org/sitemap.xml')
    print('sitemap',s.get('status'),s.get('bytes'))
