"""Built-in glossary of the terms this app uses, explained for a non-expert (Arabic / English). Deterministic, offline, instant; used BEFORE the documentation
index and the web. Definitions are general concepts and how the app uses them: they contain NO measurements for any place or period (those come only from the
app's data tools). Each entry: aliases (regex, lower-case), title, plain explanation, 'in this app' note."""
from __future__ import annotations

import re

G = [
    {"id": "anomaly", "alias": r"anomal|أنوميل|انوميل|أنوميات|انوميات|شذوذ|شاذ|انحراف عن المعتاد|انحراف عن المتوسط",
     "title": {"en": "Anomaly", "ar": "الأنوميلي (الشذوذ / الانحراف عن المعتاد)"},
     "plain": {"en": "An anomaly is how much a value differs from what is normal for that place and time of year. If July is usually 25 °C and one July was 27 °C, the anomaly is +2 °C. It lets us see whether a month was unusually warm or cold, without the big difference between summer and winter hiding it.",
               "ar": "الأنوميلي هو مقدار اختلاف القيمة عمّا هو «معتاد» لذلك المكان وذلك الوقت من السنة. إذا كان شهر يوليو عادةً 25 °م وجاء يوليو معيّن 27 °م فالأنوميلي +2 °م. فائدته أنه يُظهر هل كان الشهر أدفأ أو أبرد من المعتاد دون أن يُخفيه الفرق الكبير بين الصيف والشتاء."},
     "app": {"en": "Where you see 'thermal anomaly' for fires, it means a satellite pixel hotter than its surroundings (a possible fire), not a confirmed fire.", "ar": "عندما ترى «شذوذًا حراريًا» في الحرائق فالمقصود بكسل أسخن من محيطه في صورة القمر (حريق محتمل) وليس حريقًا مؤكدًا."}},
    {"id": "trend", "alias": r"\btrend\b|اتجاه|ترند", "title": {"en": "Trend", "ar": "الاتجاه"},
     "plain": {"en": "A trend is the general direction a value moves over many years (going up, going down, or staying flat), ignoring ordinary ups and downs from year to year.", "ar": "الاتجاه هو الوجهة العامة التي تسير فيها القيمة على مدى سنوات (صعود أو هبوط أو ثبات) بغضّ النظر عن التقلبات العادية من سنة لأخرى."},
     "app": {"en": "The app measures it with the Mann-Kendall test and Sen's slope on NASA POWER data. A trend describes the past; it is not a forecast.", "ar": "يقيسه التطبيق باختبار Mann-Kendall وميل Sen على بيانات NASA POWER. الاتجاه يصف الماضي وليس توقعًا."}},
    {"id": "sen", "alias": r"sen'?s? slope|ميل sen|ميل سين|theil", "title": {"en": "Sen's slope", "ar": "ميل Sen"},
     "plain": {"en": "Sen's slope is the typical yearly change of a value (for example °C per year). It is robust: a few odd years barely move it.", "ar": "ميل Sen هو التغيّر السنوي المعتاد للقيمة (مثلًا °م في السنة). وهو متين: بضع سنوات شاذة بالكاد تؤثر فيه."},
     "app": {"en": "A positive value means increasing, negative means decreasing; read it together with the p-value.", "ar": "القيمة الموجبة تعني ارتفاعًا والسالبة انخفاضًا، وتُقرأ مع قيمة p."}},
    {"id": "pvalue", "alias": r"p[- ]?value|قيمة ?p\b|القيمة الاحتمالية", "title": {"en": "p-value", "ar": "قيمة p"},
     "plain": {"en": "The p-value tells how surprising the result would be if there were really no trend and only chance. A small p (below 0.05) means chance alone is an unlikely explanation. It is NOT the probability that the result is true.", "ar": "قيمة p تقول مدى غرابة النتيجة لو لم يكن هناك اتجاه حقيقي والأمر مجرد صدفة. p صغيرة (أقل من 0.05) تعني أن الصدفة وحدها تفسير غير مرجّح. وهي ليست احتمال أن تكون النتيجة صحيحة."},
     "app": {"en": "The app calls a trend 'significant' when p is below 0.05; otherwise it says the data are not sufficient to confirm a trend (never 'no change').", "ar": "يعدّ التطبيق الاتجاه «دالًّا» عندما تقل p عن 0.05؛ وإلا يقول إن البيانات لا تكفي لتأكيد اتجاه (ولا يقول «لا يوجد تغيّر»)."}},
    {"id": "significance", "alias": r"signific|دلالة|دال إحصائي|ذو دلالة", "title": {"en": "Statistical significance", "ar": "الدلالة الإحصائية"},
     "plain": {"en": "A result is statistically significant when it is unlikely to be explained by chance alone at the chosen level (here 5%). It says the pattern is probably real, not that it is large or important.", "ar": "تكون النتيجة دالّة إحصائيًا عندما يصعب تفسيرها بالصدفة وحدها عند المستوى المختار (هنا 5%). تعني أن النمط حقيقي على الأرجح، وليس أنه كبير أو مهم."},
     "app": {"en": "Significance level α = 0.05.", "ar": "مستوى الدلالة α = 0.05."}},
    {"id": "baseline", "alias": r"baseline|خط الأساس|خط أساس|المعيار المرجعي", "title": {"en": "Baseline", "ar": "خط الأساس"},
     "plain": {"en": "A baseline is a simple, honest method to compare against, such as 'next month will be like the same month last year' or 'the long-term average for that month'. A fancy model is only worth using if it beats the baseline.", "ar": "خط الأساس طريقة بسيطة وأمينة نقارن بها، مثل «الشهر القادم سيشبه الشهر نفسه العام الماضي» أو «المتوسط طويل المدى لذلك الشهر». النموذج المعقّد لا يستحق إلا إذا تفوّق عليه."},
     "app": {"en": "When a model does not beat its baseline in the backtest, the app shows the baseline under its real name.", "ar": "عندما لا يتفوق النموذج على خط الأساس في الاختبار الرجعي يعرض التطبيق خط الأساس باسمه الحقيقي."}},
    {"id": "backtest", "alias": r"backtest|الاختبار الرجعي|اختبار رجعي", "title": {"en": "Backtest", "ar": "الاختبار الرجعي"},
     "plain": {"en": "A backtest hides recent data, asks the model to forecast it, and then compares with what really happened. It shows how wrong the forecasts would have been in the past.", "ar": "الاختبار الرجعي يُخفي بيانات حديثة ويطلب من النموذج توقعها ثم يقارن بما حدث فعلًا. يُظهر مقدار خطأ التوقعات لو استُخدمت في الماضي."},
     "app": {"en": "Used to report forecast errors by months ahead.", "ar": "يُستخدم لعرض أخطاء التوقع بحسب عدد الأشهر المقبلة."}},
    {"id": "interval", "alias": r"interval|prediction interval|مجال|فاصل ثقة|مجال التنبؤ|مجال الثقة", "title": {"en": "Prediction / confidence interval", "ar": "مجال التنبؤ / فاصل الثقة"},
     "plain": {"en": "An interval is a range around a number that is likely to contain the truth. A 95% interval means that, if the method is well calibrated, about 95 of 100 such ranges would contain the real value. A wide range means high uncertainty.", "ar": "المجال نطاق حول الرقم يُرجَّح أن يحوي القيمة الحقيقية. مجال 95% يعني أنه، إذا كانت الطريقة مضبوطة، فإن نحو 95 من كل 100 مجال كهذا يحوي القيمة الفعلية. والمجال الواسع يعني عدم يقين كبيرًا."},
     "app": {"en": "The app also reports how often the intervals really covered the truth in backtests.", "ar": "ويعرض التطبيق أيضًا كم مرة غطّت المجالات الحقيقة فعلًا في الاختبارات الرجعية."}},
    {"id": "mae", "alias": r"\bmae\b|mean absolute error|متوسط الخطأ المطلق|الخطأ المطلق", "title": {"en": "MAE (mean absolute error)", "ar": "متوسط الخطأ المطلق (MAE)"},
     "plain": {"en": "MAE is the average size of the forecast errors, ignoring whether they were too high or too low. An MAE of 1 °C means forecasts were typically off by about one degree.", "ar": "MAE هو متوسط حجم أخطاء التوقع بغضّ النظر عن كونها أعلى أو أقل. MAE يساوي 1 °م يعني أن التوقعات كانت تخطئ عادةً بنحو درجة."},
     "app": {"en": "Reported in the variable's own unit.", "ar": "يُعرض بوحدة الكمية نفسها."}},
    {"id": "rmse", "alias": r"\brmse\b|root mean|الجذر التربيعي", "title": {"en": "RMSE", "ar": "RMSE (جذر متوسط مربع الخطأ)"},
     "plain": {"en": "Like MAE but it punishes big mistakes more, so it is larger when a few forecasts were very wrong.", "ar": "مثل MAE لكنه يعاقب الأخطاء الكبيرة أكثر، فيكون أكبر عندما تخطئ بضعة توقعات كثيرًا."}, "app": {"en": "", "ar": ""}},
    {"id": "bias", "alias": r"\bbias\b|الانحياز", "title": {"en": "Bias", "ar": "الانحياز"},
     "plain": {"en": "Bias is the average signed error: positive means forecasts were usually too high, negative too low.", "ar": "الانحياز هو متوسط الخطأ بإشارته: الموجب يعني أن التوقعات كانت عادةً أعلى من الواقع، والسالب أقل."}, "app": {"en": "", "ar": ""}},
    {"id": "mase", "alias": r"\bmase\b", "title": {"en": "MASE", "ar": "MASE"},
     "plain": {"en": "MASE compares the model's error with the error of simply repeating last year's value. Below 1 is better than that simple rule; above 1 is worse.", "ar": "MASE يقارن خطأ النموذج بخطأ مجرد تكرار قيمة العام الماضي. أقل من 1 أفضل من هذه القاعدة البسيطة وأكثر من 1 أسوأ."}, "app": {"en": "", "ar": ""}},
    {"id": "reanalysis", "alias": r"reanalysis|إعادة التحليل|إعادة تحليل|merra|era5", "title": {"en": "Reanalysis", "ar": "إعادة التحليل (Reanalysis)"},
     "plain": {"en": "A reanalysis blends past observations (stations, satellites) with a weather model to produce a complete, consistent record on a grid for every place and time. It is not a thermometer reading at your street.", "ar": "إعادة التحليل تمزج الرصد السابق (محطات وأقمار) مع نموذج طقس لإنتاج سجل كامل ومتّسق على شبكة لكل مكان وزمان. وهي ليست قراءة مقياس حرارة في شارعك."},
     "app": {"en": "NASA POWER (MERRA-2) values are for a grid cell of about 0.5° × 0.625°, not a single point.", "ar": "قيم NASA POWER (MERRA-2) لخلية شبكية بحجم نحو 0.5° × 0.625° وليست لنقطة واحدة."}},
    {"id": "t2m", "alias": r"\bt2m\b|air temperature|حرارة الهواء", "title": {"en": "Air temperature (T2M)", "ar": "حرارة الهواء (T2M)"},
     "plain": {"en": "The temperature of the air about 2 metres above the ground, like a weather-station thermometer. It is different from land surface temperature (how hot the ground itself is).", "ar": "حرارة الهواء على ارتفاع نحو متريْن فوق الأرض، كمقياس محطة الأرصاد. وهي تختلف عن حرارة سطح الأرض (سخونة الأرض نفسها)."}, "app": {"en": "", "ar": ""}},
    {"id": "lst", "alias": r"\blst\b|land surface temp|حرارة سطح الأرض|حرارة السطح", "title": {"en": "Land surface temperature (LST)", "ar": "حرارة سطح الأرض (LST)"},
     "plain": {"en": "How hot the ground surface looks to a satellite (the 'skin' temperature). On a sunny day it can be much hotter than the air above it.", "ar": "مقدار سخونة سطح الأرض كما يراه القمر الصناعي (حرارة «الجلد»). في يوم مشمس قد تكون أعلى بكثير من حرارة الهواء فوقها."},
     "app": {"en": "Never mixed with air temperature; cloudy composites are removed.", "ar": "لا تُخلط مع حرارة الهواء، وتُزال المركّبات الغائمة."}},
    {"id": "ndvi", "alias": r"\bndvi\b|مؤشر الغطاء النباتي|مؤشر نباتي|اخضرار", "title": {"en": "NDVI (vegetation index)", "ar": "NDVI (مؤشر الغطاء النباتي)"},
     "plain": {"en": "NDVI measures how green and healthy vegetation looks from a satellite, from −1 to +1. Near 0 is bare ground or rock, around 0.2–0.4 is sparse vegetation or shrubs, and 0.6+ is dense, healthy plants. Water is negative.", "ar": "NDVI يقيس مدى اخضرار النبات وصحته من القمر الصناعي، من −1 إلى +1. القرب من 0 أرض جرداء أو صخور، ونحو 0.2–0.4 نبات متفرق أو شجيرات، و0.6 فأكثر نبات كثيف وصحي، والماء سالب."}, "app": {"en": "Computed from Sentinel-2 with clouds and invalid pixels masked.", "ar": "يُحسب من Sentinel-2 مع استبعاد الغيوم والبكسلات غير الصالحة."}},
    {"id": "frp", "alias": r"\bfrp\b|fire radiative|القدرة الإشعاعية", "title": {"en": "FRP (fire radiative power)", "ar": "FRP (القدرة الإشعاعية للحريق)"},
     "plain": {"en": "How much heat energy a fire pixel gives off, in megawatts (MW). Bigger usually means a more intense fire, but it also depends on satellite timing.", "ar": "مقدار الطاقة الحرارية التي يُصدرها بكسل الحريق بالميغاواط (MW). الأكبر يعني عادةً حريقًا أشد، لكنه يتأثر أيضًا بتوقيت مرور القمر."}, "app": {"en": "", "ar": ""}},
    {"id": "firms", "alias": r"hotspot|thermal anomal|كشف حراري|بؤرة حرارية|بؤر", "title": {"en": "Fire detection (hotspot)", "ar": "الكشف الحراري (بؤرة حريق)"},
     "plain": {"en": "A satellite saw a pixel that is much hotter than its surroundings, which often is a fire. It can also be a gas flare or industrial heat, and several detections can belong to one fire.", "ar": "رأى القمر بكسلًا أسخن بكثير من محيطه، وغالبًا هو حريق. وقد يكون شعلة غاز أو حرارة صناعية، وقد تنتمي عدة بؤر إلى حريق واحد."},
     "app": {"en": "Zero detections does not prove there was no fire (clouds, overpass timing).", "ar": "صفر كشوف لا يثبت عدم وجود حريق (الغيوم وتوقيت المرور)."}},
    {"id": "fireindex", "alias": r"fire danger|fwi|danger index|مؤشر خطر|خطر الحرائق", "title": {"en": "Fire danger index", "ar": "مؤشر خطر الحرائق"},
     "plain": {"en": "A score of how favourable the weather is for fire to start and spread (heat, dryness, wind). It is not the probability that a fire will happen.", "ar": "درجة تصف مدى ملاءمة الطقس لاشتعال الحريق وانتشاره (حرارة وجفاف ورياح). وهي ليست احتمال حدوث حريق."}, "app": {"en": "", "ar": ""}},
    {"id": "grid", "alias": r"grid cell|خلية شبكية|الخلية الشبكية|شبكة", "title": {"en": "Grid cell", "ar": "الخلية الشبكية"},
     "plain": {"en": "Model and reanalysis data come as a mesh of boxes. Your place gets the value of the box it falls in, which averages an area of tens of kilometres.", "ar": "بيانات النماذج وإعادة التحليل تأتي كشبكة من المربعات. مكانك يأخذ قيمة المربع الذي يقع فيه، وهي متوسط لمنطقة بعرض عشرات الكيلومترات."}, "app": {"en": "The map shows the real cell as a dashed rectangle.", "ar": "تعرض الخريطة الخلية الفعلية كمستطيل منقّط."}},
    {"id": "climatology", "alias": r"climatolog|المناخ الشهري|المتوسط المناخي|المعتاد", "title": {"en": "Climatology", "ar": "المتوسط المناخي (Climatology)"},
     "plain": {"en": "The usual (average) value for each calendar month over many years, for example 'the typical January'.", "ar": "القيمة المعتادة (المتوسط) لكل شهر من السنة على مدى سنوات طويلة، مثل «يناير المعتاد»."}, "app": {"en": "A baseline for monthly forecasts.", "ar": "خط أساس للتوقعات الشهرية."}},
    {"id": "seasonality", "alias": r"seasonal|موسمي|موسمية|دورة موسمية", "title": {"en": "Seasonality", "ar": "الموسمية"},
     "plain": {"en": "A pattern that repeats every year, like hot summers and cool winters.", "ar": "نمط يتكرر كل عام، مثل الصيف الحار والشتاء البارد."}, "app": {"en": "", "ar": ""}},
    {"id": "forecast_vs", "alias": r"forecast vs|projection|إسقاط|توقع إحصائي|الفرق بين التوقع", "title": {"en": "Forecast vs projection", "ar": "التوقع مقابل الإسقاط"},
     "plain": {"en": "A weather forecast says what the atmosphere will do in the next days. A statistical forecast extends past patterns for coming months. A climate projection explores scenarios decades ahead. They answer different questions.", "ar": "توقع الطقس يقول ماذا سيفعل الجو في الأيام القادمة. التوقع الإحصائي يمدّ أنماط الماضي للأشهر القادمة. والإسقاط المناخي يستكشف سيناريوهات لعقود قادمة. لكلٍّ سؤال مختلف."},
     "app": {"en": "The app does weather forecasts up to 16 days and statistical monthly forecasts up to 24 months; no projections.", "ar": "يقدّم التطبيق توقع طقس حتى 16 يومًا وتوقعًا إحصائيًا شهريًا حتى 24 شهرًا؛ ولا يقدّم إسقاطات."}},
    {"id": "precip_rate", "alias": r"mm/day|معدل الهطول|هطول يومي|mm per day", "title": {"en": "Precipitation rate (mm/day)", "ar": "معدل الهطول (مم/يوم)"},
     "plain": {"en": "The average rainfall per day during a month, in millimetres. To get the monthly total, multiply by the number of days in the month.", "ar": "متوسط الهطول في اليوم خلال الشهر بالمليمتر. لتحصل على إجمالي الشهر اضرب في عدد أيام الشهر."}, "app": {"en": "NASA POWER precipitation is a monthly mean daily rate.", "ar": "هطول NASA POWER هو معدل يومي شهري متوسط."}},
    {"id": "cloud", "alias": r"cloud cover|نسبة الغيوم|الغيوم", "title": {"en": "Cloud cover", "ar": "نسبة الغيوم"},
     "plain": {"en": "The share of an image covered by clouds. Clouds hide the ground, so cloudy pixels are removed before computing vegetation or surface temperature.", "ar": "نسبة ما تغطيه الغيوم من الصورة. الغيوم تخفي الأرض فتُزال البكسلات الغائمة قبل حساب النبات أو حرارة السطح."}, "app": {"en": "", "ar": ""}},
]
_AR_Q = re.compile(r"شو يعني|ماذا يعني|ما معنى|ما هو|ما هي|ما المقصود|اشرح|فسّر|فسر|ايش يعني|إيش يعني|وش يعني|شو هو|شو هي|يعني ايش|يعني إيش", re.I)
_EN_Q = re.compile(r"what (?:is|are|does|do)|\bmeans?\b|meaning|define|definition|explain|what's|whats|difference between", re.I)


