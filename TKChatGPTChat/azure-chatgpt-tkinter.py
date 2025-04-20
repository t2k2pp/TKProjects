import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox, simpledialog
import os
import json
import datetime
import base64
import requests
import io
from PIL import Image, ImageTk
import uuid

class AzureChatGPTApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Azure ChatGPT チャットアプリ")
        self.root.geometry("1200x800")
        
        # アプリケーションのデータ
        self.chat_history = []
        self.current_chat_id = None
        self.current_chat_path = None
        self.image_cache = {}
        
        # Azure OpenAI APIの設定
        self.api_key = "2ixiPNoDH7V6iB5xtc0HmHw1ETAPSZheevoBwa8RyOOim6B64Hq5JQQJ99BDACHYHv6XJ3w3AAAAACOGn16N"
        self.api_endpoint = "https://terah-m9p2izk7-eastus2.openai.azure.com"
        self.api_version = "2025-01-01-preview"
        self.deployment_name = "o4-mini"
        self.system_message = "あなたは役立つアシスタントです。"
        # self.api_key = "30358ce5e16847b185b1e09c31e597ee"
        # self.api_endpoint = "https://graderpmjpje.openai.azure.com/"
        # self.api_version = "2025-01-01-preview"
        # self.deployment_name = "gpt-4o-ag"
        # self.system_message = "あなたは役立つアシスタントです。"
        
        # チャット保存ディレクトリ
        self.chats_dir = os.path.join(os.path.expanduser("~"), "azure_chatgpt_chats")
        os.makedirs(self.chats_dir, exist_ok=True)
        
        # UI作成
        self.create_ui()
        
        # 保存済みのチャット履歴を読み込む
        self.load_chat_list()

    def create_ui(self):
        # メインフレームを作成
        self.main_frame = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左側のフレーム（チャット一覧）
        left_frame = ttk.Frame(self.main_frame)
        self.main_frame.add(left_frame, weight=1)
        
        # 左上のボタンフレーム
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 新規チャットボタン
        new_chat_btn = ttk.Button(btn_frame, text="新規チャット", command=self.new_chat)
        new_chat_btn.pack(side=tk.LEFT, padx=5)
        
        # 設定ボタン
        settings_btn = ttk.Button(btn_frame, text="設定", command=self.open_settings)
        settings_btn.pack(side=tk.RIGHT, padx=5)
        
        # チャット一覧のラベル
        ttk.Label(left_frame, text="チャット履歴:", anchor="w").pack(fill=tk.X, padx=5, pady=2)
        
        # チャット一覧のリストボックス
        self.chat_listbox = tk.Listbox(left_frame, selectmode=tk.SINGLE)
        self.chat_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.chat_listbox.bind('<<ListboxSelect>>', self.on_chat_selected)
        
        # 右側のタブコントロール
        self.tab_control = ttk.Notebook(self.main_frame)
        self.main_frame.add(self.tab_control, weight=3)
        
        # チャットタブ
        self.chat_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.chat_tab, text="チャット")
        
        # コンテキストタブ
        self.context_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.context_tab, text="コンテキストウィンドウ")
        
        # チャットタブのコンテンツ
        self.create_chat_tab()
        
        # コンテキストタブのコンテンツ
        self.create_context_tab()

    def create_chat_tab(self):
        # チャット表示エリア
        chat_frame = ttk.Frame(self.chat_tab)
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # チャット履歴表示エリア
        self.chat_display = scrolledtext.ScrolledText(chat_frame, wrap=tk.WORD, state=tk.DISABLED, font=("Helvetica", 10))
        self.chat_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 入力エリアのフレーム
        input_frame = ttk.Frame(chat_frame)
        input_frame.pack(fill=tk.X, pady=5)
        
        # テキスト入力エリア
        self.chat_input = scrolledtext.ScrolledText(input_frame, height=3, wrap=tk.WORD, font=("Helvetica", 10))
        self.chat_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self.chat_input.bind("<Control-Return>", self.send_message)
        
        # ボタンフレーム
        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        
        # 画像添付ボタン
        attach_btn = ttk.Button(btn_frame, text="画像添付", command=self.attach_image)
        attach_btn.pack(side=tk.TOP, pady=2)
        
        # 送信ボタン
        send_btn = ttk.Button(btn_frame, text="送信", command=self.send_message)
        send_btn.pack(side=tk.TOP, pady=2)

    def create_context_tab(self):
        # コンテキストウィンドウのコンテンツ
        context_frame = ttk.Frame(self.context_tab)
        context_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # コンテキスト編集エリア
        self.context_editor = scrolledtext.ScrolledText(context_frame, wrap=tk.WORD, font=("Helvetica", 10))
        self.context_editor.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 保存ボタン
        save_context_btn = ttk.Button(context_frame, text="コンテキスト更新", command=self.update_context)
        save_context_btn.pack(side=tk.RIGHT, padx=5, pady=5)

    def new_chat(self):
        # 新しいチャットIDを生成
        self.current_chat_id = str(uuid.uuid4())
        self.current_chat_path = os.path.join(self.chats_dir, f"{self.current_chat_id}.json")
        
        # チャット履歴をクリア
        self.chat_history = []
        
        # UIをクリア
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete(1.0, tk.END)
        self.chat_display.config(state=tk.DISABLED)
        
        self.context_editor.delete(1.0, tk.END)
        
        # タイトルを「新規チャット」として保存
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        chat_data = {
            "id": self.current_chat_id,
            "title": f"新規チャット ({timestamp})",
            "messages": []
        }
        
        with open(self.current_chat_path, 'w', encoding='utf-8') as f:
            json.dump(chat_data, f, ensure_ascii=False, indent=2)
        
        # チャットリストを更新
        self.load_chat_list()
        
        # 新しいチャットを選択
        for i in range(self.chat_listbox.size()):
            if self.chat_listbox.get(i).startswith(f"新規チャット ({timestamp})"):
                self.chat_listbox.selection_clear(0, tk.END)
                self.chat_listbox.selection_set(i)
                self.chat_listbox.see(i)
                break

    def open_settings(self):
        # 設定ダイアログを作成
        settings_window = tk.Toplevel(self.root)
        settings_window.title("設定")
        settings_window.geometry("600x400")
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        ttk.Label(settings_window, text="Azure OpenAI API 設定", font=("Helvetica", 12, "bold")).pack(pady=10)
        
        # 設定フレーム
        settings_frame = ttk.Frame(settings_window)
        settings_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # API Key
        ttk.Label(settings_frame, text="API Key:").grid(row=0, column=0, sticky="w", pady=5)
        api_key_entry = ttk.Entry(settings_frame, width=50)
        api_key_entry.grid(row=0, column=1, sticky="we", pady=5)
        api_key_entry.insert(0, self.api_key)
        
        # エンドポイント
        ttk.Label(settings_frame, text="API エンドポイント:").grid(row=1, column=0, sticky="w", pady=5)
        endpoint_entry = ttk.Entry(settings_frame, width=50)
        endpoint_entry.grid(row=1, column=1, sticky="we", pady=5)
        endpoint_entry.insert(0, self.api_endpoint)
        
        # APIバージョン
        ttk.Label(settings_frame, text="API バージョン:").grid(row=2, column=0, sticky="w", pady=5)
        version_entry = ttk.Entry(settings_frame, width=50)
        version_entry.grid(row=2, column=1, sticky="we", pady=5)
        version_entry.insert(0, self.api_version)
        
        # デプロイメント名
        ttk.Label(settings_frame, text="デプロイメント名:").grid(row=3, column=0, sticky="w", pady=5)
        deployment_entry = ttk.Entry(settings_frame, width=50)
        deployment_entry.grid(row=3, column=1, sticky="we", pady=5)
        deployment_entry.insert(0, self.deployment_name)
        
        # システムメッセージ
        ttk.Label(settings_frame, text="システムメッセージ:").grid(row=4, column=0, sticky="nw", pady=5)
        system_text = scrolledtext.ScrolledText(settings_frame, width=40, height=10, wrap=tk.WORD)
        system_text.grid(row=4, column=1, sticky="we", pady=5)
        system_text.insert(tk.INSERT, self.system_message)
        
        settings_frame.columnconfigure(1, weight=1)
        
        # ボタンフレーム
        button_frame = ttk.Frame(settings_window)
        button_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # 保存ボタン
        def save_settings():
            self.api_key = api_key_entry.get().strip()
            self.api_endpoint = endpoint_entry.get().strip()
            self.api_version = version_entry.get().strip()
            self.deployment_name = deployment_entry.get().strip()
            self.system_message = system_text.get(1.0, tk.END).strip()
            
            # ユーザー設定を保存
            settings_path = os.path.join(self.chats_dir, "settings.json")
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "api_key": self.api_key,
                    "api_endpoint": self.api_endpoint,
                    "api_version": self.api_version,
                    "deployment_name": self.deployment_name,
                    "system_message": self.system_message
                }, f, ensure_ascii=False, indent=2)
            
            settings_window.destroy()
            messagebox.showinfo("設定", "設定が保存されました。")
        
        save_btn = ttk.Button(button_frame, text="保存", command=save_settings)
        save_btn.pack(side=tk.RIGHT, padx=5)
        
        # キャンセルボタン
        cancel_btn = ttk.Button(button_frame, text="キャンセル", command=settings_window.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=5)
        
        # 設定を読み込み
        self.load_settings()

    def load_settings(self):
        settings_path = os.path.join(self.chats_dir, "settings.json")
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                self.api_key = settings.get("api_key", "")
                self.api_endpoint = settings.get("api_endpoint", "")
                self.api_version = settings.get("api_version", "2023-03-15-preview")
                self.deployment_name = settings.get("deployment_name", "")
                self.system_message = settings.get("system_message", "あなたは役立つアシスタントです。")
            except Exception as e:
                messagebox.showerror("エラー", f"設定の読み込みに失敗しました: {str(e)}")

    def load_chat_list(self):
        # チャットリストをクリア
        self.chat_listbox.delete(0, tk.END)
        
        # チャットディレクトリからJSONファイルを検索
        chat_files = [f for f in os.listdir(self.chats_dir) if f.endswith('.json') and f != "settings.json"]
        
        # チャットデータを読み込み、リストに追加
        for file in sorted(chat_files, reverse=True):
            try:
                with open(os.path.join(self.chats_dir, file), 'r', encoding='utf-8') as f:
                    chat_data = json.load(f)
                    chat_title = chat_data.get("title", "無題のチャット")
                    self.chat_listbox.insert(tk.END, chat_title)
            except Exception as e:
                print(f"チャットの読み込みエラー {file}: {str(e)}")

    def on_chat_selected(self, event):
        # 選択されたインデックスを取得
        selection = self.chat_listbox.curselection()
        if not selection:
            return
        
        selected_title = self.chat_listbox.get(selection[0])
        
        # 選択されたタイトルに対応するJSONファイルを検索
        chat_files = [f for f in os.listdir(self.chats_dir) if f.endswith('.json') and f != "settings.json"]
        
        for file in chat_files:
            try:
                with open(os.path.join(self.chats_dir, file), 'r', encoding='utf-8') as f:
                    chat_data = json.load(f)
                    if chat_data.get("title") == selected_title:
                        # チャット履歴を読み込む
                        self.current_chat_id = chat_data.get("id")
                        self.current_chat_path = os.path.join(self.chats_dir, file)
                        self.chat_history = chat_data.get("messages", [])
                        
                        # チャット表示を更新
                        self.display_chat_history()
                        
                        # コンテキストエディタを更新
                        self.update_context_editor()
                        break
            except Exception as e:
                print(f"チャットの読み込みエラー {file}: {str(e)}")

    def display_chat_history(self):
        # チャット表示をクリア
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete(1.0, tk.END)
        
        # チャット履歴を表示
        for message in self.chat_history:
            role = message.get("role", "")
            content = message.get("content", "")
            
            # ロールに応じて色を設定
            if role == "user":
                self.chat_display.insert(tk.END, "ユーザー:\n", "user")
                self.chat_display.tag_configure("user", foreground="blue")
            elif role == "assistant":
                self.chat_display.insert(tk.END, "アシスタント:\n", "assistant")
                self.chat_display.tag_configure("assistant", foreground="green")
            elif role == "system":
                continue  # システムメッセージは表示しない
            
            # メッセージの内容を表示
            if isinstance(content, list):
                for item in content:
                    if item.get("type") == "text":
                        self.chat_display.insert(tk.END, f"{item.get('text', '')}\n\n")
                    elif item.get("type") == "image_url":
                        image_data = item.get("image_url", {}).get("url", "")
                        if image_data.startswith("data:image"):
                            # Base64エンコードされた画像を表示
                            try:
                                # data:image/jpeg;base64,の形式からBase64部分を抽出
                                image_data = image_data.split(",", 1)[1]
                                image_bytes = base64.b64decode(image_data)
                                image = Image.open(io.BytesIO(image_bytes))
                                
                                # 画像のサイズを調整（幅300px）
                                width, height = image.size
                                new_width = 300
                                new_height = int(height * (new_width / width))
                                image = image.resize((new_width, new_height))
                                
                                # PhotoImageに変換して表示
                                photo = ImageTk.PhotoImage(image)
                                
                                # 画像をキャッシュに保存（GC対策）
                                image_id = str(uuid.uuid4())
                                self.image_cache[image_id] = photo
                                
                                # 画像を挿入する位置を取得
                                position = self.chat_display.index(tk.INSERT)
                                self.chat_display.image_create(position, image=photo)
                                self.chat_display.insert(tk.END, "\n\n")
                            except Exception as e:
                                self.chat_display.insert(tk.END, f"[画像の表示に失敗しました: {str(e)}]\n\n")
            else:
                self.chat_display.insert(tk.END, f"{content}\n\n")
            
            self.chat_display.insert(tk.END, "-" * 50 + "\n\n")
        
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def update_context_editor(self):
        # コンテキストエディタをクリア
        self.context_editor.delete(1.0, tk.END)
        
        # チャット履歴を編集可能な形式で表示
        for i, message in enumerate(self.chat_history):
            role = message.get("role", "")
            content = message.get("content", "")
            
            if role == "system":
                self.context_editor.insert(tk.END, f"システム ({i}):\n", "system")
                self.context_editor.tag_configure("system", foreground="red")
            elif role == "user":
                self.context_editor.insert(tk.END, f"ユーザー ({i}):\n", "user")
                self.context_editor.tag_configure("user", foreground="blue")
            elif role == "assistant":
                self.context_editor.insert(tk.END, f"アシスタント ({i}):\n", "assistant")
                self.context_editor.tag_configure("assistant", foreground="green")
            
            # メッセージの内容を表示（画像はURLとして表示）
            if isinstance(content, list):
                for item in content:
                    if item.get("type") == "text":
                        self.context_editor.insert(tk.END, f"{item.get('text', '')}\n")
                    elif item.get("type") == "image_url":
                        self.context_editor.insert(tk.END, "[画像データ]\n")
            else:
                self.context_editor.insert(tk.END, f"{content}\n")
            
            self.context_editor.insert(tk.END, "-" * 50 + "\n\n")

    def update_context(self):
        if not self.current_chat_path:
            messagebox.showinfo("エラー", "チャットが選択されていません。")
            return
        
        # 実装はシンプルにするため、コンテキストの更新は新しいチャット履歴で置き換える
        # (実際のアプリケーションではより洗練された編集機能を実装するべきです)
        result = messagebox.askyesno("確認", "コンテキストの更新はまだ実装されていません。この機能は今後のバージョンで追加される予定です。")
        if result:
            messagebox.showinfo("情報", "現在のバージョンでは、コンテキストウィンドウは閲覧専用です。")

    def attach_image(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("画像ファイル", "*.png *.jpg *.jpeg *.gif *.bmp *.webp")]
        )
        
        if file_path:
            try:
                # 画像をBase64エンコード
                with open(file_path, "rb") as image_file:
                    image_data = base64.b64encode(image_file.read()).decode()
                
                # 画像の形式を取得
                image_format = os.path.splitext(file_path)[1][1:].lower()
                if image_format == "jpg":
                    image_format = "jpeg"
                
                # 画像をチャット入力に挿入
                self.chat_input.insert(tk.END, f"[添付画像: {os.path.basename(file_path)}]\n")
                
                # 画像データを一時保存
                if not hasattr(self, "attached_images"):
                    self.attached_images = []
                
                self.attached_images.append({
                    "data": image_data,
                    "format": image_format
                })
                
                messagebox.showinfo("画像添付", "画像が添付されました。送信時にメッセージと一緒に送信されます。")
            except Exception as e:
                messagebox.showerror("エラー", f"画像の添付に失敗しました: {str(e)}")

    def send_message(self, event=None):
        if not self.current_chat_path:
            messagebox.showinfo("エラー", "新規チャットを作成してください。")
            return
        
        # 入力テキストを取得
        message_text = self.chat_input.get(1.0, tk.END).strip()
        
        if not message_text and not hasattr(self, "attached_images"):
            messagebox.showinfo("エラー", "メッセージを入力してください。")
            return
        
        # ユーザーメッセージの準備
        user_message = {
            "role": "user"
        }
        
        # 画像が添付されている場合
        content_items = []
        
        if message_text:
            content_items.append({
                "type": "text",
                "text": message_text
            })
        
        if hasattr(self, "attached_images") and self.attached_images:
            for img in self.attached_images:
                content_items.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/{img['format']};base64,{img['data']}"
                    }
                })
            
            # 添付画像をクリア
            self.attached_images = []
        
        if content_items:
            user_message["content"] = content_items
        else:
            user_message["content"] = message_text
        
        # チャット履歴に追加
        self.chat_history.append(user_message)
        
        # 入力欄をクリア
        self.chat_input.delete(1.0, tk.END)
        
        # チャット表示を更新
        self.display_chat_history()
        
        # コンテキストエディタを更新
        self.update_context_editor()
        
        # チャットを保存
        self.save_chat()
        
        # APIリクエストを送信
        self.send_to_azure_openai()

    def send_to_azure_openai(self):
        if not self.api_key or not self.api_endpoint or not self.deployment_name:
            messagebox.showinfo("エラー", "Azure OpenAI APIの設定を行ってください。")
            return
        
        try:
            # チャット履歴からAPIリクエスト用のメッセージを作成
            messages = []
            
            # システムメッセージを追加
            if self.system_message:
                messages.append({
                    "role": "system",
                    "content": self.system_message
                })
            
            # チャット履歴を追加
            for message in self.chat_history:
                messages.append(message)
            
            # APIエンドポイント
            endpoint = f"{self.api_endpoint}/openai/deployments/{self.deployment_name}/chat/completions?api-version={self.api_version}"
            # https://terah-m9p2izk7-eastus2.openai.azure.com/openai/deployments/o4-mini/chat/completions?api-version=2025-01-01-preview

            # リクエストヘッダー
            headers = {
                "Content-Type": "application/json",
                "api-key": self.api_key
            }
            
            # リクエストボディ
            body = {
                "messages": messages,
                "max_tokens": 2000
            }
            
            # 画像が添付されている場合はGPT-4-Visionを使用する設定
            for message in messages:
                content = message.get("content", "")
                if isinstance(content, list) and any(item.get("type") == "image_url" for item in content):
                    # body["model"] = "gpt-4-vision"  # Azureの場合はデプロイメント設定に依存
                    break
            
            # APIリクエストを送信
            response = requests.post(endpoint, headers=headers, json=body)
            response.raise_for_status()
            
            # レスポンスを解析
            resp_data = response.json()
            
            # アシスタントの応答を取得
            if "choices" in resp_data and len(resp_data["choices"]) > 0:
                assistant_message = resp_data["choices"][0]["message"]
                
                # チャット履歴に追加
                self.chat_history.append(assistant_message)
                
                # チャット表示を更新
                self.display_chat_history()
                
                # コンテキストエディタを更新
                self.update_context_editor()
                
                # チャットを保存
                self.save_chat()
            else:
                messagebox.showerror("エラー", "APIレスポンスが無効です。")
        
        except Exception as e:
            messagebox.showerror("エラー", f"APIリクエスト中にエラーが発生しました: {str(e)}")

    def save_chat(self):
        if not self.current_chat_path:
            return
        
        try:
            # チャットのタイトルを決定（最初のユーザーメッセージから）
            chat_title = "無題のチャット"
            for message in self.chat_history:
                if message.get("role") == "user":
                    content = message.get("content", "")
                    if isinstance(content, list):
                        for item in content:
                            if item.get("type") == "text":
                                text = item.get("text", "").strip()
                                if text:
                                    chat_title = text[:30] + ("..." if len(text) > 30 else "")
                                    break
                    else:
                        text = content.strip()
                        if text:
                            chat_title = text[:30] + ("..." if len(text) > 30 else "")
                    break
            
            # チャットデータを保存
            chat_data = {
                "id": self.current_chat_id,
                "title": chat_title,
                "messages": self.chat_history
            }
            
            with open(self.current_chat_path, 'w', encoding='utf-8') as f:
                json.dump(chat_data, f, ensure_ascii=False, indent=2)
            
            # チャットリストを更新（タイトルが変更された場合のため）
            self.load_chat_list()
        except Exception as e:
            messagebox.showerror("エラー", f"チャットの保存中にエラーが発生しました: {str(e)}")

    def rename_current_chat(self):
        if not self.current_chat_path:
            messagebox.showinfo("エラー", "チャットが選択されていません。")
            return
        
        # 現在のチャットデータを読み込む
        try:
            with open(self.current_chat_path, 'r', encoding='utf-8') as f:
                chat_data = json.load(f)
            
            # 新しいタイトルを入力
            new_title = simpledialog.askstring(
                "チャット名変更", 
                "新しいチャット名を入力してください:",
                initialvalue=chat_data.get("title", "")
            )
            
            if new_title:
                # タイトルを更新して保存
                chat_data["title"] = new_title
                
                with open(self.current_chat_path, 'w', encoding='utf-8') as f:
                    json.dump(chat_data, f, ensure_ascii=False, indent=2)
                
                # チャットリストを更新
                self.load_chat_list()
        except Exception as e:
            messagebox.showerror("エラー", f"チャット名の変更中にエラーが発生しました: {str(e)}")

    def delete_current_chat(self):
        if not self.current_chat_path:
            messagebox.showinfo("エラー", "チャットが選択されていません。")
            return
        
        # 確認ダイアログ
        result = messagebox.askyesno("確認", "現在のチャットを削除してもよろしいですか？")
        if not result:
            return
        
        try:
            # ファイルを削除
            os.remove(self.current_chat_path)
            
            # 現在のチャット情報をクリア
            self.current_chat_id = None
            self.current_chat_path = None
            self.chat_history = []
            
            # UIをクリア
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete(1.0, tk.END)
            self.chat_display.config(state=tk.DISABLED)
            
            self.context_editor.delete(1.0, tk.END)
            
            # チャットリストを更新
            self.load_chat_list()
            
            messagebox.showinfo("成功", "チャットが削除されました。")
        except Exception as e:
            messagebox.showerror("エラー", f"チャットの削除中にエラーが発生しました: {str(e)}")

    def export_chat(self):
        if not self.current_chat_path:
            messagebox.showinfo("エラー", "チャットが選択されていません。")
            return
        
        # 保存先を選択
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSONファイル", "*.json"), ("テキストファイル", "*.txt"), ("すべてのファイル", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            # 現在のチャットをコピー
            with open(self.current_chat_path, 'r', encoding='utf-8') as src:
                with open(file_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            
            messagebox.showinfo("成功", "チャットがエクスポートされました。")
        except Exception as e:
            messagebox.showerror("エラー", f"チャットのエクスポート中にエラーが発生しました: {str(e)}")

    def import_chat(self):
        # インポートするファイルを選択
        file_path = filedialog.askopenfilename(
            filetypes=[("JSONファイル", "*.json"), ("テキストファイル", "*.txt"), ("すべてのファイル", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            # JSONファイルを検証
            with open(file_path, 'r', encoding='utf-8') as f:
                chat_data = json.load(f)
            
            # 必要なフィールドが存在するか確認
            if not chat_data.get("id") or not isinstance(chat_data.get("messages"), list):
                messagebox.showerror("エラー", "無効なチャットデータ形式です。")
                return
            
            # 新しいIDを生成（重複を避けるため）
            chat_data["id"] = str(uuid.uuid4())
            
            # チャットファイルを保存
            new_path = os.path.join(self.chats_dir, f"{chat_data['id']}.json")
            with open(new_path, 'w', encoding='utf-8') as f:
                json.dump(chat_data, f, ensure_ascii=False, indent=2)
            
            # チャットリストを更新
            self.load_chat_list()
            
            messagebox.showinfo("成功", "チャットがインポートされました。")
        except Exception as e:
            messagebox.showerror("エラー", f"チャットのインポート中にエラーが発生しました: {str(e)}")


def main():
    root = tk.Tk()
    app = AzureChatGPTApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
