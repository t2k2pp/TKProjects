import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import cv2
import numpy as np
import imageio
from pathlib import Path
import re

class ImageToVideoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("静止画から動画生成アプリ")
        self.root.geometry("800x600")
        
        # 変数の初期化
        self.input_folder = tk.StringVar()
        self.output_file = tk.StringVar()
        self.fps = tk.StringVar(value="30")
        self.output_format = tk.StringVar(value="mp4")
        self.resize_option = tk.StringVar(value="fit_first_height")
        
        # 画像プレビュー用の変数
        self.preview_images = []
        self.current_preview_index = 0
        self.preview_image_tk = None
        
        # UIの作成
        self.create_ui()
    
    def create_ui(self):
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 入力フォルダ選択
        input_frame = ttk.LabelFrame(main_frame, text="入力フォルダ", padding="5")
        input_frame.pack(fill=tk.X, pady=5)
        
        ttk.Entry(input_frame, textvariable=self.input_folder, width=60).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(input_frame, text="参照", command=self.browse_input_folder).pack(side=tk.RIGHT, padx=5)
        
        # 出力ファイル選択
        output_frame = ttk.LabelFrame(main_frame, text="出力ファイル", padding="5")
        output_frame.pack(fill=tk.X, pady=5)
        
        ttk.Entry(output_frame, textvariable=self.output_file, width=60).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(output_frame, text="参照", command=self.browse_output_file).pack(side=tk.RIGHT, padx=5)
        
        # 設定フレーム
        settings_frame = ttk.LabelFrame(main_frame, text="設定", padding="5")
        settings_frame.pack(fill=tk.X, pady=5)
        
        # FPS設定
        fps_frame = ttk.Frame(settings_frame)
        fps_frame.pack(fill=tk.X, pady=2)
        ttk.Label(fps_frame, text="FPS:").pack(side=tk.LEFT, padx=5)
        ttk.Spinbox(fps_frame, from_=1, to=60, textvariable=self.fps, width=5).pack(side=tk.LEFT, padx=5)
        
        # 出力形式
        format_frame = ttk.Frame(settings_frame)
        format_frame.pack(fill=tk.X, pady=2)
        ttk.Label(format_frame, text="出力形式:").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(format_frame, text="MP4", value="mp4", variable=self.output_format).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(format_frame, text="アニメーションGIF", value="gif", variable=self.output_format).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(format_frame, text="モーションJPEG", value="mjpeg", variable=self.output_format).pack(side=tk.LEFT, padx=5)
        
        # リサイズオプション
        resize_frame = ttk.LabelFrame(settings_frame, text="サイズ調整", padding="5")
        resize_frame.pack(fill=tk.X, pady=2)
        
        ttk.Radiobutton(resize_frame, text="縦に合わせる", value="fit_first_height", variable=self.resize_option).pack(anchor=tk.W, padx=5)
        ttk.Radiobutton(resize_frame, text="横に合わせる", value="fit_first_width", variable=self.resize_option).pack(anchor=tk.W, padx=5)
        ttk.Radiobutton(resize_frame, text="縦に合わせてトリミング", value="crop_to_height", variable=self.resize_option).pack(anchor=tk.W, padx=5)
        ttk.Radiobutton(resize_frame, text="横に合わせてトリミング", value="crop_to_width", variable=self.resize_option).pack(anchor=tk.W, padx=5)
        ttk.Radiobutton(resize_frame, text="中央に表示", value="center", variable=self.resize_option).pack(anchor=tk.W, padx=5)
        ttk.Radiobutton(resize_frame, text="左上に表示", value="top_left", variable=self.resize_option).pack(anchor=tk.W, padx=5)
        
        # プレビューフレーム
        preview_frame = ttk.LabelFrame(main_frame, text="プレビュー", padding="5")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.preview_canvas = tk.Canvas(preview_frame, bg="black")
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        
        # プレビューナビゲーションフレーム
        preview_nav_frame = ttk.Frame(preview_frame)
        preview_nav_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(preview_nav_frame, text="前の画像", command=self.show_previous_image).pack(side=tk.LEFT, padx=5)
        self.preview_label = ttk.Label(preview_nav_frame, text="0/0")
        self.preview_label.pack(side=tk.LEFT, padx=5)
        ttk.Button(preview_nav_frame, text="次の画像", command=self.show_next_image).pack(side=tk.LEFT, padx=5)
        ttk.Button(preview_nav_frame, text="プレビュー更新", command=self.load_preview_images).pack(side=tk.RIGHT, padx=5)
        
        # 変換ボタン
        convert_frame = ttk.Frame(main_frame)
        convert_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(convert_frame, text="変換", command=self.generate_video).pack(fill=tk.X, ipady=10)

    def numeric_sort_key(self, path):
        # ファイル名内の数字を数値としてソートするキー関数
        parts = re.split(r'(\d+)', os.path.basename(path))
        parts[1::2] = map(int, parts[1::2])
        return parts

    def browse_input_folder(self):
        folder = filedialog.askdirectory(title="静止画フォルダを選択")
        if folder:
            self.input_folder.set(folder)
            self.load_preview_images()
    
    def browse_output_file(self):
        file_types = []
        
        if self.output_format.get() == "mp4":
            file_types = [("MP4ファイル", "*.mp4")]
            default_ext = ".mp4"
        elif self.output_format.get() == "gif":
            file_types = [("GIFファイル", "*.gif")]
            default_ext = ".gif"
        elif self.output_format.get() == "mjpeg":
            file_types = [("AVIファイル", "*.avi")]
            default_ext = ".avi"
        
        file = filedialog.asksaveasfilename(
            title="出力ファイルを選択",
            filetypes=file_types,
            defaultextension=default_ext
        )
        if file:
            self.output_file.set(file)
    
    def load_preview_images(self):
        folder = self.input_folder.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("エラー", "有効な入力フォルダを選択してください")
            return
        
        # 画像ファイルの拡張子
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
        
        # フォルダ内の画像ファイルを取得
        image_files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f)) and 
                     os.path.splitext(f.lower())[1] in image_extensions]
        
        # ファイル名でソート（数字を数値として扱う）
        image_files.sort(key=lambda x: self.numeric_sort_key(x))
        
        if not image_files:
            messagebox.showerror("エラー", "フォルダ内に画像ファイルがありません")
            return
        
        # 画像パスのリストを作成
        self.preview_images = [os.path.join(folder, f) for f in image_files]
        self.current_preview_index = 0
        
        # プレビュー表示
        self.show_preview_image()
    
    def show_preview_image(self):
        if not self.preview_images:
            return
        
        # 現在の画像をロード
        img_path = self.preview_images[self.current_preview_index]
        img = Image.open(img_path)
        
        # キャンバスのサイズを取得
        canvas_width = self.preview_canvas.winfo_width()
        canvas_height = self.preview_canvas.winfo_height()
        
        # 画像をキャンバスに合わせてリサイズ
        img_width, img_height = img.size
        ratio = min(canvas_width / img_width, canvas_height / img_height)
        new_width = int(img_width * ratio)
        new_height = int(img_height * ratio)
        
        img = img.resize((new_width, new_height), Image.LANCZOS)
        
        # 画像をTkinter形式に変換
        self.preview_image_tk = ImageTk.PhotoImage(img)
        
        # キャンバスをクリアして画像を表示
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(
            canvas_width // 2, canvas_height // 2,
            image=self.preview_image_tk, anchor=tk.CENTER
        )
        
        # プレビューラベルを更新
        self.preview_label.config(text=f"{self.current_preview_index + 1}/{len(self.preview_images)}")
    
    def show_next_image(self):
        if self.preview_images:
            self.current_preview_index = (self.current_preview_index + 1) % len(self.preview_images)
            self.show_preview_image()
    
    def show_previous_image(self):
        if self.preview_images:
            self.current_preview_index = (self.current_preview_index - 1) % len(self.preview_images)
            self.show_preview_image()
    
    def resize_image(self, img, first_img_size):
        img_width, img_height = img.size
        first_width, first_height = first_img_size
        
        resize_option = self.resize_option.get()
        
        if resize_option == "fit_first_height":
            # 縦に合わせる
            ratio = first_height / img_height
            new_width = int(img_width * ratio)
            resized_img = img.resize((new_width, first_height), Image.LANCZOS)
            # 新しい画像を作成して、中央に配置
            new_img = Image.new("RGB", (first_width, first_height), (0, 0, 0))
            paste_x = (first_width - new_width) // 2
            new_img.paste(resized_img, (paste_x, 0))
            return new_img
            
        elif resize_option == "fit_first_width":
            # 横に合わせる
            ratio = first_width / img_width
            new_height = int(img_height * ratio)
            resized_img = img.resize((first_width, new_height), Image.LANCZOS)
            # 新しい画像を作成して、中央に配置
            new_img = Image.new("RGB", (first_width, first_height), (0, 0, 0))
            paste_y = (first_height - new_height) // 2
            new_img.paste(resized_img, (0, paste_y))
            return new_img
            
        elif resize_option == "crop_to_height":
            # 縦に合わせてトリミング
            ratio = first_height / img_height
            new_width = int(img_width * ratio)
            resized_img = img.resize((new_width, first_height), Image.LANCZOS)
            # 横幅が大きい場合は中央からトリミング
            if new_width > first_width:
                left = (new_width - first_width) // 2
                resized_img = resized_img.crop((left, 0, left + first_width, first_height))
            else:
                # 横幅が小さい場合は黒背景に中央配置
                new_img = Image.new("RGB", (first_width, first_height), (0, 0, 0))
                paste_x = (first_width - new_width) // 2
                new_img.paste(resized_img, (paste_x, 0))
                return new_img
            return resized_img
            
        elif resize_option == "crop_to_width":
            # 横に合わせてトリミング
            ratio = first_width / img_width
            new_height = int(img_height * ratio)
            resized_img = img.resize((first_width, new_height), Image.LANCZOS)
            # 高さが大きい場合は中央からトリミング
            if new_height > first_height:
                top = (new_height - first_height) // 2
                resized_img = resized_img.crop((0, top, first_width, top + first_height))
            else:
                # 高さが小さい場合は黒背景に中央配置
                new_img = Image.new("RGB", (first_width, first_height), (0, 0, 0))
                paste_y = (first_height - new_height) // 2
                new_img.paste(resized_img, (0, paste_y))
                return new_img
            return resized_img
            
        elif resize_option == "center":
            # 中央に表示
            new_img = Image.new("RGB", (first_width, first_height), (0, 0, 0))
            paste_x = (first_width - img_width) // 2
            paste_y = (first_height - img_height) // 2
            paste_x = max(0, paste_x)
            paste_y = max(0, paste_y)
            
            # 画像が大きすぎる場合はリサイズ
            if img_width > first_width or img_height > first_height:
                ratio = min(first_width / img_width, first_height / img_height)
                new_width = int(img_width * ratio)
                new_height = int(img_height * ratio)
                img = img.resize((new_width, new_height), Image.LANCZOS)
                paste_x = (first_width - new_width) // 2
                paste_y = (first_height - new_height) // 2
            
            new_img.paste(img, (paste_x, paste_y))
            return new_img
            
        elif resize_option == "top_left":
            # 左上に表示
            new_img = Image.new("RGB", (first_width, first_height), (0, 0, 0))
            
            # 画像が大きすぎる場合はリサイズ
            if img_width > first_width or img_height > first_height:
                ratio = min(first_width / img_width, first_height / img_height)
                new_width = int(img_width * ratio)
                new_height = int(img_height * ratio)
                img = img.resize((new_width, new_height), Image.LANCZOS)
            
            new_img.paste(img, (0, 0))
            return new_img
        
        return img
    
    def generate_video(self):
        if not self.preview_images:
            messagebox.showerror("エラー", "入力画像がありません")
            return
        
        if not self.output_file.get():
            messagebox.showerror("エラー", "出力ファイルが指定されていません")
            return
        
        try:
            fps = int(self.fps.get())
            if fps <= 0:
                messagebox.showerror("エラー", "FPSは1以上の値を指定してください")
                return
        except ValueError:
            messagebox.showerror("エラー", "FPSは数値で指定してください")
            return
        
        # 進行状況ダイアログ
        progress_window = tk.Toplevel(self.root)
        progress_window.title("動画生成中")
        progress_window.geometry("300x100")
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        progress_label = ttk.Label(progress_window, text="画像処理中...")
        progress_label.pack(pady=10)
        
        progress_bar = ttk.Progressbar(progress_window, orient=tk.HORIZONTAL, length=250, mode='determinate')
        progress_bar.pack(pady=10)
        
        # プログレスバーの最大値を設定
        progress_bar['maximum'] = len(self.preview_images)
        
        # 最初の画像のサイズを取得
        first_img = Image.open(self.preview_images[0])
        first_img_size = first_img.size
        
        output_format = self.output_format.get()
        output_file = self.output_file.get()
        
        # 処理を別スレッドで実行
        def process_task():
            try:
                if output_format == "gif":
                    # GIF形式で出力
                    frames = []
                    for i, img_path in enumerate(self.preview_images):
                        img = Image.open(img_path)
                        img = self.resize_image(img, first_img_size)
                        frames.append(img)
                        progress_bar['value'] = i + 1
                        progress_window.update()
                    
                    # GIFとして保存
                    frames[0].save(
                        output_file,
                        save_all=True,
                        append_images=frames[1:],
                        optimize=False,
                        duration=int(1000 / fps),
                        loop=0
                    )
                
                elif output_format in ["mp4", "mjpeg"]:
                    # OpenCVで出力
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v') if output_format == "mp4" else cv2.VideoWriter_fourcc(*'MJPG')
                    out = cv2.VideoWriter(output_file, fourcc, fps, first_img_size)
                    
                    for i, img_path in enumerate(self.preview_images):
                        img = Image.open(img_path)
                        img = self.resize_image(img, first_img_size)
                        
                        # PILからOpenCV形式に変換
                        frame = np.array(img)
                        # RGBからBGRに変換
                        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                        
                        out.write(frame)
                        progress_bar['value'] = i + 1
                        progress_window.update()
                    
                    out.release()
                
                progress_window.destroy()
                messagebox.showinfo("完了", "動画の生成が完了しました")
            
            except Exception as e:
                progress_window.destroy()
                messagebox.showerror("エラー", f"動画生成中にエラーが発生しました: {str(e)}")
        
        self.root.after(100, process_task)

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageToVideoApp(root)
    
    # ウィンドウのリサイズ時にプレビューを更新
    def on_resize(event):
        if hasattr(app, 'preview_images') and app.preview_images:
            app.show_preview_image()
    
    app.preview_canvas.bind("<Configure>", on_resize)
    
    root.mainloop()
