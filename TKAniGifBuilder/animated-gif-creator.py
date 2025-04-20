"""
アニメーションGIF作成アプリケーション
- 複数の画像から時系列順にGIFアニメーションを作成
- フレームレート（FPS）設定機能
- ファイル名から時系列順にソート
- 進捗表示機能付きUI
"""

import os
import re
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk, ImageSequence
import datetime
from functools import cmp_to_key
from threading import Thread

class AnimatedGifCreator:
    """GIFアニメーション作成の核となるロジッククラス"""

    def __init__(self, image_paths=None, output_path=None, 
                 fps=10, loop=0):
        """
        初期化メソッド
        
        Parameters:
        -----------
        image_paths : list
            GIFに含める画像ファイルのパスリスト
        output_path : str
            出力GIFのパス
        fps : float
            フレームレート（フレーム/秒）
        loop : int
            ループ回数（0=無限ループ）
        """
        self.image_paths = image_paths or []
        self.output_path = output_path
        self.fps = fps
        self.loop = loop
        
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
    
    def create_animated_gif(self):
        """複数の画像からアニメーションGIFを作成"""
        if not self.image_paths or not self.output_path:
            return False
        
        try:
            # 画像を時系列でソート
            sorted_paths = self.sort_images_by_timestamp()
            
            # フレーム間の時間（ミリ秒）
            duration = int(1000 / self.fps)
            
            # 画像を読み込む
            frames = []
            
            # 進捗情報
            total_files = len(sorted_paths)
            current_file = 0
            
            for img_path in sorted_paths:
                current_file += 1
                
                if self.stop_requested:
                    break
                
                try:
                    img = Image.open(img_path)
                    # PNGなど透過画像の場合はRGBAモードになるため、
                    # RGB形式に変換して透過部分を白に
                    if img.mode == 'RGBA':
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[3])
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    frames.append(img)
                    
                    # 進捗通知
                    if self.progress_callback:
                        progress = (current_file / total_files) * 80  # 80%: 画像読み込み
                        self.progress_callback(progress, f"画像を読み込み中 ({current_file}/{total_files})")
                
                except Exception as e:
                    if self.completion_callback:
                        self.completion_callback(False, f"画像の読み込みエラー: {str(e)}")
                    return False
            
            if self.stop_requested:
                if self.completion_callback:
                    self.completion_callback(False, "処理が中断されました")
                return False
            
            if not frames:
                if self.completion_callback:
                    self.completion_callback(False, "有効な画像がありません")
                return False
            
            # 進捗通知
            if self.progress_callback:
                self.progress_callback(85, "GIFアニメーションを作成中...")
            
            # GIFアニメーションを保存
            try:
                frames[0].save(
                    self.output_path,
                    format='GIF',
                    append_images=frames[1:],
                    save_all=True,
                    duration=duration,
                    loop=self.loop,
                    optimize=False
                )
                
                # 進捗通知
                if self.progress_callback:
                    self.progress_callback(100, "GIFアニメーションを保存しました")
                
                if self.completion_callback:
                    self.completion_callback(True, f"GIFアニメーションの作成が完了しました: {self.output_path}")
                
                return True
            
            except Exception as e:
                if self.completion_callback:
                    self.completion_callback(False, f"GIFの保存エラー: {str(e)}")
                return False
        
        except Exception as e:
            if self.completion_callback:
                self.completion_callback(False, f"GIFの作成エラー: {str(e)}")
            return False
    
    def start_creation(self):
        """別スレッドでGIF作成処理を開始"""
        if self.is_processing:
            return False
        
        self.is_processing = True
        self.stop_requested = False
        
        creation_thread = Thread(target=self.create_animated_gif)
        creation_thread.daemon = True
        creation_thread.start()
        return True
    
    def stop_creation(self):
        """GIF作成処理の停止を要求"""
        self.stop_requested = True


