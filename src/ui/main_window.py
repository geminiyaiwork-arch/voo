"""Main application window — controls, status, presets, and overlays."""
from __future__ import annotations

import datetime
import shutil
import subprocess
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QAction, QPixmap
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QFrame, QComboBox, QToolButton, QMessageBox, QFileDialog, QSizePolicy,
)

from i18n import tr
from overlays import CameraOverlay, HtmlOverlay, LogoOverlay
from recorder import ScreenRecorder
from recorder.screenshot import take_screenshot
from settings import SettingsManager
from utils import HotkeyManager, SystemInfo

try:
    from dubbing import DubbingEngine, DubbingConfig
    from dubbing.pipeline import DubbingEvent
    _DUBBING_OK = True
except ImportError:                                     # pragma: no cover
    DubbingEngine = None                                # type: ignore[assignment]
    DubbingConfig = None                                # type: ignore[assignment]
    DubbingEvent = None                                  # type: ignore[assignment]
    _DUBBING_OK = False
from .author_dialog import AuthorDialog
from .region_selector import RegionSelector
from .settings_dialog import SettingsDialog
from .styles import APP_STYLE


class MainWindow(QMainWindow):
    """Top-level window. Holds all controls and orchestrates recording."""

    log_message = pyqtSignal(str)

    def __init__(self, settings: SettingsManager) -> None:
        super().__init__()
        self.setWindowTitle(f"Visio Eye — {tr('app.subtitle')}")
        self.setMinimumSize(1080, 680)
        check_icon = (Path(__file__).resolve().parents[2]
                       / "assets" / "icons" / "check_white.svg")
        self.setStyleSheet(APP_STYLE.replace("{CHECK_ICON}", str(check_icon)))

        for cand in ("logo.png", "author.png"):
            icon_path = (Path(__file__).resolve().parents[2]
                         / "assets" / "img" / cand)
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
                break

        self._settings = settings
        self.recorder = ScreenRecorder()
        self.dub_engine: DubbingEngine | None = (
            DubbingEngine() if _DUBBING_OK else None
        )
        self.dub_monitor_source: str | None = None
        self.cam_overlay: CameraOverlay | None = None
        self.logo_overlay: LogoOverlay | None = None
        self.html_overlay: HtmlOverlay | None = None
        self._region: tuple[int, int, int, int] | None = None
        self._record_started_at: datetime.datetime | None = None

        self.hotkeys = HotkeyManager(self)
        self.hotkeys.triggered.connect(self._on_hotkey)

        self._build_ui()
        self._connect_signals()
        self._refresh_overlays()
        self.hotkeys.update(self._settings.get("hotkeys"))

        # status timer
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._tick_status)
        self._status_timer.start(1000)

    # ---------- layout ----------
    def _build_ui(self) -> None:
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ----- sidebar -----
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(18, 18, 14, 18)
        sb.setSpacing(8)

        brand = QLabel("Visio Eye")
        brand.setStyleSheet(
            "color:#2563eb;font-size:24px;font-weight:900;letter-spacing:2px;"
        )
        tagline = QLabel(tr("app.subtitle"))
        tagline.setStyleSheet("color:#64748b;font-size:11px;letter-spacing:3px;")
        sb.addWidget(brand)
        sb.addWidget(tagline)
        sb.addSpacing(20)

        self.btn_record = QPushButton(tr("main.btn.record"))
        self.btn_record.setObjectName("primary")
        self.btn_record.setMinimumHeight(46)
        self.btn_record.setShortcut("F9")

        self.btn_pause = QPushButton(tr("main.btn.pause"))
        self.btn_pause.setEnabled(False)
        self.btn_pause.setShortcut("F10")

        self.btn_stop = QPushButton(tr("main.btn.stop"))
        self.btn_stop.setObjectName("danger")
        self.btn_stop.setEnabled(False)
        self.btn_stop.setMinimumHeight(40)
        self.btn_stop.setShortcut("F11")

        self.btn_screenshot = QPushButton(tr("main.btn.screenshot"))
        self.btn_screenshot.setObjectName("ghost")
        self.btn_screenshot.setShortcut("F12")

        sb.addWidget(self.btn_record)
        sb.addWidget(self.btn_pause)
        sb.addWidget(self.btn_stop)
        sb.addSpacing(6)
        sb.addWidget(self.btn_screenshot)
        sb.addStretch(1)

        self.btn_settings = QPushButton(tr("main.btn.settings"))
        self.btn_settings.setObjectName("ghost")
        self.btn_author = QPushButton(tr("main.btn.author"))
        self.btn_author.setObjectName("ghost")
        sb.addWidget(self.btn_settings)
        sb.addWidget(self.btn_author)

        root.addWidget(sidebar)

        # ----- main area -----
        main = QFrame()
        main.setObjectName("mainArea")
        ml = QVBoxLayout(main)
        ml.setContentsMargins(24, 18, 24, 18)
        ml.setSpacing(14)

        # header
        header = QFrame()
        header.setObjectName("headerBar")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 12, 16, 12)
        title = QLabel(tr("main.studio"))
        title.setObjectName("title")
        sub = QLabel(tr("main.studio_tag"))
        sub.setObjectName("subtitle")
        title_col = QVBoxLayout()
        title_col.addWidget(title)
        title_col.addWidget(sub)
        hl.addLayout(title_col)
        hl.addStretch(1)

        self.lbl_rec_dot = QLabel("●")
        self.lbl_rec_dot.setObjectName("recDot")
        self.lbl_rec_dot.setVisible(False)
        self.lbl_timer = QLabel("00:00:00")
        self.lbl_timer.setObjectName("timer")
        hl.addWidget(self.lbl_rec_dot)
        hl.addSpacing(8)
        hl.addWidget(self.lbl_timer)
        ml.addWidget(header)

        # presets row
        preset_row = QFrame()
        preset_row.setObjectName("card")
        prl = QHBoxLayout(preset_row)
        prl.setContentsMargins(18, 14, 18, 14)
        prl.setSpacing(20)

        self.cmb_mode = QComboBox()
        self.cmb_mode.addItem(tr("main.mode.fullscreen"), "fullscreen")
        self.cmb_mode.addItem(tr("main.mode.region"), "area")
        self.cmb_mode.addItem(tr("main.mode.window"), "window")

        self.cmb_quality = QComboBox()
        self.cmb_quality.addItems(["480p", "720p", "1080p", "2K", "4K"])
        self.cmb_quality.setCurrentText(self._settings.get("video", "resolution", "1080p"))

        self.cmb_fps = QComboBox()
        self.cmb_fps.addItems(["24", "30", "60"])
        self.cmb_fps.setCurrentText(str(self._settings.get("video", "fps", 30)))

        self.cmb_audio = QComboBox()
        self.cmb_audio.addItem(tr("audio.src.both"), "both")
        self.cmb_audio.addItem(tr("audio.src.mic"), "mic")
        self.cmb_audio.addItem(tr("audio.src.desk"), "desktop")
        self.cmb_audio.addItem(tr("audio.src.none"), "none")
        for i in range(self.cmb_audio.count()):
            if self.cmb_audio.itemData(i) == self._settings.get("audio", "source", "both"):
                self.cmb_audio.setCurrentIndex(i)
                break

        for label, widget in (
            (tr("main.card.mode"), self.cmb_mode),
            (tr("video.resolution"), self.cmb_quality),
            (tr("video.fps"), self.cmb_fps),
            (tr("audio.source"), self.cmb_audio),
        ):
            col = QVBoxLayout()
            lbl = QLabel(label)
            lbl.setObjectName("sectionHeader")
            col.addWidget(lbl)
            col.addWidget(widget)
            prl.addLayout(col)

        prl.addStretch(1)

        toggle_col = QVBoxLayout()
        lbl_overlays = QLabel(tr("main.card.overlays"))
        lbl_overlays.setObjectName("sectionHeader")
        toggle_col.addWidget(lbl_overlays)
        ovr_row = QHBoxLayout()
        self.btn_cam_toggle = QPushButton(f"📹  {tr('main.card.camera')}")
        self.btn_cam_toggle.setObjectName("ghost")
        self.btn_cam_toggle.setCheckable(True)
        self.btn_cam_toggle.setChecked(bool(self._settings.get("camera", "enabled", False)))
        self.btn_logo_toggle = QPushButton(f"⬡  {tr('main.card.logo')}")
        self.btn_logo_toggle.setObjectName("ghost")
        self.btn_logo_toggle.setCheckable(True)
        self.btn_logo_toggle.setChecked(bool(self._settings.get("logo", "enabled", False)))
        ovr_row.addWidget(self.btn_cam_toggle)
        ovr_row.addWidget(self.btn_logo_toggle)
        toggle_col.addLayout(ovr_row)
        prl.addLayout(toggle_col)

        ml.addWidget(preset_row)

        # output info card
        info_card = QFrame()
        info_card.setObjectName("card")
        il = QVBoxLayout(info_card)
        il.setContentsMargins(18, 16, 18, 16)
        il.setSpacing(10)

        out_lbl = QLabel(tr("output.folder"))
        out_lbl.setObjectName("sectionHeader")
        il.addWidget(out_lbl)
        out_row = QHBoxLayout()
        self.lbl_folder = QLabel(self._settings.get("output", "folder", ""))
        self.lbl_folder.setStyleSheet("color:#334155;")
        self.lbl_folder.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        btn_change = QPushButton(tr("main.card.change"))
        btn_change.setObjectName("ghost")
        btn_change.clicked.connect(self._change_folder)
        btn_open = QPushButton(tr("main.card.open"))
        btn_open.setObjectName("ghost")
        btn_open.clicked.connect(self._open_folder)
        out_row.addWidget(self.lbl_folder, 1)
        out_row.addWidget(btn_change)
        out_row.addWidget(btn_open)
        il.addLayout(out_row)

        ml.addWidget(info_card)

        # status / metrics card
        metrics = QFrame()
        metrics.setObjectName("card")
        msg = QHBoxLayout(metrics)
        msg.setContentsMargins(18, 16, 18, 16)
        msg.setSpacing(28)

        self.lbl_cpu = self._metric(tr("main.metric.cpu"), "—")
        self.lbl_gpu = self._metric("GPU", "—")
        self.lbl_mem = self._metric("RAM", "—")
        self.lbl_disk = self._metric("Disk free", "—")
        self.lbl_fps_actual = self._metric(tr("main.metric.fps"), "—")
        self.lbl_status = self._metric(tr("main.metric.status"),
                                        tr("main.status.idle"))
        for w in (self.lbl_cpu, self.lbl_gpu, self.lbl_mem, self.lbl_disk,
                  self.lbl_fps_actual, self.lbl_status):
            msg.addWidget(w[0])

        ml.addWidget(metrics)
        ml.addStretch(1)

        # log line
        self.lbl_log = QLabel("")
        self.lbl_log.setStyleSheet("color:#94a3b8;font-size:11px;")
        self.lbl_log.setWordWrap(True)
        ml.addWidget(self.lbl_log)

        root.addWidget(main, 1)
        self.setCentralWidget(central)

        self.statusBar().showMessage(tr("main.status.ready"))

    @staticmethod
    def _metric(label: str, value: str) -> tuple[QWidget, QLabel]:
        wrap = QWidget()
        v = QVBoxLayout(wrap)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        l = QLabel(label.upper())
        l.setStyleSheet("color:#94a3b8;font-size:10px;letter-spacing:1.5px;font-weight:600;")
        vv = QLabel(value)
        vv.setObjectName("statusValue")
        vv.setStyleSheet("color:#2563eb;font-weight:700;font-size:16px;")
        v.addWidget(l)
        v.addWidget(vv)
        return wrap, vv

    # ---------- signals ----------
    def _connect_signals(self) -> None:
        self.btn_record.clicked.connect(self._start_recording)
        self.btn_pause.clicked.connect(self._toggle_pause)
        self.btn_stop.clicked.connect(self._stop_recording)
        self.btn_screenshot.clicked.connect(self._take_screenshot)
        self.btn_settings.clicked.connect(self._open_settings)
        self.btn_author.clicked.connect(self._open_author)
        self.btn_cam_toggle.toggled.connect(self._toggle_camera)
        self.btn_logo_toggle.toggled.connect(self._toggle_logo)
        self.cmb_quality.currentTextChanged.connect(
            lambda v: self._save_inline("video", "resolution", v)
        )
        self.cmb_fps.currentTextChanged.connect(
            lambda v: self._save_inline("video", "fps", int(v))
        )
        self.cmb_audio.currentIndexChanged.connect(
            lambda _i: self._save_inline(
                "audio", "source", self.cmb_audio.currentData()
            )
        )

    def _save_inline(self, section: str, key: str, value) -> None:
        self._settings.set(section, key, value)
        self._settings.save()

    # ---------- overlays ----------
    def _refresh_overlays(self) -> None:
        if self.btn_cam_toggle.isChecked():
            self._start_camera_overlay()
        else:
            self._stop_camera_overlay()
        if self.btn_logo_toggle.isChecked():
            self._start_logo_overlay()
        else:
            self._stop_logo_overlay()
        if self._settings.get("html_overlay", "enabled", False):
            self._start_html_overlay()
        else:
            self._stop_html_overlay()

    def _toggle_camera(self, checked: bool) -> None:
        self._save_inline("camera", "enabled", checked)
        if checked:
            self._start_camera_overlay()
        else:
            self._stop_camera_overlay()

    def _toggle_logo(self, checked: bool) -> None:
        self._save_inline("logo", "enabled", checked)
        if checked:
            self._start_logo_overlay()
        else:
            self._stop_logo_overlay()

    def _start_camera_overlay(self) -> None:
        c = self._settings.get("camera")
        device = c.get("device", "")
        if self.cam_overlay is None:
            self.cam_overlay = CameraOverlay(device=device)
        else:
            self.cam_overlay.set_device(device)
        self.cam_overlay.resize(int(c.get("width", 240)), int(c.get("height", 180)))
        self.cam_overlay.set_radius(int(c.get("border_radius", 16)))
        self.cam_overlay.set_opacity_pct(int(c.get("opacity", 100)))
        if not self.cam_overlay.start():
            self._log(f"Cannot open camera device {device}")
            self.btn_cam_toggle.setChecked(False)
            return
        self._log(f"Camera overlay started: {device}")

    def _stop_camera_overlay(self) -> None:
        if self.cam_overlay is not None:
            self.cam_overlay.stop()

    def _start_logo_overlay(self) -> None:
        l_ = self._settings.get("logo")
        path = l_.get("path", "")
        if not path or not Path(path).exists():
            path, _ = QFileDialog.getOpenFileName(
                self, "Choose a logo image", str(Path.home()),
                "Images (*.png *.jpg *.jpeg *.svg *.webp)"
            )
            if not path:
                self.btn_logo_toggle.setChecked(False)
                return
            self._save_inline("logo", "path", path)
        if self.logo_overlay is None:
            self.logo_overlay = LogoOverlay()
        self.logo_overlay.resize(int(l_.get("width", 120)), int(l_.get("height", 120)))
        self.logo_overlay.set_opacity_pct(int(l_.get("opacity", 90)))
        if not self.logo_overlay.load(path):
            self._log(f"Cannot load logo image: {path}")
            self.btn_logo_toggle.setChecked(False)
            return
        self.logo_overlay.show()
        self._log(f"Logo overlay loaded: {path}")

    def _stop_logo_overlay(self) -> None:
        if self.logo_overlay is not None:
            self.logo_overlay.hide()

    # ---------- HTML overlay ----------
    def _start_html_overlay(self) -> None:
        h = self._settings.get("html_overlay")
        if self.html_overlay is None:
            self.html_overlay = HtmlOverlay()
        self.html_overlay.set_geometry(
            int(h.get("x", 40)), int(h.get("y", 40)),
            int(h.get("width", 480)), int(h.get("height", 200)),
        )
        self.html_overlay.set_click_through(bool(h.get("click_through", True)))
        self.html_overlay.set_transparent_background(
            bool(h.get("transparent_background", True))
        )
        self.html_overlay.set_html(h.get("html", ""))
        self.html_overlay.show()

    def _stop_html_overlay(self) -> None:
        if self.html_overlay is not None:
            self.html_overlay.hide()

    # ---------- recording ----------
    def _start_recording(self) -> None:
        from recorder.ffmpeg_handler import FFmpegRecorder
        if not FFmpegRecorder.ffmpeg_available():
            QMessageBox.critical(
                self, "FFmpeg missing",
                "FFmpeg is not installed.\n\nInstall it with:\n"
                "    sudo apt install ffmpeg"
            )
            return
        if self.recorder.is_recording():
            return

        mode = self.cmb_mode.currentData()
        region = None
        if mode == "area":
            self._begin_area_selection()
            return
        elif mode == "window":
            region = self._active_window_region()
            if region is None:
                self._log("Could not detect active window — falling back to fullscreen")

        self._save_inline("video", "capture_mode", mode)
        self._launch_recording(region)

    def _begin_area_selection(self) -> None:
        self.hide()
        QTimer.singleShot(250, self._show_region_selector)

    def _show_region_selector(self) -> None:
        sel = RegionSelector()
        sel.region_selected.connect(self._on_region_picked)
        sel.cancelled.connect(self._on_region_cancelled)
        sel.show()
        self._region_selector = sel

    def _on_region_picked(self, x: int, y: int, w: int, h: int) -> None:
        self.show()
        self._launch_recording((x, y, w, h))

    def _on_region_cancelled(self) -> None:
        self.show()
        self._log("Region selection cancelled")

    def _active_window_region(self) -> tuple[int, int, int, int] | None:
        if not shutil.which("xdotool"):
            return None
        try:
            wid = subprocess.check_output(
                ["xdotool", "getactivewindow"], text=True, timeout=2
            ).strip()
            geo = subprocess.check_output(
                ["xdotool", "getwindowgeometry", "--shell", wid],
                text=True, timeout=2,
            )
            d = {}
            for line in geo.splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    d[k.strip()] = v.strip()
            x, y = int(d["X"]), int(d["Y"])
            w, h = int(d["WIDTH"]), int(d["HEIGHT"])
            return x, y, max(w, 16), max(h, 16)
        except (OSError, subprocess.SubprocessError, KeyError, ValueError):
            return None

    def _launch_recording(self, region: tuple[int, int, int, int] | None) -> None:
        # ---- start dubbing first so the recorder can pick up the dub sink ----
        settings_snapshot = self._settings.all()
        self.dub_monitor_source = None
        dub_cfg = settings_snapshot.get("dubbing", {}) or {}
        if (_DUBBING_OK and self.dub_engine is not None
                and bool(dub_cfg.get("enabled", False))):
            # Pre-download the Whisper model with a progress dialog
            # so the first launch doesn't look frozen for ~1 minute.
            if not self._ensure_whisper_model(dub_cfg):
                self._log("Dublyator bekor qilindi — model yuklanmadi")
            else:
                try:
                    self.dub_monitor_source = self._start_dubbing(dub_cfg)
                    self._log("Dublyator yoqildi")
                    settings_snapshot.setdefault("audio", {})
                    settings_snapshot["audio"]["source"] = "desktop"
                    settings_snapshot["audio"]["desktop_device"] = self.dub_monitor_source
                except (OSError, RuntimeError) as e:
                    QMessageBox.warning(self, "Dubbing failed to start", str(e))
                    self._log(f"Dublyator yoqilmadi: {e}")
                    self.dub_monitor_source = None

        try:
            out = self.recorder.start_from_settings(settings_snapshot, region=region)
        except (OSError, RuntimeError) as e:
            self._stop_dubbing_silent()
            QMessageBox.critical(self, "Recording failed", str(e))
            return

        QTimer.singleShot(1500, self._verify_recording_alive)
        self._record_started_at = datetime.datetime.now()
        self.lbl_status[0].show()
        self.lbl_status[1].setText(tr("main.status.recording"))
        self.lbl_rec_dot.setVisible(True)
        self.btn_record.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_stop.setEnabled(True)
        self._blink_state = True
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._blink)
        self._blink_timer.start(600)
        self._log(f"Recording → {out}")
        self.statusBar().showMessage(f"Recording → {out}")

    def _verify_recording_alive(self) -> None:
        """Called 1.5s after start. If backend died, surface the stderr."""
        if self.recorder.is_recording():
            backend = getattr(self.recorder, "backend", "?")
            self._log(f"Recording started via {backend} backend")
            # Streaming subprocess status
            engine = getattr(self.recorder, "_active", None)
            sproc = getattr(engine, "_stream_proc", None)
            slog = getattr(engine, "_stream_log", "")
            if sproc is not None:
                if sproc.poll() is None:
                    self._log(f"Streaming bridge OK · log: {slog}")
                else:
                    self._log(f"⚠ Streaming bridge exited early — see {slog}")
                    QMessageBox.warning(
                        self, "Streaming",
                        "Streaming FFmpeg subprocess exited early.\n\n"
                        f"Check logs: {slog}\n\n"
                        "Tip: make sure FFmpeg is installed and the\n"
                        "stream URL/key are correct."
                    )
            return
        self._stop_dubbing_silent()
        code, err = self.recorder.stop()
        if hasattr(self, "_blink_timer"):
            self._blink_timer.stop()
        self.lbl_rec_dot.setVisible(False)
        self.btn_record.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.lbl_status[1].setText(tr("main.status.idle"))
        self._record_started_at = None

        msg = (err or "").strip()[:1200] or "Recording subprocess exited immediately."
        helpful = ""
        if self.recorder.backend == "wayland":
            helpful = (
                "\n\nWayland tips:\n"
                "  • Make sure you GRANTED the screen share permission in the\n"
                "    portal dialog that appeared.\n"
                "  • Install missing tools:\n"
                "      sudo apt install gstreamer1.0-tools \\\n"
                "        gstreamer1.0-plugins-good \\\n"
                "        gstreamer1.0-plugins-bad \\\n"
                "        gstreamer1.0-pipewire python3-dbus python3-gi"
            )
        QMessageBox.critical(self, "Recording failed", msg + helpful)
        self._log(f"Recording failed (code {code}): {msg.splitlines()[-1] if msg else ''}")

    # ---------- dubbing wiring ----------
    def _ensure_whisper_model(self, dub_cfg: dict) -> bool:
        """If the Whisper model isn't cached locally, show a progress
        dialog and download it.  Returns False if the user cancels."""
        try:
            from dubbing.asr_loader import (
                is_model_cached, download_in_thread,
            )
        except ImportError:
            return True                  # let DubbingEngine handle the error
        model_size = dub_cfg.get("asr_model", "large-v3")
        if is_model_cached(model_size):
            return True

        from PyQt6.QtWidgets import QProgressDialog
        dlg = QProgressDialog(
            f"Whisper {model_size} modelini yuklab olish (~1.5 GB)…",
            "Bekor qilish", 0, 100, self,
        )
        dlg.setWindowTitle("Visio Eye — Dublyator")
        dlg.setMinimumDuration(0)
        dlg.setAutoClose(True)
        dlg.setAutoReset(False)
        dlg.show()

        state = {"done": False, "ok": False, "abort": False}

        def progress(frac: float, status: str) -> bool:
            # Marshal to UI thread via QMetaObject — we're on a worker.
            QTimer.singleShot(0, lambda f=frac, s=status:
                              (dlg.setValue(int(f * 100)),
                               dlg.setLabelText(
                                   f"Whisper {model_size}: {s}")))
            return not state["abort"]

        def done(ok: bool) -> None:
            state["done"] = True
            state["ok"] = ok
            QTimer.singleShot(0, dlg.close)

        download_in_thread(model_size, progress, done)

        # Block UI by spinning the event loop until done/cancelled.
        from PyQt6.QtCore import QEventLoop
        loop = QEventLoop()

        def _tick() -> None:
            if state["done"] or dlg.wasCanceled():
                if dlg.wasCanceled():
                    state["abort"] = True
                loop.quit()
        timer = QTimer(self)
        timer.timeout.connect(_tick)
        timer.start(150)
        loop.exec()
        timer.stop()
        return state["ok"] and not state["abort"]

    def _start_dubbing(self, dub_cfg: dict) -> str:
        """Build DubbingConfig from settings dict and start engine.

        Returns the PulseAudio monitor source name the recorder should
        record audio from."""
        assert self.dub_engine is not None and DubbingConfig is not None
        cfg = DubbingConfig(
            enabled=True,
            asr_model=dub_cfg.get("asr_model", "large-v3"),
            asr_device=dub_cfg.get("asr_device", "cuda"),
            asr_compute=dub_cfg.get("asr_compute", "int8_float16"),
            languages=tuple(dub_cfg.get("source_languages", ["en", "ru"])),
            target_lang=dub_cfg.get("target_language", "uz"),
            voice=dub_cfg.get("voice", "uz-UZ-MadinaNeural"),
            translator=dub_cfg.get("translator", "auto"),
            yandex_api_key=dub_cfg.get("yandex_api_key", ""),
            yandex_folder_id=dub_cfg.get("yandex_folder_id", ""),
            chunk_seconds=float(dub_cfg.get("chunk_seconds", 3.0)),
        )
        self.dub_engine.set_event_callback(self._on_dub_event)
        return self.dub_engine.start(cfg)

    def _stop_dubbing_silent(self) -> None:
        if self.dub_engine is None or not self.dub_engine.running:
            return
        try:
            self.dub_engine.stop()
        except Exception:                                # pylint: disable=broad-except
            pass
        self.dub_monitor_source = None

    def _on_dub_event(self, ev) -> None:
        """Live transcript callback. Runs in worker thread → marshal."""
        try:
            text = f"[{ev.src_lang.upper()}] {ev.src_text}  →  {ev.tgt_text}"
        except AttributeError:
            return
        QTimer.singleShot(0, lambda t=text: self._log(t))

    def _toggle_pause(self) -> None:
        if not self.recorder.is_recording():
            return
        if self.recorder.is_paused():
            self.recorder.resume()
            self.btn_pause.setText("⏸  Pause")
            self.lbl_status[1].setText(tr("main.status.recording"))
            self._log("Resumed")
        else:
            self.recorder.pause()
            self.btn_pause.setText("▶  Resume")
            self.lbl_status[1].setText(tr("main.status.paused"))
            self._log(tr("main.log.paused"))

    def _stop_recording(self) -> None:
        if not self.recorder.is_recording():
            return
        self._stop_dubbing_silent()
        code, err = self.recorder.stop()
        if hasattr(self, "_blink_timer"):
            self._blink_timer.stop()
        self.lbl_rec_dot.setVisible(False)
        self.btn_record.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setText("⏸  Pause")
        self.btn_stop.setEnabled(False)
        self.lbl_status[1].setText(tr("main.status.idle"))
        self._record_started_at = None
        out = self.recorder.last_output or ""
        if code == 0:
            self._log(f"Saved: {out}")
            self.statusBar().showMessage(f"Saved: {out}", 8000)
        else:
            self._log(f"FFmpeg exited with code {code}: {err.strip()[:300]}")
            self.statusBar().showMessage(f"FFmpeg error (code {code})", 8000)

    def _blink(self) -> None:
        self.lbl_rec_dot.setVisible(not self.lbl_rec_dot.isVisible())

    def _take_screenshot(self) -> None:
        folder = self._settings.get("output", "folder")
        path = take_screenshot(folder)
        if path:
            self._log(f"Screenshot saved: {path}")
            self.statusBar().showMessage(f"Screenshot saved: {path}", 5000)
        else:
            self._log("Screenshot failed — install ffmpeg / scrot / imagemagick")

    # ---------- side actions ----------
    def _open_settings(self) -> None:
        dlg = SettingsDialog(self._settings, self)
        dlg.settings_changed.connect(self._on_settings_changed)
        dlg.exec()

    def _on_settings_changed(self) -> None:
        self.cmb_quality.setCurrentText(
            self._settings.get("video", "resolution", "1080p")
        )
        self.cmb_fps.setCurrentText(
            str(self._settings.get("video", "fps", 30))
        )
        for i in range(self.cmb_audio.count()):
            if self.cmb_audio.itemData(i) == self._settings.get("audio", "source", "both"):
                self.cmb_audio.setCurrentIndex(i)
                break
        self.lbl_folder.setText(self._settings.get("output", "folder", ""))
        self.btn_cam_toggle.setChecked(
            bool(self._settings.get("camera", "enabled", False))
        )
        self.btn_logo_toggle.setChecked(
            bool(self._settings.get("logo", "enabled", False))
        )
        self.hotkeys.update(self._settings.get("hotkeys"))
        self._refresh_overlays()
        self._log("Settings updated")

    def _open_author(self) -> None:
        AuthorDialog(self).exec()

    def _change_folder(self) -> None:
        d = QFileDialog.getExistingDirectory(
            self, "Output folder",
            self._settings.get("output", "folder", str(Path.home()))
        )
        if d:
            self._save_inline("output", "folder", d)
            self.lbl_folder.setText(d)

    def _open_folder(self) -> None:
        folder = self._settings.get("output", "folder", "")
        if folder and Path(folder).exists():
            subprocess.Popen(["xdg-open", folder])
        else:
            QMessageBox.information(self, "Folder", "Folder does not exist yet.")

    # ---------- hotkeys ----------
    def _on_hotkey(self, action: str) -> None:
        if action == "start" and not self.recorder.is_recording():
            self._start_recording()
        elif action == "pause" or action == "resume":
            self._toggle_pause()
        elif action == "stop":
            self._stop_recording()
        elif action == "screenshot":
            self._take_screenshot()

    # ---------- status tick ----------
    def _tick_status(self) -> None:
        cpu = SystemInfo.cpu_percent()
        mem = SystemInfo.memory_percent()
        disk = SystemInfo.disk_free_gb(self._settings.get("output", "folder", str(Path.home())))
        gpu = SystemInfo.gpu_percent()
        self.lbl_cpu[1].setText(f"{cpu:.0f}%")
        self.lbl_mem[1].setText(f"{mem:.0f}%")
        self.lbl_disk[1].setText(f"{disk:.1f} GB")
        self.lbl_gpu[1].setText(f"{gpu:.0f}%" if gpu is not None else "—")

        fps = self._settings.get("video", "fps", 30)
        self.lbl_fps_actual[1].setText(f"{fps}")

        if self.recorder.is_recording() and self._record_started_at:
            elapsed = datetime.datetime.now() - self._record_started_at
            t = int(elapsed.total_seconds())
            self.lbl_timer.setText(f"{t // 3600:02d}:{(t % 3600) // 60:02d}:{t % 60:02d}")
        else:
            self.lbl_timer.setText("00:00:00")

    # ---------- log ----------
    def _log(self, msg: str) -> None:
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.lbl_log.setText(f"[{ts}] {msg}")

    # ---------- cleanup ----------
    def closeEvent(self, e) -> None:
        if self.recorder.is_recording():
            self.recorder.stop()
        self._stop_dubbing_silent()
        self._stop_camera_overlay()
        self._stop_logo_overlay()
        self._stop_html_overlay()
        if self.html_overlay is not None:
            self.html_overlay.close()
        self.hotkeys.stop()
        super().closeEvent(e)
