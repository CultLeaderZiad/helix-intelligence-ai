import { useLanguage } from "@/context/LanguageContext"

/**
 * W9-2 copy (EN + AR): tags and notes on saved ads, "Monitor this brand",
 * filters on loaded results, infinite scroll and keyboard shortcuts.
 * Every number shown comes from the API or from the loaded results.
 */
export const en = {
  tagsLabel: "Tags",
  addTagPlaceholder: "Add a tag",
  addTag: "Add tag",
  removeTag: (tag) => `Remove tag ${tag}`,
  tagsSaveFailed: "Could not save tags. Try again.",
  notesLabel: "Notes",
  addNotePlaceholder: "Why did you save this ad?",
  addNote: "Add note",
  editNote: "Edit",
  saveNote: "Save",
  cancel: "Cancel",
  deleteNote: "Delete",
  noteFailed: "Could not save the note. Try again.",
  edited: "edited",
  filterByTag: "Filter by tag",
  allTags: "All",
  tagCount: (tag, n) => `${tag} (${n})`,

  monitorBrand: "Monitor this brand",
  monitorBrandTitle: (name) => `Monitor ${name}`,
  monitorWatchPage: (id) => `Watches the advertiser's page (page id ${id}).`,
  monitorWatchName: (name) => `Watches ads found for the name "${name}".`,
  monitorCadence: "How often",
  cadenceDaily: "Daily",
  cadenceWeekly: "Weekly",
  monitorCost: (run, month) => `Each run reserves up to ${run} Metapi records, about ${month} a month.`,
  monitorRemaining: (left, cap) => `${left} of ${cap} records left this month.`,
  monitorNoRoom: "Not enough records left this month for the first run. It resets on the 1st (UTC).",
  monitorExists: "An active monitor already watches this brand.",
  monitorOpen: "Open monitors",
  monitorCreate: "Create monitor",
  monitorCreated: "Monitor created. The first run starts shortly.",
  monitorFailed: "Could not create the monitor.",
  monitorLoading: "Checking cost…",
  monitorNeedsPlan: "Monitors are not on this workspace's plan.",

  loadedFiltersLabel: "Filter loaded results",
  loadedFiltersHint: "Filters only the ads already loaded. Uses 0 records.",
  mediaType: "Media",
  anyOption: "Any",
  status: "Status",
  statusActive: "Running",
  statusStopped: "Has a stop date",
  cta: "CTA",
  landingDomain: "Landing domain",
  minRunLength: (d) => `Ran at least ${d} ${d === 1 ? "day" : "days"}`,
  showingLoaded: (shown, loaded) => `Showing ${shown} of ${loaded} loaded`,
  clearLoadedFilters: "Clear",
  noLoadedMatches: "No loaded ads match these filters. Load more or clear them.",

  loadMore: "Load more",
  loadingMore: "Loading more…",
  loadedOf: (loaded, total) => `${loaded} of ${total} loaded`,
  allLoaded: "All results loaded",
  loadMoreFailed: "Could not load more results.",

  shortcutsButton: "Keyboard shortcuts",
  shortcutsTitle: "Keyboard shortcuts",
  shortcutNext: "Next result",
  shortcutPrev: "Previous result",
  shortcutSave: "Save the selected ad",
  shortcutOpen: "Open the selected ad in the Ad Library",
  shortcutHelp: "Show or hide this list",
  savedToast: "Saved to your board",
  saveFailed: "Could not save this ad.",
}

