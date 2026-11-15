from __future__ import annotations

import glob
import html
import json
import os
import runpy
import re
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
RESEARCH = ROOT / "research"
OUT = ROOT / "EarthTrend_Explorer_2026_APIs_Tools_Reference_AR.md"

BASE = r'''# EarthTrend Explorer — مرجع APIs والأدوات لعام 2026

**النطاق:** مشروع تحدي NASA Space Apps Challenge 2026: **<span dir="ltr">Be An Earth System Trend Detective!</span>**  
**تاريخ التحقق:** 14 نوفمبر 2026 (UTC)  
**الحالة:** مرجع بحثي/تصميمي. لا يوجد في مجلد العمل الحالي كود تطبيق أو تنفيذ للمشروع.

> هذا الملف يوثق بحثًا تقنيًا ومصادره واختباراته الصغيرة، ويفصل بين ما أدرجته NASA أو وكالة شريكة ضمن تحديات 2026، وما اختبرناه، وما نقترح بناءه. وجود رابط رسمي لا يعني أن API اختبرت أو أن استخراج البيانات نجح.

## الفهرس

1. [الملخص التنفيذي](#1-الملخص-التنفيذي)
2. [تغطية تحديات وموارد 2026](#2-تغطية-تحديات-وموارد-2026)
3. [كتالوج APIs ومصادر البيانات](#3-كتالوج-apis-ومصادر-البيانات)
4. [Gemini Developer API والخطة المجانية](#4-gemini-developer-api-والخطة-المجانية)
5. [مسار البيانات والتحليل والتنبؤ](#5-مسار-البيانات-والتحليل-والتنبؤ)
6. [عقود الأدوات التي يستدعيها Gemini](#6-عقود-الأدوات-التي-يستدعيها-gemini)
7. [نتائج الاختبارات والقيود](#7-نتائج-الاختبارات-والقيود)
8. [اختيارات النسخة الأولى وما يؤجل](#8-اختيارات-النسخة-الأولى-وما-يؤجل)
9. [الدليل التفصيلي لجميع الأدوات والموديلات المستخدمة والمقترحة](#9-الدليل-التفصيلي-لجميع-الأدوات-والموديلات-المستخدمة-والمقترحة)

## 1. الملخص التنفيذي

تطلب صفحة التحدي من الفرق بناء تطبيق تفاعلي يستخدم بيانات الاستشعار الراداري لمهمة NASA–ISRO NISAR لمتابعة نوع واحد أو أكثر من تغير سطح الأرض في مواقع حول العالم. يضع ذلك مشروع EarthTrend Explorer في نطاق الرصد والتحليل المكاني الزمني؛ وتحليل مناخي أوسع أو تنبؤ ARIMA أو Gemini هي توسعات فريق، وليست متطلبات رسمية للتحدي. [صفحة التحدي الرسمية](https://www.spaceappschallenge.org/2026/challenges/earth-system-trend-detective/)

الموارد الأربعة في تبويب التحدي هي Giovanni وHydrology Time Series وAppEEARS وNOAA Climate Data Online، إضافة إلى ورقة علمية، وثلاثة موارد شريكة (KNMI Climate Explorer، مادة إحصائية، وموارد CSA). Giovanni وAppEEARS يصلحان لاستكشاف/استخراج سلاسل، لكن لكل منهما قيود اعتماد أو تشغيل مختلفة. NASA POWER هو أسرع أساس لمثال سلاسل المناخ اليومية/الشهرية؛ وقد اختبرناه على طلبات قراءة صغيرة. ليس رابطًا مباشرًا في تبويب هذا التحدي، لكنه مدرج رسميًا في تحدي 2026 آخر. [Giovanni](https://giovanni.gsfc.nasa.gov/) · [AppEEARS API](https://appeears.earthdatacloud.nasa.gov/api/) · [POWER API](https://power.larc.nasa.gov/docs/services/api/)

**المسار العملي المقترح:** البحث في NASA CMR عن المنتج وإصداره؛ استخدام NASA POWER لنموذج أولي مناخي سريع، أو AppEEARS لعينات MODIS المؤهلة مع Earthdata Login؛ التحقق من flags والوحدات والتغطية؛ ثم حساب trend وconfidence intervals في Backend محلي؛ واستدعاء Gemini فقط لشرح النتائج المنظمة أو طلب أدوات allowlisted. لسؤال NISAR نفسه يلزم الحصول على منتجات SAR الصحيحة ومعالجتها، ولا يكفي تحويل لقطة خريطة إلى سلسلة رقمية.

**أصغر حزمة MVP موثقة:** Python 3.11+، `httpx` أو `requests`، `pandas`، `numpy`، `scipy`، `statsmodels`، `pydantic`، FastAPI للواجهة البرمجية، ومكتبة رسم مثل Plotly. أضف `earthaccess`/CMR و`xarray` فقط عندما تختار منتج NetCDF/Cloud data؛ و`rasterio`/`rioxarray` عند إدخال rasters؛ لا حاجة أولية إلى Computer Vision أو Prithvi أو Earth Engine. واجهة الكرة الأرضية والمخزن الدائم قرارات تنفيذية منفصلة.

**Gemini:** آخر فحص لصفحة النماذج الرسمية أظهر عائلة Gemini 3.8 مستقرة لبعض الاستخدامات، مع preview لبعض النماذج الأخرى. المعرّفات والحصص تتغير؛ افحص AI Studio قبل التشغيل. Free Tier لا يساوي اشتراك Gemini consumer، ولا يضمن quota موحدة أو بيانات غير مستخدمة لتحسين الخدمات. لا تدخل API key للمتصفح.

**المستودع:** يحتوي المجلد على ملفات أبحاث وجلب موارد واختبارات صغيرة، ولا يحتوي على implementation للموقع أو Backend أو أدوات Gemini. لهذا، كل بطاقة أدناه إما «مختبر في البحث» أو «مقترح» ولا توجد أداة مشروع «مستخدمة فعليًا» مثبتة من كود التطبيق.

## 2. تغطية تحديات وموارد 2026

### 2.1 المنهج وحدود التغطية

بدأ الفحص بقائمة التحديات الرسمية ذات المسار `/2026/`، والتي عادت في سجل الجلب بـ14 تحديًا. جُلبت صفحات التحديات وملفات موارد Resources لكل تحدٍ بتاريخ 14 نوفمبر 2026. سجلّ الأرشيف الداخلي لكل صفحة حالة HTTP 200 وعدد البايتات ووقت الجلب، وجرى استخراج 139 إحالة (133 رابطًا فريدًا بعد إزالة تكرار URL مع اختلاف بعض التسميات). استخدم جامع الملفات `tls_validation=false`؛ لذلك هذا دليل على استجابة HTTP ومحتوى محفوظ، وليس تحققًا مستقلًا من سلسلة شهادة TLS. محاولة فتح نطاق Space Apps مباشرة عبر موصل التصفح في هذا التشغيل أعادت 502، لذلك استخدمنا سجلات HTML المحفوظة وقائمة API الرسمية للـ14 تحديًا؛ نذكر هذا القيد بدل ادعاء تحقق TLS حي كامل. لم نستخدم قوائم تحديات 2025 بوصفها مصدر موارد 2026.

الجدول التالي يبين جميع التحديات والروابط وحالة تبويب الموارد وعدد الروابط كما استُخرجت من HTML المؤرشف. كل صفحات الموارد كانت 200 في سجل الجلب؛ قد تتغير الروابط بعد تاريخ التحقق.

### 2.2 تغطية التحديات

| التحدي (عنوان 2026 الرسمي) | صفحة التحدي | Resources | موارد مستخرجة |
|---|---|---:|---:|
'''

