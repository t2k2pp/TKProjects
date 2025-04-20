import tkinter as tk
from tkinter import ttk
import psutil
import win32gui
import win32process
import win32con
import win32api
import threading
import time
import os
from PIL import Image, ImageTk
import sys
import tempfile
from functools import partial

class TaskbarApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Tkinterタスクバー")
        self.root.overrideredirect(True)  # タイトルバーを非表示
        self.root.attributes("-topmost", True)  # 常に最前面に表示
        
        # 設定値
        self.position = "bottom"  # タスクバーの位置（"bottom", "top", "left", "right"）
        self.update_interval = 2  # プロセス更新間隔（秒）
        self.display_mode = "compact"  # 表示モード（"compact": 詰めて表示, "paged": ページ切り替え）
        self.is_visible = True  # タスクバーの表示状態
        self.current_page = 0  # 現在のページ（ページ切り替えモード用）
        self.buttons_per_page = 10  # 1ページあたりのボタン数
        self.taskbar_size = 40  # タスクバーのサイズ（幅または高さ）
        self.button_size = 40  # ボタンのサイズ
        self.tasks = []  # 実行中のタスク
        self.task_buttons = []  # タスクボタンのリスト
        
        # 設定パネル
        self.settings_frame = None
        self.settings_visible = False
        
        # メインフレーム作成
        self.main_frame = tk.Frame(self.root, bg="#1E1E1E")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # ボタンフレーム作成（タスクボタン用）
        self.button_frame = tk.Frame(self.main_frame, bg="#1E1E1E")
        
        # コントロールフレーム作成（設定ボタンなど用）
        self.control_frame = tk.Frame(self.main_frame, bg="#1E1E1E")
        
        # ドラッグ用の変数
        self.drag_x = 0
        self.drag_y = 0
        self.dragging = False
        
        # ウィンドウ位置とサイズの初期設定
        self.set_position(self.position)
        
        # コントロールボタンの作成
        self.create_control_buttons()
        
        # プロセス監視スレッドの開始
        self.stop_thread = False
        self.monitor_thread = threading.Thread(target=self.monitor_processes)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        # ドラッグ可能にする
        self.control_frame.bind("<ButtonPress-1>", self.start_drag)
        self.control_frame.bind("<ButtonRelease-1>", self.stop_drag)
        self.control_frame.bind("<B1-Motion>", self.on_drag)
        
        # ウィンドウ終了時の処理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # ESCキーで設定パネルを閉じる
        self.root.bind("<Escape>", lambda e: self.toggle_settings() if self.settings_visible else None)
        
    def set_position(self, position):
        """タスクバーの位置を設定する"""
        self.position = position
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # メインフレームとボタンフレームをいったんアンパック
        self.main_frame.pack_forget()
        self.button_frame.pack_forget()
        self.control_frame.pack_forget()
        
        if position == "bottom":
            # サイズと位置の設定
            self.root.geometry(f"{screen_width}x{self.taskbar_size}+0+{screen_height-self.taskbar_size}")
            # フレームの配置
            self.main_frame.pack(fill=tk.BOTH, expand=True)
            self.button_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.control_frame.pack(side=tk.RIGHT, fill=tk.Y)
            # ボタンの向き
            self.button_orientation = "horizontal"
        
        elif position == "top":
            # サイズと位置の設定
            self.root.geometry(f"{screen_width}x{self.taskbar_size}+0+0")
            # フレームの配置
            self.main_frame.pack(fill=tk.BOTH, expand=True)
            self.button_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.control_frame.pack(side=tk.RIGHT, fill=tk.Y)
            # ボタンの向き
            self.button_orientation = "horizontal"
        
        elif position == "left":
            # サイズと位置の設定
            self.root.geometry(f"{self.taskbar_size}x{screen_height}+0+0")
            # フレームの配置
            self.main_frame.pack(fill=tk.BOTH, expand=True)
            self.button_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
            self.control_frame.pack(side=tk.BOTTOM, fill=tk.X)
            # ボタンの向き
            self.button_orientation = "vertical"
        
        elif position == "right":
            # サイズと位置の設定
            self.root.geometry(f"{self.taskbar_size}x{screen_height}+{screen_width-self.taskbar_size}+0")
            # フレームの配置
            self.main_frame.pack(fill=tk.BOTH, expand=True)
            self.button_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
            self.control_frame.pack(side=tk.BOTTOM, fill=tk.X)
            # ボタンの向き
            self.button_orientation = "vertical"
    
    def create_control_buttons(self):
        """コントロールボタンを作成する"""
        # 既存のコントロールボタンを削除
        for widget in self.control_frame.winfo_children():
            widget.destroy()
        
        # 設定ボタン
        settings_button = tk.Button(self.control_frame, text="⚙", font=("Arial", 12), 
                                    bg="#1E1E1E", fg="white", bd=0, padx=5, pady=5,
                                    command=self.toggle_settings)
        settings_button.pack(side=tk.TOP if self.button_orientation == "vertical" else tk.LEFT)
        
        # 表示切替ボタン
        toggle_button = tk.Button(self.control_frame, text="◀" if self.is_visible else "▶", font=("Arial", 12), 
                                  bg="#1E1E1E", fg="white", bd=0, padx=5, pady=5,
                                  command=self.toggle_visibility)
        toggle_button.pack(side=tk.TOP if self.button_orientation == "vertical" else tk.LEFT)
        
        # ページ切替ボタン（ページモードのみ）
        if self.display_mode == "paged":
            prev_button = tk.Button(self.control_frame, text="◀", font=("Arial", 12), 
                                    bg="#1E1E1E", fg="white", bd=0, padx=5, pady=5,
                                    command=self.prev_page)
            prev_button.pack(side=tk.TOP if self.button_orientation == "vertical" else tk.LEFT)
            
            next_button = tk.Button(self.control_frame, text="▶", font=("Arial", 12), 
                                    bg="#1E1E1E", fg="white", bd=0, padx=5, pady=5,
                                    command=self.next_page)
            next_button.pack(side=tk.TOP if self.button_orientation == "vertical" else tk.LEFT)
            
            # ページ表示ラベル
            self.page_label = tk.Label(self.control_frame, text=f"{self.current_page+1}", 
                                      bg="#1E1E1E", fg="white", font=("Arial", 10))
            self.page_label.pack(side=tk.TOP if self.button_orientation == "vertical" else tk.LEFT)
        
        # 終了ボタン
        exit_button = tk.Button(self.control_frame, text="✕", font=("Arial", 12), 
                                bg="#1E1E1E", fg="white", bd=0, padx=5, pady=5,
                                command=self.on_closing)
        exit_button.pack(side=tk.TOP if self.button_orientation == "vertical" else tk.LEFT)
    
    def toggle_settings(self):
        """設定パネルの表示/非表示を切り替える"""
        if self.settings_visible:
            if self.settings_frame:
                self.settings_frame.destroy()
                self.settings_frame = None
            self.settings_visible = False
        else:
            # 設定パネルの作成
            self.settings_frame = tk.Toplevel(self.root)
            self.settings_frame.title("設定")
            self.settings_frame.attributes("-topmost", True)
            
            # 設定フレーム
            settings_content = tk.Frame(self.settings_frame, padx=10, pady=10)
            settings_content.pack(fill=tk.BOTH, expand=True)
            
            # 位置設定
            position_frame = tk.LabelFrame(settings_content, text="タスクバーの位置", padx=5, pady=5)
            position_frame.pack(fill=tk.X, pady=5)
            
            position_var = tk.StringVar(value=self.position)
            positions = [("下", "bottom"), ("上", "top"), ("左", "left"), ("右", "right")]
            
            for text, value in positions:
                rb = tk.Radiobutton(position_frame, text=text, variable=position_var, value=value)
                rb.pack(anchor=tk.W)
            
            # 表示モード設定
            mode_frame = tk.LabelFrame(settings_content, text="表示モード", padx=5, pady=5)
            mode_frame.pack(fill=tk.X, pady=5)
            
            mode_var = tk.StringVar(value=self.display_mode)
            modes = [("詰めて表示", "compact"), ("ページ切り替え", "paged")]
            
            for text, value in modes:
                rb = tk.Radiobutton(mode_frame, text=text, variable=mode_var, value=value)
                rb.pack(anchor=tk.W)
            
            # ページあたりボタン数設定
            buttons_frame = tk.LabelFrame(settings_content, text="1ページあたりのボタン数", padx=5, pady=5)
            buttons_frame.pack(fill=tk.X, pady=5)
            
            buttons_var = tk.IntVar(value=self.buttons_per_page)
            buttons_scale = tk.Scale(buttons_frame, from_=5, to=20, orient=tk.HORIZONTAL, variable=buttons_var)
            buttons_scale.pack(fill=tk.X)
            
            # 更新間隔設定
            interval_frame = tk.LabelFrame(settings_content, text="更新間隔（秒）", padx=5, pady=5)
            interval_frame.pack(fill=tk.X, pady=5)
            
            interval_var = tk.IntVar(value=self.update_interval)
            interval_scale = tk.Scale(interval_frame, from_=1, to=10, orient=tk.HORIZONTAL, variable=interval_var)
            interval_scale.pack(fill=tk.X)
            
            # 設定を適用するボタン
            apply_button = tk.Button(settings_content, text="適用", padx=10, pady=5,
                                    command=lambda: self.apply_settings(
                                        position_var.get(),
                                        mode_var.get(),
                                        buttons_var.get(),
                                        interval_var.get()
                                    ))
            apply_button.pack(pady=10)
            
            self.settings_visible = True
            
            # ESCキーで設定パネルを閉じる
            self.settings_frame.bind("<Escape>", lambda e: self.toggle_settings())
            
            # ウィンドウが閉じられたときの処理
            self.settings_frame.protocol("WM_DELETE_WINDOW", self.toggle_settings)
    
    def apply_settings(self, position, display_mode, buttons_per_page, update_interval):
        """設定を適用する"""
        # 値を更新
        self.buttons_per_page = buttons_per_page
        self.update_interval = update_interval
        
        # 表示モードが変更された場合
        if self.display_mode != display_mode:
            self.display_mode = display_mode
            self.current_page = 0  # ページをリセット
            
        # 位置が変更された場合
        if self.position != position:
            self.position = position
            self.set_position(position)
        
        # コントロールボタンを再作成
        self.create_control_buttons()
        
        # タスクボタンを更新
        self.update_task_buttons()
        
        # 設定パネルを閉じる
        self.toggle_settings()
    
    def toggle_visibility(self):
        """タスクバーの表示/非表示を切り替える"""
        if self.is_visible:
            # 最小限の表示にする
            if self.position in ["bottom", "top"]:
                current_height = self.taskbar_size
                new_height = 5  # 最小化時の高さ
                
                if self.position == "bottom":
                    screen_height = self.root.winfo_screenheight()
                    self.root.geometry(f"{self.root.winfo_width()}x{new_height}+0+{screen_height-new_height}")
                else:  # top
                    self.root.geometry(f"{self.root.winfo_width()}x{new_height}+0+0")
                
                # ボタンフレームを非表示にする
                self.button_frame.pack_forget()
                
            else:  # left, right
                current_width = self.taskbar_size
                new_width = 5  # 最小化時の幅
                
                if self.position == "left":
                    self.root.geometry(f"{new_width}x{self.root.winfo_height()}+0+0")
                else:  # right
                    screen_width = self.root.winfo_screenwidth()
                    self.root.geometry(f"{new_width}x{self.root.winfo_height()}+{screen_width-new_width}+0")
                
                # ボタンフレームを非表示にする
                self.button_frame.pack_forget()
            
            self.is_visible = False
        else:
            # 元のサイズに戻す
            self.set_position(self.position)
            self.is_visible = True
        
        # コントロールボタンを更新
        self.create_control_buttons()
    
    def prev_page(self):
        """前のページに移動"""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_task_buttons()
            if hasattr(self, 'page_label'):
                self.page_label.config(text=f"{self.current_page+1}")
    
    def next_page(self):
        """次のページに移動"""
        total_pages = max(1, (len(self.tasks) + self.buttons_per_page - 1) // self.buttons_per_page)
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.update_task_buttons()
            if hasattr(self, 'page_label'):
                self.page_label.config(text=f"{self.current_page+1}")
    
    def start_drag(self, event):
        """ドラッグ開始"""
        self.drag_x = event.x
        self.drag_y = event.y
        self.dragging = True
    
    def stop_drag(self, event):
        """ドラッグ終了"""
        self.dragging = False
    
    def on_drag(self, event):
        """ドラッグ中の処理"""
        if self.dragging:
            x = self.root.winfo_x() + (event.x - self.drag_x)
            y = self.root.winfo_y() + (event.y - self.drag_y)
            self.root.geometry(f"+{x}+{y}")
    
    def monitor_processes(self):
        """実行中のプロセスを監視する"""
        while not self.stop_thread:
            # ウィンドウを持つプロセスのリストを取得
            windowed_processes = self.get_windowed_processes()
            
            # リストが変更されていたら更新
            if self.tasks != windowed_processes:
                self.tasks = windowed_processes
                self.root.after(0, self.update_task_buttons)
            
            # 指定された間隔で待機
            time.sleep(self.update_interval)
    
    def get_windowed_processes(self):
        """ウィンドウを持つプロセスを取得"""
        windowed_processes = []
        
        def enum_windows_proc(hwnd, lParam):
            """ウィンドウ列挙用コールバック関数"""
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                # ウィンドウの状態を確認（最小化されているものも含める）
                # このアプリケーション自体は除外
                if hwnd != self.root.winfo_id():
                    try:
                        # ウィンドウのプロセスIDを取得
                        _, process_id = win32process.GetWindowThreadProcessId(hwnd)
                        title = win32gui.GetWindowText(hwnd)
                        
                        # プロセス情報を取得
                        try:
                            process = psutil.Process(process_id)
                            process_name = process.name()
                            
                            # ウィンドウサイズを取得
                            rect = win32gui.GetWindowRect(hwnd)
                            width = rect[2] - rect[0]
                            height = rect[3] - rect[1]
                            
                            # 実際に表示されているウィンドウのみ（幅と高さがある程度あるもの）
                            if width > 100 and height > 100:
                                windowed_processes.append({
                                    'hwnd': hwnd,
                                    'title': title,
                                    'process_id': process_id,
                                    'process_name': process_name
                                })
                        except psutil.NoSuchProcess:
                            pass
                    except Exception as e:
                        print(f"Error processing window {hwnd}: {e}")
            return True
        
        # すべてのウィンドウを列挙
        win32gui.EnumWindows(enum_windows_proc, None)
        return windowed_processes
    
    def update_task_buttons(self):
        """タスクボタンを更新する"""
        # 既存のボタンをクリア
        for button in self.task_buttons:
            button.destroy()
        self.task_buttons = []
        
        # タスクがない場合は何もしない
        if not self.tasks:
            return
        
        # 表示するタスクを決定
        if self.display_mode == "compact":
            # すべてのタスクを表示
            display_tasks = self.tasks
        else:  # paged
            # 現在のページのタスクのみ表示
            start_idx = self.current_page * self.buttons_per_page
            end_idx = start_idx + self.buttons_per_page
            display_tasks = self.tasks[start_idx:end_idx]
        
        # 新しいボタンを作成
        for task in display_tasks:
            # ボタンラベルの設定（プロセス名を優先、長すぎる場合はトリミング）
            label = task['process_name'].replace('.exe', '')
            if not label:
                label = task['title']
            if len(label) > 15:
                label = label[:12] + "..."
            
            # ボタンの作成
            button = tk.Button(
                self.button_frame,
                text=label,
                bg="#2D2D2D",
                fg="white",
                bd=1,
                relief=tk.RAISED,
                padx=5,
                pady=5,
                command=partial(self.focus_window, task['hwnd'])
            )
            
            # ボタンの配置
            if self.button_orientation == "horizontal":
                button.pack(side=tk.LEFT, padx=2, pady=2)
            else:  # vertical
                button.pack(side=tk.TOP, padx=2, pady=2)
            
            self.task_buttons.append(button)
    
    def focus_window(self, hwnd):
        """指定されたウィンドウにフォーカスを当てる"""
        try:
            # ウィンドウが最小化されている場合は元に戻す
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            
            # ウィンドウを前面に表示
            win32gui.SetForegroundWindow(hwnd)
        except Exception as e:
            print(f"Error focusing window {hwnd}: {e}")
    
    def on_closing(self):
        """アプリケーション終了時の処理"""
        self.stop_thread = True
        # スレッドが終了するのを少し待つ
        if self.monitor_thread.is_alive():
            self.monitor_thread.join(1.0)
        self.root.destroy()
        sys.exit(0)

def main():
    # ルートウィンドウの作成
    root = tk.Tk()
    
    # DPIスケーリングの設定
    try:
        # Windowsの場合、DPIスケーリングを有効化
        if os.name == 'nt':
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    
    # アプリケーションの作成
    app = TaskbarApp(root)
    
    # イベントループの開始
    root.mainloop()

if __name__ == "__main__":
    main()
