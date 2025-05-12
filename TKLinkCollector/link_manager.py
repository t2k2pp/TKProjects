import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, simpledialog, filedialog
import csv
import os
import re
import requests
from bs4 import BeautifulSoup
import threading
import urllib.parse
import json
import html
from datetime import datetime
import chardet
import traceback
import sys

class EditDialog(tk.Toplevel):
    """リンク情報を編集するためのダイアログ"""
    def __init__(self, parent, url="", title="", status=""):
        super().__init__(parent)
        self.title("リンク情報の編集")
        self.geometry("500x200")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self.url = url
        self.title = title
        self.status = status
        self.result = None
        
        self.create_widgets()
        
    def create_widgets(self):
        # URL入力
        url_frame = tk.Frame(self)
        url_frame.pack(fill=tk.X, padx=10, pady=5)
        url_label = tk.Label(url_frame, text="URL:", width=10, anchor="w")
        url_label.pack(side=tk.LEFT)
        self.url_entry = tk.Entry(url_frame, width=50)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.url_entry.insert(0, self.url)
        
        # タイトル入力
        title_frame = tk.Frame(self)
        title_frame.pack(fill=tk.X, padx=10, pady=5)
        title_label = tk.Label(title_frame, text="タイトル:", width=10, anchor="w")
        title_label.pack(side=tk.LEFT)
        self.title_entry = tk.Entry(title_frame, width=50)
        self.title_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.title_entry.insert(0, self.title)
        
        # ステータス選択
        status_frame = tk.Frame(self)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        status_label = tk.Label(status_frame, text="ステータス:", width=10, anchor="w")
        status_label.pack(side=tk.LEFT)
        self.status_var = tk.StringVar(value=self.status)
        status_options = ["", "取得成功", "取得失敗"]
        self.status_combo = ttk.Combobox(status_frame, textvariable=self.status_var, values=status_options, width=15)
        self.status_combo.pack(side=tk.LEFT)
        
        # ボタン
        button_frame = tk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        save_button = tk.Button(button_frame, text="保存", command=self.save)
        save_button.pack(side=tk.RIGHT, padx=5)
        cancel_button = tk.Button(button_frame, text="キャンセル", command=self.cancel)
        cancel_button.pack(side=tk.RIGHT, padx=5)
        
    def save(self):
        self.result = {
            "url": self.url_entry.get().strip(),
            "title": self.title_entry.get().strip(),
            "status": self.status_var.get()
        }
        self.destroy()
        
    def cancel(self):
        self.result = None
        self.destroy()

class RichTextBox(tk.Frame):
    """リッチテキスト対応のテキストボックス"""
    def __init__(self, parent, **kwargs):
        super().__init__(parent)
        
        # テキストウィジェットとスクロールバーを作成
        self.text = tk.Text(self, wrap="word", **kwargs)
        scrollbar = tk.Scrollbar(self, command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)
        
        # パッキング
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # ハイパーリンクのタグを設定
        self.text.tag_configure("hyperlink", foreground="blue", underline=1)
        self.text.tag_bind("hyperlink", "<Button-1>", self._on_link_click)
        self.text.tag_bind("hyperlink", "<Enter>", lambda e: self.text.config(cursor="hand2"))
        self.text.tag_bind("hyperlink", "<Leave>", lambda e: self.text.config(cursor=""))
        
        # リンクとその範囲を追跡
        self.links = {}
        
        # クリップボードからのペースト処理をカスタマイズ
        self.text.bind("<<Paste>>", self._on_paste)
    
    def _on_paste(self, event):
        """ペースト時のイベントハンドラ"""
        try:
            # クリップボードからテキストを取得
            clipboard = self.text.clipboard_get()
            
            # デフォルトのペースト動作をキャンセル
            self.text.delete("sel.first", "sel.last")
            
            # HTMLコンテンツの検出
            if clipboard.strip().startswith("<") and "href=" in clipboard:
                # HTMLからハイパーリンクを抽出
                soup = BeautifulSoup(clipboard, 'html.parser')
                links = soup.find_all('a', href=True)
                
                if links:
                    # リンクテキストとURLを取得して挿入
                    for link in links:
                        url = link['href']
                        text = link.get_text().strip() or url
                        self.insert_hyperlink(text, url)
                else:
                    # HTMLだがリンクがない場合はテキストとして挿入
                    plain_text = soup.get_text()
                    self.text.insert(tk.INSERT, plain_text)
            else:
                # 通常のテキストとして挿入
                self.text.insert(tk.INSERT, clipboard)
            
            return "break"  # デフォルトの挙動をキャンセル
        except Exception as e:
            print(f"ペースト処理エラー: {e}")
            # エラーが発生した場合はデフォルトの挙動に任せる
            return None
    
    def insert_hyperlink(self, text, url):
        """ハイパーリンクをテキストボックスに挿入"""
        # 現在の挿入位置を取得
        pos = self.text.index(tk.INSERT)
        
        # テキストを挿入
        self.text.insert(pos, text)
        
        # リンク範囲のタグ付け
        start = pos
        end = self.text.index(f"{start}+{len(text)}c")
        self.text.tag_add("hyperlink", start, end)
        
        # リンクを記録
        self.links[f"{start}:{end}"] = url
    
    def _on_link_click(self, event):
        """ハイパーリンクがクリックされたときの処理"""
        # クリックされた位置を取得
        pos = self.text.index(f"@{event.x},{event.y}")
        
        # クリックされた位置のハイパーリンクを特定
        for link_range, url in self.links.items():
            start, end = link_range.split(":")
            if self.text.compare(start, "<=", pos) and self.text.compare(pos, "<=", end):
                print(f"リンクがクリックされました: {url}")
                # ここでブラウザで開くなどの処理を追加可能
                break
    
    def get_text(self):
        """テキストボックスの全テキストを取得"""
        return self.text.get("1.0", "end-1c")
    
    def clear(self):
        """テキストボックスをクリア"""
        self.text.delete("1.0", tk.END)
        self.links = {}

    def set_text(self, text):
        """テキストボックスに内容をセット"""
        self.clear()
        self.text.insert("1.0", text)
    
    def extract_urls(self):
        """テキストとハイパーリンクの両方からURLを抽出"""
        urls = []
        
        # 1. ハイパーリンクからURLを抽出
        for _, url in self.links.items():
            if url and url not in urls:
                urls.append(url)
        
        # 2. テキスト内のURLを正規表現で抽出
        text = self.get_text()
        url_pattern = r'https?://[^\s()<>"]+(?:\([^\s()<>"]*\)|[^\s`!()\[\]{};:\'\".,<>?«»""''])*'
        found_urls = re.findall(url_pattern, text)
        
        # 見つかったURLを追加（重複排除）
        for url in found_urls:
            if url not in urls:
                urls.append(url)
        
        return urls

class LinkManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("総合リンク管理アプリケーション")
        self.root.geometry("1200x700")
        
        # デバッグ情報をコンソールに出力する設定（問題のある部分を最初に初期化）
        self.debug = True
        
        # CSVファイル名
        self.csv_filename = "links.csv"
        
        # テキストファイルとして扱う拡張子のリスト
        self.text_extensions = [
            '.txt', '.csv', '.md', '.html', '.htm', '.xml', '.json', 
            '.py', '.js', '.css', '.java', '.c', '.cpp', '.h', '.hpp',
            '.bat', '.sh', '.ini', '.log', '.cfg', '.yml', '.yaml',
            '.rst', '.adoc', '.tex'
        ]
        
        # 試行するエンコーディングリスト
        self.encodings_to_try = [
            'utf-8', 'cp932', 'shift_jis', 'euc_jp', 'iso2022_jp',
            'latin1', 'cp1252', 'ascii'
        ]
        
        # CSVファイルが存在しない場合、作成する
        self.create_csv_if_not_exists()
        
        # メインフレームを作成
        self.create_main_layout()
        
        # 左側: フォルダブラウザの作成
        self.create_folder_browser()
        
        # 右側: リンク管理機能の作成
        self.create_link_manager()
        
        # 処理中フラグ
        self.processing = False
        
        # 現在開いているフォルダパス
        self.current_folder = ""
        
        # フォルダツリーのパス管理用データ
        self.tree_paths = {}  # アイテムIDとパスの対応を保存
        
        # 初期データのロード (self.debug 変数初期化後に移動)
        self.load_links_from_csv()

    def debug_print(self, message, error=None):
        """デバッグ情報をコンソールに出力"""
        try:
            if hasattr(self, 'debug') and self.debug:
                print(f"[DEBUG] {message}")
                if error:
                    print(f"[ERROR] {str(error)}")
                    traceback.print_exc(file=sys.stdout)
        except Exception as e:
            print(f"[DEBUG ERROR] {e}")

    def create_csv_if_not_exists(self):
        """CSVファイルが存在しない場合、新規作成する"""
        if not os.path.exists(self.csv_filename):
            with open(self.csv_filename, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(["URL", "タイトル", "ステータス"])
    
    def create_main_layout(self):
        """メインレイアウトの作成"""
        # 左右に分割するメインフレーム
        self.main_frame = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左側フレーム（フォルダブラウザ）
        self.left_frame = tk.Frame(self.main_frame)
        
        # 右側フレーム（リンク管理）
        self.right_frame = tk.Frame(self.main_frame)
        
        # PanedWindowに追加
        self.main_frame.add(self.left_frame, width=400)
        self.main_frame.add(self.right_frame, width=800)
        
        # ステータスバー
        self.status_var = tk.StringVar()
        self.status_var.set("準備完了")
        self.statusbar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # プログレスバー
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progressbar = ttk.Progressbar(self.root, variable=self.progress_var, maximum=100)
        self.progressbar.pack(side=tk.BOTTOM, fill=tk.X, before=self.statusbar)
        self.progressbar.pack_forget()  # 初期状態では非表示
    
    def create_folder_browser(self):
        """フォルダブラウザの作成"""
        # 1段目: フォルダ選択部分
        folder_frame = tk.Frame(self.left_frame)
        folder_frame.pack(fill=tk.X, pady=(0, 5))
        
        # フォルダパスを表示するテキストボックス
        self.folder_entry = tk.Entry(folder_frame)
        self.folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # フォルダ選択ボタン
        self.browse_button = tk.Button(folder_frame, text="選択", command=self.browse_folder)
        self.browse_button.pack(side=tk.RIGHT)
        
        # 2段目: ファイルツリー
        tree_frame = tk.Frame(self.left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # ファイルツリーのスクロールバー
        tree_scroll_y = tk.Scrollbar(tree_frame)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        tree_scroll_x = tk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # ファイルツリー
        self.file_tree = ttk.Treeview(tree_frame, 
                                     yscrollcommand=tree_scroll_y.set,
                                     xscrollcommand=tree_scroll_x.set)
        self.file_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # スクロールバーの設定
        tree_scroll_y.config(command=self.file_tree.yview)
        tree_scroll_x.config(command=self.file_tree.xview)
        
        # ツリーの設定
        self.file_tree["columns"] = ("size", "modified")
        self.file_tree.column("#0", width=250, minwidth=150)
        self.file_tree.column("size", width=70, anchor=tk.E)
        self.file_tree.column("modified", width=150)
        
        self.file_tree.heading("#0", text="ファイル名", anchor=tk.W)
        self.file_tree.heading("size", text="サイズ", anchor=tk.E)
        self.file_tree.heading("modified", text="更新日時")
        
        # ダブルクリックでファイルを開くまたはフォルダを展開/折りたたみ
        self.file_tree.bind("<Double-1>", self.on_tree_double_click)
        
        # 項目が展開されたときのイベント
        self.file_tree.bind("<<TreeviewOpen>>", self.on_tree_open)
        
        # 3段目: 開くボタン
        button_frame = tk.Frame(self.left_frame)
        button_frame.pack(fill=tk.X)
        
        self.open_button = tk.Button(button_frame, text="選択したファイルを開く", command=self.open_selected_file)
        self.open_button.pack(fill=tk.X)
    
    def create_link_manager(self):
        """リンク管理機能の作成"""
        # テキストエリアのラベル
        text_label = tk.Label(self.right_frame, text="リンクを含むテキスト:")
        text_label.pack(anchor='w')
        
        # リッチテキストエリア
        self.text_area = RichTextBox(self.right_frame, height=8)
        self.text_area.pack(fill=tk.X, pady=(0, 5))
        
        # テキストボックス操作ボタンを含むフレーム
        text_buttons_frame = tk.Frame(self.right_frame)
        text_buttons_frame.pack(fill=tk.X, pady=(0, 10))
        
        # テキストからリンクを抽出ボタン
        self.extract_button = tk.Button(text_buttons_frame, text="テキストからリンクを抽出", command=self.extract_links)
        self.extract_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # クリップボードからリンクを抽出ボタン
        self.clipboard_button = tk.Button(text_buttons_frame, text="クリップボードからリンクを抽出", command=self.extract_links_from_clipboard)
        self.clipboard_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # テキストクリアボタン
        self.clear_button = tk.Button(text_buttons_frame, text="テキストをクリア", command=self.clear_text)
        self.clear_button.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Treeviewのラベル
        tree_label = tk.Label(self.right_frame, text="リンク一覧:")
        tree_label.pack(anchor='w')
        
        # Treeviewとスクロールバー
        tree_frame = tk.Frame(self.right_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        tree_scroll_y = tk.Scrollbar(tree_frame)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        tree_scroll_x = tk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Treeviewの作成
        self.tree = ttk.Treeview(tree_frame, columns=("url", "title", "status"), 
                                 show="headings", 
                                 yscrollcommand=tree_scroll_y.set,
                                 xscrollcommand=tree_scroll_x.set)
        
        # スクロールバーの設定
        tree_scroll_y.config(command=self.tree.yview)
        tree_scroll_x.config(command=self.tree.xview)
        
        # 列の設定
        self.tree.heading("url", text="URL")
        self.tree.heading("title", text="タイトル")
        self.tree.heading("status", text="ステータス")
        
        self.tree.column("url", width=350, anchor="w")
        self.tree.column("title", width=350, anchor="w")
        self.tree.column("status", width=100, anchor="center")
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # 編集ボタン類を含むフレーム
        edit_frame = tk.Frame(self.right_frame)
        edit_frame.pack(fill=tk.X, pady=5)
        
        self.add_button = tk.Button(edit_frame, text="追加", command=self.add_link)
        self.add_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.edit_button = tk.Button(edit_frame, text="編集", command=self.edit_link)
        self.edit_button.pack(side=tk.LEFT, padx=5)
        
        self.delete_button = tk.Button(edit_frame, text="削除", command=self.delete_link)
        self.delete_button.pack(side=tk.LEFT, padx=5)
        
        # リンク先情報取得ボタン
        self.fetch_button = tk.Button(self.right_frame, text="リンク先情報取得", command=self.fetch_link_titles)
        self.fetch_button.pack(fill=tk.X, pady=5)
        
        # 右クリックメニュー
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="編集", command=self.edit_link)
        self.context_menu.add_command(label="削除", command=self.delete_link)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="タイトル取得", command=self.fetch_selected_title)
        
        # 右クリックイベントのバインド
        self.tree.bind("<Button-3>", self.show_context_menu)
        # ダブルクリックでの編集
        self.tree.bind("<Double-1>", lambda event: self.edit_link())
    
    def browse_folder(self):
        """フォルダ選択ダイアログを表示"""
        folder_path = filedialog.askdirectory(title="フォルダを選択")
        if folder_path:
            # パスの正規化 (スラッシュの統一)
            folder_path = os.path.normpath(folder_path)
            
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder_path)
            self.current_folder = folder_path
            
            # ツリーをクリア
            for item in self.file_tree.get_children():
                self.file_tree.delete(item)
            
            # パス管理用データをクリア
            self.tree_paths = {}
            
            # ルートフォルダを追加
            root_node = self.file_tree.insert("", tk.END, text=os.path.basename(folder_path), 
                                             values=("", self.get_modified_time(folder_path)),
                                             open=True)
            
            # ルートノードのパスを記録
            self.tree_paths[root_node] = folder_path
            
            # フォルダ内のファイルとサブフォルダを追加
            self.populate_directory(root_node, folder_path)
            
            self.status_var.set(f"フォルダを読み込みました: {folder_path}")

    def populate_directory(self, parent, path, level=1):
        """ディレクトリの内容をツリーに追加する"""
        try:
            # 最大再帰レベルをチェック（深すぎるとパフォーマンスに影響）
            if level > 10:  # 10階層まで展開
                dummy = self.file_tree.insert(parent, tk.END, text="...", values=("", ""))
                return
            
            # フォルダ内のファイルとサブフォルダを取得
            items = os.listdir(path)
            
            # フォルダとファイルを分ける
            folders = []
            files = []
            
            for item in items:
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    folders.append(item)
                else:
                    # テキストファイルのみを表示
                    file_ext = os.path.splitext(item)[1].lower()
                    if file_ext in self.text_extensions:
                        files.append(item)
            
            # フォルダを先に追加
            for folder in sorted(folders):
                folder_path = os.path.join(path, folder)
                folder_id = self.file_tree.insert(parent, tk.END, text=folder, 
                                                values=("", self.get_modified_time(folder_path)),
                                                tags=("folder",))
                
                # フォルダパスを記録
                self.tree_paths[folder_id] = folder_path
                
                # フォルダであることを示すダミーアイテムを追加（遅延読み込み用）
                dummy_id = self.file_tree.insert(folder_id, tk.END, text="読み込み中...", values=("", ""), tags=("dummy",))
            
            # 次にファイルを追加（テキストファイルのみ）
            for file in sorted(files):
                file_path = os.path.join(path, file)
                file_size = os.path.getsize(file_path)
                modified_time = self.get_modified_time(file_path)
                
                # ファイルの種類を判断
                file_ext = os.path.splitext(file)[1].lower()
                
                # ファイルをツリーに追加
                file_id = self.file_tree.insert(parent, tk.END, text=file, 
                                    values=(self.format_size(file_size), modified_time),
                                    tags=(file_ext[1:] if file_ext else "file",))
                
                # ファイルパスを記録
                self.tree_paths[file_id] = file_path
        
        except Exception as e:
            error_msg = f"フォルダの読み込み中にエラーが発生しました: {path}: {e}"
            self.status_var.set(error_msg)
            self.debug_print(error_msg, e)
    
    def on_tree_open(self, event):
        """ツリーノードが展開されたときのイベント"""
        # 選択されたアイテムを取得
        item_id = self.file_tree.focus()
        
        # フォルダかどうかを確認
        tags = self.file_tree.item(item_id, "tags")
        if "folder" in tags:
            # 子アイテムを取得
            children = self.file_tree.get_children(item_id)
            
            # ダミーアイテムが含まれているかチェック（未読み込み）
            has_dummy = False
            for child in children:
                child_tags = self.file_tree.item(child, "tags")
                if "dummy" in child_tags:
                    has_dummy = True
                    # ダミーアイテムを削除
                    self.file_tree.delete(child)
                    break
            
            # ダミーアイテムがあった場合、実際のフォルダ内容を読み込む
            if has_dummy:
                # アイテムのパスを取得
                path = self.tree_paths.get(item_id)
                if path and os.path.exists(path):
                    # フォルダ内容を追加
                    self.populate_directory(item_id, path, level=self.get_item_level(item_id) + 1)
    
    def get_item_level(self, item_id):
        """ツリーアイテムの階層レベルを取得"""
        level = 0
        parent_id = self.file_tree.parent(item_id)
        
        while parent_id:
            level += 1
            parent_id = self.file_tree.parent(parent_id)
            
        return level
    
    def on_tree_double_click(self, event):
        """ツリーアイテムをダブルクリックしたときの処理"""
        item_id = self.file_tree.identify("item", event.x, event.y)
        if item_id:
            # 選択アイテムがファイルかフォルダか確認
            tags = self.file_tree.item(item_id, "tags")
            
            if "folder" in tags:
                # フォルダの場合は展開/折りたたみを切り替え
                if self.file_tree.item(item_id, "open"):
                    self.file_tree.item(item_id, open=False)
                else:
                    self.file_tree.item(item_id, open=True)
            else:
                # ファイルの場合は開く
                self.open_selected_file()
    
    def get_modified_time(self, path):
        """ファイルの更新日時を取得"""
        try:
            mtime = os.path.getmtime(path)
            return datetime.fromtimestamp(mtime).strftime("%Y/%m/%d %H:%M:%S")
        except:
            return ""
    
    def format_size(self, size_bytes):
        """ファイルサイズを読みやすい形式に変換"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def open_selected_file(self):
        """選択したファイルを開く"""
        selected = self.file_tree.selection()
        if not selected:
            messagebox.showinfo("情報", "ファイルを選択してください")
            return
        
        item = selected[0]
        
        # フォルダかどうかを確認
        tags = self.file_tree.item(item, "tags")
        if "folder" in tags:
            messagebox.showinfo("情報", "フォルダは開けません。ファイルを選択してください。")
            return
        
        # ファイルパスを取得
        file_path = self.tree_paths.get(item)
        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("エラー", f"ファイルが見つかりません: {file_path}")
            return
        
        # ファイル種類の確認
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in self.text_extensions:
            messagebox.showinfo("情報", f"このファイル形式 ({file_ext}) は対応していません。テキストファイルを選択してください。")
            return
        
        # ファイルを読み込む
        try:
            file_content = self.read_text_file_safely(file_path)
            
            # テキストエリアに表示
            self.text_area.set_text(file_content)
            self.status_var.set(f"ファイルを読み込みました: {file_path}")
            
        except Exception as e:
            error_msg = f"ファイルの読み込み中にエラーが発生しました: {e}"
            self.debug_print(error_msg, e)
            messagebox.showerror("エラー", error_msg)
    
    def read_text_file_safely(self, file_path):
        """複数のエンコーディングを試して安全にテキストファイルを読む"""
        # まずはchardetで自動検出を試みる
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                detected_encoding = result['encoding']
                confidence = result['confidence']
                
                self.debug_print(f"chardet検出結果: {detected_encoding}, 信頼度: {confidence}")
                
                # 信頼度が低い場合は後で他のエンコーディングも試す
                if detected_encoding and confidence > 0.7:
                    try:
                        return raw_data.decode(detected_encoding)
                    except Exception as e:
                        self.debug_print(f"検出されたエンコーディング {detected_encoding} での読み込み失敗: {e}")
        except Exception as e:
            self.debug_print(f"chardetによるエンコーディング検出失敗: {e}")
        
        # 複数のエンコーディングを順番に試す
        errors = []
        for encoding in self.encodings_to_try:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    self.debug_print(f"エンコーディング {encoding} で読み込み成功")
                    return content
            except UnicodeDecodeError as e:
                error_msg = f"エンコーディング {encoding} での読み込み失敗: {e}"
                self.debug_print(error_msg)
                errors.append(error_msg)
            except Exception as e:
                error_msg = f"その他のエラー ({encoding}): {e}"
                self.debug_print(error_msg)
                errors.append(error_msg)
        
        # バイナリとして読み込み、文字化けしても表示する最終手段
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                # latin1は任意のバイト列を文字として解釈するので変換エラーは起きない
                content = raw_data.decode('latin1', errors='replace')
                self.debug_print("latin1 (強制変換) で読み込み")
                return content
        except Exception as e:
            self.debug_print(f"バイナリ読み込み失敗: {e}")
        
        # すべての方法が失敗した場合
        error_details = "\n".join(errors)
        raise Exception(f"ファイル '{file_path}' を読み込めませんでした。次のエンコーディングを試しました: {', '.join(self.encodings_to_try)}\n\n詳細エラー:\n{error_details}")
    
    def clear_text(self):
        """テキストボックスをクリア"""
        self.text_area.clear()
        self.status_var.set("テキストをクリアしました")

    def load_links_from_csv(self):
        """CSVファイルからリンクをロードしてTreeviewに表示"""
        # Treeviewをクリア
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # CSVファイルが存在しない場合は何もしない
        if not os.path.exists(self.csv_filename):
            self.status_var.set("CSVファイルが見つからないため、新しく作成します")
            self.create_csv_if_not_exists()
            return
        
        try:
            # CSVファイルを適切に解析して読み込む
            with open(self.csv_filename, 'r', newline='', encoding='utf-8') as file:
                # 改良されたCSV読み込み方法
                reader = csv.reader(file, quotechar='"', delimiter=',', quoting=csv.QUOTE_MINIMAL, skipinitialspace=True)
                header = next(reader)  # ヘッダー行をスキップ
                
                for row in reader:
                    # URLを含む列のインデックスを見つける
                    url_column = None
                    for i, cell in enumerate(row):
                        if cell.startswith("http"):
                            url_column = i
                            break
                    
                    # URLが見つかった場合
                    if url_column is not None:
                        url = row[url_column]
                        # URLとして処理する部分は「http://」または「https://」で始まる部分だけにする
                        # 正規表現でURLのパターンを抽出
                        url_pattern = r'https?://[^\s,]+'
                        match = re.search(url_pattern, url)
                        if match:
                            clean_url = match.group(0)
                            print(f"元のURL: {url}, クリーンなURL: {clean_url}")
                            self.tree.insert("", tk.END, values=(clean_url, "", ""))
                    else:
                        # 標準的なCSV形式（テスト用）
                        if len(row) >= 3:
                            self.tree.insert("", tk.END, values=(row[0], row[1], row[2]))
            
            self.status_var.set(f"{len(self.tree.get_children())}件のリンクを読み込みました")
        except Exception as e:
            error_msg = f"CSVファイルの読み込み中にエラーが発生しました: {e}"
            self.debug_print(error_msg, e)
            messagebox.showerror("エラー", error_msg)
            self.status_var.set("CSVファイルの読み込みエラー")
    
    def parse_csv_text(self, text):
        """CSVテキストを適切に解析する"""
        result = []
        
        try:
            # CSVReader用にStringIOを使う
            import io
            csv_file = io.StringIO(text)
            reader = csv.reader(csv_file, quotechar='"', delimiter=',', quoting=csv.QUOTE_MINIMAL, skipinitialspace=True)
            
            for row in reader:
                # 各行をリストとして処理
                result.append(row)
            
        except Exception as e:
            self.debug_print(f"CSV解析エラー: {e}")
            # 簡易的な分割（エラー時のフォールバック）
            lines = text.split("\n")
            for line in lines:
                if line.strip():
                    # カンマで分割しつつ、引用符内のカンマを保護
                    in_quotes = False
                    fields = []
                    current_field = ""
                    
                    for char in line:
                        if char == '"':
                            in_quotes = not in_quotes
                        elif char == ',' and not in_quotes:
                            fields.append(current_field)
                            current_field = ""
                        else:
                            current_field += char
                    
                    fields.append(current_field)  # 最後のフィールドを追加
                    result.append(fields)
        
        return result
    
    def extract_links_from_clipboard(self):
        """クリップボードからリンクを抽出"""
        try:
            # クリップボードからテキストを取得
            clipboard_text = self.root.clipboard_get()
            
            # クリップボードが空の場合
            if not clipboard_text:
                messagebox.showinfo("情報", "クリップボードが空です")
                return
            
            # URLを抽出するための正規表現パターン（より厳密なパターン）
            url_pattern = r'https?://[^\s,<>"]+'
            
            # テキストからURLを抽出
            found_urls = re.findall(url_pattern, clipboard_text)
            
            # HTMLコンテンツの検出とリンク抽出
            if clipboard_text.strip().startswith("<") and "href=" in clipboard_text:
                try:
                    soup = BeautifulSoup(clipboard_text, 'html.parser')
                    links = soup.find_all('a', href=True)
                    
                    for link in links:
                        url = link['href']
                        if url.startswith('http'):  # 相対パスは除外
                            found_urls.append(url)
                except Exception as e:
                    self.debug_print(f"HTMLパース失敗: {e}")
            
            # Amazon商品ページの検出
            amazon_pattern = r'([^|]+)\s*\|\s*([^|]+)\s*\|\s*本\s*\|\s*通販\s*\|\s*Amazon'
            amazon_matches = re.findall(amazon_pattern, clipboard_text)
            
            if amazon_matches:
                for match in amazon_matches:
                    product_name = match[0].strip()
                    author = match[1].strip()
                    # Amazonの検索URLを生成
                    search_query = f"{product_name} {author}"
                    encoded_query = urllib.parse.quote_plus(search_query)
                    amazon_url = f"https://www.amazon.co.jp/s?k={encoded_query}"
                    found_urls.append(amazon_url)
            
            if not found_urls:
                messagebox.showinfo("情報", "クリップボード内にリンクが見つかりませんでした")
                return
            
            # 重複を削除
            found_urls = list(dict.fromkeys(found_urls))
            
            # 既存のリンクを取得
            existing_links = self.get_existing_links()
            
            # 新しいリンクを追加
            new_links = []
            for url in found_urls:
                if url not in existing_links:
                    self.tree.insert("", tk.END, values=(url, "", ""))
                    new_links.append([url, "", ""])
            
            # 新しいリンクがある場合、CSVに追加
            if new_links:
                self.append_links_to_csv(new_links)
                self.status_var.set(f"{len(new_links)}件の新しいリンクを追加しました")
            else:
                self.status_var.set("新しいリンクはありませんでした（重複を除外）")
            
        except Exception as e:
            error_msg = f"クリップボードからのリンク抽出中にエラーが発生しました: {e}"
            self.debug_print(error_msg, e)
            messagebox.showerror("エラー", error_msg)
    
    def extract_links(self):
        """テキストエリアからハイパーリンクを抽出"""
        # リッチテキストボックスからURLを抽出（テキストとハイパーリンクの両方）
        found_urls = self.text_area.extract_urls()
        
        # テキストからCSVデータを検出し、その中のURLを抽出
        text = self.text_area.get_text()
        
        # CSVのような形式かどうかをチェック
        if "," in text and "\n" in text and any(url_part in text for url_part in ["http:", "https:"]):
            self.debug_print("CSVのようなデータを検出しました")
            # CSVとして解析
            rows = self.parse_csv_text(text)
            
            # 各行からURLを探す
            for row in rows:
                for cell in row:
                    if "http" in cell:
                        # URLのパターンを抽出
                        url_matches = re.findall(r'https?://[^\s,<>"]+', cell)
                        for url in url_matches:
                            found_urls.append(url)
        
        # Amazon商品ページの検出（URLがないテキストから）
        amazon_pattern = r'([^|]+)\s*\|\s*([^|]+)\s*\|\s*本\s*\|\s*通販\s*\|\s*Amazon'
        amazon_matches = re.findall(amazon_pattern, text)
        
        if amazon_matches:
            for match in amazon_matches:
                product_name = match[0].strip()
                author = match[1].strip()
                # Amazonの検索URLを生成
                search_query = f"{product_name} {author}"
                encoded_query = urllib.parse.quote_plus(search_query)
                amazon_url = f"https://www.amazon.co.jp/s?k={encoded_query}"
                found_urls.append(amazon_url)
        
        if not found_urls:
            messagebox.showinfo("情報", "テキスト内にリンクが見つかりませんでした")
            return
        
        # 重複を削除してURLをきれいにする
        clean_urls = []
        for url in found_urls:
            # URLをクリーンアップ（余分なカンマ以降を削除）
            # カンマの後ろはURLではない可能性が高い
            clean_url = re.search(r'https?://[^,\s]+', url)
            if clean_url:
                clean_url = clean_url.group(0)
                if clean_url not in clean_urls:
                    clean_urls.append(clean_url)
        
        # 既存のリンクを取得
        existing_links = self.get_existing_links()
        
        # 新しいリンクを追加
        new_links = []
        for url in clean_urls:
            if url not in existing_links:
                self.tree.insert("", tk.END, values=(url, "", ""))
                new_links.append([url, "", ""])
        
        # 新しいリンクがある場合、CSVに追加
        if new_links:
            self.append_links_to_csv(new_links)
            self.status_var.set(f"{len(new_links)}件の新しいリンクを追加しました")
        else:
            self.status_var.set("新しいリンクはありませんでした（重複を除外）")
    
    def get_existing_links(self):
        """既存のリンクリストを取得"""
        links = []
        for item in self.tree.get_children():
            values = self.tree.item(item, "values")
            links.append(values[0])
        return links
    
    def append_links_to_csv(self, new_links):
        """新しいリンクをCSVに追加"""
        try:
            with open(self.csv_filename, 'a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                for link in new_links:
                    writer.writerow(link)
        except Exception as e:
            error_msg = f"リンクの保存中にエラーが発生しました: {e}"
            self.debug_print(error_msg, e)
            messagebox.showerror("エラー", error_msg)
    
    def save_all_to_csv(self):
        """全てのリンクをCSVに保存"""
        try:
            with open(self.csv_filename, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(["URL", "タイトル", "ステータス"])
                
                for item in self.tree.get_children():
                    values = self.tree.item(item, "values")
                    writer.writerow(values)
            
            self.status_var.set("全てのリンク情報を保存しました")
        except Exception as e:
            error_msg = f"リンクの保存中にエラーが発生しました: {e}"
            self.debug_print(error_msg, e)
            messagebox.showerror("エラー", error_msg)
    
    def fetch_link_titles(self):
        """リンク先にアクセスしてタイトルを取得"""
        # 既に処理中なら何もしない
        if self.processing:
            return
            
        # 処理中は操作をロック
        self.processing = True
        self.toggle_ui_elements(False)
        self.status_var.set("リンク先情報を取得中...")
        self.progressbar.pack(side=tk.BOTTOM, fill=tk.X, before=self.statusbar)
        self.progress_var.set(0)
        
        # バックグラウンドスレッドで処理を実行
        thread = threading.Thread(target=self.fetch_titles_thread)
        thread.daemon = True
        thread.start()
    
    def fetch_titles_thread(self):
        """バックグラウンドでタイトル取得処理を実行"""
        try:
            # 更新カウンター
            updated_count = 0
            
            # 各リンクについて処理
            items = list(self.tree.get_children())
            total_items = len(items)
            
            for index, item in enumerate(items):
                if not self.processing:  # 処理が中断された場合
                    break
                    
                values = self.tree.item(item, "values")
                url, title, status = values[0], values[1], values[2]
                
                # プログレスバーを更新
                progress = (index / total_items) * 100
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                
                # ステータスが空か「取得失敗」の場合のみ処理
                if not status or status == "取得失敗":
                    try:
                        # リンク先にアクセスしてタイトルを取得
                        new_title = self.get_page_title(url)
                        
                        # タイトル取得成功
                        self.root.after(0, lambda i=item, u=url, t=new_title: 
                                       self.tree.item(i, values=(u, t, "取得成功")))
                        updated_count += 1
                        
                        # UIを更新
                        self.root.after(0, lambda u=url, t=new_title: 
                                       self.status_var.set(f"処理中: {u} - {t}"))
                    except Exception as e:
                        # タイトル取得失敗
                        self.root.after(0, lambda i=item, u=url, t=title: 
                                       self.tree.item(i, values=(u, t, "取得失敗")))
                        self.debug_print(f"Error fetching {url}: {e}")
            
            # 更新があれば保存
            if updated_count > 0:
                self.root.after(0, self.save_all_to_csv)
            
            # 処理完了時にUIを更新
            self.root.after(0, lambda c=updated_count: 
                           self.status_var.set(f"処理完了: {c}件のタイトルを更新しました"))
            self.root.after(0, lambda: self.progress_var.set(100))
            self.root.after(1000, lambda: self.progressbar.pack_forget())  # 1秒後に非表示
            self.root.after(0, lambda: self.toggle_ui_elements(True))
            self.root.after(0, lambda: setattr(self, 'processing', False))
        
        except Exception as e:
            # エラー発生時
            error_msg = f"処理中にエラーが発生しました: {e}"
            self.debug_print(error_msg, e)
            self.root.after(0, lambda: messagebox.showerror("エラー", error_msg))
            self.root.after(0, lambda: self.status_var.set("エラーが発生しました"))
            self.root.after(0, lambda: self.progressbar.pack_forget())
            self.root.after(0, lambda: self.toggle_ui_elements(True))
            self.root.after(0, lambda: setattr(self, 'processing', False))
    
    def fetch_selected_title(self):
        """選択したリンクのタイトルを取得"""
        # 既に処理中なら何もしない
        if self.processing:
            return
            
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("情報", "リンクを選択してください")
            return
        
        # 処理中は操作をロック
        self.processing = True
        self.toggle_ui_elements(False)
        
        # 選択したリンクを処理
        item = selected[0]
        values = self.tree.item(item, "values")
        url = values[0]
        
        self.status_var.set(f"{url} のタイトルを取得中...")
        
        # バックグラウンドスレッドで処理を実行
        thread = threading.Thread(target=lambda: self.fetch_single_title(item, url))
        thread.daemon = True
        thread.start()
    
    def fetch_single_title(self, item, url):
        """単一のURLのタイトルを取得"""
        try:
            # リンク先にアクセスしてタイトルを取得
            new_title = self.get_page_title(url)
            
            # タイトル取得成功
            self.root.after(0, lambda: self.tree.item(item, values=(url, new_title, "取得成功")))
            self.root.after(0, lambda: self.status_var.set(f"タイトル取得完了: {new_title}"))
            self.root.after(0, self.save_all_to_csv)
        except Exception as e:
            # タイトル取得失敗
            error_msg = f"タイトル取得失敗: {e}"
            self.debug_print(error_msg, e)
            self.root.after(0, lambda: self.tree.item(item, values=(url, "", "取得失敗")))
            self.root.after(0, lambda: self.status_var.set(error_msg))
            self.root.after(0, self.save_all_to_csv)
        finally:
            # UIを有効化
            self.root.after(0, lambda: self.toggle_ui_elements(True))
            self.root.after(0, lambda: setattr(self, 'processing', False))
    
    def get_page_title(self, url):
        """指定URLのページタイトルを取得"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # YouTubeの場合は特殊処理
        if "youtu.be" in url or "youtube.com" in url:
            return self.get_youtube_title(url, headers)
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # エラーチェック
        
        # エンコーディングを明示的に設定
        if response.encoding.lower() == 'iso-8859-1':
            response.encoding = response.apparent_encoding
        
        soup = BeautifulSoup(response.text, 'html.parser')
        title_tag = soup.find('title')
        
        if title_tag:
            return title_tag.string.strip()
        else:
            return "タイトルなし"
    
    def get_youtube_title(self, url, headers):
        """YouTubeの動画タイトルを取得"""
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # YouTube動画ページからタイトルを抽出 (複数のパターンで試行)
            # メタタグから抽出
            meta_title = soup.find("meta", property="og:title")
            if meta_title and meta_title.get("content"):
                return meta_title.get("content")
            
            # タイトルタグから抽出
            title_tag = soup.find("title")
            if title_tag and title_tag.string:
                title_text = title_tag.string.strip()
                if title_text.endswith("- YouTube"):
                    return title_text[:-10].strip()
                return title_text
            
            return "YouTube動画のタイトルを取得できませんでした"
        except Exception as e:
            self.debug_print(f"YouTube title extraction error: {e}")
            # Fallback: YouTube API（簡易版）
            video_id = None
            if "youtu.be/" in url:
                video_id = url.split("youtu.be/")[1].split("?")[0]
            elif "youtube.com/watch" in url and "v=" in url:
                video_id = re.search(r'v=([^&]+)', url).group(1)
                
            if video_id:
                try:
                    api_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
                    api_response = requests.get(api_url, timeout=10)
                    api_response.raise_for_status()
                    data = json.loads(api_response.text)
                    return data.get("title", "YouTube動画のタイトルを取得できませんでした")
                except Exception as e:
                    self.debug_print(f"YouTube API error: {e}")
                    
            return "YouTube動画のタイトルを取得できませんでした"
    
    def toggle_ui_elements(self, enabled):
        """UI要素の有効/無効を切り替え"""
        state = tk.NORMAL if enabled else tk.DISABLED
        self.fetch_button.config(state=state)
        self.extract_button.config(state=state)
        self.clipboard_button.config(state=state)
        self.clear_button.config(state=state)
        self.text_area.text.config(state=state)
        self.add_button.config(state=state)
        self.edit_button.config(state=state)
        self.delete_button.config(state=state)
        self.browse_button.config(state=state)
        self.open_button.config(state=state)
        self.folder_entry.config(state=state)
    
    def show_context_menu(self, event):
        """右クリックメニューを表示"""
        # 処理中は右クリックメニューを表示しない
        if self.processing:
            return
            
        if self.tree.selection():
            self.context_menu.post(event.x_root, event.y_root)
    
    def add_link(self):
        """新しいリンクを追加"""
        # 処理中は追加できない
        if self.processing:
            return
            
        dialog = EditDialog(self.root)
        self.root.wait_window(dialog)
        
        if dialog.result:
            url = dialog.result["url"]
            title = dialog.result["title"]
            status = dialog.result["status"]
            
            # URLが空でないことを確認
            if not url:
                messagebox.showwarning("警告", "URLを入力してください")
                return
            
            # 重複チェック
            existing_links = self.get_existing_links()
            if url in existing_links:
                messagebox.showwarning("警告", "このURLは既に存在します")
                return
            
            # Treeviewに追加
            self.tree.insert("", tk.END, values=(url, title, status))
            
            # CSVに保存
            self.save_all_to_csv()
    
    def edit_link(self):
        """選択したリンクを編集"""
        # 処理中は編集できない
        if self.processing:
            return
            
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("情報", "編集するリンクを選択してください")
            return
        
        item = selected[0]
        values = self.tree.item(item, "values")
        
        dialog = EditDialog(self.root, values[0], values[1], values[2])
        self.root.wait_window(dialog)
        
        if dialog.result:
            url = dialog.result["url"]
            title = dialog.result["title"]
            status = dialog.result["status"]
            
            # URLが空でないことを確認
            if not url:
                messagebox.showwarning("警告", "URLを入力してください")
                return
            
            # 重複チェック（自分自身は除外）
            existing_links = self.get_existing_links()
            existing_links.remove(values[0])  # 現在の自分自身のURLを除外
            if url in existing_links:
                messagebox.showwarning("警告", "このURLは既に存在します")
                return
            
            # Treeviewを更新
            self.tree.item(item, values=(url, title, status))
            
            # CSVに保存
            self.save_all_to_csv()
    
    def delete_link(self):
        """選択したリンクを削除"""
        # 処理中は削除できない
        if self.processing:
            return
            
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("情報", "削除するリンクを選択してください")
            return
        
        if messagebox.askyesno("確認", "選択したリンクを削除しますか？"):
            for item in selected:
                self.tree.delete(item)
            
            # CSVに保存
            self.save_all_to_csv()

# メインアプリケーションの実行
if __name__ == "__main__":
    root = tk.Tk()
    app = LinkManagerApp(root)
    root.mainloop()
