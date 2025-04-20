import os
import sys
import re
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import importlib.util
import ast
import shutil
import time

class PyInstallerGuideApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PyInstaller Guide")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        # アプリケーションの状態を保持する変数
        self.python_file = tk.StringVar()
        self.icon_file = tk.StringVar()
        self.output_name = tk.StringVar()
        self.show_console = tk.BooleanVar(value=False)
        self.work_dir = ""
        self.output_dir = ""
        
        # 依存関係の辞書（ライブラリ名: チェック状態）
        self.dependencies = {}
        
        # よく使われるライブラリのリスト
        # OpenCV: cv2はopencv-pythonのインポート名なので両方追加
        self.common_libraries = {
            # 科学計算・データ分析
            "numpy": "科学計算の基本ライブラリ",
            "scipy": "高度な科学計算ライブラリ",
            "pandas": "データ分析ライブラリ",
            "matplotlib": "グラフ描画ライブラリ",
            "seaborn": "統計データ可視化ライブラリ",
            
            # 画像処理
            "pillow": "画像処理ライブラリ",
            "opencv-python": "コンピュータビジョンライブラリ (cv2)",
            "cv2": "OpenCVライブラリ (opencv-pythonと同じ)",
            
            # ゲーム開発
            "pygame": "ゲーム開発ライブラリ",
            "pyglet": "OpenGLベースのマルチメディアライブラリ",
            "arcade": "2Dゲーム開発ライブラリ",
            "panda3d": "3Dゲームエンジン",
            "pyopengl": "OpenGLバインディング",
            
            # Web関連
            "requests": "HTTP通信ライブラリ",
            "beautifulsoup4": "HTMLパーサライブラリ",
            "selenium": "ブラウザ自動化ライブラリ",
            "flask": "軽量Webフレームワーク",
            "django": "フルスタックWebフレームワーク",
            
            # データベース
            "sqlalchemy": "SQLデータベースライブラリ",
            "pymysql": "MySQLクライアント",
            "psycopg2": "PostgreSQLクライアント",
            "sqlite3": "SQLite3データベース",
            
            # GUI
            "pyqt5": "Qt5ベースのGUIライブラリ",
            "pyside2": "Qt5の別実装GUIライブラリ",
            "wxpython": "WxWidgetsベースのGUIライブラリ",
            "kivy": "マルチタッチアプリケーション開発フレームワーク",
            
            # AI・機械学習
            "tensorflow": "機械学習フレームワーク",
            "pytorch": "深層学習ライブラリ",
            "scikit-learn": "機械学習ライブラリ",
            "keras": "ニューラルネットワークAPI",
            "transformers": "自然言語処理モデル",
            "nltk": "自然言語処理ツールキット",
            "spacy": "自然言語処理ライブラリ",
            
            # 3D・VR
            "open3d": "3D処理ライブラリ",
            "trimesh": "3Dメッシュ操作ライブラリ",
            "pyrender": "3Dレンダリングライブラリ",
            "vtk": "可視化ツールキット",
            
            # オーディオ処理
            "pyaudio": "オーディオI/Oライブラリ",
            "librosa": "音楽・音声分析ライブラリ",
            "pydub": "オーディオ操作ライブラリ",
            
            # その他一般ライブラリ
            "tqdm": "プログレスバーライブラリ",
            "cryptography": "暗号化ライブラリ",
            "pyyaml": "YAML処理ライブラリ",
            "openpyxl": "Excel操作ライブラリ",
            "xlrd": "Excel読み込みライブラリ"
        }
        
        # UIの構築
        self.create_widgets()
    
    def create_widgets(self):
        # メインフレームの作成
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # ファイル選択セクション
        file_frame = ttk.LabelFrame(main_frame, text="ファイル設定", padding="10")
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Pythonファイル選択
        ttk.Label(file_frame, text="Pythonファイル:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(file_frame, textvariable=self.python_file, width=60).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="参照...", command=self.browse_python_file).grid(row=0, column=2, padx=5, pady=5)
        
        # アイコン選択
        ttk.Label(file_frame, text="アイコン:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(file_frame, textvariable=self.icon_file, width=60).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="参照...", command=self.browse_icon_file).grid(row=1, column=2, padx=5, pady=5)
        
        # 出力ファイル名
        ttk.Label(file_frame, text="出力ファイル名:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(file_frame, textvariable=self.output_name, width=60).grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky=tk.W+tk.E)
        
        # オプションセクション
        options_frame = ttk.LabelFrame(main_frame, text="オプション", padding="10")
        options_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # コンソール表示オプション
        ttk.Checkbutton(options_frame, text="コンソールウィンドウを表示する", variable=self.show_console).pack(anchor=tk.W, pady=5)
        
        # 依存関係セクション
        self.deps_frame = ttk.LabelFrame(main_frame, text="依存関係", padding="10")
        self.deps_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # スクロール可能な依存関係リスト
        self.deps_canvas = tk.Canvas(self.deps_frame)
        scrollbar = ttk.Scrollbar(self.deps_frame, orient="vertical", command=self.deps_canvas.yview)
        self.scrollable_frame = ttk.Frame(self.deps_canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.deps_canvas.configure(scrollregion=self.deps_canvas.bbox("all"))
        )
        
        self.deps_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.deps_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.deps_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 初期状態では依存関係リストは空
        ttk.Label(self.scrollable_frame, text="Pythonファイルを選択すると、依存関係が表示されます").grid(row=0, column=0, columnspan=2, padx=5, pady=5)
        
        # 実行ボタンセクション
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=10)
        
        ttk.Button(button_frame, text="EXEを作成", command=self.create_exe, width=20).pack(side=tk.RIGHT, padx=5)
    
    def browse_python_file(self):
        """Pythonファイルを選択するダイアログを表示"""
        filepath = filedialog.askopenfilename(
            title="Pythonファイルを選択",
            filetypes=[("Python Files", "*.py"), ("All Files", "*.*")]
        )
        if filepath:
            self.python_file.set(filepath)
            # デフォルトの出力ファイル名を設定
            filename = os.path.splitext(os.path.basename(filepath))[0]
            self.output_name.set(filename)
            # 依存関係を解析
            self.analyze_dependencies(filepath)
    
    def browse_icon_file(self):
        """アイコンファイルを選択するダイアログを表示"""
        filepath = filedialog.askopenfilename(
            title="アイコンファイルを選択",
            filetypes=[("Icon Files", "*.ico"), ("All Files", "*.*")]
        )
        if filepath:
            self.icon_file.set(filepath)
    
    def analyze_dependencies(self, filepath):
        """Pythonファイルの依存関係を解析"""
        # 既存のウィジェットをクリア
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        # 依存関係辞書をリセット
        self.dependencies = {}
        
        try:
            # ファイルを読み込む
            with open(filepath, 'r', encoding='utf-8') as file:
                source_code = file.read()
            
            # ASTを使用してimport文を解析
            tree = ast.parse(source_code)
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports.append(name.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module.split('.')[0])
            
            # 重複を削除
            imports = list(set(imports))
            
            # 標準ライブラリを除外（簡易的な処理）
            std_libs = sys.stdlib_module_names if hasattr(sys, 'stdlib_module_names') else []
            imports = [imp for imp in imports if imp not in std_libs]
            
            # OpenCV特殊処理: cv2が検出された場合、opencv-pythonも追加
            if 'cv2' in imports and 'opencv-python' not in imports:
                imports.append('opencv-python')
            
            # 依存関係の表示とチェックボックスの作成
            ttk.Label(self.scrollable_frame, text="検出された依存関係:").grid(row=0, column=0, columnspan=4, sticky=tk.W, pady=(0, 10))
            
            row = 1
            col = 0
            for imp in imports:
                self.dependencies[imp] = tk.BooleanVar(value=True)
                ttk.Checkbutton(self.scrollable_frame, text=imp, variable=self.dependencies[imp]).grid(row=row, column=col, sticky=tk.W, padx=10)
                col = (col + 1) % 4  # 2列表示のための列切り替え
                #if col == 0:
                #    row += 1
            
            # 列が途中で終わった場合、次の行に進める
            if col == 1:
                row += 1
            
            # 一般的なライブラリのセクション
            ttk.Label(self.scrollable_frame, text="一般的なライブラリ:").grid(row=row, column=0, columnspan=4, sticky=tk.W, pady=(20, 10))
            row += 1
            
            col = 0
            for lib, desc in self.common_libraries.items():
                if lib not in self.dependencies:  # まだリストにない場合のみ追加
                    self.dependencies[lib] = tk.BooleanVar(value=False)
                    cb_text = f"{lib}" if col == 0 else f"{lib}"  # 説明は省略して2列に
                    cb = ttk.Checkbutton(self.scrollable_frame, text=cb_text, variable=self.dependencies[lib])
                    cb.grid(row=row, column=col, sticky=tk.W, padx=10)
                    
                    # ツールチップの実装
                    tooltip_text = desc
                    
                    # ホバー時の説明表示機能
                    self.current_tooltip = None  # 現在表示されているツールチップを管理

                    def show_tooltip(event, tooltip_text=tooltip_text, widget=cb):
                        if self.current_tooltip:  # 既存のツールチップを非表示
                            self.current_tooltip.destroy()
                            self.current_tooltip = None
                        tooltip = tk.Toplevel(self.root)
                        tooltip.wm_overrideredirect(True)
                        tooltip.geometry(f"+{event.x_root + 15}+{event.y_root + 10}")
                        tooltip.wm_attributes("-topmost", True)
                        label = ttk.Label(tooltip, text=tooltip_text, background="#FFFFCC", relief="solid", borderwidth=1)
                        label.pack()
                        self.current_tooltip = tooltip  # 現在のツールチップを更新

                    def hide_tooltip(event, widget=cb):
                        if self.current_tooltip:  # 現在のツールチップを確実に非表示
                            self.current_tooltip.destroy()
                            self.current_tooltip = None
                    
                    cb.bind("<Enter>", show_tooltip)
                    cb.bind("<Leave>", hide_tooltip)
                    
                    col = (col + 1) % 4
                    if col == 0:
                        row += 1
            
        except Exception as e:
            ttk.Label(self.scrollable_frame, text=f"依存関係の解析中にエラーが発生しました: {str(e)}").grid(row=0, column=0, padx=5, pady=5)
    
    def prepare_work_dir(self):
        """作業ディレクトリを準備"""
        # Workディレクトリがなければ作成
        work_base_dir = os.path.join(os.path.dirname(self.python_file.get()), "Work")
        os.makedirs(work_base_dir, exist_ok=True)
        
        # アプリ名のサブディレクトリを作成
        app_name = self.output_name.get() or os.path.splitext(os.path.basename(self.python_file.get()))[0]
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        work_dir = os.path.join(work_base_dir, f"{app_name}_{timestamp}")
        os.makedirs(work_dir, exist_ok=True)
        
        return work_dir
    
    def create_exe(self):
        """PyInstallerを使用してEXEを作成"""
        # 入力チェック
        if not self.python_file.get():
            messagebox.showerror("エラー", "Pythonファイルを選択してください")
            return
        
        # 作業ディレクトリの準備
        self.work_dir = self.prepare_work_dir()
        
        # PyInstallerコマンドの構築
        cmd = ["pyinstaller", "--onefile", "--workpath", os.path.join(self.work_dir, "build"), 
               "--distpath", os.path.join(self.work_dir, "dist"), 
               "--specpath", self.work_dir]
        
        # コンソールウィンドウ表示オプション
        if not self.show_console.get():
            cmd.append("--noconsole")
        
        # アイコン指定
        if self.icon_file.get():
            cmd.extend(["--icon", self.icon_file.get()])
        
        # 出力名指定
        if self.output_name.get():
            cmd.extend(["--name", self.output_name.get()])
        
        # 依存関係の追加
        hidden_imports = []
        for lib, checked in self.dependencies.items():
            if checked.get():
                # cv2とopencv-pythonが両方含まれている場合は一方のみ追加
                if lib == "cv2" and "opencv-python" in self.dependencies and self.dependencies["opencv-python"].get():
                    continue
                if lib == "opencv-python" and "cv2" in self.dependencies and self.dependencies["cv2"].get():
                    continue
                hidden_imports.append(lib)
        
        for lib in hidden_imports:
            cmd.extend(["--hidden-import", lib])
        
        # Pythonファイルの追加
        cmd.append(self.python_file.get())
        
        # 出力ディレクトリを保存
        self.output_dir = os.path.join(self.work_dir, "dist")
        
        # 実行ボタンを無効化
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Button) and child["text"] == "EXEを作成":
                        child.config(state="disabled")
        
        # プログレスバーの表示
        progress_window = tk.Toplevel(self.root)
        progress_window.title("実行中...")
        progress_window.geometry("400x170")
        progress_window.transient(self.root)
        progress_window.grab_set()
        progress_window.resizable(False, False)
        
        ttk.Label(progress_window, text="PyInstallerを実行中...").pack(pady=(20, 5))
        ttk.Label(progress_window, text=f"作業ディレクトリ: {self.work_dir}").pack(pady=5)
        progress = ttk.Progressbar(progress_window, mode="indeterminate")
        progress.pack(fill=tk.X, padx=20, pady=10)
        progress.start()
        
        # ログ表示領域
        log_frame = ttk.Frame(progress_window)
        log_frame.pack(fill=tk.X, padx=20, pady=5)
        ttk.Label(log_frame, text="ステータス:").pack(side=tk.LEFT)
        self.status_label = ttk.Label(log_frame, text="初期化中...")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        # バックグラウンドスレッドでPyInstallerを実行
        self.thread = threading.Thread(target=self.run_pyinstaller, args=(cmd, progress_window))
        self.thread.daemon = True
        self.thread.start()
    
    def update_status(self, message):
        """ステータスラベルを更新"""
        def _update():
            if hasattr(self, 'status_label'):
                self.status_label.config(text=message)
        self.root.after(0, _update)
    
    def run_pyinstaller(self, cmd, progress_window):
        """バックグラウンドでPyInstallerを実行"""
        print(cmd)
        try:
            # ログファイルのパスを設定
            log_file = os.path.join(self.work_dir, "pyinstaller_log.txt")
            
            # コマンドを実行
            self.update_status("PyInstallerを開始...")
            with open(log_file, 'w', encoding='utf-8') as f:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=False,  # バイナリモードで読み取り
                    shell=False,
                    cwd=os.path.dirname(self.python_file.get())
                )
                
                while True:
                    try:
                        output_line = process.stdout.readline()
                        if not output_line and process.poll() is not None:
                            break
                        
                        if output_line:
                            # バイナリデータをデコード
                            try:
                                line = output_line.decode('utf-8')
                            except UnicodeDecodeError:
                                try:
                                    line = output_line.decode('cp932')  # Windows日本語
                                except UnicodeDecodeError:
                                    line = output_line.decode('ascii', errors='ignore')
                            
                            f.write(line)
                            f.flush()
                            print(line.strip())
                            self.update_status(line.strip()[:50] + ("..." if len(line) > 50 else ""))
                    except Exception as e:
                        print(f"出力の読み取り中にエラー: {str(e)}")
                        continue
                
                returncode = process.wait()
                if returncode == 0:
                    self.root.after(0, lambda: self.show_success_dialog(progress_window))
                else:
                    error_content = f"PyInstallerがエラーコード {returncode} で終了しました。\nログファイル: {log_file}"
                    self.root.after(0, lambda: self.show_error_dialog(error_content, progress_window))
                    
        except Exception as e:
            error_message = str(e)
            self.update_status("例外が発生しました")
            self.root.after(0, lambda m=error_message: self.show_error_dialog(m, progress_window))
    
    def show_success_dialog(self, progress_window):
        """成功ダイアログを表示"""
        progress_window.destroy()
        
        success_window = tk.Toplevel(self.root)
        success_window.title("成功")
        success_window.geometry("500x200")
        success_window.transient(self.root)
        success_window.grab_set()
        success_window.resizable(False, False)
        
        ttk.Label(success_window, text="EXEの作成に成功しました！", font=("", 12, "bold")).pack(pady=(20, 10))
        
        # 出力先情報
        info_frame = ttk.Frame(success_window)
        info_frame.pack(fill=tk.X, padx=20, pady=5)
        ttk.Label(info_frame, text="出力先フォルダ:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Label(info_frame, text=self.output_dir).grid(row=0, column=1, sticky=tk.W, pady=2)
        
        app_name = self.output_name.get() or os.path.splitext(os.path.basename(self.python_file.get()))[0]
        exe_path = os.path.join(self.output_dir, f"{app_name}.exe")
        ttk.Label(info_frame, text="EXEファイル:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Label(info_frame, text=exe_path).grid(row=1, column=1, sticky=tk.W, pady=2)
        
        button_frame = ttk.Frame(success_window)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="フォルダを開く", command=lambda: self.open_output_folder()).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="OK", command=success_window.destroy).pack(side=tk.LEFT, padx=10)
    
    def show_error_dialog(self, error_message, progress_window):
        """エラーダイアログを表示"""
        progress_window.destroy()
        
        error_window = tk.Toplevel(self.root)
        error_window.title("エラー")
        error_window.geometry("700x500")
        error_window.transient(self.root)
        error_window.grab_set()
        
        ttk.Label(error_window, text="EXEの作成中にエラーが発生しました:", font=("", 11, "bold")).pack(pady=(20, 10))
        
        # 作業ディレクトリ情報
        info_frame = ttk.Frame(error_window)
        info_frame.pack(fill=tk.X, padx=20, pady=5)
        ttk.Label(info_frame, text="作業ディレクトリ:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(info_frame, text=self.work_dir).grid(row=0, column=1, sticky=tk.W)
        
        # エラーメッセージを表示するテキストボックス
        error_frame = ttk.Frame(error_window)
        error_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        error_text = tk.Text(error_frame, wrap=tk.WORD, height=15)
        error_scrollbar = ttk.Scrollbar(error_frame, command=error_text.yview)
        error_text.configure(yscrollcommand=error_scrollbar.set)
        
        error_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        error_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        error_text.insert(tk.END, error_message)
        error_text.config(state="disabled")
        
        button_frame = ttk.Frame(error_window)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="作業フォルダを開く", command=lambda: self.open_folder(self.work_dir)).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="OK", command=error_window.destroy).pack(side=tk.LEFT, padx=10)
    
    def open_output_folder(self):
        """出力フォルダをエクスプローラーで開く"""
        self.open_folder(self.output_dir)
    
    def open_folder(self, folder_path):
        """指定されたフォルダをエクスプローラーで開く"""
        if folder_path and os.path.exists(folder_path):
            # OSに応じてフォルダを開くコマンドを実行
            if sys.platform == "win32":
                os.startfile(folder_path)
            elif sys.platform == "darwin":  # macOS
                subprocess.call(["open", folder_path])
            else:  # Linux
                subprocess.call(["xdg-open", folder_path])
        else:
            messagebox.showerror("エラー", f"フォルダが見つかりません: {folder_path}")


def main():
    # Tkinterウィンドウの初期化
    root = tk.Tk()
    app = PyInstallerGuideApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
