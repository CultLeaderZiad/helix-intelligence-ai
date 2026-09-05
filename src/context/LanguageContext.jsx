import React, { createContext, useContext, useState, useEffect } from "react"

const translations = {
  en: {
    // Nav
    discover: "Discover",
    intelligence: "Intelligence",
    create: "Create",
    performance: "Performance",
    swipeFiles: "Swipe Files",
    billing: "Billing & Meter",
    apiKeys: "API Keys",
    team: "Team Members",
    guide: "Playbook & Guide",
    adminConsole: "Admin Center",
    logout: "Log out",
    
    // Actions & Common
    runDiscovery: "Run Discover Search",
    searching: "Extracting Ad Corpus...",
    refresh: "Refresh",
    cancel: "Cancel",
    save: "Save",
    saving: "Saving...",
    remix: "Remix with Higgsfield",
    generate: "Generate Creative",
    video: "Video",
    image: "Image Still",
    
    // Discover
    searchPlaceholder: "Search competitor brand (e.g. nike.com) or product niche...",
    filters: "Filters",
    compositeScore: "Composite Score",
    daysActive: "Days Active",
    platform: "Platform",
    allPlatforms: "All Platforms",
    
    // Swipe Files
    swipeFilesTitle: "Swipe Files & Saved Creatives",
    swipeFilesSubtitle: "Personal swipe file library. Bookmark winning competitor ads or upload links/images (0 credits used).",
    addReference: "Add Ad Link / Reference",
    addManualRef: "Add Ad Reference or Competitor Link",
    adUrl: "Ad or Landing Page URL",
    headlineAngle: "Headline / Hook / Angle",
    notes: "Notes / Script Details",
    saveReference: "Save to Swipe File",
    discoveredAdsReady: "Discovered Ads Available",
    importPrompt: "Would you like to bookmark all creatives from your latest search into your swipe file?",
    saveAllToSwipe: "Save All to Swipe File",
    swipeEmpty: "Your swipe file is empty",
    swipeEmptyDesc: "Bookmark winning creatives while researching on Discover or click 'Add Ad Link' above to build your collection.",
    loadingSwipe: "Loading saved swipe files...",
    removedFromSwipe: "Creative removed from swipe file",
    refAdded: "Custom reference saved to swipe file",
    
    // Intelligence
    intelligenceTitle: "Intelligence Matrix & Pattern Packs",
    intelligenceSubtitle: "Extract winning hook formulas, emotional triggers, script teardowns, and audience fatigue predictions.",
    synthesizePatterns: "Synthesize Patterns",
    patternPacks: "Synthesized Pattern Packs",
    corpusHeadline: "Active Corpus Discovered",
    teardownHeadline: "Deep Creative Teardown",
    generateTeardown: "Generate Deep Teardown (1.0 cr)",
    
    // Create
    createTitle: "Create Studio",
    creativeMode: "Creative Mode",
    aspectRatio: "Aspect Ratio",
    generationPrompt: "Generation Prompt / Creative Brief",
    liveOutput: "Live Output",
    
    // Performance
    performanceTitle: "Performance & Fatigue Radar",
    durabilityLeaderboard: "Durability & Longevity Leaderboard",
    evergreenSurvivor: "Evergreen Survivor Rate",
    
    // API Keys
    apiKeysTitle: "API Keys & Developer Tokens",
    createApiKey: "Create API Key",

    // Shared stat / honesty labels
    helixSignalNote: "Helix-computed signal — not a metric reported by Meta or the ad platform.",
    performanceScores: "Performance scores",
    notScored: "not scored",
    compositeScoreLabel: "Composite score",
    avgComposite: "Avg Composite Score",
    activeAds: "Active Ads",

    // Discover states
    discoveryResults: "Discovery results",
    noRunYet: "No discovery run yet",
    noRunYetDesc: "Query a competitor ad library to enqueue a scrape. Results are ranked by composite score once the job completes.",
    zeroResultsTitle: "No ads found for this search",
    noMatchesTitle: "No creatives match the current filters",
    noMatchesDesc: "The scrape found creatives, but none fit the filters applied to this search. Clear or widen the filters and re-run.",
    clearFilters: "Clear filters",
    takingLonger: "This is taking longer than expected",
    takingLongerDesc: "The search job has not reported progress for several minutes and may have stalled. No new results will appear on their own. Retry the search, or cancel to stop watching this job.",
    retrySearch: "Retry search",
    stalled: "stalled",
    tryAgain: "Try Again",

    // Intelligence states
    noPatternsYet: "No pattern packs yet",
    noPatternsYetDesc: "Click \"Synthesize Patterns\" to mine recurring hook formulas across this corpus.",
    analysisUnavailable: "Analysis Temporarily Unavailable",
    noCorpusTitle: "No Creative Corpus Available",
    noCorpusDesc: "Run a discovery query in the Discover tab to populate the corpus with competitor ads, or generate a sample analysis.",
    openDiscover: "Open Discover",
    family: "Family",

    // Performance labels
    kpiAvgDuration: "Average Active Duration",
    kpiEvergreen: "Evergreen Survivor Rate",
    kpiComposite: "Average Composite Score",
    kpiFormat: "Format Distribution",
    durabilityHeader: "Durability & Fatigue Leaderboard",
    durabilityIndex: "Durability index",
    noPerformanceTitle: "No Performance Data Available",
    noPerformanceDesc: "Run a search in the Discover tab to gather competitor ad run-times and performance signals.",

    // Dashboard labels
    topPerformers: "Top Performers",
    rankedByComposite: "Ranked by composite score",
    leaderboardPanel: "Reach / Activity Leaderboard",
    timelinePanel: "Timeline",
    crossBrandPanel: "Cross-Brand Comparison",

    // Intelligence extras
    synthesizing: "Synthesizing Patterns...",
    analyzingTeardown: "Analyzing (Pattern Engine)...",
    adsIndexed: "ads indexed",
    noTeardownYet: "No LLM strategic teardown generated for this creative yet.",
    noTeardownYetDesc: "Click \"Generate Deep Teardown\" to run full script analysis, emotional trigger mapping, and audience fatigue prediction.",
    runNewSearch: "Run New Search",
    goToCreate: "Go to Create Studio →"
  },
  ar: {
    // Nav
    discover: "استكشاف الإعلانات",
    intelligence: "الذكاء والأنماط",
    create: "استوديو الإنشاء",
    performance: "تحليل الأداء",
    swipeFiles: "ملفات الإلهام",
    billing: "الفوترة والرصيد",
    apiKeys: "مفاتيح البرمجة API",
    team: "فريق العمل",
    guide: "دليل التشغيل",
    adminConsole: "لوحة الإدارة",
    logout: "تسجيل الخروج",
    
    // Actions & Common
    runDiscovery: "بدء استكشاف الإعلانات",
    searching: "جارٍ استخراج الإعلانات...",
    refresh: "تحديث",
    cancel: "إلغاء",
    save: "حفظ",
    saving: "جارٍ الحفظ...",
    remix: "إعادة صياغة عبر Higgsfield",
    generate: "إنشاء التصميم",
    video: "فيديو",
    image: "صورة ثابتة",
    
    // Discover
    searchPlaceholder: "ابحث عن نطاق المنافس (مثل nike.com) أو مجال المنتج...",
    filters: "تصفية النتائج",
    compositeScore: "التقييم الشامل",
    daysActive: "أيام النشاط",
    platform: "المنصة",
    allPlatforms: "جميع المنصات",
    
    // Swipe Files
    swipeFilesTitle: "ملفات الإلهام والإعلانات المحفوظة",
    swipeFilesSubtitle: "مكتبتك الخاصة لحفظ وتنظيم إعلانات المنافسين الرابحة أو روابط المراجع (0 رصيد مستهلك).",
    addReference: "إضافة رابط أو مرجع إعلاني",
    addManualRef: "إضافة مرجع إعلان أو رابط منافس",
    adUrl: "رابط الإعلان أو صفحة الهبوط",
    headlineAngle: "العنوان الرئيسي / زاوية الإعلان",
    notes: "ملاحظات وتفاصيل السيناريو",
    saveReference: "حفظ في ملفات الإلهام",
    discoveredAdsReady: "إعلانات مستكشفة جاهزة للحفظ",
    importPrompt: "هل ترغب في حفظ جميع إعلانات بحثك الأخير في ملفات الإلهام الخاصة بك؟",
    saveAllToSwipe: "حفظ الكل في ملفات الإلهام",
    swipeEmpty: "ملف الإلهام فارغ حالياً",
    swipeEmptyDesc: "قم بحفظ الإعلانات الرابحة أثناء البحث في صفحة الاستكشاف أو أضف روابط يدوياً لبناء مجموعتك.",
    loadingSwipe: "جارٍ تحميل الإعلانات المحفوظة...",
    removedFromSwipe: "تمت إزالة الإعلان من ملف الإلهام",
    refAdded: "تم حفظ المرجع بنجاح في ملف الإلهام",
    
    // Intelligence
    intelligenceTitle: "مصفوفة الذكاء الاصطناعي وحزم الأنماط",
    intelligenceSubtitle: "استخرج صيغ الخطافات الرابحة والمحفزات النفسية والتحليل السردي وتوقعات إرهاق الإعلان.",
    synthesizePatterns: "استخلاص الأنماط الرابحة",
    patternPacks: "حزم الأنماط المستخلصة",
    corpusHeadline: "بيانات الإعلانات المستكشفة",
    teardownHeadline: "التحليل السردي العميق للإعلان",
    generateTeardown: "إنشاء تحليل تفصيلي (1.0 رصيد)",
    
    // Create
    createTitle: "استوديو الإنشاء والريمكس",
    creativeMode: "نوع الإنشاء",
    aspectRatio: "أبعاد التصميم",
    generationPrompt: "موجز الإنشاء / البرومبت الذكي",
    liveOutput: "النتيجة المباشرة",
    
    // Performance
    performanceTitle: "رادار الأداء وإرهاق الإعلانات",
    durabilityLeaderboard: "قائمة تصدر استدامة وأطول الإعلانات نشاطاً",
    evergreenSurvivor: "نسبة الإعلانات المستمرة (+14 يوماً)",
    
    // API Keys
    apiKeysTitle: "مفاتيح API والتكامل البرمجي",
    createApiKey: "إنشاء مفتاح API جديد",

    // Shared stat / honesty labels
    helixSignalNote: "إشارة محسوبة داخل Helix — ليست مقياساً تعلنه منصة Meta أو منصة الإعلانات نفسها.",
    performanceScores: "درجات الأداء",
    notScored: "غير مقيّم",
    compositeScoreLabel: "التقييم الشامل",
    avgComposite: "متوسط التقييم الشامل",
    activeAds: "الإعلانات النشطة",

    // Discover states
    discoveryResults: "نتائج الاستكشاف",
    noRunYet: "لم يتم أي بحث بعد",
    noRunYetDesc: "ابحث عن إعلانات منافس لتشغيل عملية الاستخراج. تُرتّب النتائج حسب التقييم الشامل عند اكتمال البحث.",
    zeroResultsTitle: "لا توجد إعلانات لهذا البحث",
    noMatchesTitle: "لا توجد إعلانات مطابقة للفلاتر الحالية",
    noMatchesDesc: "وجد البحث إعلانات، لكن لا يطابق أي منها الفلاتر المطبقة. امسح الفلاتر أو وسّعها ثم أعد البحث.",
    clearFilters: "مسح الفلاتر",
    takingLonger: "هذا يستغرق وقتاً أطول من المتوقع",
    takingLongerDesc: "لم يُبلّغ البحث عن أي تقدم لعدة دقائق وقد يكون متوقفاً. لن تظهر نتائج جديدة تلقائياً. أعد البحث أو ألغِ مراقبة هذه المهمة.",
    retrySearch: "إعادة البحث",
    stalled: "متوقف",
    tryAgain: "حاول مجدداً",

    // Intelligence states
    noPatternsYet: "لا توجد حزم أنماط بعد",
    noPatternsYetDesc: "اضغط \"استخلاص الأنماط\" لاستخراج صيغ الخطافات المتكررة من هذه البيانات.",
    analysisUnavailable: "خدمة التحليل غير متاحة مؤقتاً",
    noCorpusTitle: "لا توجد بيانات إعلانات متاحة",
    noCorpusDesc: "قم بتشغيل بحث في صفحة الاستكشاف لتعبئة البيانات بإعلانات المنافسين، أو أنشئ تحليلاً تجريبياً.",
    openDiscover: "اذهب إلى الاستكشاف",
    family: "العائلة",

    // Performance labels
    kpiAvgDuration: "متوسط مدة النشاط",
    kpiEvergreen: "نسبة الإعلانات المستمرة",
    kpiComposite: "متوسط التقييم الشامل",
    kpiFormat: "توزيع الصيغ",
    durabilityHeader: "قائمة الاستدامة وإرهاق الإعلانات",
    durabilityIndex: "مؤشر الاستدامة",
    noPerformanceTitle: "لا توجد بيانات أداء متاحة",
    noPerformanceDesc: "قم بتشغيل بحث في صفحة الاستكشاف لجمع مدد تشغيل إعلانات المنافسين وإشارات الأداء.",

    // Dashboard labels
    topPerformers: "الأعلى أداءً",
    rankedByComposite: "مرتبة حسب التقييم الشامل",
    leaderboardPanel: "قائمة الوصول والنشاط",
    timelinePanel: "الخط الزمني",
    crossBrandPanel: "مقارنة بين العلامات",

    // Intelligence extras
    synthesizing: "جارٍ استخلاص الأنماط...",
    analyzingTeardown: "جارٍ التحليل (محرك الأنماط)...",
    adsIndexed: "إعلان مفهرس",
    noTeardownYet: "لم يتم إنشاء تحليل استراتيجي لهذا الإعلان بعد.",
    noTeardownYetDesc: "اضغط \"إنشاء تحليل تفصيلي\" لتشغيل تحليل السيناريو الكامل ورسم المحفزات العاطفية وتوقعات إرهاق الإعلان.",
    runNewSearch: "بحث جديد",
    goToCreate: "اذهب إلى استوديو الإنشاء →"
  }
}

const LanguageContext = createContext()

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState(() => {
    return localStorage.getItem("helix_lang") || "en"
  })

  useEffect(() => {
    localStorage.setItem("helix_lang", lang)
    document.documentElement.lang = lang
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr"
  }, [lang])

  const t = (key, fallback = "") => {
    return translations[lang]?.[key] || fallback || key
  }

  const toggleLanguage = () => {
    setLang((prev) => (prev === "en" ? "ar" : "en"))
  }

  return (
    <LanguageContext.Provider value={{ lang, setLang, t, toggleLanguage, isRtl: lang === "ar" }}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useLanguage() {
  const context = useContext(LanguageContext)
  if (!context) {
    return {
      lang: "en",
      setLang: () => {},
      t: (k, fallback) => fallback || k,
      toggleLanguage: () => {},
      isRtl: false,
    }
  }
  return context
}

export default LanguageContext
