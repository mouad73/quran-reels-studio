## أسهل طريقة للتشغيل على Windows

1. نزّل **Quran-Reels-Studio-0.3.0-Windows-x64.zip** من الملفات أدناه.
2. فك الضغط كاملاً (Extract All).
3. افتح **QuranReelsStudio.exe** وانتظر التحضير الأول، ثم تفتح الأداة في المتصفح.

لا تحتاج إلى تثبيت Python أو FFmpeg يدوياً، ولا تحتاج إلى صلاحيات المدير.
يتضمن التنزيل Python ومتطلبات التطبيق وتشكيل العربية. ينزّل التشغيل الأول
FFmpeg مباشرة من مصدره، ويتحقق من SHA-256، ثم يحتفظ به للتشغيلات التالية.
يلزم الإنترنت للنص والتلاوة ولإعداد محرك الفيديو أول مرة.

أبقِ نافذة التشغيل مفتوحة أثناء العمل. إغلاقها يوقف الأداة وأي تصدير جارٍ،
ويحافظ على النتائج المحفوظة. زر «مجلد الفيديوهات» يفتح النتائج في مجلد المستخدم.
الواجهة الحالية بالإنجليزية ونافذة التشغيل بالعربية.

المفاتيح اختيارية للخلفيات: Pexels أو Pixabay بمفتاحك، أو فيديو محلي دون مفتاح.

## Windows x64 portable package

- Private Python runtime; no global Python installation or PATH changes.
- Arabic launcher with automatic first-run video-engine setup, browser opening,
  output-folder and log buttons, single-instance handling and process cleanup.
- SHA-256-pinned downloads and locked wheel hashes; bundled dependency notices
  and FriBiDi corresponding source/build recipe. FFmpeg is downloaded upstream,
  not redistributed in our archive.
- All video/logo/layout features from v0.2 remain available. Rendering stays local.
- Intended for Windows 10/11 x64 with the system .NET Framework 4.x.
- Unsigned executable; source installation remains available for managed devices.

Verification: 42 automated tests, packaged Arabic shaping and H.264/AAC encoding,
an Arabic-named data folder, and local Streamlit health with no Python/FFmpeg on
PATH. The smoke-result asset records the package checks. This was not tested on
a clean Windows VM, macOS or Docker.

[Arabic tutorial and installation guide](https://techmouad.com/إنشاء-فيديو-قرآن/)

The versioned Windows ZIP is the app download. GitHub's automatically generated
“Source code” ZIP is the developer source and still needs Python/FFmpeg setup.
