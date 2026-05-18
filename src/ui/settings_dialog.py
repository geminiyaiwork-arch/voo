"""Settings dialog with tabs: General / Video / Audio / Camera / Logo / Output / Hotkeys / Author."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog, QTabWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QComboBox, QSpinBox, QCheckBox, QSlider, QPushButton, QLineEdit,
    QFileDialog, QWidget, QRadioButton, QButtonGroup, QKeySequenceEdit,
    QSizePolicy, QPlainTextEdit, QScrollArea,
)

from streaming import PLATFORM_PRESETS

from i18n import tr
from settings import SettingsManager
from utils.system_info import SystemInfo
from .author_dialog import AuthorDialog


class SettingsDialog(QDialog):
    settings_changed = pyqtSignal()

    def __init__(self, settings: SettingsManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("settings.window_title"))
        self.setMinimumSize(720, 600)
        self.resize(960, 720)
        # Give the dialog real window decorations so users can maximise
        # to full screen, resize freely, and minimise as needed.
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowMinimizeButtonHint
        )
        self.setSizeGripEnabled(True)
        self._settings = settings

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        title = QLabel(tr("settings.title"))
        title.setObjectName("title")
        root.addWidget(title)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_general(), tr("settings.tab.general"))
        self.tabs.addTab(self._build_video(), tr("settings.tab.video"))
        self.tabs.addTab(self._build_audio(), tr("settings.tab.audio"))
        self.tabs.addTab(self._build_camera(), tr("settings.tab.camera"))
        self.tabs.addTab(self._build_logo(), tr("settings.tab.logo"))
        self.tabs.addTab(self._build_output(), tr("settings.tab.output"))
        self.tabs.addTab(self._build_hotkeys(), tr("settings.tab.hotkeys"))
        self.tabs.addTab(self._build_dubbing(), tr("settings.tab.dubbing"))
        self.tabs.addTab(self._build_streaming(), tr("settings.tab.streaming"))
        self.tabs.addTab(self._build_html(), tr("settings.tab.html"))
        root.addWidget(self.tabs, 1)

        bottom = QHBoxLayout()
        author_btn = QPushButton(tr("settings.btn.author"))
        author_btn.setObjectName("ghost")
        author_btn.clicked.connect(self._open_author)
        bottom.addWidget(author_btn)
        bottom.addStretch(1)

        cancel_btn = QPushButton(tr("settings.btn.cancel"))
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton(tr("settings.btn.save"))
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save)
        bottom.addWidget(cancel_btn)
        bottom.addWidget(save_btn)
        root.addLayout(bottom)

    # ---------- General ----------
    def _build_general(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        g = self._settings.get("general")
        from i18n import supported_languages, current_language
        self.cmb_lang = QComboBox()
        for code, label in supported_languages():
            self.cmb_lang.addItem(label, code)
        self._initial_language = g.get("language", current_language())
        for i in range(self.cmb_lang.count()):
            if self.cmb_lang.itemData(i) == self._initial_language:
                self.cmb_lang.setCurrentIndex(i)
                break

        self.cmb_theme = QComboBox()
        self.cmb_theme.addItems(["light", "dark"])
        self.cmb_theme.setCurrentText(g.get("theme", "light"))

        self.chk_startup = QCheckBox(tr("general.start_with_system"))
        self.chk_startup.setChecked(bool(g.get("start_with_system", False)))

        form.addRow(tr("general.language"), self.cmb_lang)
        form.addRow(tr("general.theme"), self.cmb_theme)
        form.addRow("", self.chk_startup)
        return w

    # ---------- Video ----------
    def _build_video(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        v = self._settings.get("video")

        self.cmb_fps = QComboBox()
        self.cmb_fps.addItems(["24", "30", "60"])
        self.cmb_fps.setCurrentText(str(v.get("fps", 30)))

        self.cmb_res = QComboBox()
        self.cmb_res.addItems(["480p", "720p", "1080p", "2K", "4K"])
        self.cmb_res.setCurrentText(v.get("resolution", "1080p"))

        self.cmb_codec = QComboBox()
        self.cmb_codec.addItems(["H264", "H265"])
        self.cmb_codec.setCurrentText(v.get("codec", "H264"))

        self.cmb_format = QComboBox()
        self.cmb_format.addItems(["mp4", "mkv", "mov"])
        self.cmb_format.setCurrentText(v.get("format", "mp4"))

        self.cmb_bitrate = QComboBox()
        self.cmb_bitrate.addItems(["Auto", "Low", "Medium", "High", "Ultra"])
        self.cmb_bitrate.setCurrentText(v.get("bitrate", "Auto"))

        self.cmb_encoder = QComboBox()
        self.cmb_encoder.addItems(["CPU", "GPU"])
        self.cmb_encoder.setCurrentText(v.get("encoder", "CPU"))

        form.addRow(tr("video.fps"), self.cmb_fps)
        form.addRow(tr("video.resolution"), self.cmb_res)
        form.addRow(tr("video.codec"), self.cmb_codec)
        form.addRow(tr("video.container"), self.cmb_format)
        form.addRow(tr("video.bitrate"), self.cmb_bitrate)
        form.addRow(tr("video.encoder"), self.cmb_encoder)
        return w

    # ---------- Audio ----------
    def _build_audio(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        a = self._settings.get("audio")

        src_box = QGroupBox(tr("audio.source"))
        src_layout = QHBoxLayout(src_box)
        self.audio_group = QButtonGroup(self)
        self.rb_mic = QRadioButton(tr("audio.src.mic"))
        self.rb_desk = QRadioButton(tr("audio.src.desk"))
        self.rb_both = QRadioButton(tr("audio.src.both"))
        self.rb_none = QRadioButton(tr("audio.src.none"))
        for i, rb in enumerate((self.rb_mic, self.rb_desk, self.rb_both, self.rb_none)):
            self.audio_group.addButton(rb, i)
            src_layout.addWidget(rb)
        mapping = {"mic": self.rb_mic, "desktop": self.rb_desk,
                   "both": self.rb_both, "none": self.rb_none}
        mapping.get(a.get("source", "both"), self.rb_both).setChecked(True)
        layout.addWidget(src_box)

        dev_box = QGroupBox(tr("audio.devices"))
        dev_form = QFormLayout(dev_box)
        sources = SystemInfo.list_pulse_sources()
        self.cmb_mic = QComboBox()
        self.cmb_desk = QComboBox()
        for name, desc in sources:
            self.cmb_mic.addItem(desc, name)
            self.cmb_desk.addItem(desc, name)
        self._select_combo_data(self.cmb_mic, a.get("mic_device", "default"))
        self._select_combo_data(self.cmb_desk, a.get("desktop_device", "default"))
        dev_form.addRow(tr("audio.mic"), self.cmb_mic)
        dev_form.addRow(tr("audio.desk"), self.cmb_desk)
        layout.addWidget(dev_box)

        vol_box = QGroupBox(tr("audio.vol_quality"))
        vol_form = QFormLayout(vol_box)
        self.sld_mic = QSlider(Qt.Orientation.Horizontal)
        self.sld_mic.setRange(0, 100)
        self.sld_mic.setValue(int(a.get("mic_volume", 80)))
        self.sld_desk = QSlider(Qt.Orientation.Horizontal)
        self.sld_desk.setRange(0, 100)
        self.sld_desk.setValue(int(a.get("desktop_volume", 80)))
        self.cmb_aq = QComboBox()
        self.cmb_aq.addItems(["128", "192", "256", "320"])
        self.cmb_aq.setCurrentText(str(a.get("quality_kbps", 192)))
        self.chk_ns = QCheckBox(tr("audio.noise_suppression"))
        self.chk_ns.setChecked(bool(a.get("noise_suppression", True)))
        self.chk_ec = QCheckBox(tr("audio.echo_cancellation"))
        self.chk_ec.setChecked(bool(a.get("echo_cancellation", True)))

        vol_form.addRow(tr("audio.mic_volume"), self._labeled_slider(self.sld_mic))
        vol_form.addRow(tr("audio.desk_volume"), self._labeled_slider(self.sld_desk))
        vol_form.addRow(tr("audio.quality_kbps"), self.cmb_aq)
        vol_form.addRow("", self.chk_ns)
        vol_form.addRow("", self.chk_ec)
        layout.addWidget(vol_box)
        layout.addStretch(1)
        return w

    # ---------- Camera ----------
    def _build_camera(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        c = self._settings.get("camera")

        self.chk_cam = QCheckBox(tr("camera.enable"))
        self.chk_cam.setChecked(bool(c.get("enabled", False)))

        self.cmb_cam_dev = QComboBox()
        cam_devs = SystemInfo.list_camera_devices()
        if not cam_devs:
            import sys as _sys
            cam_devs = [("", "(no camera detected)")] if _sys.platform.startswith("win") \
                else [("/dev/video0", "/dev/video0")]
        for dev_id, dev_label in cam_devs:
            self.cmb_cam_dev.addItem(dev_label, dev_id)
        self._select_combo_data(self.cmb_cam_dev, c.get("device", cam_devs[0][0]))

        self.cmb_cam_pos = QComboBox()
        self.cmb_cam_pos.addItems(
            ["top_left", "top_right", "bottom_left", "bottom_right", "custom"]
        )
        self.cmb_cam_pos.setCurrentText(c.get("position", "bottom_right"))

        self.sp_cam_w = self._spin(100, 1280, int(c.get("width", 240)))
        self.sp_cam_h = self._spin(100, 1280, int(c.get("height", 180)))
        self.sp_cam_radius = self._spin(0, 80, int(c.get("border_radius", 16)))
        self.sld_cam_opacity = QSlider(Qt.Orientation.Horizontal)
        self.sld_cam_opacity.setRange(0, 100)
        self.sld_cam_opacity.setValue(int(c.get("opacity", 100)))
        self.chk_cam_shadow = QCheckBox(tr("camera.shadow"))
        self.chk_cam_shadow.setChecked(bool(c.get("shadow", True)))

        form.addRow("", self.chk_cam)
        form.addRow(tr("camera.device"), self.cmb_cam_dev)
        form.addRow(tr("camera.position"), self.cmb_cam_pos)
        form.addRow(tr("camera.width"), self.sp_cam_w)
        form.addRow(tr("camera.height"), self.sp_cam_h)
        form.addRow(tr("camera.radius"), self.sp_cam_radius)
        form.addRow(tr("camera.opacity"), self._labeled_slider(self.sld_cam_opacity))
        form.addRow("", self.chk_cam_shadow)
        return w

    # ---------- Logo ----------
    def _build_logo(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        l_ = self._settings.get("logo")

        self.chk_logo = QCheckBox(tr("logo.enable"))
        self.chk_logo.setChecked(bool(l_.get("enabled", False)))

        path_row = QHBoxLayout()
        self.le_logo = QLineEdit(l_.get("path", ""))
        browse = QPushButton(tr("settings.btn.browse"))
        browse.clicked.connect(self._pick_logo)
        path_row.addWidget(self.le_logo, 1)
        path_row.addWidget(browse)
        path_w = QWidget()
        path_w.setLayout(path_row)

        self.cmb_logo_pos = QComboBox()
        self.cmb_logo_pos.addItems(
            ["top_left", "top_right", "bottom_left", "bottom_right", "custom"]
        )
        self.cmb_logo_pos.setCurrentText(l_.get("position", "top_right"))

        self.sp_logo_w = self._spin(20, 1280, int(l_.get("width", 120)))
        self.sp_logo_h = self._spin(20, 1280, int(l_.get("height", 120)))
        self.sld_logo_opacity = QSlider(Qt.Orientation.Horizontal)
        self.sld_logo_opacity.setRange(0, 100)
        self.sld_logo_opacity.setValue(int(l_.get("opacity", 90)))

        form.addRow("", self.chk_logo)
        form.addRow(tr("logo.path") + " (PNG/SVG/JPG)", path_w)
        form.addRow(tr("logo.position"), self.cmb_logo_pos)
        form.addRow(tr("logo.width"), self.sp_logo_w)
        form.addRow(tr("logo.height"), self.sp_logo_h)
        form.addRow(tr("logo.opacity"), self._labeled_slider(self.sld_logo_opacity))
        return w

    # ---------- Output ----------
    def _build_output(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        o = self._settings.get("output")

        path_row = QHBoxLayout()
        self.le_folder = QLineEdit(o.get("folder", str(Path.home() / "Videos" / "VisioEye")))
        browse = QPushButton(tr("settings.btn.browse"))
        browse.clicked.connect(self._pick_folder)
        path_row.addWidget(self.le_folder, 1)
        path_row.addWidget(browse)
        pw = QWidget()
        pw.setLayout(path_row)

        self.le_template = QLineEdit(o.get(
            "filename_template", "record_{Y}_{M}_{D}_{h}_{m}_{s}"
        ))

        preset_row = QHBoxLayout()
        for name, path in (
            ("Desktop", str(Path.home() / "Desktop")),
            ("Downloads", str(Path.home() / "Downloads")),
            ("Videos", str(Path.home() / "Videos" / "VisioEye")),
        ):
            btn = QPushButton(name)
            btn.setObjectName("ghost")
            btn.clicked.connect(lambda _=False, p=path: self.le_folder.setText(p))
            preset_row.addWidget(btn)
        preset_row.addStretch(1)
        pr = QWidget()
        pr.setLayout(preset_row)

        form.addRow(tr("output.folder"), pw)
        form.addRow("", pr)
        form.addRow(tr("output.template"), self.le_template)

        hint = QLabel(tr("output.template_hint"))
        hint.setStyleSheet("color:#94a3b8;font-size:11px;")
        hint.setWordWrap(True)
        form.addRow("", hint)
        return w

    # ---------- Hotkeys ----------
    def _build_hotkeys(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        h = self._settings.get("hotkeys")
        self.hk_edits: dict[str, QLineEdit] = {}
        for action, label in (
            ("start", tr("hotkeys.start")),
            ("pause", tr("hotkeys.pause")),
            ("resume", tr("hotkeys.resume")),
            ("stop", tr("hotkeys.stop")),
            ("screenshot", tr("hotkeys.screenshot")),
        ):
            le = QLineEdit(h.get(action, ""))
            le.setPlaceholderText("e.g. Ctrl+Shift+F9")
            le.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.hk_edits[action] = le
            form.addRow(label, le)
        import sys as _sys
        platform_hint = (tr("hotkeys.hint_windows")
                         if _sys.platform.startswith("win")
                         else tr("hotkeys.hint_linux"))
        hint = QLabel(tr("hotkeys.hint") + platform_hint)
        hint.setStyleSheet("color:#94a3b8;font-size:11px;")
        hint.setWordWrap(True)
        form.addRow("", hint)
        return w

    # ---------- Dubbing ----------
    def _build_dubbing(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        d = self._settings.get("dubbing")

        top_box = QGroupBox(tr("dub.title"))
        top_form = QFormLayout(top_box)

        self.chk_dub = QCheckBox(tr("dub.enable"))
        self.chk_dub.setChecked(bool(d.get("enabled", False)))
        top_form.addRow("", self.chk_dub)

        # source languages
        src_wrap = QHBoxLayout()
        self.chk_src_en = QCheckBox("English")
        self.chk_src_ru = QCheckBox("Русский")
        langs = list(d.get("source_languages", ["en", "ru"]))
        self.chk_src_en.setChecked("en" in langs)
        self.chk_src_ru.setChecked("ru" in langs)
        src_wrap.addWidget(self.chk_src_en)
        src_wrap.addWidget(self.chk_src_ru)
        src_wrap.addStretch(1)
        src_w = QWidget(); src_w.setLayout(src_wrap)
        top_form.addRow(tr("dub.source_langs"), src_w)

        self.cmb_dub_voice = QComboBox()
        from dubbing.tts_edge import EdgeTTS
        for vid, vlabel in EdgeTTS.list_uz_voices():
            self.cmb_dub_voice.addItem(vlabel, vid)
        self._select_combo_data(self.cmb_dub_voice,
                                 d.get("voice", "uz-UZ-MadinaNeural"))
        top_form.addRow(tr("dub.voice"), self.cmb_dub_voice)

        layout.addWidget(top_box)

        # Whisper section
        asr_box = QGroupBox(tr("dub.whisper"))
        asr_form = QFormLayout(asr_box)
        self.cmb_asr_model = QComboBox()
        self.cmb_asr_model.addItems(["base", "small", "medium", "large-v3"])
        self.cmb_asr_model.setCurrentText(d.get("asr_model", "large-v3"))
        asr_form.addRow(tr("dub.model_size"), self.cmb_asr_model)

        self.cmb_asr_device = QComboBox()
        self.cmb_asr_device.addItems(["cuda", "cpu"])
        self.cmb_asr_device.setCurrentText(d.get("asr_device", "cuda"))
        asr_form.addRow(tr("dub.device"), self.cmb_asr_device)

        self.cmb_asr_compute = QComboBox()
        self.cmb_asr_compute.addItems(
            ["int8_float16", "int8", "float16", "float32"]
        )
        self.cmb_asr_compute.setCurrentText(d.get("asr_compute", "int8_float16"))
        asr_form.addRow(tr("dub.compute"), self.cmb_asr_compute)

        self.sp_chunk = QSpinBox()
        self.sp_chunk.setRange(2, 8)
        self.sp_chunk.setValue(int(d.get("chunk_seconds", 3)))
        self.sp_chunk.setSuffix(" sec")
        asr_form.addRow(tr("dub.chunk"), self.sp_chunk)
        layout.addWidget(asr_box)

        # Translator section
        trans_box = QGroupBox(tr("dub.translator"))
        trans_form = QFormLayout(trans_box)
        self.cmb_translator = QComboBox()
        self.cmb_translator.addItems(["auto", "yandex", "google"])
        self.cmb_translator.setCurrentText(d.get("translator", "auto"))
        trans_form.addRow(tr("dub.service"), self.cmb_translator)

        self.le_yandex_key = QLineEdit(d.get("yandex_api_key", ""))
        self.le_yandex_key.setPlaceholderText(tr("dub.yandex_placeholder"))
        self.le_yandex_key.setEchoMode(QLineEdit.EchoMode.Password)
        trans_form.addRow(tr("dub.yandex_key"), self.le_yandex_key)

        self.le_yandex_folder = QLineEdit(d.get("yandex_folder_id", ""))
        self.le_yandex_folder.setPlaceholderText("Yandex Cloud folder ID")
        trans_form.addRow(tr("dub.yandex_folder"), self.le_yandex_folder)
        layout.addWidget(trans_box)

        hint = QLabel(tr("dub.hint"))
        hint.setStyleSheet("color:#64748b;font-size:11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch(1)
        return w

    # ---------- Streaming ----------
    def _build_streaming(self) -> QWidget:
        outer = QScrollArea()
        outer.setWidgetResizable(True)
        outer.setFrameShape(QScrollArea.Shape.NoFrame)
        outer.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget"
                             "{background-color:#f8fafc;}")
        w = QWidget()
        w.setStyleSheet("background-color:#f8fafc;")
        outer.setWidget(w)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 8, 8, 8)

        s = self._settings.get("streaming")
        self.chk_stream = QCheckBox(tr("stream.enable"))
        self.chk_stream.setChecked(bool(s.get("enabled", False)))
        layout.addWidget(self.chk_stream)

        # Encoder section
        enc_box = QGroupBox(tr("stream.encoder"))
        enc_form = QFormLayout(enc_box)
        self.sp_stream_bitrate = self._spin(800, 20000,
                                             int(s.get("bitrate_kbps", 4500)))
        self.sp_stream_bitrate.setSuffix(" kbps")
        self.sp_stream_kf = self._spin(1, 6,
                                        int(s.get("keyframe_seconds", 2)))
        self.sp_stream_kf.setSuffix(" sec")
        self.sp_stream_audio = QComboBox()
        self.sp_stream_audio.addItems(["96", "128", "160", "192", "256"])
        self.sp_stream_audio.setCurrentText(str(s.get("audio_kbps", 160)))
        enc_form.addRow(tr("stream.bitrate"), self.sp_stream_bitrate)
        enc_form.addRow(tr("stream.keyframe"), self.sp_stream_kf)
        enc_form.addRow(tr("stream.audio_kbps"), self.sp_stream_audio)
        layout.addWidget(enc_box)

        # Targets section
        tgt_box = QGroupBox(tr("stream.targets"))
        self._tgt_layout = QVBoxLayout(tgt_box)
        self._tgt_rows: list[dict] = []

        targets = list(s.get("targets") or [])
        if not targets:
            targets = [{"platform": "youtube", "url": "", "key": "",
                        "enabled": False}]
        for t in targets:
            self._add_target_row(t)

        btn_row = QHBoxLayout()
        add_btn = QPushButton(tr("settings.btn.add_target"))
        add_btn.clicked.connect(lambda: self._add_target_row(
            {"platform": "custom", "url": "", "key": "", "enabled": False}
        ))
        btn_row.addWidget(add_btn)
        btn_row.addStretch(1)
        self._tgt_layout.addLayout(btn_row)
        layout.addWidget(tgt_box)

        hint = QLabel(tr("stream.hint"))
        hint.setStyleSheet("color:#64748b;font-size:11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch(1)
        return outer

    def _add_target_row(self, t: dict) -> None:
        platform = (t.get("platform") or "youtube").lower()
        row_box = QGroupBox(PLATFORM_PRESETS.get(platform, {}).get(
            "label", "Custom RTMP"))
        form = QFormLayout(row_box)

        chk = QCheckBox(tr("stream.target.enable"))
        chk.setChecked(bool(t.get("enabled", True)))
        form.addRow("", chk)

        cmb = QComboBox()
        for pid, info in PLATFORM_PRESETS.items():
            cmb.addItem(info["label"], pid)
        idx = max(0, cmb.findData(platform))
        cmb.setCurrentIndex(idx)

        le_url = QLineEdit(t.get("url") or PLATFORM_PRESETS.get(
            platform, {}).get("base_url", ""))
        le_url.setPlaceholderText(tr("stream.target.url_placeholder"))
        le_key = QLineEdit(t.get("key", ""))
        le_key.setPlaceholderText(tr("stream.target.key_placeholder"))
        le_key.setEchoMode(QLineEdit.EchoMode.Password)

        def _on_platform_change(_=None) -> None:
            pid = cmb.currentData() or "custom"
            preset = PLATFORM_PRESETS.get(pid, {})
            row_box.setTitle(preset.get("label", "Custom RTMP"))
            if not le_url.text().startswith(("rtmp://", "rtmps://")) \
                    and preset.get("base_url"):
                le_url.setText(preset["base_url"])
        cmb.currentIndexChanged.connect(_on_platform_change)

        form.addRow(tr("stream.target.platform"), cmb)
        form.addRow(tr("stream.target.base_url"), le_url)
        form.addRow(tr("stream.target.key"), le_key)

        btn_row = QHBoxLayout()
        test_btn = QPushButton("🧪 Test")
        test_btn.setObjectName("ghost")
        test_btn.clicked.connect(lambda: self._test_target_row(
            cmb, le_url, le_key, test_btn,
        ))
        btn_row.addWidget(test_btn)
        rm_btn = QPushButton(tr("settings.btn.remove"))
        rm_btn.setObjectName("ghost")
        def _remove() -> None:
            self._tgt_rows = [r for r in self._tgt_rows if r["box"] is not row_box]
            row_box.deleteLater()
        rm_btn.clicked.connect(_remove)
        btn_row.addWidget(rm_btn)
        btn_row.addStretch(1)
        btn_wrap = QWidget()
        btn_wrap.setLayout(btn_row)
        form.addRow("", btn_wrap)

        # insert before the (add target) button row
        self._tgt_layout.insertWidget(
            self._tgt_layout.count() - 1, row_box)
        self._tgt_rows.append({
            "box": row_box, "chk": chk, "cmb": cmb,
            "url": le_url, "key": le_key,
        })

    # ---------- streaming test ----------
    def _test_target_row(self, cmb_platform, le_url, le_key, btn) -> None:
        """Run a 2-sec lavfi → RTMP probe in a worker thread."""
        from streaming import (
            StreamTarget, build_rtmp_url, test_rtmp_target,
        )
        from PyQt6.QtCore import QThread, pyqtSignal
        from PyQt6.QtWidgets import QMessageBox

        platform = cmb_platform.currentData() or "custom"
        target = StreamTarget(
            platform=platform,
            base_url=le_url.text().strip(),
            stream_key=le_key.text().strip(),
            enabled=True,
        )
        url = build_rtmp_url(target)
        if not url:
            QMessageBox.warning(self, "Test stream",
                                 "URL / Stream key is empty.")
            return

        btn.setEnabled(False)
        old_text = btn.text()
        btn.setText("⏳ Testing…")

        class _Worker(QThread):
            done = pyqtSignal(bool, str)
            def run(self) -> None:
                ok, msg = test_rtmp_target(url, timeout_sec=12)
                self.done.emit(ok, msg)

        def _on_done(ok: bool, msg: str) -> None:
            btn.setEnabled(True)
            btn.setText(old_text)
            if ok:
                QMessageBox.information(self, "Test stream",
                                          f"✓ {msg}\n\n{url}")
            else:
                QMessageBox.warning(self, "Test stream",
                                     f"✗ {msg}\n\n{url}")

        worker = _Worker(self)
        worker.done.connect(_on_done)
        # Keep a ref so the QThread isn't GC'd before it finishes.
        if not hasattr(self, "_test_workers"):
            self._test_workers: list = []
        self._test_workers.append(worker)
        worker.finished.connect(lambda w=worker: self._test_workers.remove(w)
                                  if w in self._test_workers else None)
        worker.start()

    # ---------- HTML overlay ----------
    def _build_html(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        h = self._settings.get("html_overlay")

        self.chk_html = QCheckBox(tr("html.enable"))
        self.chk_html.setChecked(bool(h.get("enabled", False)))
        layout.addWidget(self.chk_html)

        geom_box = QGroupBox(tr("html.position_size"))
        geom_form = QFormLayout(geom_box)
        self.sp_html_x = self._spin(0, 7680, int(h.get("x", 40)))
        self.sp_html_y = self._spin(0, 4320, int(h.get("y", 40)))
        self.sp_html_w = self._spin(60, 7680, int(h.get("width", 480)))
        self.sp_html_h = self._spin(40, 4320, int(h.get("height", 200)))
        geom_form.addRow(tr("html.x"), self.sp_html_x)
        geom_form.addRow(tr("html.y"), self.sp_html_y)
        geom_form.addRow(tr("html.width"), self.sp_html_w)
        geom_form.addRow(tr("html.height"), self.sp_html_h)
        layout.addWidget(geom_box)

        opt_box = QGroupBox(tr("html.behaviour"))
        opt_form = QFormLayout(opt_box)
        self.chk_html_click = QCheckBox(tr("html.click_through"))
        self.chk_html_click.setChecked(bool(h.get("click_through", True)))
        self.chk_html_bg = QCheckBox(tr("html.transparent_bg"))
        self.chk_html_bg.setChecked(bool(h.get("transparent_background", True)))
        opt_form.addRow("", self.chk_html_click)
        opt_form.addRow("", self.chk_html_bg)
        layout.addWidget(opt_box)

        code_box = QGroupBox(tr("html.code"))
        code_lay = QVBoxLayout(code_box)
        self.txt_html = QPlainTextEdit(h.get("html", ""))
        mono = QFont("JetBrains Mono")
        if not mono.exactMatch():
            mono = QFont("Fira Code")
        if not mono.exactMatch():
            mono = QFont("Consolas")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        mono.setPointSize(10)
        self.txt_html.setFont(mono)
        self.txt_html.setMinimumHeight(220)
        code_lay.addWidget(self.txt_html)
        layout.addWidget(code_box, 1)

        hint = QLabel(tr("html.hint"))
        hint.setStyleSheet("color:#64748b;font-size:11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        return w

    # ---------- helpers ----------
    @staticmethod
    def _spin(lo: int, hi: int, val: int) -> QSpinBox:
        s = QSpinBox()
        s.setRange(lo, hi)
        s.setValue(val)
        return s

    @staticmethod
    def _labeled_slider(slider: QSlider) -> QWidget:
        wrap = QWidget()
        h = QHBoxLayout(wrap)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(slider, 1)
        lbl = QLabel(f"{slider.value()}%")
        lbl.setMinimumWidth(40)
        slider.valueChanged.connect(lambda v: lbl.setText(f"{v}%"))
        h.addWidget(lbl)
        return wrap

    @staticmethod
    def _select_combo_data(combo: QComboBox, value: str) -> None:
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return
        if combo.count() > 0:
            combo.setCurrentIndex(0)

    def _pick_logo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select logo image", str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.svg *.webp)"
        )
        if path:
            self.le_logo.setText(path)

    def _pick_folder(self) -> None:
        d = QFileDialog.getExistingDirectory(
            self, "Save folder",
            self.le_folder.text() or str(Path.home())
        )
        if d:
            self.le_folder.setText(d)

    def _open_author(self) -> None:
        AuthorDialog(self).exec()

    # ---------- save ----------
    def _save(self) -> None:
        new_lang = self.cmb_lang.currentData() or "uz"
        self._settings.set_section("general", {
            "language": new_lang,
            "theme": self.cmb_theme.currentText(),
            "start_with_system": self.chk_startup.isChecked(),
        })
        self._settings.set_section("video", {
            "fps": int(self.cmb_fps.currentText()),
            "resolution": self.cmb_res.currentText(),
            "codec": self.cmb_codec.currentText(),
            "format": self.cmb_format.currentText(),
            "bitrate": self.cmb_bitrate.currentText(),
            "encoder": self.cmb_encoder.currentText(),
        })
        src_map = {self.rb_mic: "mic", self.rb_desk: "desktop",
                   self.rb_both: "both", self.rb_none: "none"}
        source = next((v for k, v in src_map.items() if k.isChecked()), "both")
        self._settings.set_section("audio", {
            "source": source,
            "mic_volume": self.sld_mic.value(),
            "desktop_volume": self.sld_desk.value(),
            "noise_suppression": self.chk_ns.isChecked(),
            "echo_cancellation": self.chk_ec.isChecked(),
            "quality_kbps": int(self.cmb_aq.currentText()),
            "mic_device": self.cmb_mic.currentData() or "default",
            "desktop_device": self.cmb_desk.currentData() or "default",
        })
        self._settings.set_section("camera", {
            "enabled": self.chk_cam.isChecked(),
            "device": self.cmb_cam_dev.currentData() or "",
            "position": self.cmb_cam_pos.currentText(),
            "width": self.sp_cam_w.value(),
            "height": self.sp_cam_h.value(),
            "border_radius": self.sp_cam_radius.value(),
            "shadow": self.chk_cam_shadow.isChecked(),
            "opacity": self.sld_cam_opacity.value(),
        })
        self._settings.set_section("logo", {
            "enabled": self.chk_logo.isChecked(),
            "path": self.le_logo.text().strip(),
            "position": self.cmb_logo_pos.currentText(),
            "width": self.sp_logo_w.value(),
            "height": self.sp_logo_h.value(),
            "opacity": self.sld_logo_opacity.value(),
        })
        self._settings.set_section("output", {
            "folder": self.le_folder.text().strip()
                       or str(Path.home() / "Videos" / "VisioEye"),
            "filename_template": self.le_template.text().strip()
                                  or "record_{Y}_{M}_{D}_{h}_{m}_{s}",
        })
        self._settings.set_section("hotkeys", {
            k: v.text().strip() for k, v in self.hk_edits.items()
        })
        langs: list[str] = []
        if self.chk_src_en.isChecked():
            langs.append("en")
        if self.chk_src_ru.isChecked():
            langs.append("ru")
        if not langs:
            langs = ["en", "ru"]
        self._settings.set_section("dubbing", {
            "enabled": self.chk_dub.isChecked(),
            "source_languages": langs,
            "target_language": "uz",
            "voice": self.cmb_dub_voice.currentData() or "uz-UZ-MadinaNeural",
            "asr_model": self.cmb_asr_model.currentText(),
            "asr_device": self.cmb_asr_device.currentText(),
            "asr_compute": self.cmb_asr_compute.currentText(),
            "translator": self.cmb_translator.currentText(),
            "yandex_api_key": self.le_yandex_key.text().strip(),
            "yandex_folder_id": self.le_yandex_folder.text().strip(),
            "chunk_seconds": int(self.sp_chunk.value()),
        })
        targets: list[dict] = []
        for row in self._tgt_rows:
            targets.append({
                "platform": row["cmb"].currentData() or "custom",
                "url": row["url"].text().strip(),
                "key": row["key"].text().strip(),
                "enabled": row["chk"].isChecked(),
            })
        self._settings.set_section("streaming", {
            "enabled": self.chk_stream.isChecked(),
            "targets": targets,
            "bitrate_kbps": int(self.sp_stream_bitrate.value()),
            "keyframe_seconds": int(self.sp_stream_kf.value()),
            "audio_kbps": int(self.sp_stream_audio.currentText()),
        })
        self._settings.set_section("html_overlay", {
            "enabled": self.chk_html.isChecked(),
            "html": self.txt_html.toPlainText(),
            "x": int(self.sp_html_x.value()),
            "y": int(self.sp_html_y.value()),
            "width": int(self.sp_html_w.value()),
            "height": int(self.sp_html_h.value()),
            "click_through": self.chk_html_click.isChecked(),
            "transparent_background": self.chk_html_bg.isChecked(),
        })
        self._settings.save()
        if new_lang != getattr(self, "_initial_language", new_lang):
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                tr("general.lang_changed_title"),
                tr("general.lang_changed_body"),
            )
        self.settings_changed.emit()
        self.accept()