BASE += r'''
### 2.3 موارد تحدي Earth System Trend Detective

| المورد | الجهة/الفئة | نوعه كما أمكن التحقق | صلته بالمشروع |
|---|---|---|---|
| [Giovanni](https://giovanni.gsfc.nasa.gov/) | NASA GES DISC | واجهة ويب علمية؛ خدمات معالجة موثقة جزئيًا وتحتاج discovery/auth بحسب الوظيفة | مقارنة متغيرات وسلاسل زمنية؛ لا تعتمد على endpoint غير مثبت |
| [Hydrology Time Series](https://disc.gsfc.nasa.gov/information/tools?title=Hydrology%20Time%20Series) | NASA GES DISC | صفحة أداة/واجهة؛ API المستقلة الحالية غير مثبتة | مرجع للـhydrology؛ لا تربط التنفيذ بمسار قديم غير موثق |
| [AppEEARS](https://appeears.earthdatacloud.nasa.gov/) | NASA LP DAAC/USGS | REST API موثقة، مهام غير متزامنة ونقطة/منطقة | extraction لمنتجات مؤهلة وquality layers؛ Earthdata Login مطلوب للمهمة |
| [Climate Data Online](https://www.ncei.noaa.gov/cdo-web/) | NOAA NCEI، شريك/جهة غير NASA | واجهة ويب وAPI مستقلة تتطلب token | محطات تاريخية للتحقق أو المقارنة، مع تقييد جغرافي/حصة |
| [SeaWiFS time-series paper](https://ntrs.nasa.gov/api/citations/20090042747/downloads/20090042747.pdf) | NASA NTRS paper | PDF بحثي، ليس API | مثال منهجي على تحليل سلسلة بعيدة الاستشعار واختبار دلالة |
| [KNMI Climate Explorer](https://climexp.knmi.nl/) | شريك: KNMI/هولندا | أداة ويب تحليلية؛ ليس API للمشروع مثبتًا هنا | مقارنة مناخية مرجعية، وليست backend أساسيًا |
| [Statistical test methods](https://medium.com/@snp.kriss/statistical-test-methods-to-detect-trends-in-time-series-data-b361a0ec530b) | مورد شريك/خارجي مدرج رسميًا | مقال ويب، لا API | خلفية؛ نعتمد توثيق SciPy/المراجع العلمية في التنفيذ |
| [Guide to statistical significance](https://www.statsig.com/perspectives/a-comprehensive-guide-to-statistical-significance) | مورد خارجي مدرج رسميًا | مقال ويب، لا API | توجيه عام؛ ليس مرجعًا علميًا أساسيًا للاستدلال المناخي |
| [RADARSAT Constellation Mission data](https://donnees-data.asc-csa.gc.ca/en/dataset/rcm) | شريك: CSA | كتالوج وتنزيل ملفات | SAR كندي مكمل؛ افصل بياناته ومنتجاته عن NISAR |
| [GEO.ca](https://geo.ca/) | شريك: كندا | بوابة بيانات جغرافية؛ APIs/الخدمات بحسب dataset | محلي لكندا فقط عند الحاجة |
| [SWOT mission](https://www.asc-csa.gc.ca/eng/satellites/swot/) | NASA/CNES مع مساهمة CSA وUKSA | صفحة معلومات المهمة؛ ليست واجهة استخراج بحد ذاتها | قياسات مياه سطحية مكملة؛ السجل أقصر وتواتر المرور مداري |
| [Monitoring ecosystems from space](https://www.asc-csa.gc.ca/eng/satellites/everyday-lives/monitoring-and-protecting-our-ecosystems-from-space.asp) | شريك: CSA | صفحة تثقيفية | لا API مباشرة |
| [CSA SAR Python Tutorial](https://github.com/asc-csa/Synthetic_Aperture_Radar_Tutorial) | شريك: CSA/GitHub | مستودع تعليمي/كود | يعلّم workflows الرادار؛ افحص الترخيص والإصدارات قبل الاقتباس |

### 2.4 موارد NASA/شركاء من تحديات 2026 الأخرى ذات الصلة

الموارد التالية ليست ضمن تبويب التحدي الأساسي؛ أدرجناها لأنها ظهرت في تبويب موارد تحديات 2026 أخرى وقد تفيد المعمارية أو حالة استعمال قريبة. لا تخلط ذلك مع متطلبات التحدي.

- **NASA:** NASA Earthdata Search/CMR وASF Vertex وNISAR User Guide من *Dancing with the SARs*؛ NASA POWER وSMAP وGPM/IMERG وLandsat وMODIS/VIIRS وSRTM وECOSTRESS وGEDI وNLDAS/GLDAS من *Field Shift: Adapting Farms with NASA Data*؛ NASA FIRMS من *Harmonization of MODIS and VIIRS Hot Spots*؛ Worldview وEarthdata Search من *Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars*؛ NASA Open APIs وDONKI وOSDR/RadLab من *Build a Junior Astronaut Mission Trainer*؛ SVS/Earth Information Center ومواد GEDI من *The Earth Information Jukebox*؛ NTRS والبوابة الكوكبية وغيرها من تحديات الكواكب.
- **شركاء وكالات الفضاء:** CSA أدرجت RCM وRADARSAT-1 وSAR tutorials في عدة تحديات؛ ESA أدرجت Copernicus Data Space وSentinel-2 وERA5؛ JAXA أدرجت G-Portal؛ CONAE أدرجت كتالوج SAOCOM. وهذه موارد وكالة/بلد مستقل، ليست NASA APIs.
- **موارد حكومية/علمية أخرى ضمن قوائم التحدي:** NOAA CDO؛ USDA وUSGS وUSDA CropScape/Web Soil Survey؛ PRISM؛ FAO GAEZ؛ ECMWF/ERA5؛ ومصادر أخرى غير ناسا. لا يعني ظهور رابط خارجي في قائمة التحدي أن NASA تديره أو أن سياساته واحدة.

تفاصيل كل عنصر فريد من 133 URL، واسم كل تحدٍ أحاله، مدرجة في جرد الروابط بعد دليل الأدوات. ربطنا الموارد المتكررة بجميع التحديات التي وردت فيها. لم نستنتج أن كل عنصر صفحة ويب هو API: نوع المورد مبين لكل خدمة تقنية رئيسية في الكتالوج والملحق.

في جدول الجرد، عمود «إدراجه ضمن الموارد» يسجل القسم الذي ظهرت تحته الإحالة في صفحة التحدي، ولا يقرر الجهة المالكة؛ فقد تضع الصفحة مورد NOAA أو USGS أو مؤسسة أخرى تحت مجموعة NASA. عمود «الجهة المالكة» في بطاقة الخدمة هو إسناد الجهة التي تدير المنتج/الخدمة بعد مراجعة المصدر.

## 3. كتالوج APIs ومصادر البيانات

### 3.1 طريقة القراءة

تظهر هنا خدمات مفيدة أو ظهرت رسميًا ضمن موارد 2026، مع إضافات مقترحة موسومة بوضوح. «API» تعني endpoint موثقًا، و«واجهة» قد تكون موقعًا تفاعليًا فقط، و«مكتبة/SDK» عميل برمجي، أما تنزيل الملفات فلا يتحول تلقائيًا إلى API. وثائق المنتج هي المرجع النهائي لاسم المتغير والوحدة وQA؛ الخدمات العامة لا تفرض زمن تغطية أو دقة واحدة على كل collections.

### 3.2 قائمة المنتجات المرشحة

| المنتج/المجموعة | المتغيرات والوحدات المهمة | التغطية/الدقة/الزمن | الوصول والحالة/التحفظ |
|---|---|---|---|
| MOD11A2.061 | `LST_Day_1km`, `LST_Night_1km`، معامل قياس 0.02 K؛ الجودة `QC_*` | منذ 2000 تقريبًا، 1 km، مركب 8 أيام | AppEEARS catalog layer اختبر؛ LST سطح أرض لا حرارة هواء |
| MOD11C3.061 | `LST_Day_CMG`, `LST_Night_CMG`؛ 0.02 K قبل التحويل | منذ 2000 تقريبًا، 0.05°، شهري | CMR collection/granule metadata اختبر؛ المنتج واضح السحب |
| MOD13A3.061 | NDVI/EVI، معامل 0.0001، بلا وحدة؛ QA/reliability | منذ 2000 تقريبًا، 1 km، شهري | مرشح لمؤشر نبات، تحقّق من layer/QC قبل extraction |
| GPM IMERG V07 Monthly Final | precipitation حسب metadata في ملف المنتج (`mm/hr` أو تراكم حسب المنتج) | منذ 2000-06 تقريبًا، 0.1° شهري | لا تخلط Early/Late/Final؛ تحويل المعدل إلى تراكم يحتاج الزمن |
| GLDAS_NOAH025_M 2.1 | `Tair_f_inst` K؛ `Rainf_f_tavg` kg m⁻² s⁻¹ | منذ 2000 تقريبًا، 0.25° شهري | حقول نموذج assimilation وليست محطة رصد |
| MERRA-2 `M2TMNXSLV` 5.12.4 | `T2M` K وغيرها؛ مجموعات flux منفصلة | منذ 1980، 0.5°×0.625°، شهري | لا تخلط instant وmonthly mean أو مجموعات مختلفة |
| NASA POWER T2M / PRECTOTCORR | `T2M` °C؛ `PRECTOTCORR` mm/day (daily) | يومي من 1981 تقريبًا، اعتمادًا على variable/source؛ monthly endpoint مستقل | REST اختبر فعليًا؛ مصدر إعادة تحليل/دمج وليس محطة محلية |
| HLS L30/S30 v2 | reflectance bands وFmask؛ NDVI مشتق | 30 m؛ Landsat 8/9 من 2013 وSentinel-2 من 2015 تقريبًا، acquisition/cadence متغير | CMR/COG؛ يُفيد imagery لكن لا يغطي سلسلة 2005-2025 كاملة |
| SMAP SPL3SMP v9 | surface soil moisture m³/m³ و`retrieval_qual_flag` | من 2015 تقريبًا؛ 36 km؛ daily grid مع تغطية/مرور فعلي متغير | منتج NSIDC؛ لا يمثل root-zone تلقائيًا |
| ECOSTRESS ECO_L2T_LSTE.002 | LST K، emissivity وQC | من 2018؛ نحو 70 m؛ تغطية مرور ISS غير منتظمة | لا يُعرض كتواتر يومي أو سجل طويل |
| SRTMGL1.003 | Elevation m | مهمة 2000، قرابة 30 m بين 60°N و56°S | متغير ثابت؛ سياق تضاريسي وليس trend سنوي |
| GEDI L2A/L4 | RH metrics m وbiomass حسب المنتج | من 2019؛ footprints/مدارات ISS وتوقفات وتغطية مدارية | sampling footprints؛ لا تحوّله لخريطة مستمرة بلا معالجة |
| SWOT RiverSP D 2.0 | `wse` m و`slope` m/m وquality | من 2023؛ مرور/معالم نهرية غير يومية | Hydrocron read صغير اختبر؛ IDs/quality/version ضرورية |
| FIRMS MODIS/VIIRS | اكتشافات حرارية، FRP MW، confidence | MODIS ~1 km، VIIRS ~375 m؛ تاريخ حسب المصدر/المجموعة | API تتطلب MAP_KEY؛ hotspot لا يساوي burned area أو احتمالًا |
| NEX-GDDP-CMIP6 | `tas` K، `pr` kg m⁻² s⁻¹ وSSP ensembles | historical 1950–2014؛ projections 2015–2100، يومي 0.25° تقريبًا | **إضافة NASA مقترحة** وليست موردًا مستخرجًا من تحدي 2026؛ لم يختبر التنزيل |

تاريخ البداية أعلاه دلالة وصفية من وثائق المنتجات، وليس إثباتًا لتوفر كل أحدث granule أو نفس النسخة لكل موقع. استعلم عن holdings وإصداراته عند التنفيذ، ولا توحّد الدقة على شبكة أعلى وكأنها تضيف معلومات.

### 3.3 بطاقات الخدمات التقنية

التصنيفات المختصرة في بطاقات الملحق: **A** اكتشاف مجموعات البيانات/تنزيلها؛ **B** صور أو خرائط وطبقات tiles؛ **C** معالجة/استخراج سلسلة زمنية؛ **E** صفحة/واجهة أو SDK بلا API عامة موثقة end-to-end في هذا البحث. لا تعني **B** أنها Computer Vision؛ كما لا يظهر ضمن موارد تحديات 2026 API inference بصري جاهز لمشروعنا. GIBS يعيد tiles؛ أما فهم صور الأقمار فيتطلب نموذجًا/خوارزمية ومهمة وبيانات معايرة مستقلة. Prithvi خيار ذاتي الاستضافة لا API من موارد التحدي.

بطاقات الخدمات مفصلة في الملحق، بما فيها الجهة، المورد/التحدي الذي أشار إليها، docs/base URL والمسارات، data/auth/cost/limits/formats، مثال الطلب، الاستجابة ودليل الحالة. الخدمات التي لا تظهر فيها API عامة موثقة موصوفة كواجهة/ملف فقط.

## 4. Gemini Developer API والخطة المجانية

### 4.1 وضع النماذج وقت التحقق

تصف صفحة Google الرسمية في هذا التاريخ `gemini-3.8-flash` كنموذج مستقر، وتعرض `gemini-3.1-pro-preview` كـPreview. كما تسرد نماذج مستقرة للصوت/TTS مثل `gemini-3.8-live`, `gemini-3.8-live-extended-thinking`, `gemini-3.8-flash-tts`, `gemini-3.8-flash-lite-tts`، و`gemini-3.5-transcribe` مع `gemini-3.5-transcribe-live`. هذه الحالة قابلة للتغير: افحص [صفحة النماذج](https://ai.google.dev/gemini-api/docs/models) و[ملاحظات الإصدارات](https://ai.google.dev/gemini-api/docs/changelog) قبل تثبيت model ID.

| الوظيفة | نموذج/مسار موثق حاليًا | ما نوصي به | ملاحظات Free Tier |
|---|---|---|---|
| شرح نتائج واستدلال لغوي + صور اختيارية | `gemini-3.8-flash` (stable وFree Tier متاح بسعر صفر في صفحة pricing)؛ `gemini-3.1-pro-preview` (preview، لا Free Tier وقت الفحص) للاستدلال الأثقل | ابدأ بـFlash، وأرسل ملخصًا إحصائيًا صغيرًا لا raster خام | Free Tier لا يضمن quota ثابتة؛ Pro preview مدفوع فقط حسب السعر المنشور |
| Function Calling | `gemini-3.8-flash` يدعم function calling في docs | Gemini يطلب function call؛ الـBackend يتحقق وينفذ ثم يعيد JSON | API call مجانية/مدفوعة بحسب النموذج وحدود حسابك؛ JSON لا يجعل النموذج مصدرًا للحقائق |
| فهم الصور | `gemini-3.8-flash` متعدد الوسائط؛ إدخال الصور موثق | اختياري لشرح رسم أو صورة صغيرة؛ لا تسلمه tile لاستخراج علمي | Flash Free Tier listed؛ limits per project؛ الصورة لا تعوّض المنتج الرقمي/QA |
| تفريغ صوت محفوظ | `gemini-3.5-transcribe` | خيار منفصل بعد تجربة Arabic accuracy وخصوصية الصوت | الصفحة تصف 85+ لغة، وdiarization/timestamps؛ تحقق سعره/توفّره بالحساب |
| TTS عربي | `gemini-3.8-flash-tts` أو `gemini-3.8-flash-lite-tts` | Lite للتكلفة/السرعة، Flash للجودة؛ تحقق دعم Standard Arabic في الصفحة | Google تذكر العربية الفصحى في جدول اللغات؛ يلزم اختبار النطق المحلي. Free Tier في صفحة التسعير لا يعني غياب تخزين/سياسة استخدام |
| Live صوت/فيديو | `gemini-3.8-live` أو `gemini-3.8-live-extended-thinking` | مؤجل؛ لا حاجة له للنسخة العلمية | Gemini Live ليس واجهة realtime transcription نفسها؛ الأسعار والحصص منفصلة حسب النموذج |

في صفحة التسعير التي فُحصت 14 نوفمبر 2026، يظهر Standard Free Tier بسعر صفر لنموذج `gemini-3.8-flash` ولـTTS `gemini-3.8-flash-tts` و`gemini-3.8-flash-lite-tts`، وكذلك `gemini-3.5-transcribe` و`gemini-3.8-live`. في Paid Standard حتى 31 ديسمبر 2026، السعر المنشور لـFlash هو $0.75/مليون input tokens و$3.75/مليون output tokens؛ لـTTS Flash $0.50/مليون text input و$9/مليون audio output، ولـTTS Lite $0.50 text و$6 audio؛ لـTranscribe تقديري $0.003/دقيقة audio و$0.002/دقيقة text output؛ Live يقدّر $0.005/دقيقة audio input و$0.018/دقيقة audio output (مع تسعير نص/صورة منفصل). تعلن الصفحة أن أسعار بعض هذه النماذج سترتفع في 1 يناير 2027؛ لا تنقل هذه الأسعار تلقائيًا إلى preview model أو tier آخر. Search grounding يعرض 5,000 طلب مجاني شهريًا مشتركًا لنماذج Gemini 3+ ثم $14 لكل 1,000 search requests، مع سقف يومي منشور؛ لا تفعّله في MVP. [Pricing source](https://ai.google.dev/gemini-api/docs/pricing).

الـFree Tier قد يعامل البيانات على نحو مختلف عن المدفوع؛ صفحة التسعير الحالية تبيّن ممارسات استخدام البيانات حسب tier والنموذج: عمود Free Tier يذكر أن الطلبات قد تستخدم لتحسين المنتجات، بينما Paid يذكر عدم استخدامها لهذا الغرض. راجع [التسعير الحالي](https://ai.google.dev/gemini-api/docs/pricing) و[شروط استخدام Gemini API](https://ai.google.dev/gemini-api/terms). لا ترسل بيانات شخصية أو أسرار مستخدم للصوت دون سياسة مناسبة. الحدود الحالية تظهر للمشروع في [AI Studio Rate Limits](https://ai.google.dev/gemini-api/docs/rate-limits)؛ هي per-project ومرتبطة بالنموذج/المنطقة/الرصيد وتتغير، لذا لا نثبت رقم RPM/RPD عام هنا.

### 4.2 المفتاح والفوترة

1. أنشئ/اختر مشروعًا في [Google AI Studio](https://aistudio.google.com/)، ثم أنشئ Gemini API key من صفحة API Keys.
2. خزّن المفتاح محليًا أو في مدير أسرار Backend، مثل متغير بيئة `GEMINI_API_KEY`. لا ترسله في المحادثة، ولا تضعه في Git أو HTML أو JavaScript للمتصفح.
3. يقرأ Backend المفتاح من البيئة (`os.environ["GEMINI_API_KEY"]`)؛ لا تعرّضه في logs أو الاستثناءات.
4. راقب usage وlimits في AI Studio/Billing؛ لا تفعّل فوترة إلا بعد قرار واعٍ.

اشتراك تطبيق Gemini للمستهلك منتج منفصل عن مفتاح/حصص Gemini Developer API. وجود اشتراك Google AI في التطبيق لا يمنح تلقائيًا أرصدة API، ووجود Free Tier API لا يعني الاشتراك المدفوع في التطبيق.

### 4.3 أدوات Google المدمجة

Function calling قدرة ربط دوال backend؛ هي ليست أداة Google جاهزة لجلب بيانات NASA. Google Search grounding وURL Context أدوات إضافية في بعض النماذج/tiers، وقد تكون لها رسوم/حصة منفصلة؛ لا نعتمدها لمصدر القياس العلمي. لا تخلط معها Code Execution أو File Search أو Maps. لأرقام البيئة، بيانات NASA المحددة هي المصدر، والحساب داخل مشروعنا هو المرجع. راجع جداول [التسعير](https://ai.google.dev/gemini-api/docs/pricing) لكل built-in tool قبل تشغيلها.

## 5. مسار البيانات والتحليل والتنبؤ

### 5.1 جلب البيانات والتحقق

1. **حدد سؤالًا وقياسًا:** مثلا متوسط درجة حرارة الهواء الشهرية أو LST أو NDVI. لا تخلط معنى كل متغير.
2. **اكتشف المنتج:** CMR Collection API (`short_name`, `version`, temporal range, bbox/point)؛ تحقق من الجهة المنتجة وDOI والإصدار ومتى تبدأ/تنتهي التغطية.
3. **استخرج عينة صغيرة:** POWER نقطة أو AppEEARS point لمنتج مدعوم. لمنطقة، اطلب منطقة أصغر أولًا أو حمّل COG/NetCDF subsets عبر آلية موثقة.
4. **تحقق من metadata قبل القيم:** units، scale/offset، fill values، calendar/time zone، QA flags، coordinate reference system، cadence، footprint، licensing.
5. **أبقِ الفجوات كما هي:** لا تملأ NaN تلقائيًا. أظهر نسبة missing/valid، وسبب الاستبعاد، وما إذا كان interpolation استُخدم مع mask منفصل.
6. **وحّد شبكة التحليل علميًا:** تطابق الإسقاط والدقة/التقويم قبل المزج. لا تعيد sampling لمجرد توحيد العرض. احسب متوسط مضلع بأوزان مساحة الخلية عندما تختلف مساحة الخلايا، لا متوسطًا عاديًا للبكسلات جغرافيًا.
7. **Cache/source lineage:** احفظ request params، endpoint، وقت الجلب، إصدار المنتج، مرجع DOI/URL، checksum للملف، وحدات الأصل والتحويل، flags والاستبعادات، خوارزمية الإصدار وseed عند الاقتضاء. لا تحفظ Earthdata credentials أو Gemini key في cache.

**المكتبات الضرورية بحسب المدخلات:** `pandas` و`numpy` للجدول والحساب؛ `scipy.stats` للاختبارات الأساسية؛ `statsmodels` لـARIMA/SARIMA؛ `xarray` لسلاسل NetCDF متعددة الأبعاد؛ `rasterio` و`rioxarray` لـGeoTIFF/COG وCRS؛ `geopandas` فقط لعمليات vector/intersection؛ `earthaccess` اختياري لعميل Earthdata/CMR. `scikit-image` أو PyTorch لا يضافان قبل تحديد مهمة imagery واختبارها.

### 5.2 Trend Analysis

- احسب coverage وعدد المواسم/السنوات الصالحة أولًا. اعرض خطًا وunit لكل decade/year، وبيّن المجال الزمني الفعلي.
- Linear regression يعطي ميلًا بوحدة متغير/زمن، لكنه يفترض شكلًا خطيًا وبقايا مناسبة؛ استخدم عدم اليقين وفحص البقايا، ولا تستنتج causal attribution.
- Mann–Kendall يفحص اتجاهًا رتيبًا، لكنه يتأثر بالموسمية والارتباط التسلسلي. للبيانات الموسمية استخدم seasonal Mann–Kendall عند ملاءمته؛ صحّح autocorrelation أو استخدم اختبارًا متينًا مثل trend-free pre-whitening مع توثيق الاختيار، ولا تنفذ تعديلًا آليًا على كل سلسلة.
- Sen’s slope وسيط الميول الزوجية ومتانته أعلى لبعض القيم الشاذة؛ فاصل الثقة يحتاج إجراءً صالحًا مع autocorrelation وطول العينة.
- anomaly = انحراف عن baseline معلن (مثلا متوسط 1991–2020 إذا كان المصدر يملك تغطية صالحة)، مع معالجة الشهر/الموسم؛ لا تجعل خط أساس تلقائيًا يتضمن مستقبلًا لا ينتمي للتحليل.
- عند اختبار مواقع/متغيرات/بكسلات كثيرة، استخدم تصحيح تعدد الاختبارات (مثل Benjamini–Hochberg FDR) أو صرّح بأن p-values استكشافية. راعِ التداخل المكاني، الذي يجعل الاختبارات غير مستقلة.
- لا توجد عتبة عدد سنوات واحدة تصلح لكل cadence. كقاعدة تصميمية تحفظية وليست معيار NASA: trend شهري موسمي يحتاج عدة دورات سنوية كاملة (مثل 10 سنوات صالحة كبداية استكشاف) ومعدل missing معقول. الحد النهائي يقرره power/variability/design، وتُرفض الدلالة عند قصور البيانات.
- صنّف النتيجة: اتجاه (slope)، دلالة إحصائية (p/CI)، ارتباطات، سببية، وتنبؤات كيانات مختلفة. correlation لا تثبت causation، ولا يثبت slope وحده سبب التغير.

### 5.3 Forecasting باستخدام ARIMA

ARIMA(p,d,q) يُقدّر ملاءمة من بيانات زمنية؛ لا ينزل وزنًا ثابتًا. `statsmodels.tsa` مناسبة لـARIMA وSARIMAX.

- ARIMA لسلسلة أحادية بعد تثبيت التواتر ومعالجة الاتجاه/الفروق؛ SARIMA يضيف موسمية `(P,D,Q,s)` مثل 12 لسلسلة شهرية مع دورة سنوية؛ لا تفرض إعدادًا قبل تحليل ACF/PACF/الموسمية.
- SARIMAX يضيف exogenous regressors، ويلزم قيم مستقبلية لهذه المتغيرات أو سيناريوهات مستقبلية موثقة؛ لا تستخدم قيم test مستقبلية لاختيار النموذج.
- اختبر split زمنيًا دون shuffle، ثم rolling-origin أو expanding-window backtesting. كل fit/preprocessing/hyperparameter search يتم داخل كل نافذة تدريب لمنع تسرب المستقبل.
- قارن baseline مثل last-value Naive وSeasonal Naive. أبلغ MAE وRMSE (وMASE إذا أُحسن تعريف seasonal denominator). لا تستخدم MAPE عندما تقترب القيم من الصفر أو تكون سالبة.
- احتفظ بفترات تنبؤ، واختبر التغطية الفعلية على held-out windows. إذا لم يتغلب النموذج على baseline أو كان السجل قصيرًا/متقطعًا، لا تصدر توقعًا موثوقًا. ARIMA القصير المدى ليس إسقاطًا مناخيًا لعقود؛ للإسقاطات المناخية الطويلة استخدم CMIP6/NEX سيناريوهات ensembles مع تفسير مستقل.
- CPU/RAM: السلاسل المنفردة الصغيرة ممكنة على CPU عادي. الوقت والذاكرة يتزايدان مع عدد النقاط، orders، windows، والـensemble؛ raster pixel-wise modeling قد يصبح مكلفًا ويحتاج tiling/parallelization. لا نعطي أرقام موارد كقياس لمشروع لم ينفذ.

### 5.4 Prithvi / Computer Vision

مسار اختياري فقط. **Prithvi-EO-2.0** نموذج أساس geospatial pretrained، وليس خدمة API مستضافة تلقائيًا ولا كاشف حرائق/فيضانات جاهزًا. لا يثبت الاحتياج الحالي بالتحدي إلى imagery classifier إذا كان السؤال تحليل NISAR time series أو datasets رقمية. قبل اختياره، عين المهمة المحددة، المنتج/الحزم والتواريخ/المعالجة المطلوبة، fine-tuned checkpoint للمهمة ومرجعية labels، طريقة تحويل مخرجات tensor إلى قياس مع validated metrics، GPU/VRAM، ترخيص النموذج والبيانات، وقابلية التشغيل. لا نعد embeddings تقريرًا علميًا. رابط المشروع الرسمي والـweights: [IBM/NASA Prithvi](https://huggingface.co/ibm-nasa-geospatial)؛ لا API عامة مستضافة جرى إثباتها لهذا المشروع. NISAR SAR يتطلب فهم نطاق الرادار/الاستقطاب والمعالجة ومهمة متخصصة؛ لا تمرر Landsat RGB إلى نموذج imagery باعتباره بديل NISAR.

## 6. عقود الأدوات التي يستدعيها Gemini

### 6.1 مبادئ العقد والتنفيذ

كل الأداة تنفذها خدمة Backend موثوقة، لا JavaScript في المتصفح. Gemini يقرر طلب function call ويرسل حقولًا مقيدة؛ يتحقق Pydantic من القيم، ويمنع URL arbitrary، وحجم geometry، والاستعلامات غير المسموح بها. backend يعيد compact result IDs وإحصاءات وsource lineage إلى النموذج. البيانات الضخمة تظل في object store/cache وتُنقل بالمعرف. افرض timeout وrate limits وretry exponential backoff عند 429/5xx مع `Retry-After`، وcache key يتضمن إصدار المنتج والمعلمات.

| الأداة | ماذا تفعل | مدخلات أساسية | مخرجات أساسية | مكان/تكامل |
|---|---|---|---|---|
| `search_datasets` | اكتشاف collections المتوافقة | `variable`, `bbox/point`, `start`, `end`, cadence | `dataset_id`, title, provider, units/QA summary, DOI, granule availability | Backend → CMR/POWER/AppEEARS catalog |
| `fetch_timeseries` | طلب سلسلة point/area وتنظيمها | `dataset_id`, `variable`, geometry, dates, cadence, region reducer | `series_id`, timestamps, values/units, coverage, source refs | Backend → POWER أو AppEEARS async job أو NASA files |
| `validate_timeseries` | QA/time/unit/missing checks | `series_id`, QA policy, expected cadence | valid counts, missing fractions, QC/exclusion metadata, warnings | Backend/local `pandas`/`xarray` |
| `analyze_trend` | descriptive + linear/MK/Sen | `series_id`, test, seasonality, baseline | slope/unit/time, CI, p, N, method assumptions/warnings | Backend `numpy`/`scipy`/`statsmodels` |
| `detect_anomalies` | baseline-adjusted seasonal anomalies | `series_id`, reference period, method | anomaly series ID, baseline, flagged dates and threshold | Backend؛ لا يغير raw data |
| `forecast_timeseries` | rolling validation + forecast | `series_id`, horizon, frequency, seasonal period, exog IDs | forecast, interval, backtest metrics, baseline comparison, reliability status | Backend `statsmodels`; no LLM-generated numbers |
| `generate_chart` | رسم نتيجة محفوظة | `result_id`, chart type, language, units | chart ID/URL, alt text, citation stamp | Backend Plotly/renderer |
| `generate_speech` | TTS لنص ملخص موافق عليه | `text`, `language`, `voice/model` | audio reference, format, duration, model ID | Backend → Gemini TTS اختياري |
| `analyze_satellite_imagery` | inference مهمة raster محددة فقط | `asset_id`, bands, product version, mask, model/task ID | raster/metrics + validation + provenance | لاحقًا على worker/GPU؛ موقوف حتى إثبات الحاجة |

### 6.2 أمثلة JSON مختصرة

```json
{
  "name": "analyze_trend",
  "arguments": {
    "series_id": "ts_7f8d2",
    "method": "sen_mann_kendall",
    "seasonal_period": 12,
    "confidence_level": 0.95
  }
}
```

```json
{
  "status": "ok",
  "result_id": "trend_31c0",
  "variable": "T2M",
  "units": "degC/year",
  "sen_slope": 0.021,
  "confidence_interval": [0.008, 0.034],
  "p_value": 0.004,
  "n_valid": 228,
  "period": ["2005-01", "2023-12"],
  "source": [{"provider": "NASA POWER", "dataset": "MERRA2", "retrieved_at": "2026-11-14"}],
  "warnings": ["Exploratory trend; not causal attribution"]
}
```

الأرقام أعلاه **مثال على شكل العقد فقط وليست نتيجة اختبار أو تحليل موقع**. مخرجات كل أداة تشمل `status`, `result_id`, `units`, `warnings`, و`source`. الأخطاء machine-readable: `INVALID_ARGUMENT`, `UNKNOWN_DATASET`, `AUTH_REQUIRED`, `UPSTREAM_TIMEOUT`, `RATE_LIMITED`, `NO_DATA`, `INSUFFICIENT_COVERAGE`, `QC_REJECTED`, `MODEL_FAILED`; يرد النموذج للمستخدم بمعنى الخطأ ولا يخترع قيمة بديلة. حدود أولية تصميمية: bbox واحدة حتى 5°×5° أو نقطة، زمن request للـsync 30s، AppEEARS tasks async مع polling backoff، لا أكثر من نتيجة صغيرة للنموذج، raster/artifact أقل من limit موثق للخدمة. ضع limits الدقيقة في config واختبرها قبل الإطلاق.

### 6.3 Function calling flow

1. أرسل system instructions + tool schemas + سؤال المستخدم إلى نموذج Gemini.
2. إذا طلب function call، تحقّق من JSON، صلاحية dataset/user وrate/size limits؛ Gemini لا يستدعي API NASA مباشرة.
3. شغّل المهمة محليًا أو في worker؛ خزّن artifact والمصدر/الـprovenance.
4. أعد نتيجة منظمة ومضغوطة إلى Gemini ليستعملها في صياغة شرح عربي/إنجليزي.
5. عرض الرسم/الجدول مع المصدر والوحدات وconfidence والقيود، دون السماح للنص المُولّد أن يغيّر الأرقام.

## 7. نتائج الاختبارات والقيود

الاختبارات المسجلة في `research/test_*` داخل workspace أُجريت بتاريخ 14 نوفمبر 2026. هي طلبات GET/قراءات صغيرة وليست load/performance tests. قيود TLS في بعض بيئات البحث مذكورة في ملفات السجل؛ لا نستخدمها كدليل اعتماد تشغيلي.

| الخدمة/المحاولة | النتيجة المسجلة | ما الذي يثبته وما لا يثبته |
|---|---|---|
| NASA POWER daily (طلب مباشر بتاريخ 2026-11-14) | GET لنقطة 35.26E, 32.22N، 1–3 يناير 2025، `T2M,PRECTOTCORR` عاد 200 وJSON: `T2M`=10.70,10.43,10.70 °C؛ `PRECTOTCORR`=0.08,0,0 mm/day؛ source MERRA2؛ time standard LST؛ API v2.10.3 | طلب عام صغير يعمل؛ لا تحقق مستقل من القياس الأرضي أو من دقة كل منتج. [Daily API docs](https://power.larc.nasa.gov/docs/services/api/temporal/daily/) |
| NASA POWER monthly | أرجع 21 قيمة ملخص سنوي `200513`… مع بيانات شهرية بسبب `ANN`؛ عولج parser لاستبعاد الملخص السنوي من 252 شهرًا | يُظهر ضرورة فهم مفاتيح الزمن؛ لا تستخدم suffix 13 كشهر حقيقي |
| CMR collections | GET `short_name=MOD11C3&version=061&page_size=1` أعاد 200، collection `C2565788897-LPCLOUD`, `time_start=2000-02-01T00:00:00Z`؛ سجل البحث يحفظ كذلك granule metadata | اكتشاف metadata العامة نجح؛ تنزيل محمي لم يختبر. [CMR API](https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html) |
| AppEEARS catalog/layers | `/product` وproduct layer metadata لـMODIS متاحة | catalog فقط؛ login/task/bundle يحتاج Earthdata credentials ولم يختبر |
| Hydrocron / SWOT | قراءة صغيرة لـSWOT RiverSP D version 2.0 | لا يثبت trend أو التغطية الشاملة؛ quality/version تبقى أساسية |
| GIBS tile | tile واحدة عادت صورة bytes من NASA GIBS | خدمة imagery/tile فقط؛ ليست Computer Vision ولا استخراج measurement |
| EONET v3 | GET أحداث صغير ناجح | أحداث/metadata وليست time series مناخية |
| EPIC | metadata يوم واحد | لم ينفذ inference أو تنزيل batch كامل |
| SVS API | صفحة/بيانات media metadata | لا يعني تشغيل كل الفيديو أو أن الصور تحوي بيانات قابلة للتحليل |
| ASF Search | استعلام بحث صغير نجح بعد حذف `Content-Type` غير المناسب | لا تنزيل NISAR ولا SAR preprocessing |
| NOAA CDO | docs مقروءة، تحتاج token | غير مختبرة بسبب غياب مفتاح آمن |
| FIRMS | API docs موجودة؛ يتطلب MAP_KEY | لم يختبر data response لأن المفتاح غير متاح |
| Giovanni / Data Rods | واجهة موجودة؛ endpoints احتمالية أعادت 403 أو لم يثبت لها عقد API | لا نقول «API تعمل»؛ استخدم AppEEARS/CMR/POWER حتى إثبات المسار |
| Gemini Developer API | لم يختبر API call في هذا البحث ولم يدخل أي مفتاح | أسماء/حصص مأخوذة من الوثائق الرسمية بتاريخ التحقق، وليست نتيجة تشغيل |
| NEX-GDDP-CMIP6 | وثائق THREDDS والسياق متاحان؛ لم ينزل ملف/سيناريو | إضافة مقترحة غير مختبرة |

لا توجد اختبارات لنموذج trend على series حقيقية في هذا العمل، ولا backtest أو قياس زمن/VRAM لتطبيق EarthTrend. أمثلة slope/tool response هنا توضيحية وليست نتائج علمية.

## 8. اختيارات النسخة الأولى وما يؤجل

### MVP

- سؤال محدد: اتجاه متغير NASA واحد أو اثنين على نقطة/منطقة؛ اجعل الإدخال من اختيار واضح.
- NASA POWER daily/monthly لتجربة سريعة؛ CMR للبحث عن products؛ AppEEARS عند الحاجة إلى مؤشرات MODIS ونجاح Earthdata authentication.
- `pandas`, `numpy`, `scipy`, `statsmodels`, FastAPI, Pydantic، renderer للرسوم. خزن raw response + provenance وQA.
- Linear slope وMann–Kendall/Sen فقط عندما تغطي البيانات الشروط؛ anomaly baseline صريح؛ قول «غير كافٍ» عند missing قصير.
- Gemini Function Calling/شرح النتائج اختيارية، تبقى كل الأرقام محسوبة في Python. للمنافسة قد يكفي تقرير محدد بواجهة بلا LLM.
- مفتاح Google وEarthdata/FIRMS/NOAA عند الحاجة هي بيانات اعتماد خارج المشروع؛ تحكم بها في backend ولا تُضمّن في repo.

### يؤجل حتى يتأكد الاحتياج

- Prithvi/Computer Vision؛ يحتاج مهمة محددة، labels/validation، ومعالجة raster/GPU.
- NEX-GDDP-CMIP6 للإسقاطات طويلة الأجل؛ ذلك منتج scenario climate، وليس امتداد ARIMA.
- SAR/NISAR production pipeline: تحديد product level/collection والحزم/المدار والـQA، والتصحيح/المعايرة والتداخل وإزالة التداخل المداري بحسب مهمة التغير، ثم مرجع تحقق. SAR is not interchangeable with optical NDVI.
- Google Earth Engine؛ اعتماد وproject وOAuth وحصص وشروط استخدام منفصلة؛ لا يلزم للـpoint MVP.
- Live API وTTS وإدخال صور المستخدم ومكونات الخرائط المتقدمة؛ كل منها تكلفة/مخاطر تكامل لا يفرضها التحليل الأولي.

## 9. الدليل التفصيلي لجميع الأدوات والموديلات المستخدمة والمقترحة

### 9.1 جدول الأدوات والموديلات

الجدول يوجز كل service/card في كتالوج البيانات، ثم تليه بطاقة تفصيلية. «مختبَر في البحث» لا يعني مستخدمًا فعليًا داخل تطبيق غير موجود.

| الرمز | الاسم | التصنيف | الحالة |
|---|---|---|---|
'''

