import tkinter as tk
import csv
import datetime
import os
import platform
import ctypes
from tkinter import messagebox, filedialog

class KeyLoggerApp:
    def __init__(self, root):
        """Initialize the keylogger application"""
        self.root = root
        self.root.title("テスト用キーロガー")
        self.root.geometry("600x500")
        
        # ログ記録用リスト
        self.log_entries = []
        
        # 記録状態
        self.is_recording = False
        
        # 記録開始時間
        self.start_time = None
        
        # 現在のマウス位置
        self.mouse_x = 0
        self.mouse_y = 0
        
        # マウス位置更新タイマー
        self.mouse_timer = None
        
        # アクティブウィンドウ情報取得用の設定
        self.setup_platform_specifics()
        
        # UI作成
        self.create_ui()
        
        # イベントをバインド
        self.root.bind("<KeyPress>", self.on_key_press)
        self.root.bind("<Button-1>", lambda e: self.on_mouse_click(e, "左クリック"))
        self.root.bind("<Button-2>", lambda e: self.on_mouse_click(e, "中クリック"))
        self.root.bind("<Button-3>", lambda e: self.on_mouse_click(e, "右クリック"))
        self.root.bind("<Double-Button-1>", lambda e: self.on_mouse_click(e, "左ダブルクリック"))
        self.root.bind("<ButtonRelease-1>", lambda e: self.on_mouse_release(e, "左リリース"))
        self.root.bind("<ButtonRelease-2>", lambda e: self.on_mouse_release(e, "中リリース"))
        self.root.bind("<ButtonRelease-3>", lambda e: self.on_mouse_release(e, "右リリース"))
        self.root.bind("<Motion>", self.on_mouse_move)
        
    def setup_platform_specifics(self):
        """プラットフォーム固有の設定を行う"""
        self.os_type = platform.system()
        
        # Windowsの場合、アクティブウィンドウを取得するための準備
        if self.os_type == "Windows":
            self.user32 = ctypes.windll.user32
        
    def get_active_window_info(self):
        """現在アクティブなウィンドウの情報を取得"""
        window_info = {"title": "不明", "class": "不明"}
        
        try:
            if self.os_type == "Windows":
                # アクティブウィンドウのハンドルを取得
                hwnd = self.user32.GetForegroundWindow()
                
                # ウィンドウタイトルを取得
                length = self.user32.GetWindowTextLengthW(hwnd)
                buff = ctypes.create_unicode_buffer(length + 1)
                self.user32.GetWindowTextW(hwnd, buff, length + 1)
                window_info["title"] = buff.value
                
                # ウィンドウクラス名を取得
                class_buff = ctypes.create_unicode_buffer(256)
                self.user32.GetClassNameW(hwnd, class_buff, 256)
                window_info["class"] = class_buff.value
                
            elif self.os_type == "Darwin":  # macOS
                # macOSの場合はAppleScriptを使用するなどの方法があるが、ここでは簡略化
                window_info["title"] = "macOS - アクセス制限あり"
                
            elif self.os_type == "Linux":
                # Linuxの場合はxdotoolなどの外部コマンドを使用する方法があるが、ここでは簡略化
                window_info["title"] = "Linux - アクセス制限あり"
                
        except Exception as e:
            window_info["title"] = f"エラー: {str(e)}"
            
        return window_info

    def create_ui(self):
        """Create the user interface elements"""
        # メインフレーム
        main_frame = tk.Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 上部フレーム - コントロール
        control_frame = tk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=10)
        
        # 記録開始/停止ボタン
        self.record_button = tk.Button(control_frame, text="記録開始", command=self.toggle_recording, bg="green", fg="white", width=10)
        self.record_button.pack(side=tk.LEFT, padx=5)
        
        # CSVに保存ボタン
        self.save_button = tk.Button(control_frame, text="CSVに保存", command=self.save_to_csv, width=10)
        self.save_button.pack(side=tk.LEFT, padx=5)
        self.save_button["state"] = "disabled"
        
        # クリアボタン
        self.clear_button = tk.Button(control_frame, text="クリア", command=self.clear_log, width=10)
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        # 状態表示ラベル
        self.status_label = tk.Label(control_frame, text="待機中...", fg="blue")
        self.status_label.pack(side=tk.RIGHT, padx=5)
        
        # 説明ラベル
        description = "このアプリケーションはテスト目的でキー操作とマウス操作を記録します。\n記録を開始し、テストを実行してください。完了したら記録を停止し、CSVに保存できます。"
        desc_label = tk.Label(main_frame, text=description, justify=tk.LEFT, wraplength=580)
        desc_label.pack(fill=tk.X, pady=10)
        
        # マウス情報表示エリア
        mouse_frame = tk.Frame(main_frame)
        mouse_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(mouse_frame, text="マウス座標:").pack(side=tk.LEFT, padx=5)
        self.mouse_pos_label = tk.Label(mouse_frame, text="X: 0, Y: 0")
        self.mouse_pos_label.pack(side=tk.LEFT, padx=5)
        
        tk.Label(mouse_frame, text="アクティブウィンドウ:").pack(side=tk.LEFT, padx=15)
        self.active_window_label = tk.Label(mouse_frame, text="不明", wraplength=250)
        self.active_window_label.pack(side=tk.LEFT, padx=5)
        
        # ログ表示エリア
        log_frame = tk.Frame(main_frame, bd=1, relief=tk.SUNKEN)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # スクロールバー
        scrollbar = tk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # ログ表示リストボックス
        self.log_listbox = tk.Listbox(log_frame, yscrollcommand=scrollbar.set, font=("Courier", 10))
        self.log_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_listbox.yview)
        
        # ログ表示ヘッダー
        self.log_listbox.insert(tk.END, "時間\t\tイベント\t\tキー/座標\t\tウィンドウ")
        self.log_listbox.insert(tk.END, "-" * 100)
    
    def toggle_recording(self):
        """Toggle between recording and not recording states"""
        if self.is_recording:
            # 記録停止
            self.is_recording = False
            self.record_button.config(text="記録開始", bg="green")
            self.status_label.config(text="記録停止")
            self.save_button["state"] = "normal"
            
            # マウス位置更新タイマーの停止
            if self.mouse_timer:
                self.root.after_cancel(self.mouse_timer)
                self.mouse_timer = None
            
            # 最終行の追加
            end_time = datetime.datetime.now()
            elapsed = (end_time - self.start_time).total_seconds()
            self.log_entries.append({
                "timestamp": end_time.strftime("%H:%M:%S.%f")[:-3],
                "event": "RECORDING_END",
                "key": "",
                "elapsed": round(elapsed, 3),
                "x": 0,
                "y": 0,
                "window_title": "",
                "window_class": ""
            })
            self.log_listbox.insert(tk.END, f"{end_time.strftime('%H:%M:%S.%f')[:-3]}\t記録終了")
        else:
            # 記録開始
            self.is_recording = True
            self.start_time = datetime.datetime.now()
            self.record_button.config(text="記録停止", bg="red")
            self.status_label.config(text="記録中...")
            self.save_button["state"] = "disabled"
            
            # アクティブウィンドウ情報の取得
            active_window = self.get_active_window_info()
            
            # 最初の行の追加
            self.log_entries = []  # リセット
            self.log_entries.append({
                "timestamp": self.start_time.strftime("%H:%M:%S.%f")[:-3],
                "event": "RECORDING_START",
                "key": "",
                "elapsed": 0.0,
                "x": 0,
                "y": 0,
                "window_title": active_window["title"],
                "window_class": active_window["class"]
            })
            self.log_listbox.insert(tk.END, f"{self.start_time.strftime('%H:%M:%S.%f')[:-3]}\t記録開始")
            
            # マウス位置更新タイマーの開始
            self.update_mouse_info()
    
    def update_mouse_info(self):
        """マウス情報を更新するタイマー処理"""
        if not self.is_recording:
            return
            
        # アクティブウィンドウ情報を更新
        active_window = self.get_active_window_info()
        self.active_window_label.config(text=active_window["title"])
        
        # マウス位置情報を更新
        self.mouse_pos_label.config(text=f"X: {self.mouse_x}, Y: {self.mouse_y}")
        
        # 1秒後に再度実行
        self.mouse_timer = self.root.after(1000, self.update_mouse_info)
    
    def on_key_press(self, event):
        """Handle key press events"""
        if not self.is_recording:
            return
            
        # 現在時刻とキー情報の取得
        current_time = datetime.datetime.now()
        elapsed = (current_time - self.start_time).total_seconds()
        key_name = event.keysym
        
        # 特殊キーの処理
        if len(key_name) == 1:
            display_key = key_name
        else:
            display_key = f"<{key_name}>"
        
        # アクティブウィンドウ情報の取得
        active_window = self.get_active_window_info()
        
        # ログエントリの追加
        self.log_entries.append({
            "timestamp": current_time.strftime("%H:%M:%S.%f")[:-3],
            "event": "KEY_PRESS",
            "key": key_name,
            "elapsed": round(elapsed, 3),
            "x": event.x_root,
            "y": event.y_root,
            "window_title": active_window["title"],
            "window_class": active_window["class"]
        })
        
        # リストボックスに表示
        self.log_listbox.insert(tk.END, f"{current_time.strftime('%H:%M:%S.%f')[:-3]}\tKEY_PRESS\t{display_key}\t{active_window['title'][:30]}")
        self.log_listbox.see(tk.END)  # 自動スクロール
    
    def on_mouse_move(self, event):
        """マウス移動イベントの処理"""
        self.mouse_x = event.x_root
        self.mouse_y = event.y_root
        
        # マウス移動イベントはログに記録しない（多すぎるため）
        # ただし、必要に応じて記録する場合は以下のコメントを解除
        '''
        if self.is_recording:
            # 移動イベントの多くを間引く（例: 100pxごとに記録する）
            if abs(self.last_x - event.x_root) > 100 or abs(self.last_y - event.y_root) > 100:
                # アクティブウィンドウ情報の取得
                active_window = self.get_active_window_info()
                
                # 現在時刻の取得
                current_time = datetime.datetime.now()
                elapsed = (current_time - self.start_time).total_seconds()
                
                # ログエントリの追加
                self.log_entries.append({
                    "timestamp": current_time.strftime("%H:%M:%S.%f")[:-3],
                    "event": "MOUSE_MOVE",
                    "key": "",
                    "elapsed": round(elapsed, 3),
                    "x": event.x_root,
                    "y": event.y_root,
                    "window_title": active_window["title"],
                    "window_class": active_window["class"]
                })
                
                self.last_x = event.x_root
                self.last_y = event.y_root
        '''
    
    def on_mouse_click(self, event, button_type):
        """マウスクリックイベントの処理"""
        if not self.is_recording:
            return
            
        # 現在時刻の取得
        current_time = datetime.datetime.now()
        elapsed = (current_time - self.start_time).total_seconds()
        
        # アクティブウィンドウ情報の取得
        active_window = self.get_active_window_info()
        
        # ログエントリの追加
        self.log_entries.append({
            "timestamp": current_time.strftime("%H:%M:%S.%f")[:-3],
            "event": "MOUSE_CLICK",
            "key": button_type,
            "elapsed": round(elapsed, 3),
            "x": event.x_root,
            "y": event.y_root,
            "window_title": active_window["title"],
            "window_class": active_window["class"]
        })
        
        # リストボックスに表示
        click_info = f"{button_type} (X:{event.x_root}, Y:{event.y_root})"
        self.log_listbox.insert(tk.END, f"{current_time.strftime('%H:%M:%S.%f')[:-3]}\tMOUSE_CLICK\t{click_info}\t{active_window['title'][:30]}")
        self.log_listbox.see(tk.END)  # 自動スクロール
    
    def on_mouse_release(self, event, button_type):
        """マウスボタンリリースイベントの処理"""
        if not self.is_recording:
            return
            
        # 現在時刻の取得
        current_time = datetime.datetime.now()
        elapsed = (current_time - self.start_time).total_seconds()
        
        # アクティブウィンドウ情報の取得
        active_window = self.get_active_window_info()
        
        # ログエントリの追加
        self.log_entries.append({
            "timestamp": current_time.strftime("%H:%M:%S.%f")[:-3],
            "event": "MOUSE_RELEASE",
            "key": button_type,
            "elapsed": round(elapsed, 3),
            "x": event.x_root,
            "y": event.y_root,
            "window_title": active_window["title"],
            "window_class": active_window["class"]
        })
        
        # リストボックスに表示
        release_info = f"{button_type} (X:{event.x_root}, Y:{event.y_root})"
        self.log_listbox.insert(tk.END, f"{current_time.strftime('%H:%M:%S.%f')[:-3]}\tMOUSE_RELEASE\t{release_info}\t{active_window['title'][:30]}")
        self.log_listbox.see(tk.END)  # 自動スクロール
    
    def save_to_csv(self):
        """Save recorded log entries to a CSV file"""
        if not self.log_entries:
            messagebox.showinfo("情報", "保存するログがありません。")
            return
            
        # ファイル保存ダイアログ
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"eventlog_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['timestamp', 'event', 'key', 'elapsed', 'x', 'y', 'window_title', 'window_class']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for entry in self.log_entries:
                    writer.writerow(entry)
                    
            messagebox.showinfo("成功", f"ログが保存されました: {file_path}")
        except Exception as e:
            messagebox.showerror("エラー", f"ファイル保存中にエラーが発生しました: {str(e)}")
    
    def clear_log(self):
        """Clear the current log entries"""
        self.log_entries = []
        self.log_listbox.delete(2, tk.END)  # ヘッダー行は保持
        self.status_label.config(text="ログをクリアしました")
        self.save_button["state"] = "disabled"
        
        # マウス位置とアクティブウィンドウ情報もリセット
        self.mouse_pos_label.config(text="X: 0, Y: 0")
        self.active_window_label.config(text="不明")

if __name__ == "__main__":
    root = tk.Tk()
    app = KeyLoggerApp(root)
    
    # アプリケーション終了時の確認
    def on_closing():
        if messagebox.askokcancel("終了確認", "アプリケーションを終了してもよろしいですか？"):
            if app.is_recording:
                app.toggle_recording()  # 記録中
