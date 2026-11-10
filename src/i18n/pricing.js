import { useLanguage } from "@/context/LanguageContext"

const FEATURE_LABELS = {
  en: { discover: "Discover: search Meta's Ad Library", swipe_files: "Swipe Files & shareable boards", monitors: "Competitor monitors with digests" },
  ar: { discover: "الاستكشاف: ابحث في مكتبة إعلانات Meta", swipe_files: "ملفات الإلهام ولوحات قابلة للمشاركة", monitors: "مراقبة المنافسين مع ملخصات" },
}

export const en = {
  nav: "Pricing",
  label: "PRICING",
  title: "Start free. Stay when it's useful.",
  body: "Every new account gets the full product for 7 days with no credit card. Paid plans are set up by our team after your trial; there is no checkout on this site yet.",
  trialBadge: "Free trial",
  trialStatus: "No card",
  trialName: (days) => `${days} days free`,
  trialTagline: "Everything below, from the moment you sign up.",
  startTrial: "Start free trial",
  contact: "Contact us",
  perMonth: "/ month",
  custom: "Custom",
  popular: "Popular",
  plan: "Plan",
  loading: "Loading plans…",
  failed: "Plans could not be loaded. The free trial is still available.",
  noPlans: "More plans are coming. Start with the free trial.",
  footnote: "Prices in USD. Your saved searches, ads and boards are kept if your access ends.",
  features: FEATURE_LABELS.en,
}

export const ar = {
  nav: "الأسعار",
  label: "الأسعار",
  title: "ابدأ مجاناً، واستمر حين يفيدك.",
  body: "يحصل كل حساب جديد على المنتج كاملاً لمدة 7 أيام دون بطاقة ائتمان. يُعِد فريقنا الخطط المدفوعة بعد التجربة؛ ولا تتوفر عملية دفع على هذا الموقع بعد.",
  trialBadge: "تجربة مجانية",
  trialStatus: "دون بطاقة",
  trialName: (days) => `${days} أيام مجاناً`,
  trialTagline: "كل ما يلي، من لحظة التسجيل.",
  startTrial: "ابدأ التجربة المجانية",
  contact: "تواصل معنا",
  perMonth: "/ شهرياً",
  custom: "مخصص",
  popular: "الأكثر طلباً",
  plan: "خطة",
  loading: "جارٍ تحميل الخطط…",
  failed: "تعذّر تحميل الخطط. التجربة المجانية متاحة رغم ذلك.",
  noPlans: "خطط أخرى قادمة. ابدأ بالتجربة المجانية.",
  footnote: "الأسعار بالدولار الأمريكي. تبقى عمليات البحث والإعلانات واللوحات المحفوظة إذا انتهى وصولك.",
  features: FEATURE_LABELS.ar,
}

export function usePricingCopy() {
  const { lang } = useLanguage()
  return lang === "ar" ? ar : en
}

/** Pick the visitor's language from an admin-edited {en, ar} value, falling back to the other. */
export function localized(value, lang) {
  if (!value) return ""
  const primary = lang === "ar" ? value.ar : value.en
  return (primary || (lang === "ar" ? value.en : value.ar) || "").trim()
}

/** Same for {en: [], ar: []} lists. */
export function localizedList(value, lang) {
  if (!value) return []
  const primary = lang === "ar" ? value.ar : value.en
  const fallback = lang === "ar" ? value.en : value.ar
  return (primary && primary.length ? primary : fallback || []).filter(Boolean)
}
