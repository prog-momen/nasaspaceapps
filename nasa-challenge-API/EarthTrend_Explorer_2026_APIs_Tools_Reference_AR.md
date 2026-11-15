# EarthTrend Explorer — مرجع APIs والأدوات لعام 2026

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
| <span dir="ltr">Abandoned but not Forgotten: Storytelling about NASA&#x27;s Discarded Equipment on the Moon and Mars</span> | [https://www.spaceappschallenge.org/2026/challenges/nasas-discarded-equipment-storytelling/](https://www.spaceappschallenge.org/2026/challenges/nasas-discarded-equipment-storytelling/) | HTTP 200 في السجل، HTML محفوظ | 14 |
| <span dir="ltr">Be An Earth System Trend Detective!</span> | [https://www.spaceappschallenge.org/2026/challenges/earth-system-trend-detective/](https://www.spaceappschallenge.org/2026/challenges/earth-system-trend-detective/) | HTTP 200 في السجل، HTML محفوظ | 13 |
| <span dir="ltr">Build a Junior Astronaut Mission Trainer</span> | [https://www.spaceappschallenge.org/2026/challenges/junior-astronaut-mission-trainer/](https://www.spaceappschallenge.org/2026/challenges/junior-astronaut-mission-trainer/) | HTTP 200 في السجل، HTML محفوظ | 8 |
| <span dir="ltr">Create Health Monitoring Software for Astronauts on Space Missions</span> | [https://www.spaceappschallenge.org/2026/challenges/health-monitoring-software/](https://www.spaceappschallenge.org/2026/challenges/health-monitoring-software/) | HTTP 200 في السجل، HTML محفوظ | 5 |
| <span dir="ltr">Dancing with the SARs</span> | [https://www.spaceappschallenge.org/2026/challenges/dancing-with-the-sars/](https://www.spaceappschallenge.org/2026/challenges/dancing-with-the-sars/) | HTTP 200 في السجل، HTML محفوظ | 14 |
| <span dir="ltr">Field Shift: Adapting Farms with NASA Data</span> | [https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/](https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/) | HTTP 200 في السجل، HTML محفوظ | 26 |
| <span dir="ltr">Flame in Freefall: SI-Powered Fire Safety Insights from Microgravity Combustion Data</span> | [https://www.spaceappschallenge.org/2026/challenges/flame-in-freefall/](https://www.spaceappschallenge.org/2026/challenges/flame-in-freefall/) | HTTP 200 في السجل، HTML محفوظ | 10 |
| <span dir="ltr">Harmonization of MODIS and VIIRS Hot Spots</span> | [https://www.spaceappschallenge.org/2026/challenges/modis-and-viirs-hot-spots/](https://www.spaceappschallenge.org/2026/challenges/modis-and-viirs-hot-spots/) | HTTP 200 في السجل، HTML محفوظ | 1 |
| <span dir="ltr">Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars</span> | [https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/](https://www.spaceappschallenge.org/2026/challenges/permanent-moon-base-locations-and-mars/) | HTTP 200 في السجل، HTML محفوظ | 11 |
| <span dir="ltr">Interplanetary Survival Guide: Martian Map</span> | [https://www.spaceappschallenge.org/2026/challenges/interplanetary-survival-guide-martian-map/](https://www.spaceappschallenge.org/2026/challenges/interplanetary-survival-guide-martian-map/) | HTTP 200 في السجل، HTML محفوظ | 5 |
| <span dir="ltr">Lunar Landing Site Navigator</span> | [https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/](https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/) | HTTP 200 في السجل، HTML محفوظ | 4 |
| <span dir="ltr">Planet X and SPHEREx</span> | [https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/) | HTTP 200 في السجل، HTML محفوظ | 8 |
| <span dir="ltr">Space Mission Design Game</span> | [https://www.spaceappschallenge.org/2026/challenges/space-mission-design-game/](https://www.spaceappschallenge.org/2026/challenges/space-mission-design-game/) | HTTP 200 في السجل، HTML محفوظ | 9 |
| <span dir="ltr">The Earth Information Jukebox</span> | [https://www.spaceappschallenge.org/2026/challenges/the-earth-information-jukebox/](https://www.spaceappschallenge.org/2026/challenges/the-earth-information-jukebox/) | HTTP 200 في السجل، HTML محفوظ | 11 |

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

### 9.2 بطاقات APIs والخدمات

| S01 | CMR / Earthdata Search | A | مختبَر في البحث |
| S02 | AppEEARS | C | مختبَر في البحث |
| S03 | Giovanni in the Cloud | C | موثق/مرشح؛ الاختبار محدود أو لم يجر |
| S04 | Hydrology Time Series / Data Rods | C/E | مختبَر في البحث |
| S05 | NASA POWER | C | مختبَر في البحث |
| S06 | FIRMS | A/B | موثق/مرشح؛ الاختبار محدود أو لم يجر |
| S07 | Worldview / GIBS | B | مختبَر في البحث |
| S08 | ASF Search / Vertex / NISAR | A | مختبَر في البحث |
| S09 | Harmony | C | موثق/مرشح؛ الاختبار محدود أو لم يجر |
| S10 | SWOT / Hydrocron | C | مختبَر في البحث |
| S11 | NOAA Climate Data Online (CDO) | A | موثق/مرشح؛ الاختبار محدود أو لم يجر |
| S12 | NASA Open APIs portal | A/B/E | موثق/مرشح؛ الاختبار محدود أو لم يجر |
| S13 | EONET v3 | A/B | مختبَر في البحث |
| S14 | EPIC | B | مختبَر في البحث |
| S15 | NTRS | A/E | مختبَر في البحث |
| S16 | SVS / Earth Information Center | A/B | مختبَر في البحث |
| S17 | JPL Horizons | C (حساب فلكي) | مختبَر في البحث |
| S18 | Planetary Data System / LRO | A | مختبَر في البحث |
| S19 | OSDR Biological Data / Search | A | مختبَر في البحث |
| S20 | DONKI / RadLab | A (متخصص) | موثق/مرشح؛ الاختبار محدود أو لم يجر |
| S21 | IRSA / SPHEREx | A | موثق/مرشح؛ الاختبار محدود أو لم يجر |
| S22 | Moon/Mars Trek / QuickMap | B/E | موثق/مرشح؛ الاختبار محدود أو لم يجر |
| S23 | NEX-GDDP-CMIP6 / THREDDS | A/C (ملفات وإسقاطات مناخية) | موثق/مرشح؛ الاختبار محدود أو لم يجر |
| S24 | Google Earth Engine | C / SDK خارجي | موثق/مرشح؛ الاختبار محدود أو لم يجر |

#### S01 — CMR / Earthdata Search

- **التصنيف:** A
- **الحالة:** مختبَر في هذا البحث
- **الجهة المالكة:** NASA ESDIS
- **مرجع موارد التحدي:** R041,R057؛ تحديا 5 و6 و9. CMR هو API خلف الاكتشاف، وليس اسم رابط مستقل في Resources.
- **وثائق المطورين:** [https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html](https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html)
- **Base URL / الرابط:** [https://cmr.earthdata.nasa.gov/search](https://cmr.earthdata.nasa.gov/search)
- **المسارات/طريقة الاستخدام:** GET /collections.json، /granules.json؛ مع short_name,version,temporal,bounding_box أو point. تنزيل الملفات من روابط granule لدى DAAC، وليس من مصفوفة metadata نفسها.
- **الوظيفة والملاءمة:** اكتشاف المجموعات وإصداراتها وملفاتها، وربط كل نتيجة بـconcept ID وDOI. أساسي عند تعدد مصادر المشروع.
- **البيانات/المدخلات:** مجموعات NASA متعددة؛ اختبار MOD11C3.061 أعاد C2565788897-LPCLOUD. التغطية والدقة والوحدات تخص المنتج لا CMR.
- **المصادقة:** البحث العام بلا مصادقة؛ بعض metadata المقيدة والتنزيل يحتاج Earthdata Login وتصريح التطبيق/المجموعة.
- **المجانية/التكلفة:** البحث مجاني؛ لا تعمم حصص api.nasa.gov عليه. تكلفة الحوسبة/التخزين الخارجية منفصلة.
- **الحدود والقيود:** page_size أقصاه 2000 وفق التوثيق؛ pagination باستخدام CMR-Search-After عند الحاجة. لا تتجاوز الطلبات المتزامنة المعقولة؛ احفظ CMR-Request-Id وتعامل مع 429.
- **الصيغ:** JSON/UMM-JSON وXML وCSV وصيغ metadata أخرى؛ ملفات البيانات الأصلية بحسب المنتج.
- **مثال الطلب:** ```text
curl "https://cmr.earthdata.nasa.gov/search/collections.json?short_name=MOD11C3&version=061&page_size=1"
```
- **مثال الاستجابة:** ```text
فعلي مختصر: {"feed":{"entry":[{"id":"C2565788897-LPCLOUD","short_name":"MOD11C3","version_id":"061","time_start":"2000-02-01T00:00:00.000Z"}]}}
```
- **دليل التحقق:** تم اختبار collection وgranule metadata؛ لا تنزيل محمي. محاولة أولى بـContent-Type:application/json أعادت 400؛ نجح GET بعد حذف الرأس غير المناسب. قيد TLS البحثي قائم.
- **البديل:** earthaccess يبسط استعمال CMR وEarthdata؛ ليس مصدر بيانات بديلًا.

#### S02 — AppEEARS

- **التصنيف:** C
- **الحالة:** مختبَر في هذا البحث
- **الجهة المالكة:** NASA LP DAAC / USGS
- **مرجع موارد التحدي:** R017؛ تحدي 2، مع منتجات MODIS وغيرها من R056.
- **وثائق المطورين:** [https://appeears.earthdatacloud.nasa.gov/api/](https://appeears.earthdatacloud.nasa.gov/api/)
- **Base URL / الرابط:** [https://appeears.earthdatacloud.nasa.gov/api](https://appeears.earthdatacloud.nasa.gov/api)
- **المسارات/طريقة الاستخدام:** GET /product و/product/{ProductAndVersion}؛ POST /login؛ POST /task؛ GET /task/{task_id} و/bundle/{task_id} و/bundle/{task_id}/{file_id}.
- **الوظيفة والملاءمة:** استخراج point time series أو area subsets من منتجات مدعومة. أفضل مسار أولي لـMODIS دون تنزيل التغطية العالمية.
- **البيانات/المدخلات:** ProductAndVersion مثل MOD11A2.061، وlayers مثل LST_Day_1km وQC_Day. لا يفترض توفر كل منتج CMR؛ يستعلم الكتالوج أولًا.
- **المصادقة:** قائمة المنتجات وlayers عامة. login بـEarthdata username/password لتوليد Bearer token. الرموز مخزنة في Backend فقط؛ لا تُكتب في سجل الطلبات.
- **المجانية/التكلفة:** خدمة مجانية؛ لا توجد في الوثيقة حصة مالية عامة نثبتها لكل حساب. زمن الصف والحدود التشغيلية يخضعان للخدمة.
- **الحدود والقيود:** مهام غير متزامنة؛ polling بتأخير لا حلقة سريعة. التوثيق يصف token يقارب 48 ساعة؛ استخدم expiration الفعلية. تحقق من status وأسماء files وQA. area rasters لا تعني حساب متوسط مضلع تلقائيًا.
- **الصيغ:** JSON للكتالوج/المهام، CSV لعينات point؛ NetCDF/GeoTIFF لمنتجات area وفق الخيارات المدعومة.
- **مثال الطلب:** ```text
curl "https://appeears.earthdatacloud.nasa.gov/api/product/MOD11A2.061"
```
- **مثال الاستجابة:** ```text
فعلي مختصر من layer metadata: LST_Day_1km مع Units وScaleFactor وFillValue وQualityLayers. مثال مهمة موثق: {"task_type":"point","params":{"dates":[{"startDate":"01-01-2025","endDate":"01-31-2025"}],"layers":[{"product":"MOD11A2.061","layer":"LST_Day_1km"}],"coordinates":[{"id":"p1","latitude":32.22,"longitude":35.26}]}}؛ يحتاج task_name في body الكامل.
```
- **دليل التحقق:** تم اختبار /product وlayers فقط؛ login/task/bundle يتطلب حسابًا ولم يُختبر. وجود 200 للكتالوج لا يثبت نجاح extraction.
- **البديل:** CMR+earthaccess والتنزيل المحلي؛ أو Earth Engine بخطة وشروط منفصلة.

#### S03 — Giovanni in the Cloud

- **التصنيف:** C
- **الحالة:** مقترح/موثق؛ لم يُختبر end-to-end
- **الجهة المالكة:** NASA GES DISC
- **مرجع موارد التحدي:** R015؛ تحدي 2. صفحة Resources تحيل إلى Giovanni؛ API موثق في notebook NASA المتفرع.
- **وثائق المطورين:** [https://github.com/nasa/gesdisc-tutorials/blob/main/notebooks/How_to_Access_GiC_Time_Series_Service.ipynb](https://github.com/nasa/gesdisc-tutorials/blob/main/notebooks/How_to_Access_GiC_Time_Series_Service.ipynb)
- **Base URL / الرابط:** [https://api.giovanni.earthdata.nasa.gov](https://api.giovanni.earthdata.nasa.gov)
- **المسارات/طريقة الاستخدام:** GET /timeseries مع data وlocation وtime في notebook الرسمي. /proxy-timeseries ظهر في إحالات دعم أحدث، لكن لم يتوفر عقده الرسمي الكامل في الجلسة؛ لا نفترض مطابقته ولا نعتمده أساسيًا.
- **الوظيفة والملاءمة:** استخراج سلسلة لنقطة من متغيرات GES DISC المتاحة؛ الواجهة القديمة تقدم أيضًا متوسطات مناطق وخرائط. مناسب للتحقق اليدوي والتحليل، مع تجنب افتراض أن كل قدرة UI لها API مستقرة.
- **البيانات/المدخلات:** مثال موثق: GLDAS_NOAH025_3H_2_1_Tair_f_inst. الفهرس والدقة والتغطية يتبعان المتغير. ليس من المثبت في هذا البحث أن API تغطي كل MODIS أو كل متوسط مضلع.
- **المصادقة:** Earthdata Login/Bearer token وتصريح GES DISC عند الحاجة. لم تُرسل بيانات اعتماد.
- **المجانية/التكلفة:** خدمة مجانية مع cloud credits محدودة في واجهة BETA، ويمكن طلب دعم عند نفادها؛ لا نخترع رقم quota شهريًا.
- **الحدود والقيود:** قد يتغير عقد BETA؛ وقت وفترة الطلب محدودان عمليًا بالمتغير والحصة. اقرأ CSV metadata بدل إسقاط أسطر ثابتة دون فحص. لا تُعامل 403 لمسار غير مثبت كنجاح auth.
- **الصيغ:** CSV في مثال time series؛ netCDF/PNG وغيرها في قدرات الواجهة القديمة.
- **مثال الطلب:** ```text
import os, httpx
r = httpx.get("https://api.giovanni.earthdata.nasa.gov/timeseries",
    params={"data":"GLDAS_NOAH025_3H_2_1_Tair_f_inst",
            "location":"[45.125,-98.125]",
            "time":"2020-01-01T03:00:00/2020-01-02T21:00:00"},
    headers={"Authorization":"Bearer " + os.environ["EARTHDATA_TOKEN"]}, timeout=60)
r.raise_for_status()
```
- **مثال الاستجابة:** ```text
شكل موثق: CSV يبدأ ببيانات وصفية تتضمن param_name وunit، ثم Timestamp وقيم المتغير. لم تُلتقط استجابة علمية من هذا المسار في الجلسة.
```
- **دليل التحقق:** موثق رسميًا ولم يُختبر باعتماد. /openapi.json و/variables أعادا 403 بلا اعتماد، وهما محاولتا اكتشاف لا عقدا API مثبتان.
- **البديل:** AppEEARS للمنتجات المدعومة، أو CMR وتنزيل NetCDF ومعالجته محليًا. لا يبنى MVP على endpoint مجهول.

#### S04 — Hydrology Time Series / Data Rods

- **التصنيف:** C/E
- **الحالة:** مختبَر في هذا البحث
- **الجهة المالكة:** NASA GES DISC
- **مرجع موارد التحدي:** R016؛ تحدي 2.
- **وثائق المطورين:** [https://disc.gsfc.nasa.gov/information/tools?title=Hydrology%20Time%20Series](https://disc.gsfc.nasa.gov/information/tools?title=Hydrology%20Time%20Series)
- **Base URL / الرابط:** [لا Base URL مستقلة مثبتة حاليًا في هذا البحث](لا Base URL مستقلة مثبتة حاليًا في هذا البحث)
- **المسارات/طريقة الاستخدام:** صفحة ويب للمورد. نُسبت إعادة توجيه Data Rods القديمة إلى GiC في موارد الدعم؛ عقد GiC المثبت مذكور في S03. لا نثبت endpoint قديمة من الذاكرة.
- **الوظيفة والملاءمة:** استخراج هيدرولوجيا لسلسلة نقطة، خصوصًا GLDAS/NLDAS، مع فحص المنتج.
- **البيانات/المدخلات:** GLDAS/NLDAS؛ الوحدات ومواعيد القياس تخص المتغير. لا تحمل كل المقاييس نفس التواتر أو التغطية.
- **المصادقة:** المعالجة عبر GiC تحتاج Earthdata؛ الصفحة نفسها عامة.
- **المجانية/التكلفة:** لا تكلفة موثقة منفصلة للصفحة؛ حدود المعالجة تتبع الخدمة الحالية.
- **الحدود والقيود:** الصفحة المسترجعة shell قصيرة وليست specification كاملة. API تاريخية لا تُوصف بأنها تعمل دون تنفيذ حديث.
- **الصيغ:** واجهة ويب؛ CSV عند استعمال GiC الموثق.
- **مثال الطلب:** ```text
curl "https://disc.gsfc.nasa.gov/information/tools?title=Hydrology%20Time%20Series"
```
- **مثال الاستجابة:** ```text
فعلي: HTTP 200، HTML قصير يحتاج تحميل تطبيق؛ لا سلسلة زمنية.
```
- **دليل التحقق:** تم جلب صفحة المورد؛ العقد الحالي المستقل متعذر التحقق. لم يُثبت إعلان توقف رسمي في البحث.
- **البديل:** S03 أو ملفات GES DISC عبر CMR/earthaccess.

#### S05 — NASA POWER

- **التصنيف:** C
- **الحالة:** مختبَر في هذا البحث
- **الجهة المالكة:** NASA Langley Research Center
- **مرجع موارد التحدي:** R058؛ تحدي 6 Field Shift. مورد NASA رسمي في قائمة 2026، وليس رابطًا مستقلًا في تحدي 2.
- **وثائق المطورين:** [https://power.larc.nasa.gov/docs/services/api/temporal/daily/](https://power.larc.nasa.gov/docs/services/api/temporal/daily/)
- **Base URL / الرابط:** [https://power.larc.nasa.gov/api](https://power.larc.nasa.gov/api)
- **المسارات/طريقة الاستخدام:** GET /temporal/daily/point و/temporal/monthly/point؛ regional وفق وثيقة الخدمة. parameters,community,longitude,latitude,start,end,format، وtime-standard حيث يدعم.
- **الوظيفة والملاءمة:** سلسلة جاهزة صغيرة لحرارة الهواء والأمطار والرياح والطاقة؛ نقطة بداية قليلة التعقيد للتطبيق.
- **البيانات/المدخلات:** T2M بوحدة C، PRECTOTCORR بوحدة mm/day في daily. المصدر في اختبارنا MERRA2. الدقة الأصلية للطقس تقارب 0.5°×0.625°؛ لا تعد نقطة الطلب محطة ولا قراءة 30m. متغيرات الإشعاع لها دقة/بداية مختلفة. daily meteorology من 1981 إلى قرب الحاضر حسب المتغير.
- **المصادقة:** دون API key للطلبات المختبرة.
- **المجانية/التكلفة:** وصول عام مجاني؛ احترم سياسة الاستخدام ولا تعيد تنزيل نفس الخلية تكرارًا. لا رقم RPM شامل مثبت في الصفحة المختارة.
- **الحدود والقيود:** daily point حتى 20 parameters وregional متغير واحد وفق الوثيقة. monthly يستخدم YYYY ويعيد ملخصات YYYY13؛ daily YYYYMMDD. اختر UTC أو LST صراحة في المسارات الداعمة. افحص fill_value=-999. لا تختزل bbox إلى نقطة وتصفه متوسط مساحة.
- **الصيغ:** JSON وCSV وNetCDF وASCII بحسب الخدمة.
- **مثال الطلب:** ```text
curl "https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M&community=AG&longitude=35.26&latitude=32.22&start=20250101&end=20250107&format=JSON&time-standard=UTC"
```
- **مثال الاستجابة:** ```text
فعلي مختصر: {"properties":{"parameter":{"T2M":{"20250101":10.64,"20250102":10.27}}},"parameters":{"T2M":{"units":"C"}},"header":{"fill_value":-999.0,"time_standard":"UTC","sources":["MERRA2"]}}
```
- **دليل التحقق:** تم اختبار daily بمتغيرين وmonthly بمتغير واحد؛ أُعيدت 252 قيمة شهرية صحيحة بعد حذف 21 ملخصًا سنويًا. قيد TLS قائم.
- **البديل:** Giovanni/NetCDF MERRA-2 عند الحاجة لتحكم علمي أو مساحي أدق.

#### S06 — FIRMS

- **التصنيف:** A/B
- **الحالة:** مقترح/موثق؛ لم يُختبر end-to-end
- **الجهة المالكة:** NASA LANCE / FIRMS
- **مرجع موارد التحدي:** R089؛ تحدي 8 Harmonization of MODIS and VIIRS Hot Spots.
- **وثائق المطورين:** [https://firms.modaps.eosdis.nasa.gov/api/area/](https://firms.modaps.eosdis.nasa.gov/api/area/)
- **Base URL / الرابط:** [https://firms.modaps.eosdis.nasa.gov](https://firms.modaps.eosdis.nasa.gov)
- **المسارات/طريقة الاستخدام:** GET /api/area/csv/{MAP_KEY}/{SOURCE}/{west,south,east,north}/{DAY_RANGE}/{DATE optional}. مسار data_availability لفترة المنتج.
- **الوظيفة والملاءمة:** نقاط حرائق نشطة/Hotspots وFRP؛ إضافة اختيارية لتفسير سياق الأحداث، لا توقع خطر حريق من تلقاء ذاتها.
- **البيانات/المدخلات:** MODIS نحو 1 km وVIIRS نحو 375 m للكشف النشط، لكن بصمة pixel تتغير مع زاوية المسح. frp بوحدة MW، وconfidence وأعلام daynight. تواريخ وأرشيفات SP/NRT حسب المصدر. لا تخلطها بمساحة الاحتراق.
- **المصادقة:** MAP_KEY مجاني مطلوب؛ مختلف عن api.nasa.gov وEarthdata.
- **المجانية/التكلفة:** مجاني؛ الوثيقة الحالية تذكر 5000 transactions لكل 10 دقائق، والطلب الكبير قد يحسب عدة transactions.
- **الحدود والقيود:** DAY_RANGE في الصفحة الحالية 1..5. اختر SOURCE ثابتًا مثل VIIRS_SNPP_SP للتاريخ العلمي حيث يتاح، وقارن المعايرة بين الحساسات لا الأعداد الخام دون تصحيح sampling.
- **الصيغ:** CSV لنقاط الكشف؛ طبقات WMS بصيغ صور في خدمة منفصلة.
- **مثال الطلب:** ```text
# MAP_KEY is read on the Backend; do not print the resulting URL.
import os, httpx
key = os.environ["FIRMS_MAP_KEY"]
r = httpx.get(f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/VIIRS_SNPP_NRT/35,31,36,33/1/2025-01-01", timeout=60)
```
- **مثال الاستجابة:** ```text
شكل موثق: latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight. لم يُختبر رد بيانات.
```
- **دليل التحقق:** API موثقة، وتتطلب MAP_KEY غير مستخدم في الجلسة؛ لم يُختبر تنزيل بيانات.
- **البديل:** أرشيف بيانات VIIRS/MODIS القياسي عبر CMR للتحليل المتجانس طويل المدى.

#### S07 — Worldview / GIBS

- **التصنيف:** B
- **الحالة:** مختبَر في هذا البحث
- **الجهة المالكة:** NASA EOSDIS
- **مرجع موارد التحدي:** R090؛ تحديا 9 و10. Worldview واجهة؛ GIBS هو API الصور المتفرع.
- **وثائق المطورين:** [https://nasa-gibs.github.io/gibs-api-docs/access-basics/](https://nasa-gibs.github.io/gibs-api-docs/access-basics/)
- **Base URL / الرابط:** [https://gibs.earthdata.nasa.gov](https://gibs.earthdata.nasa.gov)
- **المسارات/طريقة الاستخدام:** GET /wmts/epsg4326/best/{layer}/default/{date}/{matrixset}/{z}/{row}/{col}.jpg أو png؛ WMTS capabilities، وWMS /wms/epsg4326/best/wms.cgi.
- **الوظيفة والملاءمة:** طبقة سياق خريطة/كرة أرضية وصور قبل/بعد. لا مصدر حرارة أو NDVI رقمي جاهز للاتجاه من الألوان.
- **البيانات/المدخلات:** layer مثل MODIS_Terra_CorrectedReflectance_TrueColor. الدقة والتواتر والتاريخ وصيغ الملفات من capabilities لكل طبقة؛ best قد يختار تمثيلًا مختلفًا عن std/NRT.
- **المصادقة:** المسار المختبر بلا مفتاح.
- **المجانية/التكلفة:** عام ومجاني؛ لا حصة يومية موحدة مثبتة. cache tiles وmetadata.
- **الحدود والقيود:** احترم matrix limits والإسقاط وtime dimension؛ WMS 1.3.0 له ترتيب محاور قد يختلف. خريطة حديثة ناقصة قد تعني عدم وصول المدار بعد، لا غياب الظاهرة.
- **الصيغ:** JPEG/PNG لصور العرض، XML capabilities؛ ليست original GeoTIFF values.
- **مثال الطلب:** ```text
curl "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/2025-01-01/250m/0/0/0.jpg" --output tile.jpg
```
- **مثال الاستجابة:** ```text
فعلي: HTTP 200 وimage/jpeg، حجم 52,966 byte. فُحص توقيع الملف. لا JSON response لهذه الصورة.
```
- **دليل التحقق:** تم اختبار tile واحدة؛ لا تحليل Computer Vision أو قيم علمية منها.
- **البديل:** تحميل الرستر العلمي من DAAC عندما نحتاج حسابًا، مع إبقاء GIBS للعرض.

#### S08 — ASF Search / Vertex / NISAR

- **التصنيف:** A
- **الحالة:** مختبَر في هذا البحث
- **الجهة المالكة:** NASA ASF DAAC، University of Alaska Fairbanks
- **مرجع موارد التحدي:** R042,R043؛ تحدي 5. مصدر SAR من أرشيف NASA مع محتوى تعليمي R044-R049.
- **وثائق المطورين:** [https://docs.asf.alaska.edu/api/keywords/](https://docs.asf.alaska.edu/api/keywords/)
- **Base URL / الرابط:** [https://api.daac.asf.alaska.edu/services/search](https://api.daac.asf.alaska.edu/services/search)
- **المسارات/طريقة الاستخدام:** GET /param مع platform,bbox أو intersectsWith,start,end,processingLevel,output,maxResults. SDK asf_search بديل.
- **الوظيفة والملاءمة:** اكتشاف SAR وNISAR عند توافر المنتج. اختياري لمسار radar change analysis، ولا يحل محل السلاسل المناخية الطويلة.
- **البيانات/المدخلات:** NISAR/Sentinel-1 بحسب holdings؛ لا نفترض تاريخًا طويلًا لـNISAR. وحدات backscatter/complex والـpolarization والدقة والتغطية تختلف بحسب processing level.
- **المصادقة:** بحث metadata عام؛ تنزيل بعض البيانات يحتاج Earthdata وتفويضًا. لم تختبر ملفات NISAR.
- **المجانية/التكلفة:** بيانات عامة وفق شروط المنتج؛ الحوسبة والتنزيل والتخزين منفصلة.
- **الحدود والقيود:** طلبات مكانية صغيرة وpagination أو batching. SAR يحتاج orbit/calibration/terrain correction ومعالجة speckle بحسب المهمة؛ لا تعتبر dB قياس حرارة.
- **الصيغ:** GeoJSON وJSON وCSV وملفات مهمة مثل HDF5/GeoTIFF حسب المنتج.
- **مثال الطلب:** ```text
curl "https://api.daac.asf.alaska.edu/services/search/param?platform=Sentinel-1&bbox=35.2,32.1,35.3,32.3&start=2025-01-01T00:00:00Z&end=2025-01-03T00:00:00Z&output=geojson&maxResults=1"
```
- **مثال الاستجابة:** ```text
فعلي: {"type":"FeatureCollection","features":[]}؛ 200 وبنية صحيحة لكن بلا مشاهد في المدى الصغير. لا يثبت نجاح الحصول على صورة.
```
- **دليل التحقق:** تم اختبار استعلام فارغ صحيح بعد إزالة Content-Type غير المناسب؛ تنزيل ومعالجة SAR لم يختبرا.
- **البديل:** CMR أو SDK asf_search؛ لا داعي لـSAR في MVP الأساسي.

#### S09 — Harmony

- **التصنيف:** C
- **الحالة:** مقترح/موثق؛ لم يُختبر end-to-end
- **الجهة المالكة:** NASA Earthdata
- **مرجع موارد التحدي:** إضافة NASA مرتبطة ببيانات Earthdata في R041/R068؛ ليست رابطًا مستقلًا مستخرجًا.
- **وثائق المطورين:** [https://harmony.earthdata.nasa.gov/docs](https://harmony.earthdata.nasa.gov/docs)
- **Base URL / الرابط:** [https://harmony.earthdata.nasa.gov](https://harmony.earthdata.nasa.gov)
- **المسارات/طريقة الاستخدام:** OGC API Coverages/Processes ومساراتها المعلنة؛ route موثق: GET /{collection_id}/ogc-api-coverages/1.0.0/collections/{variable}/coverage. اكتشف capabilities قبل تكوين طلب؛ jobs API لتتبع المعالجة.
- **الوظيفة والملاءمة:** subsetting وتحويل لبعض المجموعات؛ ليس كل CMR collection قابلًا لكل خدمة.
- **البيانات/المدخلات:** collection concept ID وvariable IDs من metadata؛ spatial/temporal subset، projections وصيغ وفق capabilities.
- **المصادقة:** Earthdata Login للمهام المحمية؛ تنزيل السحابة قد يحتاج آلية credentials خاصة بالـDAAC.
- **المجانية/التكلفة:** خدمة NASA مجانية حسب الإتاحة؛ لا يُضمن غياب تكلفة cloud على بنيتك.
- **الحدود والقيود:** قد يصبح الطلب غير متزامنًا. استخدم روابط job/status/result المردودة بدل اختراع job paths. افحص أخطاء الخدمة وحدود حجم subset.
- **الصيغ:** STAC/JSON للمهام وروابط نتائج؛ NetCDF/GeoTIFF وفق الخدمة.
- **مثال الطلب:** ```text
# Template only: replace metadata-validated IDs.
# GET https://harmony.earthdata.nasa.gov/{collection_id}/ogc-api-coverages/1.0.0/collections/{variable}/coverage
```
- **مثال الاستجابة:** ```text
شكل موثق: metadata/links أو استجابة مهمة وروابط outputs. لم يُنشأ job، لذلك لا توجد استجابة فعلية.
```
- **دليل التحقق:** موثق رسميًا؛ لا اختبار processing أو auth. قالب endpoint يحتاج تحقق collection/variable في وقت التنفيذ.
- **البديل:** AppEEARS للمنتجات المدعومة، أو تنزيل+تجهيز محلي.

#### S10 — SWOT / Hydrocron

- **التصنيف:** C
- **الحالة:** مختبَر في هذا البحث
- **الجهة المالكة:** NASA PO.DAAC؛ SWOT مشروع NASA/CNES مع CSA/UKSA
- **مرجع موارد التحدي:** R025 صفحة معلومات صادرة عن CSA في تحدي 2؛ Hydrocron خدمة NASA متفرعة مقترحة، لا رابط مستقل في Resources.
- **وثائق المطورين:** [https://podaac.github.io/hydrocron/timeseries/](https://podaac.github.io/hydrocron/timeseries/)
- **Base URL / الرابط:** [https://soto.podaac.earthdatacloud.nasa.gov/hydrocron/v1](https://soto.podaac.earthdatacloud.nasa.gov/hydrocron/v1)
- **المسارات/طريقة الاستخدام:** GET /timeseries؛ feature=Reach|Node|PriorLake، feature_id، start_time,end_time، fields، output=csv|geojson، وcollection_name لتثبيت الإصدار.
- **الوظيفة والملاءمة:** سلاسل ارتفاع سطح الماء ومساحة البحيرات حسب feature ID، دون تنزيل جميع shapefiles. مفيد لتوسع هيدرولوجي؛ الأرشيف قصير لاتجاه مناخي متعدد العقود.
- **البيانات/المدخلات:** SWOT_L2_HR_RiverSP_D وLakeSP_D افتراضيًا في الوثيقة الحالية؛ 2.0 اختياري. wse m وarea_total km² وفق الوحدات المعادة. يجب حفظ SWORD/PLD وCRID لأن IDs ومواقع بعض المقاطع تغيرت.
- **المصادقة:** طلب السلسلة المختبر عام بلا مفتاح.
- **المجانية/التكلفة:** عام ومجاني؛ لا حصة حساب ثابتة مثبتة. لا تعدلات بطيئة كبيرة بلا cache.
- **الحدود والقيود:** صفّر missing flags وفق المنتج ولا تحوّل sentinel الضخم إلى ارتفاع فعلي. أدلة سابقة قد تفترض 2.0 كافتراضي، بينما الوثيقة الحالية تقول D. ثبّت collection ولا تخلطهما.
- **الصيغ:** JSON envelope بداخله CSV أو GeoJSON، أو استجابة مباشرة حسب Accept؛ compact قد يغير شكل properties.
- **مثال الطلب:** ```text
curl "https://soto.podaac.earthdatacloud.nasa.gov/hydrocron/v1/timeseries?collection_name=SWOT_L2_HR_RiverSP_2.0&feature=Reach&feature_id=78340600051&output=geojson&start_time=2024-01-25T00:00:00Z&end_time=2024-02-05T00:00:00Z&fields=reach_id,time_str,wse"
```
- **مثال الاستجابة:** ```text
فعلي مختصر: {"status":"200 OK","hits":2,"results":{"geojson":{"features":[{"properties":{"reach_id":"78340600051","time_str":"2024-01-30T09:38:22Z","wse":"386.1973","wse_units":"m"}}]}}}
```
- **دليل التحقق:** تم اختبار قراءة صغيرة فعلية مع إصدار مثبت؛ لا اتجاه مناخي مستنتج. قيد TLS قائم.
- **البديل:** ملفات SWOT الأصلية عبر CMR/PO.DAAC عند الحاجة لكل QA أو topology.

#### S11 — NOAA Climate Data Online (CDO)

- **التصنيف:** A
- **الحالة:** مقترح/موثق؛ لم يُختبر end-to-end
- **الجهة المالكة:** NOAA NCEI، وليست NASA
- **مرجع موارد التحدي:** R018؛ مدرج رسميًا في تحدي 2 تحت مصادر غير NASA.
- **وثائق المطورين:** [https://www.ncei.noaa.gov/cdo-web/webservices/v2](https://www.ncei.noaa.gov/cdo-web/webservices/v2)
- **Base URL / الرابط:** [https://www.ncei.noaa.gov/cdo-web/api/v2](https://www.ncei.noaa.gov/cdo-web/api/v2)
- **المسارات/طريقة الاستخدام:** GET /datasets، /stations، /datatypes، /data مع datasetid,stationid,startdate,enddate,units,limit,offset.
- **الوظيفة والملاءمة:** تحقق ببيانات محطات؛ تغطية محطة وقياس مختلفان عن متوسط pixel وإعادة التحليل.
- **البيانات/المدخلات:** مثل GHCND أو GSOM؛ TMAX/TMIN/PRCP حسب نوع المنتج. الوحدات وscale والأعلام تختلف؛ units=metric لا يبرر تجاهل تعريف الحقل.
- **المصادقة:** token في HTTP header؛ يُطلب من NOAA، وليس Earthdata ولا NASA key.
- **المجانية/التكلفة:** مجاني؛ الوثيقة تذكر 5 طلبات/ثانية و10,000 طلب/يوم لكل token.
- **الحدود والقيود:** pagination limit حتى 1000؛ قسم التواريخ حسب حدود dataset. station history واكتمالها ضروريان للاتجاه. لا نختلق محطة قريبة ذات تغطية كاملة.
- **الصيغ:** JSON عبر API؛ CSV/ملفات عبر قنوات أخرى.
- **مثال الطلب:** ```text
import os,httpx
r=httpx.get("https://www.ncei.noaa.gov/cdo-web/api/v2/datasets",
 headers={"token":os.environ["NOAA_TOKEN"]}, params={"limit":1}, timeout=30)
```
- **مثال الاستجابة:** ```text
شكل موثق: {"metadata":{"resultset":{"offset":1,"count":...}},"results":[{"id":"GHCND",...}]}؛ توضيحي، لم يُختبر.
```
- **دليل التحقق:** وثائق مقروءة؛ يتطلب token، ولم يجر اختبار بيانات.
- **البديل:** NASA POWER للمسار الأول، مع توضيح أنه reanalysis/grid لا station.

#### S12 — NASA Open APIs portal

- **التصنيف:** A/B/E
- **الحالة:** مقترح/موثق؛ لم يُختبر end-to-end
- **الجهة المالكة:** NASA؛ APIs متعددة مستقلة
- **مرجع موارد التحدي:** R028؛ تحدي 3.
- **وثائق المطورين:** [https://api.nasa.gov/](https://api.nasa.gov/)
- **Base URL / الرابط:** [https://api.nasa.gov (بوابة، وليست base موحدة لكل NASA)](https://api.nasa.gov (بوابة، وليست base موحدة لكل NASA))
- **المسارات/طريقة الاستخدام:** تختلف المسارات والجهات لكل خدمة؛ لا /earth عام مفترض. الصفحات الحالية تقول Earth API مؤرشفة واستُبدلت بـGIBS؛ Mars Rover API مؤرشفة؛ legacy APOD معلن أرشفته في 1 ديسمبر 2026.
- **الوظيفة والملاءمة:** فهرس لاكتشاف خدمات أخرى؛ أغلب astronomical media لا يضيف قياس اتجاه أرضي. لا تضف APOD للمشروع لمجرد «استخدام NASA API».
- **البيانات/المدخلات:** لا مجموعة بيانات واحدة؛ DONKI وOSDR وEPIC وغيرها لكل منها تعريفها.
- **المصادقة:** خدمات البوابة قد تتطلب api.data.gov key؛ DEMO_KEY للاستكشاف المحدود فقط. لا ينطبق على CMR/POWER/GIBS.
- **المجانية/التكلفة:** الافتراضي المنشور للمفتاح 1000 طلب/ساعة على خدمات البوابة، وDEMO_KEY 30/ساعة و50/يوم لكل IP؛ قد تختلف الخدمة.
- **الحدود والقيود:** راجع notices قبل اعتماد مسار قديم، ورؤوس X-RateLimit. الاستبدال التقني ليس تحويلًا علميًا لنفس الدقة أو المنتج.
- **الصيغ:** غالبًا JSON وروابط وسائط؛ حسب API.
- **مثال الطلب:** ```text
curl "https://api.nasa.gov/"
```
- **مثال الاستجابة:** ```text
فعلي: HTML catalog؛ لا يمثل استجابة بيانات API موحدة.
```
- **دليل التحقق:** البوابة مقروءة؛ لم يُختبر مفتاح. حالة archived مقتصرة على الخدمات التي أعلنتها البوابة صراحةً.
- **البديل:** الموصل العلمي المحدد، مثل CMR أو POWER أو AppEEARS.

#### S13 — EONET v3

- **التصنيف:** A/B
- **الحالة:** مختبَر في هذا البحث
- **الجهة المالكة:** NASA Earth Observatory
- **مرجع موارد التحدي:** إضافة من كتالوج NASA المفتوح المتفرع من R028؛ ليست رابطًا مستقلًا في Resources.
- **وثائق المطورين:** [https://eonet.gsfc.nasa.gov/docs/v3](https://eonet.gsfc.nasa.gov/docs/v3)
- **Base URL / الرابط:** [https://eonet.gsfc.nasa.gov/api/v3](https://eonet.gsfc.nasa.gov/api/v3)
- **المسارات/طريقة الاستخدام:** GET /events، /events/geojson، /categories، /sources؛ limit,status,start,end وbbox.
- **الوظيفة والملاءمة:** سياق للأحداث ومواضعها وروابط المصادر؛ ليس كتالوجًا كاملًا لكل الحرائق ولا ground truth لتدريب توقعات الخطر.
- **البيانات/المدخلات:** events,geometry,date,categories,sources؛ بعض magnitude fields اختيارية. تغطية تحريرية متغيرة؛ لا دقة رستر ثابتة.
- **المصادقة:** المسار المختبر بلا مفتاح.
- **المجانية/التكلفة:** عام ومجاني؛ لا حصة موحدة مثبتة.
- **الحدود والقيود:** bbox في EONET ترتيبه minLon,maxLat,maxLon,minLat؛ يختلف عن west,south,east,north الشائع. لا تحسب trend طبيعي من تغير تغطية الأخبار.
- **الصيغ:** JSON/GeoJSON وروابط صور/مصادر.
- **مثال الطلب:** ```text
curl "https://eonet.gsfc.nasa.gov/api/v3/events?limit=1&status=all"
```
- **مثال الاستجابة:** ```text
فعلي: object يحوي events؛ أول حدث مع id/title/categories/sources/geometry. لم نستخدمه لحساب معدل حدث.
```
- **دليل التحقق:** تم اختبار GET صغير صحيح؛ قيد TLS قائم.
- **البديل:** FIRMS للـdetections الكمية مع تجانس المنتج.

#### S14 — EPIC

- **التصنيف:** B
- **الحالة:** مختبَر في هذا البحث
- **الجهة المالكة:** NASA DSCOVR EPIC
- **مرجع موارد التحدي:** إضافة عبر كتالوج R028؛ ليست رابطًا مستقلًا في Resources.
- **وثائق المطورين:** [https://epic.gsfc.nasa.gov/about/api](https://epic.gsfc.nasa.gov/about/api)
- **Base URL / الرابط:** [https://epic.gsfc.nasa.gov](https://epic.gsfc.nasa.gov)
- **المسارات/طريقة الاستخدام:** GET /api/natural/date/{YYYY-MM-DD} و/api/enhanced/... و/api/natural/all؛ الصور /archive/{collection}/{Y}/{M}/{D}/{format}/{image}.png.
- **الوظيفة والملاءمة:** صورة full-disk للكرة الأرضية في العرض؛ لا مسار قياس اتجاه حراري محلي ولا Computer Vision بحد ذاته.
- **البيانات/المدخلات:** image,date,caption,centroid_coordinates ومواقع DSCOVR؛ تاريخ وأوقات بحسب الرصد. natural images ليست LST.
- **المصادقة:** الطلب المباشر المختبر بلا key؛ mirror api.nasa.gov له شروطه.
- **المجانية/التكلفة:** وصول عام مجاني؛ cache metadata والصور وتحقق من credits.
- **الحدود والقيود:** يرجع قائمة أسماء صور، ثم تحميل منفصل. لا تفترض كل يوم متاحًا أو أن pixels دقة أرضية متساوية.
- **الصيغ:** JSON metadata، PNG/JPEG.
- **مثال الطلب:** ```text
curl "https://epic.gsfc.nasa.gov/api/natural/date/2025-01-01"
```
- **مثال الاستجابة:** ```text
فعلي: مصفوفة metadata تضم image وdate وcaption وcoordinates؛ لم تُستعمل لقياس.
```
- **دليل التحقق:** تم اختبار metadata ليوم واحد؛ لم يُجر استدلال أو تنزيل كل الصور.
- **البديل:** GIBS لطبقات مؤرخة على خريطة.

#### S15 — NTRS

- **التصنيف:** A/E
- **الحالة:** مختبَر في هذا البحث
- **الجهة المالكة:** NASA Technical Reports Server
- **مرجع موارد التحدي:** R019؛ تحدي 2. الورقة المرجعية رابط PDF وليست API تحليل.
- **وثائق المطورين:** [https://ntrs.nasa.gov/](https://ntrs.nasa.gov/)
- **Base URL / الرابط:** [https://ntrs.nasa.gov/api](https://ntrs.nasa.gov/api)
- **المسارات/طريقة الاستخدام:** GET /citations/{citation_id}؛ رابط تنزيل الورقة /citations/20090042747/downloads/20090042747.pdf كما في Resources. عقد بحث واسع لم يُعتمد هنا.
- **الوظيفة والملاءمة:** مصدر منهجية وإسناد؛ ليس بيانات Chlorophyll جاهزة ولا حساب p-values.
- **البيانات/المدخلات:** record 20090042747 الخاص بتحليل SeaWiFS في مناطق ساحلية متأثرة بالأنهار. الدقة/التواتر تخص الدراسة الأصلية ولا تنطبق على خدمة metadata.
- **المصادقة:** قراءة citation والملف العام دون مفتاح.
- **المجانية/التكلفة:** وصول عام؛ حقوق المادة والإسناد حسب record، وليس كل PDF NASA بلا حقوق طرف ثالث.
- **الحدود والقيود:** لا تقرأ الورقة كبرهان أن Trend أي منتج آخر صالح؛ افتح كامل المنهجية عند استخدامها. مخطط citation قابل للتغير.
- **الصيغ:** JSON citation، PDF نص علمي.
- **مثال الطلب:** ```text
curl "https://ntrs.nasa.gov/api/citations/20090042747"
```
- **مثال الاستجابة:** ```text
فعلي: citation object يتضمن id=20090042747 وعنوانًا ومؤلفين وروابط تنزيل؛ لا سلسلة قياسات.
```
- **دليل التحقق:** تم اختبار metadata؛ هذا البحث لا يدعي إعادة تنفيذ الدراسة.
- **البديل:** أدلة SciPy/statsmodels ومراجع إحصاء أولية مناسبة للمهمة.

#### S16 — SVS / Earth Information Center

- **التصنيف:** A/B
- **الحالة:** مختبَر في هذا البحث
- **الجهة المالكة:** NASA Scientific Visualization Studio
- **مرجع موارد التحدي:** R120-R130؛ تحدي 14. إحدى عشرة إحالة موحدة في خدمة SVS.
- **وثائق المطورين:** [https://svs.gsfc.nasa.gov/help/](https://svs.gsfc.nasa.gov/help/)
- **Base URL / الرابط:** [https://svs.gsfc.nasa.gov](https://svs.gsfc.nasa.gov)
- **المسارات/طريقة الاستخدام:** GET /api/search/?search={text}&limit={n}&offset={n}؛ GET /api/{page_id}/.
- **الوظيفة والملاءمة:** صور وفيديو وmetadata وإسناد وموارد تعليمية وتفسيرية. لا تُعامل animation كبيانات تحليل أصلية أو مسار forecasting.
- **البيانات/المدخلات:** صفحات 5313 night lights، 3912 currents، 5669 aerosols، 5533 air quality، 5425 ocean، 5196 CO2، 5011 lightning، 4960 atmospheric river، 4950 GEDI، و13786 sonification. تاريخ الفيلم ودقته غير دقة المنتج العلمي الأصلية.
- **المصادقة:** API عامة بلا مفتاح في الاختبار.
- **المجانية/التكلفة:** API مجانية؛ احفظ credits وقيود الوسائط المحددة. تنزيل فيديوهات كبيرة ليس جزءًا من MVP.
- **الحدود والقيود:** search default 100 نتائج كما في help؛ استخدم limit/offset. حقول media تختلف، وتحميل الملف مستقل عن metadata. بعض العناصر غير أرضية مثل Caldwell73، فتؤجل.
- **الصيغ:** JSON metadata؛ ملفات صور/فيديو/صوت متنوعة عبر روابط media.
- **مثال الطلب:** ```text
curl "https://svs.gsfc.nasa.gov/api/5313/"
```
- **مثال الاستجابة:** ```text
فعلي: JSON page metadata مع title وcredits ومجموعات وسائط؛ تم التحقق من نوع المحتوى، لا استخراج قياس night lights.
```
- **دليل التحقق:** تم اختبار page API؛ جُلبت صفحات الموارد، لا rendering لكل فيلم.
- **البديل:** الرستر المصدر في DAAC عند حساب الاتجاه بدل animation.

#### S17 — JPL Horizons

- **التصنيف:** C (حساب فلكي)
- **الحالة:** مختبَر في هذا البحث
- **الجهة المالكة:** NASA JPL Solar System Dynamics
- **مرجع موارد التحدي:** R101؛ تحدي 11، منخفض الصلة بالاتجاهات الأرضية.
- **وثائق المطورين:** [https://ssd-api.jpl.nasa.gov/doc/horizons.html](https://ssd-api.jpl.nasa.gov/doc/horizons.html)
- **Base URL / الرابط:** [https://ssd.jpl.nasa.gov/api](https://ssd.jpl.nasa.gov/api)
- **المسارات/طريقة الاستخدام:** GET /horizons.api مع format وCOMMAND وOBJ_DATA وMAKE_EPHEM، أو إعدادات ephemerides موثقة.
- **الوظيفة والملاءمة:** مواضع وأفلاك وأزمنة كواكب/أجرام؛ مفيد للملاحة الفلكية لا سلسلة طقس أو LST.
- **البيانات/المدخلات:** COMMAND=399 للأرض في تجربة metadata؛ وحدات ephemerides والإطار الزمني والمركزي حسب الإعدادات.
- **المصادقة:** المسار المختبر بلا مفتاح.
- **المجانية/التكلفة:** عام مجاني؛ راجع سياسة JPL API ولا تنفذ طلبات متزامنة كثيفة.
- **الحدود والقيود:** راجع errors داخل body حتى مع 200، وثبّت مركز الإحداثيات/time scale؛ ليس خدمة map tiles.
- **الصيغ:** JSON envelope وresult نصي، أو text.
- **مثال الطلب:** ```text
curl "https://ssd.jpl.nasa.gov/api/horizons.api?format=json&COMMAND=%27399%27&OBJ_DATA=%27YES%27&MAKE_EPHEM=%27NO%27"
```
- **مثال الاستجابة:** ```text
فعلي: signature وresult يصفان جسم الأرض، دون error field. لم تُنتج ephemeris طويلة.
```
- **دليل التحقق:** تم اختبار object metadata فقط؛ مستبعد من MVP.
- **البديل:** لا بديل مطلوب للمشروع الأرضي.

#### S18 — Planetary Data System / LRO

- **التصنيف:** A
- **الحالة:** مختبَر في هذا البحث
- **الجهة المالكة:** NASA PDS؛ عقد أرشفة جامعية
- **مرجع موارد التحدي:** R091-R093؛ تحدي 9.
- **وثائق المطورين:** [https://nasa-pds.github.io/pds-api/guides/search/endpoints.html](https://nasa-pds.github.io/pds-api/guides/search/endpoints.html)
- **Base URL / الرابط:** [https://pds.nasa.gov/api/search/1](https://pds.nasa.gov/api/search/1)
- **المسارات/طريقة الاستخدام:** GET /products، /products/{lidvid}، /properties، /classes؛ q,keywords,fields,limit,sort,search-after. بعض المواصفات الأحدث تشير /api/registry/1؛ ثبّت نسخة العقد ولا تخلطها.
- **الوظيفة والملاءمة:** بيانات كواكب وقمر ومنها Diviner؛ لا تخلط حرارة القمر بحرارة سطح الأرض. مستبعد من MVP مع حفظه في الجرد.
- **البيانات/المدخلات:** PDS4 LID/LIDVID، منتجات متعددة بملفات labels وبيانات؛ الدقة/الوحدة/الزمن للمنتج.
- **المصادقة:** البحث العام المختبر دون مفتاح؛ ملفات الأرشيف وفق node.
- **المجانية/التكلفة:** عام وفق شروط dataset؛ لا تعمم ترخيص docs على البيانات.
- **الحدود والقيود:** تغطية registry غير كاملة وفق التحذير الرسمي. paginate بحجم صغير؛ نتيجة 404 لمنتج قد تعني عدم harvest. لا نمزج دليل v1.5 ومسار قديم في طلب واحد.
- **الصيغ:** JSON metadata وPDS4 XML labels وملفات علمية متنوعة.
- **مثال الطلب:** ```text
curl "https://pds.nasa.gov/api/search/1/products?limit=1"
```
- **مثال الاستجابة:** ```text
فعلي: JSON search response مع بيانات منتج؛ قراءة metadata لا تنزيل ملف علمي.
```
- **دليل التحقق:** تم اختبار search صغير؛ LRO/Diviner processing لم يُختبر.
- **البديل:** CMR للأرض؛ PDS غير مطلوب للنسخة الأولى.

#### S19 — OSDR Biological Data / Search

- **التصنيف:** A
- **الحالة:** مختبَر في هذا البحث
- **الجهة المالكة:** NASA Open Science Data Repository
- **مرجع موارد التحدي:** R030,R031؛ تحدي 3.
- **وثائق المطورين:** [https://www.nasa.gov/osdr-api/](https://www.nasa.gov/osdr-api/)
- **Base URL / الرابط:** [https://osdr.nasa.gov](https://osdr.nasa.gov)
- **المسارات/طريقة الاستخدام:** GET /osdr/data/search?term={keyword} كما هو مرتبط في Resources؛ APIs أحدث للبيولوجيا موصوفة في الصفحة الرسمية، فلا يُفترض تطابق schema القديمة والجديدة.
- **الوظيفة والملاءمة:** بحث تجارب بيولوجيا الفضاء؛ API فعلية لكن غير ملائمة لقياس اتجاه أرضي.
- **البيانات/المدخلات:** metadata للتجارب/العينات، لا متغيرات مناخية أو grid resolution. accession معرف الدراسة.
- **المصادقة:** البحث العام المختبر بلا مفتاح؛ ملفات مقيدة إن وجدت تخضع لشروطها.
- **المجانية/التكلفة:** وصول عام للبيانات المفتوحة؛ لا حصة موحدة مثبتة في المصدر المقروء.
- **الحدود والقيود:** لا تستخدم أحجام العينات أو تغير عدد الدراسات كاتجاه بيئي. paginate بالمعاملات الموثقة للواجهة المختارة.
- **الصيغ:** JSON metadata وروابط ملفات؛ صيغ الدراسة مختلفة.
- **مثال الطلب:** ```text
curl "https://osdr.nasa.gov/osdr/data/search?term=Arabidopsis&size=1"
```
- **مثال الاستجابة:** ```text
فعلي: JSON search response؛ لم يُفسر محتواه كبيانات أرضية.
```
- **دليل التحقق:** تم اختبار search response؛ لا تنزيل/تحليل biology. مستبعد من MVP.
- **البديل:** لا بديل مطلوب في EarthTrend.

#### S20 — DONKI / RadLab

- **التصنيف:** A (متخصص)
- **الحالة:** مقترح/موثق؛ لم يُختبر end-to-end
- **الجهة المالكة:** NASA CCMC وNASA OSDR
- **مرجع موارد التحدي:** R029,R032؛ تحدي 3. خدمتان مستقلتان محفوظتان في هذه البطاقة منخفضة الصلة.
- **وثائق المطورين:** [https://ccmc.gsfc.nasa.gov/tools/DONKI/](https://ccmc.gsfc.nasa.gov/tools/DONKI/)
- **Base URL / الرابط:** [DONKI: https://api.nasa.gov/DONKI؛ RadLab: اتبع API docs بالرابط الأصلي](DONKI: https://api.nasa.gov/DONKI؛ RadLab: اتبع API docs بالرابط الأصلي)
- **المسارات/طريقة الاستخدام:** DONKI GET /CME أو /FLR مع startDate,endDate,api_key حسب كتالوج NASA. RadLab endpoint/parameters لم تُثبت من صفحة GUI المسترجعة، فلا نخترع مسار بيانات.
- **الوظيفة والملاءمة:** طقس فضائي وأحداث شمسية، وdosimetry فضائية في RadLab؛ لا تقيس حرارة أو مطر الأرض.
- **البيانات/المدخلات:** CME/FLR وقياسات إشعاع بحسب التجربة. الوحدات والتاريخ والدقة تخص الحقل، لا وحدة عالمية مشتركة.
- **المصادقة:** DONKI key بوابة NASA أو DEMO_KEY؛ RadLab حسب العقد الذي يلزم قراءته.
- **المجانية/التكلفة:** حصة DONKI تتبع بوابة NASA حيث تنطبق؛ لا تُنقل إلى RadLab.
- **الحدود والقيود:** لا توجد صلة علمية كافية لإدخالهما إلى MVP؛ لا تُختبر خدمات لا نحتاجها لمجرد زيادة عدد APIs.
- **الصيغ:** DONKI JSON؛ RadLab غير مثبت في هذه الجلسة.
- **مثال الطلب:** ```text
# Documented DONKI shape only; not executed.
# GET https://api.nasa.gov/DONKI/CME?startDate=2025-01-01&endDate=2025-01-02&api_key=${NASA_API_KEY}
```
- **مثال الاستجابة:** ```text
شكل موثق لـDONKI: مصفوفة أحداث مع activityID وstartTime؛ لا استجابة فعلية هنا. RadLab response متعذر التحقق.
```
- **دليل التحقق:** DONKI موثق ولم يُختبر؛ RadLab API route غير متحقق. مستبعدان من النسخة الأولى.
- **البديل:** CMR/POWER/AppEEARS للبيئة الأرضية.

#### S21 — IRSA / SPHEREx

- **التصنيف:** A
- **الحالة:** مقترح/موثق؛ لم يُختبر end-to-end
- **الجهة المالكة:** NASA/IPAC IRSA
- **مرجع موارد التحدي:** R103,R104؛ تحدي 12.
- **وثائق المطورين:** [https://irsa.ipac.caltech.edu/docs/program_interface/](https://irsa.ipac.caltech.edu/docs/program_interface/)
- **Base URL / الرابط:** [https://irsa.ipac.caltech.edu](https://irsa.ipac.caltech.edu)
- **المسارات/طريقة الاستخدام:** TAP/SIA وغيرها موثقة في IRSA؛ TAP sync المعتاد /TAP/sync مع REQUEST=doQuery وLANG=ADQL. جداول SPHEREx الفعلية يجب اكتشافها من TAP_SCHEMA، ولم تُثبت هنا.
- **الوظيفة والملاءمة:** أرشيف صور/أطياف فلكية؛ لا صلة مباشرة بالسلسلة الأرضية.
- **البيانات/المدخلات:** SPHEREx وبيانات فلكية أخرى؛ FITS وmetadata. إحداثيات سماوية لا lon/lat أرضية.
- **المصادقة:** قراءة بعض الخدمات عامة؛ حالة data release وشروط الوصول لكل جدول مستقلة.
- **المجانية/التكلفة:** وصول public archives دون فوترة API مثبتة؛ مهام كبيرة لها حدود الخدمة.
- **الحدود والقيود:** صفحة program_interface أعادت 403 في جلبنا. لا يُقدم جدول/استعلام SPHEREx مفترض على أنه verified. لا SLA مثبتة.
- **الصيغ:** FITS، VOTable، JSON/CSV حسب البروتوكول.
- **مثال الطلب:** ```text
# Template, not tested and not a verified SPHEREx query:
# POST https://irsa.ipac.caltech.edu/TAP/sync (ADQL against a discovered table)
```
- **مثال الاستجابة:** ```text
لا استجابة API متحققة في الجلسة؛ توثيق الوصول جزئي.
```
- **دليل التحقق:** رابط المورد موثق، لكن developer page تعذرت؛ لا اختبار API. مستبعد من MVP.
- **البديل:** ليس مطلوبًا لمشروع EarthTrend.

#### S22 — Moon/Mars Trek / QuickMap

- **التصنيف:** B/E
- **الحالة:** مقترح/موثق؛ لم يُختبر end-to-end
- **الجهة المالكة:** NASA JPL Trek؛ LROC/ASU QuickMap خدمة أخرى
- **مرجع موارد التحدي:** R033,R099,R100؛ تحديات 3 و10 و11.
- **وثائق المطورين:** [https://trek.nasa.gov/tiles/apidoc/trekAPI.html](https://trek.nasa.gov/tiles/apidoc/trekAPI.html)
- **Base URL / الرابط:** [https://trek.nasa.gov (Trek)؛ https://quickmap.lroc.asu.edu (QuickMap)](https://trek.nasa.gov (Trek)؛ https://quickmap.lroc.asu.edu (QuickMap))
- **المسارات/طريقة الاستخدام:** Trek لديه توثيق layer/tile APIs؛ لم تُثبت layer IDs ومسارات فعالة في هذا البحث. QuickMap واجهة مستقلة؛ API عامة محددة لم تثبت هنا.
- **الوظيفة والملاءمة:** خرائط كواكب وقمر، منخفضة الصلة بالأرض. صفحة HTML لا تجعلها مكتبة Python.
- **البيانات/المدخلات:** طبقات تضاريس/صور كوكبية بدقة وcoverage خاصة بكل layer. لا متغير أرضي جاهز.
- **المصادقة:** الواجهات عامة؛ أي auth إضافي حسب خدمة الطبقات.
- **المجانية/التكلفة:** تكلفة API/حصة ثابتة غير مثبتة هنا؛ حقوق الطبقات منفصلة.
- **الحدود والقيود:** لا تعيد استخدام matrixset الأرض مع القمر، ولا تخمن URL tiles؛ اكتشف الطبقات من العقد.
- **الصيغ:** Web maps وtiles/metadata وفق API المتحققة مستقبلًا.
- **مثال الطلب:** ```text
curl "https://trek.nasa.gov/tiles/apidoc/trekAPI.html"
```
- **مثال الاستجابة:** ```text
فعلي: صفحة docs HTML، دون tile data call.
```
- **دليل التحقق:** توثيق جزئي فقط، لا API end-to-end. مستبعد من MVP.
- **البديل:** GIBS+واجهة خريطة أرضية.

#### S23 — NEX-GDDP-CMIP6 / THREDDS

- **التصنيف:** A/C (ملفات وإسقاطات مناخية)
- **الحالة:** مقترح/موثق؛ لم يُختبر end-to-end
- **الجهة المالكة:** NASA NEX / NCCS
- **مرجع موارد التحدي:** إضافة NASA مقترحة بسبب صورة المستخدم؛ لم يظهر رابطها في الموارد المستخرجة لعام 2026.
- **وثائق المطورين:** [https://www.nccs.nasa.gov/data-collections/nex-gddp-cmip6/](https://www.nccs.nasa.gov/data-collections/nex-gddp-cmip6/)
- **Base URL / الرابط:** [https://ds.nccs.nasa.gov/thredds](https://ds.nccs.nasa.gov/thredds)
- **المسارات/طريقة الاستخدام:** catalog تحت /catalog/AMES/NEX/GDDP-CMIP6/، تنزيل /fileServer/AMES/NEX/GDDP-CMIP6/…، وNetCDF Subset /ncss/grid/AMES/NEX/GDDP-CMIP6/… وفق dataset path من الكتالوج. نسخة S3 عامة مرتبطة رسميًا.
- **الوظيفة والملاءمة:** المسار المطلوب لسيناريوهات حتى 2100 في شاشة الصورة؛ منفصل عن ARIMA، ومؤجل بعد MVP.
- **البيانات/المدخلات:** 0.25° يومي، historical 1950-2014 وسيناريوهات 2015-2100 بحسب الملف. tas/tasmin/tasmax K وpr kg m-2 s-1 ومتغيرات أخرى بحسب النموذج/النسخة؛ ssp126/245/370/585. حدود جنوبية ودقة ومجال كل منتج من technical note، لا نفترض دقة 25 km متساوية عالميًا.
- **المصادقة:** تنزيل public files بحسب القناة؛ S3 anonymous للبيانات العامة حيث ينص registry؛ لا مطلوب GPU.
- **المجانية/التكلفة:** البيانات متاحة عامة، لكن تنزيل ensemble وتخزينه وcloud egress قد يكلف. ترخيص CMIP6/NEX قد يشمل CC-BY-SA 4.0 أو غيره بحسب الملف/الموديل؛ راجع metadata والنشرة ولا تنسب ترخيصًا واحدًا عميانيًا.
- **الحدود والقيود:** الأرشيف كبير جدًا؛ subset منطقة/متغير/نموذج/سنة قبل التحليل. استعمل نفس model members والنسخة للمقارنة، واحترم calendars. لا تفسر ensemble spread كاحتمال معاير دون أساس.
- **الصيغ:** NetCDF4؛ catalog XML وOPeNDAP/NCSS حسب الخادم.
- **مثال الطلب:** ```text
# Obtain a dataset path from the official catalog first.
# GET https://ds.nccs.nasa.gov/thredds/catalog/AMES/NEX/GDDP-CMIP6/catalog.xml
```
- **مثال الاستجابة:** ```text
شكل موثق: THREDDS catalog XML يحوي datasets وservice links، ثم NetCDF subset. لم يُختبر ملف بيانات أو ensemble في الجلسة.
```
- **دليل التحقق:** موثق رسميًا ولم يُختبر تنزيله. ليس موردًا مستخرجًا من تحدي 2026؛ إضافة موضحة.
- **البديل:** NASA NEX CMIP5 فقط إذا اشترطنا RCP في واجهة قديمة؛ لا مجرد إعادة تسمية SSP.

#### S24 — Google Earth Engine

- **التصنيف:** C / SDK خارجي
- **الحالة:** مقترح/موثق؛ لم يُختبر end-to-end
- **الجهة المالكة:** Google
- **مرجع موارد التحدي:** إضافة خارجية مقترحة، غير مدرجة ضمن الجرد الحالي.
- **وثائق المطورين:** [https://developers.google.com/earth-engine/guides/access](https://developers.google.com/earth-engine/guides/access)
- **Base URL / الرابط:** [https://earthengine.googleapis.com/v1](https://earthengine.googleapis.com/v1)
- **المسارات/طريقة الاستخدام:** Python SDK ee.Initialize(project=...)، ImageCollection.filterDate/filterBounds/reduceRegion؛ REST مشاريع وقيم/export وفق الوثائق. لا URL سرية أو API عامة بلا تسجيل.
- **الوظيفة والملاءمة:** حسابات مناطق واسعة لـMODIS/HLS/NEX دون تنزيل كل المشاهد، إذا تحققت الأهلية والحصص. ليس ضروريًا لنقطة POWER.
- **البيانات/المدخلات:** معرّفات كتالوج GEE مثل MODIS/061/MOD11A2 وNASA/GDDP-CMIP6 يجب التحقق من صفحة dataset عند التنفيذ؛ units/QA من الكتالوج.
- **المصادقة:** حساب Google ومشروع Cloud مفعّل لـEarth Engine وOAuth/service account مناسب. منفصل عن Gemini API key.
- **المجانية/التكلفة:** استخدام غير تجاري مؤهل يحتاج تسجيلًا/verification وقد يخضع لحدود؛ التجاري والفئات المدفوعة لها تسعير منفصل. لا نفعل billing ولا ندعي مجانية غير مشروطة.
- **الحدود والقيود:** reduceRegion scale/CRS/maxPixels وtileScale وexports لها حدود وحوسبة. اعمل QA وarea weights صراحة؛ لا تستخدم bestEffort دون تسجيل تغيّر الدقة.
- **الصيغ:** JSON للنتائج الصغيرة، وexports CSV/GeoTIFF/TFRecord وفق العملية.
- **مثال الطلب:** ```text
# Proposed, not executed:
import ee
ee.Initialize(project="YOUR_REGISTERED_PROJECT")
collection=ee.ImageCollection("MODIS/061/MOD11A2").filterDate("2025-01-01","2025-02-01")
```
- **مثال الاستجابة:** ```text
شكل توضيحي: dictionary ناتج reduceRegion أو task ID لعملية export؛ لا استجابة فعلية.
```
- **دليل التحقق:** موثق رسميًا؛ لم يسجل مشروع ولم يُختبر OAuth أو معالجة.
- **البديل:** AppEEARS أو ملفات NASA+Python دون اعتماد Google إضافي.

### 9.3 تفاصيل المنتجات وقراءة الوحدات

| المجموعة | الجهة/المنتج | layers/units | coverage | طريقة الوصول | تحذير | مصدر رسمي |
|---|---|---|---|---|---|---|
| MOD11C3.061 | Terra MODIS / LP DAAC | LST_Day_CMG,LST_Night_CMG؛ K = raw×0.02 ثم °C؛ QC_Day/QC_Night | 2000-02 فصاعدًا بحسب holdings؛ عالمي 0.05°، شهري، إصدار 6.1 | CMR/تنزيل HDF4؛ ليس مضمونًا ضمن AppEEARS | Clear-sky sampling، emissivity وQA؛ اختبار CMR أثبت وجود المجموعة وgranule فقط | [https://lpdaac.usgs.gov/products/mod11c3v061/](https://lpdaac.usgs.gov/products/mod11c3v061/) |
| MOD11A2.061 | Terra MODIS / LP DAAC | LST_Day_1km,LST_Night_1km؛ scale 0.02 K، QC_Day/QC_Night | من 2000؛ عالمي أرضي، 1 km sinusoidal، مركب 8 أيام | AppEEARS أو CMR؛ تم اختبار layer catalog | ليس mean air temperature؛ احفظ اختلاف النهار/الليل ووقت المرور | [https://lpdaac.usgs.gov/products/mod11a2v061/](https://lpdaac.usgs.gov/products/mod11a2v061/) |
| MOD13A3.061 | Terra MODIS / LP DAAC | 1 km monthly NDVI/EVI؛ scale 0.0001، بلا وحدة؛ quality/reliability | من 2000؛ 1 km، شهري، أرضي | AppEEARS/CMR بحسب الكتالوج | السحب والهباء وتشبع NDVI؛ لا تحسب مساحة غابة من NDVI threshold غير متحقق | [https://lpdaac.usgs.gov/products/mod13a3v061/](https://lpdaac.usgs.gov/products/mod13a3v061/) |
| GPM_3IMERGM / 07 | NASA GPM / GES DISC | precipitation بوحدة mm/hr في منتج monthly؛ variable metadata تحكم الاسم النهائي | IMERG V07 يغطي من يونيو 2000 بحسب المنتج؛ 0.1°، شهري Final | Giovanni/CMR/ملفات GES DISC | تحويله إلى mm/month يحتاج عدد ساعات الفترة؛ Early/Late/Final ليست إصدارات متبادلة بلا فحص | [https://gpm.nasa.gov/data/imerg](https://gpm.nasa.gov/data/imerg) |
| GLDAS_NOAH025_M / 2.1 | NASA GES DISC | Tair_f_inst K، Rainf_f_tavg kg m-2 s-1، متغيرات model أخرى | من 2000، 0.25° أرضي، شهري؛ 3H منتج منفصل | Giovanni/CMR/NetCDF | نموذج/forcing لا محطة رصد؛ فرق inst مقابل tavg يجب تفسيره من المنتج | [https://ldas.gsfc.nasa.gov/gldas/model-output](https://ldas.gsfc.nasa.gov/gldas/model-output) |
| M2TMNXSLV / 5.12.4 | NASA MERRA-2 / GES DISC | T2M K، متغيرات أخرى حسب collection؛ M2TMNXFLX للهطول مثال مجموعة مختلفة | من 1980، 0.5° latitude×0.625° longitude، شهري؛ منتجات ساعة مستقلة | CMR/GES DISC/Giovanni إن ظهر في capabilities | لا يساوي القياس المباشر؛ لا تخلط M2IMNX instantaneous وM2TMNX monthly mean | [https://gmao.gsfc.nasa.gov/reanalysis/MERRA-2/](https://gmao.gsfc.nasa.gov/reanalysis/MERRA-2/) |
| POWER T2M / PRECTOTCORR | NASA POWER، مصادر MERRA2 وغيرها | T2M C، daily PRECTOTCORR mm/day؛ units من response | Daily meteorology من 1981؛ grid source-native، near-real-time حسب متغير؛ monthly مستقل | REST S05؛ قيم فعلية اختُبرت | يفصل 13th-month summary؛ monthly sample ليس LST سطحية أو station | [https://power.larc.nasa.gov/docs/services/api/temporal/](https://power.larc.nasa.gov/docs/services/api/temporal/) |
| HLSL30.020 / HLSS30.020 | NASA HLS، Landsat/Sentinel-2 | ست حزم reflectance وFmask؛ scale/QA حسب الإصدار؛ NDVI مشتق بلا وحدة | HLS v2 دقة 30m؛ L30 من Landsat 8/9 منذ 2013، S30 من Sentinel منذ 2015 بحسب holdings؛ cadence حسب acquisition/cloud | CMR/earthaccess/ملفات COG؛ للتصوير وPrithvi الاختياري | وحّد الحزم والموقع والتاريخ والـmask؛ لا يغطي 2005-2012 لتجربة 2005-2025 | [https://hls.gsfc.nasa.gov/products/](https://hls.gsfc.nasa.gov/products/) |
| SPL3SMP / Version 9 (مرجع متحقق) | NASA SMAP / NSIDC | soil_moisture بوحدة m³/m³ وأعلام retrieval_qual_flag | من 2015؛ daily 36 km EASE-Grid، التواتر الفعلي للمرور والتغطية متغير | CMR/NSIDC؛ الإصدار المتاح حاليًا يثبت بالبحث قبل التنفيذ | ليس رطوبة كامل root-zone؛ الثلج/التجمد والنبات يؤثران الاسترجاع | [https://nsidc.org/data/spl3smp/versions/9](https://nsidc.org/data/spl3smp/versions/9) |
| ECO_L2T_LSTE / 002 | NASA ECOSTRESS / LP DAAC | LST K مع emissivity وQC حسب layer metadata | من 2018؛ نحو 70m، tiled، مرور ISS غير منتظم | CMR/AppEEARS إذا أكد capabilities | لا تفترض وجود قياس يومي لكل مكان؛ short record لا يبرر trend عقود | [https://www.earthdata.nasa.gov/data/catalog/lpcloud-eco-l2t-lste-002](https://www.earthdata.nasa.gov/data/catalog/lpcloud-eco-l2t-lste-002) |
| SRTMGL1 / 003 | NASA/USGS | elevation m؛ ليس سلسلة زمنية | مهمة فبراير 2000؛ arc-second نحو 30m، غالبًا 60N-56S؛ static | AppEEARS/CMR بحسب المنتج | مرجع تضاريس/تصحيح فقط؛ إعادة استعماله كل سنة لا تصنع اتجاه ارتفاع | [https://www.earthdata.nasa.gov/data/instruments/srtm](https://www.earthdata.nasa.gov/data/instruments/srtm) |
| GEDI02_A / 002 (مرشح) | NASA GEDI / LP DAAC | rh98 أو RH metrics m وquality_flag/degrade_flag حسب product guide | من 2019؛ footprints ليدار نحو 25m، تغطية ISS تقريبًا 51.6N-51.6S، فترات توقف ممكنة | CMR/LP DAAC HDF5؛ تأكد الإصدار المتاح | ليس raster غطاء شامل، ولا mean تغير ارتفاع forests دون ضبط sampling | [https://gedi.umd.edu/data/](https://gedi.umd.edu/data/) |
| AIRS3STM / 7.0؛ OMNO2d / 003 (مرشحان) | NASA GES DISC | AIRS temperature profiles K؛ OMI NO2 columns molecules/cm² بحسب layer | AIRS من 2002، monthly 1° عادة؛ OMI من 2004، daily 0.25° في OMNO2d | CMR/Giovanni إن أكدت capabilities | altitude/pressure level مهم للحرارة؛ QA وrow anomaly مهمان لـOMI؛ لم تُختبر هذه المجموعات | [https://disc.gsfc.nasa.gov/](https://disc.gsfc.nasa.gov/) |
| SWOT_L2_HR_RiverSP_D / 2.0 | NASA/CNES SWOT / PO.DAAC | wse m، slope m/m؛ Quality وأعلام المنتج | من 2023، river features ومدارات غير يومية؛ ليس grid climate | Hydrocron S10؛ اختُبر 2.0 صراحة | تغير SWORD IDs والنسخ؛ سجل قصير، أعلام null والـquality ضرورية | [https://podaac.github.io/hydrocron/](https://podaac.github.io/hydrocron/) |
| FIRMS MODIS_SP / VIIRS_SNPP_SP | NASA FIRMS | fire detections,frp MW؛ coordinates وconfidence | MODIS نحو 1km وVIIRS 375m؛ تواريخ كل SOURCE عبر availability | S06؛ API metadata وثيقة فقط | نشاط حراري لا burned area ولا probability حريق؛ حساسية الحساس والتوقيت تختلف | [https://firms.modaps.eosdis.nasa.gov/api/area/](https://firms.modaps.eosdis.nasa.gov/api/area/) |
| NEX-GDDP-CMIP6 | NASA NEX / NCCS؛ إضافة مقترحة | tas K، pr kg m-2 s-1؛ SSP ensemble | 1950-2014 historical و2015-2100 scenarios؛ daily 0.25° | THREDDS/S3؛ S23، لم يُختبر ملف | إسقاط مناخي مشروط، calendars وموديلات ونسخة وانحياز؛ لا صورة NASA مرصودة للمستقبل | [https://www.nccs.nasa.gov/data-collections/nex-gddp-cmip6/](https://www.nccs.nasa.gov/data-collections/nex-gddp-cmip6/) |


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
| NASA Space Science Data Coordinated Archive (NSSDCA) | [https://nssdc.gsfc.nasa.gov/](https://nssdc.gsfc.nasa.gov/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Abandoned but not Forgotten: Storytelling about NASA&#x27;s Discarded Equipment on the Moon and Mars</span> |
| Apollo Lunar Modules | [https://nssdc.gsfc.nasa.gov/nmc/spacecraft/display.action?id=1969-059C](https://nssdc.gsfc.nasa.gov/nmc/spacecraft/display.action?id=1969-059C) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Abandoned but not Forgotten: Storytelling about NASA&#x27;s Discarded Equipment on the Moon and Mars</span> |
| Lunar Roving Vehicles (LRVs) | [https://nssdc.gsfc.nasa.gov/nmc/spacecraft/display.action?id=1971-063C](https://nssdc.gsfc.nasa.gov/nmc/spacecraft/display.action?id=1971-063C) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Abandoned but not Forgotten: Storytelling about NASA&#x27;s Discarded Equipment on the Moon and Mars</span> |
| ALSEP Scientific Packages | [https://nssdc.gsfc.nasa.gov/nmc/spacecraft/display.action?id=1969-099C](https://nssdc.gsfc.nasa.gov/nmc/spacecraft/display.action?id=1969-099C) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Abandoned but not Forgotten: Storytelling about NASA&#x27;s Discarded Equipment on the Moon and Mars</span> |
| Surveyor Landers | [https://science.nasa.gov/mission/surveyor-3/](https://science.nasa.gov/mission/surveyor-3/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Abandoned but not Forgotten: Storytelling about NASA&#x27;s Discarded Equipment on the Moon and Mars</span> |
| Sojourner Rover | [https://science.nasa.gov/mission/mars-pathfinder/](https://science.nasa.gov/mission/mars-pathfinder/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Abandoned but not Forgotten: Storytelling about NASA&#x27;s Discarded Equipment on the Moon and Mars</span> |
| Spirit & Opportunity | [https://science.nasa.gov/mission/mars-exploration-rovers-spirit-and-opportunity/](https://science.nasa.gov/mission/mars-exploration-rovers-spirit-and-opportunity/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Abandoned but not Forgotten: Storytelling about NASA&#x27;s Discarded Equipment on the Moon and Mars</span> |
| Viking 1 & 2 Landers | [https://science.nasa.gov/mission/viking-1/](https://science.nasa.gov/mission/viking-1/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Abandoned but not Forgotten: Storytelling about NASA&#x27;s Discarded Equipment on the Moon and Mars</span> |
| Phoenix & InSight Landers | [https://science.nasa.gov/mission/insight/](https://science.nasa.gov/mission/insight/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Abandoned but not Forgotten: Storytelling about NASA&#x27;s Discarded Equipment on the Moon and Mars</span> |
| Dawn Spacecraft | [https://science.nasa.gov/mission/dawn/](https://science.nasa.gov/mission/dawn/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Abandoned but not Forgotten: Storytelling about NASA&#x27;s Discarded Equipment on the Moon and Mars</span> |
| NEAR Shoemaker | [https://science.nasa.gov/mission/near-shoemaker/](https://science.nasa.gov/mission/near-shoemaker/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Abandoned but not Forgotten: Storytelling about NASA&#x27;s Discarded Equipment on the Moon and Mars</span> |
| Pioneer 10 & 11 | [https://science.nasa.gov/mission/pioneer-10/](https://science.nasa.gov/mission/pioneer-10/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Abandoned but not Forgotten: Storytelling about NASA&#x27;s Discarded Equipment on the Moon and Mars</span> |
| Ingenuity Helicopter | [https://science.nasa.gov/mission/mars-2020-perseverance/ingenuity-mars-helicopter/](https://science.nasa.gov/mission/mars-2020-perseverance/ingenuity-mars-helicopter/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Abandoned but not Forgotten: Storytelling about NASA&#x27;s Discarded Equipment on the Moon and Mars</span> |
| Kepler Space Telescope | [https://science.nasa.gov/mission/kepler/](https://science.nasa.gov/mission/kepler/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Abandoned but not Forgotten: Storytelling about NASA&#x27;s Discarded Equipment on the Moon and Mars</span> |
| Giovanni | [https://giovanni.gsfc.nasa.gov/](https://giovanni.gsfc.nasa.gov/) | NASA Data & Resources | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Be An Earth System Trend Detective!</span> |
| Hydrology Time Series | [https://disc.gsfc.nasa.gov/information/tools?title=Hydrology%20Time%20Series](https://disc.gsfc.nasa.gov/information/tools?title=Hydrology%20Time%20Series) | NASA Data & Resources | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Be An Earth System Trend Detective!</span> |
| AppEEARS | [https://appeears.earthdatacloud.nasa.gov/](https://appeears.earthdatacloud.nasa.gov/) | NASA Data & Resources | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Be An Earth System Trend Detective!</span> |
| Climate Data Online (CDO) | [https://www.ncei.noaa.gov/cdo-web/](https://www.ncei.noaa.gov/cdo-web/) | NASA Data & Resources | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Be An Earth System Trend Detective!</span> |
| Time-Series Analysis of Remotely-Sensed SeaWiFS Chlorophyll in River-Influenced Coastal Regions | [https://ntrs.nasa.gov/api/citations/20090042747/downloads/20090042747.pdf](https://ntrs.nasa.gov/api/citations/20090042747/downloads/20090042747.pdf) | NASA Data & Resources | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Be An Earth System Trend Detective!</span> |
| Royal Netherlands Meteorological Institute (KNMI) Climate Explorer | [https://climexp.knmi.nl/](https://climexp.knmi.nl/) | شريك: KNMI | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Be An Earth System Trend Detective!</span> |
| Statistical test methods to detect trends in time series data | [https://medium.com/@snp.kriss/statistical-test-methods-to-detect-trends-in-time-series-data-b361a0ec530b](https://medium.com/@snp.kriss/statistical-test-methods-to-detect-trends-in-time-series-data-b361a0ec530b) | Space Agency Partner Resources | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Be An Earth System Trend Detective!</span> |
| A Comprehensive Guide to Statistical Significance | [https://www.statsig.com/perspectives/a-comprehensive-guide-to-statistical-significance](https://www.statsig.com/perspectives/a-comprehensive-guide-to-statistical-significance) | Space Agency Partner Resources | مساندة: سياق/مرجع أو بيانات مكملة؛ ليست بالضرورة NASA أو API | <span dir="ltr">Be An Earth System Trend Detective!</span> |
| Radarsat Constellation Mission (RCM) - Data / RADARSAT Constellation Mission (RCM) - Data | [https://donnees-data.asc-csa.gc.ca/en/dataset/rcm](https://donnees-data.asc-csa.gc.ca/en/dataset/rcm) | شريك: CSA | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Be An Earth System Trend Detective!</span>, <span dir="ltr">Dancing with the SARs</span>, <span dir="ltr">Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars</span> |
| Geo.ca | [http://geo.ca/](http://geo.ca/) | شريك: GEO Canada | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Be An Earth System Trend Detective!</span> |
| SWOT Mission - Information | [https://www.asc-csa.gc.ca/eng/satellites/swot/](https://www.asc-csa.gc.ca/eng/satellites/swot/) | شريك: CSA | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Be An Earth System Trend Detective!</span> |
| Monitoring and protecting our ecosystem from space | [https://www.asc-csa.gc.ca/eng/satellites/everyday-lives/monitoring-and-protecting-our-ecosystems-from-space.asp](https://www.asc-csa.gc.ca/eng/satellites/everyday-lives/monitoring-and-protecting-our-ecosystems-from-space.asp) | شريك: CSA | مساندة: سياق/مرجع أو بيانات مكملة؛ ليست بالضرورة NASA أو API | <span dir="ltr">Be An Earth System Trend Detective!</span> |
| Synthetic Aperture Radar python Tutorial / Synthetic Aperture Radar (SAR) Python Tutorial | [https://github.com/asc-csa/Synthetic_Aperture_Radar_Tutorial](https://github.com/asc-csa/Synthetic_Aperture_Radar_Tutorial) | Space Agency Partner Resources | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Be An Earth System Trend Detective!</span>, <span dir="ltr">Dancing with the SARs</span>, <span dir="ltr">Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars</span> |
| NASA Open APIs | [https://api.nasa.gov/](https://api.nasa.gov/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Build a Junior Astronaut Mission Trainer</span> |
| Space Weather Database Of Notifications, Knowledge, Information (DONKI) | [https://ccmc.gsfc.nasa.gov/tools/DONKI/](https://ccmc.gsfc.nasa.gov/tools/DONKI/) | NASA Data & Resources | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Build a Junior Astronaut Mission Trainer</span> |
| NASA Open Science Data Repository (OSDR) | [https://osdr.nasa.gov/bio/repo/](https://osdr.nasa.gov/bio/repo/) | NASA Data & Resources | مساندة: سياق/مرجع أو بيانات مكملة؛ ليست بالضرورة NASA أو API | <span dir="ltr">Build a Junior Astronaut Mission Trainer</span> |
| search API | [https://osdr.nasa.gov/osdr/data/search?term=KEYWORD](https://osdr.nasa.gov/osdr/data/search?term=KEYWORD) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Build a Junior Astronaut Mission Trainer</span> |
| RadLab (OSDR Radiation Dosimetry Database) | [https://visualization.osdr.nasa.gov/radlab/gui/data-api/](https://visualization.osdr.nasa.gov/radlab/gui/data-api/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Build a Junior Astronaut Mission Trainer</span> |
| Mars Trek / Jet Propulsion Laboratory’s (JPL) Mars Trek | [https://trek.nasa.gov/mars/](https://trek.nasa.gov/mars/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Build a Junior Astronaut Mission Trainer</span>, <span dir="ltr">Interplanetary Survival Guide: Martian Map</span> |
| Space resources for STEM and youth organizations | [https://www.asc-csa.gc.ca/eng/youth-educators/resources-stem-and-youth-organizations.asp](https://www.asc-csa.gc.ca/eng/youth-educators/resources-stem-and-youth-organizations.asp) | شريك: CSA | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Build a Junior Astronaut Mission Trainer</span> |
| Food production on the moon and in remote areas | [https://www.asc-csa.gc.ca/eng/youth-educators/toolkits/food-production/](https://www.asc-csa.gc.ca/eng/youth-educators/toolkits/food-production/) | شريك: CSA | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Build a Junior Astronaut Mission Trainer</span> |
| 5 Hazards of Human Spaceflight | [https://www.nasa.gov/hrp/hazards/](https://www.nasa.gov/hrp/hazards/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Create Health Monitoring Software for Astronauts on Space Missions</span> |
| Risks of Human Spaceflight | [https://www.nasa.gov/hrp/risks/](https://www.nasa.gov/hrp/risks/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Create Health Monitoring Software for Astronauts on Space Missions</span> |
| Ongoing HRP Research in Space | [https://www.nasa.gov/hrp/ongoing-hrp-research/](https://www.nasa.gov/hrp/ongoing-hrp-research/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Create Health Monitoring Software for Astronauts on Space Missions</span> |
| Monitoring Radiation for Astronaut Health | [https://www.asc-csa.gc.ca/eng/news/articles/2026/2026-02-26-monitoring-radiation-astronaut-health.asp](https://www.asc-csa.gc.ca/eng/news/articles/2026/2026-02-26-monitoring-radiation-astronaut-health.asp) | شريك: CSA | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Create Health Monitoring Software for Astronauts on Space Missions</span> |
| Why Do We Conduct Science Experiments in Space? | [https://www.asc-csa.gc.ca/eng/iss/science/why-do-we-conduct-science-experiments-in-space.asp](https://www.asc-csa.gc.ca/eng/iss/science/why-do-we-conduct-science-experiments-in-space.asp) | شريك: CSA | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Create Health Monitoring Software for Astronauts on Space Missions</span> |
| NASA Earthdata Search | [https://search.earthdata.nasa.gov/search](https://search.earthdata.nasa.gov/search) | NASA Data & Resources | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Dancing with the SARs</span> |
| ASF Data Search Vertex | [https://search.asf.alaska.edu/](https://search.asf.alaska.edu/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Dancing with the SARs</span> |
| NISAR Data User Guide | [https://nisar-docs.asf.alaska.edu/](https://nisar-docs.asf.alaska.edu/) | NASA Data & Resources | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Dancing with the SARs</span> |
| Intro to Remote Sensing | [https://www.earthdata.nasa.gov/learn/earth-observation-data-basics/remote-sensing](https://www.earthdata.nasa.gov/learn/earth-observation-data-basics/remote-sensing) | NASA Data & Resources | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Dancing with the SARs</span> |
| Intro to Synthetic Aperture Radar (SAR) | [https://www.earthdata.nasa.gov/learn/earth-observation-data-basics/sar](https://www.earthdata.nasa.gov/learn/earth-observation-data-basics/sar) | NASA Data & Resources | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Dancing with the SARs</span> |
| NASA ARSET Trainings | [https://appliedsciences.nasa.gov/get-involved/training](https://appliedsciences.nasa.gov/get-involved/training) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Dancing with the SARs</span> |
| NISAR StoryMaps | [https://nisar.jpl.nasa.gov/applications/arcgis-storymaps/](https://nisar.jpl.nasa.gov/applications/arcgis-storymaps/) | NASA Data & Resources | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Dancing with the SARs</span> |
| NISAR Applications White Papers | [https://nisar.jpl.nasa.gov/applications/societal-benefit/](https://nisar.jpl.nasa.gov/applications/societal-benefit/) | NASA Data & Resources | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Dancing with the SARs</span> |
| UAVSAR Postcards | [https://uavsar.jpl.nasa.gov/education/postcards.html](https://uavsar.jpl.nasa.gov/education/postcards.html) | NASA Data & Resources | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Dancing with the SARs</span> |
| RADARSAT 1 - Data | [https://donnees-data.asc-csa.gc.ca/en/dataset/radarsat1](https://donnees-data.asc-csa.gc.ca/en/dataset/radarsat1) | شريك: CSA | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Dancing with the SARs</span>, <span dir="ltr">Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars</span> |
| SAOCOM Catalogue | [https://catalogos.conae.gov.ar/catalogo/catalogoSatSaocomInfo.html](https://catalogos.conae.gov.ar/catalogo/catalogoSatSaocomInfo.html) | شريك: CONAE | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Dancing with the SARs</span> |
| SAOCOM Catalogue Registration | [https://www.argentina.gob.ar/noticias/la-informacion-saocom-cada-vez-mas-accesible](https://www.argentina.gob.ar/noticias/la-informacion-saocom-cada-vez-mas-accesible) | Space Agency Partner Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Dancing with the SARs</span> |
| Soil Moisture Active Passive (SMAP) | [https://www.earthdata.nasa.gov/data/platforms/space-based-platforms/smap](https://www.earthdata.nasa.gov/data/platforms/space-based-platforms/smap) | NASA Data & Resources | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Field Shift: Adapting Farms with NASA Data</span> |
| Global Precipitation Measurement (GPM) & IMERG | [https://gpm.nasa.gov/data](https://gpm.nasa.gov/data) | NASA Data & Resources | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Field Shift: Adapting Farms with NASA Data</span> |
| Landsat | [https://earthexplorer.usgs.gov/](https://earthexplorer.usgs.gov/) | NASA Data & Resources | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Field Shift: Adapting Farms with NASA Data</span> |
| MODIS | [https://lpdaac.usgs.gov/products/](https://lpdaac.usgs.gov/products/) | NASA Data & Resources | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Field Shift: Adapting Farms with NASA Data</span> |
| VIIRS | [https://search.earthdata.nasa.gov/search?q=VIIRS](https://search.earthdata.nasa.gov/search?q=VIIRS) | NASA Data & Resources | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Field Shift: Adapting Farms with NASA Data</span> |
| NASA POWER | [https://power.larc.nasa.gov/](https://power.larc.nasa.gov/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Field Shift: Adapting Farms with NASA Data</span> |
| Shuttle Radar Topography Mission (SRTM) | [https://www.earthdata.nasa.gov/data/instruments/srtm](https://www.earthdata.nasa.gov/data/instruments/srtm) | NASA Data & Resources | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Field Shift: Adapting Farms with NASA Data</span> |
| ECOSTRESS | [https://ecostress.jpl.nasa.gov/data](https://ecostress.jpl.nasa.gov/data) | NASA Data & Resources | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Field Shift: Adapting Farms with NASA Data</span> |
| USDA Ag Data Commons | [https://www.nal.usda.gov/services/agdatacommons](https://www.nal.usda.gov/services/agdatacommons) | NASA Data & Resources | مساندة: سياق/مرجع أو بيانات مكملة؛ ليست بالضرورة NASA أو API | <span dir="ltr">Field Shift: Adapting Farms with NASA Data</span> |
| Web Soil Survey (WSS) | [https://websoilsurvey.nrcs.usda.gov/app/](https://websoilsurvey.nrcs.usda.gov/app/) | NASA Data & Resources | مساندة: سياق/مرجع أو بيانات مكملة؛ ليست بالضرورة NASA أو API | <span dir="ltr">Field Shift: Adapting Farms with NASA Data</span> |
| Cropland Data Layer (CDL): CropScape | [https://nassgeodata.gmu.edu/CropScape/](https://nassgeodata.gmu.edu/CropScape/) | NASA Data & Resources | مساندة: سياق/مرجع أو بيانات مكملة؛ ليست بالضرورة NASA أو API | <span dir="ltr">Field Shift: Adapting Farms with NASA Data</span> |
| PRISM Climate Data | [https://prism.oregonstate.edu](https://prism.oregonstate.edu) | NASA Data & Resources | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Field Shift: Adapting Farms with NASA Data</span> |
| USDA NRCS SSURGO/STATSGO2 | [https://www.nrcs.usda.gov/resources/data-and-reports/soils](https://www.nrcs.usda.gov/resources/data-and-reports/soils) | NASA Data & Resources | مساندة: سياق/مرجع أو بيانات مكملة؛ ليست بالضرورة NASA أو API | <span dir="ltr">Field Shift: Adapting Farms with NASA Data</span> |
| National Agriculture Imagery Program (NAIP) | [https://naip-usdaonline.hub.arcgis.com/](https://naip-usdaonline.hub.arcgis.com/) | NASA Data & Resources | مساندة: سياق/مرجع أو بيانات مكملة؛ ليست بالضرورة NASA أو API | <span dir="ltr">Field Shift: Adapting Farms with NASA Data</span> |
| USGS National Land Cover Database (NLCD) | [https://www.usgs.gov/centers/eros/science/national-land-cover-database](https://www.usgs.gov/centers/eros/science/national-land-cover-database) | NASA Data & Resources | مساندة: سياق/مرجع أو بيانات مكملة؛ ليست بالضرورة NASA أو API | <span dir="ltr">Field Shift: Adapting Farms with NASA Data</span> |
| NLDAS/GLDAS: Land Data Assimilation Systems | [https://www.earthdata.nasa.gov/](https://www.earthdata.nasa.gov/) | NASA Data & Resources | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Field Shift: Adapting Farms with NASA Data</span> |
| FAO Global Agro-Ecological Zones (GAEZ) | [https://gaez.fao.org](https://gaez.fao.org) | NASA Data & Resources | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Field Shift: Adapting Farms with NASA Data</span> |
| CoCoRaHS | [https://www.cocorahs.org/Maps](https://www.cocorahs.org/Maps) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Field Shift: Adapting Farms with NASA Data</span> |
| USGS National Water Information Systems (NWIS) | [https://waterdata.usgs.gov/nwis](https://waterdata.usgs.gov/nwis) | NASA Data & Resources | مساندة: سياق/مرجع أو بيانات مكملة؛ ليست بالضرورة NASA أو API | <span dir="ltr">Field Shift: Adapting Farms with NASA Data</span> |
| USDA AMS Market News | [https://www.ams.usda.gov/market-news](https://www.ams.usda.gov/market-news) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Field Shift: Adapting Farms with NASA Data</span> |
| USDA NASS QuickStats | [https://quickstats.nass.usda.gov](https://quickstats.nass.usda.gov) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Field Shift: Adapting Farms with NASA Data</span> |
| OpenET | [https://openetdata.org](https://openetdata.org) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Field Shift: Adapting Farms with NASA Data</span> |
| USFS LANDFIRE | [https://www.landfire.gov](https://www.landfire.gov) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Field Shift: Adapting Farms with NASA Data</span> |
| Global Ecosystem Dynamics Investigation (GEDI) | [https://gedi.umd.edu/data](https://gedi.umd.edu/data) | NASA Data & Resources | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Field Shift: Adapting Farms with NASA Data</span> |
| Copernicus Sentinel-2: ESA: | [https://dataspace.copernicus.eu](https://dataspace.copernicus.eu) | شريك: ESA/Copernicus | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Field Shift: Adapting Farms with NASA Data</span> |
| ERA5: ECMWF Reanalysis | [https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=overview](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=overview) | شريك: ESA/Copernicus | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Field Shift: Adapting Farms with NASA Data</span> |
| PSI Data Repository: Combustion Science | [https://psi.nasa.gov/physci/repo/search?q=combustion](https://psi.nasa.gov/physci/repo/search?q=combustion) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Flame in Freefall: SI-Powered Fire Safety Insights from Microgravity Combustion Data</span> |
| NASA Combustion Science | [https://www.nasa.gov/glenn/glenn-expertise-space-exploration/physical-sciences-program/combustion-science/](https://www.nasa.gov/glenn/glenn-expertise-space-exploration/physical-sciences-program/combustion-science/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Flame in Freefall: SI-Powered Fire Safety Insights from Microgravity Combustion Data</span> |
| NASA ScienceCasts: The Power of Studying Combustion on the ISS | [https://www.youtube.com/watch?v=W1oXykoz9zg](https://www.youtube.com/watch?v=W1oXykoz9zg) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Flame in Freefall: SI-Powered Fire Safety Insights from Microgravity Combustion Data</span> |
| A Researcher’s Guide to International Space Station Combustion Science | [https://www.nasa.gov/missions/station/a-researchers-guide-to-combustion-science/](https://www.nasa.gov/missions/station/a-researchers-guide-to-combustion-science/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Flame in Freefall: SI-Powered Fire Safety Insights from Microgravity Combustion Data</span> |
| Apollo 1 | [https://sma.nasa.gov/sma-disciplines/accllp/apollo-1](https://sma.nasa.gov/sma-disciplines/accllp/apollo-1) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Flame in Freefall: SI-Powered Fire Safety Insights from Microgravity Combustion Data</span> |
| Apollo 13 | [https://sma.nasa.gov/sma-disciplines/accllp/apollo-13](https://sma.nasa.gov/sma-disciplines/accllp/apollo-13) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Flame in Freefall: SI-Powered Fire Safety Insights from Microgravity Combustion Data</span> |
| 25 Years Ago: Fire Aboard Space Station Mir | [https://www.nasa.gov/history/25-years-ago-fire-aboard-space-station-mir/](https://www.nasa.gov/history/25-years-ago-fire-aboard-space-station-mir/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Flame in Freefall: SI-Powered Fire Safety Insights from Microgravity Combustion Data</span> |
| Fireman’s Air Tanks | [https://spinoff.nasa.gov/node/9582](https://spinoff.nasa.gov/node/9582) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Flame in Freefall: SI-Powered Fire Safety Insights from Microgravity Combustion Data</span> |
| Fire Detector | [https://spinoff.nasa.gov/node/9407](https://spinoff.nasa.gov/node/9407) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Flame in Freefall: SI-Powered Fire Safety Insights from Microgravity Combustion Data</span> |
| New Technology for the Fire Attire | [https://spinoff.nasa.gov/node/9918](https://spinoff.nasa.gov/node/9918) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Flame in Freefall: SI-Powered Fire Safety Insights from Microgravity Combustion Data</span> |
| FIRMS NASA EARTHDATA: Fire Information for Resource Management System | [https://www.earthdata.nasa.gov/data/tools/firms](https://www.earthdata.nasa.gov/data/tools/firms) | NASA Data & Resources | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Harmonization of MODIS and VIIRS Hot Spots</span> |
| NASA Earthdata Search | [https://search.earthdata.nasa.gov/?utm_source=%27chatgpt.com%27](https://search.earthdata.nasa.gov/?utm_source=%27chatgpt.com%27) | NASA Data & Resources | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars</span> |
| NASA Worldview | [https://worldview.earthdata.nasa.gov/index.html?utm_source=%27chatgpt.com%27](https://worldview.earthdata.nasa.gov/index.html?utm_source=%27chatgpt.com%27) | NASA Data & Resources | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars</span> |
| NASA Planetary Data System (PDS) | [https://pds.nasa.gov/?utm_source=%27chatgpt.com%27](https://pds.nasa.gov/?utm_source=%27chatgpt.com%27) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars</span> |
| NASA Lunar Reconnaissance Orbiter (LRO) | [https://pds-geosciences.wustl.edu/missions/lro/?utm_source=%27chatgpt.com%27](https://pds-geosciences.wustl.edu/missions/lro/?utm_source=%27chatgpt.com%27) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars</span> |
| NASA LRO Diviner Lunar Data | [https://pds-geosciences.wustl.edu/missions/lro/diviner.htm?utm_source=%27chatgpt.com%27](https://pds-geosciences.wustl.edu/missions/lro/diviner.htm?utm_source=%27chatgpt.com%27) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars</span> |
| Copernicus Data Space Ecosystem | [https://dataspace.copernicus.eu/?utm_source=%27chatgpt.com%27](https://dataspace.copernicus.eu/?utm_source=%27chatgpt.com%27) | شريك: ESA/Copernicus | مساندة: سياق/مرجع أو بيانات مكملة؛ ليست بالضرورة NASA أو API | <span dir="ltr">Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars</span> |
| ESA Open Science Catalog | [https://opensciencedata.esa.int/?utm_source=%27chatgpt.com%27](https://opensciencedata.esa.int/?utm_source=%27chatgpt.com%27) | شريك: ESA | مساندة: سياق/مرجع أو بيانات مكملة؛ ليست بالضرورة NASA أو API | <span dir="ltr">Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars</span> |
| JAXA G-Portal | [https://gportal.jaxa.jp/gpr/index/index?utm_source=%27chatgpt.com%27](https://gportal.jaxa.jp/gpr/index/index?utm_source=%27chatgpt.com%27) | شريك: JAXA | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars</span> |
| USGS-NASA Planetary Geologic Mapping Program | [https://astrogeology-usgs.hub.arcgis.com/pages/interactive-maps-mars](https://astrogeology-usgs.hub.arcgis.com/pages/interactive-maps-mars) | NASA Data & Resources | مساندة: سياق/مرجع أو بيانات مكملة؛ ليست بالضرورة NASA أو API | <span dir="ltr">Interplanetary Survival Guide: Martian Map</span> |
| Example of a route map visual for the Curiosity example mentioned above | [https://science.nasa.gov/resource/curiositys-proposed-path-up-mount-sharp/](https://science.nasa.gov/resource/curiositys-proposed-path-up-mount-sharp/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Interplanetary Survival Guide: Martian Map</span> |
| NASA Worldview | [https://worldview.earthdata.nasa.gov/](https://worldview.earthdata.nasa.gov/) | NASA Data & Resources | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">Interplanetary Survival Guide: Martian Map</span> |
| Mars Perseverance Raw Images Gallery | [https://mars.nasa.gov/mars2020/multimedia/raw-images/](https://mars.nasa.gov/mars2020/multimedia/raw-images/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Interplanetary Survival Guide: Martian Map</span> |
| Quickmap | [https://quickmap.lroc.asu.edu/](https://quickmap.lroc.asu.edu/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Lunar Landing Site Navigator</span> |
| Moon Trek | [https://trek.nasa.gov/moon/](https://trek.nasa.gov/moon/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Lunar Landing Site Navigator</span> |
| Horizons System | [https://ssd.jpl.nasa.gov/horizons/](https://ssd.jpl.nasa.gov/horizons/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Lunar Landing Site Navigator</span> |
| Moon Exploration | [https://www.asc-csa.gc.ca/eng/astronomy/moon-exploration/](https://www.asc-csa.gc.ca/eng/astronomy/moon-exploration/) | شريك: CSA | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Lunar Landing Site Navigator</span> |
| NASA/IPAC Infrared Science Archive | [https://irsa.ipac.caltech.edu/Missions/spherex.html](https://irsa.ipac.caltech.edu/Missions/spherex.html) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Planet X and SPHEREx</span> |
| SPHEREx Tutorial Notebooks | [https://caltech-ipac.github.io/irsa-tutorials/spherex/](https://caltech-ipac.github.io/irsa-tutorials/spherex/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Planet X and SPHEREx</span> |
| WiseView | [http://byw.tools/wiseview](http://byw.tools/wiseview) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Planet X and SPHEREx</span> |
| Gaia Mission Data | [https://archive.stsci.edu/missions-and-data/gaia](https://archive.stsci.edu/missions-and-data/gaia) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Planet X and SPHEREx</span> |
| NEOSSat: Observing Asteroids, Space Debris and Exoplanets | [https://www.asc-csa.gc.ca/eng/satellites/neossat/](https://www.asc-csa.gc.ca/eng/satellites/neossat/) | شريك: CSA | مساندة: سياق/مرجع أو بيانات مكملة؛ ليست بالضرورة NASA أو API | <span dir="ltr">Planet X and SPHEREx</span> |
| Canadian Astronomy Data Centre (CADC) | [https://www.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/en/](https://www.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/en/) | Space Agency Partner Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Planet X and SPHEREx</span> |
| NEOSSat Data Tutorial | [https://github.com/asc-csa/NEOSSAT_Tutorial](https://github.com/asc-csa/NEOSSAT_Tutorial) | Space Agency Partner Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Planet X and SPHEREx</span> |
| NEOSSat Dataset | [https://data.asc-csa.gc.ca/dataset/neossat](https://data.asc-csa.gc.ca/dataset/neossat) | شريك: CSA | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Planet X and SPHEREx</span> |
| Design and Develop Science Missions | [https://www.nasa.gov/wp-content/uploads/2025/04/250323-design-and-develop-science-mission.pdf?emrc=a454cf](https://www.nasa.gov/wp-content/uploads/2025/04/250323-design-and-develop-science-mission.pdf?emrc=a454cf) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Space Mission Design Game</span> |
| General Mission Analysis Tool (GMAT) | [https://software.nasa.gov/software/GSC-19468-1](https://software.nasa.gov/software/GSC-19468-1) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Space Mission Design Game</span> |
| Concept Maturity Levels (CMLs) | [https://dataverse.jpl.nasa.gov/dataset.xhtml?persistentId=hdl:2014/44299](https://dataverse.jpl.nasa.gov/dataset.xhtml?persistentId=hdl:2014/44299) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Space Mission Design Game</span> |
| Mission Design Lab (MDL) | [https://etd.gsfc.nasa.gov/capabilities/integrated-design-center/mission-design-lab/](https://etd.gsfc.nasa.gov/capabilities/integrated-design-center/mission-design-lab/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Space Mission Design Game</span> |
| NASA Mission Viz | [https://nasa.github.io/mission-viz/](https://nasa.github.io/mission-viz/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Space Mission Design Game</span> |
| A Learning Game About Telescopes | [https://science.nasa.gov/mission/webb/game-build-it-yourself/](https://science.nasa.gov/mission/webb/game-build-it-yourself/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Space Mission Design Game</span> |
| Cubesat 101 - Basic Concepts and Processes for First-Time CubeSat Developers | [https://www3.nasa.gov/sites/default/files/atoms/files/nasa_csli_cubesat_101_508.pdf](https://www3.nasa.gov/sites/default/files/atoms/files/nasa_csli_cubesat_101_508.pdf) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Space Mission Design Game</span> |
| Visualize a Space Mission Using Virtual Reality | [https://www.spaceappschallenge.org/2023/challenges/visualize-a-space-mission-using-virtual-reality/](https://www.spaceappschallenge.org/2023/challenges/visualize-a-space-mission-using-virtual-reality/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Space Mission Design Game</span> |
| Digital Games and Activities | [https://www.asc-csa.gc.ca/eng/youth-educators/digital-games-and-activities.asp](https://www.asc-csa.gc.ca/eng/youth-educators/digital-games-and-activities.asp) | شريك: CSA | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">Space Mission Design Game</span> |
| Earth Information Center (EIC) Content Database | [https://svs.gsfc.nasa.gov/gallery/earth-information-center/](https://svs.gsfc.nasa.gov/gallery/earth-information-center/) | NASA Data & Resources | مساندة: سياق/مرجع أو بيانات مكملة؛ ليست بالضرورة NASA أو API | <span dir="ltr">The Earth Information Jukebox</span> |
| Data Sonification: Caldwell 73 | [https://svs.gsfc.nasa.gov/13786/](https://svs.gsfc.nasa.gov/13786/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">The Earth Information Jukebox</span> |
| Change in Night Lights between 2012 and 2023 - EIC Version | [https://svs.gsfc.nasa.gov/5313/](https://svs.gsfc.nasa.gov/5313/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">The Earth Information Jukebox</span> |
| Global Sea Surface Currents and Temperature | [https://svs.gsfc.nasa.gov/3912/#media_group_349716](https://svs.gsfc.nasa.gov/3912/#media_group_349716) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">The Earth Information Jukebox</span> |
| GEOS Aerosols | [https://svs.gsfc.nasa.gov/5669/](https://svs.gsfc.nasa.gov/5669/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">The Earth Information Jukebox</span> |
| Air Quality Model Runs | [https://svs.gsfc.nasa.gov/5533/](https://svs.gsfc.nasa.gov/5533/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">The Earth Information Jukebox</span> |
| Perpetual Ocean 2: Western Boundary Currents | [https://svs.gsfc.nasa.gov/5425/](https://svs.gsfc.nasa.gov/5425/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">The Earth Information Jukebox</span> |
| DYAMOND Global Carbon Dioxide | [https://svs.gsfc.nasa.gov/5196/](https://svs.gsfc.nasa.gov/5196/) | NASA Data & Resources | مساندة: سياق/مرجع أو بيانات مكملة؛ ليست بالضرورة NASA أو API | <span dir="ltr">The Earth Information Jukebox</span> |
| Lightning Events Detected from the ISS 2017-2023 | [https://svs.gsfc.nasa.gov/5011/](https://svs.gsfc.nasa.gov/5011/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">The Earth Information Jukebox</span> |
| A 3D View of an Atmospheric River from an Earth System Model | [https://svs.gsfc.nasa.gov/4960/](https://svs.gsfc.nasa.gov/4960/) | NASA Data & Resources | منخفضة: تعليم/فلك/قمر/مريخ أو موضوع آخر؛ لا تدخل MVP الأرضي | <span dir="ltr">The Earth Information Jukebox</span> |
| GEDI Forest Height | [https://svs.gsfc.nasa.gov/4950/](https://svs.gsfc.nasa.gov/4950/) | NASA Data & Resources | مباشرة: بيانات/أدوات علوم أرض أو تحليلات زمنية؛ افحص API/المنتج قبل التكامل | <span dir="ltr">The Earth Information Jukebox</span> |


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
