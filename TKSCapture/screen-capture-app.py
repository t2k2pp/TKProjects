import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import os
import sys
from datetime import datetime
from PIL import ImageGrab, Image
import pygetwindow as gw
import mss
import mss.tools

class ScreenCaptureApp:
    def __init__(self, root):
        # メインウィンドウの設定
        self.root = root
        self.root.title("画面キャプチャアプリ")
        self.root.geometry("500x400")
        self.root.resizable(False, False)
        
        # 変数の初期化
        self.is_recording = False
        self.capture_thread = None
        self.save_directory = os.path.join(os.path.expanduser("~"), "Screenshots")
        self.capture_interval = 1.0  # デフォルトは1秒間隔
        self.capture_mode = "全ディスプレイ"  # デフォルトは全ディスプレイ
        self.selected_window = None
        
        # ディレクトリが存在しない場合は作成
        if not os.path.exists(self.save_directory):
            os.makedirs(self.save_directory)
            
        # UIの構築
        self._create_widgets()
        
    def _create_widgets(self):
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 設定フレーム
        settings_frame = ttk.LabelFrame(main_frame, text="設定", padding="10")
        settings_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 保存先設定
        save_dir_frame = ttk.Frame(settings_frame)
        save_dir_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(save_dir_frame, text="保存先:").pack(side=tk.LEFT)
        self.save_dir_label = ttk.Label(save_dir_frame, text=self.save_directory)
        self.save_dir_label.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(save_dir_frame, text="参照...", command=self._choose_directory).pack(side=tk.RIGHT)
        
        # 時間間隔設定
        interval_frame = ttk.Frame(settings_frame)
        interval_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(interval_frame, text="キャプチャ間隔(秒):").pack(side=tk.LEFT)
        self.interval_var = tk.StringVar(value=str(self.capture_interval))
        interval_entry = ttk.Entry(interval_frame, textvariable=self.interval_var, width=5)
        interval_entry.pack(side=tk.LEFT, padx=5)
        
        # キャプチャモード選択
        mode_frame = ttk.Frame(settings_frame)
        mode_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(mode_frame, text="キャプチャモード:").pack(side=tk.LEFT)
        self.mode_var = tk.StringVar(value=self.capture_mode)
        mode_combo = ttk.Combobox(mode_frame, textvariable=self.mode_var, 
                                 values=["全ディスプレイ", "現在のディスプレイ", "選択したアプリのみ"],
                                 state="readonly", width=20)
        mode_combo.pack(side=tk.LEFT, padx=5)
        self.select_app_button = ttk.Button(mode_frame, text="アプリ選択", command=self._select_app)
        self.select_app_button.pack(side=tk.LEFT, padx=5)
        self.select_app_button.config(state=tk.DISABLED)  # 初期状態では無効
        
        # モード変更時のイベント
        mode_combo.bind("<<ComboboxSelected>>", self._on_mode_change)
        
        # 状態表示エリア
        status_frame = ttk.LabelFrame(main_frame, text="状態", padding="10")
        status_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.status_label = ttk.Label(status_frame, text="準備完了")
        self.status_label.pack(pady=10)
        
        self.progress_var = tk.StringVar(value="キャプチャ枚数: 0")
        self.progress_label = ttk.Label(status_frame, textvariable=self.progress_var)
        self.progress_label.pack(pady=10)
        
        # 録画コントロールフレーム
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=10)
        
        self.start_button = ttk.Button(control_frame, text="録画開始", command=self._start_recording)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(control_frame, text="録画停止", command=self._stop_recording)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        self.stop_button.config(state=tk.DISABLED)  # 初期状態では無効
        
        ttk.Button(control_frame, text="終了", command=self._quit_app).pack(side=tk.RIGHT, padx=5)
        
    def _choose_directory(self):
        """保存先ディレクトリ選択ダイアログを表示"""
        dir_path = filedialog.askdirectory(initialdir=self.save_directory)
        if dir_path:  # ユーザーがディレクトリを選択した場合
            self.save_directory = dir_path
            self.save_dir_label.config(text=self.save_directory)
    
    def _on_mode_change(self, event):
        """キャプチャモード変更時のイベントハンドラ"""
        selected_mode = self.mode_var.get()
        if selected_mode == "選択したアプリのみ":
            self.select_app_button.config(state=tk.NORMAL)
        else:
            self.select_app_button.config(state=tk.DISABLED)
    
    def _select_app(self):
        """アプリケーション選択ウィンドウを表示"""
        # サブウィンドウの作成
        app_window = tk.Toplevel(self.root)
        app_window.title("アプリケーション選択")
        app_window.geometry("400x300")
        app_window.transient(self.root)  # メインウィンドウに対する子ウィンドウとして設定
        
        # 実行中のウィンドウのリストを取得
        windows = gw.getAllWindows()
        
        # リストボックスを作成
        listbox_frame = ttk.Frame(app_window, padding="10")
        listbox_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(listbox_frame, text="キャプチャするアプリケーションを選択してください:").pack(anchor=tk.W)
        
        listbox = tk.Listbox(listbox_frame, height=10)
        listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # スクロールバーの追加
        scrollbar = ttk.Scrollbar(listbox, orient=tk.VERTICAL, command=listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        listbox.config(yscrollcommand=scrollbar.set)
        
        # ウィンドウのタイトルをリストに追加
        window_titles = []
        for window in windows:
            if window.title:  # タイトルがある場合のみ
                window_titles.append(window.title)
                listbox.insert(tk.END, window.title)
        
        # 選択ボタン
        button_frame = ttk.Frame(app_window, padding="10")
        button_frame.pack(fill=tk.X)
        
        def on_select():
            """アプリケーション選択時のコールバック"""
            selection = listbox.curselection()
            if selection:
                index = selection[0]
                title = window_titles[index]
                self.selected_window = next((w for w in windows if w.title == title), None)
                if self.selected_window:
                    messagebox.showinfo("選択完了", f"選択されたアプリ: {title}")
                    app_window.destroy()
        
        ttk.Button(button_frame, text="選択", command=on_select).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="キャンセル", command=app_window.destroy).pack(side=tk.RIGHT, padx=5)
        
        # モーダルウィンドウとして表示
        app_window.grab_set()
        self.root.wait_window(app_window)
    
    def _start_recording(self):
        """録画開始処理"""
        try:
            # キャプチャ間隔の取得と検証
            try:
                interval = float(self.interval_var.get())
                if interval <= 0:
                    messagebox.showerror("エラー", "キャプチャ間隔は正の数を入力してください")
                    return
                self.capture_interval = interval
            except ValueError:
                messagebox.showerror("エラー", "キャプチャ間隔は数値を入力してください")
                return
            
            # キャプチャモードの取得
            self.capture_mode = self.mode_var.get()
            
            # アプリが選択されているか確認
            if self.capture_mode == "選択したアプリのみ" and not self.selected_window:
                messagebox.showerror("エラー", "キャプチャするアプリケーションを選択してください")
                return
            
            # 録画フラグをセット
            self.is_recording = True
            
            # UIの更新
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_label.config(text="録画中...")
            self.progress_var.set("キャプチャ枚数: 0")
            
            # 録画用のディレクトリを作成（タイムスタンプ付き）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.current_save_dir = os.path.join(self.save_directory, f"Capture_{timestamp}")
            os.makedirs(self.current_save_dir, exist_ok=True)
            
            # 録画スレッドの開始
            self.capture_thread = threading.Thread(target=self._capture_loop)
            self.capture_thread.daemon = True
            self.capture_thread.start()
            
        except Exception as e:
            messagebox.showerror("エラー", f"録画開始エラー: {str(e)}")
            self._stop_recording()
    
    def _stop_recording(self):
        """録画停止処理"""
        self.is_recording = False
        
        # UIの更新
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_label.config(text="録画停止")
    
    def _capture_loop(self):
        """キャプチャのメインループ (別スレッドで実行)"""
        count = 0
        
        with mss.mss() as sct:
            while self.is_recording:
                try:
                    start_time = time.time()
                    
                    # キャプチャ処理
                    filename = os.path.join(self.current_save_dir, f"capture_{count:05d}.png")
                    
                    if self.capture_mode == "全ディスプレイ":
                        # 全ディスプレイのキャプチャ
                        monitors = sct.monitors[0]  # monitors[0]は全モニターの合成
                        img = sct.grab(monitors)
                        mss.tools.to_png(img.rgb, img.size, output=filename)
                        
                    elif self.capture_mode == "現在のディスプレイ":
                        # アクティブなウィンドウがあるディスプレイを取得
                        active_window = gw.getActiveWindow()
                        if active_window:
                            # アクティブウィンドウがあるモニターを推定
                            # (実際には正確なモニター判定には追加のロジックが必要)
                            monitors = sct.monitors[1]  # とりあえずプライマリモニターを使用
                            img = sct.grab(monitors)
                            mss.tools.to_png(img.rgb, img.size, output=filename)
                        else:
                            # 現在のウィンドウが特定できない場合はプライマリモニター
                            monitors = sct.monitors[1]  # モニター1はプライマリモニター
                            img = sct.grab(monitors)
                            mss.tools.to_png(img.rgb, img.size, output=filename)
                            
                    elif self.capture_mode == "選択したアプリのみ":
                        # 選択したアプリのみのキャプチャ
                        if self.selected_window and self.selected_window.isMinimized:
                            # 最小化されている場合は復元
                            self.selected_window.restore()
                            time.sleep(0.2)  # 復元アニメーションの待機
                        
                        if self.selected_window:
                            left, top, right, bottom = (
                                self.selected_window.left,
                                self.selected_window.top,
                                self.selected_window.right,
                                self.selected_window.bottom
                            )
                            bbox = (left, top, right, bottom)
                            # PyGetWindowの座標をmssに変換
                            monitor = {"top": top, "left": left, "width": right - left, "height": bottom - top}
                            img = sct.grab(monitor)
                            mss.tools.to_png(img.rgb, img.size, output=filename)
                    
                    # カウンターの更新
                    count += 1
                    
                    # UIの更新 (スレッドセーフな方法で)
                    self.root.after(0, lambda c=count: self.progress_var.set(f"キャプチャ枚数: {c}"))
                    
                    # 次のキャプチャまでの待機
                    elapsed = time.time() - start_time
                    if elapsed < self.capture_interval:
                        time.sleep(self.capture_interval - elapsed)
                        
                except Exception as e:
                    print(f"キャプチャエラー: {str(e)}")
                    # UIにエラーを表示
                    self.root.after(0, lambda: messagebox.showerror("エラー", f"キャプチャエラー: {str(e)}"))
                    self.root.after(0, self._stop_recording)
                    break
    
    def _quit_app(self):
        """アプリケーションの終了"""
        if self.is_recording:
            if messagebox.askyesno("確認", "録画中です。終了しますか？"):
                self._stop_recording()
                self.root.quit()
        else:
            self.root.quit()

if __name__ == "__main__":
    # アプリケーションの起動
    root = tk.Tk()
    app = ScreenCaptureApp(root)
    root.mainloop()
