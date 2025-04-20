import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, colorchooser
from PIL import Image, ImageTk, ImageDraw
import os
import shutil
import json
import math

# 定数
THUMBNAIL_SIZES = {
    "Small (80x45)": (80, 45),
    "Large (160x90)": (160, 90),
}
DEFAULT_THUMBNAIL_KEY = "Large (160x90)"
CHECK_STATE_FILENAME = "_checked_files.json"
SUPPORTED_IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff')

class ImageCheckerApp(tk.Tk):
    """
    画像チェック・管理アプリケーションのメインクラス
    """
    def __init__(self):
        super().__init__()
        self.title("画像ビューア・チェッカー")
        self.geometry("1200x800")

        # --- 変数 ---
        self.current_folder = tk.StringVar()
        self.selected_image_path = tk.StringVar()
        self.thumbnail_size_var = tk.StringVar(value=DEFAULT_THUMBNAIL_KEY)
        self.image_files = [] # 現在のフォルダの画像ファイルリスト [(path, filename), ...]
        self.thumbnail_widgets = {} # {path: {'frame': frame, 'label': label, 'check_var': var, 'checkbutton': cb}}
        self.checked_state = {} # {filename: bool}
        self.preview_image_object = None # ImageTkオブジェクトへの参照を保持
        self.thumbnail_image_objects = {} # {path: ImageTkオブジェクト}
        self.root_folder_path = None # 選択されたルートフォルダのパス

        # --- UIのセットアップ ---
        self._setup_ui()
        # self._populate_initial_tree() # 初期ツリー設定は削除

    def _setup_ui(self):
        """UIウィジェットの配置"""
        # --- メインレイアウト (左右分割) ---
        main_paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned_window.pack(fill=tk.BOTH, expand=True)

        # --- 左ペイン (フォルダツリー) ---
        left_frame = ttk.Frame(main_paned_window, padding=5)
        main_paned_window.add(left_frame, weight=1)

        # ルートフォルダ選択ボタンを追加
        select_root_button = ttk.Button(left_frame, text="ルートフォルダを選択...", command=self._select_root_folder)
        select_root_button.pack(anchor=tk.W, pady=(0, 5))

        ttk.Label(left_frame, text="フォルダツリー").pack(anchor=tk.W)
        self.tree = ttk.Treeview(left_frame, show='tree')
        tree_scrollbar_y = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.tree.yview)
        tree_scrollbar_x = ttk.Scrollbar(left_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=tree_scrollbar_y.set, xscrollcommand=tree_scrollbar_x.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        tree_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree.bind("<<TreeviewSelect>>", self._on_folder_select)
        self.tree.bind("<Double-1>", self._on_tree_expand) # ダブルクリックで展開

        # --- 右ペイン (上:サムネイル, 下:プレビュー) ---
        right_paned_window = ttk.PanedWindow(main_paned_window, orient=tk.VERTICAL)
        main_paned_window.add(right_paned_window, weight=4) # 右ペインを広く取る

        # --- 右上: サムネイルエリア ---
        thumbnail_area_frame = ttk.Frame(right_paned_window, padding=5)
        right_paned_window.add(thumbnail_area_frame, weight=2) # サムネイルエリアの比重

        # サムネイルコントロールフレーム
        thumbnail_controls_frame = ttk.Frame(thumbnail_area_frame)
        thumbnail_controls_frame.pack(fill=tk.X, pady=5)

        ttk.Label(thumbnail_controls_frame, text="サムネイルサイズ:").pack(side=tk.LEFT, padx=5)
        for size_key in THUMBNAIL_SIZES:
            rb = ttk.Radiobutton(thumbnail_controls_frame, text=size_key, variable=self.thumbnail_size_var,
                                 value=size_key, command=self._update_thumbnails_display)
            rb.pack(side=tk.LEFT, padx=5)

        ttk.Button(thumbnail_controls_frame, text="全てチェック", command=self._check_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(thumbnail_controls_frame, text="全て解除", command=self._uncheck_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(thumbnail_controls_frame, text="チェック項目をコピー", command=self._copy_checked).pack(side=tk.LEFT, padx=5)
        ttk.Button(thumbnail_controls_frame, text="チェック項目を移動", command=self._move_checked).pack(side=tk.LEFT, padx=5)
        ttk.Button(thumbnail_controls_frame, text="チェック項目を処理...", command=self._open_process_dialog).pack(side=tk.LEFT, padx=5)


        # サムネイル表示用キャンバスとスクロールバー
        thumbnail_canvas_frame = ttk.Frame(thumbnail_area_frame)
        thumbnail_canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.thumbnail_canvas = tk.Canvas(thumbnail_canvas_frame, borderwidth=0, background="#ffffff")
        thumbnail_scrollbar_h = ttk.Scrollbar(thumbnail_canvas_frame, orient=tk.HORIZONTAL, command=self.thumbnail_canvas.xview)
        thumbnail_scrollbar_v = ttk.Scrollbar(thumbnail_canvas_frame, orient=tk.VERTICAL, command=self.thumbnail_canvas.yview) # 縦スクロールも追加
        self.thumbnail_canvas.configure(xscrollcommand=thumbnail_scrollbar_h.set, yscrollcommand=thumbnail_scrollbar_v.set)

        thumbnail_scrollbar_h.pack(side=tk.BOTTOM, fill=tk.X)
        thumbnail_scrollbar_v.pack(side=tk.RIGHT, fill=tk.Y) # 縦スクロールバーを右に配置
        self.thumbnail_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # キャンバス内にフレームを配置し、そのフレームにウィジェットを追加する
        self.thumbnails_frame = ttk.Frame(self.thumbnail_canvas, padding=5)
        self.thumbnail_canvas.create_window((0, 0), window=self.thumbnails_frame, anchor="nw")

        # スクロール範囲の設定
        self.thumbnails_frame.bind("<Configure>", lambda e: self.thumbnail_canvas.configure(scrollregion=self.thumbnail_canvas.bbox("all")))
        # マウスホイールでのスクロール (プラットフォーム依存性あり)
        self.thumbnail_canvas.bind_all("<MouseWheel>", self._on_mousewheel) # Windows/MacOS
        self.thumbnail_canvas.bind_all("<Button-4>", lambda e: self.thumbnail_canvas.yview_scroll(-1, "units")) # Linux上スクロール
        self.thumbnail_canvas.bind_all("<Button-5>", lambda e: self.thumbnail_canvas.yview_scroll(1, "units"))  # Linux下スクロール


        # --- 右下: プレビューエリア ---
        preview_frame = ttk.Frame(right_paned_window, padding=5)
        right_paned_window.add(preview_frame, weight=3) # プレビューエリアの比重

        ttk.Label(preview_frame, text="プレビュー").pack(anchor=tk.W)
        self.preview_label = ttk.Label(preview_frame, background='gray', anchor=tk.CENTER)
        self.preview_label.pack(fill=tk.BOTH, expand=True)
        self.preview_label.bind("<Configure>", self._update_preview_image) # ウィンドウリサイズ時にプレビュー更新

        # --- ステータスバー ---
        self.status_bar = ttk.Label(self, text="ルートフォルダを選択してください", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _on_mousewheel(self, event):
        """マウスホイールイベントハンドラ (Windows/MacOS)"""
        # delta > 0 は上スクロール, < 0 は下スクロール
        # shiftキーが押されている場合は横スクロール
        if event.state & 0x0004: # Shiftキー
             self.thumbnail_canvas.xview_scroll(int(-1*(event.delta/120)), "units")
        else:
             self.thumbnail_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _select_root_folder(self):
        """ルートフォルダ選択ダイアログを開き、ツリーを初期化する"""
        selected_folder = filedialog.askdirectory(title="ルートフォルダを選択")
        if selected_folder:
            self.root_folder_path = selected_folder
            self._populate_tree(self.root_folder_path)
            self.status_bar.config(text=f"ルートフォルダ: {self.root_folder_path}")
        else:
             # フォルダが選択されなかった場合、ルートが設定されていなければメッセージを表示
             if not self.root_folder_path:
                 self.status_bar.config(text="ルートフォルダを選択してください")


    def _populate_tree(self, root_path):
        """指定されたパスを起点としてツリービューを構築する"""
        # 既存のツリーアイテムを全て削除
        for item in self.tree.get_children():
            self.tree.delete(item)

        # ルートノードを挿入
        root_display_name = os.path.basename(root_path) if os.path.basename(root_path) else root_path # ルートがドライブ文字などの場合
        root_node_id = self.tree.insert('', 'end', text=root_display_name, values=[root_path], open=True) # 最初は開いた状態にする

        # ルートフォルダ直下のサブフォルダを挿入 (遅延読み込みのため、ここでは1階層のみ)
        try:
            for item in sorted(os.listdir(root_path)):
                item_path = os.path.join(root_path, item)
                if os.path.isdir(item_path):
                    self._insert_node(root_node_id, item_path, item)
        except OSError as e:
            self.status_bar.config(text=f"エラー: {root_path} にアクセスできません: {e}")


    def _insert_node(self, parent_id, path, display_name):
        """ツリービューにノードを挿入 (サブフォルダを持つ可能性を示すダミーノード付き)"""
        try:
            # isdirチェックでアクセス権限エラーが発生することがある
            if os.path.isdir(path):
                node_id = self.tree.insert(parent_id, 'end', text=display_name, values=[path], open=False)
                # このフォルダ内にさらにサブフォルダがあるかチェック
                has_subdir = False
                try:
                    for sub_item in os.listdir(path):
                        sub_item_path = os.path.join(path, sub_item)
                        if os.path.isdir(sub_item_path):
                            has_subdir = True
                            break # 1つでも見つかればOK
                except OSError:
                    pass # アクセスできないフォルダは無視

                # サブフォルダがある場合のみ、展開可能アイコンを表示するためのダミーノードを追加
                if has_subdir:
                    self.tree.insert(node_id, 'end', text='dummy') # ダミーノード
        except OSError as e:
            print(f"Error accessing path {path}: {e}") # コンソールにエラー出力

    def _on_tree_expand(self, event=None):
        """ツリーノード展開時の処理 (ダミーノードを実際のサブフォルダで置き換え)"""
        selected_id = self.tree.focus()
        if not selected_id:
            return

        # ダミーノードが存在するか確認し、存在すれば削除して実際の子ディレクトリを挿入
        children = self.tree.get_children(selected_id)
        if children and self.tree.item(children[0], 'text') == 'dummy':
            self.tree.delete(children[0]) # ダミーノード削除
            parent_path = self.tree.item(selected_id, 'values')[0]
            try:
                # フォルダをソートして挿入
                subdirs = sorted([d for d in os.listdir(parent_path) if os.path.isdir(os.path.join(parent_path, d))])
                for item in subdirs:
                    item_path = os.path.join(parent_path, item)
                    self._insert_node(selected_id, item_path, item) # 再帰的に挿入関数を呼ぶ
            except OSError as e:
                self.status_bar.config(text=f"エラー: {parent_path} にアクセスできません: {e}")


    def _on_folder_select(self, event=None):
        """フォルダツリーでフォルダが選択されたときの処理"""
        selected_id = self.tree.focus()
        if not selected_id:
            return

        # values属性が存在し、空でないことを確認
        item_values = self.tree.item(selected_id, 'values')
        if not item_values: # ルートノードなどが選択された直後など、valuesがない場合がある
             return

        folder_path = item_values[0]

        if os.path.isdir(folder_path):
            if self.current_folder.get() != folder_path:
                self.current_folder.set(folder_path)
                self.status_bar.config(text=f"フォルダ: {folder_path}")
                self._load_images()
                self._load_checked_state() # チェック状態をロード
                self._update_thumbnails_display()
                self.selected_image_path.set("") # プレビューをクリア
                self.preview_label.config(image=None) # プレビュー表示をクリア
                self.preview_image_object = None # 参照をクリア
        else:
            # 選択されたアイテムがフォルダでない場合（ファイルなど）は無視するか、メッセージを表示
            # ここでは何もしない
            pass
            # self.status_bar.config(text="選択されたアイテムはフォルダではありません")

    def _load_images(self):
        """選択されたフォルダから画像ファイルを読み込む"""
        folder_path = self.current_folder.get()
        self.image_files = []
        self.thumbnail_widgets = {} # ウィジェット情報をリセット
        self.thumbnail_image_objects = {} # サムネイル画像参照をリセット

        if not folder_path or not os.path.isdir(folder_path):
            # サムネイル表示をクリアする
            for widget_dict in self.thumbnail_widgets.values():
                widget_dict['frame'].destroy()
            self.thumbnail_widgets = {}
            self.thumbnail_image_objects = {}
            self.thumbnails_frame.update_idletasks()
            self.thumbnail_canvas.configure(scrollregion=self.thumbnail_canvas.bbox("all"))
            return

        try:
            filenames = sorted([f for f in os.listdir(folder_path)
                                if os.path.isfile(os.path.join(folder_path, f)) and
                                f.lower().endswith(SUPPORTED_IMAGE_EXTENSIONS)])
            self.image_files = [(os.path.join(folder_path, fname), fname) for fname in filenames]
            self.status_bar.config(text=f"{len(self.image_files)} 個の画像ファイルを読み込みました: {folder_path}")
        except OSError as e:
            messagebox.showerror("エラー", f"フォルダの読み込みに失敗しました: {e}")
            self.image_files = []
            # エラー時もサムネイル表示をクリア
            for widget_dict in self.thumbnail_widgets.values():
                widget_dict['frame'].destroy()
            self.thumbnail_widgets = {}
            self.thumbnail_image_objects = {}
            self.thumbnails_frame.update_idletasks()
            self.thumbnail_canvas.configure(scrollregion=self.thumbnail_canvas.bbox("all"))


    def _update_thumbnails_display(self):
        """サムネイル表示エリアを更新する"""
        # 既存のサムネイルウィジェットを削除
        for widget_dict in list(self.thumbnail_widgets.values()): # イテレート中に削除するためリストのコピーを使用
            if widget_dict.get('frame'):
                widget_dict['frame'].destroy()
        self.thumbnail_widgets = {}
        self.thumbnail_image_objects = {} # 参照をクリア

        # キャンバス内のフレームの内容をクリア (より確実に)
        for widget in self.thumbnails_frame.winfo_children():
            widget.destroy()


        if not self.image_files:
             # 画像がない場合、スクロール領域をリセット
             self.thumbnails_frame.update_idletasks()
             self.thumbnail_canvas.configure(scrollregion=self.thumbnail_canvas.bbox("all"))
             return

        thumb_size = THUMBNAIL_SIZES[self.thumbnail_size_var.get()]
        max_width, max_height = thumb_size

        row, col = 0, 0
        padding = 5
        # サムネイルフレームの現在の幅を取得しようとする
        container_width = self.thumbnails_frame.winfo_width()
        if container_width <= 1: # まだ幅が確定していない場合、親のキャンバス幅を使う試み
             container_width = self.thumbnail_canvas.winfo_width() - thumbnail_scrollbar_v.winfo_width() # スクロールバーの幅を考慮
        if container_width <= 1 : # それでもダメならデフォルト値
             container_width = 800 # 適当なデフォルト値

        items_per_row = max(1, container_width // (max_width + padding * 2 + 10)) # 余裕を持たせる

        for img_path, filename in self.image_files:
            try:
                # --- サムネイル作成 ---
                img = Image.open(img_path)
                # RGBAモードの場合、背景を白色で合成してRGBにする (JPEG保存などで問題になるため)
                if img.mode == 'RGBA':
                    bg = Image.new('RGB', img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[3]) # alphaチャンネルをマスクとして使用
                    img = bg
                elif img.mode == 'P': # パレットモードの場合もRGBに変換
                    img = img.convert('RGB')
                elif img.mode != 'RGB': # その他のモードもRGBに試みる
                    img = img.convert('RGB')


                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

                # アスペクト比を保ったまま中央に配置するための背景を作成
                bg_color = (255, 255, 255) # 白色背景
                final_thumb = Image.new('RGB', (max_width, max_height), bg_color)
                paste_x = (max_width - img.width) // 2
                paste_y = (max_height - img.height) // 2
                final_thumb.paste(img, (paste_x, paste_y))

                # Tkinterで表示できる形式に変換し、参照を保持
                tk_thumb = ImageTk.PhotoImage(final_thumb)
                self.thumbnail_image_objects[img_path] = tk_thumb # 参照を保持

                # --- ウィジェット作成 ---
                item_frame = ttk.Frame(self.thumbnails_frame, padding=padding)

                # チェックボックス
                check_var = tk.BooleanVar()
                # 以前のチェック状態を復元
                if filename in self.checked_state:
                    check_var.set(self.checked_state[filename])
                else:
                    check_var.set(False) # デフォルトはオフ
                checkbutton = ttk.Checkbutton(item_frame, variable=check_var,
                                              command=lambda f=filename, v=check_var, p=img_path: self._on_check_change(f, v, p)) # pathも渡す

                # サムネイル画像ラベル
                img_label = ttk.Label(item_frame, image=tk_thumb, anchor=tk.CENTER)
                img_label.bind("<Button-1>", lambda e, p=img_path: self._on_thumbnail_click(p))

                # ファイル名ラベル
                name_label = ttk.Label(item_frame, text=filename, wraplength=max_width, justify=tk.CENTER) # 折り返し

                # 配置
                checkbutton.pack(side=tk.TOP)
                img_label.pack(side=tk.TOP)
                name_label.pack(side=tk.TOP, fill=tk.X)

                # グリッド配置
                item_frame.grid(row=row, column=col, padx=padding, pady=padding, sticky="nsew")

                # ウィジェット情報を保存 (ファイル名をキーにする方が状態管理と整合性が取れる)
                self.thumbnail_widgets[filename] = { # キーをfilenameに変更
                    'frame': item_frame,
                    'label': img_label,
                    'check_var': check_var,
                    'checkbutton': checkbutton,
                    'path': img_path # パス情報も保持
                }

                col += 1
                if col >= items_per_row:
                    col = 0
                    row += 1

            except Exception as e:
                print(f"Error processing thumbnail for {img_path}: {e}") # コンソールにエラー出力
                # エラーが発生した画像のプレースホルダーを表示することも検討

        # スクロール領域を再計算
        self.thumbnails_frame.update_idletasks() # ウィジェットの配置を確定
        bbox = self.thumbnail_canvas.bbox("all")
        if bbox: # bboxがNoneでないことを確認
            self.thumbnail_canvas.configure(scrollregion=bbox)
        else: # サムネイルがない場合
             self.thumbnail_canvas.configure(scrollregion=(0,0,0,0))


    def _on_thumbnail_click(self, img_path):
        """サムネイルクリック時の処理 (プレビュー表示)"""
        self.selected_image_path.set(img_path)
        self._update_preview_image()

    def _update_preview_image(self, event=None):
        """プレビュー画像を更新する"""
        img_path = self.selected_image_path.get()
        if not img_path or not os.path.exists(img_path):
            self.preview_label.config(image=None, text="画像を選択してください")
            self.preview_image_object = None
            return

        try:
            # プレビューエリアのサイズを取得
            preview_width = self.preview_label.winfo_width()
            preview_height = self.preview_label.winfo_height()

            if preview_width <= 1 or preview_height <= 1: # ウィジェットがまだ描画されていない場合
                # 少し待ってから再試行
                self.after(50, self._update_preview_image)
                return

            img = Image.open(img_path)
            img_copy = img.copy() # 元の画像を保持

            # アスペクト比を維持してリサイズ
            img_copy.thumbnail((preview_width, preview_height), Image.Resampling.LANCZOS)

            # ImageTkオブジェクトを作成し、参照を保持
            self.preview_image_object = ImageTk.PhotoImage(img_copy)
            self.preview_label.config(image=self.preview_image_object, text="") # テキストをクリア

        except Exception as e:
            messagebox.showerror("プレビューエラー", f"画像のプレビュー表示に失敗しました:\n{img_path}\n{e}")
            self.preview_label.config(image=None, text="プレビューエラー")
            self.preview_image_object = None

    def _on_check_change(self, filename, var, path): # path引数を追加
        """チェックボックスの状態が変更されたときの処理"""
        self.checked_state[filename] = var.get()
        # thumbnail_widgetsのキーもfilenameに変更したため、整合性が取れる
        self._save_checked_state() # 変更を即座に保存

    def _save_checked_state(self):
        """現在のチェック状態をJSONファイルに保存"""
        folder_path = self.current_folder.get()
        if not folder_path or not os.path.isdir(folder_path):
            return

        json_path = os.path.join(folder_path, CHECK_STATE_FILENAME)
        try:
            # self.checked_stateを直接保存する
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(self.checked_state, f, indent=4)
        except Exception as e:
            print(f"Error saving check state to {json_path}: {e}") # コンソールにエラー出力

    def _load_checked_state(self):
        """JSONファイルからチェック状態を読み込む"""
        folder_path = self.current_folder.get()
        self.checked_state = {} # 読み込み前にリセット
        if not folder_path or not os.path.isdir(folder_path):
            return

        json_path = os.path.join(folder_path, CHECK_STATE_FILENAME)
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    loaded_state = json.load(f)
                    # ファイル名が存在するか確認しながら読み込む
                    current_filenames = {fname for _, fname in self.image_files}
                    self.checked_state = {fname: state
                                          for fname, state in loaded_state.items()
                                          if fname in current_filenames}

            except Exception as e:
                print(f"Error loading check state from {json_path}: {e}") # コンソールにエラー出力
                self.checked_state = {} # エラー時はリセット

    def _check_all(self):
        """表示されている全てのサムネイルをチェック"""
        changed = False
        for filename, data in self.thumbnail_widgets.items():
            if not data['check_var'].get():
                data['check_var'].set(True)
                self.checked_state[filename] = True # filenameをキーにする
                changed = True
        if changed:
            self._save_checked_state()

    def _uncheck_all(self):
        """表示されている全てのサムネイルのチェックを解除"""
        changed = False
        for filename, data in self.thumbnail_widgets.items():
            if data['check_var'].get():
                data['check_var'].set(False)
                self.checked_state[filename] = False # filenameをキーにする
                changed = True
        if changed:
            self._save_checked_state()

    def _get_checked_files(self):
        """チェックされているファイルのフルパスリストを取得"""
        checked_files = []
        # self.checked_state と self.thumbnail_widgets を使ってパスを取得
        for filename, is_checked in self.checked_state.items():
            if is_checked and filename in self.thumbnail_widgets:
                 checked_files.append(self.thumbnail_widgets[filename]['path'])
        return checked_files

    def _copy_checked(self):
        """チェックされたファイルを指定フォルダにコピー"""
        checked_files = self._get_checked_files()
        if not checked_files:
            messagebox.showinfo("情報", "コピーするファイルが選択されていません。")
            return

        dest_folder = filedialog.askdirectory(title="コピー先のフォルダを選択")
        if not dest_folder:
            return # キャンセルされた

        overwrite_all = None # None: 未定, True: 全て上書き, False: 全てスキップ
        cancel_operation = False

        for src_path in checked_files:
            if cancel_operation:
                break

            filename = os.path.basename(src_path)
            dest_path = os.path.join(dest_folder, filename)

            if os.path.exists(dest_path):
                if overwrite_all is None:
                    # 多数のファイルがある場合に備え、「全て上書き」「全てスキップ」を追加
                    response = messagebox.askyesnocancel("確認", f"{filename} は既に存在します。\n上書きしますか？\n\n(「はい」でこのファイルを上書き、「いいえ」でスキップ、「キャンセル」で処理を中止)\n\n次回以降の同名ファイルについて:\n「はい」-> 全て上書き\n「いいえ」-> 全てスキップ", detail="操作を選択してください")

                    if response is None: # キャンセル
                        cancel_operation = True
                        break
                    elif response: # はい (上書き)
                         overwrite_all = True # 次回以降も上書き
                    else: # いいえ (スキップ)
                         overwrite_all = False # 次回以降もスキップ
                         continue # このファイルはスキップ

                elif overwrite_all: # 全て上書きが選択されている
                    pass # 何もせず上書き処理へ
                else: # 全てスキップが選択されている
                    continue # 次のファイルへ

            try:
                self.status_bar.config(text=f"コピー中: {filename} -> {dest_folder}")
                self.update_idletasks() # ステータスバーを更新
                shutil.copy2(src_path, dest_path) # メタデータもコピー
            except Exception as e:
                error_response = messagebox.askretrycancel("コピーエラー", f"{filename} のコピー中にエラーが発生しました:\n{e}\n\n再試行しますか？ (キャンセルで処理中止)")
                if not error_response: # キャンセルが選択された場合
                    cancel_operation = True
                    break
                # 再試行の場合はループの次のイテレーションで再度試行される (ただし、根本原因が解決しないと無限ループの可能性)
                # より丁寧なエラー処理が必要な場合がある

        if cancel_operation:
             self.status_bar.config(text="コピー処理がキャンセルまたはエラーで中断されました。")
        else:
             self.status_bar.config(text="選択されたファイルのコピーが完了しました。")


    def _move_checked(self):
        """チェックされたファイルを指定フォルダに移動"""
        checked_files = self._get_checked_files()
        if not checked_files:
            messagebox.showinfo("情報", "移動するファイルが選択されていません。")
            return

        if not messagebox.askyesno("確認", f"{len(checked_files)}個のファイルを移動しますか？\n移動元のファイルは削除されます。"):
             return

        dest_folder = filedialog.askdirectory(title="移動先のフォルダを選択")
        if not dest_folder:
            return # キャンセルされた

        # 移動元と同じフォルダは指定できないようにする
        src_folder = self.current_folder.get()
        if src_folder and os.path.abspath(src_folder) == os.path.abspath(dest_folder):
            messagebox.showerror("エラー", "移動元と移動先のフォルダが同じです。")
            return

        overwrite_all = None
        cancel_operation = False

        moved_files_info = [] # 移動したファイルの情報を保持 (移動後にサムネイルから削除するため) { 'path': path, 'filename': filename }

        for src_path in checked_files:
            if cancel_operation:
                break

            filename = os.path.basename(src_path)
            dest_path = os.path.join(dest_folder, filename)

            if os.path.exists(dest_path):
                if overwrite_all is None:
                    response = messagebox.askyesnocancel("確認", f"{filename} は既に存在します。\n上書きしますか？\n\n(「はい」でこのファイルを上書き、「いいえ」でスキップ、「キャンセル」で処理を中止)\n\n次回以降の同名ファイルについて:\n「はい」-> 全て上書き\n「いいえ」-> 全てスキップ", detail="操作を選択してください")
                    if response is None:
                        cancel_operation = True
                        break
                    elif response:
                        overwrite_all = True
                    else:
                        overwrite_all = False
                        continue
                elif overwrite_all:
                    pass
                else:
                    continue

            try:
                self.status_bar.config(text=f"移動中: {filename} -> {dest_folder}")
                self.update_idletasks()
                shutil.move(src_path, dest_path)
                moved_files_info.append({'path': src_path, 'filename': filename}) # 移動成功したファイル情報(パスとファイル名)を記録
            except Exception as e:
                error_response = messagebox.askretrycancel("移動エラー", f"{filename} の移動中にエラーが発生しました:\n{e}\n\n再試行しますか？ (キャンセルで処理中止)")
                if not error_response:
                    cancel_operation = True
                    break

        # 移動が完了したら、サムネイル表示と内部リストから移動したファイルを削除
        if moved_files_info:
            moved_paths = {info['path'] for info in moved_files_info}
            moved_filenames = {info['filename'] for info in moved_files_info}

            # 内部リストから削除
            self.image_files = [(p, f) for p, f in self.image_files if p not in moved_paths]
            # チェック状態から削除
            self.checked_state = {fname: state for fname, state in self.checked_state.items() if fname not in moved_filenames}
            # サムネイルウィジェットから削除 (filename をキーに)
            for moved_fname in moved_filenames:
                 if moved_fname in self.thumbnail_widgets:
                     self.thumbnail_widgets[moved_fname]['frame'].destroy()
                     del self.thumbnail_widgets[moved_fname]
                 # thumbnail_image_objects のキーは path なので注意
                 # moved_path を取得する必要がある -> moved_files_info を使う
                 moved_path = next((info['path'] for info in moved_files_info if info['filename'] == moved_fname), None)
                 if moved_path and moved_path in self.thumbnail_image_objects:
                     del self.thumbnail_image_objects[moved_path] # 画像参照も削除

            # サムネイル表示を再配置（削除後の隙間を詰める）
            self._update_thumbnails_display() # 再描画
            self._save_checked_state() # チェック状態の変更を保存

        if cancel_operation:
             self.status_bar.config(text="移動処理がキャンセルまたはエラーで中断されました。")
        else:
             self.status_bar.config(text="選択されたファイルの移動が完了しました。")


    def _open_process_dialog(self):
        """リネーム、変換、リサイズ、塗りつぶしを行うダイアログを開く"""
        checked_files = self._get_checked_files()
        if not checked_files:
            messagebox.showinfo("情報", "処理するファイルが選択されていません。")
            return

        dialog = ProcessDialog(self, checked_files)
        # モーダルダイアログなので、ここで待機する
        self.wait_window(dialog)

        # ダイアログが閉じた後、必要に応じてメインウィンドウを更新
        # ProcessDialog内で更新するかどうか尋ねるように変更済み
        # self._load_images()
        # self._load_checked_state()
        # self._update_thumbnails_display()


# --- 処理ダイアログクラス ---
class ProcessDialog(tk.Toplevel):
    def __init__(self, parent, file_paths):
        super().__init__(parent)
        self.transient(parent) # 親ウィンドウの上に表示
        self.grab_set() # モーダルにする
        self.title("画像処理オプション")
        self.parent = parent
        self.file_paths = file_paths
        self.geometry("600x650") # ダイアログサイズ調整

        # --- 変数 ---
        self.output_folder_var = tk.StringVar()
        # 初期出力フォルダを現在のフォルダにするか、最後に使ったフォルダを記憶するなどの改善も可能
        if parent.current_folder.get():
            self.output_folder_var.set(parent.current_folder.get())

        self.rename_var = tk.BooleanVar()
        self.rename_prefix_var = tk.StringVar(value="image_")
        self.rename_start_var = tk.IntVar(value=1)
        self.rename_digits_var = tk.IntVar(value=3)
        self.convert_var = tk.BooleanVar()
        self.convert_format_var = tk.StringVar(value="jpg")
        self.resize_var = tk.BooleanVar()
        self.resize_mode_var = tk.StringVar(value="scale") # scale, fixed, crop
        self.resize_width_var = tk.IntVar(value=800)
        self.resize_height_var = tk.IntVar(value=600)
        self.resize_aspect_var = tk.DoubleVar(value=16/9)
        self.fill_var = tk.BooleanVar()
        self.fill_x1_var = tk.IntVar(value=0)
        self.fill_y1_var = tk.IntVar(value=0)
        self.fill_x2_var = tk.IntVar(value=100)
        self.fill_y2_var = tk.IntVar(value=100)
        self.fill_color_var = tk.StringVar(value="#ff0000") # 赤色

        # --- UI ---
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 出力フォルダ
        folder_frame = ttk.LabelFrame(main_frame, text="出力先フォルダ", padding=5)
        folder_frame.pack(fill=tk.X, pady=5)
        ttk.Entry(folder_frame, textvariable=self.output_folder_var, width=60).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(folder_frame, text="参照...", command=self._select_output_folder).pack(side=tk.LEFT)

        # リネーム
        rename_frame = ttk.LabelFrame(main_frame, text="連番リネーム", padding=5)
        rename_frame.pack(fill=tk.X, pady=5)
        ttk.Checkbutton(rename_frame, text="有効にする", variable=self.rename_var).grid(row=0, column=0, columnspan=6, sticky=tk.W) # columnspan 調整
        ttk.Label(rename_frame, text="プレフィックス:").grid(row=1, column=0, sticky=tk.W, padx=5)
        ttk.Entry(rename_frame, textvariable=self.rename_prefix_var).grid(row=1, column=1, sticky=tk.EW, padx=5)
        ttk.Label(rename_frame, text="開始番号:").grid(row=1, column=2, sticky=tk.W, padx=5)
        ttk.Entry(rename_frame, textvariable=self.rename_start_var, width=5).grid(row=1, column=3, sticky=tk.W, padx=5)
        ttk.Label(rename_frame, text="桁数:").grid(row=1, column=4, sticky=tk.W, padx=5)
        ttk.Entry(rename_frame, textvariable=self.rename_digits_var, width=5).grid(row=1, column=5, sticky=tk.W, padx=5)
        rename_frame.columnconfigure(1, weight=1)

        # 形式変換
        convert_frame = ttk.LabelFrame(main_frame, text="ファイル形式変換", padding=5)
        convert_frame.pack(fill=tk.X, pady=5)
        ttk.Checkbutton(convert_frame, text="有効にする", variable=self.convert_var).grid(row=0, column=0, sticky=tk.W)
        ttk.Label(convert_frame, text="形式:").grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Combobox(convert_frame, textvariable=self.convert_format_var, values=["jpg", "png", "bmp"], state="readonly").grid(row=0, column=2, sticky=tk.W, padx=5)

        # リサイズ
        resize_frame = ttk.LabelFrame(main_frame, text="リサイズ", padding=5)
        resize_frame.pack(fill=tk.X, pady=5)
        ttk.Checkbutton(resize_frame, text="有効にする", variable=self.resize_var, command=self._toggle_resize_options).grid(row=0, column=0, columnspan=4, sticky=tk.W)

        self.resize_options_frame = ttk.Frame(resize_frame)
        self.resize_options_frame.grid(row=1, column=0, columnspan=4, sticky=tk.EW, pady=(5,0))

        ttk.Radiobutton(self.resize_options_frame, text="拡大縮小(比率維持)", variable=self.resize_mode_var, value="scale", command=self._toggle_resize_inputs).pack(anchor=tk.W)
        self.scale_frame = ttk.Frame(self.resize_options_frame)
        self.scale_frame.pack(fill=tk.X, padx=20)
        ttk.Label(self.scale_frame, text="最大幅:").pack(side=tk.LEFT)
        ttk.Entry(self.scale_frame, textvariable=self.resize_width_var, width=7).pack(side=tk.LEFT, padx=5)
        ttk.Label(self.scale_frame, text="最大高:").pack(side=tk.LEFT)
        ttk.Entry(self.scale_frame, textvariable=self.resize_height_var, width=7).pack(side=tk.LEFT, padx=5)

        ttk.Radiobutton(self.resize_options_frame, text="固定サイズ(変形)", variable=self.resize_mode_var, value="fixed", command=self._toggle_resize_inputs).pack(anchor=tk.W)
        self.fixed_frame = ttk.Frame(self.resize_options_frame)
        self.fixed_frame.pack(fill=tk.X, padx=20)
        ttk.Label(self.fixed_frame, text="幅:").pack(side=tk.LEFT)
        ttk.Entry(self.fixed_frame, textvariable=self.resize_width_var, width=7).pack(side=tk.LEFT, padx=5)
        ttk.Label(self.fixed_frame, text="高:").pack(side=tk.LEFT)
        ttk.Entry(self.fixed_frame, textvariable=self.resize_height_var, width=7).pack(side=tk.LEFT, padx=5)

        ttk.Radiobutton(self.resize_options_frame, text="アスペクト比に合わせてトリミング", variable=self.resize_mode_var, value="crop", command=self._toggle_resize_inputs).pack(anchor=tk.W)
        self.crop_frame = ttk.Frame(self.resize_options_frame)
        self.crop_frame.pack(fill=tk.X, padx=20)
        ttk.Label(self.crop_frame, text="目標幅:").pack(side=tk.LEFT)
        ttk.Entry(self.crop_frame, textvariable=self.resize_width_var, width=7).pack(side=tk.LEFT, padx=5)
        ttk.Label(self.crop_frame, text="目標高:").pack(side=tk.LEFT)
        ttk.Entry(self.crop_frame, textvariable=self.resize_height_var, width=7).pack(side=tk.LEFT, padx=5)
        #ttk.Label(self.crop_frame, text="目標比率:").pack(side=tk.LEFT) # 比率指定も可能にする場合
        #ttk.Entry(self.crop_frame, textvariable=self.resize_aspect_var, width=7).pack(side=tk.LEFT, padx=5)

        self._toggle_resize_options() # 初期状態を設定
        self._toggle_resize_inputs() # 初期状態を設定


        # 領域塗りつぶし
        fill_frame = ttk.LabelFrame(main_frame, text="特定領域の塗りつぶし", padding=5)
        fill_frame.pack(fill=tk.X, pady=5)
        ttk.Checkbutton(fill_frame, text="有効にする", variable=self.fill_var).grid(row=0, column=0, columnspan=5, sticky=tk.W) # columnspan 調整
        ttk.Label(fill_frame, text="左上 X:").grid(row=1, column=0, sticky=tk.W, padx=5)
        ttk.Entry(fill_frame, textvariable=self.fill_x1_var, width=5).grid(row=1, column=1, sticky=tk.W, padx=5)
        ttk.Label(fill_frame, text="Y:").grid(row=1, column=2, sticky=tk.W, padx=5)
        ttk.Entry(fill_frame, textvariable=self.fill_y1_var, width=5).grid(row=1, column=3, sticky=tk.W, padx=5)
        ttk.Label(fill_frame, text="右下 X:").grid(row=2, column=0, sticky=tk.W, padx=5)
        ttk.Entry(fill_frame, textvariable=self.fill_x2_var, width=5).grid(row=2, column=1, sticky=tk.W, padx=5)
        ttk.Label(fill_frame, text="Y:").grid(row=2, column=2, sticky=tk.W, padx=5)
        ttk.Entry(fill_frame, textvariable=self.fill_y2_var, width=5).grid(row=2, column=3, sticky=tk.W, padx=5)
        ttk.Label(fill_frame, text="色:").grid(row=3, column=0, sticky=tk.W, padx=5)
        self.fill_color_entry = ttk.Entry(fill_frame, textvariable=self.fill_color_var, width=10)
        self.fill_color_entry.grid(row=3, column=1, columnspan=2, sticky=tk.EW, padx=5)
        self.fill_color_button = ttk.Button(fill_frame, text="色選択...", command=self._select_fill_color)
        self.fill_color_button.grid(row=3, column=3, sticky=tk.W, padx=5)
        # 色選択ボタンの隣に色のプレビューを表示
        self.color_preview = tk.Label(fill_frame, width=2, relief=tk.SUNKEN)
        self.color_preview.grid(row=3, column=4, sticky=tk.W, padx=5)
        self._update_color_preview() # 初期色を設定
        self.fill_color_var.trace_add("write", self._update_color_preview) # 色が変わったらプレビュー更新

        # プログレスバー
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=len(self.file_paths))
        self.progress_bar.pack(fill=tk.X, pady=(10, 0))


        # 実行ボタン
        button_frame = ttk.Frame(main_frame, padding=5)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=10)
        self.run_button = ttk.Button(button_frame, text="実行", command=self._execute_processing)
        self.run_button.pack(side=tk.RIGHT, padx=5)
        self.cancel_button = ttk.Button(button_frame, text="キャンセル", command=self.destroy)
        self.cancel_button.pack(side=tk.RIGHT)


    def _select_output_folder(self):
        """出力先フォルダ選択ダイアログ"""
        folder = filedialog.askdirectory(title="出力先フォルダを選択", parent=self)
        if folder:
            self.output_folder_var.set(folder)

    def _toggle_resize_options(self):
        """リサイズオプションの有効/無効を切り替え"""
        state = tk.NORMAL if self.resize_var.get() else tk.DISABLED
        # ラジオボタンとそれに関連するフレームの状態を一括で設定
        widgets_to_toggle = [
            self.resize_options_frame.winfo_children() # ラジオボタンとフレームを取得
        ]
        # フレーム内のウィジェットも対象にする
        widgets_to_toggle.extend(self.scale_frame.winfo_children())
        widgets_to_toggle.extend(self.fixed_frame.winfo_children())
        widgets_to_toggle.extend(self.crop_frame.winfo_children())

        flat_list = []
        for item in widgets_to_toggle:
             if isinstance(item, list):
                 flat_list.extend(item)
             else:
                 flat_list.append(item)


        for widget in flat_list:
            try:
                # 特定のウィジェットタイプをチェックして状態を設定
                if isinstance(widget, (ttk.Radiobutton, ttk.Label, ttk.Entry, ttk.Frame)):
                    widget.configure(state=state)
                # Frameの場合は中のウィジェットも再帰的に設定する必要があるが、
                # _toggle_resize_inputsで個別に行うのでここでは不要
            except tk.TclError:
                pass # stateオプションがないウィジェットはスキップ

        # リサイズが無効になったら、入力フィールドの状態も更新
        if not self.resize_var.get():
             self._toggle_resize_inputs()


    def _set_widget_state_recursive(self, widget, state):
        """ウィジェットとその子ウィジェットの状態を再帰的に設定"""
        # この関数は _toggle_resize_options の中で使われなくなったため、
        # 必要であれば保持、不要なら削除してもよい。
        # _toggle_resize_options の実装がより直接的になった。
        try:
            widget.configure(state=state)
        except tk.TclError:
            pass # stateオプションがないウィジェットはスキップ

        # 子ウィジェットに対しても再帰的に適用
        for child in widget.winfo_children():
            self._set_widget_state_recursive(child, state)


    def _toggle_resize_inputs(self):
        """リサイズモードに応じて入力フィールドの有効/無効を切り替え"""
        # まずリサイズ自体が有効かチェック
        base_state = tk.NORMAL if self.resize_var.get() else tk.DISABLED

        mode = self.resize_mode_var.get()
        scale_state = tk.NORMAL if base_state == tk.NORMAL and mode == "scale" else tk.DISABLED
        fixed_state = tk.NORMAL if base_state == tk.NORMAL and mode == "fixed" else tk.DISABLED
        crop_state = tk.NORMAL if base_state == tk.NORMAL and mode == "crop" else tk.DISABLED

        for child in self.scale_frame.winfo_children():
            if hasattr(child, 'configure'):
                try:
                    child.configure(state=scale_state)
                except tk.TclError: pass
        for child in self.fixed_frame.winfo_children():
             if hasattr(child, 'configure'):
                 try:
                     child.configure(state=fixed_state)
                 except tk.TclError: pass
        for child in self.crop_frame.winfo_children():
             if hasattr(child, 'configure'):
                 try:
                     child.configure(state=crop_state)
                 except tk.TclError: pass


    def _select_fill_color(self):
        """色選択ダイアログを開き、選択された色を変数に設定"""
        # 現在の色を初期色として渡す
        initial_color = self.fill_color_var.get()
        color_code = colorchooser.askcolor(initialcolor=initial_color, title="塗りつぶし色を選択", parent=self)
        if color_code and color_code[1]: # 色が選択され、キャンセルされなかった場合
            self.fill_color_var.set(color_code[1]) # 16進数カラーコードを設定

    def _update_color_preview(self, *args):
        """色プレビューラベルの背景色を更新"""
        color = self.fill_color_var.get()
        try:
            self.color_preview.config(bg=color)
        except tk.TclError:
            # 無効な色コードの場合はデフォルト色などにする
            self.color_preview.config(bg="white")


    def _execute_processing(self):
        """設定された処理を実行"""
        output_folder = self.output_folder_var.get()
        if not output_folder:
             messagebox.showerror("エラー", "出力先フォルダが指定されていません。", parent=self)
             return
        # 出力先フォルダが存在しない場合は作成するか確認
        if not os.path.isdir(output_folder):
            if messagebox.askyesno("確認", f"出力先フォルダが存在しません:\n{output_folder}\n作成しますか？", parent=self):
                try:
                    os.makedirs(output_folder)
                except OSError as e:
                    messagebox.showerror("エラー", f"出力先フォルダの作成に失敗しました:\n{e}", parent=self)
                    return
            else:
                return # 作成しない場合は中止


        do_rename = self.rename_var.get()
        do_convert = self.convert_var.get()
        do_resize = self.resize_var.get()
        do_fill = self.fill_var.get()

        if not (do_rename or do_convert or do_resize or do_fill):
            messagebox.showinfo("情報", "実行する処理が選択されていません。", parent=self)
            return

        # パラメータ取得とバリデーション
        try:
            prefix = self.rename_prefix_var.get() if do_rename else ""
            start_num = self.rename_start_var.get() if do_rename else 1
            digits = self.rename_digits_var.get() if do_rename else 3
            convert_format = self.convert_format_var.get() if do_convert else None
            resize_mode = self.resize_mode_var.get() if do_resize else None
            resize_w = self.resize_width_var.get() if do_resize else 0
            resize_h = self.resize_height_var.get() if do_resize else 0
            # resize_aspect = self.resize_aspect_var.get() if do_resize and resize_mode == 'crop' else 1.0
            fill_x1 = self.fill_x1_var.get() if do_fill else 0
            fill_y1 = self.fill_y1_var.get() if do_fill else 0
            fill_x2 = self.fill_x2_var.get() if do_fill else 0
            fill_y2 = self.fill_y2_var.get() if do_fill else 0
            fill_color = self.fill_color_var.get() if do_fill else None
            fill_color_rgb = None # 初期化
            if do_fill:
                 # 色コードをPillowが扱える形式(RGBタプル)に変換
                 if fill_color.startswith('#') and len(fill_color) == 7:
                     fill_color_rgb = tuple(int(fill_color[i:i+2], 16) for i in (1, 3, 5))
                 else:
                     # Pillowは一部の色名を認識できるが、ここでは#RRGGBBのみをサポート
                     # tkinterのcolorchooserはRGBタプルも返すが、ここでは16進数を想定
                     try:
                         # 16進数でない場合、色名として認識できるか試す (より堅牢にする場合)
                         # from PIL import ImageColor
                         # fill_color_rgb = ImageColor.getrgb(fill_color)
                         # 簡単のためエラーとする
                         raise ValueError("無効な色指定です。#RRGGBB形式で指定してください。")
                     except ValueError:
                          raise ValueError("無効な色指定です。#RRGGBB形式で指定してください。")


            if do_resize and (resize_w <= 0 or resize_h <= 0):
                raise ValueError("リサイズの幅と高さは正の値である必要があります。")
            if do_fill and (fill_x1 >= fill_x2 or fill_y1 >= fill_y2):
                raise ValueError("塗りつぶし領域の座標が無効です (左上 < 右下)。")

        except ValueError as e:
            messagebox.showerror("入力エラー", f"パラメータが無効です: {e}", parent=self)
            return
        except tk.TclError:
             messagebox.showerror("入力エラー", "数値パラメータには有効な数値を入力してください。", parent=self)
             return


        # --- 処理実行 ---
        num_processed = 0
        num_errors = 0
        current_num = start_num

        # 処理中はボタンを無効化
        self.run_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.DISABLED) # キャンセル機能は未実装のため無効化のまま

        self.progress_var.set(0) # プログレスバーをリセット

        # update()を呼ぶと後続の処理が実行されないことがあるため、afterを使う
        self.after(10, self._process_batch, output_folder, do_rename, prefix, start_num, digits,
                   do_convert, convert_format, do_resize, resize_mode, resize_w, resize_h,
                   do_fill, fill_x1, fill_y1, fill_x2, fill_y2, fill_color_rgb,
                   0, num_processed, num_errors, current_num) # インデックス0から開始


    def _process_batch(self, output_folder, do_rename, prefix, start_num, digits,
                       do_convert, convert_format, do_resize, resize_mode, resize_w, resize_h,
                       do_fill, fill_x1, fill_y1, fill_x2, fill_y2, fill_color_rgb,
                       index, num_processed, num_errors, current_num):
        """ファイル処理を1つずつ実行し、UIを更新する"""

        if index >= len(self.file_paths):
            # --- 全ての処理完了 ---
            self.parent.status_bar.config(text="処理完了")
            messagebox.showinfo("処理完了",
                                f"処理が完了しました。\n"
                                f"成功: {num_processed} ファイル\n"
                                f"エラー: {num_errors} ファイル\n"
                                f"出力先: {output_folder}",
                                parent=self)

            # 実行ボタンなどを再度有効化
            self.run_button.config(state=tk.NORMAL)
            self.cancel_button.config(state=tk.NORMAL)

            # ダイアログを閉じる前に、メインウィンドウのサムネイルを更新するかどうか尋ねる
            if messagebox.askyesno("確認", "メインウィンドウの表示を更新しますか？\n(処理結果を反映します)", parent=self):
                # 出力先が現在のフォルダと同じかサブフォルダの場合のみ更新を提案するのが親切かも
                current_view_folder = self.parent.current_folder.get()
                should_refresh = False
                if current_view_folder:
                    abs_output = os.path.abspath(output_folder)
                    abs_current = os.path.abspath(current_view_folder)
                    # 出力先が現在のフォルダ、またはその親フォルダの場合にリフレッシュを促す
                    if abs_output == abs_current or abs_current.startswith(abs_output + os.sep):
                         should_refresh = True
                    # 出力先が現在のフォルダのサブフォルダの場合もリフレッシュが必要な場合がある
                    elif abs_output.startswith(abs_current + os.sep):
                         should_refresh = True # Treeviewの更新が必要になる

                if should_refresh:
                    self.parent._load_images() # 現在のフォルダを再読み込み
                    self.parent._load_checked_state() # チェック状態も再読み込み
                    self.parent._update_thumbnails_display()
                    # 必要であればツリービューも更新 (フォルダ構成が変わった場合)
                    # self.parent._populate_tree(self.parent.root_folder_path) # ルートから再構築
                else:
                     print("表示中のフォルダ外への出力のため、自動更新はスキップされました。")


            self.destroy() # ダイアログを閉じる
            return


        # --- 1ファイルの処理 ---
        src_path = self.file_paths[index]
        self.parent.status_bar.config(text=f"処理中: {index + 1} / {len(self.file_paths)} - {os.path.basename(src_path)}")
        # self.update_idletasks() # afterを使っているので不要かも

        error_occurred = False
        try:
            img = Image.open(src_path)
            original_format = img.format # 元のフォーマットを保持 (PillowがNoneを返す場合もある)

            # モード変換: 透過を扱う可能性のある処理(PNG変換、塗りつぶし)があればRGBA、なければRGB
            needs_alpha = (do_convert and convert_format == 'png') or do_fill
            target_mode = "RGBA" if needs_alpha else "RGB"

            # JPEGなどアルファチャンネルを持てない形式で、かつアルファが必要な処理がない場合
            if img.mode == 'RGBA' and not needs_alpha and convert_format != 'png':
                 # 背景を白色で合成してRGBにする
                 bg = Image.new('RGB', img.size, (255, 255, 255))
                 bg.paste(img, mask=img.split()[3]) # alphaチャンネルをマスクとして使用
                 img = bg
            elif img.mode != target_mode:
                 # 必要なモードに変換 (Pモードなども考慮)
                 try:
                     img = img.convert(target_mode)
                 except ValueError: # 変換できない場合 (例: モノクロ画像をRGBAに)
                      # 一旦RGBに変換してからRGBAに試みるなど、より丁寧な処理が可能
                      img = img.convert("RGB").convert(target_mode)


            # 1. リサイズ (リサイズする場合、他の処理より先に行うことが多い)
            if do_resize:
                img_w, img_h = img.size
                if resize_mode == "scale":
                    img.thumbnail((resize_w, resize_h), Image.Resampling.LANCZOS)
                elif resize_mode == "fixed":
                    img = img.resize((resize_w, resize_h), Image.Resampling.LANCZOS)
                elif resize_mode == "crop":
                    target_aspect = resize_w / resize_h
                    img_aspect = img_w / img_h

                    if img_aspect > target_aspect: # 画像が横長すぎる -> 幅をトリミング
                        new_width = int(target_aspect * img_h)
                        offset = (img_w - new_width) // 2
                        img = img.crop((offset, 0, offset + new_width, img_h))
                    else: # 画像が縦長すぎる -> 高さをトリミング
                        new_height = int(img_w / target_aspect)
                        offset = (img_h - new_height) // 2
                        img = img.crop((0, offset, img_w, offset + new_height))
                    # 目標サイズにリサイズ
                    img = img.resize((resize_w, resize_h), Image.Resampling.LANCZOS)

            # 2. 領域塗りつぶし
            if do_fill:
                # RGBAモードでないと透過色での塗りができない場合があるため、モードを確認
                if img.mode != 'RGBA':
                    img = img.convert('RGBA') # 必要ならRGBAに変換
                draw = ImageDraw.Draw(img)
                # 座標が画像の範囲内にあることを確認 (クリッピング)
                x1 = max(0, fill_x1)
                y1 = max(0, fill_y1)
                x2 = min(img.width, fill_x2)
                y2 = min(img.height, fill_y2)
                if x1 < x2 and y1 < y2: # 有効な領域がある場合のみ描画
                    # fill_color_rgb にアルファ値を追加する必要があるか？
                    # ImageDraw.rectangle は fill タプルにアルファ値を含められる
                    # 簡単のため、ここでは不透明色のみを想定
                    draw.rectangle([x1, y1, x2, y2], fill=fill_color_rgb) # fill_color_rgbはRGBタプル


            # 3. 出力ファイル名と形式の決定
            base_filename = os.path.splitext(os.path.basename(src_path))[0]
            if do_rename:
                num_str = str(current_num).zfill(digits)
                output_filename_base = f"{prefix}{num_str}"
                # current_num は次の呼び出しのためにインクリメントしておく
            else:
                output_filename_base = base_filename

            if do_convert:
                output_extension = f".{convert_format.lower()}"
            else:
                # 元の拡張子を使うか、Pillowが判定した形式を使う
                ext = os.path.splitext(src_path)[1]
                if ext:
                    output_extension = ext.lower()
                elif original_format:
                    output_extension = f".{original_format.lower()}"
                else:
                    output_extension = ".jpg" # デフォルト

            output_filename = f"{output_filename_base}{output_extension}"
            output_path = os.path.join(output_folder, output_filename)

            # 4. 保存
            save_options = {}
            fmt = output_extension.lstrip('.').upper()
            save_format = fmt # Pillowに渡すフォーマット名
            if fmt == 'JPG':
                 save_format = 'JPEG'
                 save_options['quality'] = 95 # 高品質
                 # JPEGは透過をサポートしないため、RGBモードに変換
                 if img.mode == 'RGBA':
                      # 透過部分を白色背景で合成
                      bg = Image.new('RGB', img.size, (255, 255, 255))
                      bg.paste(img, mask=img.split()[3])
                      img = bg
                 elif img.mode != 'RGB':
                     img = img.convert('RGB')

            elif fmt == 'PNG':
                 save_options['optimize'] = True
                 # PNGは透過をサポートするのでRGBAのままでOK
                 if img.mode != 'RGBA':
                      # 透過情報がない場合でも、互換性のためRGBAに変換しておく方が安全な場合も
                      # img = img.convert('RGBA')
                      pass # RGBのままでも保存は可能

            elif fmt == 'BMP':
                 # BMPは通常RGBだが、透過BMP(RGBA)もある。Pillowの挙動に依存。
                 # 安全のためRGBに変換しておく
                 if img.mode != 'RGB':
                      img = img.convert('RGB')


            # 上書き確認 (ここでも行う場合) - シンプルにするため省略
            # 同名ファイルが存在する場合の処理はダイアログで一括指定する方がUIが良いかも

            img.save(output_path, format=save_format, **save_options)
            num_processed += 1
            if do_rename:
                current_num += 1 # 成功した場合のみ番号を進める

        except Exception as e:
            num_errors += 1
            error_occurred = True
            print(f"Error processing {src_path}: {e}") # コンソールにエラー出力
            # エラーが発生したファイルはスキップして次に進む

        # プログレスバー更新
        self.progress_var.set(index + 1)
        # self.update_idletasks() # afterを使っているので不要かも

        # 次のファイルを処理するために再帰的に呼び出す
        self.after(10, self._process_batch, output_folder, do_rename, prefix, start_num, digits,
                   do_convert, convert_format, do_resize, resize_mode, resize_w, resize_h,
                   do_fill, fill_x1, fill_y1, fill_x2, fill_y2, fill_color_rgb,
                   index + 1, num_processed, num_errors, current_num)


# --- アプリケーションの実行 ---
if __name__ == "__main__":
    app = ImageCheckerApp()
    app.mainloop()
