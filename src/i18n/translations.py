"""Language bundles for Visio Eye.

Each language is a flat ``key -> string`` dict. Keys are slugs (short,
snake_case, English) so they're stable across translations. ``en``
must define every key; ``uz`` and ``ru`` may omit entries — the lookup
falls back to English automatically.
"""

TRANSLATIONS = {
    # ============================================================
    # English
    # ============================================================
    "en": {
        # ----- main window -----
        "app.subtitle": "Screen Recorder",
        "main.studio": "Recording Studio",
        "main.studio_tag": "Professional capture",
        "main.btn.record": "● Record",
        "main.btn.pause": "⏸  Pause",
        "main.btn.resume": "▶  Resume",
        "main.btn.stop": "■ Stop",
        "main.btn.screenshot": "📷 Screenshot",
        "main.btn.settings": "⚙ Settings",
        "main.btn.author": "👤 AUTOR",
        "main.card.mode": "MODE",
        "main.card.output": "OUTPUT",
        "main.card.overlays": "OVERLAYS",
        "main.card.camera": "Camera",
        "main.card.logo": "Logo",
        "main.card.change": "Change…",
        "main.card.open": "Open",
        "main.mode.fullscreen": "Full screen",
        "main.mode.window": "Active window",
        "main.mode.region": "Region…",
        "main.metric.cpu": "CPU",
        "main.metric.mem": "MEM",
        "main.metric.disk": "DISK",
        "main.metric.fps": "FPS",
        "main.metric.status": "STATUS",
        "main.status.idle": "Idle",
        "main.status.ready": "Ready",
        "main.status.recording": "Recording",
        "main.status.paused": "Paused",
        "main.log.recording_to": "Recording → {path}",
        "main.log.recording_started": "Recording started via {backend} backend",
        "main.log.resumed": "Resumed",
        "main.log.paused": "Paused",
        "main.log.dubber_on": "Dubber enabled (loading Whisper model…)",
        "main.log.dubber_off": "Dubber stopped",
        "main.log.dubber_fail": "Dubber failed to start: {err}",
        "main.dialog.recording_failed": "Recording failed",
        "main.dialog.dubbing_failed": "Dubbing failed to start",
        "main.dialog.ffmpeg_missing": "FFmpeg missing",
        "main.dialog.ffmpeg_install":
            "FFmpeg is not installed.\n\nInstall it with:\n"
            "    sudo apt install ffmpeg",
        "main.wayland_tips":
            "\n\nWayland tips:\n"
            "  • Make sure you GRANTED the screen-share permission in the\n"
            "    portal dialog that appeared.\n"
            "  • Install missing tools:\n"
            "      sudo apt install gstreamer1.0-tools \\\n"
            "        gstreamer1.0-plugins-good \\\n"
            "        gstreamer1.0-plugins-bad \\\n"
            "        gstreamer1.0-pipewire python3-dbus python3-gi",
        # ----- region selector -----
        "region.hint": "Drag to select a region · ESC to cancel",
        # ----- settings dialog -----
        "settings.title": "Settings",
        "settings.window_title": "Visio Eye — Settings",
        "settings.tab.general": "General",
        "settings.tab.video": "Video",
        "settings.tab.audio": "Audio",
        "settings.tab.camera": "Camera",
        "settings.tab.logo": "Logo / Overlay",
        "settings.tab.output": "Output",
        "settings.tab.hotkeys": "Hotkeys",
        "settings.tab.dubbing": "Dubbing",
        "settings.tab.streaming": "Streaming",
        "settings.tab.html": "HTML Overlay",
        "settings.btn.cancel": "Cancel",
        "settings.btn.save": "Save",
        "settings.btn.author": "AUTOR",
        "settings.btn.remove": "Remove",
        "settings.btn.add_target": "+ Add another target",
        "settings.btn.browse": "Browse…",
        "settings.btn.pick_logo": "Pick…",
        # general
        "general.language": "Language",
        "general.theme": "Theme",
        "general.start_with_system": "Start with system",
        "general.lang_changed_title": "Restart required",
        "general.lang_changed_body":
            "The language change will be fully applied after restarting "
            "Visio Eye.",
        # video
        "video.fps": "FPS",
        "video.resolution": "Resolution",
        "video.codec": "Codec",
        "video.container": "Container",
        "video.bitrate": "Bitrate",
        "video.encoder": "Encoder",
        # audio
        "audio.source": "Audio Source",
        "audio.src.mic": "Microphone",
        "audio.src.desk": "System",
        "audio.src.both": "Both",
        "audio.src.none": "None",
        "audio.devices": "Devices",
        "audio.mic": "Microphone",
        "audio.desk": "Desktop / Loopback",
        "audio.vol_quality": "Volume & Quality",
        "audio.mic_volume": "Mic volume",
        "audio.desk_volume": "Desktop volume",
        "audio.quality_kbps": "Audio quality (kbps)",
        "audio.noise_suppression": "Noise suppression",
        "audio.echo_cancellation": "Echo cancellation",
        # camera
        "camera.enable": "Enable webcam overlay",
        "camera.device": "Device",
        "camera.position": "Position",
        "camera.width": "Width",
        "camera.height": "Height",
        "camera.radius": "Border radius",
        "camera.shadow": "Shadow",
        "camera.opacity": "Opacity",
        # logo
        "logo.enable": "Enable logo overlay",
        "logo.path": "Path",
        "logo.position": "Position",
        "logo.width": "Width",
        "logo.height": "Height",
        "logo.opacity": "Opacity",
        # output
        "output.folder": "Save folder",
        "output.template": "Filename template",
        "output.template_hint":
            "Available placeholders: {Y} year, {M} month, {D} day, "
            "{h} hour, {m} minute, {s} second.",
        # hotkeys
        "hotkeys.start": "Start",
        "hotkeys.pause": "Pause",
        "hotkeys.resume": "Resume",
        "hotkeys.stop": "Stop",
        "hotkeys.screenshot": "Screenshot",
        "hotkeys.hint":
            "Use modifiers + key, e.g. <b>Ctrl+Shift+F9</b>, <b>Alt+R</b>. ",
        "hotkeys.hint_linux":
            "Requires X11 — Wayland may restrict global hotkeys.",
        "hotkeys.hint_windows":
            "Windows: global hotkeys work everywhere.",
        # dubbing
        "dub.title": "Real-time dubber",
        "dub.enable": "Enable live dubbing (EN/RU → UZ)",
        "dub.source_langs": "Source languages",
        "dub.voice": "Uzbek voice",
        "dub.whisper": "Whisper ASR (speech-to-text)",
        "dub.model_size": "Model size",
        "dub.device": "Device",
        "dub.compute": "Compute type",
        "dub.chunk": "Audio chunk",
        "dub.translator": "Translator",
        "dub.service": "Service",
        "dub.yandex_key": "Yandex API key",
        "dub.yandex_folder": "Yandex folder ID",
        "dub.yandex_placeholder": "Optional — for best Uzbek quality",
        "dub.hint":
            "When enabled, Visio Eye feeds system audio into Whisper, "
            "translates EN/RU text to Uzbek and overlays Edge TTS audio "
            "into the recording.  The original soundtrack is "
            "<b>removed</b> from the saved file.  Internet and the "
            "Whisper model are required.",
        # streaming
        "stream.enable": "Enable live streaming (RTMP / RTMPS to all enabled targets)",
        "stream.encoder": "Encoder",
        "stream.bitrate": "Video bitrate",
        "stream.keyframe": "Keyframe interval",
        "stream.audio_kbps": "Audio kbps",
        "stream.targets": "Targets",
        "stream.target.enable": "Enable",
        "stream.target.platform": "Platform",
        "stream.target.base_url": "Base URL",
        "stream.target.key": "Stream key",
        "stream.target.key_placeholder": "Stream key (paste from platform)",
        "stream.target.url_placeholder": "rtmp://... (auto-filled per platform)",
        "stream.hint":
            "When recording starts Visio Eye relays the screen to each "
            "enabled platform in real-time via RTMP.  The <b>stream key</b> "
            "for each platform is taken from its 'Go Live' page.",
        # html overlay
        "html.enable": "Show HTML overlay on screen (visible in recording + stream)",
        "html.position_size": "Position and size",
        "html.x": "X",
        "html.y": "Y",
        "html.width": "Width",
        "html.height": "Height",
        "html.behaviour": "Behaviour",
        "html.click_through": "Click-through (mouse passes to apps behind)",
        "html.transparent_bg": "Transparent background",
        "html.code": "HTML / CSS / JavaScript code",
        "html.hint":
            "Visio Eye uses Chromium-based WebEngine — full HTML5 + CSS3 + "
            "JavaScript is supported. Leave the body background transparent "
            "to overlay on top of any application.",
    },

    # ============================================================
    # Uzbek
    # ============================================================
    "uz": {
        # main
        "app.subtitle": "Ekran yozuvchisi",
        "main.studio": "Yozish studiyasi",
        "main.studio_tag": "Professional ekran yozuvi",
        "main.btn.record": "● Yozish",
        "main.btn.pause": "⏸  To'xtatish",
        "main.btn.resume": "▶  Davom etish",
        "main.btn.stop": "■ Tugatish",
        "main.btn.screenshot": "📷 Skrinshot",
        "main.btn.settings": "⚙ Sozlamalar",
        "main.btn.author": "👤 MUALLIF",
        "main.card.mode": "REJIM",
        "main.card.output": "CHIQUVCHI FAYL",
        "main.card.overlays": "USTKI QATLAMLAR",
        "main.card.camera": "Kamera",
        "main.card.logo": "Logo",
        "main.card.change": "O'zgartirish…",
        "main.card.open": "Ochish",
        "main.mode.fullscreen": "To'liq ekran",
        "main.mode.window": "Faol oyna",
        "main.mode.region": "Soha…",
        "main.metric.cpu": "CPU",
        "main.metric.mem": "Xotira",
        "main.metric.disk": "Disk",
        "main.metric.fps": "FPS",
        "main.metric.status": "Holat",
        "main.status.idle": "Tayyor",
        "main.status.ready": "Tayyor",
        "main.status.recording": "Yozyapti",
        "main.status.paused": "To'xtatildi",
        "main.log.recording_to": "Yozish → {path}",
        "main.log.recording_started": "Yozish boshlandi: {backend} backend",
        "main.log.resumed": "Davom etmoqda",
        "main.log.paused": "To'xtatildi",
        "main.log.dubber_on": "Dublyator yoqildi (Whisper modeli yuklanmoqda…)",
        "main.log.dubber_off": "Dublyator to'xtatildi",
        "main.log.dubber_fail": "Dublyator yoqilmadi: {err}",
        "main.dialog.recording_failed": "Yozish muvaffaqiyatsiz",
        "main.dialog.dubbing_failed": "Dublyator yoqilmadi",
        "main.dialog.ffmpeg_missing": "FFmpeg topilmadi",
        "main.dialog.ffmpeg_install":
            "FFmpeg o'rnatilmagan.\n\nO'rnatish:\n"
            "    sudo apt install ffmpeg",
        "main.wayland_tips":
            "\n\nWayland uchun maslahatlar:\n"
            "  • Portal dialog chiqqanida ekran ulashish ruxsatini\n"
            "    BERGAN bo'lishingiz kerak.\n"
            "  • Kerakli paketlarni o'rnating:\n"
            "      sudo apt install gstreamer1.0-tools \\\n"
            "        gstreamer1.0-plugins-good \\\n"
            "        gstreamer1.0-plugins-bad \\\n"
            "        gstreamer1.0-pipewire python3-dbus python3-gi",
        "region.hint": "Soha tanlash uchun sichqoncha bilan torting · ESC bekor qiladi",
        # settings
        "settings.title": "Sozlamalar",
        "settings.window_title": "Visio Eye — Sozlamalar",
        "settings.tab.general": "Umumiy",
        "settings.tab.video": "Video",
        "settings.tab.audio": "Audio",
        "settings.tab.camera": "Kamera",
        "settings.tab.logo": "Logo / Ustki qatlam",
        "settings.tab.output": "Chiquvchi fayl",
        "settings.tab.hotkeys": "Tugmalar",
        "settings.tab.dubbing": "Dublyator",
        "settings.tab.streaming": "Strim",
        "settings.tab.html": "HTML Overlay",
        "settings.btn.cancel": "Bekor qilish",
        "settings.btn.save": "Saqlash",
        "settings.btn.author": "MUALLIF",
        "settings.btn.remove": "O'chirish",
        "settings.btn.add_target": "+ Yangi maqsad qo'shish",
        "settings.btn.browse": "Tanlash…",
        "settings.btn.pick_logo": "Tanlash…",
        "general.language": "Til",
        "general.theme": "Mavzu",
        "general.start_with_system": "Tizim bilan birga ishga tushsin",
        "general.lang_changed_title": "Qayta ishga tushirish kerak",
        "general.lang_changed_body":
            "Til o'zgarishi Visio Eye qayta ishga tushganidan keyin "
            "to'liq qo'llaniladi.",
        "video.fps": "Kadr tezligi",
        "video.resolution": "O'lcham",
        "video.codec": "Kodek",
        "video.container": "Format",
        "video.bitrate": "Bitrate",
        "video.encoder": "Enkoder",
        "audio.source": "Audio manba",
        "audio.src.mic": "Mikrofon",
        "audio.src.desk": "Tizim",
        "audio.src.both": "Ikkalasi",
        "audio.src.none": "Yo'q",
        "audio.devices": "Qurilmalar",
        "audio.mic": "Mikrofon",
        "audio.desk": "Tizim / Loopback",
        "audio.vol_quality": "Ovoz va sifat",
        "audio.mic_volume": "Mikrofon ovozi",
        "audio.desk_volume": "Tizim ovozi",
        "audio.quality_kbps": "Audio sifat (kbps)",
        "audio.noise_suppression": "Shovqinni bostirish",
        "audio.echo_cancellation": "Aks-sado yo'qotish",
        "camera.enable": "Webkamera qatlamini yoqish",
        "camera.device": "Qurilma",
        "camera.position": "Joylashuv",
        "camera.width": "Eni",
        "camera.height": "Bo'yi",
        "camera.radius": "Burchak radiusi",
        "camera.shadow": "Soya",
        "camera.opacity": "Shaffoflik",
        "logo.enable": "Logo qatlamini yoqish",
        "logo.path": "Yo'l",
        "logo.position": "Joylashuv",
        "logo.width": "Eni",
        "logo.height": "Bo'yi",
        "logo.opacity": "Shaffoflik",
        "output.folder": "Saqlash papkasi",
        "output.template": "Fayl nomi shabloni",
        "output.template_hint":
            "Belgilar: {Y} yil, {M} oy, {D} kun, {h} soat, "
            "{m} daqiqa, {s} soniya.",
        "hotkeys.start": "Boshlash",
        "hotkeys.pause": "To'xtatish",
        "hotkeys.resume": "Davom etish",
        "hotkeys.stop": "Tugatish",
        "hotkeys.screenshot": "Skrinshot",
        "hotkeys.hint":
            "Modifikator + tugma, masalan <b>Ctrl+Shift+F9</b>, "
            "<b>Alt+R</b>. ",
        "hotkeys.hint_linux":
            "X11 talab qiladi — Wayland'da global tugmalar cheklangan.",
        "hotkeys.hint_windows":
            "Windows: global tugmalar hamma joyda ishlaydi.",
        "dub.title": "Real-vaqt dublyator",
        "dub.enable": "Jonli dublyajni yoqish (EN/RU → UZ)",
        "dub.source_langs": "Manba tillari",
        "dub.voice": "O'zbekcha ovoz",
        "dub.whisper": "Whisper ASR (nutqdan matnga)",
        "dub.model_size": "Model hajmi",
        "dub.device": "Qurilma",
        "dub.compute": "Hisoblash turi",
        "dub.chunk": "Audio bo'lak",
        "dub.translator": "Tarjimon",
        "dub.service": "Xizmat",
        "dub.yandex_key": "Yandex API kalit",
        "dub.yandex_folder": "Yandex folder ID",
        "dub.yandex_placeholder": "Ixtiyoriy — eng yaxshi o'zbek sifati uchun",
        "dub.hint":
            "Dublyator yoqilganda Visio Eye tizim audio'sini Whisper'ga "
            "uzatadi, EN/RU matnni o'zbekchaga tarjima qiladi va Edge TTS "
            "ovozini videoga yozadi. Original audio yozilgan faylda "
            "<b>eshitilmaydi</b>. Internet va Whisper modeli kerak.",
        "stream.enable": "Jonli strimni yoqish (RTMP / RTMPS hamma maqsadlarga)",
        "stream.encoder": "Enkoder",
        "stream.bitrate": "Video bitrate",
        "stream.keyframe": "Asosiy kadr oralig'i",
        "stream.audio_kbps": "Audio kbps",
        "stream.targets": "Maqsadlar",
        "stream.target.enable": "Yoqish",
        "stream.target.platform": "Platforma",
        "stream.target.base_url": "Base URL",
        "stream.target.key": "Strim kaliti",
        "stream.target.key_placeholder": "Strim kaliti (platformadan oling)",
        "stream.target.url_placeholder": "rtmp://... (platforma bo'yicha avto-to'ladi)",
        "stream.hint":
            "Yozish boshlanganda Visio Eye ekranni har bir yoqilgan "
            "platformaga real-vaqt RTMP orqali jonli efirga uzatadi. "
            "<b>Strim kaliti</b> har bir platforma 'Go Live' sahifasidan olinadi.",
        "html.enable": "Ekranda HTML overlay ko'rsatish (yozuv + strimda ko'rinadi)",
        "html.position_size": "Joylashuv va o'lcham",
        "html.x": "X",
        "html.y": "Y",
        "html.width": "Eni",
        "html.height": "Bo'yi",
        "html.behaviour": "Xulq-atvor",
        "html.click_through": "Click-through (sichqoncha orqasidagi ilovalarga o'tadi)",
        "html.transparent_bg": "Shaffof fon",
        "html.code": "HTML / CSS / JavaScript kodi",
        "html.hint":
            "Visio Eye Chromium asosida WebEngine ishlatadi — to'liq HTML5 + "
            "CSS3 + JavaScript qo'llab-quvvatlanadi. Body fonini shaffof "
            "qoldirsangiz overlay har qanday ilova ustida ko'rinadi.",
    },

    # ============================================================
    # Russian
    # ============================================================
    "ru": {
        "app.subtitle": "Запись экрана",
        "main.studio": "Студия записи",
        "main.studio_tag": "Профессиональная запись",
        "main.btn.record": "● Запись",
        "main.btn.pause": "⏸  Пауза",
        "main.btn.resume": "▶  Продолжить",
        "main.btn.stop": "■ Стоп",
        "main.btn.screenshot": "📷 Скриншот",
        "main.btn.settings": "⚙ Настройки",
        "main.btn.author": "👤 АВТОР",
        "main.card.mode": "РЕЖИМ",
        "main.card.output": "ФАЙЛ",
        "main.card.overlays": "ОВЕРЛЕИ",
        "main.card.camera": "Камера",
        "main.card.logo": "Логотип",
        "main.card.change": "Изменить…",
        "main.card.open": "Открыть",
        "main.mode.fullscreen": "Весь экран",
        "main.mode.window": "Активное окно",
        "main.mode.region": "Область…",
        "main.metric.cpu": "ЦП",
        "main.metric.mem": "ОЗУ",
        "main.metric.disk": "Диск",
        "main.metric.fps": "FPS",
        "main.metric.status": "Статус",
        "main.status.idle": "Готов",
        "main.status.ready": "Готов",
        "main.status.recording": "Запись",
        "main.status.paused": "Пауза",
        "main.log.recording_to": "Запись → {path}",
        "main.log.recording_started": "Запись запущена ({backend})",
        "main.log.resumed": "Продолжено",
        "main.log.paused": "Поставлено на паузу",
        "main.log.dubber_on": "Дубляж включён (загружается модель Whisper…)",
        "main.log.dubber_off": "Дубляж остановлен",
        "main.log.dubber_fail": "Не удалось запустить дубляж: {err}",
        "main.dialog.recording_failed": "Ошибка записи",
        "main.dialog.dubbing_failed": "Не удалось запустить дубляж",
        "main.dialog.ffmpeg_missing": "FFmpeg не найден",
        "main.dialog.ffmpeg_install":
            "FFmpeg не установлен.\n\nУстановите его командой:\n"
            "    sudo apt install ffmpeg",
        "main.wayland_tips":
            "\n\nСоветы для Wayland:\n"
            "  • Убедитесь, что вы РАЗРЕШИЛИ доступ к экрану в окне\n"
            "    портала.\n"
            "  • Установите недостающие пакеты:\n"
            "      sudo apt install gstreamer1.0-tools \\\n"
            "        gstreamer1.0-plugins-good \\\n"
            "        gstreamer1.0-plugins-bad \\\n"
            "        gstreamer1.0-pipewire python3-dbus python3-gi",
        "region.hint": "Выделите область мышью · ESC чтобы отменить",
        "settings.title": "Настройки",
        "settings.window_title": "Visio Eye — Настройки",
        "settings.tab.general": "Общие",
        "settings.tab.video": "Видео",
        "settings.tab.audio": "Аудио",
        "settings.tab.camera": "Камера",
        "settings.tab.logo": "Логотип / Оверлей",
        "settings.tab.output": "Файл",
        "settings.tab.hotkeys": "Горячие клавиши",
        "settings.tab.dubbing": "Дубляж",
        "settings.tab.streaming": "Стрим",
        "settings.tab.html": "HTML Оверлей",
        "settings.btn.cancel": "Отмена",
        "settings.btn.save": "Сохранить",
        "settings.btn.author": "АВТОР",
        "settings.btn.remove": "Удалить",
        "settings.btn.add_target": "+ Добавить цель",
        "settings.btn.browse": "Обзор…",
        "settings.btn.pick_logo": "Выбрать…",
        "general.language": "Язык",
        "general.theme": "Тема",
        "general.start_with_system": "Запускать вместе с системой",
        "general.lang_changed_title": "Требуется перезапуск",
        "general.lang_changed_body":
            "Смена языка вступит в силу после перезапуска Visio Eye.",
        "video.fps": "FPS",
        "video.resolution": "Разрешение",
        "video.codec": "Кодек",
        "video.container": "Контейнер",
        "video.bitrate": "Битрейт",
        "video.encoder": "Энкодер",
        "audio.source": "Источник звука",
        "audio.src.mic": "Микрофон",
        "audio.src.desk": "Система",
        "audio.src.both": "Оба",
        "audio.src.none": "Нет",
        "audio.devices": "Устройства",
        "audio.mic": "Микрофон",
        "audio.desk": "Рабочий стол / Loopback",
        "audio.vol_quality": "Громкость и качество",
        "audio.mic_volume": "Громкость микрофона",
        "audio.desk_volume": "Громкость системы",
        "audio.quality_kbps": "Качество звука (кбит/с)",
        "audio.noise_suppression": "Шумоподавление",
        "audio.echo_cancellation": "Эхоподавление",
        "camera.enable": "Включить оверлей вебкамеры",
        "camera.device": "Устройство",
        "camera.position": "Позиция",
        "camera.width": "Ширина",
        "camera.height": "Высота",
        "camera.radius": "Радиус скругления",
        "camera.shadow": "Тень",
        "camera.opacity": "Прозрачность",
        "logo.enable": "Включить оверлей логотипа",
        "logo.path": "Путь",
        "logo.position": "Позиция",
        "logo.width": "Ширина",
        "logo.height": "Высота",
        "logo.opacity": "Прозрачность",
        "output.folder": "Папка сохранения",
        "output.template": "Шаблон имени файла",
        "output.template_hint":
            "Подстановки: {Y} год, {M} месяц, {D} день, {h} час, "
            "{m} минута, {s} секунда.",
        "hotkeys.start": "Старт",
        "hotkeys.pause": "Пауза",
        "hotkeys.resume": "Продолжить",
        "hotkeys.stop": "Стоп",
        "hotkeys.screenshot": "Скриншот",
        "hotkeys.hint":
            "Модификаторы + клавиша, например <b>Ctrl+Shift+F9</b>, "
            "<b>Alt+R</b>. ",
        "hotkeys.hint_linux":
            "Требует X11 — на Wayland глобальные клавиши ограничены.",
        "hotkeys.hint_windows":
            "Windows: глобальные клавиши работают всегда.",
        "dub.title": "Дубляж в реальном времени",
        "dub.enable": "Включить дубляж (EN/RU → UZ)",
        "dub.source_langs": "Языки источника",
        "dub.voice": "Узбекский голос",
        "dub.whisper": "Whisper ASR (речь → текст)",
        "dub.model_size": "Размер модели",
        "dub.device": "Устройство",
        "dub.compute": "Тип вычислений",
        "dub.chunk": "Аудио-кусок",
        "dub.translator": "Переводчик",
        "dub.service": "Сервис",
        "dub.yandex_key": "Ключ API Яндекс",
        "dub.yandex_folder": "Folder ID Яндекс",
        "dub.yandex_placeholder": "Необязательно — для лучшего узбекского",
        "dub.hint":
            "Когда включено, Visio Eye отправляет системный звук в Whisper, "
            "переводит EN/RU в узбекский и накладывает голос Edge TTS на "
            "запись.  Оригинальная дорожка в сохранённом файле "
            "<b>удаляется</b>.  Требуется интернет и модель Whisper.",
        "stream.enable": "Включить трансляцию (RTMP/RTMPS на все цели)",
        "stream.encoder": "Энкодер",
        "stream.bitrate": "Видео битрейт",
        "stream.keyframe": "Интервал ключевых кадров",
        "stream.audio_kbps": "Аудио кбит/с",
        "stream.targets": "Цели",
        "stream.target.enable": "Включить",
        "stream.target.platform": "Платформа",
        "stream.target.base_url": "Base URL",
        "stream.target.key": "Stream key",
        "stream.target.key_placeholder": "Stream key (скопируйте с платформы)",
        "stream.target.url_placeholder": "rtmp://... (заполняется автоматически)",
        "stream.hint":
            "Когда запись стартует, Visio Eye параллельно ретранслирует "
            "экран на каждую включённую платформу через RTMP. "
            "<b>Stream key</b> берётся со страницы 'Go Live' платформы.",
        "html.enable": "Показывать HTML-оверлей (виден в записи и трансляции)",
        "html.position_size": "Позиция и размер",
        "html.x": "X",
        "html.y": "Y",
        "html.width": "Ширина",
        "html.height": "Высота",
        "html.behaviour": "Поведение",
        "html.click_through": "Прозрачно для мыши (клики уходят под)",
        "html.transparent_bg": "Прозрачный фон",
        "html.code": "Код HTML / CSS / JavaScript",
        "html.hint":
            "Visio Eye использует Chromium WebEngine — поддерживаются HTML5 + "
            "CSS3 + JavaScript полностью. Оставьте фон body прозрачным, чтобы "
            "оверлей лежал поверх любого приложения.",
    },
}
