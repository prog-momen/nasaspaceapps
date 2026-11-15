from collect import batch
from crawl_sources import ROOT
import json

PROBES=[
('test_cmr','https://cmr.earthdata.nasa.gov/search/collections.json?short_name=MOD11C3&version=061&page_size=1'),
('test_cmr_granule','https://cmr.earthdata.nasa.gov/search/granules.json?short_name=MOD11C3&version=061&temporal=2025-01-01T00%3A00%3A00Z,2025-01-31T23%3A59%3A59Z&page_size=1'),
('test_appeears_product','https://appeears.earthdatacloud.nasa.gov/api/product?limit=1'),
('test_appeears_layers','https://appeears.earthdatacloud.nasa.gov/api/product/MOD11A2.061'),
('test_power','https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M,PRECTOTCORR&community=AG&longitude=35.26&latitude=32.22&start=20250101&end=20250107&format=JSON&time-standard=UTC'),
('test_power_monthly','https://power.larc.nasa.gov/api/temporal/monthly/point?parameters=T2M&community=AG&longitude=35.26&latitude=32.22&start=2005&end=2025&format=JSON'),
('test_gibs_tile','https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/2025-01-01/250m/0/0/0.jpg'),
('test_eonet','https://eonet.gsfc.nasa.gov/api/v3/events?limit=1&status=all'),
('test_epic','https://epic.gsfc.nasa.gov/api/natural/date/2025-01-01'),
('test_asf','https://api.daac.asf.alaska.edu/services/search/param?platform=Sentinel-1&bbox=35.2,32.1,35.3,32.3&start=2025-01-01T00%3A00%3A00Z&end=2025-01-03T00%3A00%3A00Z&output=geojson&maxResults=1'),
('test_giovanni_openapi','https://api.giovanni.earthdata.nasa.gov/openapi.json'),
('giovanni_cloud','https://giovanni.earthdata.nasa.gov/'),
('doc_appeears','https://appeears.earthdatacloud.nasa.gov/api/'),
('doc_hydrology','https://disc.gsfc.nasa.gov/information/tools?title=Hydrology%20Time%20Series'),
('doc_firms','https://firms.modaps.eosdis.nasa.gov/api/'),
('doc_hydrocron','https://podaac.github.io/hydrocron/query/'),
('doc_noaa','https://www.ncei.noaa.gov/cdo-web/webservices/v2'),
('doc_asf','https://docs.asf.alaska.edu/api/keywords/'),
('doc_harmony','https://harmony.earthdata.nasa.gov/docs'),
('doc_earthaccess','https://earthaccess.readthedocs.io/en/latest/'),
('doc_mod11','https://lpdaac.usgs.gov/products/mod11c3v061/'),
('doc_imerg','https://gpm.nasa.gov/data/imerg'),
('doc_nex','https://www.nccs.nasa.gov/data-collections/nex-gddp-cmip6/'),
('doc_prithvi','https://huggingface.co/ibm-nasa-geospatial/Prithvi-EO-2.0-300M-TL/raw/main/README.md'),
('doc_terratorch','https://raw.githubusercontent.com/IBM/terratorch/main/docs/guide/prithvi_eo.md'),
('google_speech','https://aistudio.google.com/docs/speech-generation'),
('google_transcribe','https://aistudio.google.com/docs/models/gemini-3.5-transcribe'),
('google_tts','https://aistudio.google.com/docs/models/gemini-3.8-flash-tts'),
('google_tts_lite','https://aistudio.google.com/docs/models/gemini-3.8-flash-lite-tts'),
('google_live','https://aistudio.google.com/docs/models/gemini-3.8-live'),
('google_hydrogen','https://aistudio.google.com/docs/models/gemini-4-hydrogen'),
('google_flash','https://aistudio.google.com/docs/models/gemini-3.8-flash'),
('google_lite','https://aistudio.google.com/docs/models/gemini-3.5-flash-lite'),
('google_key','https://aistudio.google.com/docs/api-key'),
('google_functions','https://aistudio.google.com/docs/function-calling'),
('google_limits','https://aistudio.google.com/docs/rate-limits'),
('google_terms','https://aistudio.google.com/docs/terms'),
]
batch(PROBES)
records=[json.loads((ROOT/(k+'.json')).read_text(encoding='utf-8')) for k,u in PROBES]
(ROOT/'probe_results.json').write_text(json.dumps([{k:v for k,v in r.items() if k!='links'} for r in records],ensure_ascii=False,indent=2),encoding='utf-8')
