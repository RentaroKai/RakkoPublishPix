import sys
import os
import shutil
import json
from PIL import Image

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QGroupBox, QRadioButton, QLineEdit, QPushButton, QFileDialog, QTextEdit,
    QScrollBar, QSlider, QSpinBox, QDialog, QDialogButtonBox, QComboBox,
    QGridLayout, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QDesktopServices, QDragEnterEvent, QDropEvent, QPixmap

# ------------------------------------------------------
# 設定編集ダイアログ: パターン1（縮小率）用の例として作成
# 他のパターン用にも応用して作成可能
# ------------------------------------------------------
class EditPattern1Dialog(QDialog):
    def __init__(self, current_value, parent=None):
        super().__init__(parent)
        self.setWindowTitle("パターン1設定編集（X割減）")
        self.resize(300, 150)

        self.value = current_value

        main_layout = QVBoxLayout(self)

        # スライダーとスピンボックスを横並びに
        slider_layout = QHBoxLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(1, 100)  # 1%～100% で設定可能
        self.slider.setValue(self.value)
        self.spin = QSpinBox()
        self.spin.setRange(1, 100)
        self.spin.setValue(self.value)

        # スライダーとスピンボックスを連動
        self.slider.valueChanged.connect(self.spin.setValue)
        self.spin.valueChanged.connect(self.slider.setValue)

        slider_layout.addWidget(QLabel("縮小率(%)"))
        slider_layout.addWidget(self.slider)
        slider_layout.addWidget(self.spin)

        main_layout.addLayout(slider_layout)

        # OK/Cancel ボタン
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    def get_value(self):
        return self.spin.value()


