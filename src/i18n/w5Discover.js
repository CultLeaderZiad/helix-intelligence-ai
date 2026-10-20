export const en = {
  statusQueued: "Queued",
  statusRunning: "Running",
  statusCancelling: "Cancellation pending",
  statusCancelError: "Cancellation not confirmed",
  statusCancelled: "Cancelled",
  statusTimedOut: "Timed out",
  statusFailed: "Failed",
  statusSucceeded: "Completed",
  cancel: "Cancel search",
  cancelling: "Cancellation requested. Waiting for the server to confirm.",
  cancelFailed: "The server has not confirmed cancellation. This job may still be running.",
  retryCancel: "Retry cancellation",
  cancelled: "The server confirmed that this search was cancelled.",
  timedOut: "The server ended this search after its deadline.",
  retrySearch: "Retry search",
  timeoutNoJob: "The request timed out before a job ID was received, so cancellation could not be confirmed.",
}

export const ar = {
  statusQueued: "في قائمة الانتظار",
  statusRunning: "قيد التنفيذ",
  statusCancelling: "طلب الإلغاء قيد الانتظار",
  statusCancelError: "لم يتم تأكيد الإلغاء",
  statusCancelled: "تم الإلغاء",
  statusTimedOut: "انتهت المهلة",
  statusFailed: "فشل",
  statusSucceeded: "اكتمل",
  cancel: "إلغاء البحث",
  cancelling: "تم طلب الإلغاء. ننتظر تأكيد الخادم.",
  cancelFailed: "لم يؤكد الخادم الإلغاء. قد تظل المهمة قيد التنفيذ.",
  retryCancel: "إعادة محاولة الإلغاء",
  cancelled: "أكد الخادم إلغاء هذا البحث.",
  timedOut: "أنهى الخادم هذا البحث بعد انتهاء مهلته.",
  retrySearch: "إعادة البحث",
  timeoutNoJob: "انتهت مهلة الطلب قبل استلام معرّف المهمة، لذلك تعذر تأكيد الإلغاء.",
}

export default { en, ar }
