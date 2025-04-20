import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import datetime
import time
import glob
import json
import base64
import threading
import queue
import re
from PIL import Image, ImageTk
import requests
import config

class ScreenshotAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("スクリーンショット分析ツール")
        self.root.geometry("800x600")
        
        # 設定の読み込み
        self.api_endpoint = config.API_ENDPOINT
        self.api_key = config.API_KEY
        self.api_version = config.API_VERSION
        self.model = config.MODEL
        self.frame_prompt = config.FRAME_ANALYSIS_PROMPT
        self.summary_prompt = config.SUMMARY_PROMPT
        
        # メッセージキュー
        self.queue = queue.Queue()
        
        # UI作成
        self.create_widgets()
        
        # 変数の初期化
        self.image_folder = ""
        self.output_folder = ""
        self.image_files = []
        self.current_index = 0
        self.total_images = 0
        self.output_filename = ""
        self.is_processing = False
        
        # 進行状況を定期的に更新
        self.root.after(100, self.process_queue)
    
    def create_widgets(self):
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 上部フレーム（フォルダ選択など）
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=5)
        
        # 画像フォルダ選択
        ttk.Label(top_frame, text="画像フォルダ:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.image_folder_var = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.image_folder_var, width=50).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(top_frame, text="参照...", command=self.select_image_folder).grid(row=0, column=2, padx=5, pady=5)
        
        # 出力フォルダ選択
        ttk.Label(top_frame, text="出力フォルダ:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.output_folder_var = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.output_folder_var, width=50).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(top_frame, text="参照...", command=self.select_output_folder).grid(row=1, column=2, padx=5, pady=5)
        
        # プレビューフレーム
        preview_frame = ttk.LabelFrame(main_frame, text="画像プレビュー", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 画像プレビュー用のキャンバス（左右に2枚）
        self.preview_frame_left = ttk.Frame(preview_frame)
        self.preview_frame_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.preview_frame_right = ttk.Frame(preview_frame)
        self.preview_frame_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        self.canvas_left = tk.Canvas(self.preview_frame_left, bg="white")
        self.canvas_left.pack(fill=tk.BOTH, expand=True)
        
        self.canvas_right = tk.Canvas(self.preview_frame_right, bg="white")
        self.canvas_right.pack(fill=tk.BOTH, expand=True)
        
        # ログフレーム
        log_frame = ttk.LabelFrame(main_frame, text="ログ", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.log_text = tk.Text(log_frame, height=8, wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # 進行状況バー
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(status_frame, text="進行状況:").pack(side=tk.LEFT, padx=5)
        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.status_label = ttk.Label(status_frame, text="準備完了")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        # 操作ボタンフレーム
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="開始", command=self.start_analysis).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="停止", command=self.stop_analysis).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="終了", command=self.root.quit).pack(side=tk.RIGHT, padx=5)
    
    def select_image_folder(self):
        folder = filedialog.askdirectory(title="画像フォルダを選択")
        if folder:
            self.image_folder = folder
            self.image_folder_var.set(folder)
            self.log(f"画像フォルダを選択: {folder}")
            
            # フォルダ内の画像ファイルを取得
            image_patterns = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff']
            self.image_files = []
            for pattern in image_patterns:
                self.image_files.extend(glob.glob(os.path.join(folder, pattern)))
            
            # 自然順でソート
            self.image_files = self.natural_sort(self.image_files)
            self.total_images = len(self.image_files)
            
            if self.total_images > 0:
                self.log(f"合計 {self.total_images} 個の画像が見つかりました。")
                # 最初の2枚をプレビュー
                if self.total_images >= 2:
                    self.display_image_preview(0, 1)
            else:
                self.log("画像が見つかりませんでした。")
    
    def natural_sort(self, l):
        """文字列を自然順（数値を考慮したソート）でソートする"""
        convert = lambda text: int(text) if text.isdigit() else text.lower() 
        alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)] 
        return sorted(l, key=alphanum_key)
    
    def select_output_folder(self):
        folder = filedialog.askdirectory(title="出力フォルダを選択")
        if folder:
            self.output_folder = folder
            self.output_folder_var.set(folder)
            self.log(f"出力フォルダを選択: {folder}")
    
    def display_image_preview(self, index1, index2):
        """指定されたインデックスの画像をプレビュー表示"""
        # 古いプレビューをクリア
        self.canvas_left.delete("all")
        self.canvas_right.delete("all")
        
        try:
            # 左側の画像を表示
            img_left = Image.open(self.image_files[index1])
            img_left = self.resize_image(img_left, (300, 200))
            self.photo_left = ImageTk.PhotoImage(img_left)
            self.canvas_left.create_image(150, 100, image=self.photo_left)
            self.canvas_left.create_text(150, 20, text=f"画像 {index1+1}: {os.path.basename(self.image_files[index1])}")
            
            # 右側の画像を表示
            img_right = Image.open(self.image_files[index2])
            img_right = self.resize_image(img_right, (300, 200))
            self.photo_right = ImageTk.PhotoImage(img_right)
            self.canvas_right.create_image(150, 100, image=self.photo_right)
            self.canvas_right.create_text(150, 20, text=f"画像 {index2+1}: {os.path.basename(self.image_files[index2])}")
        
        except Exception as e:
            self.log(f"画像のプレビュー表示エラー: {str(e)}")
    
    def resize_image(self, img, max_size):
        """アスペクト比を保持しながら画像をリサイズ"""
        width, height = img.size
        ratio = min(max_size[0] / width, max_size[1] / height)
        new_size = (int(width * ratio), int(height * ratio))
        return img.resize(new_size, Image.LANCZOS)
    
    def log(self, message):
        """ログメッセージをキューに追加"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.queue.put(f"[{timestamp}] {message}")
    
    def process_queue(self):
        """キューからメッセージを処理してログに表示"""
        try:
            while True:
                message = self.queue.get_nowait()
                self.log_text.insert(tk.END, message + "\n")
                self.log_text.see(tk.END)
                self.queue.task_done()
        except queue.Empty:
            pass
        finally:
            # 定期的に再スケジュール
            self.root.after(100, self.process_queue)
    
    def start_analysis(self):
        """分析処理を開始"""
        if self.is_processing:
            messagebox.showwarning("警告", "すでに処理が実行中です。")
            return
        
        if not self.image_folder or not self.output_folder:
            messagebox.showwarning("警告", "画像フォルダと出力フォルダを選択してください。")
            return
        
        if self.total_images < 2:
            messagebox.showwarning("警告", "分析するには少なくとも2枚の画像が必要です。")
            return
        
        # 出力ファイル名を設定（タイムスタンプ付き）
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_filename = os.path.join(self.output_folder, f"analysis_{timestamp}.txt")
        
        # 結果保存用のディレクトリを作成
        self.current_output_dir = os.path.join(self.output_folder, f"analysis_{timestamp}")
        os.makedirs(self.current_output_dir, exist_ok=True)
        
        self.is_processing = True
        self.current_index = 0
        self.progress_var.set(0)
        self.status_label.config(text="分析中...")
        
        # 別スレッドで処理を実行
        threading.Thread(target=self.process_images, daemon=True).start()
    
    def process_images(self):
        """画像を順次処理"""
        try:
            total_pairs = self.total_images - 1
            
            # 最初に全体の要約ファイルを作成
            summary_file = os.path.join(self.current_output_dir, "summary.txt")
            with open(summary_file, "w", encoding="utf-8") as f:
                f.write(f"画像分析開始: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"合計画像数: {self.total_images}\n\n")
            
            # 各ペアを処理
            for i in range(self.total_images - 1):
                if not self.is_processing:
                    self.log("処理が停止されました。")
                    break
                
                img1_path = self.image_files[i]
                img2_path = self.image_files[i+1]
                
                self.log(f"画像ペア {i+1}/{total_pairs} を処理中: {os.path.basename(img1_path)} と {os.path.basename(img2_path)}")
                
                # UIを更新して現在の画像ペアを表示
                self.root.after(0, lambda idx1=i, idx2=i+1: self.display_image_preview(idx1, idx2))
                
                # 画像をBase64エンコード
                img1_base64 = self.encode_image_to_base64(img1_path)
                img2_base64 = self.encode_image_to_base64(img2_path)
                
                # Azure OpenAI APIにリクエスト
                response = self.call_azure_openai_api(img1_base64, img2_base64, i, i+1)
                
                # 結果を保存
                pair_output_file = os.path.join(self.current_output_dir, f"pair_{i+1:03d}_to_{i+2:03d}.txt")
                with open(pair_output_file, "w", encoding="utf-8") as f:
                    f.write(f"画像ペア: {os.path.basename(img1_path)} → {os.path.basename(img2_path)}\n")
                    f.write(f"分析時刻: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write(response)
                
                # 要約ファイルにも追記
                with open(summary_file, "a", encoding="utf-8") as f:
                    f.write(f"\n--- 画像ペア {i+1} → {i+2} ---\n")
                    f.write(response)
                    f.write("\n" + "-" * 40 + "\n")
                
                # 進行状況を更新
                progress = int((i + 1) / total_pairs * 100)
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                
                # 少し待機（API制限対策）
                time.sleep(1)
            
            # 全ての分析が終わったら、まとめを生成
            if self.is_processing:
                self.log("すべての画像ペアの処理が完了しました。最終まとめを生成中...")
                self.generate_final_summary()
            
            self.is_processing = False
            self.root.after(0, lambda: self.status_label.config(text="完了"))
            self.log("処理が完了しました。")
            
        except Exception as e:
            self.log(f"エラーが発生しました: {str(e)}")
            self.is_processing = False
            self.root.after(0, lambda: self.status_label.config(text="エラー"))
    
    def encode_image_to_base64(self, image_path):
        """画像をBase64エンコード"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def call_azure_openai_api(self, img1_base64, img2_base64, index1, index2):
        """Azure OpenAI APIを呼び出し"""
        try:
            headers = {
                "Content-Type": "application/json",
                "api-key": self.api_key
            }
            
            # 画像の名前
            img1_name = os.path.basename(self.image_files[index1])
            img2_name = os.path.basename(self.image_files[index2])
            
            # プロンプトにファイル名情報を追加
            prompt = self.frame_prompt.replace("{img1_name}", img1_name).replace("{img2_name}", img2_name)
            
            payload = {
                "messages": [
                    {
                        "role": "system",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"これは連続したスクリーンショットです。画像1({img1_name})から画像2({img2_name})の間で行われた操作を詳細に分析してください。"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{img1_base64}"
                                }
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{img2_base64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 4000,
                "temperature": 0.7
            }
            
            if self.model:
                payload["model"] = self.model
            
            response = requests.post(
                f"{self.api_endpoint}/openai/deployments/{self.model}/chat/completions?api-version={self.api_version}",
                headers=headers,
                data=json.dumps(payload)
            )
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                error_msg = f"API呼び出しエラー: {response.status_code}, {response.text}"
                self.log(error_msg)
                return f"エラー: {error_msg}"
                
        except Exception as e:
            error_msg = f"API呼び出し中に例外が発生: {str(e)}"
            self.log(error_msg)
            return f"エラー: {error_msg}"
    
    def generate_final_summary(self):
        """すべての分析結果から最終まとめを生成"""
        try:
            # すべての分析結果を読み込む
            summary_file = os.path.join(self.current_output_dir, "summary.txt")
            
            with open(summary_file, "r", encoding="utf-8") as f:
                all_analysis = f.read()
            
            # Azure OpenAI APIに最終まとめのリクエスト
            headers = {
                "Content-Type": "application/json",
                "api-key": self.api_key
            }
            
            payload = {
                "messages": [
                    {
                        "role": "system",
                        "content": [
                            {
                                "type": "text",
                                "text": self.summary_prompt
                            }
                        ]
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"以下は連続したスクリーンショットの分析結果です。これらの結果から、全体の操作手順をわかりやすくまとめてください。\n\n{all_analysis}"
                            }
                        ]
                    }
                ],
                "max_tokens": 4000,
                "temperature": 0.7
            }
            
            if self.model:
                payload["model"] = self.model
            
            response = requests.post(
                f"{self.api_endpoint}/openai/deployments/{self.model}/chat/completions?api-version={self.api_version}",
                headers=headers,
                data=json.dumps(payload)
            )
            
            if response.status_code == 200:
                result = response.json()
                final_summary = result["choices"][0]["message"]["content"]
                
                # 最終まとめを保存
                final_summary_file = os.path.join(self.current_output_dir, "final_summary.txt")
                with open(final_summary_file, "w", encoding="utf-8") as f:
                    f.write("=== 操作手順の最終まとめ ===\n\n")
                    f.write(final_summary)
                
                self.log(f"最終まとめを生成しました: {final_summary_file}")
                
                # 結果をメッセージボックスで表示
                self.root.after(0, lambda: messagebox.showinfo("処理完了", 
                    f"すべての分析が完了しました。\n結果は以下のフォルダに保存されています:\n{self.current_output_dir}"))
                
            else:
                error_msg = f"最終まとめAPI呼び出しエラー: {response.status_code}, {response.text}"
                self.log(error_msg)
                
        except Exception as e:
            self.log(f"最終まとめ生成中にエラーが発生: {str(e)}")
    
    def stop_analysis(self):
        """分析処理を停止"""
        if self.is_processing:
            self.is_processing = False
            self.log("処理を停止しています...")
            self.status_label.config(text="停止中...")

def main():
    print(config.API_ENDPOINT)
    root = tk.Tk()
    app = ScreenshotAnalyzerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
