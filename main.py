"""
Yahoo!オークション 発送情報 一括解析ツール
GUI entry point — run with: python main.py
Requires: pip install PyQt5
"""

import json
import os
import sys
from pathlib import Path

from PyQt5.QtCore import QObject, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QTextCursor
from PyQt5.QtWidgets import (
    QApplication, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QProgressBar, QPushButton, QTextEdit,
    QVBoxLayout, QWidget,
)


from excel_writer import write_excel
from ocr_engine import create_engine
from parser import FIELD_KEYS, check_status, parse
from tic_writer import tic_output_path, write_tic_excel

if getattr(sys, "frozen", False):
    _CONFIG_FILE = Path(sys.executable).parent / "config.json"
else:
    _CONFIG_FILE = Path(__file__).parent / "config.json"
_SUPPORTED_EXT = {".jpg", ".jpeg", ".png"}


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    if _CONFIG_FILE.exists():
        try:
            with open(_CONFIG_FILE, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            pass
    return {
        "engine": "tongyi",
        "doubao_api_key": "",
        "doubao_model": "doubao-1-5-vision-pro-32k-250115",
        "tongyi_api_key": "",
        "tongyi_model": "qwen-vl-plus",
        "proxy": "",
    }


def _save_config(cfg: dict) -> None:
    with open(_CONFIG_FILE, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Worker thread
# ---------------------------------------------------------------------------

class WorkerSignals(QObject):
    log      = pyqtSignal(str, str)    # (message, tag)
    progress = pyqtSignal(int)
    status   = pyqtSignal(str)
    done     = pyqtSignal(object, object)  # (records | None, out_path | None)


class Worker(QThread):
    def __init__(self, engine_type: str, images: list, out_path: str, kwargs: dict):
        super().__init__()
        self.signals       = WorkerSignals()
        self._engine_type  = engine_type
        self._images       = images
        self._out_path     = out_path
        self._kwargs       = kwargs
        self._running      = True

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        records = []
        self.signals.log.emit(f"処理開始: {len(self._images)} ファイル", "info")

        try:
            ocr = create_engine(self._engine_type, **self._kwargs)
        except Exception as exc:
            self.signals.log.emit(f"OCRエンジン初期化失敗: {exc}", "err")
            self.signals.done.emit(None, None)
            return

        empty_fields = {k: "" for k in FIELD_KEYS}

        for i, img_path in enumerate(self._images):
            if not self._running:
                break
            fname = os.path.basename(img_path)
            self.signals.status.emit(f"処理中 ({i + 1}/{len(self._images)}): {fname}")

            try:
                text   = ocr.recognize(img_path)
                fields = parse(text)
                status = check_status(fields)
                records.append({"filename": fname, "status": status, **fields})
                tag = "ok" if status == "OK" else "warn"
                self.signals.log.emit(f"[{status}] {fname}", tag)
            except Exception as exc:
                records.append({"filename": fname, "status": "エラー", **empty_fields})
                self.signals.log.emit(f"[エラー] {fname}: {exc}", "err")

            self.signals.progress.emit(i + 1)

        self.signals.done.emit(records, self._out_path)


# ---------------------------------------------------------------------------
# Settings dialog
# ---------------------------------------------------------------------------

class SettingsDialog(QDialog):
    def __init__(self, parent: QWidget, cfg: dict):
        super().__init__(parent)
        self.setWindowTitle("API 設定")
        self.setFixedWidth(460)
        self._build(cfg)

    def _build(self, cfg: dict) -> None:
        layout = QGridLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        layout.addWidget(QLabel("OCRエンジン:"), 0, 0)
        self._engine = QComboBox()
        self._engine.addItems(["tongyi", "doubao"])
        self._engine.setCurrentText(cfg.get("engine", "tongyi"))
        layout.addWidget(self._engine, 0, 1)

        layout.addWidget(QLabel("通义 APIキー:"), 1, 0)
        self._tongyi_key = QLineEdit(cfg.get("tongyi_api_key", ""))
        self._tongyi_key.setEchoMode(QLineEdit.Password)
        self._tongyi_key.setMinimumWidth(260)
        self._tongyi_key.setPlaceholderText("dashscope.aliyun.com で取得")
        layout.addWidget(self._tongyi_key, 1, 1)

        layout.addWidget(QLabel("通义モデル:"), 2, 0)
        self._tongyi_model = QComboBox()
        self._tongyi_model.addItems([
            "qwen-vl-plus",
            "qwen-vl-max",
            "qwen2-vl-7b-instruct",
        ])
        self._tongyi_model.setCurrentText(cfg.get("tongyi_model", "qwen-vl-plus"))
        self._tongyi_model.setEditable(True)
        layout.addWidget(self._tongyi_model, 2, 1)

        layout.addWidget(QLabel("豆包 APIキー:"), 3, 0)
        self._doubao_key = QLineEdit(cfg.get("doubao_api_key", ""))
        self._doubao_key.setEchoMode(QLineEdit.Password)
        self._doubao_key.setMinimumWidth(260)
        self._doubao_key.setPlaceholderText("console.volcengine.com で取得")
        layout.addWidget(self._doubao_key, 3, 1)

        layout.addWidget(QLabel("豆包モデル:"), 4, 0)
        self._doubao_model = QComboBox()
        self._doubao_model.addItems([
            "doubao-1-5-vision-pro-32k-250115",
            "doubao-1.5-vision-pro-32k",
            "doubao-vision-plus-32k",
            "doubao-vision-lite-32k",
        ])
        self._doubao_model.setCurrentText(cfg.get("doubao_model", "doubao-1-5-vision-pro-32k-250115"))
        self._doubao_model.setEditable(True)
        layout.addWidget(self._doubao_model, 4, 1)

        layout.addWidget(QLabel("代理 (可选):"), 5, 0)
        self._proxy = QLineEdit(cfg.get("proxy", ""))
        self._proxy.setPlaceholderText("http://127.0.0.1:6738  (通常不需要)")
        layout.addWidget(self._proxy, 5, 1)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns, 6, 0, 1, 2)

    def get_config(self) -> dict:
        return {
            "engine":         self._engine.currentText(),
            "tongyi_api_key": self._tongyi_key.text().strip(),
            "tongyi_model":   self._tongyi_model.currentText().strip(),
            "doubao_api_key": self._doubao_key.text().strip(),
            "doubao_model":   self._doubao_model.currentText().strip(),
            "proxy":          self._proxy.text().strip(),
        }


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Yahoo!オークション 発送情報 一括解析ツール  v1.0")
        self.setMinimumSize(720, 580)
        self._cfg    = _load_config()
        self._worker = None
        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(8)
        root.setContentsMargins(12, 12, 12, 12)

        # ── Toolbar ──────────────────────────────────────────────────────
        toolbar = QFrame()
        toolbar.setFrameShape(QFrame.StyledPanel)
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(8, 4, 8, 4)
        tb.addWidget(QLabel("OCRエンジン:"))
        self._engine_lbl = QLabel(self._cfg.get("engine", "paddle").upper())
        self._engine_lbl.setStyleSheet("color: #1565C0; font-weight: bold;")
        tb.addWidget(self._engine_lbl)
        tb.addSpacing(12)
        settings_btn = QPushButton("⚙  API設定")
        settings_btn.clicked.connect(self._open_settings)
        tb.addWidget(settings_btn)
        tb.addStretch()
        root.addWidget(toolbar)

        # ── File paths ────────────────────────────────────────────────────
        file_group = QGroupBox("ファイル設定")
        fg = QGridLayout(file_group)
        fg.setSpacing(8)

        fg.addWidget(QLabel("画像フォルダ:"), 0, 0)
        self._folder = QLineEdit()
        self._folder.setPlaceholderText("截图所在文件夹...")
        fg.addWidget(self._folder, 0, 1)
        folder_btn = QPushButton("選択")
        folder_btn.clicked.connect(self._pick_folder)
        fg.addWidget(folder_btn, 0, 2)

        fg.addWidget(QLabel("出力ファイル:"), 1, 0)
        self._output = QLineEdit(str(Path.home() / "Downloads" / "shipping_info.xlsx"))
        fg.addWidget(self._output, 1, 1)
        output_btn = QPushButton("選択")
        output_btn.clicked.connect(self._pick_output)
        fg.addWidget(output_btn, 1, 2)

        root.addWidget(file_group)

        # ── Action buttons ────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        self._start_btn = QPushButton("▶  解析開始")
        self._start_btn.setFixedHeight(34)
        self._start_btn.setStyleSheet(
            "QPushButton{background:#1976D2;color:white;border-radius:4px;"
            "font-weight:bold;padding:0 16px;}"
            "QPushButton:hover{background:#1565C0;}"
            "QPushButton:disabled{background:#90CAF9;}"
        )
        self._start_btn.clicked.connect(self._start)
        btn_row.addWidget(self._start_btn)

        self._stop_btn = QPushButton("■  停止")
        self._stop_btn.setFixedHeight(34)
        self._stop_btn.setEnabled(False)
        self._stop_btn.setStyleSheet(
            "QPushButton{background:#E53935;color:white;border-radius:4px;"
            "font-weight:bold;padding:0 16px;}"
            "QPushButton:hover{background:#C62828;}"
            "QPushButton:disabled{background:#EF9A9A;}"
        )
        self._stop_btn.clicked.connect(self._stop)
        btn_row.addWidget(self._stop_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        # ── Progress ──────────────────────────────────────────────────────
        prog_group = QGroupBox("進捗")
        pg = QVBoxLayout(prog_group)
        self._prog = QProgressBar()
        self._prog.setMinimum(0)
        self._prog.setValue(0)
        pg.addWidget(self._prog)
        self._status_lbl = QLabel("待機中")
        pg.addWidget(self._status_lbl)
        root.addWidget(prog_group)

        # ── Log ───────────────────────────────────────────────────────────
        log_group = QGroupBox("ログ")
        lg = QVBoxLayout(log_group)
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        mono = "Menlo" if sys.platform == "darwin" else "Consolas"
        self._log.setFont(QFont(mono, 10))
        self._log.setStyleSheet("background:#FAFAFA; border:1px solid #E0E0E0;")
        lg.addWidget(self._log)
        root.addWidget(log_group, stretch=1)

    # ------------------------------------------------------------------

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self, self._cfg)
        if dlg.exec_() == QDialog.Accepted:
            self._cfg = dlg.get_config()
            _save_config(self._cfg)
            self._engine_lbl.setText(self._cfg["engine"].upper())

    def _pick_folder(self) -> None:
        p = QFileDialog.getExistingDirectory(self, "画像フォルダを選択")
        if p:
            self._folder.setText(p)

    def _pick_output(self) -> None:
        p, _ = QFileDialog.getSaveFileName(
            self, "出力Excelファイルを指定",
            str(Path.home() / "Downloads" / "shipping_info.xlsx"),
            "Excel (*.xlsx);;All (*.*)",
        )
        if p:
            self._output.setText(p)

    def _append_log(self, msg: str, tag: str = "info") -> None:
        colors = {
            "ok":   "#2e7d32",
            "warn": "#e65100",
            "err":  "#c62828",
            "info": "#37474f",
        }
        color = colors.get(tag, "#37474f")
        self._log.append(f'<span style="color:{color};">{msg}</span>')
        cursor = self._log.textCursor()
        cursor.movePosition(QTextCursor.End)
        self._log.setTextCursor(cursor)

    def _start(self) -> None:
        folder = self._folder.text().strip()
        out    = self._output.text().strip()

        if not folder:
            QMessageBox.warning(self, "警告", "画像フォルダを選択してください。")
            return
        if not os.path.isdir(folder):
            QMessageBox.critical(self, "エラー", f"フォルダが見つかりません:\n{folder}")
            return
        if not out:
            QMessageBox.warning(self, "警告", "出力ファイルパスを指定してください。")
            return

        engine     = self._cfg.get("engine", "tongyi")
        tongyi_key = self._cfg.get("tongyi_api_key") or os.environ.get("DASHSCOPE_API_KEY", "")
        doubao_key = self._cfg.get("doubao_api_key") or os.environ.get("ARK_API_KEY", "")

        if engine == "tongyi" and not tongyi_key:
            QMessageBox.critical(self, "エラー",
                "通义 APIキーが未設定です。\n[API設定] から入力してください。\n"
                "取得先: https://dashscope.aliyun.com/")
            return
        if engine == "doubao" and not doubao_key:
            QMessageBox.critical(self, "エラー",
                "豆包 APIキーが未設定です。\n[API設定] から入力してください。\n"
                "取得先: https://console.volcengine.com/ark/")
            return

        images = sorted(
            os.path.join(folder, f)
            for f in os.listdir(folder)
            if os.path.splitext(f)[1].lower() in _SUPPORTED_EXT
        )
        if not images:
            QMessageBox.warning(self, "警告",
                "画像ファイルが見つかりません（対応形式: jpg, jpeg, png）")
            return

        proxy = self._cfg.get("proxy", "").strip()

        kwargs: dict = {}
        if proxy:
            kwargs["proxy"] = proxy
        if engine == "tongyi":
            kwargs["api_key"] = tongyi_key
            kwargs["model"]   = self._cfg.get("tongyi_model", "qwen-vl-plus")
        elif engine == "doubao":
            kwargs["api_key"] = doubao_key
            kwargs["model"]   = self._cfg.get("doubao_model", "doubao-1-5-vision-pro-32k-250115")

        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._prog.setMaximum(len(images))
        self._prog.setValue(0)

        self._worker = Worker(engine, images, out, kwargs)
        self._worker.signals.log.connect(self._append_log)
        self._worker.signals.progress.connect(self._prog.setValue)
        self._worker.signals.status.connect(self._status_lbl.setText)
        self._worker.signals.done.connect(self._on_done)
        self._worker.start()

    def _stop(self) -> None:
        if self._worker:
            self._worker.stop()
        self._status_lbl.setText("停止しています…")

    def _on_done(self, records, out_path) -> None:
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._status_lbl.setText("完了")

        if not records:
            return

        try:
            write_excel(records, out_path)
            warn_count = sum(1 for r in records if r["status"] != "OK")

            tic_path = tic_output_path(out_path)
            write_tic_excel(records, tic_path)

            self._append_log(
                f"\n完了: {len(records)} 件処理 / 要確認: {warn_count} 件\n"
                f"出力1: {out_path}\n"
                f"出力2: {tic_path}\n",
                "ok",
            )
            QMessageBox.information(
                self, "解析完了",
                f"処理完了！\n\n"
                f"合計:   {len(records)} 件\n"
                f"要確認: {warn_count} 件\n\n"
                f"出力ファイル:\n{out_path}\n{tic_path}",
            )
        except Exception as exc:
            self._append_log(f"Excel書き込みエラー: {exc}", "err")
            QMessageBox.critical(self, "エラー", f"Excel保存に失敗しました:\n{exc}")


# ---------------------------------------------------------------------------

def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
