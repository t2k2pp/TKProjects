import os
import json
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw
import threading
from functools import partial

class ImageViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("画像ビューワ")
        self.root.geometry("1200x800")
        
        # アプリケーションの状態変数
        self.current_folder = None
        self.image_files = []
        self.thumbnails = []
        self.thumbnail_size = (80, 45)  # デフォルトサイズ
        self.checked_images = set()
        self.selected_image_index = -1
        
        # メインフレームの作成
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # メニューバーの作成
        self.create_menu()
        
        # レイアウトの設定
        self.setup_layout()
        
        # ステータスバーの作成
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_var.set("準備完了")
        
        # 初期ディレクトリを設定（ユーザーホームディレクトリ）
        self.initialize_directory_tree()

    def create_menu(self):
        menubar = tk.Menu(self.root)
        
        # ファイルメニュー
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="フォルダを開く", command=self.open_folder)
        file_menu.add_separator()
        file_menu.add_command(label="チェックした画像をコピー", command=self.copy_checked_images)
        file_menu.add_command(label="チェックした画像を移動", command=self.move_checked_images)
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.root.quit)
        menubar.add_cascade(label="ファイル", menu=file_menu)
        
        # 編集メニュー
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="全てチェック", command=self.check_all)
        edit_menu.add_command(label="全てチェック解除", command=self.uncheck_all)
        edit_menu.add_separator()
        edit_menu.add_command(label="チェックした画像をリネーム", command=self.rename_checked_images)
        edit_menu.add_command(label="チェックした画像の形式を変更", command=self.convert_checked_images)
        edit_menu.add_command(label="チェックした画像をリサイズ", command=self.resize_checked_images)
        edit_menu.add_command(label="チェックした画像を塗りつぶし", command=self.fill_region_checked_images)
        menubar.add_cascade(label="編集", menu=edit_menu)
        
        # 表示メニュー
        view_menu = tk.Menu(menubar, tearoff=0)
        
        # サムネイルサイズのサブメニュー
        size_menu = tk.Menu(view_menu, tearoff=0)
        size_menu.add_command(label="小 (80x45)", command=lambda: self.change_thumbnail_size((80, 45)))
        size_menu.add_command(label="大 (160x90)", command=lambda: self.change_thumbnail_size((160, 90)))
        view_menu.add_cascade(label="サムネイルサイズ", menu=size_menu)
        
        menubar.add_cascade(label="表示", menu=view_menu)
        
        # ヘルプメニュー
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="使い方", command=self.show_help)
        help_menu.add_command(label="バージョン情報", command=self.show_about)
        menubar.add_cascade(label="ヘルプ", menu=help_menu)
        
        self.root.config(menu=menubar)

    def setup_layout(self):
        # 左側のフレーム（フォルダツリー用）
        self.left_frame = ttk.Frame(self.main_frame, width=250)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # フォルダツリーの作成
        self.tree_frame = ttk.Frame(self.left_frame)
        self.tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.tree_scroll = ttk.Scrollbar(self.tree_frame)
        self.tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.folder_tree = ttk.Treeview(self.tree_frame, yscrollcommand=self.tree_scroll.set)
        self.folder_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree_scroll.config(command=self.folder_tree.yview)
        
        # フォルダツリーの設定
        self.folder_tree.heading('#0', text='フォルダ', anchor=tk.W)
        self.folder_tree.bind("<<TreeviewSelect>>", self.on_folder_select)
        
        # 右側のフレーム（上部：サムネイル、下部：選択画像表示用）
        self.right_frame = ttk.Frame(self.main_frame)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 上部のサムネイル表示エリア
        self.thumbnail_frame = ttk.Frame(self.right_frame)
        self.thumbnail_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # サムネイルキャンバスとスクロールバー
        self.thumbnail_canvas = tk.Canvas(self.thumbnail_frame, height=130)
        self.thumbnail_canvas.pack(side=tk.TOP, fill=tk.X, expand=True)
        
        self.thumbnail_scrollbar = ttk.Scrollbar(self.thumbnail_frame, orient=tk.HORIZONTAL, command=self.thumbnail_canvas.xview)
        self.thumbnail_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.thumbnail_canvas.configure(xscrollcommand=self.thumbnail_scrollbar.set)
        
        # サムネイル内部フレーム
        self.thumbnail_inner_frame = ttk.Frame(self.thumbnail_canvas)
        self.thumbnail_canvas.create_window((0, 0), window=self.thumbnail_inner_frame, anchor=tk.NW)
        self.thumbnail_inner_frame.bind("<Configure>", self.on_thumbnail_frame_configure)
        
        # 下部の選択画像表示エリア
        self.image_frame = ttk.LabelFrame(self.right_frame, text="選択画像")
        self.image_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 画像表示用キャンバス
        self.image_canvas = tk.Canvas(self.image_frame, bg="black")
        self.image_canvas.pack(fill=tk.BOTH, expand=True)
        
        # ボタンフレーム
        self.button_frame = ttk.Frame(self.right_frame)
        self.button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # チェックボタン
        self.check_all_button = ttk.Button(self.button_frame, text="全てチェック", command=self.check_all)
        self.check_all_button.pack(side=tk.LEFT, padx=5)
        
        self.uncheck_all_button = ttk.Button(self.button_frame, text="全てチェック解除", command=self.uncheck_all)
        self.uncheck_all_button.pack(side=tk.LEFT, padx=5)
        
        # 操作ボタン
        self.copy_button = ttk.Button(self.button_frame, text="コピー", command=self.copy_checked_images)
        self.copy_button.pack(side=tk.RIGHT, padx=5)
        
        self.move_button = ttk.Button(self.button_frame, text="移動", command=self.move_checked_images)
        self.move_button.pack(side=tk.RIGHT, padx=5)
        
        # キーボードショートカットの設定
        self.root.bind("<Left>", self.prev_image)
        self.root.bind("<Right>", self.next_image)
        self.root.bind("<space>", self.toggle_check_current)

    def initialize_directory_tree(self):
        # ツールバーの作成
        toolbar = ttk.Frame(self.left_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        # ルートフォルダ設定ボタン
        ttk.Button(toolbar, text="ルートフォルダ設定", command=self.set_root_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="更新", command=self.refresh_tree).pack(side=tk.LEFT, padx=5)
        
        # フォルダツリーの初期化
        self.root_folder = None
        self.refresh_tree()

    def set_root_folder(self):
        folder = filedialog.askdirectory(title="ルートフォルダを選択")
        if folder:
            self.root_folder = folder
            self.refresh_tree()

    def refresh_tree(self):
        # 既存のツリーをクリア
        for item in self.folder_tree.get_children():
            self.folder_tree.delete(item)
        
        if not self.root_folder:
            # ルートフォルダが設定されていない場合
            self.folder_tree.insert("", "end", text="ルートフォルダを設定してください", tags=["message"])
            return
        
        # ルートフォルダを追加
        root_id = self.folder_tree.insert("", "end", text=os.path.basename(self.root_folder), 
                                         values=[self.root_folder])
        try:
            # サブフォルダを確認
            has_subfolder = any(os.path.isdir(os.path.join(self.root_folder, item)) 
                              for item in os.listdir(self.root_folder))
            if has_subfolder:
                self.folder_tree.insert(root_id, "end", text="")
        except Exception as e:
            messagebox.showerror("エラー", f"フォルダの読み込みに失敗しました: {e}")

    def on_folder_select(self, event):
        # フォルダが選択されたとき画像を読み込む
        selected_item = self.folder_tree.focus()
        if not selected_item:
            return
            
        # フォルダパスを取得
        folder_path = self.folder_tree.item(selected_item, "values")[0]
        if not os.path.isdir(folder_path):
            return
            
        self.current_folder = folder_path
        self.load_images(folder_path)

    def is_valid_image(self, file_path):
        """画像ファイルの有効性を確認"""
        try:
            # 拡張子チェック
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                return False
            
            # ファイルの存在確認
            if not os.path.exists(file_path):
                return False
            
            # 画像として開けるかチェック
            with Image.open(file_path) as img:
                img.verify()
            return True
        except Exception:
            return False

    def load_images(self, folder_path):
        self.status_var.set(f"フォルダを読み込み中: {folder_path}")
        self.image_files = []
        
        try:
            # フォルダ内のファイルをチェック
            for file in sorted(os.listdir(folder_path)):
                file_path = os.path.join(folder_path, file)
                if self.is_valid_image(file_path):
                    self.image_files.append(file_path)
        except Exception as e:
            messagebox.showerror("エラー", f"フォルダを読み込めませんでした: {e}")
            self.status_var.set("エラー: フォルダを読み込めませんでした")
            return
        
        # チェック情報を読み込む
        self.load_check_info()
        
        # サムネイルを生成
        self.generate_thumbnails()
        
        # 画像の表示
        if self.image_files:
            self.select_image(0)
        else:
            self.status_var.set(f"画像が見つかりませんでした: {folder_path}")
            self.clear_display()

    def generate_thumbnails(self):
        # サムネイル表示エリアをクリア
        for widget in self.thumbnail_inner_frame.winfo_children():
            widget.destroy()
        
        self.thumbnails = []
        
        # 画像がなければ何もしない
        if not self.image_files:
            return
        
        # サムネイルを生成するスレッドを開始
        threading.Thread(target=self._generate_thumbnails_thread, daemon=True).start()
    
    def _generate_thumbnails_thread(self):
        # サムネイルを生成
        for i, img_path in enumerate(self.image_files):
            try:
                # 画像の読み込み
                img = Image.open(img_path)
                
                # サムネイルのサイズ計算 (アスペクト比を維持)
                width, height = img.size
                thumb_width, thumb_height = self.thumbnail_size
                
                if width / height > thumb_width / thumb_height:
                    # 横長の画像
                    new_width = thumb_width
                    new_height = int(height * (thumb_width / width))
                else:
                    # 縦長の画像
                    new_height = thumb_height
                    new_width = int(width * (thumb_height / height))
                
                # サムネイル生成
                img_thumb = img.resize((new_width, new_height), Image.LANCZOS)
                img_tk = ImageTk.PhotoImage(img_thumb)
                
                # メインスレッドでGUIを更新
                self.root.after(0, self._add_thumbnail, i, img_tk, os.path.basename(img_path))
                
                # 状態を更新
                self.status_var.set(f"サムネイル生成中... ({i+1}/{len(self.image_files)})")
            except Exception as e:
                print(f"Error generating thumbnail for {img_path}: {e}")
                # エラーの場合もダミーサムネイルを表示
                self.root.after(0, self._add_thumbnail, i, None, os.path.basename(img_path))
        
        # 完了
        self.status_var.set(f"画像の読み込みが完了しました: {len(self.image_files)}個のファイル")
    
    def _add_thumbnail(self, index, img_tk, filename):
        # サムネイルフレームを作成
        frame = ttk.Frame(self.thumbnail_inner_frame)
        frame.grid(row=0, column=index, padx=5, pady=5)
        
        # 画像ボタン
        if img_tk:
            btn = tk.Button(frame, image=img_tk, command=lambda idx=index: self.select_image(idx))
            btn.image = img_tk  # 参照を保持
            btn.pack()
        else:
            # ダミーボタン（エラー時）
            btn = tk.Button(frame, text="Error", width=10, height=5, command=lambda idx=index: self.select_image(idx))
            btn.pack()
        
        # チェックボックス
        var = tk.BooleanVar()
        var.set(index in self.checked_images)
        cb = ttk.Checkbutton(frame, text="", variable=var, command=lambda idx=index, v=var: self.toggle_check(idx, v.get()))
        cb.pack()
        
        # ファイル名ラベル (短縮表示)
        max_length = 10
        short_name = filename if len(filename) <= max_length else filename[:max_length-3] + "..."
        lbl = ttk.Label(frame, text=short_name)
        lbl.pack()
        
        # ツールチップ
        self.create_tooltip(btn, filename)
        self.create_tooltip(lbl, filename)
        
        self.thumbnails.append((btn, var, lbl))
        
        # サムネイルフレームを更新
        self.thumbnail_inner_frame.update_idletasks()
        self.thumbnail_canvas.config(scrollregion=self.thumbnail_canvas.bbox("all"))

    def on_thumbnail_frame_configure(self, event):
        # サムネイルフレームのサイズが変わったときにスクロール領域を更新
        self.thumbnail_canvas.configure(scrollregion=self.thumbnail_canvas.bbox("all"))

    def select_image(self, index):
        # 画像を選択
        if 0 <= index < len(self.image_files):
            self.selected_image_index = index
            self.display_selected_image()
            
            # サムネイルをスクロールして表示
            if self.thumbnails:
                btn = self.thumbnails[index][0]
                x = btn.winfo_x()
                canvas_width = self.thumbnail_canvas.winfo_width()
                self.thumbnail_canvas.xview_moveto(max(0, (x - canvas_width/2) / self.thumbnail_inner_frame.winfo_width()))

    def display_selected_image(self):
        # 初期化
        canvas_width = self.image_canvas.winfo_width()
        canvas_height = self.image_canvas.winfo_height()
        
        if not self.image_files or self.selected_image_index < 0:
            self.image_canvas.delete("all")
            self.image_canvas.create_text(canvas_width//2, canvas_height//2, 
                                        text="画像がありません", fill="white")
            return
            
        img_path = self.image_files[self.selected_image_index]
        
        try:
            # 画像を読み込む
            img = Image.open(img_path)
            
            # 画像のサイズを調整
            width, height = img.size
            
            if width > canvas_width or height > canvas_height:
                ratio = min(canvas_width / width, canvas_height / height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # 画像を表示
            img_tk = ImageTk.PhotoImage(img)
            self.image_canvas.delete("all")
            self.image_canvas.create_image(canvas_width//2, canvas_height//2, image=img_tk)
            self.image_canvas.image = img_tk
            
            # ファイル情報の表示
            filename = os.path.basename(img_path)
            file_size = os.path.getsize(img_path) / 1024  # KB
            info_text = f"{filename} ({width}x{height}, {file_size:.1f} KB)"
            self.image_frame.configure(text=info_text)
            
        except Exception as e:
            self.image_canvas.delete("all")
            self.image_canvas.create_text(canvas_width//2, canvas_height//2, 
                                        text=f"画像を表示できません\n{str(e)}", fill="white")
            self.image_frame.configure(text="エラー")

    def toggle_check(self, index, checked):
        # チェック状態の切り替え
        if checked:
            self.checked_images.add(index)
        else:
            self.checked_images.discard(index)
        
        # チェック情報を保存
        self.save_check_info()

    def toggle_check_current(self, event=None):
        # 現在選択中の画像のチェック状態を切り替え
        if self.selected_image_index >= 0:
            idx = self.selected_image_index
            if idx < len(self.thumbnails):
                var = self.thumbnails[idx][1]
                var.set(not var.get())
                self.toggle_check(idx, var.get())

    def check_all(self):
        # 全ての画像をチェック
        for i in range(len(self.image_files)):
            if i < len(self.thumbnails):
                self.thumbnails[i][1].set(True)
            self.checked_images.add(i)
        
        # チェック情報を保存
        self.save_check_info()

    def uncheck_all(self):
        # 全ての画像のチェックを解除
        for i in range(len(self.image_files)):
            if i < len(self.thumbnails):
                self.thumbnails[i][1].set(False)
        self.checked_images.clear()
        
        # チェック情報を保存
        self.save_check_info()

    def save_check_info(self):
        # チェック情報をJSONファイルに保存
        if not self.current_folder:
            return
            
        json_path = os.path.join(self.current_folder, "image_viewer_checks.json")
        
        try:
            check_data = {
                "checked_images": list(sorted(self.checked_images))
            }
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(check_data, f, indent=2)
                
        except Exception as e:
            print(f"チェック情報の保存に失敗しました: {e}")

    def load_check_info(self):
        # チェック情報をJSONファイルから読み込む
        self.checked_images.clear()
        
        if not self.current_folder:
            return
            
        json_path = os.path.join(self.current_folder, "image_viewer_checks.json")
        
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    check_data = json.load(f)
                    
                if "checked_images" in check_data:
                    self.checked_images = set(check_data["checked_images"])
                    
            except Exception as e:
                print(f"チェック情報の読み込みに失敗しました: {e}")

    def change_thumbnail_size(self, size):
        # サムネイルサイズを変更
        self.thumbnail_size = size
        if self.current_folder:
            self.generate_thumbnails()

    def clear_display(self):
        # 表示をクリア
        self.selected_image_index = -1
        
        # サムネイルをクリア
        for widget in self.thumbnail_inner_frame.winfo_children():
            widget.destroy()
        self.thumbnails = []
        
        # 画像表示もクリア
        self.image_canvas.delete("all")
        canvas_width = self.image_canvas.winfo_width()
        canvas_height = self.image_canvas.winfo_height()
        self.image_canvas.create_text(canvas_width//2, canvas_height//2, text="画像がありません", fill="white")
        self.image_frame.configure(text="選択画像")

    def open_folder(self):
        # フォルダ選択ダイアログを表示
        folder_path = filedialog.askdirectory(title="フォルダを選択")
        if folder_path:
            self.current_folder = folder_path
            self.load_images(folder_path)

    def copy_checked_images(self):
        # チェックした画像をコピー
        if not self.checked_images:
            messagebox.showinfo("情報", "コピーする画像が選択されていません。")
            return
            
        # コピー先フォルダを選択
        target_folder = filedialog.askdirectory(title="コピー先フォルダを選択")
        if not target_folder:
            return
            
        # 進捗ダイアログ
        progress_win = tk.Toplevel(self.root)
        progress_win.title("コピー中")
        progress_win.geometry("300x100")
        progress_win.transient(self.root)
        progress_win.grab_set()
        
        progress_lbl = ttk.Label(progress_win, text="ファイルをコピー中...")
        progress_lbl.pack(pady=10)
        
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(progress_win, variable=progress_var, maximum=len(self.checked_images))
        progress_bar.pack(fill=tk.X, padx=10, pady=10)
        
        # コピー処理を別スレッドで実行
        threading.Thread(target=self._copy_files_thread, args=(target_folder, progress_win, progress_var, progress_lbl)).start()

    def _copy_files_thread(self, target_folder, progress_win, progress_var, progress_lbl):
        # ファイルコピーの実行
        copied_count = 0
        error_count = 0
        skipped_count = 0
        
        for i, idx in enumerate(sorted(self.checked_images)):
            if idx >= len(self.image_files):
                continue
                
            src_path = self.image_files[idx]
            file_name = os.path.basename(src_path)
            dst_path = os.path.join(target_folder, file_name)
            
            progress_var.set(i + 1)
            progress_lbl.config(text=f"コピー中: {file_name}")
            progress_win.update_idletasks()
            
            try:
                if os.path.exists(dst_path):
                    # 同名ファイルが存在する場合
                    response = messagebox.askyesnocancel(
                        "確認", 
                        f"ファイル '{file_name}' は既に存在します。上書きしますか？\n"
                        "「はい」で上書き、「いいえ」でスキップ、「キャンセル」で処理を中止します。"
                    )
                    
                    if response is None:  # キャンセル
                        break
                    elif response:  # はい（上書き）
                        shutil.copy2(src_path, dst_path)
                        copied_count += 1
                    else:  # いいえ（スキップ）
                        skipped_count += 1
                        continue
                else:
                    shutil.copy2(src_path, dst_path)
                    copied_count += 1
                    
            except Exception as e:
                error_count += 1
                print(f"コピーエラー: {e}")
        
        # 処理完了
        progress_win.destroy()
        
        # 結果表示
        result_msg = f"{copied_count}個のファイルをコピーしました。"
        if skipped_count > 0:
            result_msg += f"\n{skipped_count}個のファイルをスキップしました。"
        if error_count > 0:
            result_msg += f"\n{error_count}個のファイルでエラーが発生しました。"
            
        messagebox.showinfo("コピー完了", result_msg)

    def move_checked_images(self):
        # チェックした画像を移動
        if not self.checked_images:
            messagebox.showinfo("情報", "移動する画像が選択されていません。")
            return
            
        # 移動先フォルダを選択
        target_folder = filedialog.askdirectory(title="移動先フォルダを選択")
        if not target_folder:
            return
            
        # 確認ダイアログ
        if not messagebox.askyesno("確認", "選択した画像を移動しますか？この操作は元に戻せません。"):
            return
            
        # 進捗ダイアログ
        progress_win = tk.Toplevel(self.root)
        progress_win.title("移動中")
        progress_win.geometry("300x100")
        
        progress_win.transient(self.root)
        progress_win.grab_set()
        
        progress_lbl = ttk.Label(progress_win, text="ファイルを移動中...")
        progress_lbl.pack(pady=10)
        
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(progress_win, variable=progress_var, maximum=len(self.checked_images))
        progress_bar.pack(fill=tk.X, padx=10, pady=10)
        
        # 移動処理を別スレッドで実行
        threading.Thread(target=self._move_files_thread, args=(target_folder, progress_win, progress_var, progress_lbl)).start()

    def _move_files_thread(self, target_folder, progress_win, progress_var, progress_lbl):
        # ファイル移動の実行
        moved_count = 0
        error_count = 0
        skipped_count = 0
        
        # 移動する画像のインデックスリスト（ソート済み）
        indices_to_move = sorted(self.checked_images)
        
        for i, idx in enumerate(indices_to_move):
            if idx >= len(self.image_files):
                continue
                
            src_path = self.image_files[idx]
            file_name = os.path.basename(src_path)
            dst_path = os.path.join(target_folder, file_name)
            
            progress_var.set(i + 1)
            progress_lbl.config(text=f"移動中: {file_name}")
            progress_win.update_idletasks()
            
            try:
                if os.path.exists(dst_path):
                    # 同名ファイルが存在する場合
                    response = messagebox.askyesnocancel(
                        "確認", 
                        f"ファイル '{file_name}' は既に存在します。上書きしますか？\n"
                        "「はい」で上書き、「いいえ」でスキップ、「キャンセル」で処理を中止します。"
                    )
                    
                    if response is None:  # キャンセル
                        break
                    elif response:  # はい（上書き）
                        shutil.move(src_path, dst_path)
                        moved_count += 1
                    else:  # いいえ（スキップ）
                        skipped_count += 1
                        continue
                else:
                    shutil.move(src_path, dst_path)
                    moved_count += 1
                    
            except Exception as e:
                error_count += 1
                print(f"移動エラー: {e}")
        
        # 処理完了
        progress_win.destroy()
        
        # 結果表示
        result_msg = f"{moved_count}個のファイルを移動しました。"
        if skipped_count > 0:
            result_msg += f"\n{skipped_count}個のファイルをスキップしました。"
        if error_count > 0:
            result_msg += f"\n{error_count}個のファイルでエラーが発生しました。"
            
        messagebox.showinfo("移動完了", result_msg)
        
        # 移動後は画像リストを更新
        if moved_count > 0:
            self.load_images(self.current_folder)

    def rename_checked_images(self):
        # チェックした画像をリネーム
        if not self.checked_images:
            messagebox.showinfo("情報", "リネームする画像が選択されていません。")
            return
            
        # リネームダイアログを表示
        rename_dialog = RenameDialog(self.root, len(self.checked_images))
        if not rename_dialog.result:
            return
            
        # リネーム情報を取得
        base_name = rename_dialog.base_name
        start_number = rename_dialog.start_number
        digits = rename_dialog.digits
        
        # 確認ダイアログ
        if not messagebox.askyesno("確認", "選択した画像をリネームしますか？"):
            return
            
        # リネームの実行
        renamed_count = 0
        error_count = 0
        
        # チェックした画像のインデックスをソート
        indices = sorted(self.checked_images)
        
        for i, idx in enumerate(indices):
            if idx >= len(self.image_files):
                continue
                
            src_path = self.image_files[idx]
            file_ext = os.path.splitext(src_path)[1]
            
            # 新しいファイル名を生成
            number = start_number + i
            new_name = f"{base_name}{number:0{digits}d}{file_ext}"
            dst_path = os.path.join(os.path.dirname(src_path), new_name)
            
            try:
                # ファイルが存在する場合はスキップ
                if os.path.exists(dst_path) and src_path != dst_path:
                    if not messagebox.askyesno("確認", f"ファイル '{new_name}' は既に存在します。上書きしますか？"):
                        continue
                
                os.rename(src_path, dst_path)
                renamed_count += 1
                
            except Exception as e:
                error_count += 1
                print(f"リネームエラー: {e}")
        
        # 結果表示
        result_msg = f"{renamed_count}個のファイルをリネームしました。"
        if error_count > 0:
            result_msg += f"\n{error_count}個のファイルでエラーが発生しました。"
            
        messagebox.showinfo("リネーム完了", result_msg)
        
        # リネーム後は画像リストを更新
        if renamed_count > 0:
            self.load_images(self.current_folder)

    def convert_checked_images(self):
        # チェックした画像の形式を変更
        if not self.checked_images:
            messagebox.showinfo("情報", "変換する画像が選択されていません。")
            return
            
        # 変換ダイアログを表示
        convert_dialog = ConvertDialog(self.root)
        if not convert_dialog.result:
            return
            
        # 変換設定を取得
        format_type = convert_dialog.format_type
        quality = convert_dialog.quality
        
        # 進捗ダイアログ
        progress_win = tk.Toplevel(self.root)
        progress_win.title("変換中")
        progress_win.geometry("300x100")
        progress_win.transient(self.root)
        progress_win.grab_set()
        
        progress_lbl = ttk.Label(progress_win, text="ファイルを変換中...")
        progress_lbl.pack(pady=10)
        
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(progress_win, variable=progress_var, maximum=len(self.checked_images))
        progress_bar.pack(fill=tk.X, padx=10, pady=10)
        
        # 変換処理を別スレッドで実行
        threading.Thread(target=self._convert_files_thread, args=(format_type, quality, progress_win, progress_var, progress_lbl)).start()

    def _convert_files_thread(self, format_type, quality, progress_win, progress_var, progress_lbl):
        # ファイル変換の実行
        converted_count = 0
        error_count = 0
        
        for i, idx in enumerate(sorted(self.checked_images)):
            if idx >= len(self.image_files):
                continue
                
            src_path = self.image_files[idx]
            file_name = os.path.splitext(os.path.basename(src_path))[0]
            dst_path = os.path.join(os.path.dirname(src_path), f"{file_name}.{format_type.lower()}")
            
            progress_var.set(i + 1)
            progress_lbl.config(text=f"変換中: {os.path.basename(src_path)}")
            progress_win.update_idletasks()
            
            try:
                # 画像を開く
                img = Image.open(src_path)
                
                # RGB形式に変換（アルファチャンネルを処理）
                if img.mode == 'RGBA' and format_type.lower() == 'jpg':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])
                    img = background
                
                # 同名ファイルが存在する場合
                if os.path.exists(dst_path) and src_path != dst_path:
                    response = messagebox.askyesnocancel(
                        "確認", 
                        f"ファイル '{os.path.basename(dst_path)}' は既に存在します。上書きしますか？"
                    )
                    
                    if response is None:  # キャンセル
                        continue
                    elif not response:  # いいえ
                        continue
                
                # 保存
                if format_type.lower() == 'jpg':
                    img.save(dst_path, 'JPEG', quality=quality)
                elif format_type.lower() == 'png':
                    img.save(dst_path, 'PNG')
                elif format_type.lower() == 'bmp':
                    img.save(dst_path, 'BMP')
                
                converted_count += 1
                
            except Exception as e:
                error_count += 1
                print(f"変換エラー: {e}")
        
        # 処理完了
        progress_win.destroy()
        
        # 結果表示
        result_msg = f"{converted_count}個のファイルを{format_type}形式に変換しました。"
        if error_count > 0:
            result_msg += f"\n{error_count}個のファイルでエラーが発生しました。"
            
        messagebox.showinfo("変換完了", result_msg)
        
        # 変換後は画像リストを更新
        if converted_count > 0:
            self.load_images(self.current_folder)

    def resize_checked_images(self):
        # チェックした画像をリサイズ
        if not self.checked_images:
            messagebox.showinfo("情報", "リサイズする画像が選択されていません。")
            return
            
        # リサイズダイアログを表示
        resize_dialog = ResizeDialog(self.root)
        if not resize_dialog.result:
            return
            
        # リサイズ設定を取得
        resize_mode = resize_dialog.resize_mode
        width = resize_dialog.width
        height = resize_dialog.height
        format_type = resize_dialog.format_type
        quality = resize_dialog.quality
        
        # 進捗ダイアログ
        progress_win = tk.Toplevel(self.root)
        progress_win.title("リサイズ中")
        progress_win.geometry("300x100")
        progress_win.transient(self.root)
        progress_win.grab_set()
        
        progress_lbl = ttk.Label(progress_win, text="ファイルをリサイズ中...")
        progress_lbl.pack(pady=10)
        
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(progress_win, variable=progress_var, maximum=len(self.checked_images))
        progress_bar.pack(fill=tk.X, padx=10, pady=10)
        
        # リサイズ処理を別スレッドで実行
        thread_args = (resize_mode, width, height, format_type, quality, progress_win, progress_var, progress_lbl)
        threading.Thread(target=self._resize_files_thread, args=thread_args).start()

    def _resize_files_thread(self, resize_mode, width, height, format_type, quality, progress_win, progress_var, progress_lbl):
        # ファイルリサイズの実行
        resized_count = 0
        error_count = 0
        
        for i, idx in enumerate(sorted(self.checked_images)):
            if idx >= len(self.image_files):
                continue
                
            src_path = self.image_files[idx]
            file_name = os.path.splitext(os.path.basename(src_path))[0]
            
            # 出力ファイル名を生成
            if format_type:
                dst_path = os.path.join(os.path.dirname(src_path), f"{file_name}_resized.{format_type.lower()}")
            else:
                ext = os.path.splitext(src_path)[1]
                dst_path = os.path.join(os.path.dirname(src_path), f"{file_name}_resized{ext}")
            
            progress_var.set(i + 1)
            progress_lbl.config(text=f"リサイズ中: {os.path.basename(src_path)}")
            progress_win.update_idletasks()
            
            try:
                # 画像を開く
                img = Image.open(src_path)
                orig_width, orig_height = img.size
                
                # リサイズ方法に応じて処理
                if resize_mode == "比率を維持":
                    # アスペクト比を維持
                    if width and height:
                        ratio = min(width / orig_width, height / orig_height)
                    elif width:
                        ratio = width / orig_width
                    elif height:
                        ratio = height / orig_height
                    else:
                        ratio = 1.0
                        
                    new_width = int(orig_width * ratio)
                    new_height = int(orig_height * ratio)
                    resized_img = img.resize((new_width, new_height), Image.LANCZOS)
                    
                elif resize_mode == "指定サイズに合わせる":
                    # 指定サイズに合わせる（余白なし）
                    if not width:
                        width = orig_width
                    if not height:
                        height = orig_height
                        
                    resized_img = img.resize((width, height), Image.LANCZOS)
                    
                elif resize_mode == "トリミング":
                    # アスペクト比を維持しつつ、はみ出た部分をトリミング
                    if not width:
                        width = orig_width
                    if not height:
                        height = orig_height
                        
                    ratio = max(width / orig_width, height / orig_height)
                    interim_width = int(orig_width * ratio)
                    interim_height = int(orig_height * ratio)
                    
                    interim_img = img.resize((interim_width, interim_height), Image.LANCZOS)
                    
                    # 中央部分を切り出し
                    left = (interim_width - width) // 2
                    top = (interim_height - height) // 2
                    right = left + width
                    bottom = top + height
                    
                    resized_img = interim_img.crop((left, top, right, bottom))
                
                # RGB形式に変換（アルファチャンネルを処理）
                if resized_img.mode == 'RGBA' and format_type and format_type.lower() == 'jpg':
                    background = Image.new('RGB', resized_img.size, (255, 255, 255))
                    background.paste(resized_img, mask=resized_img.split()[3])
                    resized_img = background
                
                # 同名ファイルが存在する場合
                if os.path.exists(dst_path):
                    response = messagebox.askyesnocancel(
                        "確認", 
                        f"ファイル '{os.path.basename(dst_path)}' は既に存在します。上書きしますか？"
                    )
                    
                    if response is None or not response:  # キャンセルまたはいいえ
                        continue
                
                # 保存
                if format_type:
                    if format_type.lower() == 'jpg':
                        resized_img.save(dst_path, 'JPEG', quality=quality)
                    elif format_type.lower() == 'png':
                        resized_img.save(dst_path, 'PNG')
                    elif format_type.lower() == 'bmp':
                        resized_img.save(dst_path, 'BMP')
                else:
                    # 元の形式で保存
                    ext = os.path.splitext(src_path)[1].lower()
                    if ext == '.jpg' or ext == '.jpeg':
                        resized_img.save(dst_path, 'JPEG', quality=quality)
                    elif ext == '.png':
                        resized_img.save(dst_path, 'PNG')
                    elif ext == '.bmp':
                        resized_img.save(dst_path, 'BMP')
                    else:
                        resized_img.save(dst_path)
                
                resized_count += 1
                
            except Exception as e:
                error_count += 1
                print(f"リサイズエラー: {e}")
        
        # 処理完了
        progress_win.destroy()
        
        # 結果表示
        result_msg = f"{resized_count}個のファイルをリサイズしました。"
        if error_count > 0:
            result_msg += f"\n{error_count}個のファイルでエラーが発生しました。"
            
        messagebox.showinfo("リサイズ完了", result_msg)
        
        # リサイズ後は画像リストを更新
        if resized_count > 0:
            self.load_images(self.current_folder)

    def fill_region_checked_images(self):
        # チェックした画像の特定領域を塗りつぶし
        if not self.checked_images:
            messagebox.showinfo("情報", "処理する画像が選択されていません。")
            return
            
        # 塗りつぶしダイアログを表示
        fill_dialog = FillRegionDialog(self.root)
        if not fill_dialog.result:
            return
            
        # 設定を取得
        x1 = fill_dialog.x1
        y1 = fill_dialog.y1
        x2 = fill_dialog.x2
        y2 = fill_dialog.y2
        color = fill_dialog.color
        format_type = fill_dialog.format_type
        quality = fill_dialog.quality
        
        # 進捗ダイアログ
        progress_win = tk.Toplevel(self.root)
        progress_win.title("処理中")
        progress_win.geometry("300x100")
        progress_win.transient(self.root)
        progress_win.grab_set()
        
        progress_lbl = ttk.Label(progress_win, text="ファイルを処理中...")
        progress_lbl.pack(pady=10)
        
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(progress_win, variable=progress_var, maximum=len(self.checked_images))
        progress_bar.pack(fill=tk.X, padx=10, pady=10)
        
        # 処理を別スレッドで実行
        thread_args = (x1, y1, x2, y2, color, format_type, quality, progress_win, progress_var, progress_lbl)
        threading.Thread(target=self._fill_region_thread, args=thread_args).start()

    def _fill_region_thread(self, x1, y1, x2, y2, color, format_type, quality, progress_win, progress_var, progress_lbl):
        # 塗りつぶし処理の実行
        processed_count = 0
        error_count = 0
        
        for i, idx in enumerate(sorted(self.checked_images)):
            if idx >= len(self.image_files):
                continue
                
            src_path = self.image_files[idx]
            file_name = os.path.splitext(os.path.basename(src_path))[0]
            
            # 出力ファイル名を生成
            if format_type:
                dst_path = os.path.join(os.path.dirname(src_path), f"{file_name}_filled.{format_type.lower()}")
            else:
                ext = os.path.splitext(src_path)[1]
                dst_path = os.path.join(os.path.dirname(src_path), f"{file_name}_filled{ext}")
            
            progress_var.set(i + 1)
            progress_lbl.config(text=f"処理中: {os.path.basename(src_path)}")
            progress_win.update_idletasks()
            
            try:
                # 画像を開く
                img = Image.open(src_path)
                
                # 描画用オブジェクト
                draw = ImageDraw.Draw(img)
                
                # 指定領域を塗りつぶし
                draw.rectangle([x1, y1, x2, y2], fill=color)
                
                # RGB形式に変換（アルファチャンネルを処理）
                if img.mode == 'RGBA' and format_type and format_type.lower() == 'jpg':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])
                    img = background
                
                # 同名ファイルが存在する場合
                if os.path.exists(dst_path):
                    response = messagebox.askyesnocancel(
                        "確認", 
                        f"ファイル '{os.path.basename(dst_path)}' は既に存在します。上書きしますか？"
                    )
                    
                    if response is None or not response:  # キャンセルまたはいいえ
                        continue
                
                # 保存
                if format_type:
                    if format_type.lower() == 'jpg':
                        img.save(dst_path, 'JPEG', quality=quality)
                    elif format_type.lower() == 'png':
                        img.save(dst_path, 'PNG')
                    elif format_type.lower() == 'bmp':
                        img.save(dst_path, 'BMP')
                else:
                    # 元の形式で保存
                    ext = os.path.splitext(src_path)[1].lower()
                    if ext == '.jpg' or ext == '.jpeg':
                        img.save(dst_path, 'JPEG', quality=quality)
                    elif ext == '.png':
                        img.save(dst_path, 'PNG')
                    elif ext == '.bmp':
                        img.save(dst_path, 'BMP')
                    else:
                        img.save(dst_path)
                
                processed_count += 1
                
            except Exception as e:
                error_count += 1
                print(f"処理エラー: {e}")
        
        # 処理完了
        progress_win.destroy()
        
        # 結果表示
        result_msg = f"{processed_count}個のファイルを処理しました。"
        if error_count > 0:
            result_msg += f"\n{error_count}個のファイルでエラーが発生しました。"
            
        messagebox.showinfo("処理完了", result_msg)
        
        # 処理後は画像リストを更新
        if processed_count > 0:
            self.load_images(self.current_folder)

    def prev_image(self, event=None):
        # 前の画像を表示
        if self.selected_image_index > 0:
            self.select_image(self.selected_image_index - 1)

    def next_image(self, event=None):
        # 次の画像を表示
        if self.selected_image_index < len(self.image_files) - 1:
            self.select_image(self.selected_image_index + 1)

    def show_help(self):
        # ヘルプ情報を表示
        help_text = """
画像ビューワの使い方:

【基本操作】
・左側のフォルダツリーからフォルダを選択して画像を表示できます。
・上部にサムネイルが表示され、クリックで選択できます。
・サムネイル下のチェックボックスで画像を選択できます。
・選択した画像は下部に大きく表示されます。

【ショートカットキー】
・左右矢印キー: 前/次の画像を表示
・スペースキー: 現在の画像のチェックを切り替え

【画像の操作】
・「全てチェック」「全てチェック解除」ボタンで一括操作ができます。
・チェックした画像に対して、コピー、移動、リネーム、形式変更、リサイズ、
 領域塗りつぶしの操作ができます。

※チェック状態は自動的に保存され、アプリを再起動しても維持されます。
        """
        
        help_window = tk.Toplevel(self.root)
        help_window.title("使い方")
        help_window.geometry("500x400")
        help_window.transient(self.root)
        
        text = tk.Text(help_window, wrap=tk.WORD, padx=10, pady=10)
        text.pack(fill=tk.BOTH, expand=True)
        text.insert(tk.END, help_text)
        text.config(state=tk.DISABLED)
        
        close_button = ttk.Button(help_window, text="閉じる", command=help_window.destroy)
        close_button.pack(pady=10)

    def show_about(self):
        # バージョン情報を表示
        about_text = """
画像ビューワ v1.0

動画から切り出した静止画をチェックするためのアプリケーションです。
画像のチェック、管理、編集機能を提供します。

© 2025 Your Name
        """
        
        messagebox.showinfo("バージョン情報", about_text)

    def create_tooltip(self, widget, text):
        # ツールチップの作成
        tooltip = ToolTip(widget, text)
        return tooltip