class AnimatedGifCreatorApp:
    """GIFアニメーション作成アプリケーションのUIクラス"""
    
    def __init__(self, root):
        """
        初期化メソッド
        
        Parameters:
        -----------
        root : tk.Tk
            tkinterのルートウィンドウ
        """
        self.root = root
        self.root.title("アニメーションGIF作成ツール")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # スタイル設定
        self.style = ttk.Style()
        self.style.configure("TButton", font=("Helvetica", 12))
        self.style.configure("TLabel", font=("Helvetica", 12))
        
        # 選択された画像ファイルのリスト
        self.image_paths = []
        
        # UI作成
        self.create_widgets()
        
        # 処理ステータス
        self.processing = False
        
        # GIF作成クラス
        self.gif_creator = AnimatedGifCreator()

        # プレビュー用の変数
        self.preview_gif = None
        self.preview_frames = []
        self.preview_index = 0
        self.preview_playing = False
    
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
        
        # GIF設定フレーム
        settings_frame = ttk.LabelFrame(main_frame, text="GIF設定", padding="10")
        settings_frame.pack(fill=tk.X, pady=5)
        
        # フレームレート設定
        ttk.Label(settings_frame, text="フレームレート:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.fps_var = tk.DoubleVar(value=10)
        fps_scale = ttk.Scale(settings_frame, from_=1, to=30, 
                             variable=self.fps_var, orient=tk.HORIZONTAL, length=200)
        fps_scale.grid(row=0, column=1, sticky=tk.W, pady=5)
        ttk.Label(settings_frame, textvariable=self.fps_var).grid(row=0, column=2, sticky=tk.W, pady=5)
        ttk.Label(settings_frame, text="fps").grid(row=0, column=3, sticky=tk.W, pady=5)
        
        # ループ設定
        ttk.Label(settings_frame, text="ループ:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.loop_var = tk.IntVar(value=0)
        self.loop_combobox = ttk.Combobox(settings_frame, textvariable=self.loop_var, 
                                         values=["0 (無限ループ)", "1", "2", "3", "5", "10"])
        self.loop_combobox.current(0)
        self.loop_combobox.grid(row=1, column=1, sticky=tk.W, pady=5)
        self.loop_combobox.bind("<<ComboboxSelected>>", self.update_loop)
        
        # 出力設定フレーム
        output_frame = ttk.LabelFrame(main_frame, text="出力設定", padding="10")
        output_frame.pack(fill=tk.X, pady=5)
        
        # 出力ファイル選択
        ttk.Label(output_frame, text="出力ファイル:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.output_path_var = tk.StringVar()
        ttk.Entry(output_frame, textvariable=self.output_path_var, width=50).grid(row=0, column=1, pady=5, padx=5)
        ttk.Button(output_frame, text="参照...", command=self.browse_output).grid(row=0, column=2, pady=5)
        
        # プレビューとプログレスフレーム
        preview_frame = ttk.LabelFrame(main_frame, text="プレビューと進捗", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # プレビュー画像
        self.preview_label = ttk.Label(preview_frame)
        self.preview_label.pack(pady=10)
        
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
        
        # GIF作成開始ボタン
        self.start_button = ttk.Button(button_frame, text="GIFを作成", command=self.start_creation)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        # 停止ボタン
        self.stop_button = ttk.Button(button_frame, text="停止", command=self.stop_creation, state="disabled")
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # 終了ボタン
        self.quit_button = ttk.Button(button_frame, text="終了", command=self.root.destroy)
        self.quit_button.pack(side=tk.RIGHT, padx=5)
        
        # プレビュー用の初期画像
        self.update_preview_placeholder()
    
    def update_preview_placeholder(self):
        """プレビュー用のプレースホルダ画像を表示"""
        img = Image.new('RGB', (320, 240), color=(200, 200, 200))
        img_tk = ImageTk.PhotoImage(image=img)
        self.preview_label.config(image=img_tk)
        self.preview_label.image = img_tk
    
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
            self.load_preview_images()
    
    def update_file_list(self):
        """ファイルリストの更新"""
        self.file_listbox.delete(0, tk.END)
        
        # 画像を時間順にソート（表示用）
        sorted_paths = AnimatedGifCreator(self.image_paths).sort_images_by_timestamp()
        
        for path in sorted_paths:
            self.file_listbox.insert(tk.END, os.path.basename(path))
        
        self.file_count_var.set(f"選択されたファイル: {len(self.image_paths)}")
    
    def load_preview_images(self):
        """プレビュー用に画像をロード"""
        if not self.image_paths:
            self.update_preview_placeholder()
            return
        
        # 画像を時間順にソート
        sorted_paths = AnimatedGifCreator(self.image_paths).sort_images_by_timestamp()
        
        # プレビュー用のサイズ
        preview_width = 320
        preview_height = 240
        
        # プレビュー用フレームをロード
        self.preview_frames = []
        for path in sorted_paths[:20]:  # 最初の20フレームだけ使用
            try:
                img = Image.open(path)
                
                # アスペクト比を保ったままリサイズ
                img.thumbnail((preview_width, preview_height), Image.LANCZOS)
                
                # 中央に配置するためのオフセットを計算
                bg = Image.new('RGB', (preview_width, preview_height), color=(200, 200, 200))
                x_offset = (preview_width - img.width) // 2
                y_offset = (preview_height - img.height) // 2
                
                bg.paste(img, (x_offset, y_offset))
                
                # ImageTkオブジェクトに変換
                img_tk = ImageTk.PhotoImage(image=bg)
                self.preview_frames.append(img_tk)
            except:
                pass
        
        # 少なくとも1つのフレームがあればプレビュー開始
        if self.preview_frames:
            self.start_preview_animation()
    
    def start_preview_animation(self):
        """プレビューアニメーションの開始"""
        if not self.preview_frames:
            return
        
        self.preview_playing = True
        self.preview_index = 0
        self.update_preview_frame()
    
    def update_preview_frame(self):
        """プレビューフレームの更新"""
        if not self.preview_playing or not self.preview_frames:
            return
        
        # 現在のフレームを表示
        self.preview_label.config(image=self.preview_frames[self.preview_index])
        
        # 次のフレームのインデックスを計算
        self.preview_index = (self.preview_index + 1) % len(self.preview_frames)
        
        # フレームレートに基づいて次のフレーム更新をスケジュール
        delay = int(1000 / self.fps_var.get())
        self.root.after(delay, self.update_preview_frame)
    
    def stop_preview_animation(self):
        """プレビューアニメーションの停止"""
        self.preview_playing = False
    
    def clear_selection(self):
        """選択ファイルのクリア"""
        self.image_paths = []
        self.file_listbox.delete(0, tk.END)
        self.file_count_var.set("選択されたファイル: 0")
        self.stop_preview_animation()
        self.update_preview_placeholder()
    
    def update_loop(self, event=None):
        """ループ設定の更新"""
        selection = self.loop_combobox.get()
        if selection.startswith("0"):
            self.loop_var.set(0)
        else:
            try:
                self.loop_var.set(int(selection))
            except:
                self.loop_var.set(0)
    
    def browse_output(self):
        """出力ファイル選択ダイアログ"""
        file_path = filedialog.asksaveasfilename(
            title="出力ファイルを選択",
            filetypes=[
                ("GIFアニメーション", "*.gif"),
                ("すべてのファイル", "*.*")
            ],
            defaultextension=".gif"
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
            self.load_created_gif()
        else:
            messagebox.showerror("エラー", message)
        
        # UIの更新
        self.progress_label.config(text=message)
    
    def load_created_gif(self):
        """作成されたGIFを読み込む（オプション）"""
        output_path = self.output_path_var.get()
        if not output_path or not os.path.exists(output_path):
            return
        
        try:
            # GIFを読み込み、UIを更新するコードを追加できます
            # 例: 新しいウィンドウでGIFを表示するなど
            pass
        except:
            pass
    
    def start_creation(self):
        """GIF作成処理の開始"""
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
        
        # プレビューの停止
        self.stop_preview_animation()
        
        # 設定の適用
        self.gif_creator = AnimatedGifCreator(
            image_paths=self.image_paths,
            output_path=self.output_path_var.get(),
            fps=self.fps_var.get(),
            loop=self.loop_var.get()
        )
        
        # コールバックの設定
        self.gif_creator.set_callbacks(
            progress_callback=self.update_progress,
            completion_callback=self.process_completed
        )
        
        # GIF作成開始
        if self.gif_creator.start_creation():
            self.processing = True
            self.start_button.config(state="disabled")
            self.stop_button.config(state="normal")
            self.progress_var.set(0)
            self.progress_label.config(text="処理を開始しています...")
        else:
            messagebox.showerror("エラー", "処理の開始に失敗しました")
    
    def stop_creation(self):
        """GIF作成処理の停止"""
        if self.processing and self.gif_creator:
            self.gif_creator.stop_creation()
            self.stop_button.config(state="disabled")
            self.progress_label.config(text="停止中...")


def main():
    """メインエントリーポイント"""
    root = tk.Tk()
    app = AnimatedGifCreatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
