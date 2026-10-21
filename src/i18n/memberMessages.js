export const memberMessages = {
  en: {
    settingsNavigation: "Settings",
    profileAccountBreadcrumb: "Account & profile",
    profileSettingsTitle: "Account & profile settings",
    profileSettingsDescription: "Manage your personal details, profile photo, and account security.",
    profileLoadFailed: "Could not load your profile. Refresh and try again.",
    profileAvatarUpdated: "Profile photo updated.",
    profileAvatarUploadFailed: "Could not upload your photo. Try again.",
    profileCurrentPasswordRequired: "Enter your current password to set a new one.",
    profilePasswordTooShort: "Your new password must be at least 8 characters.",
    profilePasswordMismatch: "The new passwords do not match.",
    profileUpdated: "Your profile was updated.",
    profileUpdateFailed: "Could not update your profile. Check your details and try again.",
    profilePhoto: "Profile photo",
    changePhoto: "Change photo",
    photoUploadGuidance: "Upload a PNG, JPG, or WebP image. Maximum size: 5 MB.",
    uploadingPhoto: "Uploading…",
    uploadPhoto: "Upload new photo",
    personalInformation: "Personal information",
    fullName: "Full name",
    fullNamePlaceholder: "e.g. John Doe",
    emailAddress: "Email address",
    workspaceEmailDescription: "Account email linked to your workspace.",
    roleLabel: "Role",
    profileRoleCustomer: "Customer",
    profileRoleMember: "Member",
    profileRoleAdmin: "Administrator",
    profileRoleOwner: "Owner",
    profileRoleUser: "User",
    changePassword: "Change password",
    currentPassword: "Current password",
    showCurrentPassword: "Show current password",
    hideCurrentPassword: "Hide current password",
    newPassword: "New password",
    showNewPassword: "Show new password",
    hideNewPassword: "Hide new password",
    confirmNewPassword: "Confirm new password",
    showConfirmPassword: "Show password confirmation",
    hideConfirmPassword: "Hide password confirmation",
    savingChanges: "Saving changes…",
    saveSettings: "Save settings",
    loadingProfile: "Loading profile…",
  },
  ar: {
    settingsNavigation: "الإعدادات",
    profileAccountBreadcrumb: "الحساب والملف الشخصي",
    profileSettingsTitle: "إعدادات الحساب والملف الشخصي",
    profileSettingsDescription: "أدِر بياناتك الشخصية وصورة ملفك الشخصي وأمان حسابك.",
    profileLoadFailed: "تعذّر تحميل ملفك الشخصي. حدّث الصفحة وحاول مرة أخرى.",
    profileAvatarUpdated: "تم تحديث صورة الملف الشخصي.",
    profileAvatarUploadFailed: "تعذّر رفع الصورة. حاول مرة أخرى.",
    profileCurrentPasswordRequired: "أدخل كلمة المرور الحالية لتعيين كلمة مرور جديدة.",
    profilePasswordTooShort: "يجب ألا تقل كلمة المرور الجديدة عن 8 أحرف.",
    profilePasswordMismatch: "كلمتا المرور الجديدتان غير متطابقتين.",
    profileUpdated: "تم تحديث ملفك الشخصي.",
    profileUpdateFailed: "تعذّر تحديث ملفك الشخصي. تحقق من البيانات وحاول مرة أخرى.",
    profilePhoto: "صورة الملف الشخصي",
    changePhoto: "تغيير الصورة",
    photoUploadGuidance: "ارفع صورة بصيغة PNG أو JPG أو WebP، بحد أقصى 5 ميغابايت.",
    uploadingPhoto: "جارٍ رفع الصورة…",
    uploadPhoto: "رفع صورة جديدة",
    personalInformation: "المعلومات الشخصية",
    fullName: "الاسم الكامل",
    fullNamePlaceholder: "مثال: أحمد محمد",
    emailAddress: "البريد الإلكتروني",
    workspaceEmailDescription: "البريد الإلكتروني المرتبط بمساحة العمل.",
    roleLabel: "الدور",
    profileRoleCustomer: "عميل",
    profileRoleMember: "عضو",
    profileRoleAdmin: "مشرف",
    profileRoleOwner: "مالك",
    profileRoleUser: "مستخدم",
    changePassword: "تغيير كلمة المرور",
    currentPassword: "كلمة المرور الحالية",
    showCurrentPassword: "إظهار كلمة المرور الحالية",
    hideCurrentPassword: "إخفاء كلمة المرور الحالية",
    newPassword: "كلمة المرور الجديدة",
    showNewPassword: "إظهار كلمة المرور الجديدة",
    hideNewPassword: "إخفاء كلمة المرور الجديدة",
    confirmNewPassword: "تأكيد كلمة المرور الجديدة",
    showConfirmPassword: "إظهار تأكيد كلمة المرور",
    hideConfirmPassword: "إخفاء تأكيد كلمة المرور",
    savingChanges: "جارٍ حفظ التغييرات…",
    saveSettings: "حفظ الإعدادات",
    loadingProfile: "جارٍ تحميل الملف الشخصي…",
  },
}

export function getMemberMessage(lang, key) {
  return memberMessages[lang]?.[key] || memberMessages.en[key] || key
}

export function getMemberRoleLabel(lang, role) {
  const roleKeys = {
    admin: "profileRoleAdmin",
    org_admin: "profileRoleAdmin",
    organization_admin: "profileRoleAdmin",
    workspace_admin: "profileRoleAdmin",
    super_admin: "profileRoleAdmin",
    owner: "profileRoleOwner",
    member: "profileRoleMember",
    customer: "profileRoleCustomer",
    user: "profileRoleUser",
  }
  const key = roleKeys[String(role || "").toLowerCase()]
  return getMemberMessage(lang, key || "profileRoleUser")
}

/** @param {Intl.DateTimeFormatOptions} [options] */
export function formatMemberDate(value, lang, fallback, options = { dateStyle: "medium" }) {
  if (value === null || value === undefined || value === "") return fallback
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return fallback
  return date.toLocaleString(lang === "ar" ? "ar" : "en", options)
}

export function memberTimestamp(value) {
  if (value === null || value === undefined || value === "") return 0
  const timestamp = new Date(value).getTime()
  return Number.isFinite(timestamp) ? timestamp : 0
}