def asks_for_meaning(msg: str) -> bool:
    return bool(_AR_Q.search(msg) or _EN_Q.search(msg))


def find_terms(msg: str, limit: int = 2) -> list[dict]:
    t = msg.lower()
    out = []
    for g in G:
        if re.search(g["alias"], t, re.I):
            out.append(g)
    return out[:limit]


def explain(msg: str, lang: str) -> str | None:
    """Markdown explanation from the built-in glossary, or None when no term of the glossary is being asked about."""
    if not asks_for_meaning(msg):
        return None
    terms = find_terms(msg)
    if not terms:
        return None
    blocks = []
    for g in terms:
        head = f"## 📘 {g['title'][lang]}"
        body = f"> [!info] {g['plain'][lang]}"
        app = g["app"][lang]
        blocks += [head, body] + ([f"{'في هذا التطبيق' if lang == 'ar' else 'In this app'}: {app}"] if app else [])
    blocks.append("^ " + ("شرح عام مُدمج في التطبيق (ليس بيانات). لأي رقم أو نتيجة لمكان وفترة محددين تُستخدم أدوات البيانات والمصادر المحددة فقط." if lang == "ar"
                          else "General explanation built into the app (not data). Numbers or results for a place and period always come from the app's data tools and defined sources only."))
    return (chr(10) * 2).join(blocks)
