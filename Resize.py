import os
import shutil
import json
from PIL import Image
import tkinter as tk
from tkinter import filedialog, simpledialog
from tkinterdnd2 import DND_FILES, TkinterDnD

class ImageResizeTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Rakko publishPix")
        
        self.load_config()
        
        # 新しい保存オプションを追加
        self.save_option = tk.StringVar(value="overwrite")  # 'overwrite', 'prefix', 'suffix'
        self.prefix = tk.StringVar()
        self.suffix = tk.StringVar()
        
        self.patterns = {
            "パターン1X割減": {
                "color": "#c7b198",
                "func": self.pattern1_resize,
                "description": f"画像を{self.config['パターン1X割減']['resize_percentage']}%に縮小"
            },
            "パターン2□mini": {
                "color": "#b9aa8f",
                "func": self.pattern2_resize,
                "description": f"最大幅{self.config['パターン2□mini']['max_width']}px、最大高さ{self.config['パターン2□mini']['max_height']}pxに縮小"
            },
            "パターン3↕": {
                "color": "#a1998e",
                "func": self.pattern3_resize,
                "description": f"高さ{self.config['パターン3↕']['pattern3_height']}pxに合わせて幅を自動調整"
            },
            "パターン4⇔": {
                "color": "#8c8a93",
                "func": self.pattern4_resize,
                "description": f"幅{self.config['パターン4⇔']['pattern4_max_width']}pxに合わせて高さを自動調整"
            },
            "透かし追加": {
                "color": "#7f7f7f",
                "func": self.add_watermark,
                "description": "画像に透かしを追加"
            }
        }

        self.backup_dir = "backup_images"
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
        
        self.create_save_options()
        self.create_widgets()
        self.create_backup_link()
        self.create_log_area()
        self.log_message("領域にファイルをドラッグアンドドロップしてください。リサイズして上書きします。元のファイルはバックアップフォルダに移動します。")

    def create_save_options(self):
        save_frame = tk.LabelFrame(self.root, text="保存オプション", padx=10, pady=10)
        save_frame.grid(row=0, column=0, columnspan=len(self.patterns), padx=5, pady=5, sticky="ew")
        
        # ラジオボタン
        overwrite_rb = tk.Radiobutton(save_frame, text="上書き保存", variable=self.save_option, value="overwrite")
        overwrite_rb.grid(row=0, column=0, sticky="w")
        
        prefix_rb = tk.Radiobutton(save_frame, text="プリフィクスを追加して保存", variable=self.save_option, value="prefix")
        prefix_rb.grid(row=1, column=0, sticky="w")
        
        suffix_rb = tk.Radiobutton(save_frame, text="サフィクスを追加して保存", variable=self.save_option, value="suffix")
        suffix_rb.grid(row=2, column=0, sticky="w")
        
        # プリフィクス入力
        self.prefix_entry = tk.Entry(save_frame, textvariable=self.prefix)
        self.prefix_entry.grid(row=1, column=1, padx=5)
        self.prefix_entry.config(state="disabled")
        
        # サフィクス入力
        self.suffix_entry = tk.Entry(save_frame, textvariable=self.suffix)
        self.suffix_entry.grid(row=2, column=1, padx=5)
        self.suffix_entry.config(state="disabled")
        
        # ラジオボタンの状態変更を監視
        self.save_option.trace_add("write", self.toggle_save_entries)
        
    def toggle_save_entries(self, *args):
        option = self.save_option.get()
        if option == "prefix":
            self.prefix_entry.config(state="normal")
            self.suffix_entry.config(state="disabled")
        elif option == "suffix":
            self.suffix_entry.config(state="normal")
            self.prefix_entry.config(state="disabled")
        else:
            self.prefix_entry.config(state="disabled")
            self.suffix_entry.config(state="disabled")

    def process_image(self, file_path, pattern):
        # バックアップを保存
        shutil.copy(file_path, self.backup_dir)
        # リサイズ処理
        processed_path = self.patterns[pattern]["func"](file_path)
        # リネームまたは上書き保存
        save_option = self.save_option.get()
        if save_option == "overwrite":
            final_path = file_path
            # 上書き保存の場合、一時ファイルを直接元のファイルに上書き
            shutil.move(processed_path, final_path)
        elif save_option == "prefix":
            prefix = self.prefix.get()
            dirname, basename = os.path.split(file_path)
            final_path = os.path.join(dirname, f"{prefix}{basename}")
            shutil.move(processed_path, final_path)
        elif save_option == "suffix":
            suffix = self.suffix.get()
            dirname, basename = os.path.split(file_path)
            name, ext = os.path.splitext(basename)
            final_path = os.path.join(dirname, f"{name}{suffix}{ext}")
            shutil.move(processed_path, final_path)
        else:
            final_path = file_path  # デフォルトは上書き
        
        # 保存処理
        self.log_message(f"{os.path.basename(file_path)} を保存しました: {final_path}")

    def pattern1_resize(self, file_path):
        image = Image.open(file_path)
        resize_percentage = self.config["パターン1X割減"]["resize_percentage"]
        new_size = tuple([int(x * resize_percentage / 100) for x in image.size])
        resized_image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        # 上書き保存または別名保存のために一時ファイルを使用
        temp_path = f"{file_path}.temp{os.path.splitext(file_path)[1]}"
        resized_image.save(temp_path)
        image.close()
        resized_image.close()
        return temp_path

    def pattern2_resize(self, file_path):
        image = Image.open(file_path)
        max_width = self.config["パターン2□mini"]["max_width"]
        max_height = self.config["パターン2□mini"]["max_height"]
        image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # 上書き保存または別名保存のために一時ファイルを使用
        temp_path = f"{file_path}.temp{os.path.splitext(file_path)[1]}"
        image.save(temp_path)
        image.close()
        return temp_path

    def pattern3_resize(self, file_path):
        image = Image.open(file_path)
        pattern3_height = self.config["パターン3↕"]["pattern3_height"]
        ratio = pattern3_height / image.height
        new_width = int(image.width * ratio)
        resized_image = image.resize((new_width, pattern3_height), Image.Resampling.LANCZOS)
        
        # 上書き保存または別名保存のために一時ファイルを使用
        temp_path = f"{file_path}.temp{os.path.splitext(file_path)[1]}"
        resized_image.save(temp_path)
        image.close()
        resized_image.close()
        return temp_path

    def pattern4_resize(self, file_path):
        image = Image.open(file_path)
        pattern4_max_width = self.config["パターン4⇔"]["pattern4_max_width"]
        if image.width > pattern4_max_width:
            ratio = pattern4_max_width / image.width
            new_height = int(image.height * ratio)
            resized_image = image.resize((pattern4_max_width, new_height), Image.Resampling.LANCZOS)
            
            # 上書き保存または別名保存のために一時ファイルを使用
            temp_path = f"{file_path}.temp{os.path.splitext(file_path)[1]}"
            resized_image.save(temp_path)
            image.close()
            resized_image.close()
            return temp_path
        else:
            self.log_message(f"{os.path.basename(file_path)} は既に{pattern4_max_width}ピクセル以下なのでリサイズは不要です。")
            return file_path

    def add_watermark(self, file_path):
        image = Image.open(file_path).convert("RGBA")
        watermark_path = self.config["透かし追加"]["watermark_image"]
        
        if not watermark_path or not os.path.exists(watermark_path):
            self.log_message(f"エラー: 透かし画像が指定されていないか、見つかりません: {watermark_path}")
            image.close()
            return file_path  # 元の画像パスをそのまま返す

        watermark = Image.open(watermark_path).convert("RGBA")
        position = self.config["透かし追加"]["position"]
        opacity = int(self.config["透かし追加"]["opacity"] * 255 / 100)

        # 透明度を適用
        watermark.putalpha(opacity)

        # 位置を計算
        x = self.calculate_position(image.width, watermark.width, position, axis='x')
        y = self.calculate_position(image.height, watermark.height, position, axis='y')

        # 透かしを追加
        image.paste(watermark, (x, y), watermark)
        image = image.convert("RGB")  # 必要に応じてRGBに変換
        
        # 上書き保存または別名保存のために一時ファイルを使用
        temp_path = f"{file_path}.temp{os.path.splitext(file_path)[1]}"
        image.save(temp_path)
        image.close()
        watermark.close()
        return temp_path

    def calculate_position(self, image_size, watermark_size, position, axis):
        alignment = {
            '左': 0,
            '中央': (image_size - watermark_size) // 2,
            '右': image_size - watermark_size
        }
        if axis == 'x':
            if "左" in position:
                return alignment['左']
            elif "右" in position:
                return alignment['右']
            else:
                return alignment['中央']
        else:
            if "上" in position:
                return alignment['左']
            elif "下" in position:
                return alignment['右']
            else:
                return alignment['中央']

    def create_widgets(self):
        self.frames = {}
        for idx, (pattern, info) in enumerate(self.patterns.items()):
            frame = tk.LabelFrame(self.root, text=pattern, bg=info["color"], width=200, height=200)
            frame.grid(row=1, column=idx, padx=5, pady=5, sticky="nsew")
            frame.drop_target_register(DND_FILES)
            frame.dnd_bind('<<Drop>>', lambda e, p=pattern: self.drop(e, p))
            self.frames[pattern] = frame

            desc_text = tk.Text(frame, bg=info["color"], wrap=tk.WORD, height=4, width=25)
            desc_text.pack(padx=10, pady=10)
            desc_text.tag_configure("bold", font=("TkDefaultFont", 12, "bold"))
            self.update_description(pattern, desc_text)

            edit_button = tk.Button(frame, text="設定編集", command=lambda p=pattern: self.edit_config(p))
            edit_button.pack(padx=10, pady=5)

    def edit_config(self, pattern):
        if pattern == "パターン1X割減":
            new_value = simpledialog.askinteger("設定編集", "縮小率を入力してください（%）:", 
                                                initialvalue=self.config[pattern]['resize_percentage'])
            if new_value is not None:
                self.config[pattern]['resize_percentage'] = new_value
        elif pattern == "パターン2□mini":
            new_width = simpledialog.askinteger("設定編集", "最大幅を入力してください（px）:", 
                                                initialvalue=self.config[pattern]['max_width'])
            new_height = simpledialog.askinteger("設定編集", "最大高さを入力してください（px）:", 
                                                 initialvalue=self.config[pattern]['max_height'])
            if new_width is not None and new_height is not None:
                self.config[pattern]['max_width'] = new_width
                self.config[pattern]['max_height'] = new_height
        elif pattern == "パターン3↕":
            new_value = simpledialog.askinteger("設定編集", "高さを入力してください（px）:", 
                                                initialvalue=self.config[pattern]['pattern3_height'])
            if new_value is not None:
                self.config[pattern]['pattern3_height'] = new_value
        elif pattern == "パターン4⇔":
            new_value = simpledialog.askinteger("設定編集", "最大幅を入力してください（px）:", 
                                                initialvalue=self.config[pattern]['pattern4_max_width'])
            if new_value is not None:
                self.config[pattern]['pattern4_max_width'] = new_value
        elif pattern == "透かし追加":
            self.edit_watermark_config()

        self.save_config()
        self.update_descriptions()

    def edit_watermark_config(self):
        watermark_window = tk.Toplevel(self.root)
        watermark_window.title("透かし設定")
        watermark_window.transient(self.root)  # 親ウィンドウとの関係を設定
        watermark_window.grab_set()  # フォーカスを維持

        tk.Label(watermark_window, text="透かし画像:").grid(row=0, column=0, sticky="e")
        image_path = tk.Entry(watermark_window, width=50)
        image_path.grid(row=0, column=1)
        image_path.insert(0, self.config["透かし追加"]["watermark_image"])
        tk.Button(watermark_window, text="参照", command=lambda: self.browse_watermark(image_path)).grid(row=0, column=2)

        tk.Label(watermark_window, text="位置:").grid(row=1, column=0, sticky="e")
        position_var = tk.StringVar(value=self.config["透かし追加"]["position"])
        positions = ["左上", "中央上", "右上", "左中央", "中央", "右中央", "左下", "中央下", "右下"]
        position_menu = tk.OptionMenu(watermark_window, position_var, *positions)
        position_menu.grid(row=1, column=1, sticky="w")

        tk.Label(watermark_window, text="不透明度 (%):").grid(row=2, column=0, sticky="e")
        opacity_var = tk.DoubleVar(value=self.config["透かし追加"]["opacity"])
        opacity_scale = tk.Scale(watermark_window, from_=0, to=100, orient=tk.HORIZONTAL, variable=opacity_var, resolution=0.1)
        opacity_scale.grid(row=2, column=1, sticky="we")

        tk.Button(watermark_window, text="保存", command=lambda: self.save_watermark_config(
            image_path.get(), position_var.get(), opacity_var.get(), watermark_window
        )).grid(row=3, column=1)

        # ウィンドウが閉じられたときの処理を追加
        watermark_window.protocol("WM_DELETE_WINDOW", lambda: self.on_watermark_window_close(watermark_window))

    def on_watermark_window_close(self, window):
        window.grab_release()  # グラブを解放
        window.destroy()

    def browse_watermark(self, entry):
        filename = filedialog.askopenfilename(filetypes=[("PNG files", "*.png")])
        if filename:
            entry.delete(0, tk.END)
            entry.insert(0, filename)

    def save_watermark_config(self, image_path, position, opacity, window):
        self.config["透かし追加"]["watermark_image"] = image_path
        self.config["透かし追加"]["position"] = position
        self.config["透かし追加"]["opacity"] = opacity
        self.save_config()
        self.update_descriptions()
        window.grab_release()  # グラブを解放
        window.destroy()

    def update_descriptions(self):
        for pattern, info in self.patterns.items():
            desc_text = self.frames[pattern].winfo_children()[0]
            self.update_description(pattern, desc_text)

    def update_description(self, pattern, desc_text):
        desc_text.config(state=tk.NORMAL)
        desc_text.delete("1.0", tk.END)
        if pattern == "パターン1X割減":
            desc_text.insert(tk.END, "画像を")
            desc_text.insert(tk.END, f"{self.config[pattern]['resize_percentage']}%", "bold")
            desc_text.insert(tk.END, "に縮小")
        elif pattern == "パターン2□mini":
            desc_text.insert(tk.END, "最大幅")
            desc_text.insert(tk.END, f"{self.config[pattern]['max_width']}px", "bold")
            desc_text.insert(tk.END, "、最大高さ")
            desc_text.insert(tk.END, f"{self.config[pattern]['max_height']}px", "bold")
            desc_text.insert(tk.END, "に縮小")
        elif pattern == "パターン3↕":
            desc_text.insert(tk.END, "高さ")
            desc_text.insert(tk.END, f"{self.config[pattern]['pattern3_height']}px", "bold")
            desc_text.insert(tk.END, "に合わせて幅を自動調整")
        elif pattern == "パターン4⇔":
            desc_text.insert(tk.END, "幅")
            desc_text.insert(tk.END, f"{self.config[pattern]['pattern4_max_width']}px", "bold")
            desc_text.insert(tk.END, "に合わせて高さを自動調整")
        elif pattern == "透かし追加":
            desc_text.insert(tk.END, "透かし画像を追加\n")
            desc_text.insert(tk.END, f"位置: {self.config[pattern]['position']}\n", "bold")
            desc_text.insert(tk.END, f"不透明度: {self.config[pattern]['opacity']}%", "bold")
        desc_text.config(state=tk.DISABLED)

    def drop(self, event, pattern):
        files = self.root.tk.splitlist(event.data)
        for file in files:
            if os.path.isfile(file) and file.lower().endswith(('.png', '.jpg', '.jpeg')):
                self.process_image(file, pattern)

    def load_config(self):
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            self.config = {
                "パターン1X割減": {"resize_percentage": 80},
                "パターン2□mini": {"max_width": 350, "max_height": 200},
                "パターン3↕": {"pattern3_height": 600},
                "パターン4⇔": {"pattern4_max_width": 800},
                "透かし追加": {
                    "watermark_image": "",
                    "position": "右下",
                    "opacity": 0.3  # デフォルトの透明度を0.3%に設定
                }
            }
            self.save_config()

    def save_config(self):
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def create_backup_link(self):
        backup_frame = tk.Frame(self.root)
        backup_frame.grid(row=2, column=0, columnspan=len(self.patterns), pady=10)

        backup_label = tk.Label(backup_frame, text="バックアップフォルダ：")
        backup_label.pack(side=tk.LEFT)

        backup_path = os.path.abspath(self.backup_dir)
        backup_button = tk.Button(backup_frame, text="開く", command=lambda: os.startfile(backup_path))
        backup_button.pack(side=tk.LEFT)

    def create_log_area(self):
        self.log_frame = tk.Frame(self.root)
        self.log_frame.grid(row=3, column=0, columnspan=len(self.patterns), pady=10, sticky="ew")

        self.log_text = tk.Text(self.log_frame, height=5, width=80, wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(self.log_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

    def log_message(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = ImageResizeTool(root)
    root.mainloop()