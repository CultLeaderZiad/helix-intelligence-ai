export const docsReferenceCopy = {
  en: {
    title: "Reference status",
    message:
      "Some features or API endpoints described here may be historical, experimental, or unavailable in this workspace. Documentation does not grant access; an administrator controls access and usage limits. Verify current availability before relying on a feature or endpoint.",
    usage:
      "Usage controls are not prices or purchasable credits. This workspace does not provide checkout or subscription management.",
  },
  ar: {
    title: "حالة المواد المرجعية",
    message:
      "قد تكون بعض الميزات أو نقاط API المذكورة هنا تاريخية أو تجريبية أو غير متاحة في مساحة العمل هذه. لا يمنح التوثيق صلاحية الوصول؛ يتحكم المشرف في الوصول وحدود الاستخدام. تحقّق من التوافر الحالي قبل الاعتماد على أي ميزة أو نقطة API.",
    usage:
      "حدود الاستخدام ليست أسعاراً أو رصيداً قابلاً للشراء. لا تتوفر في مساحة العمل هذه إدارة للدفع أو الاشتراكات.",
  },
}

export function getDocsReferenceCopy(lang) {
  return docsReferenceCopy[lang] ?? docsReferenceCopy.en
}
