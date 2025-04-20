"""
画像連結アプリケーション
- 複数の画像を指定した方向に連結
- 連結方向: 上から下、右から左、左から右、ジグザグ(左右交互、2行)
- 画像間に10pxの黒い帯を追加
- ファイル名から時系列順にソート
"""

import os
import re
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk, ImageDraw
import datetime
from functools import cmp_to_key
from threading import Thread

class ImageConcatenator:
    """画像連結の核となるロジッククラス"""

    def __init__(self, image_paths=None, output_path=None, 
                 direction="vertical", boundary_size=10):
        """
        初期化メソッド
        
        Parameters:
        -----------
        image_paths : list
            連結する画像ファイルのパスリスト
        output_path : str
            出力画像のパス
        direction : str
            連結方向 ("vertical", "right_to_left", "left_to_right", "zigzag")
        boundary_size : int
            画像間の境界線のサイズ (px)
        """
        self.image_paths = image_paths or []
        self.output_path = output_path
        self.direction = direction
        self.boundary_size = boundary_size
        
        # 処理状態
        self.is_processing = False
        self.stop_requested = False
        
        # コールバック関数
        self.progress_callback = None
        self.completion_callback = None
    
    def set_callbacks(self, progress_callback=None, completion_callback=None):
        """コールバック関数を設定"""
        self.progress_callback = progress_callback
        self.completion_callback = completion_callback
    
    def sort_images_by_timestamp(self):
        """ファイル名から時系列でソート"""
        def extract_time_info(file_path):
            """ファイル名から時間情報を抽出"""
            filename = os.path.basename(file_path)
            
            # frame_000123_0-00-05.jpg 形式のファイル名を想定
            time_match = re.search(r'_(\d+-\d+-\d+)', filename)
            frame_match = re.search(r'_(\d+)_', filename)
            
            if time_match:
                time_str = time_match.group(1).replace('-', ':')
                try:
                    time_obj = datetime.datetime.strptime(time_str, '%H:%M:%S')
                    seconds = time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second
                    return seconds
                except:
                    pass
            
            if frame_match:
                try:
                    return int(frame_match.group(1))
                except:
                    pass
            
            # フォールバック: ファイル作成日時を使用
            return os.path.getctime(file_path)
        
        def compare_images(a, b):
            """画像の比較関数"""
            time_a = extract_time_info(a)
            time_b = extract_time_info(b)
            return (time_a > time_b) - (time_a < time_b)
        
        # 画像をソート
        sorted_paths = sorted(self.image_paths, key=cmp_to_key(compare_images))
        return sorted_paths
    
    def concatenate_images(self):
        """指定された方向に画像を連結"""
        if not self.image_paths or not self.output_path:
            return False
        
        try:
            # 画像を時系列でソート
            sorted_paths = self.sort_images_by_timestamp()
            
            # 画像を読み込む
            images = []
            total_width = 0
            total_height = 0
            max_width = 0
            max_height = 0
            
            # 進捗情報
            total_files = len(sorted_paths)
            current_file = 0
            
            for img_path in sorted_paths:
                current_file += 1
                
                if self.stop_requested:
                    break
                
                try:
                    img = Image.open(img_path)
                    images.append(img)
                    
                    # 最大サイズを更新
                    max_width = max(max_width, img.width)
                    max_height = max(max_height, img.height)
                    
                    # 合計サイズを計算
                    total_width += img.width
                    total_height += img.height
                    
                    # 進捗通知
                    if self.progress_callback:
                        progress = (current_file / total_files) * 40  # 40%: 画像読み込み
                        self.progress_callback(progress, f"画像を読み込み中 ({current_file}/{total_files})")
                
                except Exception as e:
                    if self.completion_callback:
                        self.completion_callback(False, f"画像の読み込みエラー: {str(e)}")
                    return False
            
            if self.stop_requested:
                if self.completion_callback:
                    self.completion_callback(False, "処理が中断されました")
                return False
            
            # 方向に応じて新しい画像を作成
            if self.direction == "vertical":  # 上から下
                # 10pxの境界線を考慮
                result_width = max_width
                result_height = total_height + (len(images) - 1) * self.boundary_size
                
                result = Image.new('RGB', (result_width, result_height), color='black')
                draw = ImageDraw.Draw(result)
                
                y_offset = 0
                for i, img in enumerate(images):
                    # 水平方向中央揃え
                    x_offset = (result_width - img.width) // 2
                    
                    result.paste(img, (x_offset, y_offset))
                    y_offset += img.height + self.boundary_size
                    
                    # 進捗通知
                    if self.progress_callback:
                        progress = 40 + (i / len(images)) * 60  # 40-100%: 画像処理
                        self.progress_callback(progress, f"画像を連結中 ({i+1}/{len(images)})")
            
            elif self.direction == "left_to_right":  # 左から右
                # 10pxの境界線を考慮
                result_width = total_width + (len(images) - 1) * self.boundary_size
                result_height = max_height
                
                result = Image.new('RGB', (result_width, result_height), color='black')
                draw = ImageDraw.Draw(result)
                
                x_offset = 0
                for i, img in enumerate(images):
                    # 垂直方向中央揃え
                    y_offset = (result_height - img.height) // 2
                    
                    result.paste(img, (x_offset, y_offset))
                    x_offset += img.width + self.boundary_size
                    
                    # 進捗通知
                    if self.progress_callback:
                        progress = 40 + (i / len(images)) * 60
                        self.progress_callback(progress, f"画像を連結中 ({i+1}/{len(images)})")
            
            elif self.direction == "right_to_left":  # 右から左
                # まず左から右に連結してから水平反転
                result_width = total_width + (len(images) - 1) * self.boundary_size
                result_height = max_height
                
                result = Image.new('RGB', (result_width, result_height), color='black')
                draw = ImageDraw.Draw(result)
                
                x_offset = 0
                for i, img in enumerate(reversed(images)):  # 逆順に配置
                    # 垂直方向中央揃え
                    y_offset = (result_height - img.height) // 2
                    
                    result.paste(img, (x_offset, y_offset))
                    x_offset += img.width + self.boundary_size
                    
                    # 進捗通知
                    if self.progress_callback:
                        progress = 40 + (i / len(images)) * 60
                        self.progress_callback(progress, f"画像を連結中 ({i+1}/{len(images)})")
            
            elif self.direction == "zigzag":  # ジグザグ（左、右、左、右...）
                # 画像を2行に分ける
                half_count = (len(images) + 1) // 2  # 奇数の場合は1行目が多くなる
                first_row = images[:half_count]
                second_row = images[half_count:]
                
                # 各行の幅と高さを計算
                first_row_width = sum(img.width for img in first_row) + (len(first_row) - 1) * self.boundary_size
                second_row_width = sum(img.width for img in second_row) + (len(second_row) - 1) * self.boundary_size if second_row else 0
                
                max_row_width = max(first_row_width, second_row_width)
                max_first_row_height = max(img.height for img in first_row) if first_row else 0
                max_second_row_height = max(img.height for img in second_row) if second_row else 0
                
                # 結果画像のサイズを計算
                result_width = max_row_width
                result_height = max_first_row_height + max_second_row_height + self.boundary_size if second_row else max_first_row_height
                
                result = Image.new('RGB', (result_width, result_height), color='black')
                draw = ImageDraw.Draw(result)
                
                # 1行目（左から右）
                x_offset = 0
                for i, img in enumerate(first_row):
                    result.paste(img, (x_offset, 0))
                    x_offset += img.width + self.boundary_size
                    
                    # 進捗通知
                    if self.progress_callback:
                        progress = 40 + (i / len(images)) * 30
                        self.progress_callback(progress, f"1行目を連結中 ({i+1}/{len(first_row)})")
                
                # 2行目（右から左）
                if second_row:
                    x_offset = result_width - second_row[0].width
                    y_offset = max_first_row_height + self.boundary_size
                    
                    for i, img in enumerate(second_row):
                        result.paste(img, (x_offset, y_offset))
                        x_offset -= (img.width + self.boundary_size)
                        
                        # 進捗通知
                        if self.progress_callback:
                            progress = 70 + (i / len(images)) * 30
                            self.progress_callback(progress, f"2行目を連結中 ({i+1}/{len(second_row)})")
            
            # 結果を保存
            result.save(self.output_path)
            
            if self.completion_callback:
                self.completion_callback(True, f"画像の連結が完了しました: {self.output_path}")
            
            return True
        
        except Exception as e:
            if self.completion_callback:
                self.completion_callback(False, f"画像の連結エラー: {str(e)}")
            return False
    
    def start_concatenation(self):
        """別スレッドで連結処理を開始"""
        if self.is_processing:
            return False
        
        self.is_processing = True
        self.stop_requested = False
        
        concatenation_thread = Thread(target=self.concatenate_images)
        concatenation_thread.daemon = True
        concatenation_thread.start()
        return True
    
    def stop_concatenation(self):
        """連結処理の停止を要求"""
        self.stop_requested = True


