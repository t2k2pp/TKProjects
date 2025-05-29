import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import PyPDF2
import os
import math
from pathlib import Path
import threading


class PDFSplitterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF分割ツール")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        
        # 変数の初期化
        self.input_file_path = tk.StringVar()
        self.output_folder_path = tk.StringVar()
        self.split_method = tk.StringVar(value="page_split")  # "page_split" or "count_split"
        self.page_number = tk.StringVar()
        self.pages_per_file = tk.StringVar()
        self.status_text = tk.StringVar(value="PDFファイルと保存先フォルダを選択してください")
        self.total_pages = tk.StringVar(value="")
        
        self.setup_gui()
        
    def setup_gui(self):
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # グリッドの重みを設定
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        row = 0
        
        # PDFファイル選択
        ttk.Label(main_frame, text="入力PDFファイル:").grid(row=row, column=0, sticky=tk.W, pady=5)
        
        file_frame = ttk.Frame(main_frame)
        file_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        file_frame.columnconfigure(0, weight=1)
        
        self.file_entry = ttk.Entry(file_frame, textvariable=self.input_file_path, state="readonly")
        self.file_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        ttk.Button(file_frame, text="PDFファイルを選択", 
                  command=self.select_input_file).grid(row=0, column=1)
        
        row += 1
        
        # 出力先フォルダ選択
        ttk.Label(main_frame, text="保存先フォルダ:").grid(row=row, column=0, sticky=tk.W, pady=5)
        
        folder_frame = ttk.Frame(main_frame)
        folder_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        folder_frame.columnconfigure(0, weight=1)
        
        self.folder_entry = ttk.Entry(folder_frame, textvariable=self.output_folder_path, state="readonly")
        self.folder_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        ttk.Button(folder_frame, text="保存先フォルダを選択", 
                  command=self.select_output_folder).grid(row=0, column=1)
        
        row += 1
        
        # 総ページ数表示
        ttk.Label(main_frame, text="総ページ数:").grid(row=row, column=0, sticky=tk.W, pady=5)
        ttk.Label(main_frame, textvariable=self.total_pages).grid(row=row, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        row += 1
        
        # 分割方法選択
        ttk.Label(main_frame, text="分割方法:").grid(row=row, column=0, sticky=tk.W, pady=(20, 5))
        
        method_frame = ttk.Frame(main_frame)
        method_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=(20, 5), padx=(10, 0))
        
        ttk.Radiobutton(method_frame, text="指定ページで分割", 
                       variable=self.split_method, value="page_split",
                       command=self.on_method_change).grid(row=0, column=0, sticky=tk.W)
        
        ttk.Radiobutton(method_frame, text="ページ数単位で分割", 
                       variable=self.split_method, value="count_split",
                       command=self.on_method_change).grid(row=1, column=0, sticky=tk.W)
        
        row += 1
        
        # 分割設定フレーム
        self.settings_frame = ttk.LabelFrame(main_frame, text="分割設定", padding="10")
        self.settings_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        self.settings_frame.columnconfigure(1, weight=1)
        
        # 指定ページで分割の設定
        self.page_split_frame = ttk.Frame(self.settings_frame)
        self.page_split_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E))
        self.page_split_frame.columnconfigure(1, weight=1)
        
        ttk.Label(self.page_split_frame, text="分割ページ番号 (1つ目のファイルの最終ページ):").grid(
            row=0, column=0, sticky=tk.W, pady=5)
        self.page_entry = ttk.Entry(self.page_split_frame, textvariable=self.page_number, width=10)
        self.page_entry.grid(row=0, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # ページ数単位で分割の設定
        self.count_split_frame = ttk.Frame(self.settings_frame)
        self.count_split_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E))
        self.count_split_frame.columnconfigure(1, weight=1)
        
        ttk.Label(self.count_split_frame, text="1ファイルあたりのページ数:").grid(
            row=0, column=0, sticky=tk.W, pady=5)
        self.count_entry = ttk.Entry(self.count_split_frame, textvariable=self.pages_per_file, width=10)
        self.count_entry.grid(row=0, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        row += 1
        
        # 実行ボタン
        self.execute_button = ttk.Button(main_frame, text="分割実行", 
                                       command=self.execute_split)
        self.execute_button.grid(row=row, column=0, columnspan=2, pady=20)
        
        row += 1
        
        # 進捗・結果表示エリア
        ttk.Label(main_frame, text="処理状況:").grid(row=row, column=0, sticky=tk.W, pady=5)
        
        self.status_label = ttk.Label(main_frame, textvariable=self.status_text, 
                                    foreground="blue", wraplength=400)
        self.status_label.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        # 初期状態の設定
        self.on_method_change()
        
    def select_input_file(self):
        """PDFファイルを選択"""
        file_path = filedialog.askopenfilename(
            title="PDFファイルを選択してください",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        
        if file_path:
            self.input_file_path.set(file_path)
            self.get_pdf_info(file_path)
            
    def select_output_folder(self):
        """出力先フォルダを選択"""
        folder_path = filedialog.askdirectory(title="保存先フォルダを選択してください")
        
        if folder_path:
            self.output_folder_path.set(folder_path)
            
    def get_pdf_info(self, file_path):
        """PDFの情報を取得"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                page_count = len(pdf_reader.pages)
                self.total_pages.set(f"{page_count} ページ")
                self.status_text.set(f"PDFファイルを読み込みました ({page_count} ページ)")
        except Exception as e:
            self.total_pages.set("取得できませんでした")
            self.status_text.set(f"エラー: PDFファイルの読み込みに失敗しました - {str(e)}")
            
    def on_method_change(self):
        """分割方法の変更時の処理"""
        if self.split_method.get() == "page_split":
            # 指定ページで分割
            self.page_split_frame.grid()
            self.count_split_frame.grid_remove()
        else:
            # ページ数単位で分割
            self.page_split_frame.grid_remove()
            self.count_split_frame.grid()
            
    def validate_inputs(self):
        """入力値の検証"""
        # PDFファイルの選択確認
        if not self.input_file_path.get():
            raise ValueError("PDFファイルが選択されていません")
            
        # 出力先フォルダの選択確認
        if not self.output_folder_path.get():
            raise ValueError("保存先フォルダが選択されていません")
            
        # PDFファイルの存在確認
        if not os.path.exists(self.input_file_path.get()):
            raise ValueError("選択されたPDFファイルが存在しません")
            
        # PDFファイルの読み込み確認
        try:
            with open(self.input_file_path.get(), 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)
        except Exception as e:
            raise ValueError(f"PDFファイルの読み込みに失敗しました: {str(e)}")
            
        # 分割方法に応じた入力値検証
        if self.split_method.get() == "page_split":
            # 指定ページで分割
            try:
                page_num = int(self.page_number.get())
                if page_num < 1 or page_num >= total_pages:
                    raise ValueError(f"ページ番号は1以上{total_pages-1}以下で入力してください")
            except ValueError as ve:
                if "invalid literal" in str(ve):
                    raise ValueError("ページ番号は整数で入力してください")
                else:
                    raise ve
        else:
            # ページ数単位で分割
            try:
                pages_per_file = int(self.pages_per_file.get())
                if pages_per_file <= 0:
                    raise ValueError("1ファイルあたりのページ数は1以上で入力してください")
            except ValueError as ve:
                if "invalid literal" in str(ve):
                    raise ValueError("ページ数は整数で入力してください")
                else:
                    raise ve
                    
        return total_pages
        
    def execute_split(self):
        """PDF分割処理の実行"""
        try:
            # 入力値の検証
            total_pages = self.validate_inputs()
            
            # ボタンを無効化
            self.execute_button.config(state="disabled")
            self.status_text.set("処理中...")
            
            # 別スレッドで処理を実行
            thread = threading.Thread(target=self.split_pdf_thread, args=(total_pages,))
            thread.daemon = True
            thread.start()
            
        except ValueError as e:
            self.status_text.set(f"エラー: {str(e)}")
            messagebox.showerror("入力エラー", str(e))
        except Exception as e:
            self.status_text.set(f"予期しないエラー: {str(e)}")
            messagebox.showerror("エラー", f"予期しないエラーが発生しました: {str(e)}")
            
    def split_pdf_thread(self, total_pages):
        """PDF分割処理（スレッド実行用）"""
        try:
            # 出力フォルダの作成
            input_filename = Path(self.input_file_path.get()).stem
            output_base_folder = Path(self.output_folder_path.get())
            output_folder = output_base_folder / input_filename
            
            output_folder.mkdir(exist_ok=True)
            
            # PDFファイルを開く
            with open(self.input_file_path.get(), 'rb') as input_file:
                pdf_reader = PyPDF2.PdfReader(input_file)
                
                if self.split_method.get() == "page_split":
                    # 指定ページで分割
                    self.split_by_page(pdf_reader, output_folder, input_filename, total_pages)
                else:
                    # ページ数単位で分割
                    self.split_by_count(pdf_reader, output_folder, input_filename, total_pages)
                    
        except Exception as e:
            self.root.after(0, lambda: self.handle_error(str(e)))
        finally:
            self.root.after(0, lambda: self.execute_button.config(state="normal"))
            
    def split_by_page(self, pdf_reader, output_folder, input_filename, total_pages):
        """指定ページで分割"""
        split_page = int(self.page_number.get())
        
        # 1つ目のPDF (1ページ目からSページ目まで)
        pdf_writer1 = PyPDF2.PdfWriter()
        for page_num in range(0, split_page):
            pdf_writer1.add_page(pdf_reader.pages[page_num])
            
        output_file1 = output_folder / f"{input_filename}_1-{split_page}.pdf"
        with open(output_file1, 'wb') as output_file:
            pdf_writer1.write(output_file)
            
        files_created = 1
        
        # 2つ目のPDF (S+1ページ目から最終ページまで)
        if split_page < total_pages:
            pdf_writer2 = PyPDF2.PdfWriter()
            for page_num in range(split_page, total_pages):
                pdf_writer2.add_page(pdf_reader.pages[page_num])
                
            output_file2 = output_folder / f"{input_filename}_{split_page+1}-{total_pages}.pdf"
            with open(output_file2, 'wb') as output_file:
                pdf_writer2.write(output_file)
            files_created = 2
            
        self.root.after(0, lambda: self.status_text.set(
            f"分割完了: {files_created}個のファイルに分割しました\n保存先: {output_folder}"))
        
    def split_by_count(self, pdf_reader, output_folder, input_filename, total_pages):
        """ページ数単位で分割"""
        pages_per_file = int(self.pages_per_file.get())
        file_count = math.ceil(total_pages / pages_per_file)
        
        for i in range(file_count):
            pdf_writer = PyPDF2.PdfWriter()
            
            start_page = i * pages_per_file
            end_page = min((i + 1) * pages_per_file, total_pages)
            
            for page_num in range(start_page, end_page):
                pdf_writer.add_page(pdf_reader.pages[page_num])
                
            output_file = output_folder / f"{input_filename}_pages_{start_page+1}-{end_page}.pdf"
            with open(output_file, 'wb') as output_file_handle:
                pdf_writer.write(output_file_handle)
                
        self.root.after(0, lambda: self.status_text.set(
            f"分割完了: {file_count}個のファイルに分割しました\n保存先: {output_folder}"))
        
    def handle_error(self, error_message):
        """エラーハンドリング"""
        self.status_text.set(f"エラー: {error_message}")
        messagebox.showerror("処理エラー", f"PDF分割処理中にエラーが発生しました:\n{error_message}")


def main():
    root = tk.Tk()
    app = PDFSplitterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()