/** @type {typeof en} */
export const ar = {
  tagsLabel: "الوسوم",
  addTagPlaceholder: "أضف وسمًا",
  addTag: "إضافة وسم",
  removeTag: (tag) => `إزالة الوسم ${tag}`,
  tagsSaveFailed: "تعذّر حفظ الوسوم. حاول مرة أخرى.",
  notesLabel: "الملاحظات",
  addNotePlaceholder: "لماذا حفظت هذا الإعلان؟",
  addNote: "إضافة ملاحظة",
  editNote: "تعديل",
  saveNote: "حفظ",
  cancel: "إلغاء",
  deleteNote: "حذف",
  noteFailed: "تعذّر حفظ الملاحظة. حاول مرة أخرى.",
  edited: "معدّلة",
  filterByTag: "التصفية حسب الوسم",
  allTags: "الكل",
  tagCount: (tag, n) => `${tag} (${n})`,

  monitorBrand: "راقب هذه العلامة التجارية",
  monitorBrandTitle: (name) => `مراقبة ${name}`,
  monitorWatchPage: (id) => `يراقب صفحة المعلن (معرّف الصفحة ${id}).`,
  monitorWatchName: (name) => `يراقب الإعلانات التي يُعثر عليها للاسم "${name}".`,
  monitorCadence: "معدل التكرار",
  cadenceDaily: "يوميًا",
  cadenceWeekly: "أسبوعيًا",
  monitorCost: (run, month) => `كل تشغيل يحجز حتى ${run} سجل من Metapi، أي حوالي ${month} شهريًا.`,
  monitorRemaining: (left, cap) => `يتبقى ${left} من ${cap} سجل هذا الشهر.`,
  monitorNoRoom: "لا تكفي السجلات المتبقية هذا الشهر للتشغيل الأول. تتجدد في اليوم الأول من الشهر (UTC).",
  monitorExists: "توجد مراقبة نشطة لهذه العلامة التجارية بالفعل.",
  monitorOpen: "فتح المراقبات",
  monitorCreate: "إنشاء المراقبة",
  monitorCreated: "تم إنشاء المراقبة. يبدأ التشغيل الأول قريبًا.",
  monitorFailed: "تعذّر إنشاء المراقبة.",
  monitorLoading: "جارٍ حساب التكلفة…",
  monitorNeedsPlan: "المراقبات غير متاحة في خطة مساحة العمل هذه.",

  loadedFiltersLabel: "تصفية النتائج المحمّلة",
  loadedFiltersHint: "يصفّي الإعلانات المحمّلة فقط. يستخدم 0 سجل.",
  mediaType: "الوسائط",
  anyOption: "الكل",
  status: "الحالة",
  statusActive: "قيد التشغيل",
  statusStopped: "له تاريخ توقف",
  cta: "زر الدعوة",
  landingDomain: "نطاق الصفحة المقصودة",
  minRunLength: (d) => `استمر ${d} يوم على الأقل`,
  showingLoaded: (shown, loaded) => `يُعرض ${shown} من ${loaded} محمّل`,
  clearLoadedFilters: "مسح",
  noLoadedMatches: "لا توجد إعلانات محمّلة تطابق هذه المرشحات. حمّل المزيد أو امسحها.",

  loadMore: "تحميل المزيد",
  loadingMore: "جارٍ تحميل المزيد…",
  loadedOf: (loaded, total) => `تم تحميل ${loaded} من ${total}`,
  allLoaded: "تم تحميل كل النتائج",
  loadMoreFailed: "تعذّر تحميل المزيد من النتائج.",

  shortcutsButton: "اختصارات لوحة المفاتيح",
  shortcutsTitle: "اختصارات لوحة المفاتيح",
  shortcutNext: "النتيجة التالية",
  shortcutPrev: "النتيجة السابقة",
  shortcutSave: "حفظ الإعلان المحدد",
  shortcutOpen: "فتح الإعلان المحدد في مكتبة الإعلانات",
  shortcutHelp: "إظهار هذه القائمة أو إخفاؤها",
  savedToast: "تم الحفظ في لوحتك",
  saveFailed: "تعذّر حفظ هذا الإعلان.",
}

const copy = { en, ar }

/** @returns {typeof en} */
export function useW92Copy() {
  const { lang } = useLanguage()
  return copy[lang] ?? en
}

export default copy
