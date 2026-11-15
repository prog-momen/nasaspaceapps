# تقرير Debug فعلي — EarthTrend Explorer

التاريخ: 14 نوفمبر 2026، توقيت Asia/Jerusalem. جميع أوامر Python نُفذت من `earthtrend_rag/.venv/Scripts/python.exe`، وهي بيئة تشغيل التطبيق نفسها. لم تُعرض قيمة أي مفتاح، ولم تُفعّل فوترة أو تُشترَ خدمة أو يُضَف مزود بيانات جديد.

## الحكم الحالي

POWER، قراءة بياناته، حساب الاتجاه، RAG retrieval، ومسار الإجابة البديلة تعمل. **التوليد على `gemini-3.8-flash` فشل حياً بـ429 يومية مثبتة**. تنفيذ Function Calling والعودة بنتيجة الأداة إلى هذا النموذج **BLOCKED**؛ لا تثبته الاختبارات المحلية ولا الإجابة البديلة. طلب Function Calling التجريبي نفسه وصل للخدمة ورُفض بـ429 قبل تنفيذ أي وظيفة.

أثناء هذه الجلسة وصلت تعديلات أخرى للملفات: تغيّر الافتراضي من `gemini-3.8-flash` دون بدائل إلى `gemini-3.5-flash-lite` مع `gemini-3.1-flash-lite,gemini-3.8-flash`، وأضيف `reconcile_years` واختبارات ووثائق ثم تقوية للعدادات وفحوص السنوات المفقودة. حُفظت هذه التعديلات ولم ألغها. نجحت إجابة RAG وثائقية حية واحدة على `3.5-flash-lite` خلال هذه الحالة، ثم أظهر العداد المحلي الوصول إلى الحد 18 عليه وعلى `3.1-flash-lite`؛ لاحقاً سجل الملف 20 للأول بسبب العمل المتزامن. هذه نتيجة مختلفة عن اختبار النموذج الأصلي؛ ليست إثباتاً أن `3.8-flash` عاد للعمل.