class ImageConcatenatorApp:
    """画像連結アプリケーションのUIクラス"""
    
    def __init__(self, root):
        """
        初期化メソッド
        
        Parameters:
        -----------
        root : tk.Tk
            tkinterのルートウィンドウ
        """
        self.root = root
        self.root.title("画像連結ツール")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # スタイル設定
        self.style = ttk.Style()
        self.style.configure("TButton", font=("Helvetica", 12))
        self.style.configure("TLabel", font=("Helvetica", 12))
        self.style.configure("TRadiobutton", font=("Helvetica", 12))
        
        # 選択された画像ファイルのリスト
        self.image_paths = []
        
        # UI作成
        self.create_widgets()
        
        # 処理ステータス
        self.processing = False
        
        # 画像連結クラス
        self.concatenator = ImageConcatenator()
    
    def create_widgets(self):
        """UIウィジェットの作成"""
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # ファイル選択フレーム
        file_frame = ttk.LabelFrame(main_frame, text="ファイル選択", padding="10")
        file_frame.pack(fill=tk.X, pady=5)
        
        # 画像ファイル選択ボタン
        ttk.Button(file_frame, text="画像ファイルを選択", command=self.browse_images).grid(row=0, column=0, pady=5)
        
        # 選択されたファイル数表示
        self.file_count_var = tk.StringVar(value="選択されたファイル: 0")
        ttk.Label(file_frame, textvariable=self.file_count_var).grid(row=0, column=1, pady=5, padx=10)
        
        # 選択ファイルクリアボタン
        ttk.Button(file_frame, text="選択をクリア", command=self.clear_selection).grid(row=0, column=2, pady=5)
        
        # ファイルリスト表示エリア
        list_frame = ttk.Frame(file_frame)
        list_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # スクロールバー付きリストボックス
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.file_listbox = tk.Listbox(list_frame, height=8, width=80, yscrollcommand=scrollbar.set)
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.file_listbox.yview)
        
        # 連結設定フレーム
        settings_frame = ttk.LabelFrame(main_frame, text="連結設定", padding="10")
        settings_frame.pack(fill=tk.X, pady=5)
        
        # 連結方向選択
        ttk.Label(settings_frame, text="連結方向:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.direction_var = tk.StringVar(value="vertical")
        
        ttk.Radiobutton(settings_frame, text="上から下", variable=self.direction_var,
                        value="vertical").grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Radiobutton(settings_frame, text="左から右", variable=self.direction_var,
                        value="left_to_right").grid(row=0, column=2, sticky=tk.W, pady=5)
        
        ttk.Radiobutton(settings_frame, text="右から左", variable=self.direction_var,
                        value="right_to_left").grid(row=1, column=1, sticky=tk.W, pady=5)
        
        ttk.Radiobutton(settings_frame, text="ジグザグ (左右交互、2行)", variable=self.direction_var,
                        value="zigzag").grid(row=1, column=2, sticky=tk.W, pady=5)
        
        # 境界線サイズ設定
        ttk.Label(settings_frame, text="境界線サイズ:").grid(row=2, column=0, sticky=tk.W, pady=5)
        
        self.boundary_size_var = tk.IntVar(value=10)
        boundary_scale = ttk.Scale(settings_frame, from_=0, to=50, 
                                  variable=self.boundary_size_var, orient=tk.HORIZONTAL, length=200)
        boundary_scale.grid(row=2, column=1, sticky=tk.W, pady=5)
        ttk.Label(settings_frame, textvariable=self.boundary_size_var).grid(row=2, column=2, sticky=tk.W, pady=5)
        ttk.Label(settings_frame, text="px").grid(row=2, column=3, sticky=tk.W, pady=5)
        
        # 出力設定フレーム
        output_frame = ttk.LabelFrame(main_frame, text="出力設定", padding="10")
        output_frame.pack(fill=tk.X, pady=5)
        
        # 出力ファイル選択
        ttk.Label(output_frame, text="出力ファイル:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.output_path_var = tk.StringVar()
        ttk.Entry(output_frame, textvariable=self.output_path_var, width=50).grid(row=0, column=1, pady=5, padx=5)
        ttk.Button(output_frame, text="参照...", command=self.browse_output).grid(row=0, column=2, pady=5)
        
        # プレビューとプログレスフレーム
        preview_frame = ttk.LabelFrame(main_frame, text="進捗", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 進捗バー
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(preview_frame, variable=self.progress_var, maximum=100, length=700)
        self.progress_bar.pack(pady=10, fill=tk.X)
        
        # 進捗情報
        self.progress_label = ttk.Label(preview_frame, text="準備完了")
        self.progress_label.pack(pady=5)
        
        # ボタンフレーム
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # 連結開始ボタン
        self.start_button = ttk.Button(button_frame, text="画像を連結", command=self.start_concatenation)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        # 停止ボタン
        self.stop_button = ttk.Button(button_frame, text="停止", command=self.stop_concatenation, state="disabled")
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # 終了ボタン
        self.quit_button = ttk.Button(button_frame, text="終了", command=self.root.destroy)
        self.quit_button.pack(side=tk.RIGHT, padx=5)
    
    def browse_images(self):
        """画像ファイル選択ダイアログ"""
        file_paths = filedialog.askopenfilenames(
            title="画像ファイルを選択",
            filetypes=[
                ("画像ファイル", "*.jpg *.jpeg *.png *.bmp"),
                ("すべてのファイル", "*.*")
            ]
        )
        
        if file_paths:
            self.image_paths.extend(file_paths)
            self.update_file_list()
    
    def update_file_list(self):
        """ファイルリストの更新"""
        self.file_listbox.delete(0, tk.END)
        
        # 画像を時間順にソート（表示用）
        sorted_paths = ImageConcatenator(self.image_paths).sort_images_by_timestamp()
        
        for path in sorted_paths:
            self.file_listbox.insert(tk.END, os.path.basename(path))
        
        self.file_count_var.set(f"選択されたファイル: {len(self.image_paths)}")
    
    def clear_selection(self):
        """選択ファイルのクリア"""
        self.image_paths = []
        self.file_listbox.delete(0, tk.END)
        self.file_count_var.set("選択されたファイル: 0")
    
    def browse_output(self):
        """出力ファイル選択ダイアログ"""
        file_path = filedialog.asksaveasfilename(
            title="出力ファイルを選択",
            filetypes=[
                ("PNG画像", "*.png"),
                ("JPEG画像", "*.jpg"),
                ("すべてのファイル", "*.*")
            ],
            defaultextension=".png"
        )
        
        if file_path:
            self.output_path_var.set(file_path)
    
    def update_progress(self, progress, message):
        """進捗状況の更新"""
        self.progress_var.set(progress)
        self.progress_label.config(text=message)
        self.root.update_idletasks()
    
    def process_completed(self, success, message):
        """処理完了時のコールバック"""
        self.processing = False
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        
        if success:
            messagebox.showinfo("完了", message)
        else:
            messagebox.showerror("エラー", message)
        
        # UIの更新
        self.progress_label.config(text=message)
    
    def start_concatenation(self):
        """連結処理の開始"""
        # 入力チェック
        if not self.image_paths:
            messagebox.showerror("エラー", "画像ファイルを選択してください")
            return
        
        if not self.output_path_var.get():
            messagebox.showerror("エラー", "出力ファイルを指定してください")
            return
        
        # 出力ディレクトリの確認
        output_dir = os.path.dirname(self.output_path_var.get())
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                messagebox.showerror("エラー", f"出力フォルダの作成に失敗しました: {str(e)}")
                return
        
        # 設定の適用
        self.concatenator = ImageConcatenator(
            image_paths=self.image_paths,
            output_path=self.output_path_var.get(),
            direction=self.direction_var.get(),
            boundary_size=self.boundary_size_var.get()
        )
        
        # コールバックの設定
        self.concatenator.set_callbacks(
            progress_callback=self.update_progress,
            completion_callback=self.process_completed
        )
        
        # 連結開始
        if self.concatenator.start_concatenation():
            self.processing = True
            self.start_button.config(state="disabled")
            self.stop_button.config(state="normal")
            self.progress_var.set(0)
            self.progress_label.config(text="処理を開始しています...")
        else:
            messagebox.showerror("エラー", "処理の開始に失敗しました")
    
    def stop_concatenation(self):
        """連結処理の停止"""
        if self.processing and self.concatenator:
            self.concatenator.stop_concatenation()
            self.stop_button.config(state="disabled")
            self.progress_label.config(text="停止中...")


def main():
    """メインエントリーポイント"""
    root = tk.Tk()
    app = ImageConcatenatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