def resource_records():
    return json.loads((RESEARCH / "resource_inventory.json").read_text(encoding="utf-8"))

def coverage_records():
    return json.loads((RESEARCH / "coverage.json").read_text(encoding="utf-8"))

def chall_slug_map():
    return {Path(f).stem.replace("challenge_", ""): json.loads(Path(f).read_text(encoding="utf-8"))
            for f in glob.glob(str(RESEARCH / "challenge_*_resources.json"))}

def is_status_tested(status: str) -> bool:
    s = status.lower()
    return any(x in s for x in ("تم اختبار", "اختبر", "اختبر فعليًا", "تم جلب", "تم اختبار", "نجح"))

def services_and_datasets():
    db = runpy.run_path(str(RESEARCH / "catalog_data.py"))
    return db["SERVICES"], db["DATASETS"]

def section_for_url(html_path: Path) -> dict[str, str]:
    class Parser(HTMLParser):
        def __init__(self):
            super().__init__(); self.heading = "NASA Data & Resources"; self.in_h = False; self.anchor = None; self.pairs = {}; self.partner_mode = False
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag in ("h2", "h3"):
                self.in_h = tag
            if tag == "a" and attrs.get("href"):
                self.anchor = [attrs["href"], ""]
        def handle_data(self, data):
            if self.in_h and data.strip():
                if self.in_h == "h2":
                    self.heading = data.strip()
                    self.partner_mode = "partner" in self.heading.lower()
                elif self.partner_mode:
                    self.heading = "شريك: " + data.strip()
            if self.anchor is not None: self.anchor[1] += data
        def handle_endtag(self, tag):
            if tag in ("h2", "h3"): self.in_h = False
            if tag == "a" and self.anchor is not None:
                url, label = self.anchor
                section = self.heading if self.partner_mode else "NASA Data & Resources"
                self.pairs[url.rstrip("/")] = section
                self.anchor = None
    p = Parser()
    p.feed(html_path.read_text(encoding="utf-8", errors="replace"))
    return p.pairs

