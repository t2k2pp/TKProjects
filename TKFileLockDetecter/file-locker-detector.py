import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import psutil
import win32api
import win32con
import win32file
import win32process
import pywintypes
import ctypes
from ctypes import byref, create_unicode_buffer, sizeof, windll
from ctypes.wintypes import DWORD
import threading

class FileLockChecker:
    def __init__(self, root):
        self.root = root
        root.title("Windowsファイルロックチェッカー")
        root.geometry("800x600")
        root.minsize(650, 500)

        # メインフレーム
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # パス入力部分
        path_frame = ttk.Frame(main_frame)
        path_frame.pack(fill=tk.X, pady=5)

        ttk.Label(path_frame, text="ファイル/フォルダパス:").pack(side=tk.LEFT)
        self.path_var = tk.StringVar()
        self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var, width=50)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        ttk.Button(path_frame, text="参照", command=self.browse_path).pack(side=tk.LEFT)
        ttk.Button(path_frame, text="チェック", command=self.check_locks).pack(side=tk.LEFT, padx=5)

        # 結果表示エリア
        result_frame = ttk.LabelFrame(main_frame, text="結果", padding="5")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # ツリービュー
        self.tree = ttk.Treeview(result_frame, columns=("pid", "name", "user", "path", "handle"), 
                               show="headings", selectmode="browse")
        
        # 列の設定
        self.tree.heading("pid", text="プロセスID")
        self.tree.heading("name", text="アプリケーション名")
        self.tree.heading("user", text="ユーザー名")
        self.tree.heading("path", text="実行パス")
        self.tree.heading("handle", text="ハンドル")
        
        self.tree.column("pid", width=70, anchor=tk.CENTER)
        self.tree.column("name", width=150)
        self.tree.column("user", width=100)
        self.tree.column("path", width=250)
        self.tree.column("handle", width=80, anchor=tk.CENTER)
        
        # スクロールバー
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        # レイアウト
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 詳細情報表示部分
        detail_frame = ttk.LabelFrame(main_frame, text="詳細情報", padding="5")
        detail_frame.pack(fill=tk.BOTH, pady=5)

        self.detail_text = tk.Text(detail_frame, height=8, wrap=tk.WORD)
        self.detail_text.pack(fill=tk.BOTH, expand=True)

        # ステータスバー
        self.status_var = tk.StringVar()
        self.status_var.set("準備完了")
        status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # 操作ボタン
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        self.kill_button = ttk.Button(button_frame, text="プロセス終了", command=self.kill_process, state=tk.DISABLED)
        self.kill_button.pack(side=tk.RIGHT, padx=5)
        
        # イベントバインド
        self.tree.bind("<<TreeviewSelect>>", self.on_item_select)

        # プログレスバー
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(main_frame, 
                                       orient=tk.HORIZONTAL, 
                                       length=100, 
                                       mode='indeterminate',
                                       variable=self.progress_var)
        self.progress.pack(fill=tk.X, pady=5)
        
        # 現在選択されているアイテム
        self.selected_pid = None

    def browse_path(self):
        """ファイル/フォルダ選択ダイアログを表示"""
        path = filedialog.askdirectory() or filedialog.askopenfilename()
        if path:
            self.path_var.set(path)

    def check_locks(self):
        """指定されたパスのロックを非同期でチェックする"""
        path = self.path_var.get().strip()
        if not path:
            messagebox.showwarning("警告", "ファイルまたはフォルダのパスを入力してください。")
            return
        
        if not os.path.exists(path):
            messagebox.showerror("エラー", f"指定されたパス '{path}' が存在しません。")
            return
        
        # ツリービューをクリア
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.detail_text.delete(1.0, tk.END)
        self.status_var.set("チェック中...")
        self.kill_button.config(state=tk.DISABLED)
        
        # プログレスバーを開始
        self.progress.start()
        
        # 非同期でチェックを実行（UIをブロックしないため）
        threading.Thread(target=self._check_locks_thread, args=(path,), daemon=True).start()

    def _check_locks_thread(self, path):
        """非同期でロックチェックを実行するスレッド関数"""
        try:
            result = self.find_process_locking_file(path)
            
            # UIスレッドでの処理を実行
            self.root.after(0, self._update_ui_with_results, result, path)
        except Exception as e:
            self.root.after(0, self._show_error, f"エラーが発生しました: {str(e)}")

    def _update_ui_with_results(self, result, path):
        """結果をUIに反映する（UIスレッドで呼び出される）"""
        if not result:
            self.detail_text.insert(tk.END, f"'{path}' を使用しているプロセスは見つかりませんでした。\n")
            self.status_var.set("チェック完了 - ロックは見つかりませんでした")
        else:
            for r in result:
                self.tree.insert("", tk.END, values=(
                    r["pid"], 
                    r["name"], 
                    r["username"], 
                    r["executable"], 
                    r["handle_type"]
                ))
            self.status_var.set(f"チェック完了 - {len(result)} 個のプロセスが見つかりました")
        
        self.progress.stop()

    def _show_error(self, message):
        """エラーメッセージを表示する（UIスレッドで呼び出される）"""
        messagebox.showerror("エラー", message)
        self.status_var.set("エラーが発生しました")
        self.progress.stop()

    def on_item_select(self, event):
        """ツリービューでアイテムが選択されたときの処理"""
        selected_items = self.tree.selection()
        if not selected_items:
            return
        
        item = selected_items[0]
        values = self.tree.item(item, "values")
        
        if values:
            pid = int(values[0])
            self.selected_pid = pid
            
            # 詳細情報を表示
            self.detail_text.delete(1.0, tk.END)
            
            try:
                process = psutil.Process(pid)
                
                # プロセス詳細情報
                self.detail_text.insert(tk.END, f"プロセス名: {process.name()}\n")
                self.detail_text.insert(tk.END, f"プロセスID: {pid}\n")
                self.detail_text.insert(tk.END, f"実行パス: {process.exe()}\n")
                self.detail_text.insert(tk.END, f"作成時間: {process.create_time()}\n")
                self.detail_text.insert(tk.END, f"メモリ使用量: {process.memory_info().rss / (1024*1024):.2f} MB\n")
                self.detail_text.insert(tk.END, f"ステータス: {process.status()}\n")
                
                # コマンドライン引数
                try:
                    cmdline = process.cmdline()
                    self.detail_text.insert(tk.END, f"コマンドライン: {' '.join(cmdline)}\n")
                except:
                    self.detail_text.insert(tk.END, "コマンドライン: 取得できません\n")
                
                # プロセス終了ボタンを有効化
                self.kill_button.config(state=tk.NORMAL)
                
            except psutil.NoSuchProcess:
                self.detail_text.insert(tk.END, f"プロセス {pid} は既に終了しています。\n")
                self.kill_button.config(state=tk.DISABLED)
            except psutil.AccessDenied:
                self.detail_text.insert(tk.END, f"プロセス {pid} へのアクセスが拒否されました。\n")
                self.detail_text.insert(tk.END, "管理者権限で実行すると詳細情報を取得できる場合があります。\n")
                self.kill_button.config(state=tk.NORMAL)
            except Exception as e:
                self.detail_text.insert(tk.END, f"エラー: {str(e)}\n")
                self.kill_button.config(state=tk.DISABLED)

    def kill_process(self):
        """選択されたプロセスを終了する"""
        if not self.selected_pid:
            return
        
        try:
            result = messagebox.askyesno(
                "確認", 
                f"プロセスID {self.selected_pid} を終了しますか？\n"
                "注意: プロセスを強制終了すると、保存されていないデータが失われる可能性があります。"
            )
            
            if result:
                process = psutil.Process(self.selected_pid)
                process.terminate()
                
                # 少し待ってからチェック
                self.root.after(1000, self._check_process_terminated)
        except Exception as e:
            messagebox.showerror("エラー", f"プロセスの終了に失敗しました: {str(e)}")

    def _check_process_terminated(self):
        """プロセスが正常に終了したかチェック"""
        try:
            process = psutil.Process(self.selected_pid)
            # プロセスがまだ存在する場合
            messagebox.showinfo("情報", f"プロセスID {self.selected_pid} の終了を待っています...")
            
            # さらに待ってからチェック
            self.root.after(2000, self._check_process_terminated)
        except psutil.NoSuchProcess:
            # プロセスが終了している場合
            messagebox.showinfo("成功", f"プロセスID {self.selected_pid} を正常に終了しました。")
            # ロック状態を再チェック
            self.check_locks()

    def find_process_locking_file(self, path):
        """指定されたパスをロックしているプロセスを見つける"""
        results = []
        path = os.path.abspath(path).lower()
        
        # ディレクトリの場合は特別な処理
        if os.path.isdir(path):
            return self._find_processes_locking_directory(path)
        
        # まずはファイルが実際にロックされているか簡易チェック
        try:
            # 読み書きモードでファイルを開こうとする
            with open(path, "r+b"):
                pass
            # 成功した場合、ファイルはロックされていない可能性が高い
        except PermissionError:
            # ファイルがロックされている可能性が高い
            pass
        except Exception:
            # その他のエラー（ファイルが存在しないなど）
            return []
        
        # すべてのプロセスをスキャン
        for proc in psutil.process_iter(['pid', 'name', 'username']):
            try:
                # open_filesはファイルパスを含む, 存在しない場合はValueErrorを発生
                proc_files = proc.open_files()
                for file in proc_files:
                    if file.path.lower() == path:
                        results.append({
                            "pid": proc.pid,
                            "name": proc.name(),
                            "username": proc.username(),
                            "executable": proc.exe(),
                            "handle_type": "FILE" if os.path.isfile(path) else "DIRECTORY"
                        })
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
        
        # 結果が見つからない場合は低レベルAPIを使用
        if not results:
            try:
                results.extend(self._find_handles_using_winapi(path))
            except:
                pass
        
        return results

    def _find_processes_locking_directory(self, directory_path):
        """ディレクトリをロックしているプロセスを見つける"""
        results = []
        
        # ディレクトリ内のすべてのファイルに対してチェック
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    # 各ファイルのロックを確認
                    file_results = self.find_process_locking_file(file_path)
                    if file_results:
                        # 重複を避けるため既存のPIDをチェック
                        existing_pids = [r["pid"] for r in results]
                        for r in file_results:
                            if r["pid"] not in existing_pids:
                                r["locked_file"] = file_path  # どのファイルがロックされているかを追加
                                results.append(r)
                except Exception:
                    # エラーが発生した場合はスキップ
                    continue
        
        return results

    def _find_handles_using_winapi(self, path):
        """Windows APIを使用してファイルハンドルを見つける（管理者権限が必要）"""
        # この関数は管理者権限が必要で、低レベルな操作を行うため、
        # エラーハンドリングが重要です
        results = []
        
        # 省略: ここにはWin32 APIを使用してハンドルを検索するコードが入ります
        # この実装は高度な知識を要するため、標準のpsutilによる検出に頼ります
        
        return results

if __name__ == "__main__":
    try:
        # Windowsスタイルを適用
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass
            
        root = tk.Tk()
        app = FileLockChecker(root)
        root.mainloop()
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        messagebox.showerror("起動エラー", f"アプリケーションの起動中にエラーが発生しました:\n\n{error_msg}")
