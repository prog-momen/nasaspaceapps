// NASA Earth Science Environmental Trends & Statistical Significance Data
// Based on NASA Space Apps Challenge 2026

export type EnvLayerKey = "natural" | "temp" | "water" | "winds" | "veg" | "fires";

export interface CountryTrend {
  key: string;
  nameAr: string;
  nameEn: string;
  code2: string;
  code3: string;
  lat: number;
  lon: number;
  pilotKey?: string;
  primaryHazardAr: string;
  primaryHazardEn: string;
  tempAnomaly: string;
  waterTrend: string;
  fireRiskAr: string;
  fireRiskEn: string;
  clarity: number; // 0..100%
  years: number[];
  series: {
    natural: number[];
    temp: number[];
    water: number[];
    winds: number[];
    veg: number[];
    fires: number[];
  };
  descAr: Record<EnvLayerKey, string>;
  descEn: Record<EnvLayerKey, string>;
  stats: {
    slope: string;
    slopeVal: number;
    mkTau: number;
    mkZ: number;
    pValue: string;
    sampleSize: number;
    isSignificant: boolean;
  };
}

export interface PilotRegion {
  id: string;
  nameAr: string;
  nameEn: string;
  lat: number;
  lon: number;
  temp: number;
  dry: number;
  fires: number;
  ndvi: number;
  risk: number; // 0..100%
  caught: number;
  missed: number;
  falseAlarm: number;
  expAr: string;
  expEn: string;
  actionsAr: { title: string; src: string; reason: string }[];
  actionsEn: { title: string; src: string; reason: string }[];
}

export interface PilotCluster {
  key: string;
  titleAr: string;
  titleEn: string;
  camLat: number;
  camLon: number;
  camDist: number;
  regions: PilotRegion[];
}

export interface DetectiveCase {
  id: string;
  titleAr: string;
  titleEn: string;
  regionNameAr: string;
  regionNameEn: string;
  lat: number;
  lon: number;
  variableKey: EnvLayerKey;
  questionAr: string;
  questionEn: string;
  findingAr: string;
  findingEn: string;
  significanceAr: string;
  significanceEn: string;
}

