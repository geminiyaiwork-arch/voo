"""Author modal — shows photo and contact info."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath, QFont
from PyQt6.QtWidgets import (
    QDialog, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QWidget,
)


def _round_pixmap(src: QPixmap, size: int, radius: int) -> QPixmap:
    if src.isNull():
        return src
    scaled = src.scaled(size, size,
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation)
    out = QPixmap(size, size)
    out.fill(Qt.GlobalColor.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    path = QPainterPath()
    path.addRoundedRect(0, 0, size, size, radius, radius)
    p.setClipPath(path)
    x = (size - scaled.width()) // 2
    y = (size - scaled.height()) // 2
    p.drawPixmap(x, y, scaled)
    p.end()
    return out


class AuthorDialog(QDialog):
    PHONE_1 = "+998 (91) 169-37-66"
    PHONE_2 = "+998 (99) 433-37-66"
    TELEGRAM = "@voo_uz"
    EMAIL = "elyorbek-13@mail.ru"

    def __init__(self, parent: QWidget | None = None,
                 image_path: str | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Autor — Visio Eye")
        self.setModal(True)
        self.setMinimumSize(420, 520)
        self.setStyleSheet("""
            QDialog { background-color: #f8fafc; }
            QLabel#name { color: #0f172a; font-size: 22px; font-weight: 800; }
            QLabel#role { color: #2563eb; font-size: 13px; font-weight: 600;
                          text-transform: uppercase; letter-spacing: 2px; }
            QLabel#contactLabel { color: #94a3b8; font-size: 11px;
                                   text-transform: uppercase;
                                   letter-spacing: 1.5px;
                                   font-weight: 700; }
            QLabel#contactValue { color: #0f172a; font-size: 15px;
                                   font-weight: 600; }
            QFrame#card {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 14px;
            }
            QPushButton {
                background-color: #ffffff;
                color: #0f172a;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 10px 18px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #3b82f6;
                border: 1px solid #2563eb;
                color: #ffffff;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        # avatar
        avatar = QLabel()
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setFixedSize(QSize(160, 160))
        path = image_path or str(
            Path(__file__).resolve().parents[2] / "assets" / "img" / "author.png"
        )
        pm = QPixmap(path)
        if not pm.isNull():
            avatar.setPixmap(_round_pixmap(pm, 160, 80))
        else:
            avatar.setStyleSheet(
                "background-color:#eff6ff;border-radius:80px;color:#2563eb;"
                "border:2px solid #bfdbfe;"
            )
            avatar.setText("VE")
            f = QFont()
            f.setPointSize(28)
            f.setBold(True)
            avatar.setFont(f)

        avatar_wrap = QHBoxLayout()
        avatar_wrap.addStretch(1)
        avatar_wrap.addWidget(avatar)
        avatar_wrap.addStretch(1)
        root.addLayout(avatar_wrap)

        name = QLabel("Elyorbek")
        name.setObjectName("name")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(name)

        role = QLabel("Developer · Visio Eye")
        role.setObjectName("role")
        role.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(role)

        # contact card
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(12)

        card_layout.addLayout(self._make_row("Phone 1", self.PHONE_1))
        card_layout.addLayout(self._make_row("Phone 2", self.PHONE_2))
        card_layout.addLayout(self._make_row("Telegram", self.TELEGRAM))
        card_layout.addLayout(self._make_row("Email", self.EMAIL))
        root.addWidget(card)

        # close button
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

    @staticmethod
    def _make_row(label: str, value: str) -> QHBoxLayout:
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setObjectName("contactLabel")
        lbl.setMinimumWidth(80)
        val = QLabel(value)
        val.setObjectName("contactValue")
        val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        row.addWidget(lbl)
        row.addWidget(val, 1)
        return row