# ------------------------------------------------------
# メインウィンドウ
# ------------------------------------------------------
class ImageResizeTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rakko publishPix - PySide6版")
        self.resize(1000, 600)

        # コンフィグを読み込み
        self.load_config()

        # -----------------------------
        # メインコンテンツの配置
        # -----------------------------
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        # 保存オプション
        save_option_group = self.create_save_option_group()
        main_layout.addWidget(save_option_group)

        # パターン一覧を並べる
        pattern_layout = QHBoxLayout()
        main_layout.addLayout(pattern_layout)

        # フレーム（パターン）を作成して配置
        # ドロップ対応させるために、カスタム QWidget を作るか、既存QLabelを拡張してもOK
        self.pattern_frames = {}
        for pattern_name, info in self.patterns().items():
            frame = self.create_pattern_frame(pattern_name, info)
            pattern_layout.addWidget(frame)
            self.pattern_frames[pattern_name] = frame

        # バックアップフォルダを開くボタン
        backup_layout = QHBoxLayout()
        main_layout.addLayout(backup_layout)
        backup_label = QLabel("バックアップフォルダ：")
        backup_layout.addWidget(backup_label)
        backup_button = QPushButton("開く")
        backup_button.clicked.connect(self.open_backup_folder)
        backup_layout.addWidget(backup_button)

        # ログ表示
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        main_layout.addWidget(self.log_text)

        # バックアップディレクトリの作成
        self.backup_dir = "backup_images"
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)

        self.log_message("画像ファイルを各パターン枠にドラッグ＆ドロップしてください。")

    # -----------------------------
    # パターンの辞書定義（色など）
    # -----------------------------
    def patterns(self):
        return {
            "パターン1X割減": {
                "color": "#c7b198",
                "desc": "画像を {resize_percentage}% に縮小",
                "func": self.pattern1_resize
            },
            "パターン2□mini": {
                "color": "#b9aa8f",
                "desc": "サイズ制限で縮小",
                "func": self.pattern2_resize
            },
            "パターン3↕": {
                "color": "#a1998e",
                "desc": "高さ {pattern3_height}px に合わせて幅を自動調整",
                "func": self.pattern3_resize
            },
            "パターン4⇔": {
                "color": "#8c8a93",
                "desc": "幅 {pattern4_max_width}px に合わせて高さを自動調整",
                "func": self.pattern4_resize
            },
            "透かし追加": {
                "color": "#7f7f7f",
                "desc": "位置:{position} 不透明度:{opacity}% で透かしを追加",
                "func": self.add_watermark
            },
        }

    # -----------------------------
    # 保存オプション
    # -----------------------------
    def create_save_option_group(self):
        group = QGroupBox("保存オプション")
        layout = QHBoxLayout(group)

        # ラジオボタン
        self.save_option_overwrite = QRadioButton("上書き保存")
        self.save_option_prefix = QRadioButton("プリフィクス追加")
        self.save_option_suffix = QRadioButton("サフィックス追加")

        # デフォルトは上書き
        self.save_option_overwrite.setChecked(True)

        layout.addWidget(self.save_option_overwrite)
        layout.addWidget(self.save_option_prefix)
        layout.addWidget(self.save_option_suffix)

        # Prefix/Suffix 用の入力欄
        self.prefix_edit = QLineEdit()
        self.prefix_edit.setPlaceholderText("prefix_")
        self.prefix_edit.setEnabled(False)

        self.suffix_edit = QLineEdit()
        self.suffix_edit.setPlaceholderText("_suffix")
        self.suffix_edit.setEnabled(False)

        layout.addWidget(self.prefix_edit)
        layout.addWidget(self.suffix_edit)

        # ラジオボタンが切り替わったら入力欄の有効/無効を切り替え
        self.save_option_overwrite.toggled.connect(self.toggle_prefix_suffix)
        self.save_option_prefix.toggled.connect(self.toggle_prefix_suffix)
        self.save_option_suffix.toggled.connect(self.toggle_prefix_suffix)

        return group

    def toggle_prefix_suffix(self):
        if self.save_option_prefix.isChecked():
            self.prefix_edit.setEnabled(True)
            self.suffix_edit.setEnabled(False)
        elif self.save_option_suffix.isChecked():
            self.prefix_edit.setEnabled(False)
            self.suffix_edit.setEnabled(True)
        else:
            self.prefix_edit.setEnabled(False)
            self.suffix_edit.setEnabled(False)

    # -----------------------------
    # パターン用フレームの作成
    # -----------------------------
    def create_pattern_frame(self, pattern_name, info):
        frame = DropFrame(parent=self)
        frame.setAcceptDrops(True)
        frame.pattern_name = pattern_name  # 後で使うために保持
        frame.func = info["func"]         # リサイズ等の処理関数

        # 背景色の明るさを計算して文字色を決定
        bg_color = info['color'].lstrip('#')
        r = int(bg_color[0:2], 16)
        g = int(bg_color[2:4], 16)
        b = int(bg_color[4:6], 16)
        brightness = (r * 299 + g * 587 + b * 114) / 1000  # 輝度計算
        text_color = '#000000' if brightness > 128 else '#FFFFFF'  # 明るい背景には黒字、暗い背景には白字

        frame.setStyleSheet(f"""
            QWidget {{
                background-color: {info['color']};
                color: {text_color};
                border-radius: 5px;
                padding: 10px;
            }}
            QLineEdit {{
                background-color: white;
                color: black;
                border: 1px solid #999;
                padding: 2px;
                min-width: 60px;
                max-width: 60px;
                font-size: 14px;
            }}
            QPushButton {{
                background-color: #f0f0f0;
                color: black;
                border: 1px solid #999;
                padding: 5px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: #e0e0e0;
            }}
            QLabel {{
                font-size: 14px;
            }}
        """)
        frame.setMinimumWidth(200)  # フレームの最小幅を設定

        vlayout = QVBoxLayout(frame)
        vlayout.setContentsMargins(10, 10, 10, 10)  # 余白を追加

        # タイトル
        title_label = QLabel(pattern_name)
        title_label.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {text_color};")
        vlayout.addWidget(title_label, alignment=Qt.AlignHCenter)

        # パターンごとの入力フィールドを作成
        if pattern_name == "パターン1X割減":
            value = self.config[pattern_name]["resize_percentage"]
            hlayout = QHBoxLayout()
            edit = QLineEdit(str(value))
            edit.setMaximumWidth(50)
            edit.setAlignment(Qt.AlignRight)
            edit.textChanged.connect(lambda text: self.validate_and_update(pattern_name, "resize_percentage", text, 1, 100))
            hlayout.addWidget(QLabel("縮小率:"))
            hlayout.addWidget(edit)
            hlayout.addWidget(QLabel("%"))
            vlayout.addLayout(hlayout)
        elif pattern_name == "パターン2□mini":
            w = self.config[pattern_name]["max_width"]
            h = self.config[pattern_name]["max_height"]
            grid = QGridLayout()
            edit_w = QLineEdit(str(w))
            edit_w.setMaximumWidth(50)
            edit_w.setAlignment(Qt.AlignRight)
            edit_w.textChanged.connect(lambda text: self.validate_and_update(pattern_name, "max_width", text, 1, 9999))
            edit_h = QLineEdit(str(h))
            edit_h.setMaximumWidth(50)
            edit_h.setAlignment(Qt.AlignRight)
            edit_h.textChanged.connect(lambda text: self.validate_and_update(pattern_name, "max_height", text, 1, 9999))
            grid.addWidget(QLabel("幅:"), 0, 0)
            grid.addWidget(edit_w, 0, 1)
            grid.addWidget(QLabel("px"), 0, 2)
            grid.addWidget(QLabel("高さ:"), 1, 0)
            grid.addWidget(edit_h, 1, 1)
            grid.addWidget(QLabel("px"), 1, 2)
            vlayout.addLayout(grid)
        elif pattern_name == "パターン3↕":
            value = self.config[pattern_name]["pattern3_height"]
            hlayout = QHBoxLayout()
            edit = QLineEdit(str(value))
            edit.setMaximumWidth(50)
            edit.setAlignment(Qt.AlignRight)
            edit.textChanged.connect(lambda text: self.validate_and_update(pattern_name, "pattern3_height", text, 1, 9999))
            hlayout.addWidget(QLabel("高さ:"))
            hlayout.addWidget(edit)
            hlayout.addWidget(QLabel("px"))
            vlayout.addLayout(hlayout)
        elif pattern_name == "パターン4⇔":
            value = self.config[pattern_name]["pattern4_max_width"]
            hlayout = QHBoxLayout()
            edit = QLineEdit(str(value))
            edit.setMaximumWidth(50)
            edit.setAlignment(Qt.AlignRight)
            edit.textChanged.connect(lambda text: self.validate_and_update(pattern_name, "pattern4_max_width", text, 1, 9999))
            hlayout.addWidget(QLabel("幅:"))
            hlayout.addWidget(edit)
            hlayout.addWidget(QLabel("px"))
            vlayout.addLayout(hlayout)
        elif pattern_name == "透かし追加":
            # 透かしの設定は複雑なので、設定編集ボタンを残す
            edit_button = QPushButton("設定編集")
            edit_button.clicked.connect(lambda: self.edit_config(pattern_name))
            vlayout.addWidget(edit_button, alignment=Qt.AlignHCenter)

        # 説明文
        desc = info["desc"].format(**self.config.get(pattern_name, {}))
        desc_label = QLabel(desc)
        desc_label.setWordWrap(True)
        vlayout.addWidget(desc_label, alignment=Qt.AlignHCenter)

        return frame

    def validate_and_update(self, pattern_name, key, text, min_val, max_val):
        """入力値を検証して、有効な場合のみ設定を更新する"""
        try:
            value = int(text)
            if min_val <= value <= max_val:
                self.update_config(pattern_name, key, value)
        except ValueError:
            pass  # 数値以外が入力された場合は無視

    def update_config(self, pattern_name, key, value):
        """設定値を更新し、設定ファイルに保存する"""
        self.config[pattern_name][key] = value
        self.save_config()
        # フレームの説明文を更新
        self.update_pattern_descriptions()

    # -----------------------------
    # コンフィグのロード／セーブ
    # -----------------------------
    def load_config(self):
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            # デフォルト値
            self.config = {
                "パターン1X割減": {"resize_percentage": 80},
                "パターン2□mini": {"max_width": 350, "max_height": 200},
                "パターン3↕": {"pattern3_height": 600},
                "パターン4⇔": {"pattern4_max_width": 800},
                "透かし追加": {
                    "watermark_image": "",
                    "position": "右下",
                    "opacity": 30  # 30%
                }
            }
            self.save_config()

    def save_config(self):
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    # -----------------------------
    # 設定編集の呼び出し
    # -----------------------------
    def edit_config(self, pattern_name):
        if pattern_name == "パターン1X割減":
            current_value = self.config[pattern_name]["resize_percentage"]
            dialog = EditPattern1Dialog(current_value=current_value, parent=self)
            if dialog.exec() == QDialog.Accepted:
                new_value = dialog.get_value()
                self.config[pattern_name]["resize_percentage"] = new_value
        elif pattern_name == "パターン2□mini":
            self.edit_pattern2_dialog()
        elif pattern_name == "パターン3↕":
            self.edit_pattern3_dialog()
        elif pattern_name == "パターン4⇔":
            self.edit_pattern4_dialog()
        elif pattern_name == "透かし追加":
            self.edit_watermark_dialog()

        self.save_config()
        # フレームの説明文を更新
        self.update_pattern_descriptions()

    def edit_pattern2_dialog(self):
        # 幅と高さをQSpinBoxで設定する例
        w = self.config["パターン2□mini"]["max_width"]
        h = self.config["パターン2□mini"]["max_height"]
        dlg = QDialog(self)
        dlg.setWindowTitle("パターン2 - 最大幅/高さ編集")
        layout = QVBoxLayout(dlg)

        grid = QGridLayout()
        layout.addLayout(grid)

        grid.addWidget(QLabel("最大幅(px):"), 0, 0)
        spin_w = QSpinBox()
        spin_w.setRange(1, 9999)
        spin_w.setValue(w)
        grid.addWidget(spin_w, 0, 1)

        grid.addWidget(QLabel("最大高さ(px):"), 1, 0)
        spin_h = QSpinBox()
        spin_h.setRange(1, 9999)
        spin_h.setValue(h)
        grid.addWidget(spin_h, 1, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        if dlg.exec() == QDialog.Accepted:
            self.config["パターン2□mini"]["max_width"] = spin_w.value()
            self.config["パターン2□mini"]["max_height"] = spin_h.value()

    def edit_pattern3_dialog(self):
        # 高さのみ
        val = self.config["パターン3↕"]["pattern3_height"]
        dlg = QDialog(self)
        dlg.setWindowTitle("パターン3 - 高さ編集")
        layout = QVBoxLayout(dlg)

        hbox = QHBoxLayout()
        layout.addLayout(hbox)

        hbox.addWidget(QLabel("高さ(px):"))
        spin = QSpinBox()
        spin.setRange(1, 9999)
        spin.setValue(val)
        hbox.addWidget(spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        if dlg.exec() == QDialog.Accepted:
            self.config["パターン3↕"]["pattern3_height"] = spin.value()

    def edit_pattern4_dialog(self):
        # 幅のみ
        val = self.config["パターン4⇔"]["pattern4_max_width"]
        dlg = QDialog(self)
        dlg.setWindowTitle("パターン4 - 幅編集")
        layout = QVBoxLayout(dlg)

        hbox = QHBoxLayout()
        layout.addLayout(hbox)

        hbox.addWidget(QLabel("最大幅(px):"))
        spin = QSpinBox()
        spin.setRange(1, 9999)
        spin.setValue(val)
        hbox.addWidget(spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        if dlg.exec() == QDialog.Accepted:
            self.config["パターン4⇔"]["pattern4_max_width"] = spin.value()

    def edit_watermark_dialog(self):
        # 透かし設定
        dlg = QDialog(self)
        dlg.setWindowTitle("透かし設定")
        layout = QVBoxLayout(dlg)

        grid = QGridLayout()
        layout.addLayout(grid)

        # 画像パス
        grid.addWidget(QLabel("透かし画像:"), 0, 0)
        path_edit = QLineEdit()
        path_edit.setText(self.config["透かし追加"]["watermark_image"])
        grid.addWidget(path_edit, 0, 1)
        browse_btn = QPushButton("参照")
        grid.addWidget(browse_btn, 0, 2)

        def on_browse():
            fname, _ = QFileDialog.getOpenFileName(self, "透かし画像を選択", "", "PNG Files (*.png)")
            if fname:
                path_edit.setText(fname)

        browse_btn.clicked.connect(on_browse)

        # 位置
        grid.addWidget(QLabel("位置:"), 1, 0)
        combo = QComboBox()
        positions = ["左上", "中央上", "右上", "左中央", "中央", "右中央", "左下", "中央下", "右下"]
        combo.addItems(positions)
        current_pos = self.config["透かし追加"]["position"]
        if current_pos in positions:
            combo.setCurrentText(current_pos)
        grid.addWidget(combo, 1, 1)

        # 不透明度
        grid.addWidget(QLabel("不透明度(%):"), 2, 0)
        opacity_spin = QSpinBox()
        opacity_spin.setRange(0, 100)
        opacity_spin.setValue(self.config["透かし追加"]["opacity"])
        grid.addWidget(opacity_spin, 2, 1)

        # OK/Cancel
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)

        if dlg.exec() == QDialog.Accepted:
            self.config["透かし追加"]["watermark_image"] = path_edit.text()
            self.config["透かし追加"]["position"] = combo.currentText()
            self.config["透かし追加"]["opacity"] = opacity_spin.value()

    # -----------------------------
    # パターン説明文の更新
    # -----------------------------
    def update_pattern_descriptions(self):
        for pattern_name, frame in self.pattern_frames.items():
            info = self.patterns()[pattern_name]
            desc_label = frame.findChild(QLabel, "")
            # findChild で最初に見つかったQLabelがタイトルかもしれないので
            # 2番目のQLabelが説明にあたる…というように工夫
            # ここでは単純化して、QLabel をすべて取得して2番目を更新してみる
            labels = frame.findChildren(QLabel)
            if len(labels) >= 2:
                new_desc = info["desc"].format(**self.config[pattern_name])
                labels[1].setText(new_desc)

    # -----------------------------
    # バックアップフォルダを開く
    # -----------------------------
    def open_backup_folder(self):
        backup_path = os.path.abspath("backup_images")
        QDesktopServices.openUrl(QUrl.fromLocalFile(backup_path))

    # -----------------------------
    # ログメッセージ追加
    # -----------------------------
    def log_message(self, msg):
        self.log_text.append(msg)

    # -----------------------------
    # リサイズ・透かし処理 (パターン別)
    # -----------------------------
    def pattern1_resize(self, file_path):
        # 例: 画像を縮小率でリサイズ
        resize_percentage = self.config["パターン1X割減"]["resize_percentage"]
        image = Image.open(file_path)
        new_size = (
            int(image.width * resize_percentage / 100),
            int(image.height * resize_percentage / 100)
        )
        name, ext = os.path.splitext(file_path)
        temp_path = name + "_temp" + ext
        resized = image.resize(new_size, Image.Resampling.LANCZOS)
        resized.save(temp_path)
        image.close()
        resized.close()
        return temp_path

    def pattern2_resize(self, file_path):
        max_width = self.config["パターン2□mini"]["max_width"]
        max_height = self.config["パターン2□mini"]["max_height"]
        image = Image.open(file_path)
        image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        name, ext = os.path.splitext(file_path)
        temp_path = name + "_temp" + ext
        image.save(temp_path)
        image.close()
        return temp_path

    def pattern3_resize(self, file_path):
        pattern3_height = self.config["パターン3↕"]["pattern3_height"]
        image = Image.open(file_path)
        ratio = pattern3_height / image.height
        new_width = int(image.width * ratio)
        resized = image.resize((new_width, pattern3_height), Image.Resampling.LANCZOS)
        name, ext = os.path.splitext(file_path)
        temp_path = name + "_temp" + ext
        resized.save(temp_path)
        image.close()
        resized.close()
        return temp_path

    def pattern4_resize(self, file_path):
        max_w = self.config["パターン4⇔"]["pattern4_max_width"]
        image = Image.open(file_path)
        if image.width > max_w:
            ratio = max_w / image.width
            new_height = int(image.height * ratio)
            resized = image.resize((max_w, new_height), Image.Resampling.LANCZOS)
            name, ext = os.path.splitext(file_path)
            temp_path = name + "_temp" + ext
            resized.save(temp_path)
            image.close()
            resized.close()
            return temp_path
        else:
            self.log_message(f"{os.path.basename(file_path)} は幅 {max_w}px 以下なのでリサイズ不要")
            return file_path

    def add_watermark(self, file_path):
        watermark_info = self.config["透かし追加"]
        wm_path = watermark_info["watermark_image"]
        if not wm_path or not os.path.exists(wm_path):
            self.log_message("透かし画像が指定されていないか存在しません。")
            return file_path

        position = watermark_info["position"]
        opacity = watermark_info["opacity"]

        image = Image.open(file_path).convert("RGBA")
        wm = Image.open(wm_path).convert("RGBA")

        # 透かしの透明度を調整
        alpha = int(255 * (opacity / 100))
        wm.putalpha(alpha)

        x, y = self.calculate_position(image.size, wm.size, position)

        image.paste(wm, (x, y), wm)
        image = image.convert("RGB")

        name, ext = os.path.splitext(file_path)
        temp_path = name + "_temp" + ext
        image.save(temp_path)
        image.close()
        wm.close()
        return temp_path

    def calculate_position(self, img_size, wm_size, position_text):
        """
        位置指定文字列（例: "右上", "左中央" など）から (x, y) を計算して返す。
        """
        img_w, img_h = img_size
        wm_w, wm_h = wm_size

        # 水平方向
        if "左" in position_text:
            x = 0
        elif "右" in position_text:
            x = img_w - wm_w
        else:
            x = (img_w - wm_w) // 2

        # 垂直方向
        if "上" in position_text:
            y = 0
        elif "下" in position_text:
            y = img_h - wm_h
        else:
            y = (img_h - wm_h) // 2

        return x, y

    # -----------------------------
    # ファイルを処理し保存する
    # -----------------------------
    def process_image(self, file_path, func):
        # まずバックアップ
        basename = os.path.basename(file_path)
        shutil.copy(file_path, os.path.join(self.backup_dir, basename))

        # 処理（リサイズや透かしなど）
        processed_path = func(file_path)

        # 保存オプションに応じてファイル名を決定
        final_path = file_path  # デフォルトは上書き
        if self.save_option_overwrite.isChecked():
            # 上書き
            shutil.move(processed_path, file_path)
            final_path = file_path
        elif self.save_option_prefix.isChecked():
            prefix = self.prefix_edit.text()
            dirname = os.path.dirname(file_path)
            new_name = prefix + basename
            final_path = os.path.join(dirname, new_name)
            shutil.move(processed_path, final_path)
        elif self.save_option_suffix.isChecked():
            suffix = self.suffix_edit.text()
            dirname = os.path.dirname(file_path)
            name, ext = os.path.splitext(basename)
            new_name = name + suffix + ext
            final_path = os.path.join(dirname, new_name)
            shutil.move(processed_path, final_path)

        self.log_message(f"{basename} を保存しました: {final_path}")


# ------------------------------------------------------
# ドロップを受け付けるためのフレーム
# ------------------------------------------------------
class DropFrame(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_tool = parent  # 親の ImageResizeTool 参照
        self.pattern_name = ""
        self.func = None

    def dragEnterEvent(self, event: QDragEnterEvent):
        # デバッグログを追加
        self.parent_tool.log_message("dragEnterEvent triggered")
        # 画像ファイルなら受け付ける
        if event.mimeData().hasUrls():
            # 一つでも画像拡張子を含むなら受け付ける
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                self.parent_tool.log_message(f"Checking file: {file_path}")
                if os.path.isfile(file_path) and file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                    event.acceptProposedAction()
                    self.parent_tool.log_message("File accepted")
                    return
        self.parent_tool.log_message("File ignored")
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        self.parent_tool.log_message("dropEvent triggered")
        urls = event.mimeData().urls()
        for url in urls:
            file_path = url.toLocalFile()
            self.parent_tool.log_message(f"Processing file: {file_path}")
            if os.path.isfile(file_path) and file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                # 親ウィンドウの process_image を呼ぶ
                self.parent_tool.process_image(file_path, self.func)
        event.acceptProposedAction()


# ------------------------------------------------------
# メイン実行
# ------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageResizeTool()
    window.show()
    sys.exit(app.exec())
