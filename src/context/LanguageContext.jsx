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