class ToolTip:
    """
    ウィジェット上にマウスを置いたときに表示されるツールチップ
    """
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
    
    def show_tooltip(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        # ツールチップウィンドウを作成
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        
        label = ttk.Label(self.tooltip, text=self.text, background="#FFFFDD", relief=tk.SOLID, borderwidth=1)
        label.pack()
    
    def hide_tooltip(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None


class RenameDialog:
    """
    ファイル名変更ダイアログ
    """
    def __init__(self, parent, file_count):
        self.result = None
        
        # ダイアログウィンドウの作成
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("リネーム設定")
        self.dialog.geometry("400x200")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # ファイル名のベース
        ttk.Label(self.dialog, text="ファイル名のベース:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        self.base_name_var = tk.StringVar(value="image_")
        ttk.Entry(self.dialog, textvariable=self.base_name_var, width=20).grid(row=0, column=1, padx=10, pady=10)
        
        # 開始番号
        ttk.Label(self.dialog, text="開始番号:").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        self.start_number_var = tk.IntVar(value=1)
        ttk.Spinbox(self.dialog, from_=0, to=9999, textvariable=self.start_number_var, width=5).grid(row=1, column=1, padx=10, pady=10, sticky=tk.W)
        
        # 桁数
        ttk.Label(self.dialog, text="桁数:").grid(row=2, column=0, padx=10, pady=10, sticky=tk.W)
        self.digits_var = tk.IntVar(value=3)
        ttk.Spinbox(self.dialog, from_=1, to=10, textvariable=self.digits_var, width=5).grid(row=2, column=1, padx=10, pady=10, sticky=tk.W)

        # プレビュー
        ttk.Label(self.dialog, text="プレビュー:").grid(row=3, column=0, padx=10, pady=10, sticky=tk.W)
        self.preview_var = tk.StringVar()
        ttk.Label(self.dialog, textvariable=self.preview_var).grid(row=3, column=1, padx=10, pady=10, sticky=tk.W)
        self.update_preview()

        # ボタン
        button_frame = ttk.Frame(self.dialog)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="OK", command=self.ok).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="キャンセル", command=self.cancel).pack(side=tk.LEFT, padx=10)

        # 入力値の変更を監視
        self.base_name_var.trace('w', lambda *args: self.update_preview())
        self.start_number_var.trace('w', lambda *args: self.update_preview())
        self.digits_var.trace('w', lambda *args: self.update_preview())

    def update_preview(self):
        try:
            number = self.start_number_var.get()
            digits = self.digits_var.get()
            preview = f"{self.base_name_var.get()}{number:0{digits}d}.jpg"
            self.preview_var.set(preview)
        except:
            self.preview_var.set("Invalid input")

    def ok(self):
        self.base_name = self.base_name_var.get()
        self.start_number = self.start_number_var.get()
        self.digits = self.digits_var.get()
        self.result = True
        self.dialog.destroy()

    def cancel(self):
        self.result = False
        self.dialog.destroy()


class ConvertDialog:
    """
    画像形式変換ダイアログ
    """
    def __init__(self, parent):
        self.result = None
        
        # ダイアログウィンドウの作成
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("形式変換設定")
        self.dialog.geometry("300x200")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 形式選択
        ttk.Label(self.dialog, text="変換形式:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        self.format_var = tk.StringVar(value="JPG")
        format_frame = ttk.Frame(self.dialog)
        format_frame.grid(row=0, column=1, padx=10, pady=10, sticky=tk.W)
        
        ttk.Radiobutton(format_frame, text="JPG", variable=self.format_var, value="JPG", 
                       command=self.on_format_change).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(format_frame, text="PNG", variable=self.format_var, value="PNG", 
                       command=self.on_format_change).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(format_frame, text="BMP", variable=self.format_var, value="BMP", 
                       command=self.on_format_change).pack(side=tk.LEFT, padx=5)

        # JPEG品質
        self.quality_frame = ttk.LabelFrame(self.dialog, text="JPEG品質")
        self.quality_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky=tk.EW)
        
        self.quality_var = tk.IntVar(value=85)
        self.quality_scale = ttk.Scale(self.quality_frame, from_=1, to=100, orient=tk.HORIZONTAL, 
                                     variable=self.quality_var)
        self.quality_scale.pack(padx=10, pady=5, fill=tk.X)
        
        self.quality_label = ttk.Label(self.quality_frame, text="85")
        self.quality_label.pack(pady=5)
        self.quality_var.trace('w', self.update_quality_label)

        # ボタン
        button_frame = ttk.Frame(self.dialog)
        button_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="OK", command=self.ok).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="キャンセル", command=self.cancel).pack(side=tk.LEFT, padx=10)

        # 初期状態の設定
        self.on_format_change()

    def on_format_change(self):
        # JPGの場合のみ品質設定を有効化
        if self.format_var.get() == "JPG":
            self.quality_frame.grid()
        else:
            self.quality_frame.grid_remove()

    def update_quality_label(self, *args):
        self.quality_label.config(text=str(self.quality_var.get()))

    def ok(self):
        self.format_type = self.format_var.get()
        self.quality = self.quality_var.get()
        self.result = True
        self.dialog.destroy()

    def cancel(self):
        self.result = False
        self.dialog.destroy()


