import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import cv2
from PIL import Image, ImageSequence
import numpy as np
import tempfile
import subprocess
import shutil
from pathlib import Path


class VideoMergerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("動画結合アプリ")
        self.root.geometry("700x500")
        self.root.configure(padx=10, pady=10)
        
        self.selected_files = []
        self.output_file = ""
        
        # フレーム作成
        self.setup_ui()
        
    def setup_ui(self):
        # ファイル選択フレーム
        file_frame = ttk.LabelFrame(self.root, text="ファイル選択")
        file_frame.pack(fill="x", padx=5, pady=5)
        
        # ファイルリストボックス
        self.file_listbox = tk.Listbox(file_frame, height=10, width=80)
        self.file_listbox.pack(fill="x", padx=5, pady=5)
        
        # スクロールバー
        scrollbar = ttk.Scrollbar(self.file_listbox)
        scrollbar.pack(side="right", fill="y")
        self.file_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.file_listbox.yview)
        
        # ボタンフレーム
        button_frame = ttk.Frame(file_frame)
        button_frame.pack(fill="x", padx=5, pady=5)
        
        # ファイル追加ボタン
        add_button = ttk.Button(button_frame, text="ファイル追加", command=self.add_files)
        add_button.pack(side="left", padx=5)
        
        # ファイル削除ボタン
        remove_button = ttk.Button(button_frame, text="選択したファイルを削除", command=self.remove_selected_file)
        remove_button.pack(side="left", padx=5)
        
        # ファイル上下移動ボタン
        move_up_button = ttk.Button(button_frame, text="上へ移動", command=self.move_file_up)
        move_up_button.pack(side="left", padx=5)
        
        move_down_button = ttk.Button(button_frame, text="下へ移動", command=self.move_file_down)
        move_down_button.pack(side="left", padx=5)
        
        # 出力ファイル設定フレーム
        output_frame = ttk.LabelFrame(self.root, text="出力ファイル設定")
        output_frame.pack(fill="x", padx=5, pady=5)
        
        # 出力ファイルパス表示
        self.output_path_var = tk.StringVar()
        output_path_entry = ttk.Entry(output_frame, textvariable=self.output_path_var, width=70)
        output_path_entry.pack(side="left", padx=5, pady=5, fill="x", expand=True)
        
        # 出力ファイル選択ボタン
        output_button = ttk.Button(output_frame, text="保存先を選択", command=self.select_output_file)
        output_button.pack(side="right", padx=5, pady=5)
        
        # ステータスフレーム
        status_frame = ttk.LabelFrame(self.root, text="ステータス")
        status_frame.pack(fill="x", padx=5, pady=5)
        
        # プログレスバー
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(status_frame, orient="horizontal", length=100, mode="determinate", variable=self.progress_var)
        self.progress_bar.pack(fill="x", padx=5, pady=5)
        
        # ステータスラベル
        self.status_var = tk.StringVar(value="準備完了")
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.pack(anchor="w", padx=5, pady=5)
        
        # 実行ボタンフレーム
        exec_frame = ttk.Frame(self.root)
        exec_frame.pack(fill="x", padx=5, pady=10)
        
        # 実行ボタン
        exec_button = ttk.Button(exec_frame, text="動画を結合", command=self.merge_videos)
        exec_button.pack(side="right", padx=5)
        
    def add_files(self):
        """ファイルを追加する"""
        filetypes = [
            ("動画ファイル", "*.mp4 *.avi *.mov *.gif *.mjpeg *.mjpg"),
            ("MP4ファイル", "*.mp4"),
            ("GIFファイル", "*.gif"),
            ("モーションJPEG", "*.mjpeg *.mjpg"),
            ("すべてのファイル", "*.*")
        ]
        
        files = filedialog.askopenfilenames(
            title="結合する動画ファイルを選択",
            filetypes=filetypes
        )
        
        if files:
            for file in files:
                if file not in self.selected_files:
                    self.selected_files.append(file)
                    self.file_listbox.insert(tk.END, os.path.basename(file))
    
    def remove_selected_file(self):
        """選択したファイルをリストから削除する"""
        try:
            selected_idx = self.file_listbox.curselection()[0]
            self.file_listbox.delete(selected_idx)
            self.selected_files.pop(selected_idx)
        except IndexError:
            messagebox.showwarning("警告", "削除するファイルを選択してください")
    
    def move_file_up(self):
        """選択したファイルを上に移動"""
        try:
            selected_idx = self.file_listbox.curselection()[0]
            if selected_idx > 0:
                # リストボックスの更新
                file_name = self.file_listbox.get(selected_idx)
                self.file_listbox.delete(selected_idx)
                self.file_listbox.insert(selected_idx - 1, file_name)
                self.file_listbox.selection_set(selected_idx - 1)
                
                # 内部リストの更新
                file_path = self.selected_files.pop(selected_idx)
                self.selected_files.insert(selected_idx - 1, file_path)
        except IndexError:
            messagebox.showwarning("警告", "移動するファイルを選択してください")
    
    def move_file_down(self):
        """選択したファイルを下に移動"""
        try:
            selected_idx = self.file_listbox.curselection()[0]
            if selected_idx < len(self.selected_files) - 1:
                # リストボックスの更新
                file_name = self.file_listbox.get(selected_idx)
                self.file_listbox.delete(selected_idx)
                self.file_listbox.insert(selected_idx + 1, file_name)
                self.file_listbox.selection_set(selected_idx + 1)
                
                # 内部リストの更新
                file_path = self.selected_files.pop(selected_idx)
                self.selected_files.insert(selected_idx + 1, file_path)
        except IndexError:
            messagebox.showwarning("警告", "移動するファイルを選択してください")
    
    def select_output_file(self):
        """出力ファイルを選択する"""
        filetypes = [
            ("MP4ファイル", "*.mp4"),
            ("GIFファイル", "*.gif"),
            ("モーションJPEG", "*.mjpeg"),
            ("AVIファイル", "*.avi")
        ]
        
        output_file = filedialog.asksaveasfilename(
            title="保存先を選択",
            filetypes=filetypes,
            defaultextension=".mp4"
        )
        
        if output_file:
            self.output_file = output_file
            self.output_path_var.set(output_file)
    
    def check_format_compatibility(self):
        """動画フォーマットや解像度が一致しているか確認"""
        if len(self.selected_files) < 2:
            return False, "ファイルが2つ以上必要です"
        
        # 最初のファイルの情報を取得
        first_ext = os.path.splitext(self.selected_files[0])[1].lower()
        
        # GIFかどうかをチェック
        is_gif_format = first_ext == '.gif'
        
        # すべてのファイルが同じ拡張子かチェック
        for file in self.selected_files:
            ext = os.path.splitext(file)[1].lower()
            if ext != first_ext:
                return False, f"異なるフォーマットが混在しています: {first_ext} と {ext}"
        
        # GIFの場合は別処理
        if is_gif_format:
            try:
                # 最初のGIFの情報を取得
                first_gif = Image.open(self.selected_files[0])
                first_width, first_height = first_gif.size
                
                # 他のGIFをチェック
                for file in self.selected_files[1:]:
                    gif = Image.open(file)
                    width, height = gif.size
                    if width != first_width or height != first_height:
                        return False, f"GIFの解像度が一致しません: {first_width}x{first_height} と {width}x{height}"
                
                return True, "GIFフォーマットは互換性があります"
            except Exception as e:
                return False, f"GIFの確認中にエラーが発生しました: {e}"
        
        # 動画ファイルの場合
        try:
            # 最初の動画の情報を取得
            cap = cv2.VideoCapture(self.selected_files[0])
            first_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            first_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            first_fps = cap.get(cv2.CAP_PROP_FPS)
            cap.release()
            
            # 他の動画をチェック
            for file in self.selected_files[1:]:
                cap = cv2.VideoCapture(file)
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                cap.release()
                
                # 解像度をチェック
                if width != first_width or height != first_height:
                    return False, f"解像度が一致しません: {first_width}x{first_height} と {width}x{height}"
                
                # FPSをチェック（厳密に同じでなくても許容範囲内であればOK）
                if abs(fps - first_fps) > 1.0:
                    return False, f"フレームレートが大きく異なります: {first_fps:.2f}fps と {fps:.2f}fps"
            
            return True, "動画フォーマットは互換性があります"
        
        except Exception as e:
            return False, f"動画の確認中にエラーが発生しました: {e}"
    
    def merge_videos(self):
        """動画を結合する"""
        # ファイル選択と出力先のチェック
        if not self.selected_files:
            messagebox.showerror("エラー", "結合するファイルを選択してください")
            return
        
        if not self.output_file:
            messagebox.showerror("エラー", "出力ファイルを指定してください")
            return
        
        # 動画フォーマットの互換性チェック
        compatible, msg = self.check_format_compatibility()
        if not compatible:
            messagebox.showerror("フォーマットエラー", msg)
            return
        
        self.status_var.set("動画の結合を開始します...")
        self.progress_var.set(0)
        self.root.update()
        
        try:
            # 出力ファイルの拡張子を取得
            output_ext = os.path.splitext(self.output_file)[1].lower()
            
            # GIFの場合
            if output_ext == '.gif':
                self.merge_gifs()
            
            # 通常の動画ファイルの場合
            else:
                self.merge_video_files()
            
            self.status_var.set("動画の結合が完了しました")
            self.progress_var.set(100)
            messagebox.showinfo("完了", f"動画の結合が完了しました:\n{self.output_file}")
            
        except Exception as e:
            self.status_var.set(f"エラーが発生しました: {e}")
            messagebox.showerror("エラー", f"結合処理中にエラーが発生しました:\n{e}")
    
    def merge_gifs(self):
        """GIFファイルを結合する"""
        self.status_var.set("GIFファイルを結合中...")
        
        # すべてのフレームを格納するリスト
        all_frames = []
        
        # すべてのGIFからフレームを抽出
        total_files = len(self.selected_files)
        for i, file_path in enumerate(self.selected_files):
            try:
                gif = Image.open(file_path)
                frames = [frame.copy() for frame in ImageSequence.Iterator(gif)]
                all_frames.extend(frames)
                
                # 進捗更新
                progress = (i + 1) / total_files * 80
                self.progress_var.set(progress)
                self.root.update()
                
                # 一時的なメモリ解放
                gif.close()
                
            except Exception as e:
                raise Exception(f"GIFファイル '{os.path.basename(file_path)}' の処理中にエラーが発生しました: {e}")
        
        # フレームが取得できなかった場合
        if not all_frames:
            raise Exception("結合可能なフレームが見つかりませんでした")
        
        self.status_var.set(f"結合したGIFを保存中... ({len(all_frames)}フレーム)")
        self.root.update()
        
        # GIFとして保存
        try:
            # 最初のフレームから新しいGIFを作成
            all_frames[0].save(
                self.output_file,
                save_all=True,
                append_images=all_frames[1:],
                optimize=False,
                duration=100,  # フレーム間の時間（ミリ秒）
                loop=0  # 0は無限ループ
            )
            self.progress_var.set(100)
        except Exception as e:
            raise Exception(f"GIFの保存中にエラーが発生しました: {e}")
    
    def merge_video_files(self):
        """通常の動画ファイルを結合する"""
        # 動画の情報を取得
        cap = cv2.VideoCapture(self.selected_files[0])
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        
        # 出力ファイルの拡張子
        output_ext = os.path.splitext(self.output_file)[1].lower()
        
        # コーデックとフォーマット設定
        if output_ext == '.mp4':
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        elif output_ext == '.avi':
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
        elif output_ext in ('.mjpeg', '.mjpg'):
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        else:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # デフォルトはmp4v
        
        # FFmpegが利用可能かチェック
        has_ffmpeg = shutil.which('ffmpeg') is not None
        
        # FFmpegが使える場合はFFmpegで結合
        if has_ffmpeg:
            self.merge_with_ffmpeg(fps)
        else:
            # OpenCVで結合
            self.merge_with_opencv(fourcc, fps, width, height)
    
    def merge_with_ffmpeg(self, fps):
        """FFmpegを使って動画を結合する"""
        self.status_var.set("FFmpegで動画を結合中...")
        
        # 一時ファイルリストを作成
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as temp_file:
            temp_path = temp_file.name
            for file_path in self.selected_files:
                temp_file.write(f"file '{file_path.replace('\\', '/')}'\n".encode())
        
        try:
            # FFmpegコマンドを構築
            output_ext = os.path.splitext(self.output_file)[1].lower()
            
            # 出力形式に応じたFFmpegオプション
            if output_ext == '.mp4':
                cmd = [
                    'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                    '-i', temp_path, '-c:v', 'libx264', '-crf', '23',
                    '-preset', 'medium', self.output_file
                ]
            elif output_ext == '.gif':
                cmd = [
                    'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                    '-i', temp_path, '-vf', 'split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse',
                    self.output_file
                ]
            elif output_ext in ('.mjpeg', '.mjpg'):
                cmd = [
                    'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                    '-i', temp_path, '-c:v', 'mjpeg', '-q:v', '3',
                    self.output_file
                ]
            else:
                # デフォルトはMP4
                cmd = [
                    'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                    '-i', temp_path, '-c:v', 'libx264', '-crf', '23',
                    '-preset', 'medium', self.output_file
                ]
            
            # FFmpegプロセスを実行
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # 進捗更新のため、プロセスの出力を監視
            while process.poll() is None:
                self.root.update()
                # ここでは簡易的に進捗を50%として表示
                self.progress_var.set(50)
            
            # プロセスが終了したら結果をチェック
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                raise Exception(f"FFmpegエラー: {stderr}")
            
            self.progress_var.set(100)
            
        finally:
            # 一時ファイルを削除
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def merge_with_opencv(self, fourcc, fps, width, height):
        """OpenCVを使って動画を結合する"""
        self.status_var.set("OpenCVで動画を結合中...")
        
        # VideoWriterを作成
        out = cv2.VideoWriter(self.output_file, fourcc, fps, (width, height))
        
        # 各動画のフレームを結合
        total_files = len(self.selected_files)
        for i, file_path in enumerate(self.selected_files):
            self.status_var.set(f"ファイル {i+1}/{total_files} を処理中: {os.path.basename(file_path)}")
            self.root.update()
            
            cap = cv2.VideoCapture(file_path)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # フレームごとに処理
            for j in range(frame_count):
                ret, frame = cap.read()
                if not ret:
                    break
                
                # フレームを書き込み
                out.write(frame)
                
                # 10フレームごとに進捗を更新
                if j % 10 == 0:
                    progress = (i + j/frame_count) / total_files * 100
                    self.progress_var.set(progress)
                    self.root.update()
            
            cap.release()
        
        # リソースを解放
        out.release()


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoMergerApp(root)
    root.mainloop()