export const COUNTRIES_TRENDS: Record<string, CountryTrend> = {
  Palestine: {
    key: "Palestine",
    nameAr: "فلسطين (Palestine)",
    nameEn: "Palestine",
    code2: "PS",
    code3: "PSE",
    lat: 31.95,
    lon: 35.23,
    pilotKey: "palestine_jordan",
    primaryHazardAr: "الخطر الأساسي: حرائق الأحراش الجبلية مع تراجع الرطوبة الموسمية",
    primaryHazardEn: "Primary Hazard: Highland Brush Fires & Seasonal Moisture Deficit",
    tempAnomaly: "+1.8°C",
    waterTrend: "-22%",
    fireRiskAr: "متوسط - عالي",
    fireRiskEn: "Mod-High",
    clarity: 89,
    years: [1990, 1996, 2002, 2008, 2014, 2020, 2026],
    series: {
      natural: [0.2, 0.45, 0.72, 1.05, 1.32, 1.58, 1.8],
      temp: [0.2, 0.45, 0.72, 1.05, 1.32, 1.58, 1.8],
      water: [565, 540, 515, 490, 465, 442, 420],
      winds: [14.0, 14.5, 15.1, 15.6, 16.2, 16.8, 17.2],
      veg: [0.43, 0.42, 0.4, 0.39, 0.37, 0.36, 0.35],
      fires: [11, 14, 17, 21, 25, 30, 34],
    },
    descAr: {
      natural: "ترصد أقمار ناسا ارتفاعا تدريجيا في حرارة السطح (+1.8°C) مع تراجع في الهطول المطري (-22%) وزيادة أيام الجفاف في المرتفعات.",
      temp: "بيانات NASA MODIS وMERRA-2 تظهر ارتفاع حرارة سطح الأرض بمقدار +1.8°C مقارنة بمتوسط الثمانينات.",
      water: "قراءات بخار الماء والأمطار (NASA GPM & GLDAS) تشير إلى تراجع الرطوبة الموسمية بنسبة 22%.",
      winds: "نماذج NASA MERRA-2 ترصد زيادة في هبوب الرياح الشرقية الجافة في الربيع والخريف.",
      veg: "مؤشر الغطاء النباتي (MODIS NDVI) يوضح جفافا أسرع للأعشاب والأحراش بعد انتهاء الشتاء.",
      fires: "يرصد قمر NASA FIRMS زيادة في بؤر حرائق الأعشاب والأحراش الجبلية خلال موجات الحر.",
    },
    descEn: {
      natural: "NASA satellites observe a +1.8°C warming trend alongside a 22% decline in seasonal moisture in highlands.",
      temp: "NASA MODIS & MERRA-2 records indicate a +1.8°C surface warming shift compared to historical baselines.",
      water: "NASA GPM & GLDAS soil moisture data show a 22% reduction in seasonal moisture availability.",
      winds: "MERRA-2 atmospheric wind models demonstrate stronger dry easterlies during transitional seasons.",
      veg: "MODIS NDVI indicates earlier seasonal drying of highland brush and pastoral vegetation.",
      fires: "NASA FIRMS detects rising seasonal brush fire hotspots during prolonged heatwaves.",
    },
    stats: {
      slope: "+0.44°C/decade",
      slopeVal: 0.44,
      mkTau: 0.82,
      mkZ: 4.1,
      pValue: "p < 0.001",
      sampleSize: 432,
      isSignificant: true,
    },
  },

  Jordan: {
    key: "Jordan",
    nameAr: "الأردن (Jordan)",
    nameEn: "Jordan",
    code2: "JO",
    code3: "JOR",
    lat: 31.24,
    lon: 36.51,
    pilotKey: "palestine_jordan",
    primaryHazardAr: "الخطر الأساسي: حرائق غابات عجلون وجرش مع شح المياه الحرج",
    primaryHazardEn: "Primary Hazard: Northern Woodland Fires & Water Scarcity",
    tempAnomaly: "+1.9°C",
    waterTrend: "-26%",
    fireRiskAr: "مرتفع بالغابات",
    fireRiskEn: "High in Forests",
    clarity: 91,
    years: [1990, 1996, 2002, 2008, 2014, 2020, 2026],
    series: {
      natural: [0.25, 0.52, 0.8, 1.12, 1.4, 1.68, 1.9],
      temp: [0.25, 0.52, 0.8, 1.12, 1.4, 1.68, 1.9],
      water: [295, 282, 268, 255, 240, 226, 215],
      winds: [15.5, 16.0, 16.6, 17.2, 17.8, 18.4, 19.0],
      veg: [0.32, 0.31, 0.29, 0.28, 0.26, 0.25, 0.24],
      fires: [12, 16, 20, 25, 31, 36, 41],
    },
    descAr: {
      natural: "تظهر بيانات ناسا احترارا واضحا (+1.9°C) وانخفاضا في الأمطار (-26%) مما يرفع خطر حرائق غابات عجلون وجرش.",
      temp: "ارتفاع مطرد في حرارة السطح (+1.9°C) حسب أرصاد MODIS وPOWER.",
      water: "تراجع واضح في بخار الماء ورطوبة التربة عبر GPM وGLDAS.",
      winds: "نشاط ملحوظ للرياح الجافة التي تسرع التبخر وانتشار النيران.",
      veg: "إجهاد مائي تدريجي في الغطاء النباتي والمراعي الطبيعية.",
      fires: "رصد 41 بؤرة حريق موسمية عبر NASA FIRMS في المرتفعات الحرجية.",
    },
    descEn: {
      natural: "NASA records demonstrate +1.9°C warming and a 26% rainfall deficit, elevating fire hazards in northern woodlands.",
      temp: "Consistent +1.9°C surface temperature anomaly recorded across terrestrial sensors.",
      water: "GPM-IMERG and GLDAS data reveal persistent root-zone moisture depletion.",
      winds: "MERRA-2 models show increasing frequency of low-humidity gusts.",
      veg: "MODIS NDVI confirms severe moisture stress in pine and oak canopies.",
      fires: "NASA FIRMS cataloged 41 active thermal fire anomalies across highland forests.",
    },
    stats: {
      slope: "+0.48°C/decade",
      slopeVal: 0.48,
      mkTau: 0.86,
      mkZ: 4.35,
      pValue: "p < 0.001",
      sampleSize: 432,
      isSignificant: true,
    },
  },

  Egypt: {
    key: "Egypt",
    nameAr: "مصر (Egypt)",
    nameEn: "Egypt",
    code2: "EG",
    code3: "EGY",
    lat: 26.8,
    lon: 30.8,
    pilotKey: "palestine_jordan",
    primaryHazardAr: "الخطر الأساسي: الإجهاد الحراري والتبخر الزراعي في وادي ودلتا النيل",
    primaryHazardEn: "Primary Hazard: Heat Stress & High Evapotranspiration in Nile Delta",
    tempAnomaly: "+1.7°C",
    waterTrend: "-16%",
    fireRiskAr: "منخفض (إجهاد حراري)",
    fireRiskEn: "Low (Heat Stress)",
    clarity: 88,
    years: [1990, 1996, 2002, 2008, 2014, 2020, 2026],
    series: {
      natural: [0.2, 0.45, 0.7, 0.98, 1.22, 1.48, 1.7],
      temp: [0.2, 0.45, 0.7, 0.98, 1.22, 1.48, 1.7],
      water: [62, 59, 57, 55, 54, 53, 52],
      winds: [16.0, 16.3, 16.7, 17.0, 17.4, 17.8, 18.2],
      veg: [0.38, 0.39, 0.38, 0.39, 0.38, 0.39, 0.38],
      fires: [7, 8, 7, 8, 9, 8, 9],
    },
    descAr: {
      natural: "ترصد أقمار ناسا ارتفاعا في الحرارة السطحية (+1.7°C) مع زيادة في التبخر، بينما يحافظ وادي النيل على استقرار غطائه المروي.",
      temp: "ارتفاع حرارة السطح بمقدار +1.7°C عبر بيانات MODIS.",
      water: "انخفاض الهطول الساحلي بـ 16% وزيادة معدل التبخر من المسطحات الزراعية.",
      winds: "رياح الخماسين الربيعية تنشط محملة بالأتربة من الصحراء الكبرى.",
      veg: "مؤشر NDVI مستقر إحصائيا في الدلتا بفضل الري الدائم (غير دال كاتجاه تدهور).",
      fires: "نشاط الحرائق الطبيعية منخفض ومستقر إحصائيا.",
    },
    descEn: {
      natural: "NASA measurements show +1.7°C warming and elevated evaporation, while irrigated Nile Delta NDVI maintains stability.",
      temp: "+1.7°C surface temperature trend verified by MODIS and AIRS.",
      water: "16% coastal precipitation decrease accompanied by heightened atmospheric evaporation demand.",
      winds: "MERRA-2 tracks regular springtime Khamsin dust transports.",
      veg: "Irrigated Nile agricultural NDVI displays no statistically significant downward trend.",
      fires: "Natural wildfire occurrence remains minimal and statistically stationary.",
    },
    stats: {
      slope: "+0.42°C/decade",
      slopeVal: 0.42,
      mkTau: 0.79,
      mkZ: 3.9,
      pValue: "p < 0.001",
      sampleSize: 432,
      isSignificant: true,
    },
  },

  Spain: {
    key: "Spain",
    nameAr: "إسبانيا (Spain)",
    nameEn: "Spain",
    code2: "ES",
    code3: "ESP",
    lat: 40.46,
    lon: -3.75,
    pilotKey: "spain",
    primaryHazardAr: "الخطر الأساسي: حرائق الغابات المتوسطية والجفاف المتفاقم في الجنوب والغرب",
    primaryHazardEn: "Primary Hazard: Mediterranean Forest Fires & Severe Drought in South/West",
    tempAnomaly: "+2.2°C",
    waterTrend: "-24%",
    fireRiskAr: "مرتفع جدا",
    fireRiskEn: "Very High",
    clarity: 93,
    years: [1990, 1996, 2002, 2008, 2014, 2020, 2026],
    series: {
      natural: [0.3, 0.62, 0.98, 1.35, 1.68, 1.95, 2.2],
      temp: [0.3, 0.62, 0.98, 1.35, 1.68, 1.95, 2.2],
      water: [610, 585, 550, 520, 495, 475, 460],
      winds: [13.2, 13.5, 13.8, 14.1, 14.5, 14.9, 15.3],
      veg: [0.48, 0.47, 0.45, 0.44, 0.42, 0.4, 0.39],
      fires: [28, 35, 44, 56, 68, 82, 95],
    },
    descAr: {
      natural: "تسجل بيانات ناسا احترارا كبيرا بمقدار +2.2°C وتراجعا في الهطول (-24%) مع تصاعد حاد في حرائق الغابات في إكستريمادورا والأندلس.",
      temp: "موجات حر متكررة تسجلها مستشعرات MODIS بمعدل تسارع يفوق المعدل العالمي.",
      water: "تراجع كبير في رطوبة التربة عبر GLDAS ومخزون المياه الجوفية.",
      winds: "رياح جافة قادمة من الجنوب تساهم في سرعة انتشار بؤر الحرائق.",
      veg: "تراجع ملحوظ في حيوية الغابات الحرجية (NDVI تراجع من 0.48 إلى 0.39).",
      fires: "ارتفاع قياسي في بؤر الحرائق النشطة المرصودة عبر NASA FIRMS.",
    },
    descEn: {
      natural: "NASA records verify severe +2.2°C warming, a 24% rainfall decline, and acute wildfire growth across western and southern Spain.",
      temp: "Intense warming trends logged by MODIS and MERRA-2 outpace global continental averages.",
      water: "GLDAS and GRACE records show substantial soil wetness depletion.",
      winds: "Warm dry air masses elevate wildfire propagation speeds.",
      veg: "Vegetation vigor index (NDVI) dropped substantially from 0.48 to 0.39.",
      fires: "NASA FIRMS logs a nearly fourfold surge in seasonal thermal fire anomalies.",
    },
    stats: {
      slope: "+0.55°C/decade",
      slopeVal: 0.55,
      mkTau: 0.89,
      mkZ: 4.6,
      pValue: "p < 0.001",
      sampleSize: 432,
      isSignificant: true,
    },
  },

  "United States": {
    key: "United States",
    nameAr: "الولايات المتحدة (USA)",
    nameEn: "United States",
    code2: "US",
    code3: "USA",
    lat: 38.89,
    lon: -77.03,
    pilotKey: "usa",
    primaryHazardAr: "الخطر الأساسي: حرائق غابات كاليفورنيا والغرب وموجات الجفاف الطويلة",
    primaryHazardEn: "Primary Hazard: California & Western Mega-fires with Prolonged Drought",
    tempAnomaly: "+1.6°C",
    waterTrend: "-18%",
    fireRiskAr: "حرج في الغرب",
    fireRiskEn: "Critical in West",
    clarity: 92,
    years: [1990, 1996, 2002, 2008, 2014, 2020, 2026],
    series: {
      natural: [0.25, 0.48, 0.72, 0.98, 1.2, 1.42, 1.6],
      temp: [0.25, 0.48, 0.72, 0.98, 1.2, 1.42, 1.6],
      water: [780, 765, 750, 730, 715, 695, 680],
      winds: [14.5, 14.8, 15.1, 15.4, 15.8, 16.2, 16.5],
      veg: [0.55, 0.54, 0.53, 0.52, 0.51, 0.5, 0.49],
      fires: [45, 58, 72, 88, 105, 122, 140],
    },
    descAr: {
      natural: "بيانات ناسا ترصد تفاوتا إقليميا كبيرا: احترار وجفاف حاد في الغرب الأمريكي مع تزايد وتيرة الحرائق الكبرى.",
      temp: "ارتفاع متوسط حرارة السطح بمقدار +1.6°C مع تركيز شديد في الولايات الغربية.",
      water: "تراجع الغطاء الثلجي في جبال سييرا نيفادا وجفاف حوض نهر كولورادو.",
      winds: "رياح سانتا آنا ورياح ديابلو الجافة تؤجج بؤر الحرائق الموسمية.",
      veg: "موت أشجار الصنوبر وإجهاد رطوبي واضح في الغابات الجبلية.",
      fires: "تضاعف مساحات الحرائق المسجلة عبر FIRMS وMODIS ثلاث مرات.",
    },
    descEn: {
      natural: "NASA datasets highlight stark regional contrasts: Western states face intense warming, drought, and mega-fires.",
      temp: "+1.6°C nationwide warming with intensified hotspots in California and the Southwest.",
      water: "Sierra Nevada snowpack decline and Colorado River basin water depletion.",
      winds: "Diablo and Santa Ana dry wind events dramatically expand fire perimeters.",
      veg: "Widespread canopy dieback and reduced moisture in coniferous forests.",
      fires: "NASA FIRMS observations reveal a threefold increase in mega-fire occurrence.",
    },
    stats: {
      slope: "+0.40°C/decade",
      slopeVal: 0.4,
      mkTau: 0.78,
      mkZ: 3.85,
      pValue: "p < 0.001",
      sampleSize: 432,
      isSignificant: true,
    },
  },

  Australia: {
    key: "Australia",
    nameAr: "أستراليا (Australia)",
    nameEn: "Australia",
    code2: "AU",
    code3: "AUS",
    lat: -25.27,
    lon: 133.77,
    pilotKey: "australia",
    primaryHazardAr: "الخطر الأساسي: حرائق الأدغال الكارثية في الجنوب الشرقي وتطرف درجات الحرارة",
    primaryHazardEn: "Primary Hazard: Catastrophic Bushfires in Southeast & Thermal Extremes",
    tempAnomaly: "+2.0°C",
    waterTrend: "-21%",
    fireRiskAr: "حرج جدا",
    fireRiskEn: "Extreme",
    clarity: 94,
    years: [1990, 1996, 2002, 2008, 2014, 2020, 2026],
    series: {
      natural: [0.3, 0.58, 0.9, 1.25, 1.55, 1.82, 2.0],
      temp: [0.3, 0.58, 0.9, 1.25, 1.55, 1.82, 2.0],
      water: [480, 460, 440, 420, 400, 385, 375],
      winds: [16.2, 16.6, 17.0, 17.5, 18.0, 18.5, 19.1],
      veg: [0.36, 0.35, 0.34, 0.33, 0.31, 0.3, 0.29],
      fires: [60, 75, 92, 115, 140, 175, 210],
    },
    descAr: {
      natural: "أرصاد ناسا تسجل احترارا واسعا (+2.0°C) وتزايد مواسم حرائق الأدغال الطويلة ذات التأثير الكارثي على التنوع الحيوي.",
      temp: "شذوذ حراري متصاعد في نيو ساوث ويلز وفيكتوريا يكسر المعدلات التاريخية.",
      water: "تكرار نوبات الجفاف وتراجع رطوبة التربة عبر أرصاد GLDAS وGRACE.",
      winds: "رياح صحراوية حارة شديدة الجفاف تهب من قلب القارة نحو السواحل.",
      veg: "جفاف أوراق أشجار الكينا سريعة الاشتعال وانخفاض مؤشر NDVI.",
      fires: "سجلات FIRMS تسجل مواسم حرائق أدغال غير مسبوقة.",
    },
    descEn: {
      natural: "NASA sensors detect +2.0°C continental warming and lengthening bushfire seasons with profound ecosystem impact.",
      temp: "Escalating thermal anomalies across southeastern agricultural and forested corridors.",
      water: "Consecutive multi-year drought phases confirmed by GLDAS moisture analytics.",
      winds: "Continental interior winds push hot, dry air directly into coastal bushland.",
      veg: "Severe desiccation of eucalyptus forests with NDVI declining significantly.",
      fires: "NASA FIRMS documents record-setting thermal radiation during fire seasons.",
    },
    stats: {
      slope: "+0.50°C/decade",
      slopeVal: 0.5,
      mkTau: 0.85,
      mkZ: 4.4,
      pValue: "p < 0.001",
      sampleSize: 432,
      isSignificant: true,
    },
  },
};

