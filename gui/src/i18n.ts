import { ref, computed } from 'vue'

export type Locale = 'uk' | 'en'

const STORAGE_KEY = 'shsm.locale'
const locale = ref<Locale>('uk')

const dict: Record<Locale, Record<string, string>> = {
  uk: {
    'app.title': 'Shattered Memories',
    'app.subtitle': 'Localization Tool',
    'app.version': 'v0.1.0',
    'app.languageLabel': 'Мова',
    'app.lang.uk': 'Українська',
    'app.lang.en': 'English',

    'sidebar.pickPlatform': 'Виберіть платформу:',
    'sidebar.nav': 'Навігація:',
    'platform.ps2': 'PlayStation 2',
    'platform.psp': 'PSP',
    'platform.wii': 'Nintendo Wii',

    'nav.texts': 'Тексти',
    'nav.search': 'Пошук',
    'nav.export': 'Експорт',
    'nav.import': 'Імпорт',
    'nav.settings': 'Налаштування',
    'nav.about': 'Про програму',

    'status.rows': 'Рядків у файлі:',
    'status.translated': 'Перекладено:',
    'status.saved': 'Збережено',
    'status.dirty': 'Змін не збережено',

    'strings.fileLabel': 'Файл:',
    'strings.encodingLabel': 'Кодування:',
    'strings.searchPlaceholder': 'Пошук…',
    'strings.thId': 'ID',
    'strings.thOriginal': 'Оригінал (Англійська)',
    'strings.thTranslation': 'Переклад (Українська)',
    'strings.untranslated': 'не перекладено',
    'strings.empty': 'Нічого не знайдено.',
    'strings.fileShared': 'translate_shared.txt  (загальний)',
    'strings.fileOnly': 'translate_{p}_only.txt  (тільки {P})',

    'search.title': ':: ПОШУК У ВСІХ ФАЙЛАХ',
    'search.sub': 'Глобальний пошук по чотирьох файлах перекладу.',
    'search.foundOf': 'Знайдено: {shown} із {total} (перекладено {tr}).',
    'search.placeholder': 'Текст або hash…',
    'search.fileLabel': 'Файл:',
    'search.statusLabel': 'Статус:',
    'search.allFiles': 'Усі файли',
    'search.statusAll': 'Усі',
    'search.statusTranslated': 'Перекладено',
    'search.statusUntranslated': 'Не перекладено',
    'search.loading': 'Завантаження…',
    'search.empty': 'Нічого не знайдено за цими фільтрами.',
    'search.dotTranslated': '● перекладено',
    'search.dotUntranslated': '○ не перекладено',
    'search.truncated': '… показано перші {shown} із {total}. Уточніть пошук.',

    'export.title': ':: ЕКСПОРТ / ЗБІРКА',
    'export.sub': 'Платформа: {label}. Запускає {script}; зливає {shared} + {only}, патчить шрифт, пакує файли в архіви, рекомпонує образ.',
    'export.runBuild': '▶  ЗАПУСТИТИ ЗБІРКУ',
    'export.building': 'ЗБИРАЄТЬСЯ…',
    'export.clearLog': 'ОЧИСТИТИ ЛОГ',
    'export.outputLabel': 'ВИХІДНИЙ ФАЙЛ',
    'export.outputPending': '(буде створено після збірки)',
    'export.openFolder': 'ВІДКРИТИ ПАПКУ',
    'export.logPlaceholder': "Лог буде з'являтись тут після запуску збірки.",
    'export.logHeader': '>>> python tool/build_ua_{platform}.py …',
    'export.spawnError': '!!! spawn error: {msg}',
    'export.buildDone': '=== BUILD DONE :: exit 0 ===',
    'export.buildFailed': '!!! BUILD FAILED :: exit {code} !!!',
    'export.platLabel.ps2': 'PlayStation 2  (ISO  ·  NTSC-U)',
    'export.platLabel.wii': 'Nintendo Wii   (RVZ  ·  NTSC-U)',
    'export.platLabel.psp': 'PSP            (ISO  ·  NTSC-U)',

    'export.analysisTitle': ':: АНАЛІЗ СЛОТУ',
    'export.analysisHint': 'Знайти рядки, де український переклад значно довший за англійський оригінал — вони першими переповнюють слот у data.arc.',
    'export.analysisRun': 'ЗНАЙТИ НАЙДОВШІ',
    'export.analysisRunning': 'Аналізую…',
    'export.analysisEmpty': 'Усі переклади коротші або рівні англ. оригіналу — слот не повинен переповнюватись.',
    'export.analysisErr': 'Помилка: не знайдено оригінальних рядків. Спочатку розпакуй проєкт у Імпорт.',
    'export.analysisTotalRows': 'Перекладених рядків: {n}',
    'export.analysisLongerRows': 'Довших за оригінал: {n}',
    'export.analysisOversum': 'Сумарний приріст: <b>+{n}</b> симв.',
    'export.analysisThHash': 'Hash',
    'export.analysisThEn': 'EN (оригінал)',
    'export.analysisThUa': 'UA (переклад)',
    'export.analysisThDelta': 'Δ симв.',
    'export.analysisShownOf': 'Показано перші {shown} із {total}',

    'import.title': ':: ІМПОРТ / ПРОЄКТИ',
    'import.sub': 'Кожен проєкт — це джерельний ISO/RVZ для конкретної платформи. Розпакування виконується автоматично; шрифти й рядки витягуються у {a}, {b} або {c}.',
    'import.add': '+  ДОДАТИ НОВИЙ ПРОЄКТ',
    'import.foundCount': 'Знайдено проєктів: {n}',
    'import.empty.line1': 'Немає жодного проєкту.',
    'import.empty.line2': 'Натисни «Додати новий проєкт», щоб вибрати ISO джерельного диску для PS2 / Wii / PSP.',
    'import.row.iso': 'ISO:',
    'import.row.reference': 'Референс:',
    'import.row.created': 'Створено:',
    'import.row.extracted': 'Розпаковано:',
    'import.notExtracted': 'не виконано',
    'import.confirmRemove': 'Видалити цей проєкт із конфігу? (Файли на диску не видаляються.)',
    'import.dash': '—',

    'settings.title': ':: НАЛАШТУВАННЯ / ДІАГНОСТИКА',
    'settings.sub': 'Стан робочого середовища: шляхи, статистика по перекладу, кількість гліфів для кожної платформи. Тут лише перегляд (не редагується) — конфіг шляхів задається в коді.',
    'settings.cardPaths': ':: РОБОЧА ПАПКА',
    'settings.cardFiles': ':: ФАЙЛИ ПЕРЕКЛАДУ',
    'settings.cardGlyphs': ':: ГЛІФИ ШРИФТУ',
    'settings.cardOutputs': ':: ВИХІДНІ ОБРАЗИ',
    'settings.kProjectRoot': 'Project Root',
    'settings.kPython': 'Python  (з $PATH)',
    'settings.thFile': 'Файл',
    'settings.thTotal': 'Всього',
    'settings.thTranslated': 'Перекладено',
    'settings.thProgress': 'Прогрес',
    'settings.totalRow': 'УСЬОГО',
    'settings.glyphPng': 'PNG-гліфи',
    'settings.openBtn': 'ВІДКРИТИ',
    'settings.loading': 'завантаження…',

    'about.tag': 'LOCALIZATION TOOL  ·  v{v}',
    'about.aboutTitle': ':: ПРО ПРОГРАМУ',
    'about.aboutP1': '<b>SHATTERED MEMORIES — Localization Tool</b> — інструмент для української локалізації гри <i>Silent Hill: Shattered Memories</i> на трьох платформах: <b>PlayStation 2 (NTSC-U)</b>, <b>Nintendo Wii (R5WEA4)</b>, <b>PSP (ULUS)</b>.',
    'about.aboutP2': 'Усі три збірки беруть текст з одного централізованого джерела <code>TEXT_TRANSLATION/translate_shared.txt</code> (4853 hash\'и — об\'єднання ключів усіх трьох платформ) + по <code>translate_X_only.txt</code> для платформо-специфічних рядків. Тож переклад робиться один раз і автоматично потрапляє в усі три ROM-збірки.',
    'about.howTitle': ':: ЯК ВОНО ПРАЦЮЄ',
    'about.howUnpack': '<b>Розпакування</b> — при першому запуску інструмент бере вихідний образ диску (ISO / RVZ) і витягує з нього файли через DolphinTool (Wii), 7-Zip (PSP) або прямий парсер ISO9660 (PS2).',
    'about.howFont': '<b>Шрифт</b> — Font_EUR (KFONT-формат) патчиться: до існуючих Latin-символів додаються всі необхідні літери українського алфавіту (включно з Є є Ї ї І і Ґ ґ) шляхом donor-remap слотів Latin-1 supplements та extension таблиці CharRecord. На Wii/PSP цей шрифт сидить всередині main.dol / EBOOT.BIN як вбудований zlib-стрим.',
    'about.howStrings': '<b>Рядки</b> — strings таблиці (translate_sys / translate_ui у data.arc) перепаковуються; для літер без окремих glyph-слотів використовується підстановка на візуально-схожі Latin-двійники (А→A, В→B тощо).',
    'about.howBuild': '<b>Збірка</b> — модифікований data.arc записується назад у потрібний слот, диск рекомпонується (wit для Wii, pycdlib для PSP, in-place patch для PS2) і конвертується у фінальний формат (RVZ для Dolphin, ISO для PCSX2 / PPSSPP).',
    'about.stackTitle': ':: ТЕХНОЛОГІЧНИЙ СТЕК',
    'about.stack.gui': 'GUI shell, frontend',
    'about.stack.ts': 'Type-safe renderer + IPC',
    'about.stack.py': '25 utility-скриптів для KFONT, RLE, ARC, ISO, strings',
    'about.stack.zopfli': 'Краще zlib-стиснення для slot-fit пайплайнів',
    'about.stack.wii': 'Wii ISO/RVZ розпакування і збірка',
    'about.stack.psp': 'PSP ISO9660 розпакування і збірка',
    'about.authorTitle': ':: АВТОР',
    'about.author.studio': '«Little Bit»',
    'about.author.meta1': 'Український розробник, ентузіаст retro-портів.',
    'about.author.meta2': 'Грає у класичні survival horror, реверсить ROM\'и, перекладає те, що не локалізували видавці.',
    'about.licenseTitle': ':: ЛІЦЕНЗІЯ',
    'about.license.p1': 'Інструмент і всі скрипти — open source. Перекладений текст є фанатською роботою; <b>Silent Hill: Shattered Memories</b> належить Konami. Цей інструмент не модифікує ваш оригінальний ROM — він створює окрему пропатчену копію. Користувач повинен надати свій легальний дамп диску.',
    'about.license.p2': '© 2026 Dmytro Bidlov / Little Bit. Built with ❤ для української спільноти.',

    'modal.title': 'NEW PROJECT',
    'modal.step': 'STEP {n} OF 3',
    'modal.prompt.pickPlatform': 'Choose target platform.',
    'modal.prompt.sources': 'Point to the source disc image for {name}.',
    'modal.prompt.extracting': 'Extracting {name}…',
    'modal.platformLabel': 'PLATFORM',
    'modal.sourceLabel': 'SOURCE ISO / RVZ',
    'modal.referenceLabel': 'РЕФЕРЕНСНИЙ ОБРАЗ  (опціонально)',
    'modal.referencePlaceholder': "(не обов'язково — для додаткових донор-слотів шрифту)",
    'modal.back': 'BACK',
    'modal.extract': 'EXTRACT & CONTINUE',
    'modal.continue': 'OPEN PROJECT',
    'modal.continueAnyway': 'CONTINUE ANYWAY',
    'modal.note.ps2': 'Джерело: оригінальний NTSC-U ISO.',
    'modal.note.wii': 'Джерело: оригінальний NTSC-U RVZ або ISO. Опційно — додатковий референсний образ для шрифту.',
    'modal.note.psp': 'Джерело: оригінальний NTSC-U ISO. Опційно — додатковий референсний образ для шрифту.',

    'common.dash': '—',
  },

  en: {
    'app.title': 'Shattered Memories',
    'app.subtitle': 'Localization Tool',
    'app.version': 'v0.1.0',
    'app.languageLabel': 'Language',
    'app.lang.uk': 'Українська',
    'app.lang.en': 'English',

    'sidebar.pickPlatform': 'Select platform:',
    'sidebar.nav': 'Navigation:',
    'platform.ps2': 'PlayStation 2',
    'platform.psp': 'PSP',
    'platform.wii': 'Nintendo Wii',

    'nav.texts': 'Strings',
    'nav.search': 'Search',
    'nav.export': 'Export',
    'nav.import': 'Import',
    'nav.settings': 'Settings',
    'nav.about': 'About',

    'status.rows': 'Rows in file:',
    'status.translated': 'Translated:',
    'status.saved': 'Saved',
    'status.dirty': 'Unsaved changes',

    'strings.fileLabel': 'File:',
    'strings.encodingLabel': 'Encoding:',
    'strings.searchPlaceholder': 'Search…',
    'strings.thId': 'ID',
    'strings.thOriginal': 'Original (English)',
    'strings.thTranslation': 'Translation (Ukrainian)',
    'strings.untranslated': 'not translated',
    'strings.empty': 'Nothing found.',
    'strings.fileShared': 'translate_shared.txt  (shared)',
    'strings.fileOnly': 'translate_{p}_only.txt  ({P} only)',

    'search.title': ':: SEARCH ACROSS ALL FILES',
    'search.sub': 'Global search across the four translation files.',
    'search.foundOf': 'Found: {shown} of {total} (translated {tr}).',
    'search.placeholder': 'Text or hash…',
    'search.fileLabel': 'File:',
    'search.statusLabel': 'Status:',
    'search.allFiles': 'All files',
    'search.statusAll': 'All',
    'search.statusTranslated': 'Translated',
    'search.statusUntranslated': 'Untranslated',
    'search.loading': 'Loading…',
    'search.empty': 'Nothing matched these filters.',
    'search.dotTranslated': '● translated',
    'search.dotUntranslated': '○ not translated',
    'search.truncated': '… showing the first {shown} of {total}. Refine the search.',

    'export.title': ':: EXPORT / BUILD',
    'export.sub': 'Platform: {label}. Runs {script}; merges {shared} + {only}, patches the font, packs files into archives, recomposes the image.',
    'export.runBuild': '▶  RUN BUILD',
    'export.building': 'BUILDING…',
    'export.clearLog': 'CLEAR LOG',
    'export.outputLabel': 'OUTPUT FILE',
    'export.outputPending': '(will be created after the build)',
    'export.openFolder': 'OPEN FOLDER',
    'export.logPlaceholder': 'Log will appear here once the build starts.',
    'export.logHeader': '>>> python tool/build_ua_{platform}.py …',
    'export.spawnError': '!!! spawn error: {msg}',
    'export.buildDone': '=== BUILD DONE :: exit 0 ===',
    'export.buildFailed': '!!! BUILD FAILED :: exit {code} !!!',
    'export.platLabel.ps2': 'PlayStation 2  (ISO  ·  NTSC-U)',
    'export.platLabel.wii': 'Nintendo Wii   (RVZ  ·  NTSC-U)',
    'export.platLabel.psp': 'PSP            (ISO  ·  NTSC-U)',

    'export.analysisTitle': ':: SLOT ANALYSIS',
    'export.analysisHint': 'Find rows where the Ukrainian translation is significantly longer than the English source — those are the rows that overflow the data.arc slot first.',
    'export.analysisRun': 'FIND LONGEST',
    'export.analysisRunning': 'Analysing…',
    'export.analysisEmpty': 'All translations are shorter than or equal to the English source — the slot should not overflow.',
    'export.analysisErr': "Error: original strings not found. Extract the project from the Import tab first.",
    'export.analysisTotalRows': 'Translated rows: {n}',
    'export.analysisLongerRows': 'Longer than source: {n}',
    'export.analysisOversum': 'Total overflow: <b>+{n}</b> chars',
    'export.analysisThHash': 'Hash',
    'export.analysisThEn': 'EN (source)',
    'export.analysisThUa': 'UA (translation)',
    'export.analysisThDelta': 'Δ chars',
    'export.analysisShownOf': 'Showing first {shown} of {total}',

    'import.title': ':: IMPORT / PROJECTS',
    'import.sub': 'Each project is a source ISO/RVZ for a specific platform. Extraction runs automatically; fonts and strings end up in {a}, {b} or {c}.',
    'import.add': '+  ADD NEW PROJECT',
    'import.foundCount': 'Projects found: {n}',
    'import.empty.line1': 'No projects yet.',
    'import.empty.line2': 'Click "Add new project" to pick a source ISO for PS2 / Wii / PSP.',
    'import.row.iso': 'ISO:',
    'import.row.reference': 'Reference:',
    'import.row.created': 'Created:',
    'import.row.extracted': 'Extracted:',
    'import.notExtracted': 'not extracted',
    'import.confirmRemove': 'Remove this project from the config? (Files on disk are not deleted.)',
    'import.dash': '—',

    'settings.title': ':: SETTINGS / DIAGNOSTICS',
    'settings.sub': 'Workspace state: paths, translation statistics, glyph counts for each platform. View-only — paths live in code.',
    'settings.cardPaths': ':: WORKING DIRECTORY',
    'settings.cardFiles': ':: TRANSLATION FILES',
    'settings.cardGlyphs': ':: FONT GLYPHS',
    'settings.cardOutputs': ':: OUTPUT IMAGES',
    'settings.kProjectRoot': 'Project Root',
    'settings.kPython': 'Python  (from $PATH)',
    'settings.thFile': 'File',
    'settings.thTotal': 'Total',
    'settings.thTranslated': 'Translated',
    'settings.thProgress': 'Progress',
    'settings.totalRow': 'TOTAL',
    'settings.glyphPng': 'PNG glyphs',
    'settings.openBtn': 'OPEN',
    'settings.loading': 'loading…',

    'about.tag': 'LOCALIZATION TOOL  ·  v{v}',
    'about.aboutTitle': ':: ABOUT',
    'about.aboutP1': '<b>SHATTERED MEMORIES — Localization Tool</b> is a toolkit for Ukrainian localization of <i>Silent Hill: Shattered Memories</i> on three platforms: <b>PlayStation 2 (NTSC-U)</b>, <b>Nintendo Wii (R5WEA4)</b>, <b>PSP (ULUS)</b>.',
    'about.aboutP2': 'All three builds pull text from a single centralized source <code>TEXT_TRANSLATION/translate_shared.txt</code> (4853 hashes — the union of keys across all three platforms) plus <code>translate_X_only.txt</code> for platform-specific lines. Translation is done once and is automatically applied to every ROM build.',
    'about.howTitle': ':: HOW IT WORKS',
    'about.howUnpack': '<b>Unpacking</b> — on first run the tool grabs the source disc image (ISO / RVZ) and extracts files via DolphinTool (Wii), 7-Zip (PSP) or a direct ISO9660 parser (PS2).',
    'about.howFont': '<b>Font</b> — Font_EUR (KFONT format) is patched: all required Ukrainian alphabet letters (including Є є Ї ї І і Ґ ґ) are added on top of the existing Latin set via donor-remap of Latin-1 supplement slots and the CharRecord extension table. On Wii/PSP this font lives inside main.dol / EBOOT.BIN as an embedded zlib stream.',
    'about.howStrings': '<b>Strings</b> — string tables (translate_sys / translate_ui in data.arc) are repacked; for letters without their own glyph slot, visually-similar Latin lookalikes (А→A, В→B etc.) are substituted.',
    'about.howBuild': '<b>Build</b> — the modified data.arc is written back to its slot, the disc is recomposed (wit for Wii, pycdlib for PSP, in-place patch for PS2) and converted into the final format (RVZ for Dolphin, ISO for PCSX2 / PPSSPP).',
    'about.stackTitle': ':: TECH STACK',
    'about.stack.gui': 'GUI shell, frontend',
    'about.stack.ts': 'Type-safe renderer + IPC',
    'about.stack.py': '25 utility scripts for KFONT, RLE, ARC, ISO, strings',
    'about.stack.zopfli': 'Better zlib compression for slot-fit pipelines',
    'about.stack.wii': 'Wii ISO/RVZ unpack and build',
    'about.stack.psp': 'PSP ISO9660 unpack and build',
    'about.authorTitle': ':: AUTHOR',
    'about.author.studio': '"Little Bit"',
    'about.author.meta1': 'Ukrainian developer, retro-port enthusiast.',
    'about.author.meta2': 'Plays classic survival horror, reverses ROMs, translates what publishers never localized.',
    'about.licenseTitle': ':: LICENSE',
    'about.license.p1': 'The tool and all scripts are open source. The translation text is a fan work; <b>Silent Hill: Shattered Memories</b> belongs to Konami. This tool does not modify your original ROM — it produces a separate patched copy. The user must supply their own legal disc dump.',
    'about.license.p2': '© 2026 Dmytro Bidlov / Little Bit. Built with ❤ for the Ukrainian community.',

    'modal.title': 'NEW PROJECT',
    'modal.step': 'STEP {n} OF 3',
    'modal.prompt.pickPlatform': 'Choose target platform.',
    'modal.prompt.sources': 'Point to the source disc image for {name}.',
    'modal.prompt.extracting': 'Extracting {name}…',
    'modal.platformLabel': 'PLATFORM',
    'modal.sourceLabel': 'SOURCE ISO / RVZ',
    'modal.referenceLabel': 'REFERENCE IMAGE  (optional)',
    'modal.referencePlaceholder': '(optional — for extra font donor slots)',
    'modal.back': 'BACK',
    'modal.extract': 'EXTRACT & CONTINUE',
    'modal.continue': 'OPEN PROJECT',
    'modal.continueAnyway': 'CONTINUE ANYWAY',
    'modal.note.ps2': 'Source: original NTSC-U ISO.',
    'modal.note.wii': 'Source: original NTSC-U RVZ or ISO. Optionally a secondary reference image for the font.',
    'modal.note.psp': 'Source: original NTSC-U ISO. Optionally a secondary reference image for the font.',

    'common.dash': '—',
  },
}

function applyParams(s: string, params?: Record<string, string | number>): string {
  if (!params) return s
  return s.replace(/\{(\w+)\}/g, (_, k) => (params[k] !== undefined ? String(params[k]) : `{${k}}`))
}

export function t(key: string, params?: Record<string, string | number>): string {
  const table = dict[locale.value] ?? dict.en
  const raw = table[key] ?? dict.en[key] ?? key
  return applyParams(raw, params)
}

export function setLocale(l: Locale) {
  if (l !== 'uk' && l !== 'en') return
  locale.value = l
  try { localStorage.setItem(STORAGE_KEY, l) } catch {}
}

export function getLocale(): Locale { return locale.value }

export const localeRef = locale
export const tr = computed(() => locale.value)   // re-export reactive trigger

export async function initLocale() {
  let saved: Locale | null = null
  try {
    const s = localStorage.getItem(STORAGE_KEY)
    if (s === 'uk' || s === 'en') saved = s
  } catch {}
  if (saved) {
    locale.value = saved
    return
  }
  // First launch — derive from OS locale via main process.
  try {
    const sys = await window.api.defaultLocale()
    locale.value = sys.toLowerCase().startsWith('uk') ? 'uk' : 'en'
  } catch {
    locale.value = 'en'
  }
}
