import tkinter as tk
from tkinter import ttk
import psutil
import win32gui
import win32process
import win32con
import win32api
import win32ui # create_default_icon と get_window_icon (GetDIBits) で必要
import threading
import time
import os
from PIL import Image, ImageTk, ImageDraw # Pillowライブラリ
import sys
import tempfile
import ctypes # 今は未使用だが、将来的な拡張のために残しても良い
from functools import partial
import io

class TaskbarApp:
    def __init__(self, root):
        # print(">>> ENTERING __init__") # デバッグ出力は一旦コメントアウト
        self.root = root
        self.root.title("Tkinterタスクバー")
        self.root.overrideredirect(True)  # タイトルバーを非表示
        self.root.attributes("-topmost", True)  # 常に最前面に表示

        # --- 設定値 ---
        self.position = "bottom"  # タスクバーの位置
        self.update_interval = 2  # プロセス更新間隔（秒）
        self.display_mode = "paged"  # 表示モード ("compact", "paged")
        self.label_mode = "title"   # ラベル表示モード ("process", "title")
        self.is_visible = True      # タスクバーの表示状態
        self.current_page = 0     # 現在のページ（ページ切り替えモード用）
        self.buttons_per_page = 12 # 1ページあたりのボタン数
        self.taskbar_size = 40    # タスクバーのサイズ（幅または高さ）
        self.button_size = 40     # ボタンの高さ (アイコン+テキスト領域含む)
        self.button_width = 120   # ページモード時のボタン幅
        # --- 状態変数 ---
        self.tasks = []           # 実行中のタスク情報リスト
        self.task_buttons = []    # タスクボタンウィジェットのリスト
        self.icon_cache = {}      # アイコン画像キャッシュ (PhotoImage)
        self.start_button_widget = None # スタートボタンウィジェット参照用
        # --- 設定パネル関連 ---
        self.settings_frame = None
        self.settings_visible = False
        # --- ドラッグ関連 ---
        self.drag_x = 0
        self.drag_y = 0
        self.dragging = False
        # --- スレッド関連 ---
        self.stop_thread = False
        self.monitor_thread = None

        # --- UI要素の作成 ---
        # メインフレーム
        self.main_frame = tk.Frame(self.root, bg="#1E1E1E")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # ボタンフレーム（タスクボタン用）
        self.button_frame = tk.Frame(self.main_frame, bg="#1E1E1E")

        # コントロールフレーム（設定ボタンなど用）
        self.control_frame = tk.Frame(self.main_frame, bg="#1E1E1E")

        # ウィンドウ位置とレイアウトの初期設定
        self.set_position(self.position)

        # プロセス監視スレッドの開始
        self.monitor_thread = threading.Thread(target=self.monitor_processes)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

        # ドラッグイベントのバインド (コントロールフレームにバインド)
        self.control_frame.bind("<ButtonPress-1>", self.start_drag)
        self.control_frame.bind("<ButtonRelease-1>", self.stop_drag)
        self.control_frame.bind("<B1-Motion>", self.on_drag)

        # ウィンドウ終了時の処理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # ESCキーで設定パネルを閉じる
        self.root.bind("<Escape>", lambda e: self.toggle_settings() if self.settings_visible else None)
        # print("<<< LEAVING __init__")

    def set_position(self, position):
        # print(f">>> ENTERING set_position(position='{position}')")
        """タスクバーの位置とレイアウトを設定する"""
        self.position = position
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # 既存のフレームをアンパック
        self.main_frame.pack_forget()
        if self.button_frame.winfo_manager():
            self.button_frame.pack_forget()
        if self.control_frame.winfo_manager():
            self.control_frame.pack_forget()

        # ★★★ ボタンフレーム内のすべての子ウィジェットを削除 ★★★
        for widget in self.button_frame.winfo_children():
            widget.destroy()
        self.start_button_widget = None # スタートボタン参照クリア
        self.task_buttons = []          # タスクボタンリストクリア

        # ウィンドウジオメトリ設定
        if position == "bottom":
            self.root.geometry(f"{screen_width}x{self.taskbar_size}+0+{screen_height-self.taskbar_size}")
            self.button_orientation = "horizontal"
        elif position == "top":
            self.root.geometry(f"{screen_width}x{self.taskbar_size}+0+0")
            self.button_orientation = "horizontal"
        elif position == "left":
            self.root.geometry(f"{self.taskbar_size}x{screen_height}+0+0")
            self.button_orientation = "vertical"
        elif position == "right":
            self.root.geometry(f"{self.taskbar_size}x{screen_height}+{screen_width-self.taskbar_size}+0")
            self.button_orientation = "vertical"

        # フレームの再配置
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        if self.button_orientation == "horizontal":
            # 水平配置: [Button Frame (Start + Tasks)] [Control Frame]
            self.button_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.control_frame.pack(side=tk.RIGHT, fill=tk.Y)
        else: # vertical
            # 垂直配置: [Button Frame (Start + Tasks)]
            #           [Control Frame]
            self.button_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
            self.control_frame.pack(side=tk.BOTTOM, fill=tk.X)

        # 新しいスタートボタンを作成して配置 (button_frame が空の状態で)
        self.create_start_button()

        # コントロールボタンを(再)作成
        self.create_control_buttons()

        # タスクボタンを更新 (button_frame にタスクボタンを追加)
        self.update_task_buttons()
        # print(f"<<< LEAVING set_position(position='{position}')")

    def create_start_button(self):
        # print(">>> ENTERING create_start_button")
        """スタートボタンを作成する"""
        # print("Creating start button")
        # スタートボタンウィジェット参照を更新
        self.start_button_widget = tk.Button(self.button_frame, text="スタート",
                              bg="#0078D7", fg="white", bd=0,
                              padx=10, pady=5,
                              command=self.show_start_menu)

        # ボタンの配置
        if self.button_orientation == "horizontal":
            self.start_button_widget.pack(side=tk.LEFT, padx=2, pady=2)
        else:  # vertical
            self.start_button_widget.pack(side=tk.TOP, padx=2, pady=2, fill=tk.X) # 縦置きは幅いっぱいに広げる例

        # print(f"    Start button created: {self.start_button_widget}")
        # print("<<< LEAVING create_start_button")

    def show_start_menu(self):
        """スタートメニューを表示する (Win + S の代替)"""
        try:
            # 単純に Win キーを送信してスタートメニューを開く
            win32api.keybd_event(win32con.VK_LWIN, 0, 0, 0)
            win32api.keybd_event(win32con.VK_LWIN, 0, win32con.KEYEVENTF_KEYUP, 0)
        except Exception as e:
            print(f"Error showing start menu: {e}")

    def create_control_buttons(self):
        # print(">>> ENTERING create_control_buttons")
        """コントロールボタンを作成する"""
        # 既存のコントロールボタンを削除
        for widget in self.control_frame.winfo_children():
            widget.destroy()

        pack_side = tk.TOP if self.button_orientation == "vertical" else tk.LEFT
        anchor_side = tk.N if self.button_orientation == "vertical" else tk.W # アンカーも考慮

        # 設定ボタン
        settings_button = tk.Button(self.control_frame, text="⚙", font=("Arial", 12),
                                    bg="#1E1E1E", fg="white", bd=0, padx=5, pady=5,
                                    command=self.toggle_settings)
        settings_button.pack(side=pack_side, anchor=anchor_side)

        # 表示切替ボタン
        toggle_text = "🥚" if self.is_visible else "🐣"
        toggle_button = tk.Button(self.control_frame, text=toggle_text, font=("Arial", 12),
                                  bg="#1E1E1E", fg="white", bd=0, padx=5, pady=5,
                                  command=self.toggle_visibility)
        toggle_button.pack(side=pack_side, anchor=anchor_side)

        # ページ切替ボタン（ページモードのみ）
        if self.display_mode == "paged":
            prev_button = tk.Button(self.control_frame, text="◀", font=("Arial", 12),
                                    bg="#1E1E1E", fg="white", bd=0, padx=5, pady=5,
                                    command=self.prev_page)
            prev_button.pack(side=pack_side, anchor=anchor_side)

            next_button = tk.Button(self.control_frame, text="▶", font=("Arial", 12),
                                    bg="#1E1E1E", fg="white", bd=0, padx=5, pady=5,
                                    command=self.next_page)
            next_button.pack(side=pack_side, anchor=anchor_side)

            # ページ表示ラベル
            self.page_label = tk.Label(self.control_frame, text=f"{self.current_page+1}",
                                       bg="#1E1E1E", fg="white", font=("Arial", 10))
            self.page_label.pack(side=pack_side, anchor=anchor_side)

        # 終了ボタン
        exit_button = tk.Button(self.control_frame, text="✕", font=("Arial", 12),
                                bg="#1E1E1E", fg="white", bd=0, padx=5, pady=5,
                                command=self.on_closing)
        # 終了ボタンは反対側に配置する（見た目のため）
        exit_pack_side = tk.BOTTOM if self.button_orientation == "vertical" else tk.RIGHT
        exit_anchor_side = tk.S if self.button_orientation == "vertical" else tk.E
        exit_button.pack(side=exit_pack_side, anchor=exit_anchor_side)

        # print("<<< LEAVING create_control_buttons")

    def toggle_settings(self):
        """設定パネルの表示/非表示を切り替える"""
        if self.settings_visible:
            if self.settings_frame:
                self.settings_frame.destroy()
                self.settings_frame = None
            self.settings_visible = False
        else:
            # 設定パネル (Toplevelウィンドウ) の作成
            self.settings_frame = tk.Toplevel(self.root)
            self.settings_frame.title("設定")
            self.settings_frame.attributes("-topmost", True)
            # self.settings_frame.geometry("300x450") # サイズ固定例

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
            modes = [("詰めて表示 (Compact)", "compact"), ("ページ切り替え (Paged)", "paged")]
            for text, value in modes:
                rb = tk.Radiobutton(mode_frame, text=text, variable=mode_var, value=value)
                rb.pack(anchor=tk.W)

            # ラベル表示モード設定
            label_mode_frame = tk.LabelFrame(settings_content, text="ラベル表示モード", padx=5, pady=5)
            label_mode_frame.pack(fill=tk.X, pady=5)
            label_mode_var = tk.StringVar(value=self.label_mode)
            label_modes = [("プロセス名", "process"), ("ウィンドウタイトル", "title")]
            for text, value in label_modes:
                rb = tk.Radiobutton(label_mode_frame, text=text, variable=label_mode_var, value=value)
                rb.pack(anchor=tk.W)

            # ページあたりボタン数設定
            buttons_frame = tk.LabelFrame(settings_content, text="1ページあたりのボタン数 (Pagedモード)", padx=5, pady=5)
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

            # 設定適用ボタン
            apply_button = tk.Button(settings_content, text="適用", padx=10, pady=5,
                                     command=lambda: self.apply_settings(
                                         position_var.get(), mode_var.get(),
                                         buttons_var.get(), interval_var.get(),
                                         label_mode_var.get()
                                     ))
            apply_button.pack(pady=10)

            self.settings_visible = True
            self.settings_frame.bind("<Escape>", lambda e: self.toggle_settings())
            self.settings_frame.protocol("WM_DELETE_WINDOW", self.toggle_settings)

    def apply_settings(self, position, display_mode, buttons_per_page, update_interval, label_mode):
        """設定を適用する"""
        changes_made = False
        position_changed = False

        if self.position != position:
            self.position = position
            position_changed = True # 位置変更フラグ
            changes_made = True

        if self.display_mode != display_mode:
            self.display_mode = display_mode
            self.current_page = 0 # モード変更時はページリセット
            changes_made = True

        if self.buttons_per_page != buttons_per_page:
            self.buttons_per_page = buttons_per_page
            changes_made = True

        if self.update_interval != update_interval:
            self.update_interval = update_interval
            # スレッドの更新間隔変更はここでは行わない (次回のループから適用)
            changes_made = True

        if self.label_mode != label_mode:
            self.label_mode = label_mode
            changes_made = True

        # 設定パネルを閉じる
        self.toggle_settings()

        # 変更があった場合のみUIを更新
        if position_changed:
            # 位置が変わった場合は set_position で全体を再構築
            self.set_position(self.position)
        elif changes_made:
            # 位置以外の変更があった場合はコントロールボタンとタスクボタンを更新
            self.create_control_buttons()
            self.update_task_buttons()

    def toggle_visibility(self):
        """タスクバーの表示/非表示 (最小化/復元) を切り替える"""
        if self.is_visible:
            # 非表示 (最小化)
            if self.position in ["bottom", "top"]:
                min_height = 10 # 最小化時の高さ
                if self.position == "bottom":
                    screen_height = self.root.winfo_screenheight()
                    self.root.geometry(f"{self.root.winfo_width()}x{min_height}+0+{screen_height-min_height}")
                else: # top
                    self.root.geometry(f"{self.root.winfo_width()}x{min_height}+0+0")
                # ボタンフレームを隠す
                if self.button_frame.winfo_manager(): self.button_frame.pack_forget()
            else: # left, right
                min_width = 10 # 最小化時の幅
                if self.position == "left":
                    self.root.geometry(f"{min_width}x{self.root.winfo_height()}+0+0")
                else: # right
                    screen_width = self.root.winfo_screenwidth()
                    self.root.geometry(f"{min_width}x{self.root.winfo_height()}+{screen_width-min_width}+0")
                # ボタンフレームを隠す
                if self.button_frame.winfo_manager(): self.button_frame.pack_forget()

            self.is_visible = False
            # コントロールボタンを目立たせる（例）
            for widget in self.control_frame.winfo_children():
                 if isinstance(widget, tk.Button) and widget.cget("text") in ["🥚", "🐣"]:
                     widget.config(text="🐣", relief=tk.RAISED, bg="#3E3E3E")
                 elif isinstance(widget, tk.Button):
                     widget.config(relief=tk.RAISED, bg="#3E3E3E") # 他のボタンも

        else:
            # 表示 (復元)
            self.is_visible = True
            # 元のレイアウトに戻す
            self.set_position(self.position)
            # トグルボタンの表示を更新 (set_position内で再作成されるので不要かも)
            # for widget in self.control_frame.winfo_children():
            #     if isinstance(widget, tk.Button) and widget.cget("text") in ["🥚", "🐣"]:
            #         widget.config(text="🥚", relief=tk.FLAT, bg="#1E1E1E")


    def prev_page(self):
        """前のページに移動"""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_task_buttons()
            if hasattr(self, 'page_label') and self.page_label:
                self.page_label.config(text=f"{self.current_page+1}")

    def next_page(self):
        """次のページに移動"""
        total_tasks = len(self.tasks)
        total_pages = max(1, (total_tasks + self.buttons_per_page - 1) // self.buttons_per_page)
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.update_task_buttons()
            if hasattr(self, 'page_label') and self.page_label:
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

    # ========================================================================
    # アイコン取得関数 (最新の修正版)
    # ========================================================================
    def get_window_icon(self, hwnd):
        # アイコンキャッシュのチェック
        if hwnd in self.icon_cache:
            return self.icon_cache[hwnd]

        # ボタン内のアイコン表示目標サイズ (最終リサイズ用)
        target_display_size = max(1, self.button_size - 10)
        hicon = None # 取得するアイコンハンドル
        large_icon, small_icon = None, None # ExtractIconExの結果用
        img = None # 最終的に生成するPIL Imageオブジェクト

        try:
            # ウィンドウからプロセスIDと実行ファイルパスを取得
            _, process_id = win32process.GetWindowThreadProcessId(hwnd)
            try:
                process = psutil.Process(process_id)
                exe_path = process.exe()

                # 実行ファイルパスからアイコンハンドルを取得 (ExtractIconExを再度使用)
                if os.path.exists(exe_path):
                    try:
                        large_icon, small_icon = win32gui.ExtractIconEx(exe_path, 0, 1)
                        # 小さいアイコンを優先的に使用
                        if small_icon:
                            hicon = small_icon[0]
                        elif large_icon:
                            hicon = large_icon[0]

                        if hicon:
                            # --- アイコンハンドルから実際のサイズを取得 ---
                            icon_info = None
                            icon_width = 16 # デフォルトサイズ
                            icon_height = 16 # デフォルトサイズ
                            try:
                                icon_info = win32gui.GetIconInfo(hicon)
                                if icon_info:
                                    # カラービットマップ(hbmColor)かマスクビットマップ(hbmMask)からサイズを取得
                                    # GetObjectでビットマップ情報を取得
                                    hbm_check = icon_info[3] if icon_info[3] else icon_info[4]
                                    if hbm_check:
                                        try:
                                            bmp_info = win32gui.GetObject(hbm_check)
                                            icon_width = bmp_info.bmWidth
                                            icon_height = bmp_info.bmHeight
                                            # print(f"DEBUG: Got icon size from GetIconInfo: {icon_width}x{icon_height} for hwnd {hwnd}")
                                        except Exception as e_getobj:
                                             print(f"WARN: Could not get bitmap info via GetObject for hwnd {hwnd}: {e_getobj}")
                            except Exception as e_getinfo:
                                print(f"WARN: Could not get icon info/size for hwnd {hwnd}: {e_getinfo}")
                            finally:
                                # GetIconInfoで取得したビットマップハンドルはDeleteObjectで解放
                                if icon_info:
                                    if icon_info[3]:
                                        try: win32gui.DeleteObject(icon_info[3])
                                        except: pass
                                    if icon_info[4]:
                                        try: win32gui.DeleteObject(icon_info[4])
                                        except: pass

                            # --- 取得したアイコンハンドルを実際のサイズで描画・ビットマップ化 ---
                            hdcScreen = None
                            hdcMem = None
                            hbm = None
                            try:
                                hdcScreen = win32gui.GetDC(0)
                                hdcMem = win32gui.CreateCompatibleDC(hdcScreen)
                                # ★ 実際のアイコンサイズでビットマップを作成
                                hbm = win32gui.CreateCompatibleBitmap(hdcScreen, icon_width, icon_height)
                                hbmOld = win32gui.SelectObject(hdcMem, hbm)

                                # ★ DrawIconExでアイコンを描画
                                if win32gui.DrawIconEx(hdcMem, 0, 0, hicon, icon_width, icon_height, 0, 0, win32con.DI_NORMAL):
                                    # ★ GetDIBitsでビットマップデータを取得 (Top-down形式で)
                                    bmi = win32ui.CreateBitmapInfo(icon_width, -icon_height)
                                    bmpstr = win32gui.GetDIBits(hdcMem, hbm, 0, icon_height, bmi)

                                    # --- PIL Imageに変換 ---
                                    img_mode = 'RGBA'
                                    img_size = (icon_width, icon_height)
                                    expected_size = img_size[0] * img_size[1] * 4 # RGBA想定

                                    if len(bmpstr) >= expected_size:
                                        try:
                                            # GetDIBitsは通常BGRA順なので、まずBGRAを試す
                                            img = Image.frombuffer(img_mode, img_size, bmpstr, 'raw', 'BGRA', 0, 1)
                                            # print(f"DEBUG: Created {img_size} image from hwnd {hwnd} (BGRA)")
                                        except ValueError:
                                            try: # BGRAがダメならRGBAを試す
                                                img = Image.frombuffer(img_mode, img_size, bmpstr, 'raw', 'RGBA', 0, 1)
                                                # print(f"DEBUG: Created {img_size} image from hwnd {hwnd} (RGBA)")
                                            except ValueError as e_rgba:
                                                print(f"ERROR: frombuffer failed (BGRA/RGBA) for hwnd {hwnd}: {e_rgba}")
                                    else:
                                         print(f"ERROR: Data size mismatch for hwnd {hwnd}. Expected >= {expected_size}, got {len(bmpstr)}")
                                else:
                                     print(f"ERROR: DrawIconEx failed for hwnd {hwnd}. Error: {win32api.GetLastError()}")

                                # SelectObjectを元に戻す
                                win32gui.SelectObject(hdcMem, hbmOld)

                            except Exception as e_draw:
                                print(f"ERROR: Exception during icon drawing/conversion for hwnd {hwnd}: {e_draw}")
                            finally:
                                # 作成したビットマップとDCを解放
                                if hbm:
                                    try: win32gui.DeleteObject(hbm)
                                    except: pass
                                if hdcMem:
                                    try: win32gui.DeleteDC(hdcMem)
                                    except: pass
                                if hdcScreen:
                                    try: win32gui.ReleaseDC(0, hdcScreen)
                                    except: pass
                    except Exception as e_extract:
                        print(f"WARN: Failed to extract icon from {exe_path}: {e_extract}")
                    finally:
                         # ExtractIconExで取得したハンドルを解放 (重要)
                        if small_icon:
                            try: win32gui.DestroyIcon(small_icon[0])
                            except: pass
                        if large_icon:
                            try: win32gui.DestroyIcon(large_icon[0])
                            except: pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                 pass # これらは頻繁に発生しうるので、エラー表示抑制
            except Exception as e_proc:
                print(f"ERROR: Unexpected error getting process info for hwnd {hwnd}: {e_proc}")
        except Exception as e_win:
            print(f"ERROR: Unexpected error accessing window info for hwnd {hwnd}: {e_win}")

        # --- PIL Image が正常に作成できていればリサイズして PhotoImage に ---
        if img:
            try:
                # ★ 最終的なボタン表示サイズにリサイズ (LANCZOSで綺麗に)
                img_resized = img.resize((target_display_size, target_display_size), Image.Resampling.LANCZOS)
                photo_img = ImageTk.PhotoImage(img_resized)
                self.icon_cache[hwnd] = photo_img
                # print(f"DEBUG: Successfully processed and cached icon for hwnd {hwnd}")
                return photo_img
            except AttributeError: # 古いPillowバージョン用フォールバック
                 img_resized = img.resize((target_display_size, target_display_size), Image.LANCZOS)
                 photo_img = ImageTk.PhotoImage(img_resized)
                 self.icon_cache[hwnd] = photo_img
                 return photo_img
            except Exception as e_resize:
                print(f"ERROR: Failed to resize/convert image for hwnd {hwnd}: {e_resize}")

        # --- アイコン取得/処理に失敗した場合 ---
        default_icon = self.create_default_icon() # デフォルトアイコンを返す
        self.icon_cache[hwnd] = default_icon
        return default_icon

    def create_default_icon(self):
        """デフォルトのアイコンを作成する（リサイズ対応）"""
        target_icon_size = max(1, self.button_size - 10) # get_window_icon の target_display_size と合わせる
        # キャッシュにデフォルトアイコンがなければ作成
        cache_key = f"default_{target_icon_size}"
        if cache_key not in self.icon_cache:
            img = Image.new('RGBA', (target_icon_size, target_icon_size), (50, 50, 50, 255)) # 濃い灰色背景
            draw = ImageDraw.Draw(img)
            # 白っぽい枠線
            draw.rectangle([1, 1, target_icon_size-2, target_icon_size-2], outline=(200, 200, 200, 255), width=1)
            # 簡易的なドキュメント風の絵
            draw.line([(4, 4), (target_icon_size-5, 4)], fill=(200, 200, 200, 255), width=1)
            draw.line([(4, 7), (target_icon_size-8, 7)], fill=(200, 200, 200, 255), width=1)
            draw.line([(4, 10), (target_icon_size-5, 10)], fill=(200, 200, 200, 255), width=1)

            self.icon_cache[cache_key] = ImageTk.PhotoImage(img)
        return self.icon_cache[cache_key]

    def monitor_processes(self):
        """実行中のプロセスとウィンドウを監視する"""
        while not self.stop_thread:
            try:
                windowed_processes = self.get_windowed_processes()
                # リストの内容が変更されたか、タスク数が変わった場合にUI更新
                if self.tasks != windowed_processes:
                    self.tasks = windowed_processes
                    # TkinterのUI更新はメインスレッドで行う必要があるので after を使う
                    self.root.after(0, self.update_task_buttons)
            except Exception as e:
                 print(f"ERROR in monitor_processes loop: {e}")
            # 指定された間隔で待機
            time.sleep(self.update_interval)

    def get_windowed_processes(self):
        """表示対象となるウィンドウを持つプロセスのリストを取得"""
        windowed_processes = []
        hwnds = []

        def enum_windows_proc(hwnd, lParam):
            # 見えていて、タイトルがあり、ツールウィンドウでないものを候補とする
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd) and \
               not (win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) & win32con.WS_EX_TOOLWINDOW):
                # このタスクバー自体は除外
                if hwnd != self.root.winfo_id():
                    hwnds.append(hwnd)
            return True

        win32gui.EnumWindows(enum_windows_proc, None)

        current_hwnds = {task['hwnd'] for task in self.tasks}
        active_hwnds = set(hwnds)

        # 既存のタスク情報と突き合わせ (プロセス名などは毎回取得しない)
        new_tasks = []
        cached_tasks = {task['hwnd']: task for task in self.tasks}

        for hwnd in hwnds:
            if hwnd in cached_tasks:
                 # 既存タスクはタイトルと最小化状態のみ更新
                 try:
                      title = win32gui.GetWindowText(hwnd)
                      is_minimized = win32gui.IsIconic(hwnd)
                      # タイトルが変わっていなくても更新する（状態が変わるため）
                      cached_tasks[hwnd]['title'] = title
                      cached_tasks[hwnd]['is_minimized'] = is_minimized
                      new_tasks.append(cached_tasks[hwnd])
                 except Exception: # ウィンドウが閉じられた場合など
                      pass # このウィンドウはリストから消える
            else:
                 # 新しいウィンドウ
                 try:
                     title = win32gui.GetWindowText(hwnd)
                     is_minimized = win32gui.IsIconic(hwnd)
                     _, process_id = win32process.GetWindowThreadProcessId(hwnd)
                     try:
                         process = psutil.Process(process_id)
                         process_name = process.name()
                         new_tasks.append({
                             'hwnd': hwnd,
                             'title': title,
                             'process_id': process_id,
                             'process_name': process_name,
                             'is_minimized': is_minimized
                         })
                     except (psutil.NoSuchProcess, psutil.AccessDenied):
                         pass # プロセス情報が取れなければ追加しない
                 except Exception as e:
                      print(f"Error processing new window {hwnd}: {e}")

        # 不要になったアイコンキャッシュを削除 (オプション)
        removed_hwnds = current_hwnds - active_hwnds
        for hwnd in removed_hwnds:
            if hwnd in self.icon_cache:
                del self.icon_cache[hwnd]

        # タイトルでソートする例（任意）
        # new_tasks.sort(key=lambda x: x['title'].lower())

        return new_tasks


    def update_task_buttons(self):
        # print(">>> ENTERING update_task_buttons")
        """タスクボタン表示を更新する"""

        # 現在表示されているボタンのhwndリストを取得 (スタートボタン除く)
        current_button_hwnds = {btn.hwnd for btn in self.task_buttons if hasattr(btn, 'hwnd')}
        # 現在表示すべきタスクのhwndセットを取得
        display_tasks_all = self.tasks
        target_hwnds = {task['hwnd'] for task in display_tasks_all}

        # --- ページング処理 ---
        if self.display_mode == "paged":
            start_idx = self.current_page * self.buttons_per_page
            end_idx = start_idx + self.buttons_per_page
            display_tasks_page = display_tasks_all[start_idx:end_idx]
            target_hwnds_page = {task['hwnd'] for task in display_tasks_page}
        else: # compact モード
            display_tasks_page = display_tasks_all
            target_hwnds_page = target_hwnds

        # --- ボタンの更新 ---
        # 不要になったボタンを削除
        buttons_to_remove = [btn for btn in self.task_buttons if hasattr(btn, 'hwnd') and btn.hwnd not in target_hwnds_page]
        for btn in buttons_to_remove:
            btn.destroy()
            self.task_buttons.remove(btn)

        # 既存ボタンの情報更新と、新規ボタンの作成
        new_buttons = []
        existing_buttons_map = {btn.hwnd: btn for btn in self.task_buttons if hasattr(btn, 'hwnd')}

        for task in display_tasks_page:
            hwnd = task['hwnd']
            # ラベル設定
            if self.label_mode == "process":
                label = task['process_name'].replace('.exe', '')
            else: # title
                label = task['title']
            # ラベル長制限 (button_widthに合わせて調整可能)
            max_label_len = 15
            if len(label) > max_label_len:
                label = label[:max_label_len-3] + "..."

            # アイコン取得
            icon_image = self.get_window_icon(hwnd)

            if hwnd in existing_buttons_map:
                # 既存ボタンの更新
                button = existing_buttons_map[hwnd]
                # アイコンとテキストが変更されていたら更新
                if button.cget('text') != label:
                    button.config(text=label)
                # アイコン画像参照が異なれば更新 (PhotoImageオブジェクト比較は注意)
                # 毎回更新してもパフォーマンス影響は小さいはず
                button.config(image=icon_image)
                button.image = icon_image # 参照保持も更新
                # 状態に応じた見た目変更 (例: 最小化されているか)
                # button.config(relief=tk.SUNKEN if task['is_minimized'] else tk.RAISED)
                new_buttons.append(button) # 更新後リストに追加
            else:
                # 新規ボタンの作成
                button = tk.Button(
                    self.button_frame,
                    image=icon_image,
                    compound=tk.LEFT, # アイコンを左に
                    font=("Arial", 10),
                    anchor=tk.W,      # テキストを左寄せ
                    width=self.button_width if self.display_mode == "paged" else None, # Pagedモードのみ幅指定
                    height=self.button_size,
                    text=label,
                    bg="#2D2D2D",
                    fg="white",
                    bd=1,
                    relief=tk.RAISED,
                    padx=5,
                    pady=2, # 上下のパディングを少し減らす
                    command=partial(self.focus_window, hwnd)
                )
                # PhotoImageがGCされないように参照を保持 (重要)
                button.image = icon_image
                # ボタンにhwnd属性を持たせて管理しやすくする
                button.hwnd = hwnd

                # ボタンの配置
                pack_side = tk.LEFT if self.button_orientation == "horizontal" else tk.TOP
                fill_opt = tk.NONE if self.button_orientation == "horizontal" else tk.X # 縦置きは幅を広げる
                button.pack(side=pack_side, padx=2, pady=2, fill=fill_opt)
                new_buttons.append(button) # 新規リストに追加

        # ボタンリストを更新後のものに置き換え
        self.task_buttons = new_buttons

        # Pagedモードの場合、ページラベルを更新
        if self.display_mode == "paged" and hasattr(self, 'page_label') and self.page_label:
             total_tasks = len(self.tasks)
             total_pages = max(1, (total_tasks + self.buttons_per_page - 1) // self.buttons_per_page)
             # 現在ページが最大ページを超えないように調整 (タスクが減った場合)
             self.current_page = min(self.current_page, total_pages - 1)
             self.page_label.config(text=f"{self.current_page + 1}/{total_pages}")

        # print(f"<<< LEAVING update_task_buttons ({len(self.task_buttons)} buttons)")


    def focus_window(self, hwnd):
        """指定されたウィンドウにフォーカスを当てる"""
        try:
            # ウィンドウが最小化されている場合は元に戻す
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            else:
                # すでに表示されている場合は最前面に持ってくる
                 win32gui.ShowWindow(hwnd, win32con.SW_SHOW) # 念のため表示状態にする
                 win32gui.SetForegroundWindow(hwnd)

            # SetForegroundWindowが失敗した場合の代替手段 (Altキー操作をシミュレート)
            # これは最終手段であり、挙動が不安定になる可能性もある
            # try:
            #     win32gui.SetForegroundWindow(hwnd)
            # except pywintypes.error as e:
            #     if e.winerror == 0: # エラーコード0は権限問題などで失敗することがある
            #         # Altキーを押して離すトリック
            #         win32api.keybd_event(win32con.VK_MENU, 0, 0, 0) # Alt Press
            #         win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0) # Alt Release
            #         win32gui.SetForegroundWindow(hwnd) # 再度トライ
            #     else:
            #         raise e

        except Exception as e:
            print(f"Error focusing window {hwnd}: {e}")

    def on_closing(self):
        """アプリケーション終了時の処理"""
        print("Closing application...")
        self.stop_thread = True
        # スレッドが終了するのを少し待つ
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(1.0)
        self.root.destroy()
        sys.exit(0)

# --- メイン実行部分 ---
def main():
    # ルートウィンドウの作成
    root = tk.Tk()

    # DPIスケーリングの設定 (Windows向け)
    try:
        if os.name == 'nt':
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception as e:
        print(f"Note: Could not set DPI awareness. Scaling might be incorrect. Error: {e}")

    # アプリケーションインスタンスの作成
    app = TaskbarApp(root)

    # Tkinterイベントループの開始
    root.mainloop()

if __name__ == "__main__":
    main()