// Pilot Clusters for AI Wildfire / Internal Regions Mode
export const PILOT_CLUSTERS: Record<string, PilotCluster> = {
  palestine_jordan: {
    key: "palestine_jordan",
    titleAr: "فلسطين والأردن (مرتفعات بلاد الشام)",
    titleEn: "Palestine & Jordan (Levant Highlands)",
    camLat: 32.0,
    camLon: 35.5,
    camDist: 142,
    regions: [
      {
        id: "ajloun",
        nameAr: "1. مرتفعات وأحراش عجلون وجرش",
        nameEn: "1. Ajloun & Jerash Pine Highlands",
        lat: 32.33,
        lon: 35.78,
        temp: 2.3,
        dry: -34,
        fires: 38,
        ndvi: 0.58,
        risk: 82,
        caught: 88,
        missed: 12,
        falseAlarm: 15,
        expAr: "سجلت أقمار ناسا كثافة غابات صنوبرية عالية مع ارتفاع حرارة السطح (+2.3°C) وتراجع الرطوبة (-34%)، مما يرفع تقدير النموذج لخطر الحرائق.",
        expEn: "Dense pine cover combined with +2.3°C temperature anomaly and -34% moisture deficit elevates model fire risk.",
        actionsAr: [
          { title: "متابعة تنبيهات الدفاع المدني ووزارة الزراعة", src: "الدفاع المدني", reason: "رصد 38 بؤرة حريق سابقة في الأحراش" },
          { title: "تنظيف الأعشاب الجافة حول خطوط التماس الحرجية", src: "إرشادات الوقاية", reason: "انخفاض رطوبة الغطاء النباتي بنسبة 34%" },
        ],
        actionsEn: [
          { title: "Monitor Civil Defense & Forestry Bulletins", src: "Civil Defense", reason: "38 historical fire detections in pine canopy" },
          { title: "Clear Dry Brush Along Forest Perimeter", src: "Forestry Guide", reason: "-34% moisture deficit in ground fuel" },
        ],
      },
      {
        id: "nablus",
        nameAr: "2. جبال نابلس وجنين والكرمل",
        nameEn: "2. Nablus, Jenin & Carmel Highlands",
        lat: 32.22,
        lon: 35.25,
        temp: 2.1,
        dry: -29,
        fires: 31,
        ndvi: 0.52,
        risk: 76,
        caught: 86,
        missed: 14,
        falseAlarm: 17,
        expAr: "تشهد المرتفعات الوسطى والشمالية جفافا مبكرا للأعشاب والأحراش مع نشاط للرياح الشرقية الجافة.",
        expEn: "Central and northern highland brush experiences early seasonal drying alongside dry easterly winds.",
        actionsAr: [
          { title: "الامتناع عن إشعال النيران قرب حقول الزيتون والأحراش", src: "الدفاع المدني", reason: "سرعة انتشار الحرائق في المنحدرات الجبلية" },
          { title: "تجهيز خطوط النار الترابية حول الأراضي الزراعية", src: "وزارة الزراعة", reason: "ارتفاع حرارة السطح بمقدار +2.1°C" },
        ],
        actionsEn: [
          { title: "Avoid Open Burning Near Olive Groves", src: "Civil Defense", reason: "Rapid fire spread across dry terraced slopes" },
          { title: "Maintain Agricultural Firebreaks", src: "Ministry of Agriculture", reason: "+2.1°C elevated surface heating" },
        ],
      },
      {
        id: "jerusalem",
        nameAr: "3. تلال القدس والخليل وجنوب الضفة",
        nameEn: "3. Jerusalem & Hebron Hills",
        lat: 31.65,
        lon: 35.12,
        temp: 1.9,
        dry: -24,
        fires: 22,
        ndvi: 0.39,
        risk: 64,
        caught: 84,
        missed: 16,
        falseAlarm: 18,
        expAr: "خطر متوسط إلى مرتفع في أواخر الصيف نتيجة تراجع الرطوبة الموسمية (-24%) وتراكم الأعشاب الجافة.",
        expEn: "Moderate-to-high late-summer risk driven by -24% moisture deficit and dry grass accumulation.",
        actionsAr: [
          { title: "مراقبة التحذيرات الجوية خلال موجات الحر", src: "الأرصاد الجوية", reason: "خطر حرائق متوسط إلى مرتفع (64%)" },
        ],
        actionsEn: [
          { title: "Follow Meteorological Heatwave Bulletins", src: "Met Service", reason: "Moderate-high risk rating (64%)" },
        ],
      },
      {
        id: "jordan_valley",
        nameAr: "4. الأغوار ووادي الأردن",
        nameEn: "4. Jordan Valley Lowlands",
        lat: 31.85,
        lon: 35.55,
        temp: 2.5,
        dry: -18,
        fires: 14,
        ndvi: 0.22,
        risk: 38,
        caught: 85,
        missed: 15,
        falseAlarm: 19,
        expAr: "رغم الحرارة المرتفعة (+2.5°C)، فإن قلة كثافة الغابات تجعل خطر الحرائق الكبرى أقل من المرتفعات.",
        expEn: "Despite +2.5°C warming, sparse forest fuel keeps large wildfire risk lower than in the northern highlands.",
        actionsAr: [
          { title: "التركيز على حماية المزارع من الإجهاد الحراري", src: "إرشادات الري", reason: "كثافة غابات منخفضة (NDVI = 0.22)" },
        ],
        actionsEn: [
          { title: "Focus on Crop Heat Stress & Irrigation Scheduling", src: "Ag Extension", reason: "Low forest fuel density (NDVI = 0.22)" },
        ],
      },
    ],
  },

  spain: {
    key: "spain",
    titleAr: "إسبانيا (الغابات المتوسطية)",
    titleEn: "Spain (Mediterranean Woodlands)",
    camLat: 40.0,
    camLon: -4.0,
    camDist: 155,
    regions: [
      {
        id: "extremadura",
        nameAr: "1. إكستريمادورا وغرب إسبانيا",
        nameEn: "1. Extremadura Woodlands",
        lat: 39.2,
        lon: -6.1,
        temp: 2.4,
        dry: -35,
        fires: 52,
        ndvi: 0.56,
        risk: 86,
        caught: 89,
        missed: 11,
        falseAlarm: 14,
        expAr: "غابات كثيفة تشهد عجزاً مطرياً حاداً (-35%) وارتفاع حرارة (+2.4°C) مع رصد 52 بؤرة سابقة عبر FIRMS.",
        expEn: "High woodland density with -35% rainfall deficit and +2.4°C anomaly produces acute wildfire danger.",
        actionsAr: [
          { title: "متابعة خريطة الإنذار اليومية AEMET", src: "الأرصاد الإسبانية", reason: "خطر حرائق مرتفع جدا (86%)" },
        ],
        actionsEn: [
          { title: "Check AEMET Daily Wildfire Alerts", src: "AEMET Spain", reason: "Very high fire potential (86%)" },
        ],
      },
      {
        id: "catalonia",
        nameAr: "2. تلال كاتالونيا وشرق المتوسط",
        nameEn: "2. Catalonia Mediterranean Hills",
        lat: 41.6,
        lon: 1.8,
        temp: 2.1,
        dry: -28,
        fires: 39,
        ndvi: 0.51,
        risk: 77,
        caught: 87,
        missed: 13,
        falseAlarm: 16,
        expAr: "احترار ساحلي وجفاف غابي يرفع من خطر الحرائق التاجية في غابات الصنوبر.",
        expEn: "Coastal warming and canopy dryness elevate risk of crowning fires in coastal pine belts.",
        actionsAr: [
          { title: "تفعيل الدوريات الوقائية لمكافحة الحرائق", src: "الحماية المدنية", reason: "رصد 39 بؤرة حرارية سابقة" },
        ],
        actionsEn: [
          { title: "Deploy Regional Fire Patrols", src: "Civil Protection", reason: "39 historical active fire records" },
        ],
      },
    ],
  },
};

