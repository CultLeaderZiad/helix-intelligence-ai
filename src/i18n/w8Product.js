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
  // First-run empty states: one sentence on the next action, one primary CTA.
  discoverEmptyStatus: "first search",
  discoverEmptyTitle: "See which competitor ads have run the longest",
  discoverEmptyBody: "Type a brand or domain above and run your first search; results are sorted by how long each Meta ad has been running, because ads that keep running are usually the ones that work.",
  discoverEmptyCta: "Run first search",
  monitorsEmptyStatus: "nothing watched",
  monitorsEmptyTitle: "No monitors yet",
  monitorsEmptyBody: "Run a search in Discover, then watch it here on a schedule to see new, stopped and rewritten ads.",
  monitorsEmptyBodyWithSearch: "Use the form above or watch your last Discover search; each run reports new, stopped and rewritten ads here.",
  monitorsEmptyCta: "Run a search in Discover",
  boardsEmptyTitle: "No saved ads yet",
  boardsEmptyBody: "Open any ad in Discover and press Save to keep it here; a board can then be shared as a read-only link.",
  boardsEmptyCta: "Find ads in Discover",
  boardsLockedTitle: "Boards are not enabled for this workspace",
  boardsLockedBody: "Request access and an admin can turn on Boards for your workspace.",
  requestAccess: "Request access",
  // Access page: what exists, what this workspace has, what happens next.
  accessIntro: "Access is granted by an administrator, not purchased. Helix is invite-only while Discover is being proven; an admin reviews each request and turns features on per workspace.",
  accessFeaturesTitle: "What this workspace can use",
  accessGranted: "on",
  accessNotGranted: "off",
  featureDiscover: "Discover — search the Meta Ad Library for a brand and sort its ads by how long they have run.",
  featureMonitors: "Monitors — re-run a saved search on a schedule and list new, stopped and rewritten ads.",
  featureBoards: "Boards — save ads and share a board as a read-only link.",
  accessNextTitle: "What happens next",
  accessNextBody: "After you send a request, an admin approves or declines it and this page shows the result; nothing is charged either way.",
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
  discoverEmptyStatus: "أول بحث",
  discoverEmptyTitle: "اعرف أي إعلانات المنافسين استمرت أطول مدة",
  discoverEmptyBody: "اكتب اسم علامة تجارية أو نطاقًا في الأعلى وشغّل أول بحث؛ تُرتَّب النتائج حسب مدة تشغيل كل إعلان على Meta، لأن الإعلانات التي تستمر هي غالبًا التي تنجح.",
  discoverEmptyCta: "شغّل أول بحث",
  monitorsEmptyStatus: "لا شيء قيد المراقبة",
  monitorsEmptyTitle: "لا توجد عمليات مراقبة بعد",
  monitorsEmptyBody: "شغّل بحثًا في الاستكشاف، ثم راقبه هنا وفق جدول لترى الإعلانات الجديدة والمتوقفة والمعدّلة.",
  monitorsEmptyBodyWithSearch: "استخدم النموذج في الأعلى أو راقب آخر بحث في الاستكشاف؛ كل تشغيل يعرض هنا الإعلانات الجديدة والمتوقفة والمعدّلة.",
  monitorsEmptyCta: "شغّل بحثًا في الاستكشاف",
  boardsEmptyTitle: "لا توجد إعلانات محفوظة بعد",
  boardsEmptyBody: "افتح أي إعلان في الاستكشاف واضغط حفظ ليظهر هنا؛ يمكن بعدها مشاركة اللوحة كرابط للقراءة فقط.",
  boardsEmptyCta: "ابحث عن إعلانات في الاستكشاف",
  boardsLockedTitle: "اللوحات غير مفعّلة لمساحة العمل هذه",
  boardsLockedBody: "اطلب الوصول ويمكن للمسؤول تفعيل اللوحات لمساحة عملك.",
  requestAccess: "طلب الوصول",
  accessIntro: "يمنح المشرف صلاحية الوصول ولا يتم شراؤها. Helix متاح بالدعوة فقط أثناء التحقق من الاستكشاف؛ يراجع المسؤول كل طلب ويفعّل الميزات لكل مساحة عمل.",
  accessFeaturesTitle: "ما يمكن لمساحة العمل هذه استخدامه",
  accessGranted: "مفعّل",
  accessNotGranted: "غير مفعّل",
  featureDiscover: "الاستكشاف — ابحث في مكتبة إعلانات Meta عن علامة تجارية ورتّب إعلاناتها حسب مدة تشغيلها.",
  featureMonitors: "المراقبة — أعد تشغيل بحث محفوظ وفق جدول واعرض الإعلانات الجديدة والمتوقفة والمعدّلة.",
  featureBoards: "اللوحات — احفظ الإعلانات وشارك لوحة كرابط للقراءة فقط.",
  accessNextTitle: "ماذا يحدث بعد ذلك",
  accessNextBody: "بعد إرسال الطلب، يوافق المسؤول عليه أو يرفضه وتعرض هذه الصفحة النتيجة؛ لا يتم تحصيل أي مبلغ في الحالتين.",
}

const copy = { en, ar }

/** @returns {typeof en} */
export function useW8Copy() {
  const { lang } = useLanguage()
  return copy[lang] ?? en
}

export default copy
