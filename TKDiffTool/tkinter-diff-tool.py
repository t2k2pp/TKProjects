import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from difflib import SequenceMatcher
import os

class DiffTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Tkinter Diff Tool")
        self.root.geometry("1200x700")
        
        # ファイルパス変数
        self.left_file_path = tk.StringVar()
        self.right_file_path = tk.StringVar()
        
        # 差分データ保存用
        self.diff_blocks = []
        self.current_diff_index = -1
        
        # レイアウト作成
        self.create_layout()
        
    def create_layout(self):
        # メインフレーム
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # ファイル選択部分 (上部)
        file_frame = ttk.Frame(main_frame)
        file_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 左側ファイル選択
        ttk.Label(file_frame, text="Left File:").grid(row=0, column=0, padx=(0, 5))
        ttk.Entry(file_frame, textvariable=self.left_file_path, width=50).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(file_frame, text="Browse", command=self.browse_left_file).grid(row=0, column=2, padx=(0, 10))
        
        # 右側ファイル選択
        ttk.Label(file_frame, text="Right File:").grid(row=0, column=3, padx=(10, 5))
        ttk.Entry(file_frame, textvariable=self.right_file_path, width=50).grid(row=0, column=4, padx=(0, 5))
        ttk.Button(file_frame, text="Browse", command=self.browse_right_file).grid(row=0, column=5)
        
        # 比較ボタン
        ttk.Button(file_frame, text="比較開始", command=self.compare_files, style="Compare.TButton").grid(row=0, column=6, padx=(20, 0))
        
        # 操作ボタンフレーム (中部)
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        # ナビゲーションボタン
        ttk.Button(button_frame, text="前の差分", command=self.prev_diff).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="次の差分", command=self.next_diff).pack(side=tk.LEFT, padx=(0, 20))
        
        # マージボタン
        ttk.Button(button_frame, text="→ 右へマージ", command=lambda: self.merge_diff("right")).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="← 左へマージ", command=lambda: self.merge_diff("left")).pack(side=tk.LEFT)
        
        # 差分情報ラベル
        self.diff_info_label = ttk.Label(button_frame, text="")
        self.diff_info_label.pack(side=tk.RIGHT)
        
        # テキストエリアフレーム (下部)
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左側のテキストウィジェット
        left_frame = ttk.LabelFrame(text_frame, text="Left File")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.left_text = tk.Text(left_frame, wrap=tk.NONE)
        self.left_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        left_scroll_y = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.left_text.yview)
        left_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.left_text.config(yscrollcommand=left_scroll_y.set)
        
        left_scroll_x = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=self.left_text.xview)
        left_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.left_text.config(xscrollcommand=left_scroll_x.set)
        
        # 右側のテキストウィジェット
        right_frame = ttk.LabelFrame(text_frame, text="Right File")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.right_text = tk.Text(right_frame, wrap=tk.NONE)
        self.right_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        right_scroll_y = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.right_text.yview)
        right_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.right_text.config(yscrollcommand=right_scroll_y.set)
        
        right_scroll_x = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=self.right_text.xview)
        right_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.right_text.config(xscrollcommand=right_scroll_x.set)
        
        # スタイル設定
        self.setup_styles()
        
        # テキストウィジェットの初期設定
        self.setup_text_widgets()
        
        # スクロール同期
        self.sync_scrolling()
    
    def setup_styles(self):
        # タグとスタイルの設定
        self.left_text.tag_configure("diff", background="#ffcccc")  # 差分行の背景色 (赤)
        self.right_text.tag_configure("diff", background="#ffcccc")  # 差分行の背景色 (赤)
        self.left_text.tag_configure("current", background="#ffff99")  # 現在選択中の差分 (黄色)
        self.right_text.tag_configure("current", background="#ffff99")  # 現在選択中の差分 (黄色)
        
        # ボタンスタイル
        style = ttk.Style()
        style.configure("Compare.TButton", font=("TkDefaultFont", 10, "bold"))
    
    def setup_text_widgets(self):
        # テキストウィジェットの設定 (行番号、フォントなど)
        font = ("Courier", 10)
        self.left_text.config(font=font)
        self.right_text.config(font=font)
        
    def sync_scrolling(self):
        # 垂直スクロールを同期させる
        def on_left_scroll(*args):
            self.right_text.yview_moveto(args[0])
        
        def on_right_scroll(*args):
            self.left_text.yview_moveto(args[0])
        
        # スクロールコマンドを上書き
        left_yscroll = self.left_text.cget("yscrollcommand")
        right_yscroll = self.right_text.cget("yscrollcommand")
        
        def left_scroll_callback(*args):
            left_yscroll(*args)
            on_left_scroll(args[0])
        
        def right_scroll_callback(*args):
            right_yscroll(*args)
            on_right_scroll(args[0])
        
        self.left_text.config(yscrollcommand=left_scroll_callback)
        self.right_text.config(yscrollcommand=right_scroll_callback)
    
    def browse_left_file(self):
        filename = filedialog.askopenfilename(title="左側ファイルを選択",
                                             filetypes=[("Text files", "*.txt"), 
                                                       ("Python files", "*.py"),
                                                       ("Markdown files", "*.md"),
                                                       ("All files", "*.*")])
        if filename:
            self.left_file_path.set(filename)
    
    def browse_right_file(self):
        filename = filedialog.askopenfilename(title="右側ファイルを選択",
                                             filetypes=[("Text files", "*.txt"), 
                                                       ("Python files", "*.py"),
                                                       ("Markdown files", "*.md"),
                                                       ("All files", "*.*")])
        if filename:
            self.right_file_path.set(filename)
    
    def compare_files(self):
        left_path = self.left_file_path.get()
        right_path = self.right_file_path.get()
        
        # ファイルパスのバリデーション
        if not left_path or not os.path.isfile(left_path):
            messagebox.showerror("エラー", "左側ファイルが指定されていないか、存在しません")
            return
        
        if not right_path or not os.path.isfile(right_path):
            messagebox.showerror("エラー", "右側ファイルが指定されていないか、存在しません")
            return
        
        try:
            # ファイル読み込み
            with open(left_path, 'r', encoding='utf-8') as f:
                left_content = f.read()
            
            with open(right_path, 'r', encoding='utf-8') as f:
                right_content = f.read()
            
            # テキストウィジェットをクリア
            self.left_text.delete(1.0, tk.END)
            self.right_text.delete(1.0, tk.END)
            
            # テキストウィジェットにコンテンツを挿入
            self.left_text.insert(tk.END, left_content)
            self.right_text.insert(tk.END, right_content)
            
            # 差分を検出して表示
            self.detect_and_highlight_diff(left_content, right_content)
            
        except Exception as e:
            messagebox.showerror("エラー", f"ファイル比較エラー: {str(e)}")
    
    def detect_and_highlight_diff(self, left_content, right_content):
        # タグをクリア
        self.left_text.tag_remove("diff", "1.0", tk.END)
        self.right_text.tag_remove("diff", "1.0", tk.END)
        self.left_text.tag_remove("current", "1.0", tk.END)
        self.right_text.tag_remove("current", "1.0", tk.END)
        
        # 差分ブロックリストをクリア
        self.diff_blocks = []
        self.current_diff_index = -1
        
        # 行ごとに分割
        left_lines = left_content.splitlines()
        right_lines = right_content.splitlines()
        
        # SequenceMatcherを使って差分を検出
        matcher = SequenceMatcher(None, left_lines, right_lines)
        
        left_index = 0
        right_index = 0
        
        # 差分を処理
        for op, i1, i2, j1, j2 in matcher.get_opcodes():
            if op != 'equal':  # 差分がある場合
                # 差分ブロック情報を保存
                diff_block = {
                    'left_start': left_index + i1 + 1,  # 行番号は1から始まる
                    'left_end': left_index + i2,
                    'right_start': right_index + j1 + 1,
                    'right_end': right_index + j2,
                    'op': op
                }
                self.diff_blocks.append(diff_block)
                
                # 差分にタグを付ける
                for i in range(i1, i2):
                    line_number = left_index + i + 1
                    start = f"{line_number}.0"
                    end = f"{line_number}.end"
                    self.left_text.tag_add("diff", start, end)
                
                for j in range(j1, j2):
                    line_number = right_index + j + 1
                    start = f"{line_number}.0"
                    end = f"{line_number}.end"
                    self.right_text.tag_add("diff", start, end)
        
        # 差分の数を表示
        diff_count = len(self.diff_blocks)
        self.diff_info_label.config(text=f"差分: {diff_count}箇所")
        
        # 最初の差分にフォーカス（あれば）
        if diff_count > 0:
            self.current_diff_index = 0
            self.highlight_current_diff()
    
    def highlight_current_diff(self):
        if not self.diff_blocks or self.current_diff_index < 0:
            return
        
        # 現在の差分ハイライトをクリア
        self.left_text.tag_remove("current", "1.0", tk.END)
        self.right_text.tag_remove("current", "1.0", tk.END)
        
        # 現在の差分を取得
        diff = self.diff_blocks[self.current_diff_index]
        
        # 左側の差分にハイライト
        for i in range(diff['left_start'], diff['left_end'] + 1):
            start = f"{i}.0"
            end = f"{i}.end"
            self.left_text.tag_add("current", start, end)
        
        # 右側の差分にハイライト
        for i in range(diff['right_start'], diff['right_end'] + 1):
            start = f"{i}.0"
            end = f"{i}.end"
            self.right_text.tag_add("current", start, end)
        
        # 差分が見えるようにスクロール
        self.left_text.see(f"{diff['left_start']}.0")
        self.right_text.see(f"{diff['right_start']}.0")
        
        # 差分情報を更新
        diff_count = len(self.diff_blocks)
        self.diff_info_label.config(text=f"差分: {self.current_diff_index + 1}/{diff_count}箇所")
    
    def next_diff(self):
        if not self.diff_blocks:
            return
        
        if self.current_diff_index < len(self.diff_blocks) - 1:
            self.current_diff_index += 1
            self.highlight_current_diff()
    
    def prev_diff(self):
        if not self.diff_blocks:
            return
        
        if self.current_diff_index > 0:
            self.current_diff_index -= 1
            self.highlight_current_diff()
    
    def merge_diff(self, direction):
        if not self.diff_blocks or self.current_diff_index < 0:
            return
        
        diff = self.diff_blocks[self.current_diff_index]
        
        if direction == "right":  # 左から右へマージ
            # 左側のテキストを取得
            left_start = f"{diff['left_start']}.0"
            left_end = f"{diff['left_end']}.end"
            content = self.left_text.get(left_start, left_end)
            
            # 右側のテキストを置換
            right_start = f"{diff['right_start']}.0"
            right_end = f"{diff['right_end']}.end"
            self.right_text.delete(right_start, right_end)
            if content:  # 空でない場合のみ挿入
                self.right_text.insert(right_start, content)
        
        elif direction == "left":  # 右から左へマージ
            # 右側のテキストを取得
            right_start = f"{diff['right_start']}.0"
            right_end = f"{diff['right_end']}.end"
            content = self.right_text.get(right_start, right_end)
            
            # 左側のテキストを置換
            left_start = f"{diff['left_start']}.0"
            left_end = f"{diff['left_end']}.end"
            self.left_text.delete(left_start, left_end)
            if content:  # 空でない場合のみ挿入
                self.left_text.insert(left_start, content)
        
        # 再比較してハイライトを更新
        left_content = self.left_text.get(1.0, tk.END)
        right_content = self.right_text.get(1.0, tk.END)
        self.detect_and_highlight_diff(left_content, right_content)


if __name__ == "__main__":
    root = tk.Tk()
    app = DiffTool(root)
    root.mainloop()
