"""
動画フレーム抽出アプリケーション
- マウスカーソル程度の小さな変化は無視
- 実質的な動きのあるフレームを抽出
- tkinterベースのUI
- サンプリングタイミング指定可能
- 出力画像サイズをカスタマイズ可能
"""

import os
import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from skimage.metrics import structural_similarity as ssim
from threading import Thread
from PIL import Image, ImageTk
import time
from datetime import timedelta

class VideoFrameExtractor:
    def __init__(self, video_path=None, output_dir=None, 
                 diff_threshold=0.05, min_area_threshold=500, 
                 blur_size=5, sample_interval=0, resize_output=False, 
                 output_width=None, output_height=None, force_sampling=False,
                 output_format='jpg'):  # 追加
        """
        動画フレーム抽出のメインクラス
        
        Parameters:
        -----------
        video_path : str
            入力動画ファイルのパス
        output_dir : str
            出力フレームを保存するディレクトリ
        diff_threshold : float
            フレーム間の差分閾値 (0.0～1.0)
        min_area_threshold : int
            有意な変化と判断する最小領域サイズ (px^2)
        blur_size : int
            ノイズ除去用ブラーのサイズ
        sample_interval : float
            サンプリング間隔（秒）。0の場合はすべてのフレームを処理
        resize_output : bool
            出力サイズ変更フラグ
        output_width : int
            出力画像の幅
        output_height : int
            出力画像の高さ
        force_sampling : bool
            サンプリング間隔ごとにフレームを強制保存するフラグ
        output_format : str
            出力画像のフォーマット ('jpg' または 'png')
        """
        self.video_path = video_path
        self.output_dir = output_dir
        self.diff_threshold = diff_threshold
        self.min_area_threshold = min_area_threshold
        self.blur_size = blur_size
        self.sample_interval = sample_interval
        self.resize_output = resize_output
        self.output_width = output_width
        self.output_height = output_height
        self.force_sampling = force_sampling
        self.output_format = output_format.lower()  # jpg または png
        
        # 処理状態
        self.is_processing = False
        self.stop_requested = False
        self.current_frame = 0
        self.total_frames = 0
        self.saved_frames = 0
        self.video_duration = 0
        self.current_time = 0
        
        # コールバック関数
        self.progress_callback = None
        self.completion_callback = None
    
    def set_callbacks(self, progress_callback=None, completion_callback=None):
        """コールバック関数を設定"""
        self.progress_callback = progress_callback
        self.completion_callback = completion_callback
    
    def extract_frames(self):
        """動画からフレームを抽出する"""
        if not self.video_path or not self.output_dir:
            if self.completion_callback:
                self.completion_callback(False, "入力動画または出力ディレクトリが未指定です")
            return False
        
        # カウンターのリセット
        self.current_frame = 0
        self.saved_frames = 0
        self.is_processing = True
        self.stop_requested = False

        # 出力ディレクトリを作成（日本語パス対応）
        try:
            output_dir = str(self.output_dir)  # 明示的に文字列化
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            if self.completion_callback:
                self.completion_callback(False, f"出力ディレクトリの作成に失敗: {str(e)}")
            return False

        try:
            # 動画ファイルのパスを明示的に文字列化し、日本語パスに対応
            video_path = str(self.video_path)
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                if self.completion_callback:
                    self.completion_callback(False, "動画ファイルを開けませんでした")
                return False

            # 動画情報の取得
            self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            self.video_duration = self.total_frames / fps if fps > 0 else 0
            frame_interval = max(1, int(fps * self.sample_interval)) if self.sample_interval > 0 else 1

            # 最初のフレームの読み込みと保存
            ret, first_frame = cap.read()
            if not ret:
                if self.completion_callback:
                    self.completion_callback(False, "最初のフレームを読み込めませんでした")
                return False

            # 最初のフレームを保存（エラーハンドリング強化）
            try:
                if self.resize_output and self.output_width and self.output_height:
                    first_frame = cv2.resize(first_frame, (self.output_width, self.output_height))
                
                first_output_path = os.path.join(output_dir, f"frame_000000_00-00-00.{self.output_format}")
                print(f"保存を試みます: {first_output_path}")
                print(f"フレームの形状: {first_frame.shape}")
                print(f"フレームのデータ型: {first_frame.dtype}")
                
                # パスが存在することを確認
                os.makedirs(os.path.dirname(first_output_path), exist_ok=True)
                
                # フレームが有効か確認
                if first_frame is None or first_frame.size == 0:
                    print("エラー: フレームが無効です")
                    return False
                
                # 絶対パスに変換
                first_output_path = os.path.abspath(first_output_path)
                
                # 書き込み権限の確認
                if not os.access(os.path.dirname(first_output_path), os.W_OK):
                    print(f"エラー: 書き込み権限がありません - {os.path.dirname(first_output_path)}")
                    return False
                
                success = cv2.imwrite(first_output_path, first_frame)
                if not success:
                    print(f"警告: cv2.imwrite が失敗を返しました - {first_output_path}")
                    # 代替の保存方法を試す
                    try:
                        img = Image.fromarray(cv2.cvtColor(first_frame, cv2.COLOR_BGR2RGB))
                        img.save(first_output_path, self.output_format.upper())
                        success = True
                        print("PIL による保存が成功しました")
                    except Exception as e:
                        print(f"PIL による保存も失敗: {str(e)}")
                
                if success:
                    self.saved_frames += 1
                    print(f"最初のフレームを保存しました: {first_output_path}")
                else:
                    print(f"警告: 最初のフレームの保存に失敗 - {first_output_path}")

            except Exception as e:
                print(f"最初のフレーム保存エラーの詳細: {str(e)}")
                print(f"エラーの種類: {type(e)}")
                import traceback
                traceback.print_exc()

            # 以降の処理
            prev_frame = cv2.cvtColor(first_frame, cv2.COLOR_BGR2GRAY)
            prev_frame = cv2.GaussianBlur(prev_frame, (self.blur_size, self.blur_size), 0)
            frame_time = 0

            while not self.stop_requested:
                ret, current_frame = cap.read()
                if not ret:
                    break

                self.current_frame += 1
                frame_time = self.current_frame / fps

                # サンプリング間隔のタイミングで強制保存するかどうかをチェック
                if self.current_frame % frame_interval == 0 and self.force_sampling:
                    save_frame = True
                else:
                    # 通常の変化検出による保存判定
                    gray_frame = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
                    gray_frame = cv2.GaussianBlur(gray_frame, (self.blur_size, self.blur_size), 0)

                    similarity_score = ssim(prev_frame, gray_frame)
                    diff_frame = cv2.absdiff(prev_frame, gray_frame)
                    _, diff_thresh = cv2.threshold(diff_frame, 25, 255, cv2.THRESH_BINARY)
                    contours, _ = cv2.findContours(diff_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    significant_change = any(cv2.contourArea(c) > self.min_area_threshold for c in contours)
                    save_frame = 1.0 - similarity_score > self.diff_threshold and significant_change

                # フレームの保存処理
                if save_frame:
                    try:
                        # 必要に応じてリサイズ
                        if self.resize_output and self.output_width and self.output_height:
                            output_frame = cv2.resize(current_frame, (self.output_width, self.output_height))
                        else:
                            output_frame = current_frame.copy()
                        
                        # ファイル名に時間情報を含める
                        time_str = str(timedelta(seconds=int(frame_time))).replace(':', '-')
                        output_path = os.path.join(self.output_dir, f"frame_{self.current_frame:06d}_{time_str}.{self.output_format}")
                        
                        # まずOpenCVで試す
                        success = cv2.imwrite(output_path, output_frame)
                        if not success:
                            print(f"警告: cv2.imwrite が失敗を返しました - {output_path}")
                            # 代替の保存方法を試す
                            try:
                                img = Image.fromarray(cv2.cvtColor(output_frame, cv2.COLOR_BGR2RGB))
                                if self.output_format == 'jpg':
                                    img.save(output_path, "JPEG", quality=95)
                                else:
                                    img.save(output_path, "PNG")
                                success = True
                                print(f"PIL による保存が成功しました - フレーム {self.current_frame}")
                            except Exception as e:
                                print(f"PIL による保存も失敗: {str(e)}")
                        
                        if success:
                            self.saved_frames += 1
                            print(f"フレーム {self.current_frame} を保存しました: {output_path}")
                        else:
                            print(f"警告: フレーム {self.current_frame} の保存に失敗 - {output_path}")
                            
                    except Exception as e:
                        print(f"フレーム {self.current_frame} 保存エラー: {str(e)}")
                        print(f"エラーの種類: {type(e)}")
                        import traceback
                        traceback.print_exc()

                prev_frame = gray_frame

                if self.progress_callback:
                    self.progress_callback(self.current_frame, self.total_frames, frame_time, self.video_duration, self.saved_frames)

        except Exception as e:
            if self.completion_callback:
                self.completion_callback(False, f"処理中にエラーが発生しました: {str(e)}")
            return False
        finally:
            cap.release()
            self.is_processing = False

        # 処理完了通知
        if self.completion_callback:
            if self.stop_requested:
                self.completion_callback(False, "処理が中断されました")
            else:
                self.completion_callback(True, f"処理完了: 合計{self.current_frame}フレーム中、{self.saved_frames}フレームを抽出しました")
        
        return not self.stop_requested
    
    def start_extraction(self):
        """別スレッドでフレーム抽出を開始"""
        if self.is_processing:
            return False
        
        extraction_thread = Thread(target=self.extract_frames)
        extraction_thread.daemon = True
        extraction_thread.start()
        return True
    
    def stop_extraction(self):
        """抽出処理の停止を要求"""
        self.stop_requested = True


class VideoFrameExtractorApp:
    def __init__(self, root):
        """
        アプリケーションのUIクラス
        
        Parameters:
        -----------
        root : tk.Tk
            tkinterのルートウィンドウ
        """
        self.root = root
        self.root.title("動画フレーム抽出ツール")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        # スタイル設定
        self.style = ttk.Style()
        self.style.configure("TButton", font=("Helvetica", 12))
        self.style.configure("TLabel", font=("Helvetica", 12))
        self.style.configure("TCheckbutton", font=("Helvetica", 12))
        
        # フレーム抽出クラス
        self.extractor = VideoFrameExtractor()
        
        # UI作成
        self.create_widgets()
        
        # 処理ステータス
        self.processing = False
    
    def create_widgets(self):
        """UIウィジェットの作成"""
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # ファイル選択フレーム
        file_frame = ttk.LabelFrame(main_frame, text="ファイル選択", padding="10")
        file_frame.pack(fill=tk.X, pady=5)
        
        # 動画ファイル選択
        ttk.Label(file_frame, text="入力動画ファイル:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.video_path_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.video_path_var, width=50).grid(row=0, column=1, pady=5, padx=5)
        ttk.Button(file_frame, text="参照...", command=self.browse_video).grid(row=0, column=2, pady=5)
        
        # 出力フォルダ選択
        ttk.Label(file_frame, text="出力フォルダ:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.output_dir_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.output_dir_var, width=50).grid(row=1, column=1, pady=5, padx=5)
        ttk.Button(file_frame, text="参照...", command=self.browse_output_dir).grid(row=1, column=2, pady=5)
        
        # 設定フレーム
        settings_frame = ttk.LabelFrame(main_frame, text="抽出設定", padding="10")
        settings_frame.pack(fill=tk.X, pady=5)
        
        # 差分閾値
        ttk.Label(settings_frame, text="変化検出感度:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.threshold_var = tk.DoubleVar(value=0.05)
        threshold_scale = ttk.Scale(settings_frame, from_=0.01, to=0.2, 
                                    variable=self.threshold_var, orient=tk.HORIZONTAL, length=200)
        threshold_scale.grid(row=0, column=1, sticky=tk.W, pady=5)
        ttk.Label(settings_frame, textvariable=self.threshold_var).grid(row=0, column=2, sticky=tk.W, pady=5)
        ttk.Label(settings_frame, text="(小さい値ほど敏感)").grid(row=0, column=3, sticky=tk.W, pady=5)
        
        # 最小変化領域
        ttk.Label(settings_frame, text="最小変化領域:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.area_threshold_var = tk.IntVar(value=500)
        area_scale = ttk.Scale(settings_frame, from_=100, to=2000, 
                               variable=self.area_threshold_var, orient=tk.HORIZONTAL, length=200)
        area_scale.grid(row=1, column=1, sticky=tk.W, pady=5)
        ttk.Label(settings_frame, textvariable=self.area_threshold_var).grid(row=1, column=2, sticky=tk.W, pady=5)
        ttk.Label(settings_frame, text="px² (大きい値ほど小さな変化を無視)").grid(row=1, column=3, sticky=tk.W, pady=5)
        
        # サンプリング間隔
        ttk.Label(settings_frame, text="サンプリング間隔:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.sample_interval_var = tk.DoubleVar(value=0)
        interval_options = ["すべてのフレーム", "0.1秒", "0.5秒", "1秒", "2秒", "5秒", "10秒"]
        self.interval_combobox = ttk.Combobox(settings_frame, values=interval_options, state="readonly", width=15)
        self.interval_combobox.current(0)
        self.interval_combobox.grid(row=2, column=1, sticky=tk.W, pady=5)
        self.interval_combobox.bind("<<ComboboxSelected>>", self.update_interval)
        
        # サンプリング間隔で強制抽出
        self.force_sampling_var = tk.BooleanVar(value=False)
        force_sampling_check = ttk.Checkbutton(settings_frame, 
            text="サンプリング間隔で強制抽出", 
            variable=self.force_sampling_var)
        force_sampling_check.grid(row=2, column=2, columnspan=2, sticky=tk.W, pady=5)
        
        # 出力サイズ設定
        size_frame = ttk.LabelFrame(main_frame, text="出力サイズ設定", padding="10")
        size_frame.pack(fill=tk.X, pady=5)
        
        # サイズ変更オプション
        self.resize_var = tk.BooleanVar(value=False)
        resize_check = ttk.Checkbutton(size_frame, text="出力サイズを変更する", 
                                       variable=self.resize_var, command=self.toggle_resize)
        resize_check.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # 幅と高さの入力
        ttk.Label(size_frame, text="幅:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.width_var = tk.IntVar(value=640)
        self.width_entry = ttk.Entry(size_frame, textvariable=self.width_var, width=10, state="disabled")
        self.width_entry.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        
        ttk.Label(size_frame, text="高さ:").grid(row=1, column=2, sticky=tk.W, pady=5)
        self.height_var = tk.IntVar(value=480)
        self.height_entry = ttk.Entry(size_frame, textvariable=self.height_var, width=10, state="disabled")
        self.height_entry.grid(row=1, column=3, sticky=tk.W, pady=5, padx=5)
        
        # 出力形式の選択
        ttk.Label(size_frame, text="出力形式:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.format_var = tk.StringVar(value='jpg')
        format_frame = ttk.Frame(size_frame)
        format_frame.grid(row=2, column=1, columnspan=3, sticky=tk.W, pady=5)
        ttk.Radiobutton(format_frame, text="JPEG", variable=self.format_var, value='jpg').pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(format_frame, text="PNG", variable=self.format_var, value='png').pack(side=tk.LEFT, padx=5)
        
        # プレビューフレーム
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
        
        # 実行ボタン
        self.start_button = ttk.Button(button_frame, text="抽出開始", command=self.start_extraction)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        # 停止ボタン
        self.stop_button = ttk.Button(button_frame, text="停止", command=self.stop_extraction, state="disabled")
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # 終了ボタン
        self.quit_button = ttk.Button(button_frame, text="終了", command=self.root.destroy)
        self.quit_button.pack(side=tk.RIGHT, padx=5)
        
        # デフォルトのプレビュー画像
        self.update_preview(None)
    
    def browse_video(self):
        """動画ファイル選択ダイアログ"""
        file_path = filedialog.askopenfilename(
            title="動画ファイルを選択",
            filetypes=[
                ("動画ファイル", "*.mp4 *.avi *.mov *.mkv *.flv"),
                ("すべてのファイル", "*.*")
            ]
        )
        if file_path:
            self.video_path_var.set(file_path)
            # サムネイル表示
            self.load_video_thumbnail(file_path)
    
    def browse_output_dir(self):
        """出力フォルダ選択ダイアログ"""
        dir_path = filedialog.askdirectory(title="出力フォルダを選択")
        if dir_path:
            self.output_dir_var.set(dir_path)
    
    def toggle_resize(self):
        """リサイズオプションの切り替え"""
        state = "normal" if self.resize_var.get() else "disabled"
        self.width_entry.config(state=state)
        self.height_entry.config(state=state)
    
    def update_interval(self, event=None):
        """サンプリング間隔の更新"""
        selection = self.interval_combobox.get()
        if selection == "すべてのフレーム":
            self.sample_interval_var.set(0)
        else:
            # "X秒"の形式から数値部分を取り出す
            interval = float(selection.split("秒")[0])
            self.sample_interval_var.set(interval)
    
    def load_video_thumbnail(self, video_path):
        """動画のサムネイルを読み込んで表示"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return
            
            # 最初のフレームを取得
            ret, frame = cap.read()
            if ret:
                # OpenCVはBGR形式なのでRGBに変換
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # プレビューサイズに調整
                h, w = frame_rgb.shape[:2]
                max_size = 400
                if w > h:
                    new_w = max_size
                    new_h = int(h * max_size / w)
                else:
                    new_h = max_size
                    new_w = int(w * max_size / h)
                
                frame_resized = cv2.resize(frame_rgb, (new_w, new_h))
                
                # PILイメージに変換
                img = Image.fromarray(frame_resized)
                img_tk = ImageTk.PhotoImage(image=img)
                
                # 画像を表示
                self.preview_label.config(image=img_tk)
                self.preview_label.image = img_tk  # GC対策の参照保持
                
                # 動画情報を表示
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                duration = frame_count / fps if fps > 0 else 0
                
                self.progress_label.config(text=f"動画情報: {w}x{h}, {fps:.2f}fps, {frame_count}フレーム, {duration:.2f}秒")
            
            cap.release()
        except Exception as e:
            messagebox.showerror("エラー", f"サムネイル読み込みエラー: {str(e)}")
    
    def update_preview(self, frame):
        """プレビュー画像の更新"""
        if frame is None:
            # デフォルト画像（グレーの背景）
            img = Image.new('RGB', (400, 300), color=(200, 200, 200))
            img_tk = ImageTk.PhotoImage(image=img)
            self.preview_label.config(image=img_tk)
            self.preview_label.image = img_tk
            return
        
        # OpenCVはBGR形式なのでRGBに変換
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # プレビューサイズに調整
        h, w = frame_rgb.shape[:2]
        max_size = 400
        if w > h:
            new_w = max_size
            new_h = int(h * max_size / w)
        else:
            new_h = max_size
            new_w = int(w * max_size / h)
        
        frame_resized = cv2.resize(frame_rgb, (new_w, new_h))
        
        # PILイメージに変換
        img = Image.fromarray(frame_resized)
        img_tk = ImageTk.PhotoImage(image=img)
        
        # 画像を表示
        self.preview_label.config(image=img_tk)
        self.preview_label.image = img_tk  # GC対策の参照保持
    
    def update_progress(self, current_frame, total_frames, current_time, total_time, saved_frames):
        """進捗状況の更新"""
        if total_frames > 0:
            progress = (current_frame / total_frames) * 100
            self.progress_var.set(progress)
            
            time_str = str(timedelta(seconds=int(current_time))).split('.')[0]
            total_str = str(timedelta(seconds=int(total_time))).split('.')[0]
            
            self.progress_label.config(
                text=f"進捗: {current_frame}/{total_frames} フレーム ({progress:.1f}%), "
                     f"時間: {time_str}/{total_str}, 保存済み: {saved_frames}枚"
            )
            
            # 適当な間隔でプレビューを更新（リソース節約のため）
            if current_frame % 30 == 0 and not self.extractor.stop_requested:
                try:
                    cap = cv2.VideoCapture(self.video_path_var.get())
                    cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
                    ret, frame = cap.read()
                    if ret:
                        self.update_preview(frame)
                    cap.release()
                except:
                    pass
    
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
    
    def start_extraction(self):
        """抽出処理の開始"""
        # 入力チェック
        if not self.video_path_var.get():
            messagebox.showerror("エラー", "動画ファイルを選択してください")
            return
        
        if not self.output_dir_var.get():
            messagebox.showerror("エラー", "出力フォルダを選択してください")
            return
        
        # 出力ディレクトリの確認
        output_dir = self.output_dir_var.get()
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                messagebox.showerror("エラー", f"出力フォルダの作成に失敗しました: {str(e)}")
                return
        
        # 設定の適用
        self.extractor = VideoFrameExtractor(
            video_path=self.video_path_var.get(),
            output_dir=output_dir,
            diff_threshold=self.threshold_var.get(),
            min_area_threshold=self.area_threshold_var.get(),
            blur_size=5,  # 固定値
            sample_interval=self.sample_interval_var.get(),
            resize_output=self.resize_var.get(),
            output_width=self.width_var.get() if self.resize_var.get() else None,
            output_height=self.height_var.get() if self.resize_var.get() else None,
            force_sampling=self.force_sampling_var.get(),
            output_format=self.format_var.get()  # 追加
        )
        
        # コールバックの設定
        self.extractor.set_callbacks(
            progress_callback=self.update_progress,
            completion_callback=self.process_completed
        )
        
        # 抽出開始
        if self.extractor.start_extraction():
            self.processing = True
            self.start_button.config(state="disabled")
            self.stop_button.config(state="normal")
            self.progress_var.set(0)
            self.progress_label.config(text="処理を開始しています...")
        else:
            messagebox.showerror("エラー", "処理の開始に失敗しました")
    
    def stop_extraction(self):
        """抽出処理の停止"""
        if self.processing and self.extractor:
            self.extractor.stop_extraction()
            self.stop_button.config(state="disabled")
            self.progress_label.config(text="停止中...")


def main():
    """メインエントリーポイント"""
    root = tk.Tk()
    app = VideoFrameExtractorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
