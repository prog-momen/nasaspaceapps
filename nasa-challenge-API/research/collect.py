from crawl_sources import *

def batch(items):
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        for r in ex.map(lambda kv:fetch(*kv),items):
            print(r['id'],r.get('status'),r.get('bytes'),r.get('error',''),flush=True)

if __name__=='__main__':
    batch([
      ('trend','https://www.spaceappschallenge.org/2026/challenges/earth-system-trend-detective/?tab=resources'),
      ('trend_be','https://www.spaceappschallenge.org/2026/challenges/be-an-earth-system-trend-detective/?tab=resources'),
      ('google_pricing','https://aistudio.google.com/docs/pricing'),
      ('google_models','https://aistudio.google.com/docs/models'),
      ('google_index','https://aistudio.google.com/llms.txt'),
    ])
    raw=(ROOT/'challenges_2026.raw').read_text(encoding='utf-8')
    scripts=re.findall(r'<script[^>]+src="([^"]+)"',raw)
    batch([('js_'+path.split('/')[-1].split('.')[0],urljoin('https://www.spaceappschallenge.org',path)) for path in scripts])