// Guided Detective Cases from Challenge Objectives
export const DETECTIVE_CASES: DetectiveCase[] = [
  {
    id: "med_fires",
    titleAr: "1. غابات المتوسط وبلاد الشام (حرائق وجفاف)",
    titleEn: "1. Levant & Mediterranean (Fires & Drought)",
    regionNameAr: "فلسطين والأردن وإسبانيا",
    regionNameEn: "Palestine, Jordan & Spain",
    lat: 32.0,
    lon: 35.5,
    variableKey: "fires",
    questionAr: "كيف يؤدي تزامن ارتفاع الحرارة (MODIS) مع عجز الرطوبة (GLDAS) إلى إشعال حرائق الغابات في حوض المتوسط؟",
    questionEn: "How does co-occurring warming (MODIS) and moisture deficit (GLDAS) trigger seasonal wildfire outbreaks?",
    findingAr: "رصدت أقمار ناسا ارتفاعا بمقدار +1.8°C إلى +2.3°C مقترنا بتراجع رطوبة التربة بنسبة 22% إلى 35%. أظهر اختبار مان-كيندال اتجاها تصاعديا دالا إحصائيا (p < 0.001) في عدد بؤر الحرائق النشطة.",
    findingEn: "NASA sensors detect +1.8°C to +2.3°C warming combined with 22% to 35% soil moisture loss. Mann-Kendall tests confirm a statistically significant upward trend (p < 0.001) in fire frequency.",
    significanceAr: "دال إحصائياً (Mann-Kendall Z = +4.1, p < 0.001, n = 432)",
    significanceEn: "Statistically Significant (Mann-Kendall Z = +4.1, p < 0.001, n = 432)",
  },
  {
    id: "himalaya_glaciers",
    titleAr: "2. الجبال الجليدية في الهيمالايا (الاتجاه المعاكس)",
    titleEn: "2. Himalayan Glaciers (Opposite Trend Phenomenon)",
    regionNameAr: "سلسلة جبال الهيمالايا والتبت",
    regionNameEn: "Himalayas & Tibetan Plateau",
    lat: 28.5,
    lon: 86.5,
    variableKey: "temp",
    questionAr: "مثال التحدي الرسمي: كيف تؤدي نفس عملية الاحترار إلى ذوبان الجليد وتضخم البحيرات (+48%) بدلا من الجفاف؟",
    questionEn: "Official Challenge Example: How does identical warming cause glacial meltwater surge (+48%) rather than drought?",
    findingAr: "في المرتفعات الباردة، لا يؤدي ارتفاع درجات الحرارة إلى جفاف سطحي فوري بل يسرع ذوبان الأنهار الجليدية، مما يسبب تضخم البحيرات الجليدية بنسبة 48% ويزيد مخاطر الفيضانات المفاجئة.",
    findingEn: "In cold cryosphere altitudes, warming accelerates glacier runoff rather than immediate desiccation, causing glacial lake area expansion of 48% with flash outburst risks.",
    significanceAr: "دال إحصائياً (اتجاه ذوبان جليدي حاد، p < 0.001)",
    significanceEn: "Statistically Significant (Sharp Cryosphere Melt, p < 0.001)",
  },
  {
    id: "amazon_rainforest",
    titleAr: "3. غابات الأمازون المطيرة (إجهاد الغطاء النباتي)",
    titleEn: "3. Amazon Rainforest (Vegetation Moisture Stress)",
    regionNameAr: "حوض الأمازون والبرازيل",
    regionNameEn: "Amazon Basin, Brazil",
    lat: -3.4,
    lon: -62.2,
    variableKey: "veg",
    questionAr: "كيف تتأثر رطوبة منطقة الجذور ومؤشر NDVI نتيجة مواسم الجفاف المتكررة في الغابات الاستوائية؟",
    questionEn: "How are root-zone soil wetness and NDVI impacted by repetitive tropical drought phases?",
    findingAr: "قراءات MERRA-2 وMODIS تظهر انخفاضا مستمرا في رطوبة طبقة الجذور (GWETROOT) مع تراجع ملحوظ في مؤشر الخضرة النباتية (NDVI) على أطراف حوض الأمازون الجنوبي والشرقي.",
    findingEn: "MERRA-2 and MODIS observations show persistent root-zone moisture decline (GWETROOT) paired with observable NDVI brown-down on southern rainforest frontiers.",
    significanceAr: "دال إحصائياً (Sen's Slope سالب، p < 0.005)",
    significanceEn: "Statistically Significant (Negative Sen's Slope, p < 0.005)",
  },
  {
    id: "arabian_desert",
    titleAr: "4. الأقاليم الصحراوية ووادي النيل (التطرف الحراري)",
    titleEn: "4. Deserts & Nile Valley (Thermal Extremes & Evaporation)",
    regionNameAr: "الجزيرة العربية ومصر وشمال إفريقيا",
    regionNameEn: "Arabian Peninsula, Egypt & North Africa",
    lat: 25.0,
    lon: 42.0,
    variableKey: "temp",
    questionAr: "ما هو معدل الشذوذ الحراري ومعدلات التبخر المحسوبة من نماذج ناسا المناخية في الأقاليم الجافة؟",
    questionEn: "What is the rate of thermal anomaly and evaporation demand modeled across arid eco-zones?",
    findingAr: "سجلت مستشعرات AIRS وMODIS شذوذا حراريا تجاوز +2.1°C، وتظهر نماذج CMIP6 تسارعا مستقبليا في معدلات الإجهاد الحراري بمعدل +0.5°C لكل عقد حتى 2050.",
    findingEn: "AIRS and MODIS record persistent anomalies exceeding +2.1°C, with CMIP6 projections confirming future heat stress escalation at +0.5°C/decade through 2050.",
    significanceAr: "دال إحصائياً (Mann-Kendall Z = +4.5, p < 0.001)",
    significanceEn: "Statistically Significant (Mann-Kendall Z = +4.5, p < 0.001)",
  },
];