الخطوة المتبقية المحددة: مراجعة [استهلاك Gemini للمشروع](https://ai.dev/rate-limit)، ثم إعادة تشخيص النص والأداة الثابتة بعد عودة الحصة. لا تمسح `usage.json` أو ترفع الحد المحلي لتجاوز التشخيص. `RetryInfo` أشار إلى 45381 ثانية وقت القياس؛ لا أعدّه موعد ضمان لإتاحة الخدمة. لم أعد تجربة 503 أو أُثبت سببها التاريخي.

## حالة الملفات وبيئة التنفيذ

- `C:\nasa challenge API` ليس مستودع Git، وكذلك مجلد التطبيق: `git status` يعيد `not a git repository`. لم يوجد AGENTS.md على القرص ضمن مساحة العمل أو جذرها الأعلى؛ اتُبعت التعليمات التي أرسلها المستخدم.
- قبل التعديل نُسخت `app/`, `tests/`, `docs/`, README والمتطلبات وpytest.ini إلى `data/debug_before_20261114/` مع SHA256. لا تتضمن النسخة ملفات البيئة أو المفاتيح. ليست هذه نسخة Git ولا تشمل قاعدة المتجهات كاملة.
- الملف الحالي الذي ينجح منه تحميل المفتاح هو `البروتوتايب/.env`. المفتاح موجود بواسطة `load_gemini_key()`، مع عدم وجوده كمتغير عملية عند القياس الأول. لم توجد EARTHDATA_USERNAME / EARTHDATA_PASSWORD / EARTHDATA_TOKEN / FIRMS_MAP_KEY / MAP_KEY / NASA_API_KEY في العملية أو ملفات البيئة المفحوصة.
- لا proxy أو SSL_CERT_FILE في بيئة العملية عند القياس. لا يوجد خادم سابق على localhost:8000 عند الفحص. شُغّل خادم اختبار مستقل على 8765، ثم أُوقف بعد الاختبار.
- `get_settings()` يحمّل فقط أسماء إعدادات Settings من ملفات البيئة، ومفتاح Gemini يُقرأ بصورة منفصلة. وجود متغير Earthdata في ملف مستقبلي لا ينشئ عميل تنزيل غير موجود.

| المكوّن | النسخة المستخدمة فعلياً |
|---|---|
| Python | 3.14.7 |
| google-genai | 3.3.0 |
| httpx | 0.28.1 |
| numpy / scipy | 2.5.4 / 1.18.1 |
| pymannkendall | 1.4.3 |
| FastAPI / Pydantic | 0.163.0 / 2.14.3 |
| Qdrant client / sentence-transformers | 1.20.0 / 6.3.0 |
| portalocker / tzdata، أضيفا في العمل المتزامن | 4.4.2 / 2026.6 |
| Embedding | intfloat/multilingual-e5-small، بُعد 384، من cache محلي حقيقي |
| Gemini endpoint الفعلي | `https://generativelanguage.googleapis.com/v1/models/{model}:generateContent` |

المتطلبات تستخدم حدوداً دنيا غير مقفلة؛ هذه النسخ وصف للتشغيل الذي اختُبر، لا ضمان أن تثبيتاً جديداً سيختار النسخ نفسها. الـSDK الحالي اختار `v1` فعلياً؛ لم أستبدله بافتراض قديم عن `v1beta`.

## مسار التنفيذ الفعلي

```text
سؤال المستخدم → /api/rag/query → classify → embedding + hybrid retrieval من Qdrant
  ├─ سؤال وثائق → passages → Gemini → فحص citations → document_answer
  ├─ سؤال اتجاه → TrendAgent → Gemini function declaration: analyze_trend
  │    → TrendRequest → catalog (المتغير/النقطة) → POWER monthly point
  │    → parse JSON → screen/QC → annual/seasonal diagnostics → MK + Sen
  │    → function response إلى النموذج نفسه → فحص النص → gemini أو template
  └─ قيمة/تنبؤ → requires_data_tool؛ ليست كل أسماء TOOL_MAP دوال منفذة

/api/analysis/trend → TrendRequest → POWER → QC → الإحصاء مباشرة بلا Gemini
/api/analysis/trend/ask → TrendAgent مباشرة
```

في فرع الاتجاه، المقاطع المسترجعة تُرفق كمصادر مرتبطة في استجابة RAG؛ لا تُحقن حالياً في prompt وكيل الاتجاه. النموذج لا يتصل بـNASA مباشرة. الدالة الفعلية المكشوفة له هي `analyze_trend` فقط؛ لا يوجد تنفيذ فعلي حالي لـ`search_datasets`, `fetch_timeseries`, `forecast_timeseries` مستقل بالمعنى الذي توحي به أسماء التوجيه.

## الأعطال المؤكدة حسب التأثير

| الأولوية والمرحلة | الدليل والطلب الأدنى | التصنيف والإصلاح |
|---|---|---|
| 1 — Gemini generation | نص `Reply OK`، دون RAG أو أدوات: HTTP 429 خلال 0.797 ثانية؛ محاولة واحدة | حصة خدمة، لا DNS/TLS ولا خطأ parsing. لا يمكن إصلاح الحصة بالكود. احتُفظ بالتوقف المحدود دون إعادة يومية |
| 1 — الأداة التجريبية الحية | طلب دالة محلية ثابتة، HTTP 429 خلال 0.390 ثانية. `QuotaFailure`: `GenerateRequestsPerDayPerProjectPerModel-FreeTier`، model=`gemini-3.8-flash`، quotaValue=`20`، RetryInfo=`45381s` | دليل يومية من الخدمة نفسها، وليس استنتاجاً من 503. لم يتوفر request ID في الرؤوس المفحوصة |
| 2 — fallback قبل استدعاء الأداة | قبل الإصلاح، فشل Gemini الأول يُرمى قبل الحصول على analysis؛ RAG يرجع requires_data_tool فقط | أُضيف استخراج محافظ لمتغير صريح، مكان واحد معروف وسنتين. لا يستبدل LST ولا يخمن فترات. الحالات الغامضة تبقى محجوبة |
| 2 — POWER retries/validation | الكود السابق: حتى 3 طلبات متتالية، timeout=60 لكل طلب، بلا backoff أو حد إجمالي؛ يخزّن payload قبل التحقق منه | اختبار HTTP 200 HTML/login أو JSON خطأ يكشف المسار. الآن تحقق نوع المحتوى والبنية والوحدة والفترة والقيم قبل cache؛ محاولتان مع jitter وRetry-After وحد إجمالي |
| 2 — تواريخ مكررة | `MonthlySeries([2024,2024],[1,1],[1,9],...)`: screen كان يُبقي 9 بصمت | الآن invalid_data / INVALID_TIMESERIES دون حكم. الإدخال غير المرتب يُرتب بالتقويم؛ NaN مفقود وInfinity غير صالح |
| 2 — فحص نص الإجابة | `unsupported_numbers('slope=-0.0491', {'slope':0.0491})` كان يقبل قلب الإشارة؛ tolerance يقبل قيماً صغيرة غير صحيحة | أُزيل قبول القيمة المطلقة وضُيّق tolerance. رفض حكم اتجاه بلا أداة حتى لو بلا أرقام. الفحص العددي ليس برهاناً على صحة معنى كل جملة |
| 2 — health والحد المحلي | خادم حقيقي أعاد health=ok مع وصول النماذج المتاحة إلى حد محلي أو quota مخزنة | الآن health يبيّن blocked / configured_unprobed وسبب كل نموذج، دون طلب Gemini. الحد المحلي يُتجاوز إلى البديل المهيأ فقط إذا كان متاحاً؛ لا يتوقف الاختيار عند reserve الأول |
| 3 — بروتوكول الأدوات | الكود `fcs[:1]` كان يتجاهل بقية الاستدعاءات بصمت | طلب متعدد التحليلات مرفوض صراحة قبل التنفيذ؛ دعم المقارنة متعددة النتائج غير منفذ. حفظ call ID وthought signature، ورفض arguments غير object والأسماء غير المعروفة. حد دورتين نموذجيّتين؛ استدعاء جديد في طور الشرح يوقف الحلقة |
| 3 — تصنيف الاستثناءات | except Exception كان يصنف TypeError محلياً كخطأ network ويعيده | الآن فقط أخطاء النقل/timeout قابلة للمحاولة؛ أخطاء config/SDK المحلية client_error بلا تكرار. 5xx يصنف service_error، لا إثبات overload أو free-tier |
| 3 — اختبار حي مضلل | integration fixture كان skip عند تعطل الخدمة؛ اختبار FC يسمح template؛ اختبار تنزيل قد يستخدم cache | أُزيل probe المكرر وتجاهل أخطاء الخدمة، وأُلزم اختبار Gemini بمصدر gemini، واختبار POWER بتنزيل غير مخبأ. الاختبار الحي المحدد الآن يفشل صراحة عند quota، كما ينبغي |

الأدلة المنقحة موجودة في `data/debug_initial_evidence.json`، نتائج POWER في `data/debug_20261114.json`، وإعادة فحص المنع المخزن في `data/debug_gemini_recheck.json`. صُحّح تصنيف السطر المخزن في التقرير الأول من FAIL إلى BLOCKED مع إبقاء `raw_recorded_status` وسبب التصحيح؛ لم يُرسل ذلك السطر طلباً حياً جديداً.

## نتائج الطبقات قبل وبعد

| الطبقة | قبل الإصلاح / القياس الأول | بعد الإصلاح والتحقق | النتيجة |
|---|---|---|---|
| سلسلة متزايدة/متناقصة/ثابتة | الاختبارات الأساسية ناجحة | slopes=+1/−1/0 لكل سنة؛ p≈9.709e−15 / نفس القيمة / 1؛ مقارنة pymannkendall | PASS محلي |
| قيم ناقصة، قصيرة، مكررة أو غير مرتبة | gaps/short مغطاة جزئياً؛ duplicate صامت؛ raw NaN ينتج NaN | فحوص صارمة، QC واضح، رفض التكرار، منع NaN من دخول دوال الإحصاء الخام | PASS محلي |
| seasonal / autocorrelation | تنفيذ موجود | اختبارات seasonal وHamed–Rao ضد pymannkendall؛ slope مقابل SciPy؛ حدود التطبيق أدناه | PASS ضمن الحدود |
| POWER مباشر صغير | 200 JSON، 13 سجلاً منها annual summary | 12 شهراً في 2024، T2M بوحدة C، صفر missing، وليست صفحة تسجيل دخول | PASS حي |
| POWER عبر عميل المشروع ثم الأداة بنفس الطلب الصغير | 12 شهراً؛ الأداة TOO_FEW_YEARS | لا نقطة اختلاف خاطئة؛ الرفض الإحصائي لسنة واحدة متوقع | PASS حي |
| POWER أداة حقيقية كاملة | capture/cache ليسا دليلاً حياً | تنزيل دون cache: نابلس 2005–2025، 252/252 شهراً، MERRA2، ثم تحليل | PASS حي |
| PRECTOTCORR | وحدة موثقة بالكود | تنزيل حي 12 شهراً، mm/day، ليس مجموعاً شهرياً | PASS حي |
| Gemini metadata | models.get ناجح 0.271 ثانية | اسم .3.8-flash متاح وgenerateContent مسجل؛ لا يثبت السماح بالتوليد | PASS metadata |
| Gemini نص فقط (.3.8) | HTTP 429 | إعادة الفحص توقفت من quota cache دون شبكة؛ الفشل الحي الأول ما زال قائماً | FAIL حي / BLOCKED إعادة |
| Function Calling محلي ثابت | طلب الخدمة رُفض 429 | schema/arguments/call ID/response/الحدود مختبرة محلياً؛ roundtrip حي غير مكتمل | PASS محلي / BLOCKED حي |
| Gemini → NASA tool → شرح model | لا دليل حالي ناجح على .3.8 | اختبار integration مستهدف: FAIL صريح لأن answer_source=template، دون نجاح زائف | BLOCKED حي |
| RAG الحقيقي retrieval | فهرس موجود | earth_knowledge=878، gemini_platform=241؛ FIRMS score≈0.8155 أكبر من 0.79 | PASS حقيقي |
| RAG وثائق + توليد | تغير إعداد النموذج أثناء العمل | إجابة حية بخمسة مصادر على .3.5-flash-lite خلال 1.709 ثانية | PASS لذلك النموذج فقط |
| HTTP endpoints + fallback | لا خادم على 8000 عند البداية | خادم اختبار 8765: direct/ask/RAG تعيد 200 ونتيجة صحيحة المصدر؛ LST غير مدعوم. استُخدم cache في هذا الاختبار تحديداً | PASS HTTP/fallback |
| HLS/MODIS/FIRMS تنزيل وقراءة ملفات | لا عميل مدمج | لم يُضف تكامل جديد ولم يُدّع نجاح تحميل ملف | NOT TESTED / غير منفذ |

اختبارات الوحدة عند البداية: **147 passed، 40 integration deselected**. بعد إصلاحات هذه الجلسة والاختبارات الجديدة بلغ العدد 186، ثم وصلت 31 حالة أخرى من العمل المتزامن. آخر تشغيل للمجموعة كاملة: **217 passed، 40 deselected**، وتحذير واحد عن عدم تأثير payload indexes في Qdrant المحلي. هذه الـ40 لم تُعدّ ناجحة. اختبار Gemini الحي المستهدف أُجري منفصلاً وأعطى **1 failed**، متوقعاً بسبب quota؛ سجله `data/debug_live_gemini_test.xml`. نتيجة الوحدة محفوظة في `data/debug_unit_tests.xml`.

تأكيد HTTP نهائي بعد إصلاح health: `data/debug_http_final_results.json` يسجل health=degraded، generation=blocked، وموانع النماذج الثلاثة. `/trend/ask` و`/rag/query` أعادا template بسبب quota، مع نتيجة analysis=ok من cache و252 شهراً. لم تُرسل هذه الطلبات أي طلب Gemini جديد لأن النماذج كلها حُجبت قبل الشبكة. أُوقف خادم الاختبار بعدها.

التحليل الحي لنابلس يقدّر T2M عند نقطة تمثيلية: 21 متوسطاً سنوياً، MK original، p=0.006، tau=0.4381، Sen=0.04910 °C/year، مجال 95% بالتنفيذ الحالي [0.01120, 0.06803]. هذه نتيجة الأداة والبيانات، وليست نتيجة مولدة من Gemini أو متوسط مساحة المدينة، ولا إثبات سببية أو تنبؤاً.

## الحسابات والمصادر والصلاحيات

| المصدر / الوظيفة الفعلية | endpoint | المصادقة والمتغير | الإعداد والاختبار |
|---|---|---|---|
| Gemini، توليد النص واختيار الأداة | generativelanguage.googleapis.com/v1/models/{model}:generateContent | API key عبر SDK، GEMINI_API_KEY | موجود؛ .3.8 generation=429؛ metadata=200؛ .3.5 وثائق نجحت ثم حد محلي |
| POWER، T2M وPRECTOTCORR | power.larc.nasa.gov/api/temporal/monthly/point | لا مفتاح لهذا الطلب؛ لا NASA_API_KEY ولا Earthdata | PASS حي JSON صالح، تنزيل فعلي وقراءة وحساب؛ لا pagination لهذا الطلب النقطي |
| analyze_trend / MK / Sen | وظيفة Python محلية /api/analysis/trend | لا اعتماد مستقل؛ جلب البيانات يستخدم POWER | PASS محلي + بيانات POWER حية |
| RAG ingestion/retrieval | ملفات allow-list محلية + Qdrant محلي؛ نموذج E5 مخبأ | لا مفتاح Gemini للاسترجاع | PASS؛ لم يُعد بناء الفهرس ولم يُنزَّل embedding جديد |
| MODIS LST / HLS / Earthdata | لا استدعاء فعلي في app حالياً؛ AppEEARS عند إضافة تكامل متعلق | Earthdata Login مستقل؛ USERNAME/PASSWORD أو token حسب العميل | متغيرات مفحوصة غير موجودة، وعميل تنزيل/QC غير منفذ. ليس نقص المفتاح وحده العائق |
| FIRMS | لا استدعاء data فعلي؛ موثق api/area/csv/{MAP_KEY}/... | MAP_KEY مستقل عن مفاتيح Gemini وapi.nasa.gov | غير موجود، والعميل وتجميع الأحداث غير منفذين؛ NOT TESTED |
| api.nasa.gov | لا endpoint مستخدم في التنفيذ الحالي | NASA_API_KEY لخدماته فقط | غير موجود لكنه ليس متطلباً لتشغيل POWER؛ NOT TESTED وغير مطلوب للإصلاح |

لا يوجد نجاح metadata لـCMR/HLS في هذه الجلسة، ولا تنزيل أو فتح GeoTIFF/HDF/NetCDF لتلك المنتجات. لذلك لم أفحص pagination أو cloud masks/QA bits لعملاء غير موجودين. في POWER فُحصت الفترة والإحداثيات والوحدات وfill=-999 والسجلات، وتُحذف YYYY13 لأنها خلاصة سنوية. POWER يعيد native grid حول النقطة، وليس تغطية مضلع أو pixels منتقاة بعلامات سحب. لا تُختلق أعلام جودة غير موجودة.

T2M = حرارة الهواء على ارتفاع مترين، وليست LST. كما أن `header.time_standard='LST'` في POWER يعني **Local Solar Time**؛ لا يغيّر نوع المتغير إلى حرارة سطح الأرض. طلب LST يعيد data_source_unavailable ولا يستبدل المتغير.

روابط التسجيل والتوثيق الرسمية:

- [Gemini API key](https://aistudio.google.com/apikeys)، [الحصة والاستهلاك](https://ai.dev/rate-limit)، [دليل الأعطال](https://aistudio.google.com/docs/troubleshooting). المفتاح موجود؛ لا حاجة لإنشاء واحد آخر لمجرد quota.
- [النموذج .3.8 ودعم Function Calling](https://aistudio.google.com/docs/models/gemini-3.8-flash)، [SDK الرسمي](https://googleapis.github.io/python-genai/). النموذج والـSDK صالحان؛ metadata لا تثبت صلاحية inference للمشروع.
- [POWER monthly API](https://power.larc.nasa.gov/docs/services/api/temporal/monthly/): الطلب المختبَر نفسه لا يستخدم مفتاحاً.
- [Earthdata Login والتسجيل](https://urs.earthdata.nasa.gov/)، [AppEEARS](https://appeears.earthdatacloud.nasa.gov/). يلزم أيضاً عميل استخراج/تنزيل/QC إذا أُريد LST مستقبلاً.
- [FIRMS MAP_KEY مجاني](https://firms.modaps.eosdis.nasa.gov/api/map_key/)، [شرح API الرسمي](https://firms.modaps.eosdis.nasa.gov/content/academy/data_api/firms_api_use.html).
- [تسجيل api.nasa.gov](https://api.nasa.gov/): ليس مفتاح POWER أو Earthdata أو FIRMS.

## حدود الإحصاء والفرضيات غير المحسومة

- الميل محسوب باستخدام السنوات العشرية الفعلية؛ °C/year أو (mm/day)/year. الفجوات لا تتحول إلى خطوة سنة زائفة في Sen.
- الموسمية تُفحص بـKruskal–Wallis مع effect size، ثم ارتباط بواقي منزوعة الموسمية والاتجاه بـLjung–Box. الاختيار الافتراضي Seasonal MK عندما تكون الموسمية واضحة ولا يوجد ارتباط مكتشف؛ وإلا متوسطات سنوية ثم تصحيح Hamed–Rao حسب lags المؤثرة. المتوسط السنوي لا يُفترض أنه يزيل الارتباط تلقائياً.
- فجوات البواقي الشهرية تُضغط في Ljung–Box الحالي؛ معايرة p عند فقد كبير أو غير منتظم ليست مثبتة. التعديل المتزامن جعل annual Ljung–Box وHamed–Rao يُتجاوزان صراحة عند وجود سنوات محذوفة، مع lag1 بمحاذاة التقويم. هذا يمنع تجاوراً زمنياً كاذباً لكنه لا يثبت استقلال السلسلة السنوية المتبقية؛ MK الأصلي حينها غير مصحح لهذا الارتباط المحتمل. المتوسط السنوي متوسط غير موزون للأشهر الصالحة، ومن ≥9 أشهر قد ينحاز إن اختلفت الأشهر المفقودة موسمياً. أُضيف تنبيه صريح في النتيجة، دون الادعاء بإصلاح بحثي كامل.
- إجبار monthly_seasonal رغم ارتباط البواقي لا يطبق correlated-seasonal MK؛ أُضيف تحذير إلى notes. الموسمية عبر السنوات ليست بالضرورة ثابتة، وعدم رفض اختبار الارتباط ليس إثبات الاستقلال.
- الإحصاء الخام يستخدم تقريباً طبيعياً وليس exact MK للسلاسل الصغيرة؛ الأداة تشترط 10 سنوات صالحة وتغطية ≥0.6 افتراضياً. الحد المختار سياسة تطبيق لا ضمان قوة إحصائية.
- مقارنة scipy.stats.theilslopes أعطت slope مطابقاً. CI الحالي يستخدم interpolation لرتب slopes، بينما SciPy يقرّب الرتب: مثلاً synthetic seed=1 يعطي [0.4467017,0.5123139] مقابل [0.4478736,0.5117743]. هذا اختلاف مُعلن، لا تطابق CI حرفي. اختبار المقارنة يقيد الاختلاف بالرتب المجاورة. [مرجع SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.theilslopes.html)، [تنفيذ pyMannKendall المرجعي](https://github.com/mmhs013/pyMannKendall).
- سبب 503/504 التاريخية وعدد محاولات الـ17 دقيقة ليسا مثبتين بسجلات خام حاضرة هنا. `docs/GEMINI_RELIABILITY.md` يحتوي ملاحظات من عمل متزامن؛ ادعاء overload فيه لا يصبح دليلاً من هذه الجلسة. نحتاج body/status/headers/timestamps للطلب التاريخي لتعيين سببه. لم يحدث 503 حي في اختبارات هذه الجلسة.
- لا دليل على خطأ DNS/TLS/proxy في الاتصال المختبَر: POWER عمل، Gemini metadata عمل وgeneration أعاد رد quota منظماً. هذا لا ينفي أعطال شبكة في وقت سابق.
- عدادات usage محلية وليست كشف استهلاك Google؛ يوجد أيضاً تنسيق قديم في الملف. لا أستنتج منها وحدها عدد طلبات المشروع الخارجي أو وقت إعادة الحصة. العمل المتزامن أضاف قفل ملف بين العمليات وكتابة atomic، واختبارات ذلك نجحت ضمن التشغيل النهائي. العداد صار يستخدم يوم Pacific متوافقاً مع [التوثيق الرسمي للحصص](https://aistudio.google.com/docs/rate-limits)؛ مشاركة ملف العداد لا تشمل طلبات أجهزة أو تطبيقات أخرى لا تكتبه.
- deadline يحد انتظار الشبكة عبر worker محدود، مع timeouts للنقل. قد تكمل الخدمة طلباً أُغلق انتظاره وتحتسبه؛ لا يُستخدم نجاحه المتأخر ولا تُطلق محاولة متداخلة بعد hard timeout. حسابات CPU المحلية ليست قابلة للإلغاء القسري بهذه الآلية.

## الملفات المعدّلة وسببها

| الملفات | التغيير في هذا العمل |
|---|---|
| app/reliability.py، app/config.py | سياق deadline مشترك، انتظار شبكة محدود، Retry-After رقمي أو HTTP-date، إعدادات POWER |
| app/data_sources/power.py | validation قبل cache، retries محدودة، backoff/jitter، deadlines، cache_hit، سجل attempts، معنى time_standard |
| app/analysis/timeseries.py، stats.py، trend.py | رفض duplicate/nonfinite/raw short، ترتيب التقويم، حماية variance factor، تنبيهات الافتراضات |
| app/analysis/catalog.py، app/tools/trend_tool.py | توضيح عدم تنفيذ بعض مصادر البيانات؛ إرجاع invalid_data وerror_kind/attempts بدل حكم أو استثناء غير واضح |
| app/llm/gemini_client.py | عزل transport errors، عدم استنتاج يومية من delay فقط، service_error، request IDs إن توفرت، deadline وحدود محلية واختيار البديل المهيأ |
| app/agent/deterministic.py، trend_agent.py | fallback محافظ قبل الاتصال بالأداة، سبب صريح، call ID، رفض multi-call والأسماء/args غير الصحيحة، guard للإشارات والأرقام والحكم بلا أداة |
| app/rag/service.py، pipeline.py، app/api/main.py، schemas.py | source/reason في الاستجابات، health يبين المنع المعروف ولا يدّعي live probe، تمرير deadline |
| app/diagnose.py | أداة إعادة تشخيص offline افتراضياً، opt-in للشبكة، ميزانية صريحة، JSON منزوع الأسرار، PASS/FAIL/BLOCKED/NOT TESTED |
| tests/test_debug_regressions.py | اختبارات إعادة إنتاج العيوب وفصل مصدر الإجابة وحماية البروتوكول والمهلة |
| tests/integration/conftest.py، test_real_trend.py | عدم تحويل تعطل الخدمة إلى skip، وعدم اعتبار template أو cache نجاحاً حياً |
| requirements.txt، tests/test_followup_hardening.py وتعديلات تقوية أخرى | عمل متزامن محفوظ: portalocker/tzdata، Pacific day، atomic file lock، فترات غير ملتبسة، وفحوص سنوات مفقودة؛ شُملت في الاختبار النهائي |
| README.md، هذا التقرير | أوامر إعادة الفحص وتصحيح الملاحظات القديمة عن المفتاح والاختبارات |

الملفات الأخرى الظاهرة في `data/debug_change_manifest.json` تشمل تعديلات متزامنة حُفظت؛ لا أنسب جميعها لهذا العمل. لم أعدل `.env` أو أصفّر العدادات أو أعِد بناء الفهرس. مقارنة SHA256 بالنسخة الأولى متاحة في manifest.

## إعادة الفحص بميزانية صغيرة

من PowerShell:

```powershell
Set-Location 'C:\nasa challenge API\earthtrend_rag'
./.venv/Scripts/python.exe -m pytest -q
./.venv/Scripts/python.exe -m app.diagnose --out data/debug_offline.json
./.venv/Scripts/python.exe -m app.diagnose --live-power --out data/debug_power.json
./.venv/Scripts/python.exe -m app.diagnose --live-gemini --model gemini-3.8-flash --max-gemini-requests 3 --out data/debug_gemini.json
# بعد نجاح النص والأداة الثابتة وعودة الحصة:
./.venv/Scripts/python.exe -m app.diagnose --live-gemini --real-rag --model gemini-3.8-flash --max-gemini-requests 8 --out data/debug_full.json
```

الافتراضي لا يرسل شبكة. `--live-power` يستخدم أربع طلبات HTTP غير مخبأة، دون إعادة تشخيصية. Gemini diagnostics لا يستخدم نماذج بديلة، ولا retries، وكل نداء ≤15 ثانية، ويحترم المنع المحلي/المخزن. `--model` يخصص التشخيص فقط ولا يعدّل إعدادات التطبيق. 0=نجاح المحدد، 1=فشل، 2=محجوب. عدم تشغيل طبقة يُكتب NOT TESTED. لا تشغّل مجموعة integration كاملة باعتبارها probe رخيصاً.

السياسة الإنتاجية: حد الطلب المشترك 90 ثانية، Gemini ≤75 ثانية للنداء و≤30 للمحاولة و3 محاولات لكل نموذج، POWER ≤30 إجمالاً وconnect≤5/read≤15 ومحاولتان. كل طبقة مقيدة بالوقت المتبقي من الطلب؛ retries الـSDK معطلة. لا retry لـ400/401/403/404 أو quota يومية مثبتة؛ Retry-After الطويل لا يسبب انتظاراً يتجاوز الميزانية. سبب template متاح صراحة في `fallback_reason`، وغياب البيانات لا ينتج رقماً إحصائياً.

الخلاصة التشغيلية: NASA POWER والتحليل ومسار fallback قابلة للاستخدام الآن. المسار الذي ينتهي بتوليد Gemini الأصلي لم يُثبت نجاحه؛ عائقه المحدد حصة .3.8، ثم يلزم تشغيل اختبار roundtrip الحي بعد عودتها. إضافة مفاتيح Earthdata أو NASA العامة لن تحل هذا العائق.
