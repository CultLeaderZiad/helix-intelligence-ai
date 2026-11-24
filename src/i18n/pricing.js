import { useLanguage } from "@/context/LanguageContext"

const FEATURE_LABELS = {
  en: { discover: "Discover: search Meta's Ad Library", swipe_files: "Swipe Files & shareable boards", monitors: "Competitor monitors with digests", team_accounts: "Team accounts and shared boards" },
  ar: { discover: "الاستكشاف: ابحث في مكتبة إعلانات Meta", swipe_files: "ملفات الإلهام ولوحات قابلة للمشاركة", monitors: "مراقبة المنافسين مع ملخصات", team_accounts: "حسابات الفريق ولوحات مشتركة" },
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
  failed: "Plans could not be loaded.",
  bodyNoTrial: "Access is granted by our team after you sign up, with no credit card. There is no checkout on this site yet.",
  noPlans: "More plans are coming. Start with the free trial.",
  footnote: "Prices in USD. Your saved searches, ads and boards are kept if your access ends.",
  features: FEATURE_LABELS.en,
  // Used when at least one plan can be bought online.
  bodyCheckout: "Every new account gets the full product for 7 days with no credit card. Subscribe to a plan any time.",
  bodyCheckoutNoTrial: "Subscribe to a plan to get access.",
  subscribe: "Subscribe",
  openingCheckout: "Opening checkout…",
  checkoutFailed: "Checkout could not open. Try again in a moment.",
  startTrialDays: (n) => `Start your ${n}-day free trial`,
  getStarted: "Get started",
  trialNote: (n) => `${n}-day free trial · no card`,
  limitLabels: {
    searches_per_day: "Searches a day",
    monitors: "Active monitors",
    records_per_month: "Data records a month",
    agent_messages_per_day: "Ask Helix questions a day",
    agent_generations_per_day: "Ad drafts a day",
    teardowns_per_day: "AI ad analyses a day",
    alerts_per_day: "Alerts a day",
    alert_telegram_chats: "Telegram alert chats",
    alert_webhooks: "Alert webhooks",
  },
  plansTitle: "Plans",
  accessUntil: (date) => `Your access runs until ${date}. Subscribe to keep going; your saved searches, ads and boards are kept either way.`,
  trialEnded: "Your free trial has ended. Subscribe to continue. Your saved searches, ads and boards are kept.",
  activating: "Activating your plan…",
  activated: "Your plan is active.",
  activationSlow: "This is taking longer than usual. Your plan will appear here shortly; press Refresh.",
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
  failed: "تعذّر تحميل الخطط.",
  bodyNoTrial: "يمنح فريقنا الوصول بعد التسجيل ودون بطاقة ائتمان. ولا تتوفر عملية دفع على هذا الموقع بعد.",
  noPlans: "خطط أخرى قادمة. ابدأ بالتجربة المجانية.",
  footnote: "الأسعار بالدولار الأمريكي. تبقى عمليات البحث والإعلانات واللوحات المحفوظة إذا انتهى وصولك.",
  features: FEATURE_LABELS.ar,
  bodyCheckout: "يحصل كل حساب جديد على المنتج كاملاً لمدة 7 أيام دون بطاقة ائتمان. اشترك في خطة في أي وقت.",
  bodyCheckoutNoTrial: "اشترك في خطة للحصول على الوصول.",
  subscribe: "اشترك",
  openingCheckout: "جارٍ فتح صفحة الدفع…",
  checkoutFailed: "تعذّر فتح صفحة الدفع. حاول مرة أخرى بعد قليل.",
  startTrialDays: (n) => `ابدأ تجربتك المجانية لمدة ${n} أيام`,
  getStarted: "ابدأ الآن",
  trialNote: (n) => `تجربة مجانية ${n} أيام · دون بطاقة`,
  limitLabels: {
    searches_per_day: "عمليات بحث يومياً",
    monitors: "مراقبات نشطة",
    records_per_month: "سجلات بيانات شهرياً",
    agent_messages_per_day: "أسئلة اسأل Helix يومياً",
    agent_generations_per_day: "مسودات إعلانات يومياً",
    teardowns_per_day: "تحليلات إعلانات بالذكاء الاصطناعي يومياً",
    alerts_per_day: "تنبيهات يومياً",
    alert_telegram_chats: "محادثات تيليجرام للتنبيهات",
    alert_webhooks: "روابط webhook للتنبيهات",
  },
  plansTitle: "الخطط",
  accessUntil: (date) => `وصولك مستمر حتى ${date}. اشترك لتواصل؛ وتبقى عمليات البحث والإعلانات واللوحات المحفوظة في كل الأحوال.`,
  trialEnded: "انتهت تجربتك المجانية. اشترك لتواصل. تبقى عمليات البحث والإعلانات واللوحات المحفوظة.",
  activating: "جارٍ تفعيل خطتك…",
  activated: "خطتك مفعّلة.",
  activationSlow: "يستغرق الأمر وقتاً أطول من المعتاد. ستظهر خطتك هنا قريباً؛ اضغط تحديث.",
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
