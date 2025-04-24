import os
import json
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import re
from datetime import datetime
import openai
from openai import AzureOpenAI
import markdown
import platform
import webbrowser

class Config:
    def __init__(self):
        # ユーザープロファイルパスを取得
        if platform.system() == "Windows":
            self.profile_path = os.path.join(os.environ["USERPROFILE"], "AzureOpenAIApp")
        else:  # macOS/Linux
            self.profile_path = os.path.join(os.path.expanduser("~"), ".AzureOpenAIApp")
        
        # 設定ディレクトリがなければ作成
        if not os.path.exists(self.profile_path):
            os.makedirs(self.profile_path)
        
        self.config_file = os.path.join(self.profile_path, "config.json")
        self.default_config = {
            "api_key": "",
            "api_base": "",
            "api_version": "2024-12-01-preview",  # 2024年の最新APIバージョン
            "deployment_name": "gpt-4o",
            "completion_token_limit": 4000,
            "top_p": 0.95,                        # temperatureの代わりにtop_pを使用
            "response_format": "text",            # レスポンスフォーマット（text/json）
            "user_prompt_template": "以下の依頼に対して詳細に回答してください。回答の最後に{completion_marker}と記載してください。",
            "system_prompt": "あなたは親切で、創造的で、賢いアシスタントです。ユーザーの質問に対して詳細に答えてください。",
            "max_retries": 5,
            "completion_marker": "####END####",   # 完了マーカーを設定可能に
            "output_dir": os.path.join(self.profile_path, "outputs")
        }
        
        # 出力ディレクトリがなければ作成
        if not os.path.exists(self.default_config["output_dir"]):
            os.makedirs(self.default_config["output_dir"])
        
        self.load_config()
    
    def load_config(self):
        """設定ファイルを読み込む"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                saved_config = json.load(f)
                self.config = {**self.default_config, **saved_config}
        else:
            self.config = self.default_config
            self.save_config()
    
    def save_config(self):
        """設定ファイルを保存する"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def get(self, key):
        """設定値を取得する"""
        # ユーザープロンプトテンプレートに完了マーカーを埋め込む
        if key == "user_prompt_template":
            template = self.config.get(key, self.default_config.get(key))
            completion_marker = self.get("completion_marker")
            return template.format(completion_marker=completion_marker)
        return self.config.get(key, self.default_config.get(key))
    
    def set(self, key, value):
        """設定値を設定する"""
        self.config[key] = value
        self.save_config()

class AzureOpenAIClient:
    def __init__(self, config):
        self.config = config
        self.client = None
        self.initialize_client()
    
    def initialize_client(self):
        """Azure OpenAI クライアントを初期化する"""
        try:
            self.client = AzureOpenAI(
                api_key=self.config.get("api_key"),
                api_version=self.config.get("api_version"),
                azure_endpoint=self.config.get("api_base")
            )
            return True
        except Exception as e:
            print(f"クライアント初期化エラー: {e}")
            return False
    
    def get_completion(self, messages, top_p=None):
        """Azureからレスポンスを取得する"""
        if self.client is None:
            if not self.initialize_client():
                return None, "エラー: Azure OpenAI クライアントが初期化されていません。設定を確認してください。"
        
        if top_p is None:
            top_p = float(self.config.get("top_p"))
        
        try:
            # 2024-12-01-preview APIバージョンに対応したパラメータを使用
            response = self.client.chat.completions.create(
                model=self.config.get("deployment_name"),
                messages=messages,
                top_p=top_p,
                max_completion_tokens=int(self.config.get("completion_token_limit")),
                response_format={"type": self.config.get("response_format")}
            )
            return True, response.choices[0].message.content
        except Exception as e:
            error_message = f"API呼び出しエラー: {str(e)}"
            print(error_message)  # コンソールにエラーを出力
            return False, error_message

