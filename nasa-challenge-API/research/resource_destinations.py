from crawl_sources import *
from collect import batch
items=json.loads((ROOT/'inventory_normalized.json').read_text(encoding='utf8'))
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    for r in ex.map(lambda i:fetch('resource_'+i['id'],i['url'],750_000),items):
        print(r['id'],r.get('status'),r.get('bytes'),r.get('error',''),flush=True)
