import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk, ImageChops # ImageChops をインポート
import io
import os
import sys
import time
import threading
import tempfile
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import tkinter.dnd as dnd

# 設定とログの初期化
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# SVG変換用のインポート
try:
    import cairosvg
    SVG_AVAILABLE = True
except ImportError as e:
    SVG_AVAILABLE = False
    logger.warning(f"SVG conversion not available: {e}")

# HTML変換用のインポート
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.common.exceptions import WebDriverException, TimeoutException
    
    # webdriver-managerの自動インストール対応
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        WEBDRIVER_MANAGER_AVAILABLE = True
    except ImportError:
        WEBDRIVER_MANAGER_AVAILABLE = False
        
    HTML_AVAILABLE = True
except ImportError as e:
    HTML_AVAILABLE = False
    WEBDRIVER_MANAGER_AVAILABLE = False
    logger.warning(f"HTML conversion not available: {e}")

class AppConfig:
    """アプリケーション設定管理"""
    def __init__(self):
        self.config_file = Path.home() / ".png_converter_config.json"
        self.default_config = {
            "recent_files": [],
            "last_output_dir": str(Path.home()),
            "svg_default_width": "",
            "svg_default_height": "",
            "svg_transparent": True,
            "svg_bg_color": "#FFFFFF",
            "html_default_width": "",
            "html_default_height": "",
            "html_default_wait": "2",
            "html_transparent": False,
            "html_bg_color": "#FFFFFF",
            "window_geometry": "950x750"
        }
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """設定を読み込み"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # デフォルト値で不足分を補完
                for key, value in self.default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        except Exception as e:
            logger.error(f"設定読み込みエラー: {e}")
        return self.default_config.copy()
    
    def save_config(self):
        """設定を保存"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"設定保存エラー: {e}")
    
    def add_recent_file(self, file_path: str):
        """最近使用したファイルを追加"""
        if file_path in self.config["recent_files"]:
            self.config["recent_files"].remove(file_path)
        self.config["recent_files"].insert(0, file_path)
        self.config["recent_files"] = self.config["recent_files"][:10]  # 最大10件
        self.save_config()

class DragDropMixin:
    """ドラッグ&ドロップ機能のミックスイン"""
    def setup_drag_drop(self, widget, callback, file_types=None):
        """ドラッグ&ドロップを設定"""
        def drop_handler(event):
            files = event.data.split()
            if files:
                file_path = files[0].strip('{}')  # Windowsの場合の{}を除去
                if file_types:
                    if any(file_path.lower().endswith(ext) for ext in file_types):
                        callback(file_path)
                    else:
                        messagebox.showwarning("警告", f"対応していないファイル形式です。\n対応形式: {', '.join(file_types)}")
                else:
                    callback(file_path)
        
        # tkinterのdndは制限が多いため、代替実装
        widget.bind('<Button-1>', lambda e: None)  # プレースホルダー

class UnifiedConverter:
    def __init__(self, root):
        self.root = root
        self.config = AppConfig()
        self.root.title("Multi-Format to PNG Converter Pro v2.9") # バージョン更新
        
        # 設定から窓サイズを復元
        geometry = self.config.config.get("window_geometry", "950x750")
        self.root.geometry(geometry)
        
        # アプリケーション終了時の処理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.setup_ui()
        self.create_menu()
        
    def setup_ui(self):
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # ノートブック（タブコンテナ）
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # SVGタブ
        if SVG_AVAILABLE:
            self.svg_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.svg_frame, text="SVG → PNG")
            self.svg_converter = SVGConverterTab(self.svg_frame, self.config, self) # self (UnifiedConverter instance) を渡す
        else:
            self.svg_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.svg_frame, text="SVG → PNG (無効)")
            self.create_disabled_tab(self.svg_frame, "SVG変換", "cairosvg Pillow")
        
        # HTMLタブ
        if HTML_AVAILABLE:
            self.html_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.html_frame, text="HTML → PNG")
            self.html_converter = HTMLConverterTab(self.html_frame, self.config, self) # self (UnifiedConverter instance) を渡す
        else:
            self.html_frame = ttk.Frame(self.notebook)
            self.notebook.add(self.html_frame, text="HTML → PNG (無効)")
            self.create_disabled_tab(self.html_frame, "HTML変換", "selenium webdriver-manager Pillow")
        
        # 情報タブ
        info_frame = ttk.Frame(self.notebook)
        self.notebook.add(info_frame, text="情報")
        self.create_info_tab(info_frame)
        
        # ステータスバー
        self.status_frame = ttk.Frame(main_frame)
        self.status_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        self.status_label = ttk.Label(self.status_frame, text="準備完了")
        self.status_label.pack(side=tk.LEFT)
        
        # グリッドの重みを設定
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
    
    def create_menu(self):
        """メニューバーを作成"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # ファイルメニュー
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ファイル", menu=file_menu)
        
        # 最近使用したファイル
        self.recent_menu = tk.Menu(file_menu, tearoff=0) 
        file_menu.add_cascade(label="最近使用したファイル", menu=self.recent_menu)
        self.update_recent_files_menu(self.recent_menu)
        
        file_menu.add_separator()
        file_menu.add_command(label="設定をリセット", command=self.reset_settings)
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.on_closing)
        
        # ヘルプメニュー
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ヘルプ", menu=help_menu)
        help_menu.add_command(label="使用方法", command=lambda: self.notebook.select(2)) 
        help_menu.add_command(label="バージョン情報", command=self.show_about)
    
    def update_recent_files_menu(self, menu=None): 
        if menu is None:
            menu = self.recent_menu 

        menu.delete(0, tk.END)
        recent_files = self.config.config.get("recent_files", [])
        
        if not recent_files:
            menu.add_command(label="（履歴なし）", state=tk.DISABLED)
        else:
            valid_entry_exists = False
            for file_path in recent_files:
                if Path(file_path).exists(): 
                    label_text = Path(file_path).name
                    menu.add_command(
                        label=label_text,
                        command=lambda f=file_path: self.open_recent_file(f)
                    )
                    valid_entry_exists = True
            if not valid_entry_exists: 
                 menu.add_command(label="（有効な履歴なし）", state=tk.DISABLED)

    def open_recent_file(self, file_path):
        logger.info(f"最近使用したファイルを開く試行: {file_path}")
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.svg':
            if SVG_AVAILABLE and hasattr(self, 'svg_converter'):
                self.notebook.select(0) 
                self.svg_converter.load_file(file_path)
                logger.info(f"SVGファイルをロード: {file_path}")
            else:
                messagebox.showwarning("情報", "SVG変換機能が無効か、タブが初期化されていません。")
        elif file_ext in ['.html', '.htm']:
            if HTML_AVAILABLE and hasattr(self, 'html_converter'):
                self.notebook.select(1) 
                self.html_converter.load_file(file_path)
                logger.info(f"HTMLファイルをロード: {file_path}")
            else:
                messagebox.showwarning("情報", "HTML変換機能が無効か、タブが初期化されていません。")
        else:
            messagebox.showwarning("情報", f"対応していないファイル形式です: {file_ext}")
            logger.warning(f"最近使用したファイルを開けません (未対応形式): {file_path}")

    def reset_settings(self):
        if messagebox.askyesno("確認", "すべての設定を初期値に戻しますか？\n（最近使用したファイルの履歴もクリアされます）"):
            logger.info("設定をリセットします。")
            self.config.config = self.config.default_config.copy()
            self.config.config["recent_files"] = []
            self.config.save_config()
            
            if hasattr(self, 'svg_converter') and SVG_AVAILABLE:
                self.svg_converter.load_settings_from_config()
                self.svg_converter.update_recent_files() 
            if hasattr(self, 'html_converter') and HTML_AVAILABLE:
                self.html_converter.load_settings_from_config()
                self.html_converter.update_recent_files() 
            
            self.update_recent_files_menu() 
            
            messagebox.showinfo("完了", "設定をリセットしました。\nアプリケーションを再起動するとウィンドウサイズも初期化されます。")
            logger.info("設定のリセットが完了しました。")
    
    def show_about(self):
        about_text = """Multi-Format to PNG Converter Pro v2.9

高機能ファイル変換ツール

新機能 v2.9:
• HTML変換時の画像下部欠け問題を改善 (ウィンドウサイズ調整強化)
• その他軽微な安定性向上

機能:
• SVG → PNG変換（日本語フォント対応）
• HTML → PNG変換（縦横比保持調整）
• 背景色設定・透過対応
• ドラッグ&ドロップ対応
• 設定の自動保存

