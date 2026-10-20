# قياس وزن Dependencies

القياس من workspace المثبت بالفعل، من غير تثبيت أو تحديث packages. الأرقام دي حجم الملفات على القرص؛ مش حجم download أو JavaScript اللي بيتبعت للعميل. البيانات التفصيلية والversions في dependencies.json.

## الأرقام

- node_modules حجمه 234,236,741 bytes؛ فيه 397 package directories تحت .pnpm، والـ store المقاس 222,123,714 bytes. ده يشمل dev/test dependencies ومش production payload.
- package.json فيه 10 runtime dependencies و19 development dependencies.
- ملفات dist الناتجة حجمها الإجمالي 1,958,073 bytes عبر 122 ملف. أكبر JavaScript entry: 481,532 bytes raw و147,494 gzip. DocSearchModal chunk: 182,288 raw و51,820 gzip. CSS: 135,665 raw و25,694 gzip. التفصيل في build.log.
- بيئة Python الموجودة في /tmp/w4-venv فيها 58 distributions. حجم البيئة 181,398,865 bytes، وsite-packages 181,369,362 bytes. ده قياس للبيئة المثبتة، مش لحجم production container.
- أكبر distributions حسب مجموع الملفات المسجلة بالـ metadata: SQLAlchemy نحو 22.5 MB، botocore نحو 22.2 MB، Pillow نحو 21.1 MB، uvloop نحو 16.6 MB، cryptography نحو 15.6 MB، asyncpg نحو 13.4 MB. ده قياس ملفات distribution؛ ماينفعش نجمعه باعتباره الحجم النهائي للصورة.

## مراجعة الإزالة

عملت literal source-reference search لكل runtime dependency في src/؛ مفيش dependency مباشرة واضحة إنها unused. أمثلة: driver.js في src/app/OnboardingTour.jsx، وgsap في src/components/ui/CardSwap.jsx، وclsx وtailwind-merge في src/lib/utils.js، والخطوط في src/main.jsx وsrc/styles/globals.css. lucide-react مستخدم في مكونات وصفحات كتير. الفحص نصي، مش AST، ومش بيثبت إن كل export أو dependency transitive مطلوب؛ dynamic imports وشرطيات build محتاجة مراجعة لو ظهرت مشكلة محددة. مفيش توصية بحذف dependency مباشرة حاليًا.

## الاستنتاج

- ما نقللش node_modules لمجرد الرقم؛ ده developer footprint، مش payload المستخدم.
- أكبر asset هو main JS. افحص route lazy-loading وcoverage قبل أي تقسيم إضافي؛ DocSearchModal بالفعل chunk مستقل.
- lucide-react من أكبر directories المثبتة، لكن ده مش bundle cost؛ named imports ممكن تتشال بالـ tree-shaking. راجع bundle report قبل استبدال مكتبة icons.
- Python packages الثقيلة مرتبطة بالـ ORM/database/media/storage. مايتشالش أي package من requirements من غير إثبات إن integration مش مستخدمة ومراجعة transitive/runtime dependencies.
