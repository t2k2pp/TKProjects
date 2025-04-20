import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import csv
import os
import requests
import json
from datetime import datetime

class PromptGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("プロンプトジェネレーター")
        self.root.geometry("1200x700")
        
        # CSVデータを格納する変数
        self.csv_data = []
        self.titles = []
        
        # テキストA・Bの初期値（後で書き換え可能）
        self.text_a = "あなたは話上手な熟練のプロジェクトマネージャです。若手育成のためあなたの知識と話術を使って「プロジェクトマネージャの千夜一夜物語」というショートショート集の1話を書いてください。\r\n\
\r\n\
# 基本要件\r\n\
- 1話は約1,500-2,000字（読了時間約5分）で完結する\r\n\
- プロジェクトマネジメントの特定の知識・手法・概念を1つ取り上げて、ストーリーを通じて分かりやすく伝える\r\n\
- 物語として面白く、かつ教育的な内容にする\r\n\
- 現場のプロジェクトマネージャーが「あるある」と共感でき、「ニヤリ」と笑える要素を含める\r\n\
- 読者が実際のプロジェクト現場で活用できる実践的な知識を盛り込む\r\n\
- 起承転結の構造と、印象に残る「落ち」を持たせる\r\n\
\r\n\
# ストーリー構造\r\n\
1. 導入部（起）- 200-300字: 主人公のPMとプロジェクトの基本設定を紹介\r\n\
2. 問題提示（承）- 300-400字: 主人公が直面する具体的な課題や問題を明確に示す\r\n\
3. 転換点（転）- 300-400字: 主人公がPM知識/手法に出会う、または思い出す瞬間\r\n\
4. 解決（結）- 300-400字: 知識/手法の適用とその成功または失敗の結果\r\n\
5. 落ち/結論 - 100-200字: 読者に「ニヤリ」とさせる意外な展開や気づき\r\n\
\r\n\
# 書き方の指針\r\n\
- 主人公は名前、性格の特徴、経験レベルを持つ具体的なPMとして描写する\r\n\
- 実際のプロジェクト現場でありそうな会話やシーンを描く\r\n\
- 専門用語は自然に説明しつつ物語に組み込む\r\n\
- PM知識/手法の名称と基本概念をストーリー内で明確に説明する\r\n\
- 適用前と適用後の変化を明確に示す\r\n\
- 「教える」のではなく「見せる」ことで概念を伝える\r\n\
- 簡潔で読みやすい文体を心がける\r\n\
- 物語の場面ごとに何処の場所かを表す見出しを付ける（例:役員の集まる会議室、誰もいなくなったオフィスなど）\r\n\
- 起、承、転、結を見出しに記載しない\r\n\
\r\n\
# 題材\r\n\
"

        self.text_b = "\n\n# 出力形式\r\n\
必ず日本語（一般的に使われる英語は許可）を使って、以下の形式で執筆してください：\r\n\
\r\n\
## [タイトル]\r\n\
[本文（起承転結の構造に沿って書く）]\r\n\
\r\n\
## 学べるポイント\r\n\
[この物語から学べるPM知識/手法の概要と実践のヒント（100-200字程度）]\r\n\
\r\n\
以上の条件に基づいて、選択された題材からショートショートをアーティファクトで執筆してください。PM知識を自然に物語に織り込みながら、読者が楽しめて共感でき、かつ実践的な学びが得られる内容を目指してください。\r\n\
"        
        # Azure OpenAI APIの設定
        self.api_base = tk.StringVar(value="")
        self.api_key = tk.StringVar(value="")
        self.model_id = tk.StringVar(value="")
        self.api_version = tk.StringVar(value="")
        
        # 初期化時にファイル選択ダイアログを表示
        self.select_file()
    
    def select_file(self):
        # ファイル選択ダイアログを表示
        file_path = filedialog.askopenfilename(
            title="CSVファイルを選択してください",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:  # ファイルが選択された場合
            self.load_csv(file_path)
            self.create_main_window()
        else:  # キャンセルされた場合はアプリを終了
            self.root.destroy()
    
    def load_csv(self, file_path):
        # CSVファイルを読み込む
        encodings = ['utf-8', 'shift_jis', 'cp932', 'euc_jp', 'iso2022_jp']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    reader = csv.reader(file)
                    header = next(reader)  # ヘッダー行をスキップ
                    self.csv_data = list(reader)
                    # タイトル一覧を抽出
                    self.titles = [row[0] for row in self.csv_data]
                    print(f"ファイルは {encoding} エンコーディングで読み込まれました")
                    return  # 成功したらループを抜ける
            except UnicodeDecodeError:
                continue  # 次のエンコーディングを試す
            except Exception as e:
                messagebox.showerror("エラー", f"CSVファイルの読み込みに失敗しました：{e}")
                self.root.destroy()
                return
        
        # すべてのエンコーディングで失敗した場合
        messagebox.showerror("エラー", "対応するエンコーディングが見つかりませんでした。")
        self.root.destroy()
    
    def create_main_window(self):
        # メインフレームを作成
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左右に分割
        paned_window = tk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        # 左側：タイトル一覧（スクロール可能）
        left_frame = tk.Frame(paned_window, width=300)
        paned_window.add(left_frame)
        
        # タイトル一覧のラベル
        title_label = tk.Label(left_frame, text="タイトル一覧", font=("", 12, "bold"))
        title_label.pack(anchor=tk.W, pady=(0, 5))
        
        # リストボックスとスクロールバー
        list_frame = tk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # インデックス付きのリストボックス
        self.listbox = ttk.Treeview(list_frame, yscrollcommand=scrollbar.set, columns=("index", "title"), show="headings")
        self.listbox.column("index", width=50)
        self.listbox.column("title", width=250)
        self.listbox.heading("index", text="No.")
        self.listbox.heading("title", text="タイトル")
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar.config(command=self.listbox.yview)
        
        # タイトルをリストボックスに追加（インデックス付き）
        for i, title in enumerate(self.titles):
            self.listbox.insert("", tk.END, values=(i+1, title))
        
        # 選択イベントをバインド
        self.listbox.bind("<<TreeviewSelect>>", self.on_title_select)
        
        # 右側：プロンプト表示エリア
        right_frame = tk.Frame(paned_window)
        paned_window.add(right_frame)
        
        # プロンプトのラベル
        prompt_label = tk.Label(right_frame, text="プロンプト", font=("", 12, "bold"))
        prompt_label.pack(anchor=tk.W, pady=(0, 5))
        
        # テキストボックスとスクロールバー
        text_frame = tk.Frame(right_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        text_scrollbar = tk.Scrollbar(text_frame)
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.text_box = tk.Text(text_frame, yscrollcommand=text_scrollbar.set, wrap=tk.WORD)
        self.text_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        text_scrollbar.config(command=self.text_box.yview)
        
        # ボタンフレーム（横並びにする）
        button_frame = tk.Frame(right_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # コピーボタン
        copy_button = tk.Button(button_frame, text="プロンプトをコピー", command=self.copy_to_clipboard)
        copy_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # テキストA/Bを編集するボタン
        edit_button = tk.Button(button_frame, text="テキストA/Bを編集", command=self.edit_template_text)
        edit_button.pack(side=tk.LEFT)
        
        # Azure OpenAI API設定フレーム
        api_frame = tk.LabelFrame(right_frame, text="Azure OpenAI API設定", padx=10, pady=10)
        api_frame.pack(fill=tk.X, pady=10)
        
        # API Base URL
        base_label = tk.Label(api_frame, text="Base URL:")
        base_label.grid(row=0, column=0, sticky=tk.W, pady=2)
        base_entry = tk.Entry(api_frame, textvariable=self.api_base, width=50)
        base_entry.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        # API Key
        key_label = tk.Label(api_frame, text="API Key:")
        key_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        key_entry = tk.Entry(api_frame, textvariable=self.api_key, width=50, show="*")
        key_entry.grid(row=1, column=1, sticky=tk.W, pady=2)
        
        # Model ID
        model_label = tk.Label(api_frame, text="Model ID:")
        model_label.grid(row=2, column=0, sticky=tk.W, pady=2)
        model_entry = tk.Entry(api_frame, textvariable=self.model_id, width=50)
        model_entry.grid(row=2, column=1, sticky=tk.W, pady=2)
        
        # API Version
        version_label = tk.Label(api_frame, text="API Version:")
        version_label.grid(row=3, column=0, sticky=tk.W, pady=2)
        version_entry = tk.Entry(api_frame, textvariable=self.api_version, width=50)
        version_entry.grid(row=3, column=1, sticky=tk.W, pady=2)
        
        # 実行ボタン
        execute_button = tk.Button(api_frame, text="OpenAIに送信", command=self.execute_api)
        execute_button.grid(row=4, column=0, columnspan=2, pady=(10, 0))
        
    def on_title_select(self, event):
        # 選択されたタイトルのアイテムを取得
        selected_items = self.listbox.selection()
        if not selected_items:
            return
        
        # 選択された項目の値を取得
        item_values = self.listbox.item(selected_items[0], "values")
        index = int(item_values[0]) - 1  # インデックスは1から始まるので調整
        
        if 0 <= index < len(self.csv_data):
            selected_row = self.csv_data[index]
            self.update_prompt(selected_row)
    
    def update_prompt(self, row_data):
        # 選択された行のデータをフォーマットしてプロンプトを作成
        csv_content = f"タイトル：{row_data[0]}\n"
        csv_content += f"話の概要：{row_data[1]}\n"
        csv_content += f"シチュエーション：{row_data[2]}\n"
        csv_content += f"学べるPM知識／用語：{row_data[3]}"
        
        # プロンプトを作成（テキストA + CSV内容 + テキストB）
        prompt = f"{self.text_a}{csv_content}{self.text_b}"
        
        # テキストボックスをクリアして新しいプロンプトを表示
        self.text_box.delete(1.0, tk.END)
        self.text_box.insert(tk.END, prompt)
    
    def copy_to_clipboard(self):
        # テキストボックスの内容をクリップボードにコピー
        prompt_text = self.text_box.get(1.0, tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(prompt_text)
        messagebox.showinfo("コピー完了", "プロンプトをクリップボードにコピーしました")
    
    def edit_template_text(self):
        # テキストA/Bを編集するためのダイアログを表示
        edit_window = tk.Toplevel(self.root)
        edit_window.title("テンプレート編集")
        edit_window.geometry("600x400")
        
        # フレームを作成
        frame = tk.Frame(edit_window, padx=10, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # テキストAのラベルと入力エリア
        tk.Label(frame, text="テキストA:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        text_a_box = tk.Text(frame, height=6)
        text_a_box.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        text_a_box.insert(tk.END, self.text_a)
        
        # テキストBのラベルと入力エリア
        tk.Label(frame, text="テキストB:").grid(row=2, column=0, sticky=tk.W, pady=(10, 5))
        text_b_box = tk.Text(frame, height=6)
        text_b_box.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        text_b_box.insert(tk.END, self.text_b)
        
        # グリッドの行と列の重みを設定
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_rowconfigure(3, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        
        # 保存ボタン
        def save_template():
            self.text_a = text_a_box.get(1.0, tk.END).rstrip("\n")
            self.text_b = text_b_box.get(1.0, tk.END).rstrip("\n")
            # 現在選択中の項目があれば、プロンプトを更新
            selected_items = self.listbox.selection()
            if selected_items:
                item_values = self.listbox.item(selected_items[0], "values")
                index = int(item_values[0]) - 1
                self.update_prompt(self.csv_data[index])
            edit_window.destroy()
            messagebox.showinfo("保存完了", "テンプレートを保存しました")
        
        save_button = tk.Button(frame, text="保存", command=save_template)
        save_button.grid(row=4, column=0, pady=10)

    def execute_api(self):
        # 選択されているタイトルがあるか確認
        selected_items = self.listbox.selection()
        if not selected_items:
            messagebox.showerror("エラー", "タイトルを選択してください")
            return
        
        # プロンプトを取得
        prompt_text = self.text_box.get(1.0, tk.END).strip()
        if not prompt_text:
            messagebox.showerror("エラー", "プロンプトが空です")
            return
        
        # APIパラメータのバリデーション
        if not self.api_base.get() or not self.api_key.get() or not self.model_id.get() or not self.api_version.get():
            messagebox.showerror("エラー", "API設定が不完全です")
            return
        
        # APIリクエストの準備
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key.get()
        }
        
        # Azure OpenAI APIに送信するデータ
        data = {
            "messages": [
                {"role": "system", "content": "あなたは物語を書く執筆アシスタントです。以下のプロンプトに従って物語を作成してください。"},
                {"role": "user", "content": prompt_text}
            ],
            "max_tokens": 10000
        }
        
        try:
            # 処理中を表示
            self.root.config(cursor="wait")
            self.root.update()
            
            # 選択されたタイトルを取得
            item_values = self.listbox.item(selected_items[0], "values")
            index = int(item_values[0]) - 1
            title = self.titles[index]
            
            # Azure OpenAI APIのエンドポイントを構築
            api_version = self.api_version.get()
            endpoint = f"{self.api_base.get().rstrip('/')}/openai/deployments/{self.model_id.get()}/chat/completions?api-version={api_version}"
            
            # APIリクエスト送信
            response = requests.post(endpoint, headers=headers, data=json.dumps(data))
            response.raise_for_status()  # エラーがあれば例外を発生
            
            # レスポンスを解析
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # 結果をファイルに保存
            filename = f"O{index+1:05d}_{title}.md"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            
            messagebox.showinfo("実行完了", f"応答を {filename} に保存しました")
            self.move_treeview_selection_down()
            
        except Exception as e:
            messagebox.showerror("エラー", f"API実行中にエラーが発生しました：{e}")
        
        finally:
            # カーソルを元に戻す
            self.root.config(cursor="")
    
    def move_treeview_selection_down(self):
        selected_items = self.listbox.selection()
        if selected_items:
            selected_item = selected_items[0]
            parent_item = self.listbox.parent(selected_item)
            children = self.listbox.get_children(parent_item)

            try:
                current_index = children.index(selected_item)
                next_index = current_index + 1
                if next_index < len(children):
                    next_item = children[next_index]
                    self.listbox.selection_set(next_item)
                    self.listbox.focus(next_item) # 必要に応じて
            except ValueError:
                pass # 選択された項目が子要素リストに見つからない場合 (通常ありえないはず)



if __name__ == "__main__":
    root = tk.Tk()
    app = PromptGenerator(root)
    root.mainloop()