class ResizeDialog:
    """
    画像リサイズダイアログ
    """
    def __init__(self, parent):
        self.result = None

        # ダイアログウィンドウの作成
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("リサイズ設定")
        self.dialog.geometry("400x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # リサイズモード
        ttk.Label(self.dialog, text="リサイズモード:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        self.mode_var = tk.StringVar(value="比率を維持")
        mode_frame = ttk.Frame(self.dialog)
        mode_frame.grid(row=0, column=1, padx=10, pady=10, sticky=tk.W)
        
        modes = ["比率を維持", "指定サイズに合わせる", "トリミング"]
        for mode in modes:
            ttk.Radiobutton(mode_frame, text=mode, variable=self.mode_var, value=mode).pack(anchor=tk.W)

        # サイズ設定
        size_frame = ttk.LabelFrame(self.dialog, text="サイズ指定")
        size_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky=tk.EW)

        ttk.Label(size_frame, text="幅:").grid(row=0, column=0, padx=5, pady=5)
        self.width_var = tk.StringVar()
        ttk.Entry(size_frame, textvariable=self.width_var, width=10).grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(size_frame, text="px").grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(size_frame, text="高さ:").grid(row=1, column=0, padx=5, pady=5)
        self.height_var = tk.StringVar()
        ttk.Entry(size_frame, textvariable=self.height_var, width=10).grid(row=1, column=1, padx=5, pady=5)
        ttk.Label(size_frame, text="px").grid(row=1, column=2, padx=5, pady=5)

        # 出力形式
        format_frame = ttk.LabelFrame(self.dialog, text="出力形式")
        format_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky=tk.EW)

        self.format_var = tk.StringVar(value="変更なし")
        formats = ["変更なし", "JPG", "PNG", "BMP"]
        for i, fmt in enumerate(formats):
            ttk.Radiobutton(format_frame, text=fmt, variable=self.format_var, 
                          value=fmt, command=self.on_format_change).grid(row=i, column=0, padx=5, pady=2, sticky=tk.W)

        # JPEG品質
        self.quality_frame = ttk.LabelFrame(self.dialog, text="JPEG品質")
        self.quality_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky=tk.EW)
        
        self.quality_var = tk.IntVar(value=85)
        self.quality_scale = ttk.Scale(self.quality_frame, from_=1, to=100, orient=tk.HORIZONTAL, 
                                     variable=self.quality_var)
        self.quality_scale.pack(padx=10, pady=5, fill=tk.X)
        
        self.quality_label = ttk.Label(self.quality_frame, text="85")
        self.quality_label.pack(pady=5)
        self.quality_var.trace('w', self.update_quality_label)

        # ボタン
        button_frame = ttk.Frame(self.dialog)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="OK", command=self.ok).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="キャンセル", command=self.cancel).pack(side=tk.LEFT, padx=10)

        # 初期状態の設定
        self.on_format_change()

    def on_format_change(self):
        # JPGの場合のみ品質設定を有効化
        if self.format_var.get() == "JPG":
            self.quality_frame.grid()
        else:
            self.quality_frame.grid_remove()

    def update_quality_label(self, *args):
        self.quality_label.config(text=str(self.quality_var.get()))

    def ok(self):
        # 入力値の検証
        try:
            self.width = int(self.width_var.get()) if self.width_var.get() else None
            self.height = int(self.height_var.get()) if self.height_var.get() else None
            
            if (self.width is not None and self.width <= 0) or \
               (self.height is not None and self.height <= 0):
                raise ValueError("サイズは正の整数を指定してください")
                
            if self.width is None and self.height is None:
                raise ValueError("幅か高さのどちらかを指定してください")
                
        except ValueError as e:
            messagebox.showerror("エラー", str(e))
            return

        self.resize_mode = self.mode_var.get()
        self.format_type = None if self.format_var.get() == "変更なし" else self.format_var.get()
        self.quality = self.quality_var.get()
        self.result = True
        self.dialog.destroy()

    def cancel(self):
        self.result = False
        self.dialog.destroy()