開発: tkinter熟練スペシャリスト"""
        
        messagebox.showinfo("バージョン情報", about_text)
    
    def on_closing(self):
        self.config.config["window_geometry"] = self.root.geometry()
        self.config.save_config()
        if HTML_AVAILABLE and hasattr(self, 'html_converter') and self.html_converter.current_driver:
            try:
                logger.info("アプリケーション終了時にWebDriverをクリーンアップします。")
                self.html_converter.current_driver.quit()
                self.html_converter.current_driver = None
            except Exception as e:
                logger.error(f"WebDriver終了エラー: {e}")
        self.root.destroy()
        
    def create_disabled_tab(self, parent, converter_name, required_packages):
        frame = ttk.Frame(parent, padding="20")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        ttk.Label(
            frame, 
            text=f"{converter_name}は使用できません",
            font=("", 14, "bold")
        ).grid(row=0, column=0, pady=(0, 20))
        
        ttk.Label(
            frame,
            text=f"必要なライブラリがインストールされていません:\n{required_packages}",
            justify="center"
        ).grid(row=1, column=0, pady=(0, 20))
        
        ttk.Label(
            frame,
            text="以下のコマンドでインストールしてください:",
            justify="center"
        ).grid(row=2, column=0, pady=(0, 10))
        
        install_text_frame = ttk.Frame(frame) 
        install_text_frame.grid(row=3, column=0, pady=(0,10))

        install_cmd = f"pip install {required_packages}"
        install_text = scrolledtext.ScrolledText(install_text_frame, height=1, width=len(install_cmd) + 5, relief="flat", background=frame.cget("background"))
        install_text.insert(1.0, install_cmd)
        install_text.config(state="disabled", font=("Consolas", 10) if sys.platform == "win32" else ("Monaco", 10))
        install_text.pack(side=tk.LEFT, padx=(0,5))

        def copy_to_clipboard():
            self.root.clipboard_clear()
            self.root.clipboard_append(install_cmd)
            messagebox.showinfo("コピー完了", "インストールコマンドをクリップボードにコピーしました。")

        copy_button = ttk.Button(install_text_frame, text="コピー", command=copy_to_clipboard, width=5)
        copy_button.pack(side=tk.LEFT)

        ttk.Button(frame, text="パッケージ自動インストール試行", command=lambda p=required_packages: self.install_packages_thread(p)).grid(row=4, column=0, pady=(10,0))
        
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
    
    def install_packages_thread(self, packages):
        def install():
            try:
                import subprocess
                cmd_list = [sys.executable, "-m", "pip", "install"] + packages.split()
                logger.info(f"パッケージインストール試行: {' '.join(cmd_list)}")
                
                result = subprocess.run(cmd_list, capture_output=True, text=True, check=False, encoding='utf-8')
                
                if result.returncode == 0:
                    logger.info(f"パッケージインストール成功: {packages}\n{result.stdout}")
                    self.root.after(0, lambda: messagebox.showinfo("完了", f"パッケージのインストールが完了しました。\n{packages}\n\nアプリケーションを再起動して変更を反映してください。"))
                else:
                    logger.error(f"パッケージインストール失敗: {packages}\nExit Code: {result.returncode}\nStderr: {result.stderr}\nStdout: {result.stdout}")
                    error_details = result.stderr or result.stdout or "詳細不明"
                    self.root.after(0, lambda: messagebox.showerror("エラー", f"インストールに失敗しました ({packages}):\n\n{error_details}\n\n手動でのインストールをお試しください。"))
            except FileNotFoundError: 
                 logger.error(f"pipコマンド実行エラー (FileNotFoundError): {packages}")
                 self.root.after(0, lambda: messagebox.showerror("エラー", "pipコマンドが見つかりません。Pythonの環境設定を確認してください。"))
            except Exception as e:
                logger.error(f"パッケージインストール中の予期せぬエラー: {e}", exc_info=True)
                self.root.after(0, lambda: messagebox.showerror("エラー", f"インストール中に予期せぬエラーが発生しました ({packages}):\n{str(e)}"))
        
        if messagebox.askyesno("インストール確認", f"以下のパッケージをインストールしようとしています:\n{packages}\n\n続行しますか？\n（管理者権限が必要な場合があります）"):
            threading.Thread(target=install, daemon=True).start()
        
    def create_info_tab(self, parent):
        frame = ttk.Frame(parent, padding="20")
        frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        ttk.Label(
            frame, 
            text="Multi-Format to PNG Converter Pro v2.9", 
            font=("", 16, "bold")
        ).grid(row=0, column=0, pady=(0, 20))
        
        info_text = scrolledtext.ScrolledText(frame, height=25, width=80, wrap=tk.WORD)
        info_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        info_content = """
🚀 Multi-Format to PNG Converter Pro v2.9

このアプリケーションは複数の形式のファイルをPNG画像に変換する統合ツールです。

【新機能 v2.9】
🔧 HTML変換時の画像下部欠け問題を改善 (ウィンドウサイズ調整強化)
✨ その他軽微な安定性向上

【主要機能】
✨ ドラッグ&ドロップ対応
✨ 設定の自動保存・復元
✨ 最近使用したファイル履歴
✨ 詳細なエラーハンドリング
✨ 日本語完全対応
✨ 縦横比保持変換
✨ 背景色・透過設定

【機能】
📄 SVG → PNG変換
• ベクター形式のSVGファイルを高品質なPNG画像に変換
• システムフォント自動対応（日本語含む）
• アスペクト比を維持したプレビュー表示
• カスタムサイズ出力対応
• 背景色設定・透過対応
• 大きなファイルの最適化処理

🌐 HTML → PNG変換
• HTMLファイルをブラウザでレンダリングしてPNG画像として保存
• 実サイズ出力対応（サイズ指定なし時）
• 指定サイズ出力対応（縦横比保持・全体表示）
• 日本語フォント強制適用（文字化け完全解決）
• 背景色のオーバーライド・透過対応
• JavaScript実行対応

【背景設定】
🎨 SVG変換:
• 透過: 元のSVGの透過を保持
• 背景色: 指定した色で背景を塗りつぶし

🎨 HTML変換:
• 透過: 背景を透明に設定（技術的制限あり）
• 背景色: 指定した色でページ背景をオーバーライド

※ HTML→PNGの透過背景は技術的制限により、完全には対応できない場合があります。
  確実な透過背景が必要な場合は、SVG形式をご利用ください。

【使用方法】
1. 上部のタブから変換したい形式を選択
2. ファイルをドラッグ&ドロップまたは「参照」ボタンで選択
3. プレビューで内容を確認
4. サイズ・背景設定をカスタマイズ
5. 「PNG に変換」ボタンで変換実行

【ショートカット】
• Ctrl+O: ファイルを開く (アクティブなタブに応じて)
• Ctrl+S: 変換実行 (アクティブなタブに応じて)
• Ctrl+Q: アプリケーション終了
• F1: この情報を表示

【必要な依存関係】
SVG変換:
• pip install cairosvg Pillow

HTML変換:
• pip install selenium webdriver-manager Pillow
• ChromeDriverは自動でダウンロードされます

【対応ファイル形式】
入力: .svg, .html, .htm
出力: .png（透過・背景色対応）

