import { useLanguage } from "@/context/LanguageContext"

/**
 * W8 product copy (EN + AR). Labels describe only what the data supports:
 * run length comes from the ad library's start date, and the score is a
 * text rubric, not a performance prediction.
 */
export const en = {
  filters: "Filters",
  clear: "clear",
  country: "Country",
  countryHint: "Country is sent with the search. Change it, then run the search again.",
  longevity: "Running for",
  longevityAny: "Any run length",
  longevity30: "30+ days",
  longevity60: "60+ days",
  longevity90: "90+ days",
  longevityHint: "Ads that have run longer are usually the ones still working. Applies to these results instantly.",
  rubric: "Text rubric score",
  rubricAny: "Any score",
  rubricMin: (n) => `${n}.0 and above`,
  rubricHint: "A score of the ad text only, not a performance prediction.",
  notApplied: "not applied",
  notAppliedBody: "Country changed since the last search. Run the search again to apply it.",
  runLengthUnknown: "unknown",
  hiddenUnknown: (n) => `${n} ${n === 1 ? "ad" : "ads"} with unknown run length hidden`,
}

export const ar = {
  filters: "عوامل التصفية",
  clear: "مسح",
  country: "الدولة",
  countryHint: "تُرسل الدولة مع البحث. غيّرها ثم أعد تشغيل البحث.",
  longevity: "مدة التشغيل",
  longevityAny: "أي مدة",
  longevity30: "30 يومًا أو أكثر",
  longevity60: "60 يومًا أو أكثر",
  longevity90: "90 يومًا أو أكثر",
  longevityHint: "الإعلانات التي تعمل لفترة أطول هي غالبًا التي لا تزال تحقق نتائج. تُطبَّق على هذه النتائج فورًا.",
  rubric: "تقييم نص الإعلان",
  rubricAny: "أي تقييم",
  rubricMin: (n) => `${n}.0 فأعلى`,
  rubricHint: "تقييم لنص الإعلان فقط، وليس توقعًا للأداء.",
  notApplied: "لم يُطبَّق",
  notAppliedBody: "تغيّرت الدولة منذ آخر بحث. أعد تشغيل البحث لتطبيقها.",
  runLengthUnknown: "غير معروفة",
  hiddenUnknown: (n) => `تم إخفاء ${n} إعلان بمدة تشغيل غير معروفة`,
}

const copy = { en, ar }

/** @returns {typeof en} */
export function useW8Copy() {
  const { lang } = useLanguage()
  return copy[lang] ?? en
}

export default copy