def write():
    coverage = coverage_records()
    coverage_rows = "".join(
        f"| <span dir=\"ltr\">{html.escape(c['title'])}</span> | [{c['url']}]({c['url']}) | HTTP 200 في السجل، HTML محفوظ | {c['resource_count']} |\n"
        for c in coverage
    )
    content = [BASE.replace(
        "|---|---|---:|---:|\n\n### 2.3 موارد تحدي Earth System Trend Detective",
        "|---|---|---:|---:|\n" + coverage_rows + "\n### 2.3 موارد تحدي Earth System Trend Detective",
        1,
    )]
    if content[0] == BASE:
        raise RuntimeError("Coverage insertion point not found in document template")
    content.append("\n### 9.2 بطاقات APIs والخدمات\n\n")
    services, datasets = services_and_datasets()
    for s in services:
        tested = is_status_tested(s["status"])
        state = "مختبَر في البحث" if tested else "موثق/مرشح؛ الاختبار محدود أو لم يجر"
        content.append(f"| {s['id']} | {s['name']} | {s['category']} | {state} |\n")
    content.append("\n")
    for s in services:
        tested = is_status_tested(s["status"])
        state = "مختبَر في هذا البحث" if tested else "مقترح/موثق؛ لم يُختبر end-to-end"
        fields = [
            ("التصنيف", s["category"]), ("الحالة", state), ("الجهة المالكة", s["owner"]),
            ("مرجع موارد التحدي", s["listing"]), ("وثائق المطورين", f"[{s['docs']}]({s['docs']})"),
            ("Base URL / الرابط", f"[{s['base']}]({s['base']})"), ("المسارات/طريقة الاستخدام", s["paths"]),
            ("الوظيفة والملاءمة", s["purpose"]), ("البيانات/المدخلات", s["data"]),
            ("المصادقة", s["auth"]), ("المجانية/التكلفة", s["cost"]), ("الحدود والقيود", s["limits"]),
            ("الصيغ", s["formats"]), ("مثال الطلب", "```text\n" + s["example"] + "\n```"),
            ("مثال الاستجابة", "```text\n" + s["response"] + "\n```"),
            ("دليل التحقق", s["status"]), ("البديل", s["alternative"]),
        ]
        content.append(f"#### {s['id']} — {s['name']}\n\n")
        for k, v in fields:
            content.append(f"- **{k}:** {v}\n")
        content.append("\n")
    content.append("### 9.3 تفاصيل المنتجات وقراءة الوحدات\n\n")
    content.append("| المجموعة | الجهة/المنتج | layers/units | coverage | طريقة الوصول | تحذير | مصدر رسمي |\n|---|---|---|---|---|---|---|\n")
    for d in datasets:
        # tuples are intentionally maintained as a compact editorial source in catalog_data.py
        code, owner, vars_, coverage_, access_, caveat_, url = d
        vals = [code, owner, vars_, coverage_, access_, caveat_, f"[{url}]({url})"]
        content.append("| " + " | ".join(str(x).replace("|", "\\|").replace("\n", " ") for x in vals) + " |\n")
    content.append(r'''

### 9.4 خوارزميات ومكتبات النواة

#### `pandas`

- **التصنيف/الحالة:** Python library؛ مقترح لنسخة أولى، غير مثبت كاعتماد تطبيق.
- **الوظيفة/السبب:** جدولة timestamps، resampling/aggregation، missingness، joins، وبناء جداول series.
- **مدخل/مخرج:** DataFrame فيه `time,value,units,quality_flag` → filtered/aggregated DataFrame مع أعمدة موثقة. لا تُسقط QA أو missing silently.
- **التشغيل/التكامل:** `pip install pandas`; داخل Backend قبل التحليل؛ [docs](https://pandas.pydata.org/docs/).
- **التكلفة/المتطلبات/القيود:** مفتوحة المصدر؛ CPU/RAM بحسب rows؛ لا تفتح NetCDF/raster متضخم كجدول مسطح بلا chunking.
- **بديل:** `xarray` للبيانات متعددة الأبعاد و`polars` لجداول كبيرة إذا ثبتت الحاجة.

#### `NumPy`

- **التصنيف/الحالة:** Python numerical library؛ مقترح.
- **الوظيفة:** arrays، vectorized transforms، summaries/units-aware calculations (مع توثيق التحويل يدويًا).
- **مثال:** `values = np.asarray(valid_values, dtype=float)` بعد قناع quality/missing صريح.
- **تشغيل/تكلفة/قيود:** `pip install numpy`; مفتوحة المصدر وCPU؛ الحساب العددي لا يحمل وحدات تلقائيًا.
- **مصدر:** [NumPy documentation](https://numpy.org/doc/).

#### `SciPy`

- **التصنيف/الحالة:** مكتبة إحصاء/تحسين؛ مقترحة؛ لا اختبارات اتجاه نفذت في المشروع.
- **الوظيفة:** اختبارات إحصائية مثل Mann–Kendall (قد تحتاج package موثوقة إضافية) واختبارات اتجاه/فواصل وفق assumptions.
- **مثال:** فحص اتجاه باستخدام `scipy.stats.linregress(x_time, values)` بعد اختيار الفترة والتحقق من الاستقلالية/البقايا.
- **حدود:** الدلالة الاسمية لا تعالج تلقائيًا الموسمية أو autocorrelation أو تعدد الاختبارات.
- **تشغيل/مصدر:** `pip install scipy`; [SciPy stats docs](https://docs.scipy.org/doc/scipy/reference/stats.html).

#### `statsmodels`

- **التصنيف/الحالة:** إحصاء/forecasting؛ مقترحة؛ لم يجر fit أو backtest هنا.
- **الوظيفة:** `ARIMA`, `SARIMAX`, seasonality, confidence intervals، تشخيص البقايا.
- **مثال:** `from statsmodels.tsa.arima.model import ARIMA; fit = ARIMA(train, order=(p,d,q)).fit()`؛ اختَر hyperparameters داخل windows التدريب فقط.
- **تكلفة/قيود:** مفتوحة المصدر؛ CPU كافٍ غالبًا لسلاسل منفردة؛ iterations/search عديدة ترفع الزمن. ليس model weights ثابتًا.
- **مصدر:** [statsmodels time-series docs](https://www.statsmodels.org/stable/tsa.html).

#### `xarray`

- **التصنيف/الحالة:** NetCDF / multidimensional arrays؛ اختياري عند تنزيل هذه الصيغ.
- **الوظيفة:** حفظ أبعاد `time/lat/lon/band`, coordinates, attrs والوحدات، القراءة chunkwise.
- **مثال:** `ds = xr.open_dataset(path, chunks={"time": 12})` ثم اختيار مكان/وقت. راجع calendars وattrs قبل التحويل.
- **قيود:** dask/chunking قد يلزمان لبيانات كبيرة؛ لا يمحو need CRS/reprojection.
- **مصدر:** [xarray docs](https://docs.xarray.dev/).

#### `rasterio` / `rioxarray`

- **التصنيف/الحالة:** GeoTIFF/COG geospatial raster؛ اختياري للخرائط/imagery.
- **الوظيفة:** قراءة نافذة raster، affine/CRS/nodata، masking/reprojection موثق.
- **مثال:** `with rasterio.open(path) as src: window = from_bounds(*bbox, transform=src.transform)`؛ تحقق CRS وbounds.
- **تكلفة/قيد:** مفتوحة المصدر؛ ملفات raster كبيرة تزيد RAM/disk/IO؛ إعادة الإسقاط تعيد التعيين ولا تحسن دقة القياس.
- **مصادر:** [Rasterio](https://rasterio.readthedocs.io/) · [rioxarray](https://corteva.github.io/rioxarray/).

#### `GeoPandas`

- **التصنيف/الحالة:** vector GIS Python library؛ اختياري إذا طلب المستخدم polygon/administrative boundary.
- **الوظيفة:** polygons، CRS transformations، spatial joins وarea calculations.
- **مثال:** `gdf = gdf.to_crs(equal_area_crs); area = gdf.geometry.area`؛ المساحة الجغرافية تتطلب CRS مناسبًا.
- **قيود:** geometry topology وCRS/time slicing تحتاج معرفة GIS؛ لا تستخدم lat/lon planar area.
- **مصدر:** [GeoPandas docs](https://geopandas.org/en/stable/).

#### Mann–Kendall + Sen’s slope

- **التصنيف/الحالة:** طرائق تحليل إحصائي؛ مقترحة مشروطة وليست APIs/نموذج AI.
- **المدخل/المخرج:** أزمنة وقيم مرتبة مع cadence؛ p/statistic وSen slope (unit per time) وفاصل CI إذا أمكن.
- **الدور:** monotonic trend/robust magnitude؛ راعِ ties، seasonality، autocorrelation، missing timestamps وتعدد الاختبارات.
- **التشغيل/التكلفة:** CPU خفيف لسلسلة واحدة؛ اختبارات آلاف البيكسلات ترفع العمل؛ استخدام `pyMannKendall` ممكن بعد تثبيت/مراجعة الإصدار والترخيص.
- **مصادر:** [Hamed & Rao 1998 (serial correlation)](https://doi.org/10.1016/S0022-1694(97)00125-X)؛ [Hirsch, Slack & Smith 1982](https://doi.org/10.1029/WR018i001p00107).

#### ARIMA / SARIMA / SARIMAX

- **التصنيف/الحالة:** خوارزميات time-series؛ تقييم/توصية مشروطة، غير منفذة.
- **المدخل/المخرج:** سلسلة منتظمة/متغيرات خارجية؛ fitted params, forecast, intervals, diagnostics.
- **الدور:** ARIMA `(p,d,q)`؛ SARIMA موسمي؛ SARIMAX مع `exog` معروفة مستقبلًا أو سيناريو مفروض.
- **المتطلبات:** CPU لseries صغيرة؛ RAM/time ترتفع مع طول السلسلة وكثرة grid-search/windows/ensemble. الرقم الفعلي يقاس على hardware التنفيذ.
- **القيود/البديل:** backtest زمني + Naive/SNaive؛ إذا فشل لا تعرضه. للإسقاط المناخي لعقود، سيناريوهات CMIP6 مجموعة مختلفة.
- **مصدر:** [statsmodels ARIMA](https://www.statsmodels.org/stable/generated/statsmodels.tsa.arima.model.ARIMA.html) · [SARIMAX](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAX.html).

### 9.5 نماذج Gemini وبطاقات إدماج AI

| المعرّف | الفئة/الحالة | الوظيفة/المخرجات | قيود/مراجع |
|---|---|---|---|
| `gemini-3.8-flash` | LLM متعدد الوسائط؛ stable حسب صفحة النماذج بتاريخ التحقق؛ مقترح | شرح عربي/إنجليزي، اختيار function calling وأدوات backend | الأرقام من Python وmetadata؛ free limits على AI Studio؛ [models](https://ai.google.dev/gemini-api/docs/models) و[function calling](https://ai.google.dev/gemini-api/docs/function-calling) |
| `gemini-3.1-pro-preview` | LLM reasoning؛ Preview ومقترح للاستخدام المقارن | مهام شرح أثقل/تخطيط أدوات عند توفره | Preview قد يتغير/حدوده أقل استقرارًا؛ لا حاجة MVP |
| `gemini-3.5-transcribe` | speech-to-text؛ stable بحسب الدليل؛ اختياري | صوت → نص مع language detection/speaker/timestamp | لم يختبر؛ راجع اللغة/الـquota والموافقة/الخصوصية؛ [transcription](https://ai.google.dev/gemini-api/docs/transcribe) |
| `gemini-3.8-flash-tts` | TTS؛ stable بحسب صفحة Google؛ اختياري | نص → صوت، مع دعم العربية الفصحى المذكور في جدول اللغات | نطق العربية واللهجة يحتاج اختبارًا؛ رسوم Free/Paid تتغير؛ [speech generation](https://ai.google.dev/gemini-api/docs/speech-generation) |
| `gemini-3.8-flash-lite-tts` | TTS أخف؛ stable بحسب الصفحة؛ اختياري | صوت حواري أقل تكلفة/زمن بحسب الوصف الرسمي | ليس transcription؛ تحقق دعم اللغة والتسعير الجاري |
| `gemini-3.8-live` | Live multimodal/audio؛ stable بحسب docs؛ مؤجل | تفاعل صوتي/فيديو منخفض التأخير | تكلفة وربط realtime زائدان عن الحاجة؛ [Live API](https://ai.google.dev/gemini-api/docs/live) |
| `gemini-3.8-live-extended-thinking` | Live + reasoning؛ stable بحسب docs؛ مؤجل | voice flow مع استدلال إضافي | لا تستخدمه لحساب trend أو كبديل backend deterministic |
| Gemini built-in Search grounding | أداة Google؛ اختيارية منفصلة | بحث ويب grounded للنص | ليس NASA data API؛ رسوم/حدود مستقلة بحسب tier في [pricing](https://ai.google.dev/gemini-api/docs/pricing) |
| Gemini URL Context | أداة Google؛ اختيارية | قراءة URL عبر model في حالات مدعومة | ليست crawler inventory أو ضمان وصول للبيانات؛ لا تستخدمها كمرجع وحيد للحقائق المتغيرة |

#### بطاقة: `gemini-3.8-flash`

- **التصنيف والحالة:** LLM multimodal؛ Stable حسب model catalog بتاريخ 2026-11-14؛ مقترح، لم يُستدعَ بمفتاح في هذا البحث.
- **الوظيفة/سبب الاختيار:** شرح نتائج الإحصاء بالعربية والإنجليزية، فهم صورة/مخطط عند الحاجة، وتوجيه tool call. Google توثق function calling لهذا المعرّف. استخدمه لأنه الاختيار الأحدث المعلن stable في الكتالوج وقت الفحص، مع سرعة/تكلفة تناسب واجهة شرح؛ يعاد فحص model IDs قبل إصدار.
- **المدخل/المخرج:** نص + compact JSON من Backend، صورة اختيارية مدعومة، أو function declaration؛ يخرج نص/structured response أو function call، لا قيمة علمية موثوقة من تلقاء نفسه.
- **مكانه/التشغيل:** Backend عبر `google-genai` و`GEMINI_API_KEY`; لا تشغيل محلي/وزن تنزيل. API key من AI Studio.
- **التكلفة/الحدود:** Free Tier Standard مدرج بسعر صفر وقت التحقق؛ rate limits حسب المشروع والنموذج وتتغير. Paid standard منشور $0.75/M input و$3.75/M output حتى 2026-12-31، وأسعار جديدة معلنة من 2027-01-01. Free Tier requests may be used to improve Google products حسب pricing page.
- **القيود/البديل:** لا تحسب trend/predict؛ طبّق JSON schema وallowlist للـfunctions؛ البديل تقرير backend بقوالب إذا لم نرد اعتماد API.
- **المراجع:** [model catalog](https://ai.google.dev/gemini-api/docs/models) · [function calling](https://ai.google.dev/gemini-api/docs/function-calling) · [pricing](https://ai.google.dev/gemini-api/docs/pricing).

#### بطاقة: `gemini-3.1-pro-preview`

- **التصنيف والحالة:** LLM multimodal reasoning؛ Preview في model catalog؛ لا ندخله default production.
- **الوظيفة/الدور:** شرح مسألة معقدة أو مقارنة لغوية أكبر إذا أظهر benchmark داخلي فائدة على Flash؛ مدخلاته النص/الوسائط/نتيجة الأدوات، مخرجاته نص أو tool call عند دعم config. لا نحتاجه لحساب إحصائي.
- **التشغيل/المتطلبات:** Gemini Developer API + server-side API key، أو تجربة AI Studio؛ cloud inference، لا نموذج محلي مطلوب.
- **التكلفة والحدود:** **ليس متاحًا في Free Tier** بحسب جدول Google الحالي. Paid Standard: $2/M input و$12/M output حتى 200k input-context tokens، ثم $4/M و$18/M على السياق الأكبر؛ الأسعار والحصص قد تتغير. حالة Preview وتوافره تتغير.
- **البديل:** `gemini-3.8-flash` أو Backend deterministic بدون LLM. [models](https://ai.google.dev/gemini-api/docs/models) · [pricing](https://ai.google.dev/gemini-api/docs/pricing).

#### بطاقة: `gemini-3.5-transcribe`

- **التصنيف والحالة:** نموذج speech-to-text؛ مدرج في دليل Audio Transcription؛ لم يتأكد من وسم Stable/Preview من بيانات catalog المقروءة في هذا البحث، لذا حالته التشغيلية تراجع قبل pinning.
- **الوظيفة/السبب:** صوت محفوظ → نص، مع كشف اللغة، diarization، timestamps word-level وcustom vocabulary بحسب صفحة Google. يُختار فقط إن كان إدخال الصوت مطلوبًا.
- **مدخل/مخرج وتكامل:** ملف صوتي حتى ساعة حسب model card → نص/word annotations؛ Backend يرفع الملف إلى Google Files/Interactions حسب SDK، ثم يحذف/يدير الملف وفق retention/privacy.
- **التكلفة/المصادقة:** API key، Free Tier Standard ظاهر $0 في صفحة pricing؛ Paid تقديري $0.003/min input audio + $0.002/min text output وقت الفحص؛ الحصة تتغير، ومحتوى Free Tier قد يستخدم لتحسين الخدمة.
- **القيود/البديل:** Arabic quality ليست مثبتة باختبار خاص للمشروع؛ جرّب لهجة/فصحى ومصطلحات ناسا، واطلب موافقة لرفع الصوت. بديل browser/device STT أو تعطيل الصوت.
- **مصادر:** [transcribe guide](https://ai.google.dev/gemini-api/docs/transcribe) · [model card](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-transcribe) · [pricing](https://ai.google.dev/gemini-api/docs/pricing).

#### بطاقة: `gemini-3.8-flash-tts`

- **التصنيف والحالة:** text-to-speech model؛ Stable حسب Google catalog؛ اختياري.
- **الوظيفة/السبب:** قراءة ملخص تقرير مراجع نصيًا، بنبرة/سرعة قابلة للتوجيه؛ Google تسرد Standard Arabic ضمن اللغات.
- **مدخل/مخرج:** نص تقرير عربي/إنجليزي + إعداد voice style → audio tokens؛ يحفظ Backend الملف أو يعيده كرابط قصير العمر.
- **التشغيل/المصادقة/التكلفة:** `google-genai` عبر Gemini API key؛ Free Tier Standard=$0 بحسب صفحة pricing وقت التحقق؛ Paid حتى نهاية 2026: $0.50/M text input و$9/M audio output (التسعير المقدر لكل 10 ثوانٍ $0.00225). سياسة Free use لتحسين المنتج مذكورة في جدول السعر.
- **الحدود/البديل:** النطق للهجة العربية وجودة الكلمات العلمية غير مختبرين؛ لا تنطق مخرجات غير مراجعة؛ البديل TTS محلي/نظامي أو نص فقط.
- **مصدر:** [speech generation & supported languages](https://ai.google.dev/gemini-api/docs/speech-generation) · [pricing](https://ai.google.dev/gemini-api/docs/pricing).

#### بطاقة: `gemini-3.8-flash-lite-tts`

- **التصنيف والحالة:** TTS سريع/منخفض التكلفة؛ Stable حسب Google؛ اختياري.
- **المدخل/المخرج والدور:** نص التقرير → صوت عربي/إنجليزي؛ توليد صوت قصير بعد تثبيت التقرير الإحصائي.
- **المتطلبات/التكلفة:** API key؛ Free Tier Standard=$0 في الجدول الحالي؛ Paid حتى 2026-12-31: $0.50/M text و$6/M audio، ويعلن الجدول تغيرًا في 2027. حصة الاستخدام الفعلية في AI Studio.
- **القيود/البديل:** لا يفرغ صوتًا ولا يجري live dialogue؛ تحقق دعم Standard Arabic وجودة المصطلح علميًا. البديل Flash TTS أو النص.
- **المصدر:** [model catalog](https://ai.google.dev/gemini-api/docs/models) · [speech generation](https://ai.google.dev/gemini-api/docs/speech-generation) · [pricing](https://ai.google.dev/gemini-api/docs/pricing).

#### بطاقة: `gemini-3.8-live` و`gemini-3.8-live-extended-thinking`

- **التصنيف والحالة:** Live audio/multimodal models؛ Stable في model catalog وقت التحقق؛ مؤجلان.
- **الوظيفة/المدخل/المخرج:** جلسة bidirectional منخفضة التأخير للصوت/الفيديو → audio/text responses؛ extended-thinking يضيف reasoning حسب الوصف. لا يحقق أي تحليل بيانات ارضية دون أدوات backend.
- **سبب عدم اختيارهما لـMVP:** يتطلب WebSocket/session lifecycle وقيود audio/video، وcost/latency لا تلزم لسؤال trend بعد انتهائه.
- **المتطلبات/التكلفة:** Gemini Live API وAPI key؛ Free Tier Standard ظاهر بسعر صفر في pricing page، لكن الحدود per project والمحتوى قد يستخدم لتحسين الخدمات. Paid standard وقت الفحص $0.005/min audio input و$0.018/min audio output تقريبًا إضافة إلى text/image tokens؛ راجع جدول live للنموذج الدقيق.
- **البديل:** `gemini-3.5-transcribe` للصوت المسجل أو إدخال نصي أو Live بوسيط مستقل عند ثبوت الحاجة.
- **مصادر:** [Live API](https://ai.google.dev/gemini-api/docs/live) · [model catalog](https://ai.google.dev/gemini-api/docs/models) · [pricing](https://ai.google.dev/gemini-api/docs/pricing).

#### بطاقة: Google Search grounding وURL Context

- **التصنيف والحالة:** أدوات hosted إضافية من Google؛ اختيارية، غير مستخدمة في هذا المرجع.
- **الوظيفة/المدخل/المخرج:** model search grounding يعيد إجابة ونسب بحث؛ URL context يسمح للنموذج بقراءة URL مدعوم. لا يقومان بتنزيل أو توحيد Earth science collections مثل CMR/AppEEARS.
- **سبب الإضافة المحتمل:** تحديث تعريف API خارجي أو سؤال عام؛ لا تستخدم مصدرًا علميًا لـmeasurement ولا مصدرًا وحيدًا لحدود API.
- **التكلفة/التشغيل:** تمرير tool في Google API؛ احصل على API key؛ Search grounding مدعوم لبعض النماذج/tiers وتفاصيل السعر والحصة منفصلة (صفحة التسعير تعرض 5000 free search requests/month shared لبعض نماذج Gemini 3+ ثم $14/1000؛ التوفر يختلف حسب النموذج/plan).
- **البديل:** مصادر NASA الرسمية المحددة والبحث اليدوي مع citations. [Search grounding](https://ai.google.dev/gemini-api/docs/google-search) · [URL context](https://ai.google.dev/gemini-api/docs/url-context) · [pricing](https://ai.google.dev/gemini-api/docs/pricing).

**مثال استدعاء Python (شكل تكاملي، لم يُشغّل):**

```python
import os
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
response = client.models.generate_content(
    model="gemini-3.8-flash",
    contents="اشرح نتيجة الاتجاه المسجلة في result_id trend_31c0",
    config=types.GenerateContentConfig(
        tools=[trend_tools],
        system_instruction=(
            "استدعِ الأدوات المسموح بها عند الحاجة. لا تحسب أو تغيّر أرقامًا علمية؛ "
            "اشرح فقط نواتج backend ووحداتها وفترتها وقيودها."
        ),
    ),
)
```

هذا sketch توضيحي؛ schema لـ`trend_tools` يحتاج تعريفًا حسب إصدار `google-genai` المثبت. يجب أن يمنع backend أي tool function غير معروفة أو غير مصرح بها. مصدر البدء: [Google Gen AI SDK for Python](https://googleapis.github.io/python-genai/).

### 9.6 بنية التشغيل

#### Python + FastAPI + Pydantic

- **التصنيف/الحالة:** runtime + API framework؛ مقترح، لا endpoint فعلي في المستودع الحالي.
- **الدور:** فصل الواجهة عن data/analysis service؛ Pydantic للتحقق من JSON؛ FastAPI endpoints تستدعي أدوات محددة؛ يمكن إعادة استخدامه من mobile/desktop/site.
- **مثال:** `POST /v1/series` بطلب schema → `series_id`; `GET /v1/results/{result_id}` → نتيجة ووحدات ومصادر.
- **التكلفة/التشغيل:** Python process على CPU للتجربة؛ نشر/خدمة/حوسبة raster لها تكاليف مستقلة؛ لا أسرار بالـclient.
- **مصادر:** [FastAPI](https://fastapi.tiangolo.com/) · [Pydantic](https://docs.pydantic.dev/).

#### Cache + metadata store

- **التصنيف/الحالة:** pattern بنية تشغيل؛ مقترح.
- **الوظيفة:** تخزين cache للاستجابات وseries/results IDs والـlineage، لا إعادة طلب المصدر المتكرر؛ ملفات raw الكبيرة في object storage.
- **البدء:** SQLite/PostgreSQL metadata + filesystem/object store بحسب نشر المشروع؛ Redis only إذا احتاج async job queue.
- **المخاطر:** version/expiry/license، حذف credentials، وعدم تقديم cache قديم كبيانات لحظية.

#### Plotly charts / geospatial frontend

- **التصنيف/الحالة:** renderer/واجهة مرشحة، غير مضافة فعليًا.
- **الوظيفة:** chart للtrend مع CI/baseline/missing; map layers للنطاق المكاني مع scale وlegend.
- **الدور:** عرض النتائج المحسوبة من backend. لا تحسب slope في المتصفح على مخرجات مقتطعة.
- **مصادر:** [Plotly Python](https://plotly.com/python/)؛ طبقة خرائط 3D اختيار تصميمي، لا تعني استخدام NASA Worldview API.

#### Earthdata Login / secrets handling

- **التصنيف/الحالة:** اعتماد NASA لبعض التنزيلات؛ مطلوب عند استخدامه، غير متوفر/غير اختبر هنا.
- **الدور:** AppEEARS task/data download أو access controlled collections؛ bearer tokens قصيرة العمر في Backend فقط.
- **تشغيل:** سجّل Earthdata account وأنشئ application authorization حسب NASA docs، استخدم secret manager أو env؛ لا تضع user/pass في browser.
- **المراجع:** [Earthdata Login](https://urs.earthdata.nasa.gov/) · [AppEEARS API](https://appeears.earthdatacloud.nasa.gov/api/).

### 9.7 الجرد الكامل لروابط Resources في تحديات 2026

هذه القائمة هي إزالة تكرار للـURL عبر صفحات Resources الأربعة عشر، **مع حفظ كل تسميات/تحديات الإحالة**. لا تتساوى الموارد في موثوقية المجال أو النوع؛ افحصها وفق جدول الخدمة/المصدر، ولا تعتبر كل عنوان API.

| المورد (التسمية المنشورة) | URL | إدراجه ضمن الموارد | صلته بـEarthTrend Explorer | التحديات التي أشارت إليه |
|---|---|---|---|---|
''')
    # Need explicit dedup while preserving challenges and names.
    c_map = {c["id"]: c for c in coverage}
    inventory = resource_records()
    sections = {}
    for c in coverage:
        html_path = RESEARCH / f"challenge_{c['id']}_resources.html"
        if html_path.exists(): sections.update(section_for_url(html_path))
    def relevance(item):
        name = " ".join(item.get("labels", [])).lower()
        url = item.get("url", "").lower()
        alltext = name + " " + url
        high = ("nisar", "sar", "earthdata", "giovanni", "appeears", "hydrology", "climate", "soil moisture", "precipitation", "landsat", "modis", "viirs", "ecostress", "gpm", "swot", "gedi", "time-series", "time series", "trend", "weather", "earth observation", "earth science", "fao", "era5", "nldas", "gldas", "srtm", "sea level", "vegetation", "radarsat", "rcm", "worldview", "firms")
        medium = ("noaa", "usgs", "ag data", "agriculture", "soil", "crop", "water", "ecosystem", "land cover", "satellite", "remote sensing", "statistics", "statistical", "significance", "open science", "earth information", "cdo", "prism", "co2", "carbon")
        if any(k in alltext for k in high): return "مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل"
        if any(k in alltext for k in medium): return "مساندة: سياق/مرجع أو بيانات مكملة؛ ليست بالضرورة NASA أو API"
        return "منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي"
    for item in inventory:
        labels = " / ".join(item.get("labels", []))
        section = sections.get(item["url"].rstrip("/"), "جهة خارجية/نوع الإدراج لم يحسم من صفحة المورد")
        host = urlsplit(item["url"]).netloc.lower()
        partner_hosts = ("asc-csa.gc.ca", "geo.ca", "esa.int", "copernicus.eu", "jaxa.jp", "conae.gov.ar", "knmi.nl")
        partner_domain = next((x for x in partner_hosts if host == x or host.endswith("." + x)), None)
        if partner_domain:
            agency = {"asc-csa.gc.ca": "CSA", "geo.ca": "GEO Canada", "esa.int": "ESA", "copernicus.eu": "ESA/Copernicus", "jaxa.jp": "JAXA", "conae.gov.ar": "CONAE", "knmi.nl": "KNMI"}[partner_domain]
            section = "شريك: " + agency
        titles = []
        for slug in item.get("challenges", []):
            if slug in c_map: titles.append("<span dir=\"ltr\">" + html.escape(c_map[slug]["title"]) + "</span>")
        content.append(f"| {labels} | [{item['url']}]({item['url']}) | {section} | {relevance(item)} | {', '.join(titles)} |\n")
    content.append(r'''

### 9.8 Gemini API key وإعداد بيئة نموذج أولي

```powershell
$env:GEMINI_API_KEY = "<ضع المفتاح محليًا في جلسة shell آمنة>"
python -m pip install google-genai
```

لا تكتب المفتاح الحقيقي في هذا المستند أو ملف `.env` مرفوع. في التطبيق، الأفضل secret manager أو ملف محلي مستثنى من Git. عند استعمال `.env` المحلي، أضفه إلى `.gitignore` وتأكد من عدم تضمينه في frontend bundle. اقرأ المفتاح في Python عبر `os.environ.get("GEMINI_API_KEY")`، واستخدم least privilege. إذا تعرض مفتاح، أبطله/دوّره من AI Studio.

### 9.9 وثائق علمية وأدلة رسمية إضافية

- [NASA Space Apps 2026 Challenges](https://www.spaceappschallenge.org/2026/challenges/) — قائمة التحديات 2026.
- [NASA CMR Search API docs](https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html) — discovery endpoints وpagination.
- [AppEEARS API](https://appeears.earthdatacloud.nasa.gov/api/) — tasks/catalog وتوثيق extraction.
- [NASA POWER API](https://power.larc.nasa.gov/docs/services/api/) — daily/monthly/annual endpoints وunits.
- [Earthdata APIs](https://www.earthdata.nasa.gov/data/tools) — discovery/processing/access pathways.
- [NASA GIBS WMTS API](https://nasa-gibs.github.io/gibs-api-docs/) — imagery tiles.
- [NASA Harmony docs](https://harmony.earthdata.nasa.gov/docs) — processing/granule access API.
- [NASA FIRMS API](https://firms.modaps.eosdis.nasa.gov/api/) — key-protected fire endpoints.
- [Hydrocron](https://podaac.github.io/hydrocron/) — SWOT time-series API.
- [NEX-GDDP-CMIP6](https://www.nccs.nasa.gov/data-collections/nex-gddp-cmip6/) — scenario data, historical and projections.
- [Gemini models](https://ai.google.dev/gemini-api/docs/models), [pricing](https://ai.google.dev/gemini-api/docs/pricing), [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits), [Function calling](https://ai.google.dev/gemini-api/docs/function-calling), [Live API](https://ai.google.dev/gemini-api/docs/live).
- [Prithvi-EO-2.0 model card/weights](https://huggingface.co/ibm-nasa-geospatial) — يتحقق منها قبل إدخال CV.
- [NASA/USGS LP DAAC product pages](https://lpdaac.usgs.gov/products/) — المنتج/collection/version/quality layers.

---

**إخلاء منهجي:** هذا الملف ليس اعتمادًا من NASA أو تفسيرًا قانونيًا للترخيص، ولا يقدم توصية مناخية/تشغيلية. قبل نشر نسخة لاحقة، أعد فحص challenge resources والـAPI model IDs والـterms، وسجل بتاريخ التحقق version+parameters لكل dataset. إذا أضيف استدلال على خطر عام، يجب وجود تقييم وتحقيق بشري مستقل.
''')
    OUT.write_text("".join(content), encoding="utf-8")
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")

if __name__ == "__main__":
    write()