class App:
    def __init__(self, root):
        self.root = root
        self.config = Config()
        self.client = AzureOpenAIClient(self.config)
        
        self.root.title("Azure OpenAI 依頼やり切りアプリ")
        self.root.geometry("1000x800")
        
        self.create_widgets()
        self.create_menu()
    
    def create_menu(self):
        """メニューバーを作成する"""
        menu_bar = tk.Menu(self.root)
        
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="新規", command=self.new_conversation)
        file_menu.add_command(label="保存", command=self.save_conversation)
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.root.quit)
        menu_bar.add_cascade(label="ファイル", menu=file_menu)
        
        settings_menu = tk.Menu(menu_bar, tearoff=0)
        settings_menu.add_command(label="設定", command=self.open_settings)
        menu_bar.add_cascade(label="設定", menu=settings_menu)
        
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menu_bar.add_cascade(label="ヘルプ", menu=help_menu)
        
        self.root.config(menu=menu_bar)
    
    def create_widgets(self):
        """ウィジェットを作成する"""
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 入力部分
        input_frame = ttk.LabelFrame(main_frame, text="入力", padding=5)
        input_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.input_text = scrolledtext.ScrolledText(input_frame, wrap=tk.WORD, height=10)
        self.input_text.pack(fill=tk.BOTH, expand=True)
        
        # 入力ボタンフレーム
        input_button_frame = ttk.Frame(main_frame)
        input_button_frame.pack(fill=tk.X, pady=5)
        
        self.send_button = ttk.Button(input_button_frame, text="送信", command=self.send_request)
        self.send_button.pack(side=tk.RIGHT, padx=5)
        
        self.clear_input_button = ttk.Button(input_button_frame, text="入力クリア", command=self.clear_input)
        self.clear_input_button.pack(side=tk.RIGHT, padx=5)
        
        # 状態表示
        self.status_var = tk.StringVar()
        self.status_var.set("準備完了")
        status_label = ttk.Label(input_button_frame, textvariable=self.status_var)
        status_label.pack(side=tk.LEFT, padx=5)
        
        # プログレスバー
        self.progress = ttk.Progressbar(input_button_frame, mode="indeterminate")
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 出力部分
        output_frame = ttk.LabelFrame(main_frame, text="出力", padding=5)
        output_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD)
        self.output_text.pack(fill=tk.BOTH, expand=True)
        
        # 出力ボタンフレーム
        output_button_frame = ttk.Frame(main_frame)
        output_button_frame.pack(fill=tk.X, pady=5)
        
        self.save_button = ttk.Button(output_button_frame, text="保存", command=self.save_conversation)
        self.save_button.pack(side=tk.RIGHT, padx=5)
        
        self.clear_output_button = ttk.Button(output_button_frame, text="出力クリア", command=self.clear_output)
        self.clear_output_button.pack(side=tk.RIGHT, padx=5)
        
        # 初期状態
        self.is_processing = False
        self.conversation_history = []
    
    def send_request(self):
        """リクエストを送信する"""
        if self.is_processing:
            return
        
        user_input = self.input_text.get("1.0", tk.END).strip()
        if not user_input:
            messagebox.showinfo("入力エラー", "入力が空です。")
            return
        
        # 処理開始
        self.is_processing = True
        self.send_button.config(state=tk.DISABLED)
        self.clear_input_button.config(state=tk.DISABLED)
        self.clear_output_button.config(state=tk.DISABLED)
        self.status_var.set("処理中...")
        self.progress.start()
        
        # スレッドで処理を実行
        threading.Thread(target=self.process_request, args=(user_input,), daemon=True).start()
    
    def process_request(self, user_input):
        """リクエストを処理する"""
        try:
            # ユーザープロンプトテンプレートを取得
            prompt_template = self.config.get("user_prompt_template")
            
            # プロンプトを作成
            prompt = f"{prompt_template}\n\n{user_input}"
            
            # システムメッセージを準備
            system_message = self.config.get("system_prompt")
            
            # 完了マーカーを取得
            completion_marker = self.config.get("completion_marker")
            
            # メッセージ履歴を設定
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ]
            
            # 完全な応答を取得するまで繰り返す
            complete_response = ""
            is_complete = False
            retries = 0
            max_retries = int(self.config.get("max_retries"))
            
            while not is_complete and retries < max_retries:
                # レスポンスを取得
                success, response = self.client.get_completion(messages)
                
                # エラー処理
                if not success:
                    # エラーが発生した場合は処理を中止して通知
                    self.update_output(f"🚫 エラーが発生しました：\n{response}")
                    self.update_status(f"エラー発生")
                    messagebox.showerror("API エラー", response)
                    break
                
                # 完了マーカーを確認
                if completion_marker in response:
                    is_complete = True
                    response = response.replace(completion_marker, "").strip()
                
                # 重複部分を検出して削除
                if complete_response and response:
                    # 重複部分を検出するために最も長い共通部分を見つける
                    overlap = self.find_overlap(complete_response, response)
                    if overlap:
                        response = response[len(overlap):]
                
                # レスポンスを追加
                complete_response += response
                
                # 完了していなければ継続リクエスト
                if not is_complete:
                    retries += 1
                    self.update_status(f"継続処理中... (試行 {retries}/{max_retries})")
                    
                    # 継続リクエスト用のメッセージを追加
                    continuation_prompt = f"""
                    前回の応答が不完全でした。続きを生成してください。
                    応答の最後に{completion_marker}と記載することを忘れないでください。
                    これまでの応答:
                    {complete_response}
                    """
                    
                    messages = [
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": complete_response},
                        {"role": "user", "content": continuation_prompt}
                    ]
            
            # 会話履歴に追加（APIエラーでない場合のみ）
            if is_complete or retries == max_retries:
                self.conversation_history.append({"role": "user", "content": user_input})
                self.conversation_history.append({"role": "assistant", "content": complete_response})
                
                # 最大リトライ回数に達した場合、その旨を通知
                if retries == max_retries and not is_complete:
                    incomplete_notice = f"\n\n---\n【注意】最大リトライ回数（{max_retries}回）に達したため、応答が不完全である可能性があります。"
                    complete_response += incomplete_notice
                    self.update_status("最大リトライ回数に達しました")
                    messagebox.showwarning("リトライ上限", f"最大リトライ回数（{max_retries}回）に達しました。応答が不完全である可能性があります。")
                else:
                    self.update_status("処理完了")
                
                # 出力を更新
                self.update_output(complete_response)
            
        except Exception as e:
            error_message = f"予期しないエラーが発生しました: {str(e)}"
            self.update_output(f"🚫 {error_message}")
            self.update_status("エラー")
            messagebox.showerror("エラー", error_message)
        
        finally:
            # UI状態を更新
            self.root.after(0, self.finalize_request)
    
    def finalize_request(self):
        """リクエスト処理の終了処理"""
        self.is_processing = False
        self.send_button.config(state=tk.NORMAL)
        self.clear_input_button.config(state=tk.NORMAL)
        self.clear_output_button.config(state=tk.NORMAL)
        self.progress.stop()
    
    def find_overlap(self, str1, str2, min_overlap=20):
        """二つの文字列間の重複部分を見つける"""
        # 最小オーバーラップ長より短い場合は処理しない
        if len(str1) < min_overlap or len(str2) < min_overlap:
            return ""
        
        # str1の末尾とstr2の先頭の重複を検索
        max_overlap = min(len(str1), len(str2))
        for i in range(min_overlap, max_overlap + 1):
            if str1[-i:] == str2[:i]:
                return str2[:i]
        
        return ""
    
    def update_output(self, text):
        """出力テキストを更新する"""
        self.root.after(0, lambda: self._update_output(text))
    
    def _update_output(self, text):
        """スレッドセーフな出力更新"""
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.END, text)
    
    def update_status(self, text):
        """ステータスを更新する"""
        self.root.after(0, lambda: self.status_var.set(text))
    
    def clear_input(self):
        """入力をクリアする"""
        if messagebox.askyesno("確認", "入力内容をクリアしますか？"):
            self.input_text.delete("1.0", tk.END)
    
    def clear_output(self):
        """出力をクリアする"""
        if messagebox.askyesno("確認", "出力内容をクリアしますか？"):
            self.output_text.delete("1.0", tk.END)
    
    def new_conversation(self):
        """新しい会話を開始する"""
        if messagebox.askyesno("確認", "現在の会話内容がクリアされます。よろしいですか？"):
            self.conversation_history = []
            self.input_text.delete("1.0", tk.END)
            self.output_text.delete("1.0", tk.END)
            self.status_var.set("新しい会話を開始しました")
    
    def save_conversation(self):
        """会話を保存する"""
        # 出力テキストを取得
        output_text = self.output_text.get("1.0", tk.END).strip()
        if not output_text:
            messagebox.showinfo("保存エラー", "保存する内容がありません。")
            return
        
        # デフォルトファイル名を作成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"conversation_{timestamp}.md"
        default_path = os.path.join(self.config.get("output_dir"), default_filename)
        
        # 保存ダイアログを表示
        file_path = filedialog.asksaveasfilename(
            initialdir=self.config.get("output_dir"),
            initialfile=default_filename,
            defaultextension=".md",
            filetypes=[("Markdown ファイル", "*.md"), ("テキストファイル", "*.txt"), ("すべてのファイル", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(output_text)
            
            messagebox.showinfo("保存完了", f"会話を保存しました:\n{file_path}")
            
            # ファイルを開くか尋ねる
            if messagebox.askyesno("確認", "保存したファイルを開きますか？"):
                webbrowser.open(file_path)
                
        except Exception as e:
            messagebox.showerror("保存エラー", f"保存中にエラーが発生しました:\n{str(e)}")
    
    def open_settings(self):
        """設定ダイアログを開く"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("設定")
        settings_window.geometry("600x650")
        settings_window.resizable(True, True)
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # メインフレーム
        main_frame = ttk.Frame(settings_window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # ノートブック（タブコントロール）
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # API設定タブ
        api_frame = ttk.Frame(notebook, padding=10)
        notebook.add(api_frame, text="API設定")
        
        # APIキー
        ttk.Label(api_frame, text="API キー:").grid(row=0, column=0, sticky=tk.W, pady=5)
        api_key_var = tk.StringVar(value=self.config.get("api_key"))
        api_key_entry = ttk.Entry(api_frame, width=50, textvariable=api_key_var, show="*")
        api_key_entry.grid(row=0, column=1, sticky=tk.W+tk.E, pady=5)
        
        # APIベースURL
        ttk.Label(api_frame, text="API エンドポイント:").grid(row=1, column=0, sticky=tk.W, pady=5)
        api_base_var = tk.StringVar(value=self.config.get("api_base"))
        api_base_entry = ttk.Entry(api_frame, width=50, textvariable=api_base_var)
        api_base_entry.grid(row=1, column=1, sticky=tk.W+tk.E, pady=5)
        
        # APIバージョン
        ttk.Label(api_frame, text="API バージョン:").grid(row=2, column=0, sticky=tk.W, pady=5)
        api_version_var = tk.StringVar(value=self.config.get("api_version"))
        api_version_entry = ttk.Entry(api_frame, width=20, textvariable=api_version_var)
        api_version_entry.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # デプロイメント名
        ttk.Label(api_frame, text="デプロイメント名:").grid(row=3, column=0, sticky=tk.W, pady=5)
        deployment_name_var = tk.StringVar(value=self.config.get("deployment_name"))
        deployment_name_entry = ttk.Entry(api_frame, width=30, textvariable=deployment_name_var)
        deployment_name_entry.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # モデル設定タブ
        model_frame = ttk.Frame(notebook, padding=10)
        notebook.add(model_frame, text="モデル設定")
        
        # Top-p値（temperatureの代替）
        ttk.Label(model_frame, text="Top-p値:").grid(row=0, column=0, sticky=tk.W, pady=5)
        top_p_var = tk.StringVar(value=self.config.get("top_p"))
        top_p_entry = ttk.Entry(model_frame, width=10, textvariable=top_p_var)
        top_p_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(model_frame, text="(0.0〜1.0: 低いと一貫性が高く、高いと創造性が高くなります)").grid(row=0, column=2, sticky=tk.W, pady=5)
        
        # レスポンスフォーマット
        ttk.Label(model_frame, text="レスポンスフォーマット:").grid(row=1, column=0, sticky=tk.W, pady=5)
        response_format_var = tk.StringVar(value=self.config.get("response_format"))
        response_format_combobox = ttk.Combobox(model_frame, width=10, textvariable=response_format_var)
        response_format_combobox["values"] = ("text", "json")
        response_format_combobox.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # トークン制限
        ttk.Label(model_frame, text="生成トークン上限:").grid(row=2, column=0, sticky=tk.W, pady=5)
        completion_token_limit_var = tk.StringVar(value=self.config.get("completion_token_limit"))
        completion_token_limit_entry = ttk.Entry(model_frame, width=10, textvariable=completion_token_limit_var)
        completion_token_limit_entry.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # 最大リトライ回数
        ttk.Label(model_frame, text="最大リトライ回数:").grid(row=3, column=0, sticky=tk.W, pady=5)
        max_retries_var = tk.StringVar(value=self.config.get("max_retries"))
        max_retries_entry = ttk.Entry(model_frame, width=10, textvariable=max_retries_var)
        max_retries_entry.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # 完了マーカー
        ttk.Label(model_frame, text="完了マーカー:").grid(row=4, column=0, sticky=tk.W, pady=5)
        completion_marker_var = tk.StringVar(value=self.config.get("completion_marker"))
        completion_marker_entry = ttk.Entry(model_frame, width=20, textvariable=completion_marker_var)
        completion_marker_entry.grid(row=4, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(model_frame, text="(応答の完了を示す特殊文字列)").grid(row=4, column=2, sticky=tk.W, pady=5)
        
        # プロンプト設定タブ
        prompt_frame = ttk.Frame(notebook, padding=10)
        notebook.add(prompt_frame, text="プロンプト設定")
        
        # システムプロンプト
        ttk.Label(prompt_frame, text="システムプロンプト:").grid(row=0, column=0, sticky=tk.W, pady=5)
        system_prompt_text = scrolledtext.ScrolledText(prompt_frame, wrap=tk.WORD, width=60, height=6)
        system_prompt_text.grid(row=1, column=0, columnspan=3, sticky=tk.W+tk.E+tk.N+tk.S, pady=5)
        system_prompt_text.insert(tk.END, self.config.get("system_prompt"))
        
        # ユーザープロンプトテンプレート
        ttk.Label(prompt_frame, text="ユーザープロンプトテンプレート:").grid(row=2, column=0, sticky=tk.W, pady=5)
        
        # テンプレートには完了マーカーのプレースホルダーを含ませる
        template = self.config.get("user_prompt_template")
        # {completion_marker}プレースホルダーをそのまま表示するため、formatで適用される前の状態に戻す
        if "{completion_marker}" not in template:
            template = template.replace(self.config.get("completion_marker"), "{completion_marker}")
        
        user_prompt_template_text = scrolledtext.ScrolledText(prompt_frame, wrap=tk.WORD, width=60, height=6)
        user_prompt_template_text.grid(row=3, column=0, columnspan=3, sticky=tk.W+tk.E+tk.N+tk.S, pady=5)
        user_prompt_template_text.insert(tk.END, template)
        
        # プロンプト説明
        ttk.Label(prompt_frame, text="※ ユーザーの入力は自動的にテンプレートの後に追加されます").grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=5)
        ttk.Label(prompt_frame, text="※ {completion_marker}は設定した完了マーカーに置き換えられます").grid(row=5, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        # 出力設定タブ
        output_frame = ttk.Frame(notebook, padding=10)
        notebook.add(output_frame, text="出力設定")
        
        # 出力ディレクトリ
        ttk.Label(output_frame, text="出力ディレクトリ:").grid(row=0, column=0, sticky=tk.W, pady=5)
        output_dir_var = tk.StringVar(value=self.config.get("output_dir"))
        output_dir_entry = ttk.Entry(output_frame, width=50, textvariable=output_dir_var)
        output_dir_entry.grid(row=0, column=1, sticky=tk.W+tk.E, pady=5)
        
        # 出力ディレクトリ選択ボタン
        def select_output_dir():
            dir_path = filedialog.askdirectory(initialdir=output_dir_var.get())
            if dir_path:
                output_dir_var.set(dir_path)
        
        select_dir_button = ttk.Button(output_frame, text="参照...", command=select_output_dir)
        select_dir_button.grid(row=0, column=2, padx=5, pady=5)
        
        # ボタンフレーム
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # 保存ボタン
        def save_settings():
            try:
                # API設定
                self.config.set("api_key", api_key_var.get())
                self.config.set("api_base", api_base_var.get())
                self.config.set("api_version", api_version_var.get())
                self.config.set("deployment_name", deployment_name_var.get())
                
                # モデル設定
                self.config.set("top_p", float(top_p_var.get()))
                self.config.set("response_format", response_format_var.get())
                self.config.set("completion_token_limit", int(completion_token_limit_var.get()))
                self.config.set("max_retries", int(max_retries_var.get()))
                self.config.set("completion_marker", completion_marker_var.get())
                
                # プロンプト設定
                self.config.set("system_prompt", system_prompt_text.get("1.0", tk.END).strip())
                
                # ユーザープロンプトテンプレート（{completion_marker}プレースホルダーをそのまま保存）
                self.config.set("user_prompt_template", user_prompt_template_text.get("1.0", tk.END).strip())
                
                # 出力設定
                output_dir = output_dir_var.get()
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                self.config.set("output_dir", output_dir)
                
                # クライアントを再初期化
                self.client = AzureOpenAIClient(self.config)
                
                messagebox.showinfo("設定保存", "設定が保存されました。")
                settings_window.destroy()
                
            except Exception as e:
                messagebox.showerror("エラー", f"設定の保存中にエラーが発生しました:\n{str(e)}")
        
        save_button = ttk.Button(button_frame, text="保存", command=save_settings)
        save_button.pack(side=tk.RIGHT, padx=5)
        
        # キャンセルボタン
        cancel_button = ttk.Button(button_frame, text="キャンセル", command=settings_window.destroy)
        cancel_button.pack(side=tk.RIGHT, padx=5)
        
        # デフォルトに戻すボタン
        def reset_defaults():
            if messagebox.askyesno("確認", "設定をデフォルトに戻しますか？\n現在の設定は失われます。"):
                # API設定
                api_key_var.set(self.config.default_config["api_key"])
                api_base_var.set(self.config.default_config["api_base"])
                api_version_var.set(self.config.default_config["api_version"])
                deployment_name_var.set(self.config.default_config["deployment_name"])
                
                # モデル設定
                top_p_var.set(self.config.default_config["top_p"])
                response_format_var.set(self.config.default_config["response_format"])
                completion_token_limit_var.set(self.config.default_config["completion_token_limit"])
                max_retries_var.set(self.config.default_config["max_retries"])
                completion_marker_var.set(self.config.default_config["completion_marker"])
                
                # プロンプト設定
                system_prompt_text.delete("1.0", tk.END)
                system_prompt_text.insert(tk.END, self.config.default_config["system_prompt"])
                
                user_prompt_template_text.delete("1.0", tk.END)
                user_prompt_template_text.insert(tk.END, self.config.default_config["user_prompt_template"])
                
                # 出力設定
                output_dir_var.set(self.config.default_config["output_dir"])
        
        reset_button = ttk.Button(button_frame, text="デフォルトに戻す", command=reset_defaults)
        reset_button.pack(side=tk.LEFT, padx=5)
        
        # 設定のテスト
        def test_connection():
            # 一時的に設定を適用してテスト
            temp_config = Config()
            temp_config.set("api_key", api_key_var.get())
            temp_config.set("api_base", api_base_var.get())
            temp_config.set("api_version", api_version_var.get())
            temp_config.set("deployment_name", deployment_name_var.get())
            
            temp_client = AzureOpenAIClient(temp_config)
            
            # テスト用メッセージ
            test_messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, this is a test message."}
            ]
            
            try:
                # 接続テスト中の表示
                test_button.config(state=tk.DISABLED)
                test_button.config(text="テスト中...")
                settings_window.update()
                
                # APIテスト
                success, response = temp_client.get_completion(test_messages)
                
                if success:
                    messagebox.showinfo("接続テスト", "Azure OpenAI Serviceとの接続に成功しました！")
                else:
                    messagebox.showerror("接続テスト", f"エラー: {response}")
            except Exception as e:
                messagebox.showerror("接続テスト", f"エラー: {str(e)}")
            finally:
                test_button.config(state=tk.NORMAL)
                test_button.config(text="接続テスト")
        
        test_button = ttk.Button(button_frame, text="接続テスト", command=test_connection)
        test_button.pack(side=tk.LEFT, padx=5)
    
    def show_about(self):
        """アプリケーション情報を表示する"""
        about_text = """
        Azure OpenAI 依頼やり切りアプリ

        Azure OpenAI Serviceを使用して、大きな依頼を自動的に続けて処理するアプリケーションです。
        
        特徴:
        - 大きな依頼を自動的に分割して処理
        - 応答の重複部分を検出して削除
        - エラー処理の強化
        - マークダウン形式での保存
        - カスタマイズ可能な設定
        
        Version 1.1.0
        """
        
        messagebox.showinfo("About", about_text.strip())

def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()

if __name__ == "__main__":
    main()
