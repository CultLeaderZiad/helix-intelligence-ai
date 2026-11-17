import { useLanguage } from "@/context/LanguageContext"

/**
 * W9-1 copy (EN + AR): archive search, the Metapi record meter, the record
 * estimate before a search or monitor, and "use stored results first".
 * Every number shown comes from the API; nothing here is a placeholder.
 */
export const en = {
  archiveSearchLabel: "Search your archive",
  archiveSearchPlaceholder: "Brand, headline or ad text",
  archiveSearchHint: "Searches ads already saved in this workspace. Uses 0 records.",
  archiveSearchButton: "Search archive",
  archiveSearchEmpty: (q) => `No archived ads match "${q}".`,
  archiveSearchCount: (n) => `${n} archived ${n === 1 ? "ad" : "ads"}`,
  savedSearchCount: (n) => `${n} saved ${n === 1 ? "ad" : "ads"}`,
  archiveSearchFailed: "Search failed. Try again.",
  archivedOn: (d) => `Archived ${d}`,
  openAd: "Open in Ad Library",
  close: "Close",
  swipeSearchLabel: "Search saved ads",
  swipeSearchPlaceholder: "Brand, headline or ad text",
  swipeSearchButton: "Search",
  swipeSearchClear: "Clear search",
  swipeSearchEmpty: (q) => `No saved ads match "${q}".`,
  recordsTitle: "Metapi records this month",
  recordsUsed: (used, cap) => `${used} of ${cap} records used`,
  recordsRemaining: (n) => `${n} left this month`,
  recordsResets: (d) => `Counted since ${d} (UTC). Resets on the 1st.`,
  recordsWarning: "This workspace has used 80% or more of its monthly records. Use stored results and archive search where you can.",
  recordsReached: "This workspace has used all of its monthly records. New searches and monitor runs are paused until the 1st. Stored results and archive search still work.",
  recordsExplain: (search) => `Metapi bills each ad it returns as one record. A Discover search or monitor run uses up to ${search}.`,
  recordsUnavailable: "Record usage is unavailable right now.",
  searchEstimate: (n, left) => `A new search uses up to ${n} records (${left} left this month).`,
  storedTitle: "You already have results for this search",
  storedBody: (n, d) => `${n} ads from a search on ${d}.`,
  storedView: "View stored results (0 records)",
  storedFresh: (n) => `Run fresh search (up to ${n} records)`,
  storedCancel: "Cancel",
  recordCapError: "This workspace has used its monthly Metapi records. Stored results and archive search still work. Open Access & Usage to see the meter.",
  monitorEstimate: (cadence, n) => `About ${n} records a month at ${cadence === "weekly" ? "weekly" : "daily"} runs (up to the cap).`,
}

export const ar = {
  archiveSearchLabel: "ابحث في أرشيفك",
  archiveSearchPlaceholder: "العلامة التجارية أو العنوان أو نص الإعلان",
  archiveSearchHint: "يبحث في الإعلانات المحفوظة بالفعل في مساحة العمل هذه. يستهلك 0 سجلات.",
  archiveSearchButton: "ابحث في الأرشيف",
  archiveSearchEmpty: (q) => `لا توجد إعلانات مؤرشفة تطابق "${q}".`,
  archiveSearchCount: (n) => `${n} إعلان مؤرشف`,
  savedSearchCount: (n) => `${n} إعلان محفوظ`,
  archiveSearchFailed: "تعذّر البحث. حاول مرة أخرى.",
  archivedOn: (d) => `أُرشف في ${d}`,
  openAd: "افتح في مكتبة الإعلانات",
  close: "إغلاق",
  swipeSearchLabel: "ابحث في الإعلانات المحفوظة",
  swipeSearchPlaceholder: "العلامة التجارية أو العنوان أو نص الإعلان",
  swipeSearchButton: "بحث",
  swipeSearchClear: "مسح البحث",
  swipeSearchEmpty: (q) => `لا توجد إعلانات محفوظة تطابق "${q}".`,
  recordsTitle: "سجلات Metapi هذا الشهر",
  recordsUsed: (used, cap) => `تم استخدام ${used} من ${cap} سجل`,
  recordsRemaining: (n) => `متبقٍ ${n} هذا الشهر`,
  recordsResets: (d) => `محسوبة منذ ${d} (UTC). تُعاد في اليوم الأول من الشهر.`,
  recordsWarning: "استخدمت مساحة العمل 80% أو أكثر من سجلاتها الشهرية. استخدم النتائج المحفوظة والبحث في الأرشيف قدر الإمكان.",
  recordsReached: "استخدمت مساحة العمل كل سجلاتها الشهرية. تتوقف عمليات البحث الجديدة وتشغيل المراقبات حتى اليوم الأول من الشهر. تظل النتائج المحفوظة والبحث في الأرشيف متاحة.",
  recordsExplain: (search) => `تحتسب Metapi كل إعلان تعيده سجلًا واحدًا. يستخدم بحث Discover أو تشغيل المراقبة ما يصل إلى ${search} سجل.`,
  recordsUnavailable: "استخدام السجلات غير متاح الآن.",
  searchEstimate: (n, left) => `يستخدم البحث الجديد ما يصل إلى ${n} سجل (متبقٍ ${left} هذا الشهر).`,
  storedTitle: "لديك نتائج لهذا البحث بالفعل",
  storedBody: (n, d) => `${n} إعلان من بحث بتاريخ ${d}.`,
  storedView: "اعرض النتائج المحفوظة (0 سجلات)",
  storedFresh: (n) => `شغّل بحثًا جديدًا (حتى ${n} سجل)`,
  storedCancel: "إلغاء",
  recordCapError: "استخدمت مساحة العمل سجلات Metapi الشهرية. تظل النتائج المحفوظة والبحث في الأرشيف متاحة. افتح الوصول والاستخدام لرؤية العدّاد.",
  monitorEstimate: (cadence, n) => `حوالي ${n} سجل شهريًا عند التشغيل ${cadence === "weekly" ? "الأسبوعي" : "اليومي"} (حتى الحد).`,
}

const copy = { en, ar }

/** @returns {typeof en} */
export function useW9Copy() {
  const { lang } = useLanguage()
  return copy[lang] ?? en
}

export default copy