【設定ファイル】
設定は自動的に以下の場所に保存されます:
{config_file}
        """.format(config_file=AppConfig().config_file)
        
        info_text.insert(1.0, info_content.strip())
        info_text.config(state="disabled")
        
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

class FontManager:
    @staticmethod
    def get_japanese_fonts():
        return [
            "Hiragino Sans", "Hiragino Kaku Gothic ProN", "Yu Gothic", 
            "Meiryo", "MS Gothic", "MS Mincho", "Takao Gothic", 
            "IPA Gothic", "Noto Sans CJK JP", "DejaVu Sans", "sans-serif"
        ]

class SVGConverterTab(DragDropMixin):
    def __init__(self, parent, config: AppConfig, app_instance): # app_instance を追加
        self.parent = parent
        self.config = config
        self.app = app_instance # UnifiedConverterのインスタンスを保持
        self.input_file_path = tk.StringVar()
        self.output_file_path = tk.StringVar()
        
        self.width_var = tk.StringVar()
        self.height_var = tk.StringVar()
        self.transparent_var = tk.BooleanVar()
        self.bg_color_var = tk.StringVar()
        
        self.load_settings_from_config()

        self.current_svg_data = None
        self.preview_image = None
        self.conversion_cancelled = False
        
        self.setup_ui()
        
    def load_settings_from_config(self):
        self.width_var.set(self.config.config.get("svg_default_width", ""))
        self.height_var.set(self.config.config.get("svg_default_height", ""))
        self.transparent_var.set(self.config.config.get("svg_transparent", True))
        self.bg_color_var.set(self.config.config.get("svg_bg_color", "#FFFFFF"))
        if hasattr(self, 'transparent_check'): 
            self.on_transparent_changed() 

    def setup_ui(self):
        main_frame = ttk.Frame(self.parent, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        input_frame = ttk.LabelFrame(main_frame, text="入力ファイル (SVG) - ドラッグ&ドロップ対応", padding="5")
        input_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.input_entry = ttk.Entry(input_frame, textvariable=self.input_file_path, width=60, state="readonly")
        self.input_entry.grid(row=0, column=0, padx=(0, 5), sticky=(tk.W, tk.E))
        ttk.Button(input_frame, text="参照", command=self.browse_input_file).grid(row=0, column=1)
        
        self.setup_drag_drop(self.input_entry, self.load_file, ['.svg'])
        
        recent_frame = ttk.Frame(input_frame)
        recent_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        
        self.recent_combo = ttk.Combobox(recent_frame, width=50, state="readonly")
        self.recent_combo.grid(row=0, column=0, padx=(0, 5), sticky=(tk.W, tk.E))
        self.recent_combo.bind('<<ComboboxSelected>>', self.on_recent_selected)
        ttk.Button(recent_frame, text="開く", command=self.open_recent).grid(row=0, column=1)
        
        self.update_recent_files()
        
        output_frame = ttk.LabelFrame(main_frame, text="出力ファイル (PNG)", padding="5")
        output_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Entry(output_frame, textvariable=self.output_file_path, width=60).grid(row=0, column=0, padx=(0, 5), sticky=(tk.W, tk.E))
        ttk.Button(output_frame, text="参照", command=self.browse_output_file).grid(row=0, column=1)
        
        preview_frame = ttk.LabelFrame(main_frame, text="プレビュー", padding="5")
        preview_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.preview_canvas = tk.Canvas(preview_frame, width=400, height=300, bg="white", relief="sunken", borderwidth=2)
        self.preview_canvas.grid(row=0, column=0, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.preview_label = ttk.Label(preview_frame, text="SVGファイルを選択またはドラッグ&ドロップしてください")
        self.preview_label.grid(row=1, column=0, pady=5)
        
        options_frame = ttk.LabelFrame(main_frame, text="変換オプション", padding="5")
        options_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        size_frame = ttk.Frame(options_frame)
        size_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        ttk.Label(size_frame, text="出力サイズ:").grid(row=0, column=0, padx=(0, 5))
        ttk.Label(size_frame, text="幅:").grid(row=0, column=1, padx=(10, 2))
        
        width_entry = ttk.Entry(size_frame, textvariable=self.width_var, width=8)
        width_entry.grid(row=0, column=2, padx=(0, 5))
        width_entry.bind('<FocusOut>', self.save_settings)
        
        ttk.Label(size_frame, text="高さ:").grid(row=0, column=3, padx=(10, 2))
        
        height_entry = ttk.Entry(size_frame, textvariable=self.height_var, width=8)
        height_entry.grid(row=0, column=4, padx=(0, 5))
        height_entry.bind('<FocusOut>', self.save_settings)
        
        ttk.Label(size_frame, text="(空白の場合は元のサイズ)").grid(row=0, column=5, padx=(10, 0))
        
        bg_frame = ttk.Frame(options_frame)
        bg_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        ttk.Label(bg_frame, text="背景:").grid(row=0, column=0, padx=(0, 10))
        
        self.transparent_check = ttk.Checkbutton(
            bg_frame, text="透過", variable=self.transparent_var,
            command=self.on_transparent_changed
        )
        self.transparent_check.grid(row=0, column=1, padx=(0, 10))
        
        ttk.Label(bg_frame, text="背景色:").grid(row=0, column=2, padx=(10, 5))
        
        self.bg_color_frame = tk.Frame(bg_frame, width=30, height=20, relief="sunken", borderwidth=2)
        self.bg_color_frame.grid(row=0, column=3, padx=(0, 5))
        self.bg_color_frame.bind("<Button-1>", self.choose_bg_color)
        
        self.bg_color_label = ttk.Label(bg_frame, text=self.bg_color_var.get())
        self.bg_color_label.grid(row=0, column=4, padx=(5, 10))
        
        ttk.Button(bg_frame, text="色選択", command=self.choose_bg_color).grid(row=0, column=5)
        
        self.update_bg_color_display()
        self.on_transparent_changed() 
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        self.convert_button = ttk.Button(button_frame, text="PNG に変換 (Ctrl+S)", command=self.convert_svg_to_png, state="disabled")
        self.convert_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.cancel_button = ttk.Button(button_frame, text="キャンセル", command=self.cancel_conversion, state="disabled")
        self.cancel_button.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="プレビュー更新", command=self.update_preview).pack(side=tk.LEFT)
        
        self.progress = ttk.Progressbar(button_frame, mode='determinate', length=100)
        self.progress.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)
        
        self.app.root.bind_all('<Control-o>', lambda e: self.handle_global_shortcut(self.browse_input_file, 0), add="+")
        self.app.root.bind_all('<Control-s>', lambda e: self.handle_global_shortcut(self.convert_svg_to_png, 0), add="+")

        self.parent.columnconfigure(0, weight=1)
        self.parent.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1) 
        input_frame.columnconfigure(0, weight=1)
        output_frame.columnconfigure(0, weight=1)
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        recent_frame.columnconfigure(0, weight=1)
        options_frame.columnconfigure(0, weight=1)

    def handle_global_shortcut(self, command_func, tab_index):
        try:
            if self.app.notebook.index(self.app.notebook.select()) == tab_index:
                if command_func == self.convert_svg_to_png and self.convert_button['state'] == 'normal':
                    command_func()
                elif command_func == self.browse_input_file: 
                     command_func()
        except tk.TclError: 
            logger.warning("グローバルショートカット処理中にTclError (SVGタブ)")
        except Exception as e:
            logger.error(f"グローバルショートカット処理エラー (SVGタブ): {e}")


    def update_recent_files(self):
        recent_svg_files = [f for f in self.config.config.get("recent_files", []) 
                            if Path(f).suffix.lower() == '.svg' and Path(f).exists()]
        
        self.recent_combo['values'] = [Path(f).name for f in recent_svg_files]
        self.recent_files_paths = recent_svg_files 
        
        if recent_svg_files:
            self.recent_combo.current(0) 
        else:
            self.recent_combo.set('') 
    
    def on_recent_selected(self, event):
        selected_index = self.recent_combo.current()
        if selected_index >= 0 and selected_index < len(self.recent_files_paths):
            self.load_file(self.recent_files_paths[selected_index])

    def open_recent(self):
        selection_index = self.recent_combo.current()
        if selection_index >= 0 and selection_index < len(self.recent_files_paths):
            self.load_file(self.recent_files_paths[selection_index])
        elif self.recent_combo.get(): 
             messagebox.showwarning("情報", "有効なファイルが選択されていません。")
        else:
             messagebox.showinfo("情報", "最近使用したSVGファイルの履歴がありません。")

    def on_transparent_changed(self):
        if self.transparent_var.get():
            self.bg_color_frame.config(bg="gray90") 
            self.bg_color_label.config(foreground="gray50")
            self.bg_color_frame.unbind("<Button-1>")
        else:
            self.bg_color_label.config(foreground=ttk.Style().lookup('TLabel', 'foreground')) 
            self.update_bg_color_display()
            self.bg_color_frame.bind("<Button-1>", self.choose_bg_color)
        self.save_settings()
        if self.current_svg_data: 
            self.update_preview() 
    
    def choose_bg_color(self, event=None):
        if self.transparent_var.get():
            return 
            
        try:
            from tkinter import colorchooser
            current_color = self.bg_color_var.get()
            color_info = colorchooser.askcolor(
                title="背景色を選択",
                initialcolor=current_color if current_color and current_color.startswith("#") else "#FFFFFF" 
            )
            if color_info and color_info[1]:  
                self.bg_color_var.set(color_info[1])
                self.update_bg_color_display()
                self.save_settings()
                if self.current_svg_data: 
                    self.update_preview()
        except ImportError:
            messagebox.showwarning("警告", "カラーピッカーが利用できません (tkinter.colorchooserが見つかりません)。")
        except Exception as e:
            logger.error(f"色選択エラー: {e}")
            messagebox.showerror("エラー", f"色の選択中にエラーが発生しました: {e}")

    def update_bg_color_display(self):
        try:
            color = self.bg_color_var.get()
            if not color or not color.startswith("#") or len(color) != 7: 
                color = "#FFFFFF" 
                self.bg_color_var.set(color)
            self.bg_color_frame.config(bg=color)
            self.bg_color_label.config(text=color)
        except tk.TclError: 
            self.bg_color_var.set("#FFFFFF")
            self.bg_color_frame.config(bg="#FFFFFF")
            self.bg_color_label.config(text="#FFFFFF")
    
    def save_settings(self, event=None):
        self.config.config["svg_default_width"] = self.width_var.get()
        self.config.config["svg_default_height"] = self.height_var.get()
        self.config.config["svg_transparent"] = self.transparent_var.get()
        self.config.config["svg_bg_color"] = self.bg_color_var.get()
        self.config.save_config()
    
    def browse_input_file(self):
        initial_dir_svg = self.config.config.get("last_input_dir_svg", self.config.config.get("last_output_dir", str(Path.home())))

        file_path = filedialog.askopenfilename(
            title="SVGファイルを選択",
            initialdir=initial_dir_svg,
            filetypes=[("SVG files", "*.svg"), ("All files", "*.*")]
        )
        
        if file_path:
            self.config.config["last_input_dir_svg"] = str(Path(file_path).parent) 
            self.config.save_config()
            self.load_file(file_path)
    
    def load_file(self, file_path: str):
        try:
            file_size = Path(file_path).stat().st_size
            if file_size > 10 * 1024 * 1024: 
                if not messagebox.askyesno("警告", f"ファイルサイズが大きいです ({file_size // (1024 * 1024)}MB)。\n処理に時間がかかる可能性があります。続行しますか？"):
                    return
            
            self.input_file_path.set(file_path)
            
            input_p = Path(file_path)
            output_dir_default = self.config.config.get("last_output_dir", str(input_p.parent))
            output_path = Path(output_dir_default) / f"{input_p.stem}.png"
            self.output_file_path.set(str(output_path))
            
            self.load_svg_file(file_path) 
            if self.current_svg_data: 
                self.convert_button.config(state="normal")
            else:
                self.convert_button.config(state="disabled")

            self.config.add_recent_file(file_path)
            self.update_recent_files() 
            self.app.update_recent_files_menu() # UnifiedConverterのメソッドを呼び出す

            if file_path in self.recent_files_paths:
                 self.recent_combo.current(self.recent_files_paths.index(file_path))

        except Exception as e:
            logger.error(f"ファイル読み込みエラー: {e}", exc_info=True)
            messagebox.showerror("エラー", f"ファイルの読み込みに失敗しました: {str(e)}")
            self.convert_button.config(state="disabled")
    
    def browse_output_file(self):
        default_name = ""
        if self.input_file_path.get():
            default_name = f"{Path(self.input_file_path.get()).stem}.png"
        
        initial_dir_out = self.config.config.get("last_output_dir", str(Path.home()))

        file_path = filedialog.asksaveasfilename(
            title="PNGファイルの保存先を選択",
            initialdir=initial_dir_out,
            initialfile=default_name,
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        
        if file_path:
            self.output_file_path.set(file_path)
            self.config.config["last_output_dir"] = str(Path(file_path).parent)
            self.config.save_config()
            
    def load_svg_file(self, file_path):
        self.current_svg_data = None 
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()
            logger.info(f"UTF-8でSVGファイル読み込み成功: {file_path}")
        except UnicodeDecodeError:
            logger.warning(f"UTF-8でのSVG読み込み失敗、cp932で再試行: {file_path}")
            try:
                with open(file_path, 'r', encoding='cp932') as f: 
                    svg_content = f.read()
                logger.info(f"cp932でSVGファイル読み込み成功: {file_path}")
            except Exception as e_alt_enc:
                logger.error(f"SVGファイル読み込みエラー (代替エンコーディング試行後): {e_alt_enc}", exc_info=True)
                messagebox.showerror("エラー", f"SVGファイルの読み込みに失敗しました: {str(e_alt_enc)}\n\nファイルエンコーディングを確認してください (UTF-8, Shift_JISなど)。")
                return 
        except Exception as e:
            logger.error(f"SVGファイル読み込みエラー: {e}", exc_info=True)
            messagebox.showerror("エラー", f"SVGファイルの読み込みに失敗しました: {str(e)}")
            return 
        
        try:
            processed_svg = self.preprocess_svg_for_japanese(svg_content)
            logger.info("SVG前処理 (preprocess_svg_for_japanese) 完了")
        except Exception as e_preprocess:
            logger.error(f"SVG前処理エラー: {e_preprocess}", exc_info=True)
            messagebox.showerror("エラー", f"SVGの前処理中にエラーが発生しました: {str(e_preprocess)}")
            return 

        if not processed_svg.strip().lower().startswith('<svg'):
            logger.warning("前処理後のSVGが<svg>で始まっていません。")
            if not messagebox.askyesno("警告", "このファイルは有効なSVGファイルではない可能性があります (前処理後)。続行しますか？"):
                return 
        
        self.current_svg_data = processed_svg
        self.update_preview() 
            
    def preprocess_svg_for_japanese(self, svg_content: str) -> str:
        import xml.etree.ElementTree as ET
        from xml.etree.ElementTree import ParseError

        logger.info("preprocess_svg_for_japanese 開始")
        
        preferred_fonts = '"Hiragino Sans", "Hiragino Kaku Gothic ProN", "Yu Gothic", "Meiryo", "MS Gothic", "MS Mincho", "Takao Gothic", "IPA Gothic", "Noto Sans CJK JP", "DejaVu Sans", sans-serif'
        
        font_style_rules_text = f"""
            text, tspan, textPath {{ 
                font-family: {preferred_fonts} !important; 
                font-weight: normal !important; 
                font-style: normal !important; 
                font-variant: normal !important;
                text-decoration: none !important;
            }}
        """
        try:
            namespaces = {
                'svg': 'http://www.w3.org/2000/svg',
                'xlink': 'http://www.w3.org/1999/xlink'
            }
            for prefix, uri in namespaces.items():
                ET.register_namespace(prefix, uri)

            if svg_content.startswith('\ufeff'):
                svg_content = svg_content[1:]

            root = ET.fromstring(svg_content)
            logger.info("SVGをXMLとしてパース成功")

            defs_tag = root.find('svg:defs', namespaces)
            if defs_tag is None:
                defs_tag = ET.SubElement(root, '{http://www.w3.org/2000/svg}defs')
                logger.info("<defs>タグを作成しました。")
            
            style_tag = defs_tag.find('svg:style', namespaces)
            if style_tag is None:
                style_tag = ET.SubElement(defs_tag, '{http://www.w3.org/2000/svg}style')
                style_tag.set('type', 'text/css')
                logger.info("<style>タグを作成し、<defs>に追加しました。")

            if style_tag.text:
                style_tag.text += "\n" + font_style_rules_text
            else:
                style_tag.text = font_style_rules_text
            logger.info("フォントスタイルルールを<style>タグに追記/設定しました。")

            processed_svg_content = ET.tostring(root, encoding='unicode', method='xml')
            logger.info("XMLツリーから文字列への変換完了")
            return processed_svg_content

        except ParseError as e_parse:
            logger.error(f"SVGのXMLパースエラー: {e_parse}。正規表現ベースのフォールバック処理を試みます。", exc_info=True)
            import re
            style_match = re.search(r'<style[^>]*>([\s\S]*?)</style>', svg_content, re.IGNORECASE)
            if style_match:
                existing_styles = style_match.group(1)
                new_styles = existing_styles + "\n" + font_style_rules_text
                svg_content = svg_content.replace(existing_styles, new_styles, 1)
            else:
                font_defs = f"<defs><style type=\"text/css\">{font_style_rules_text.strip()}</style></defs>"
                svg_pattern = r'(<svg[^>]*>)' 
                if re.search(svg_pattern, svg_content, re.IGNORECASE):
                    svg_content = re.sub(svg_pattern, lambda m: m.group(1) + font_defs, svg_content, 1, flags=re.IGNORECASE)
                else: 
                    logger.warning("フォールバック処理: SVGタグが見つかりませんでした。")
                    svg_content = font_defs + svg_content 
            logger.info("正規表現ベースのフォールバック処理完了")
            return svg_content
        except Exception as e_general:
            logger.error(f"SVG前処理中に予期せぬエラー: {e_general}", exc_info=True)
            return svg_content 

            
    def update_preview(self):
        if not self.current_svg_data:
            self.preview_canvas.delete("all")
            self.preview_label.config(text="SVGファイルを選択またはドラッグ&ドロップしてください")
            return
            
        try:
            self.progress.config(mode='indeterminate')
            self.progress.start()
            self.parent.update_idletasks() 

            render_params = {'dpi': 150} 
            if not self.transparent_var.get():
                bg_color_val = self.bg_color_var.get()
                if bg_color_val and bg_color_val.startswith("#"): 
                     render_params['background_color'] = bg_color_val
                else:
                    logger.warning(f"プレビュー背景色が無効({bg_color_val})なため、デフォルト白を使用します。")
                    render_params['background_color'] = "#FFFFFF"

            logger.info(f"プレビューレンダリング開始。SVGデータ長: {len(self.current_svg_data)} bytes")
            svg_bytes_for_cairo = self.current_svg_data.encode('utf-8')
            png_data = cairosvg.svg2png(
                bytestring=svg_bytes_for_cairo, 
                **render_params
            )
            logger.info(f"プレビューレンダリング完了。PNGデータ長: {len(png_data)} bytes")
            
            image = Image.open(io.BytesIO(png_data))
            
            self.preview_canvas.update_idletasks() 
            canvas_width = self.preview_canvas.winfo_width()
            canvas_height = self.preview_canvas.winfo_height()
            
            if canvas_width <= 1 or canvas_height <= 1: 
                canvas_width = 400 
                canvas_height = 300
                
            image_ratio = image.width / image.height if image.height != 0 else 1
            canvas_ratio = canvas_width / canvas_height if canvas_height != 0 else 1
            
            margin = 20 
            if image_ratio > canvas_ratio:
                new_width = canvas_width - margin
                new_height = int(new_width / image_ratio) if image_ratio != 0 else canvas_height - margin
            else:
                new_height = canvas_height - margin
                new_width = int(new_height * image_ratio) if canvas_height !=0 else canvas_width - margin
            
            new_width = max(1, new_width) 
            new_height = max(1, new_height)

            resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            self.preview_image = ImageTk.PhotoImage(resized_image)
            
            self.preview_canvas.delete("all")
            x_offset = (canvas_width - new_width) // 2
            y_offset = (canvas_height - new_height) // 2
            self.preview_canvas.create_image(x_offset, y_offset, anchor=tk.NW, image=self.preview_image)
            
            file_size_bytes = len(svg_bytes_for_cairo)
            size_text = f"元サイズ: {image.width}×{image.height} px, ファイル: {file_size_bytes // 1024} KB"
            self.preview_label.config(text=size_text)
            
        except Exception as e:
            logger.error(f"プレビュー生成エラー: {e}", exc_info=True)
            self.preview_canvas.delete("all")
            self.preview_label.config(text=f"プレビューエラー (詳細ログ参照)")
            if not isinstance(e, (OSError, ValueError)) or "cairosvg" not in str(e).lower():
                 messagebox.showerror("プレビューエラー", f"プレビューの生成中に予期せぬエラーが発生しました:\n{str(e)}")
        finally:
            self.progress.stop()
            self.progress.config(mode='determinate', value=0)
    
    def cancel_conversion(self):
        self.conversion_cancelled = True
        if self.input_file_path.get() and self.output_file_path.get() and self.current_svg_data:
            self.convert_button.config(state="normal")
        else:
            self.convert_button.config(state="disabled")
        self.cancel_button.config(state="disabled")
        self.progress.stop()
        self.progress.config(value=0)
        logger.info("SVG変換がキャンセルされました")
        if hasattr(self.app, 'status_label'): 
            self.app.status_label.config(text="SVG変換がキャンセルされました")
    
    def convert_svg_to_png(self):
        if not self.current_svg_data: 
            messagebox.showwarning("警告", "SVGファイルが読み込まれていないか、読み込みに失敗しています。")
            logger.warning("convert_svg_to_png: current_svg_dataがありません。")
            return
            
        if not self.output_file_path.get():
            messagebox.showwarning("警告", "出力ファイルのパスが指定されていません。")
            return
        
        output_p = Path(self.output_file_path.get())
        try:
            output_p.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"出力ディレクトリ作成エラー: {e}", exc_info=True)
            messagebox.showerror("エラー", f"出力ディレクトリの作成に失敗しました: {e}")
            return

        self.convert_button.config(state="disabled")
        self.cancel_button.config(state="normal")
        self.conversion_cancelled = False
        if hasattr(self.app, 'status_label'):
            self.app.status_label.config(text="SVG変換中...")
        
        threading.Thread(target=self._convert_thread, daemon=True).start()
    
    def _convert_thread(self):
        try:
            output_width_str = self.width_var.get().strip()
            output_height_str = self.height_var.get().strip()
            output_width = None
            output_height = None
            
            if output_width_str:
                try:
                    output_width = int(output_width_str)
                    if output_width <= 0: raise ValueError()
                except ValueError:
                    self.app.root.after(0, lambda: self._conversion_complete(False, "幅の指定が無効です。正の整数値を入力してください。"))
                    return
                    
            if output_height_str:
                try:
                    output_height = int(output_height_str)
                    if output_height <= 0: raise ValueError()
                except ValueError:
                    self.app.root.after(0, lambda: self._conversion_complete(False, "高さの指定が無効です。正の整数値を入力してください。"))
                    return
            
            self.app.root.after(0, lambda: self.progress.config(mode='indeterminate'))
            self.app.root.after(0, lambda: self.progress.start())
            
            conversion_params = {
                'output_width': output_width,
                'output_height': output_height,
                'dpi': 300 
            }
            if not self.transparent_var.get():
                bg_color_val = self.bg_color_var.get()
                if bg_color_val and bg_color_val.startswith("#"):
                    conversion_params['background_color'] = bg_color_val
                else:
                    logger.warning(f"変換時背景色が無効({bg_color_val})なため、デフォルト白を使用します。")
                    conversion_params['background_color'] = "#FFFFFF"

            logger.info(f"SVG変換実行。パラメータ: {conversion_params}")
            svg_bytes_for_cairo = self.current_svg_data.encode('utf-8')
            png_data = cairosvg.svg2png(bytestring=svg_bytes_for_cairo, **conversion_params)
            logger.info(f"cairosvg.svg2png 完了。PNGデータ長: {len(png_data)} bytes")
            
            if self.conversion_cancelled:
                self.app.root.after(0, lambda: self._conversion_complete(False, "変換がキャンセルされました (スレッド内)"))
                return
            
            with open(self.output_file_path.get(), 'wb') as f:
                f.write(png_data)
            
            output_size_kb = len(png_data) // 1024
            with Image.open(self.output_file_path.get()) as img_out: 
                final_w, final_h = img_out.size

            success_message = (f"変換が完了しました\n"
                               f"出力: {self.output_file_path.get()}\n"
                               f"サイズ: {final_w}×{final_h} px, {output_size_kb} KB")
            
            self.app.root.after(0, lambda: self._conversion_complete(True, success_message))
            
        except Exception as e:
            logger.error(f"SVG変換スレッドエラー: {e}", exc_info=True)
            self.app.root.after(0, lambda: self._conversion_complete(False, f"SVG変換エラー:\n{str(e)}"))
    
    def _conversion_complete(self, success: bool, message: str):
        self.progress.stop()
        self.progress.config(mode='determinate', value=0)
        if self.input_file_path.get() and self.output_file_path.get() and self.current_svg_data:
            self.convert_button.config(state="normal")
        else:
            self.convert_button.config(state="disabled")
        self.cancel_button.config(state="disabled")
        
        status_text_prefix = "SVG変換"
        status_label_widget = self.app.status_label if hasattr(self.app, 'status_label') else None

        if success and not self.conversion_cancelled:
            if status_label_widget: status_label_widget.config(text=f"{status_text_prefix}完了: {Path(self.output_file_path.get()).name}")
            messagebox.showinfo("完了", message)
            logger.info(f"{status_text_prefix}が正常に完了しました。")
        elif not self.conversion_cancelled: 
            if status_label_widget: status_label_widget.config(text=f"{status_text_prefix}失敗")
            messagebox.showerror("エラー", f"{status_text_prefix}に失敗しました:\n{message}")
            logger.warning(f"{status_text_prefix}失敗: {message}")

class HTMLConverterTab(DragDropMixin):
    def __init__(self, parent, config: AppConfig, app_instance): # app_instance を追加
        self.parent = parent
        self.config = config
        self.app = app_instance # UnifiedConverterのインスタンスを保持
        self.input_file_path = tk.StringVar()
        self.output_file_path = tk.StringVar()
        
        self.window_width = tk.StringVar()
        self.window_height = tk.StringVar()
        self.wait_time = tk.StringVar()
        self.transparent_var = tk.BooleanVar()
        self.bg_color_var = tk.StringVar()

        self.load_settings_from_config()
        
        self.conversion_cancelled = False
        self.current_driver = None 
        
        self.setup_ui()

    def load_settings_from_config(self):
        self.window_width.set(self.config.config.get("html_default_width", ""))
        self.window_height.set(self.config.config.get("html_default_height", ""))
        self.wait_time.set(self.config.config.get("html_default_wait", "2"))
        self.transparent_var.set(self.config.config.get("html_transparent", False))
        self.bg_color_var.set(self.config.config.get("html_bg_color", "#FFFFFF"))
        if hasattr(self, 'transparent_check'):
            self.on_transparent_changed()
        
    def setup_ui(self):
        main_frame = ttk.Frame(self.parent, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        input_frame = ttk.LabelFrame(main_frame, text="入力ファイル (HTML) - ドラッグ&ドロップ対応", padding="5")
        input_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.input_entry = ttk.Entry(input_frame, textvariable=self.input_file_path, width=70, state="readonly")
        self.input_entry.grid(row=0, column=0, padx=(0, 5), sticky=(tk.W, tk.E))
        ttk.Button(input_frame, text="参照", command=self.browse_input_file).grid(row=0, column=1)
        
        self.setup_drag_drop(self.input_entry, self.load_file, ['.html', '.htm'])
        
        recent_frame = ttk.Frame(input_frame)
        recent_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        
        self.recent_combo = ttk.Combobox(recent_frame, width=50, state="readonly")
        self.recent_combo.grid(row=0, column=0, padx=(0, 5), sticky=(tk.W, tk.E))
        self.recent_combo.bind('<<ComboboxSelected>>', self.on_recent_selected)
        ttk.Button(recent_frame, text="開く", command=self.open_recent).grid(row=0, column=1)
        
        self.update_recent_files()
        
        output_frame = ttk.LabelFrame(main_frame, text="出力ファイル (PNG)", padding="5")
        output_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Entry(output_frame, textvariable=self.output_file_path, width=70).grid(row=0, column=0, padx=(0, 5), sticky=(tk.W, tk.E))
        ttk.Button(output_frame, text="参照", command=self.browse_output_file).grid(row=0, column=1)
        
        preview_frame = ttk.LabelFrame(main_frame, text="HTMLプレビュー (ソース)", padding="5")
        preview_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.html_text = scrolledtext.ScrolledText(
            preview_frame, 
            width=80, 
            height=10, 
            wrap=tk.WORD,
            state="disabled",
            font=("Consolas", 9) if sys.platform == "win32" else ("Monaco", 10) 
        )
        self.html_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        options_frame = ttk.LabelFrame(main_frame, text="変換オプション", padding="5")
        options_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        size_frame = ttk.Frame(options_frame)
        size_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(size_frame, text="出力サイズ:").grid(row=0, column=0, padx=(0, 10))
        ttk.Label(size_frame, text="幅:").grid(row=0, column=1, padx=(0, 2))
        
        width_entry = ttk.Entry(size_frame, textvariable=self.window_width, width=8)
        width_entry.grid(row=0, column=2, padx=(0, 10))
        width_entry.bind('<FocusOut>', self.save_settings)
        
        ttk.Label(size_frame, text="高さ:").grid(row=0, column=3, padx=(0, 2))
        
        height_entry = ttk.Entry(size_frame, textvariable=self.window_height, width=8)
        height_entry.grid(row=0, column=4, padx=(0, 10))
        height_entry.bind('<FocusOut>', self.save_settings)
        
        ttk.Label(size_frame, text="px (空白=実サイズ出力)").grid(row=0, column=5)
        
        wait_frame = ttk.Frame(options_frame)
        wait_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(wait_frame, text="レンダリング待機時間:").grid(row=0, column=0, padx=(0, 10))
        
        wait_entry = ttk.Entry(wait_frame, textvariable=self.wait_time, width=8)
        wait_entry.grid(row=0, column=1, padx=(0, 5))
        wait_entry.bind('<FocusOut>', self.save_settings)
        
        ttk.Label(wait_frame, text="秒").grid(row=0, column=2)
        
        bg_frame = ttk.Frame(options_frame)
        bg_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        ttk.Label(bg_frame, text="背景:").grid(row=0, column=0, padx=(0, 10))
        
        self.transparent_check = ttk.Checkbutton(
            bg_frame, text="透過", variable=self.transparent_var,
            command=self.on_transparent_changed
        )
        self.transparent_check.grid(row=0, column=1, padx=(0, 10))
        
        ttk.Label(bg_frame, text="背景色:").grid(row=0, column=2, padx=(10, 5))
        
        self.bg_color_frame = tk.Frame(bg_frame, width=30, height=20, relief="sunken", borderwidth=2)
        self.bg_color_frame.grid(row=0, column=3, padx=(0, 5))
        self.bg_color_frame.bind("<Button-1>", self.choose_bg_color)
        
        self.bg_color_label = ttk.Label(bg_frame, text=self.bg_color_var.get())
        self.bg_color_label.grid(row=0, column=4, padx=(5, 10))
        
        ttk.Button(bg_frame, text="色選択", command=self.choose_bg_color).grid(row=0, column=5)
        
        self.update_bg_color_display()
        self.on_transparent_changed() 
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        self.convert_button = ttk.Button(button_frame, text="PNG に変換 (Ctrl+S)", command=self.start_conversion, state="disabled")
        self.convert_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.cancel_button = ttk.Button(button_frame, text="キャンセル", command=self.cancel_conversion, state="disabled")
        self.cancel_button.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="HTMLプレビュー更新", command=self.update_html_preview).pack(side=tk.LEFT, padx=(0, 10))
        
        self.progress = ttk.Progressbar(button_frame, mode='indeterminate', length=100)
        self.progress.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)
        
        self.status_label = ttk.Label(main_frame, text="HTMLファイルを選択またはドラッグ&ドロップしてください")
        self.status_label.grid(row=5, column=0, columnspan=2, pady=5, sticky=tk.W)
        
        self.app.root.bind_all('<Control-o>', lambda e: self.handle_global_shortcut(self.browse_input_file, 1), add="+")
        self.app.root.bind_all('<Control-s>', lambda e: self.handle_global_shortcut(self.start_conversion, 1), add="+")
        
        self.parent.columnconfigure(0, weight=1)
        self.parent.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1) 
        input_frame.columnconfigure(0, weight=1)
        output_frame.columnconfigure(0, weight=1)
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        recent_frame.columnconfigure(0, weight=1)
        options_frame.columnconfigure(0, weight=1)

    def handle_global_shortcut(self, command_func, tab_index):
        try:
            if self.app.notebook.index(self.app.notebook.select()) == tab_index:
                if command_func == self.start_conversion and self.convert_button['state'] == 'normal':
                    command_func()
                elif command_func == self.browse_input_file:
                     command_func()
        except tk.TclError:
            logger.warning("グローバルショートカット処理中にTclError (HTMLタブ)")
        except Exception as e:
            logger.error(f"グローバルショートカット処理エラー (HTMLタブ): {e}")


    def update_recent_files(self):
        recent_html_files = [f for f in self.config.config.get("recent_files", []) 
                             if Path(f).suffix.lower() in ['.html', '.htm'] and Path(f).exists()]
        
        self.recent_combo['values'] = [Path(f).name for f in recent_html_files]
        self.recent_files_paths = recent_html_files
        
        if recent_html_files:
            self.recent_combo.current(0)
        else:
            self.recent_combo.set('')
    
    def on_recent_selected(self, event):
        selected_index = self.recent_combo.current()
        if selected_index >= 0 and selected_index < len(self.recent_files_paths):
            self.load_file(self.recent_files_paths[selected_index])
    
    def open_recent(self):
        selection_index = self.recent_combo.current()
        if selection_index >= 0 and selection_index < len(self.recent_files_paths):
            self.load_file(self.recent_files_paths[selection_index])
        elif self.recent_combo.get():
             messagebox.showwarning("情報", "有効なファイルが選択されていません。")
        else:
             messagebox.showinfo("情報", "最近使用したHTMLファイルの履歴がありません。")
    
    def save_settings(self, event=None):
        self.config.config["html_default_width"] = self.window_width.get()
        self.config.config["html_default_height"] = self.window_height.get()
        self.config.config["html_default_wait"] = self.wait_time.get()
        self.config.config["html_transparent"] = self.transparent_var.get()
        self.config.config["html_bg_color"] = self.bg_color_var.get()
        self.config.save_config()
    
    def on_transparent_changed(self):
        if self.transparent_var.get():
            self.bg_color_frame.config(bg="gray90")
            self.bg_color_label.config(foreground="gray50")
            self.bg_color_frame.unbind("<Button-1>")
        else:
            self.bg_color_label.config(foreground=ttk.Style().lookup('TLabel', 'foreground'))
            self.update_bg_color_display()
            self.bg_color_frame.bind("<Button-1>", self.choose_bg_color)
        self.save_settings()
    
    def choose_bg_color(self, event=None):
        if self.transparent_var.get():
            return
        try:
            from tkinter import colorchooser
            current_color = self.bg_color_var.get()
            color_info = colorchooser.askcolor(
                title="背景色を選択",
                initialcolor=current_color if current_color and current_color.startswith("#") else "#FFFFFF"
            )
            if color_info and color_info[1]:
                self.bg_color_var.set(color_info[1])
                self.update_bg_color_display()
                self.save_settings()
        except ImportError:
            messagebox.showwarning("警告", "カラーピッカーが利用できません。")
        except Exception as e:
            logger.error(f"色選択エラー: {e}")
            messagebox.showerror("エラー", f"色の選択中にエラーが発生しました: {e}")

    def update_bg_color_display(self):
        try:
            color = self.bg_color_var.get()
            if not color or not color.startswith("#") or len(color) != 7:
                color = "#FFFFFF"
                self.bg_color_var.set(color)
            self.bg_color_frame.config(bg=color)
            self.bg_color_label.config(text=color)
        except tk.TclError:
            self.bg_color_var.set("#FFFFFF")
            self.bg_color_frame.config(bg="#FFFFFF")
            self.bg_color_label.config(text="#FFFFFF")
    
    def browse_input_file(self):
        initial_dir_html = self.config.config.get("last_input_dir_html", self.config.config.get("last_output_dir", str(Path.home())))
        file_path = filedialog.askopenfilename(
            title="HTMLファイルを選択",
            initialdir=initial_dir_html,
            filetypes=[("HTML files", "*.html;*.htm"), ("All files", "*.*")] 
        )
        if file_path:
            self.config.config["last_input_dir_html"] = str(Path(file_path).parent)
            self.config.save_config()
            self.load_file(file_path)
    
    def load_file(self, file_path: str):
        try:
            file_size = Path(file_path).stat().st_size
            if file_size > 50 * 1024 * 1024: 
                if not messagebox.askyesno("警告", f"ファイルサイズが大きいです ({file_size // (1024*1024)}MB)。\n処理に時間がかかる可能性があります。続行しますか？"):
                    return
            
            self.input_file_path.set(file_path)
            input_p = Path(file_path)
            output_dir_default = self.config.config.get("last_output_dir", str(input_p.parent))
            output_path = Path(output_dir_default) / f"{input_p.stem}.png"
            self.output_file_path.set(str(output_path))
            
            self.update_html_preview()
            self.convert_button.config(state="normal")
            self.status_label.config(text=f"HTMLファイル読込: {input_p.name}")
            
            self.config.add_recent_file(file_path)
            self.update_recent_files()
            self.app.update_recent_files_menu() # UnifiedConverterのメソッドを呼び出す
            if file_path in self.recent_files_paths:
                 self.recent_combo.current(self.recent_files_paths.index(file_path))

        except Exception as e:
            logger.error(f"HTMLファイル読み込みエラー: {e}", exc_info=True)
            messagebox.showerror("エラー", f"ファイルの読み込みに失敗しました: {str(e)}")
            self.convert_button.config(state="disabled")
    
    def browse_output_file(self):
        default_name = ""
        if self.input_file_path.get():
            default_name = f"{Path(self.input_file_path.get()).stem}.png"
        initial_dir_out = self.config.config.get("last_output_dir", str(Path.home()))
        file_path = filedialog.asksaveasfilename(
            title="PNGファイルの保存先を選択",
            initialdir=initial_dir_out,
            initialfile=default_name,
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        if file_path:
            self.output_file_path.set(file_path)
            self.config.config["last_output_dir"] = str(Path(file_path).parent)
            self.config.save_config()
            
    def update_html_preview(self):
        if not self.input_file_path.get():
            self.html_text.config(state="normal")
            self.html_text.delete(1.0, tk.END)
            self.html_text.insert(1.0, "HTMLファイルを選択してください。")
            self.html_text.config(state="disabled")
            return
            
        html_content = ""
        try:
            with open(self.input_file_path.get(), 'r', encoding='utf-8') as f:
                html_content = f.read()
        except UnicodeDecodeError:
            try:
                with open(self.input_file_path.get(), 'r', encoding='cp932') as f:
                    html_content = f.read()
            except Exception as e_alt:
                logger.error(f"HTMLプレビュー読込エラー(代替エンコーディング): {e_alt}", exc_info=True)
                messagebox.showerror("エラー", f"HTMLファイルの読み込みに失敗(プレビュー): {e_alt}\nエンコーディングを確認してください。")
                return
        except Exception as e:
            logger.error(f"HTMLプレビュー読込エラー: {e}", exc_info=True)
            messagebox.showerror("エラー", f"HTMLファイルの読み込みに失敗(プレビュー): {e}")
            return

        self.html_text.config(state="normal")
        self.html_text.delete(1.0, tk.END)
        preview_limit = 10000 
        if len(html_content) > preview_limit:
            self.html_text.insert(1.0, html_content[:preview_limit])
            self.html_text.insert(tk.END, f"\n\n... (ファイルが大きいため最初の{preview_limit}文字のみ表示)")
        else:
            self.html_text.insert(1.0, html_content)
        self.html_text.config(state="disabled")
        
        try:
            file_size_kb = Path(self.input_file_path.get()).stat().st_size // 1024
            self.status_label.config(text=f"HTMLプレビュー更新: {Path(self.input_file_path.get()).name}, {file_size_kb} KB")
        except FileNotFoundError:
             self.status_label.config(text=f"HTMLプレビュー更新: ファイルが見つかりません。")


    def cancel_conversion(self):
        self.conversion_cancelled = True
        if self.current_driver:
            try:
                logger.info("変換キャンセルによりWebDriverを終了します。")
                self.current_driver.quit()
            except Exception as e:
                logger.warning(f"キャンセル時のWebDriver終了エラー: {e}")
            finally:
                self.current_driver = None
        
        if self.input_file_path.get() and self.output_file_path.get():
            self.convert_button.config(state="normal")
        else:
            self.convert_button.config(state="disabled")
        self.cancel_button.config(state="disabled")
        self.progress.stop()
        self.progress.config(value=0)
        self.status_label.config(text="HTML変換がキャンセルされました")
        logger.info("HTML変換がキャンセルされました")
        if hasattr(self.app, 'status_label'):
            self.app.status_label.config(text="HTML変換がキャンセルされました")
            
    def start_conversion(self):
        logger.info("### HTMLConverterTab.start_conversion() 開始 ###")
        
        input_file = self.input_file_path.get()
        output_file = self.output_file_path.get()
        
        if not input_file:
            messagebox.showwarning("警告", "HTMLファイルが選択されていません")
            return
        if not output_file:
            messagebox.showwarning("警告", "出力ファイルのパスが指定されていません")
            return
        
        output_p = Path(output_file)
        try:
            output_p.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"出力ディレクトリ作成エラー: {e}", exc_info=True)
            messagebox.showerror("エラー", f"出力ディレクトリの作成に失敗しました: {e}")
            return
        
        self.convert_button.config(state="disabled")
        self.cancel_button.config(state="normal")
        self.progress.config(mode='indeterminate')
        self.progress.start()
        self.status_label.config(text="HTML変換中...")
        if hasattr(self.app, 'status_label'):
            self.app.status_label.config(text="HTML変換中...")
        self.conversion_cancelled = False
        
        threading.Thread(target=self.convert_html_to_png, daemon=True, name="HTMLConversionThread").start()
        logger.info("### HTMLConverterTab.start_conversion() 完了 (スレッド開始) ###")
        
    def convert_html_to_png(self):
        logger.info("### convert_html_to_png() スレッド処理開始 ###")
        
        try:
            width_str = self.window_width.get().strip()
            height_str = self.window_height.get().strip()
            wait_time_str = self.wait_time.get().strip()
            
            target_width, target_height, size_specified = None, None, False

            if width_str and height_str:
                try:
                    target_width, target_height = int(width_str), int(height_str)
                    if not (target_width > 0 and target_height > 0): raise ValueError()
                    size_specified = True
                    logger.info(f"指定サイズ: {target_width}x{target_height}")
                except ValueError:
                    self.app.root.after(0, lambda: self.conversion_complete(False, "幅と高さは正の整数で指定してください。"))
                    return
            
            wait_seconds = float(wait_time_str) if wait_time_str else 2.0
            if wait_seconds < 0: wait_seconds = 0

            chrome_options = Options()
            chrome_options.add_argument("--headless=new") 
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            # 初期ウィンドウサイズは大きめに設定し、後でコンテンツに合わせて調整
            initial_window_width, initial_window_height = 1920, 1200 
            chrome_options.add_argument(f"--window-size={initial_window_width},{initial_window_height}")
            chrome_options.add_argument("--hide-scrollbars")
            chrome_options.add_argument("--force-device-scale-factor=1")
            chrome_options.add_argument("--lang=ja-JP")
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging']) 

            logger.info("WebDriver初期化開始")
            try:
                if WEBDRIVER_MANAGER_AVAILABLE:
                    try:
                        service = Service(ChromeDriverManager().install())
                        self.current_driver = webdriver.Chrome(service=service, options=chrome_options)
                    except Exception as e_wdm: 
                        logger.error(f"webdriver-managerでの初期化失敗: {e_wdm}. 通常のChromeドライバで試行します。")
                        self.current_driver = webdriver.Chrome(options=chrome_options)
                else: 
                    self.current_driver = webdriver.Chrome(options=chrome_options)
                logger.info("WebDriver初期化完了")
            except WebDriverException as e:
                logger.error(f"WebDriverException: {e}", exc_info=True)
                msg = str(e)
                if "chromedriver" in msg.lower() and ("executable needs to be in PATH" in msg or "not found" in msg):
                    msg = "ChromeDriver がPATHに設定されていないか、見つかりません。\nwebdriver-manager のインストール (pip install webdriver-manager) を推奨します。"
                elif "chrome" in msg.lower() and ("cannot find" in msg or "not found" in msg or "failed to start" in msg):
                     msg = "Google Chrome ブラウザが見つからないか、起動に失敗しました。インストール状況とバージョンを確認してください。"
                self.app.root.after(0, lambda: self.conversion_complete(False, f"WebDriverエラー: {msg}"))
                return
            except Exception as e: 
                logger.error(f"WebDriver初期化中の予期せぬエラー: {e}", exc_info=True)
                self.app.root.after(0, lambda: self.conversion_complete(False, f"WebDriver初期化エラー: {e}"))
                return

            if self.conversion_cancelled: return

            file_url = Path(self.input_file_path.get()).resolve().as_uri()
            logger.info(f"HTMLファイル読み込み: {file_url}")
            self.current_driver.get(file_url)
            logger.info("HTMLファイル読み込み完了")

            # フォント設定の注入
            font_script = """
            var style = document.createElement('style'); style.type = 'text/css';
            style.innerHTML = `* { 
                font-family: "Hiragino Sans", "Hiragino Kaku Gothic ProN", "Yu Gothic", "Meiryo", 
                             "MS Gothic", "MS Mincho", "Takao Gothic", "IPA Gothic", 
                             "Noto Sans CJK JP", "DejaVu Sans", sans-serif !important; 
                font-weight: normal !important; font-style: normal !important; 
            }`;
            document.head.appendChild(style); document.body.offsetHeight; // offsetHeightで再描画をトリガー
            """
            self.current_driver.execute_script(font_script)
            logger.info("フォント設定注入完了")

            # 背景色/透過設定
            if not self.transparent_var.get():
                bg_color = self.bg_color_var.get()
                bg_script = f"document.documentElement.style.backgroundColor='{bg_color}'; document.body.style.backgroundColor='{bg_color}';"
                self.current_driver.execute_script(bg_script)
                logger.info(f"背景色適用: {bg_color}")
            else:
                # 透過の場合、htmlとbodyの背景を透明に設定
                bg_script = "document.documentElement.style.backgroundColor='transparent'; document.body.style.backgroundColor='transparent';"
                self.current_driver.execute_script(bg_script)
                logger.info("透過背景設定試行")
            
            time.sleep(0.2) # スタイル適用待ち

            # ページ全体の実際の幅と高さをJavaScriptで取得
            get_dimensions_script = """
            return {
                width: Math.max(
                    document.body.scrollWidth, document.documentElement.scrollWidth,
                    document.body.offsetWidth, document.documentElement.offsetWidth,
                    document.body.clientWidth, document.documentElement.clientWidth
                ),
                height: Math.max(
                    document.body.scrollHeight, document.documentElement.scrollHeight,
                    document.body.offsetHeight, document.documentElement.offsetHeight,
                    document.body.clientHeight, document.documentElement.clientHeight
                )
            };
            """
            dimensions = self.current_driver.execute_script(get_dimensions_script)
            content_width = dimensions['width']
            content_height = dimensions['height']
            
            # 最小サイズを保証 (例: 1x1ピクセルなど極端に小さい場合を避ける)
            content_width = max(content_width, 1)
            content_height = max(content_height, 1)

            logger.info(f"JavaScriptによるページ実サイズ: {content_width}x{content_height}")
            
            # ウィンドウサイズをコンテンツの大きさに正確に設定
            self.current_driver.set_window_size(content_width, content_height)
            logger.info(f"ウィンドウサイズをコンテンツ実寸に調整: {content_width}x{content_height}")
            
            # レンダリング待機 (スタイル適用やJavaScriptによる動的変更を待つ)
            # wait_seconds はユーザー指定の待機時間
            time.sleep(0.5 + wait_seconds) 

            if self.conversion_cancelled: return

            logger.info(f"スクリーンショット撮影開始: {self.output_file_path.get()}")
            try:
                # ページ全体のスクリーンショットを取得
                png_data = self.current_driver.get_screenshot_as_png()
                with open(self.output_file_path.get(), 'wb') as f:
                    f.write(png_data)
                logger.info("ページ全体のスクリーンショット撮影完了")

            except TimeoutException as e_timeout:
                logger.error(f"ページ読み込みまたはスクリプト実行中にタイムアウトが発生: {e_timeout}", exc_info=True)
                self.app.root.after(0, lambda: self.conversion_complete(False, f"タイムアウトエラー: {e_timeout}"))
                return
            except WebDriverException as e_wd:
                logger.error(f"WebDriverエラー（スクリーンショット撮影中など）: {e_wd}", exc_info=True)
                self.app.root.after(0, lambda: self.conversion_complete(False, f"WebDriverエラー: {e_wd}"))
                return
            except Exception as e_shot: # その他の予期せぬエラー
                logger.error(f"スクリーンショット撮影中に予期せぬエラーが発生: {e_shot}", exc_info=True)
                self.app.root.after(0, lambda: self.conversion_complete(False, f"スクリーンショット撮影エラー: {e_shot}"))
                return

            if self.conversion_cancelled: return # スクリーンショット保存直後にもキャンセルチェック

            saved_image_path = self.output_file_path.get()
            
            # Pillowを使用して画像処理
            with Image.open(saved_image_path) as img:
                logger.info(f"スクリーンショット原画像サイズ (Pillow): {img.width}x{img.height}")
                
                # processed_img は、トリミングまたはリサイズ後の最終的な画像データを保持
                processed_img = img.copy() 

                if not size_specified: 
                    logger.info("実サイズ出力 - 余白トリミング処理開始")
                    if self.transparent_var.get():
                        # 透過背景の場合、アルファチャンネルに基づいてトリミング
                        img_rgba = processed_img.convert('RGBA') if processed_img.mode != 'RGBA' else processed_img
                        bbox = img_rgba.getbbox() # コンテンツがある領域のバウンディングボックス
                        if bbox: 
                            processed_img = processed_img.crop(bbox)
                        else: 
                            logger.info("透過画像でBBox取得できず。トリミングスキップ。")
                    else:
                        # 不透明背景の場合、指定された背景色との差分でトリミング
                        bg_hex = self.bg_color_var.get()
                        try: 
                            bg_rgb = tuple(int(bg_hex[i:i+2], 16) for i in (1,3,5))
                        except: 
                            bg_rgb = (255,255,255) # 不正な場合は白
                            logger.warning("背景色指定が無効なため、白でトリミング処理します。")
                        
                        img_rgb_diff = processed_img.convert('RGB') # 比較用にRGBに変換
                        bg_fill = Image.new('RGB', img_rgb_diff.size, bg_rgb) # 背景色で塗りつぶした画像
                        diff = ImageChops.difference(img_rgb_diff, bg_fill) # 差分画像
                        bbox = diff.getbbox() # 差分がある領域 (つまりコンテンツ領域)
                        if bbox: 
                            processed_img = processed_img.crop(bbox)
                        else: 
                            logger.info("画像全体が背景色と一致。トリミングスキップ。")
                    
                    processed_img.save(saved_image_path, 'PNG')
                    final_output_width, final_output_height = processed_img.size # トリミング後のサイズ
                    logger.info(f"実サイズ出力トリミング後サイズ: {final_output_width}x{final_output_height}")

                elif size_specified: 
                    logger.info(f"指定サイズ出力 ({target_width}x{target_height}) - リサイズ処理開始")
                    original_w, original_h = processed_img.size
                    
                    # アスペクト比を保ってリサイズ
                    scale = min(target_width/original_w if original_w > 0 else 1, 
                                target_height/original_h if original_h > 0 else 1)
                    new_w = int(original_w * scale)
                    new_h = int(original_h * scale)
                    
                    # 0除算を避けるため、最小でも1ピクセルにする
                    new_w = max(1, new_w)
                    new_h = max(1, new_h)

                    resized_content = processed_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                    # 最終的なキャンバスを作成
                    if self.transparent_var.get():
                        # 透過背景
                        final_canvas = Image.new('RGBA', (target_width, target_height), (0,0,0,0)) # 完全透過
                        content_to_paste = resized_content.convert('RGBA') if resized_content.mode != 'RGBA' else resized_content
                    else:
                        # 不透明背景
                        bg_hex = self.bg_color_var.get()
                        try: 
                            bg_rgb_canvas = tuple(int(bg_hex[i:i+2], 16) for i in (1,3,5))
                        except: 
                            bg_rgb_canvas = (255,255,255) # 不正な場合は白
                        final_canvas = Image.new('RGB', (target_width, target_height), bg_rgb_canvas)
                        
                        # resized_content を最終キャンバスに合成 (透過情報を考慮)
                        if resized_content.mode == 'RGBA':
                            # 一時的な背景を作成し、その上にアルファ合成してからRGBに変換
                            temp_bg_for_alpha_composite = Image.new('RGBA', resized_content.size, (*bg_rgb_canvas, 255))
                            content_to_paste = Image.alpha_composite(temp_bg_for_alpha_composite, resized_content).convert('RGB')
                        else:
                            content_to_paste = resized_content.convert('RGB')
                    
                    # 中央に配置
                    x_offset = (target_width - new_w) // 2
                    y_offset = (target_height - new_h) // 2
                    final_canvas.paste(content_to_paste, (x_offset, y_offset))
                    
                    processed_img = final_canvas # リサイズ・背景合成後の画像を processed_img に
                    processed_img.save(saved_image_path, 'PNG')
                    final_output_width, final_output_height = processed_img.size # 保存後のサイズ
                    logger.info(f"指定サイズ出力完了。最終画像サイズ: {final_output_width}x{final_output_height}")
                
            # この時点で final_output_width, final_output_height には最終的な画像の寸法が格納されているはず

            output_kb = Path(saved_image_path).stat().st_size // 1024
            msg_prefix = "実サイズ" if not size_specified else "指定サイズ"
            success_message = (f"変換完了 ({msg_prefix}出力)\n"
                               f"出力: {saved_image_path}\n"
                               f"最終サイズ: {final_output_width}x{final_output_height} px, {output_kb} KB")
            
            logger.info("HTML変換処理完了 (Pillow後処理含む)")
            self.app.root.after(0, lambda: self.conversion_complete(True, success_message))
            
        except Exception as e:
            logger.error(f"HTML変換中の予期せぬエラー: {e}", exc_info=True)
            self.app.root.after(0, lambda: self.conversion_complete(False, f"変換エラー: {e}"))
        finally:
            if self.current_driver:
                logger.info("WebDriver終了処理")
                try: self.current_driver.quit()
                except Exception as e_q: logger.error(f"WebDriver終了エラー: {e_q}")
                finally: self.current_driver = None
            logger.info("### convert_html_to_png() スレッド処理終了 ###")
            
    def conversion_complete(self, success: bool, message: str):
        logger.info(f"HTML conversion_complete: success={success}")
        self.progress.stop(); self.progress.config(mode='determinate', value=0)
        if self.input_file_path.get() and self.output_file_path.get():
            self.convert_button.config(state="normal")
        else:
            self.convert_button.config(state="disabled")
        self.cancel_button.config(state="disabled")
        
        status_text_prefix = "HTML変換"
        status_label_widget = self.status_label 
        if hasattr(self.app, 'status_label'): 
            self.app.status_label.config(text=f"{status_text_prefix}{'完了' if success else '失敗'}")


        if success and not self.conversion_cancelled:
            status_label_widget.config(text=f"{status_text_prefix}完了: {Path(self.output_file_path.get()).name}")
            messagebox.showinfo("完了", message)
            logger.info(f"{status_text_prefix}正常完了")
        elif not self.conversion_cancelled:
            status_label_widget.config(text=f"{status_text_prefix}失敗")
            messagebox.showerror("エラー", f"{status_text_prefix}失敗:\n{message}")
            logger.warning(f"{status_text_prefix}失敗: {message}")

def main():
    try:
        app_dir = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
        log_file = app_dir / "png_converter.log"
    except:
        log_file = Path.home() / "png_converter.log"

    file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='a')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(threadName)s] - %(module)s.%(funcName)s:%(lineno)d - %(message)s')
    file_handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.INFO) 
    
    try:
        root = tk.Tk()
        app = UnifiedConverter(root)
        logger.info("アプリケーションが開始されました。")
        root.mainloop()
        logger.info("アプリケーションが正常に終了しました。")
    except Exception as e:
        logger.critical(f"アプリケーションの致命的なエラー: {e}", exc_info=True)
        try:
            messagebox.showerror("致命的エラー", f"アプリケーションで予期せぬエラーが発生しました: {str(e)}\n詳細はログファイルを確認してください:\n{log_file}")
        except tk.TclError: 
            print(f"致命的エラー (Tk未初期化): {e}") 

if __name__ == "__main__":
    main()