class FillRegionDialog:
    """
    領域塗りつぶしダイアログ
    """
    def __init__(self, parent):
        self.result = None

        # ダイアログウィンドウの作成
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("領域塗りつぶし設定")
        self.dialog.geometry("400x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 座標指定
        coords_frame = ttk.LabelFrame(self.dialog, text="塗りつぶし座標")
        coords_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky=tk.EW)

        # 左上座標
        ttk.Label(coords_frame, text="左上 X:").grid(row=0, column=0, padx=5, pady=5)
        self.x1_var = tk.StringVar()
        ttk.Entry(coords_frame, textvariable=self.x1_var, width=10).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(coords_frame, text="Y:").grid(row=0, column=2, padx=5, pady=5)
        self.y1_var = tk.StringVar()
        ttk.Entry(coords_frame, textvariable=self.y1_var, width=10).grid(row=0, column=3, padx=5, pady=5)

        # 右下座標
        ttk.Label(coords_frame, text="右下 X:").grid(row=1, column=0, padx=5, pady=5)
        self.x2_var = tk.StringVar()
        ttk.Entry(coords_frame, textvariable=self.x2_var, width=10).grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(coords_frame, text="Y:").grid(row=1, column=2, padx=5, pady=5)
        self.y2_var = tk.StringVar()
        ttk.Entry(coords_frame, textvariable=self.y2_var, width=10).grid(row=1, column=3, padx=5, pady=5)

        # 塗りつぶし色
        color_frame = ttk.LabelFrame(self.dialog, text="塗りつぶし色")
        color_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky=tk.EW)

        self.color_var = tk.StringVar(value="#000000")
        ttk.Entry(color_frame, textvariable=self.color_var, width=10).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(color_frame, text="色を選択", command=self.choose_color).pack(side=tk.LEFT, padx=5, pady=5)

        # プレビュー
        self.preview_canvas = tk.Canvas(color_frame, width=50, height=25, bg=self.color_var.get())
        self.preview_canvas.pack(side=tk.LEFT, padx=5, pady=5)
        self.color_var.trace('w', self.update_preview)

        # 出力形式
        format_frame = ttk.LabelFrame(self.dialog, text="出力形式")
        format_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky=tk.EW)

        self.format_var = tk.StringVar(value="変更なし")
        formats = ["変更なし", "JPG", "PNG", "BMP"]
        for i, fmt in enumerate(formats):
            ttk.Radiobutton(format_frame, text=fmt, variable=self.format_var, 
                          value=fmt, command=self.on_format_change).grid(row=i, column=0, padx=5, pady=2, sticky=tk.W)

        # JPEG品質
        self.quality_frame = ttk.LabelFrame(self.dialog, text="JPEG品質")
        self.quality_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky=tk.EW)
        
        self.quality_var = tk.IntVar(value=85)
        self.quality_scale = ttk.Scale(self.quality_frame, from_=1, to=100, orient=tk.HORIZONTAL, 
                                     variable=self.quality_var)
        self.quality_scale.pack(padx=10, pady=5, fill=tk.X)
        
        self.quality_label = ttk.Label(self.quality_frame, text="85")
        self.quality_label.pack(pady=5)
        self.quality_var.trace('w', self.update_quality_label)

        # ボタン
        button_frame = ttk.Frame(self.dialog)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="OK", command=self.ok).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="キャンセル", command=self.cancel).pack(side=tk.LEFT, padx=10)

        # 初期状態の設定
        self.on_format_change()

    def choose_color(self):
        color = colorchooser.askcolor(color=self.color_var.get())[1]
        if color:
            self.color_var.set(color)

    def update_preview(self, *args):
        try:
            self.preview_canvas.configure(bg=self.color_var.get())
        except:
            pass

    def on_format_change(self):
        if self.format_var.get() == "JPG":
            self.quality_frame.grid()
        else:
            self.quality_frame.grid_remove()

    def update_quality_label(self, *args):
        self.quality_label.config(text=str(self.quality_var.get()))

    def ok(self):
        try:
            # 座標の検証
            self.x1 = int(self.x1_var.get())
            self.y1 = int(self.y1_var.get())
            self.x2 = int(self.x2_var.get())
            self.y2 = int(self.y2_var.get())
            
            if self.x1 >= self.x2 or self.y1 >= self.y2:
                raise ValueError("右下の座標は左上の座標より大きい値を指定してください")
                
            # 色の検証
            color = self.color_var.get()
            if not color.startswith('#') or len(color) != 7:
                raise ValueError("色は16進数形式(#RRGGBB)で指定してください")
                
            self.color = color
            self.format_type = None if self.format_var.get() == "変更なし" else self.format_var.get()
            self.quality = self.quality_var.get()
            self.result = True
            self.dialog.destroy()
            
        except ValueError as e:
            messagebox.showerror("エラー", str(e))

    def cancel(self):
        self.result = False
        self.dialog.destroy()


def main():
    root = tk.Tk()
    app = ImageViewerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()