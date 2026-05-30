"""Donate dialog — crypto wallet addresses with copy buttons.

Shown from the AUTOR dialog and the Settings tab.  The two supported
chains are Tether USDT on the TRC20 network and Bitcoin (native segwit
bech32).  Every label below the address shows the minimum deposit so
the user doesn't lose funds on dust transactions.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QFont, QGuiApplication
from PyQt6.QtWidgets import (
    QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QFrame,
    QWidget, QMessageBox,
)


USDT_ADDRESS = "TH3NqBukfpJ2CQuEfpsTjd2uUCq6gssBq8"
USDT_MIN = "10 USDT"
USDT_NETWORK = "TRC20 (Tron network)"

BTC_ADDRESS = "bc1qthlc34ne0qwgm2p9p0q99c7pq9takvl89ykelj"
BTC_MIN = "0.0002 BTC"
BTC_NETWORK = "Bitcoin native SegWit (bech32)"


class DonateDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Donate — Visio Eye")
        self.setModal(True)
        self.setMinimumSize(520, 580)
        self.setStyleSheet("""
            QDialog { background-color: #f8fafc; }
            QLabel#title { color: #0f172a; font-size: 22px; font-weight: 800; }
            QLabel#subtitle { color: #64748b; font-size: 12px;
                              letter-spacing: 1.5px; text-transform: uppercase;
                              font-weight: 600; }
            QLabel#chainLabel { color: #0f172a; font-size: 16px;
                                font-weight: 700; }
            QLabel#chainNet { color: #64748b; font-size: 11px; }
            QLabel#address {
                color: #0f172a;
                font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
                font-size: 13px;
                background: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 10px 14px;
            }
            QLabel#minLabel { color: #b45309; font-size: 12px;
                              font-weight: 700; background: #fef3c7;
                              border: 1px solid #fcd34d; border-radius: 6px;
                              padding: 4px 10px; }
            QFrame#card {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 14px;
            }
            QPushButton {
                background-color: #3b82f6;
                color: #ffffff;
                border: 1px solid #2563eb;
                border-radius: 8px;
                padding: 8px 18px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton#close {
                background: transparent;
                color: #334155;
                border: 1px solid #cbd5e1;
            }
            QPushButton#close:hover {
                background: #f1f5f9;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        # ---- header ----
        sub = QLabel("Support development")
        sub.setObjectName("subtitle")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(sub)

        title = QLabel("☕  Donate to Visio Eye")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        msg = QLabel(
            "Visio Eye is free and open source.  If it helps you, "
            "please consider a small donation — it keeps the project "
            "alive and fuels new features."
        )
        msg.setStyleSheet("color:#475569;font-size:13px;")
        msg.setWordWrap(True)
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(msg)

        # ---- USDT card ----
        root.addWidget(self._build_card(
            icon="usdt.svg", chain="USDT (Tether)",
            network=USDT_NETWORK,
            address=USDT_ADDRESS, minimum=USDT_MIN,
        ))

        # ---- BTC card ----
        root.addWidget(self._build_card(
            icon="btc.svg", chain="Bitcoin (BTC)",
            network=BTC_NETWORK,
            address=BTC_ADDRESS, minimum=BTC_MIN,
        ))

        # ---- close ----
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        close_btn = QPushButton("Close")
        close_btn.setObjectName("close")
        close_btn.clicked.connect(self.accept)
        bottom.addWidget(close_btn)
        root.addLayout(bottom)

    # ---------- helpers ----------
    def _build_card(self, icon: str, chain: str, network: str,
                     address: str, minimum: str) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        v = QVBoxLayout(card)
        v.setContentsMargins(18, 14, 18, 14)
        v.setSpacing(8)

        head = QHBoxLayout()
        icon_lbl = QLabel()
        icon_path = (Path(__file__).resolve().parents[2]
                     / "assets" / "icons" / icon)
        if icon_path.exists():
            pm = QPixmap(str(icon_path)).scaled(
                36, 36,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            icon_lbl.setPixmap(pm)
        icon_lbl.setFixedSize(40, 40)
        head.addWidget(icon_lbl)

        text_col = QVBoxLayout()
        text_col.setSpacing(0)
        chain_lbl = QLabel(chain)
        chain_lbl.setObjectName("chainLabel")
        net_lbl = QLabel(network)
        net_lbl.setObjectName("chainNet")
        text_col.addWidget(chain_lbl)
        text_col.addWidget(net_lbl)
        head.addLayout(text_col, 1)

        min_lbl = QLabel(f"Min: {minimum}")
        min_lbl.setObjectName("minLabel")
        head.addWidget(min_lbl, alignment=Qt.AlignmentFlag.AlignTop)
        v.addLayout(head)

        addr_lbl = QLabel(address)
        addr_lbl.setObjectName("address")
        addr_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        addr_lbl.setWordWrap(True)
        v.addWidget(addr_lbl)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        copy_btn = QPushButton("📋  Copy address")
        copy_btn.clicked.connect(lambda: self._copy(address, copy_btn))
        btn_row.addWidget(copy_btn)
        v.addLayout(btn_row)
        return card

    def _copy(self, text: str, btn: QPushButton) -> None:
        QGuiApplication.clipboard().setText(text)
        old = btn.text()
        btn.setText("✓  Copied")
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: btn.setText(old))
