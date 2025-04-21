import os
import json
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
from datetime import datetime
import base64
from pathlib import Path
from PIL import Image, ImageTk
import io
import threading
import time
from openai import AzureOpenAI

class ChatGPTApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Azure ChatGPT Chat")
        self.root.geometry("1200x800")
        
        # アプリケーションデータディレクトリの設定
        self.app_data_dir = os.path.join(os.path.expanduser("~"), ".azure_chatgpt_app")
        os.makedirs(self.app_data_dir, exist_ok=True)
        
        # チャット履歴保存ディレクトリ
        self.chat_history_dir = os.path.join(self.app_data_dir, "chat_history")
        os.makedirs(self.chat_history_dir, exist_ok=True)
        
        # 設定ファイルのパス
        self.config_file = os.path.join(self.app_data_dir, "config.json")
        
        # デフォルト設定の読み込み
        self.load_config()
        
        # クライアントの初期化
        self.initialize_client()
        
        # 現在のチャットセッション情報
        self.current_chat_id = None
        self.current_chat_path = None
        self.chat_messages = []
        self.context_messages = []
        
        # 左側のフレーム（チャット履歴リスト）
        self.left_frame = ttk.Frame(root, width=200)
        self.left_frame.pack(fill=tk.Y, side=tk.LEFT, padx=5, pady=5)
        
        # 新規チャットボタン
        ttk.Button(self.left_frame, text="新規チャット", command=self.new_chat).pack(fill=tk.X, padx=5, pady=5)
        
        # チャット履歴リスト
        ttk.Label(self.left_frame, text="チャット履歴").pack(anchor=tk.W, padx=5)
        self.history_listbox = tk.Listbox(self.left_frame, width=25, height=30)
        self.history_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.history_listbox.bind('<<ListboxSelect>>', self.load_selected_chat)
        
        # 右側のメインフレーム（タブを含む）
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT, padx=5, pady=5)
        
        # タブ管理
        self.tab_control = ttk.Notebook(self.main_frame)
        
        # チャットタブ
        self.chat_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.chat_tab, text="チャット")
        
        # コンテキストタブ
        self.context_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.context_tab, text="コンテキスト")
        
        # 設定タブ
        self.settings_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.settings_tab, text="設定")
        
        self.tab_control.pack(fill=tk.BOTH, expand=True)
        
        # チャットタブのUI構築
        self.setup_chat_tab()
        
        # コンテキストタブのUI構築
        self.setup_context_tab()
        
        # 設定タブのUI構築
        self.setup_settings_tab()
        
        # チャット履歴を更新
        self.update_chat_history_list()
        
        # 新規チャットを開始
        self.new_chat()

    def load_config(self):
        # デフォルト設定
        self.config = {
            "api_key": "",
            "endpoint": "",
            "api_version": "2024-04-01",
            "deployment_name": "gpt-4o-mini",
            "system_message": "あなたは有能なAIアシスタントです。ユーザーの質問に的確に回答してください。",
            "max_tokens": 4000,
            "temperature": 0.7
        }
        
        # 設定ファイルが存在する場合は読み込む
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    # 既存の設定を更新
                    self.config.update(saved_config)
            except Exception as e:
                messagebox.showerror("設定エラー", f"設定ファイルの読み込みに失敗しました: {e}")
    
    def save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            messagebox.showerror("設定エラー", f"設定ファイルの保存に失敗しました: {e}")
    
    def initialize_client(self):
        try:
            if self.config["api_key"] and self.config["endpoint"]:
                self.client = AzureOpenAI(
                    api_key=self.config["api_key"],
                    azure_endpoint=self.config["endpoint"],
                    api_version=self.config["api_version"],
                )
            else:
                self.client = None
        except Exception as e:
            messagebox.showerror("API初期化エラー", f"Azure OpenAI APIの初期化に失敗しました: {e}")
            self.client = None
    
    def setup_chat_tab(self):
        # チャット表示エリア
        self.chat_frame = ttk.Frame(self.chat_tab)
        self.chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # チャットメッセージの表示エリア
        self.chat_display = scrolledtext.ScrolledText(self.chat_frame, wrap=tk.WORD, bg="#f0f0f0", state=tk.DISABLED)
        self.chat_display.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.chat_display.tag_configure("user", background="#e6f2ff", justify='right')
        self.chat_display.tag_configure("assistant", background="#f5f5f5", justify='left')
        
        # 入力エリア
        self.input_frame = ttk.Frame(self.chat_frame)
        self.input_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # 画像添付ボタン
        self.attach_button = ttk.Button(self.input_frame, text="画像添付", command=self.attach_image)
        self.attach_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # メッセージ入力欄
        self.message_entry = scrolledtext.ScrolledText(self.input_frame, wrap=tk.WORD, height=4)
        self.message_entry.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=(0, 5))
        self.message_entry.bind("<Control-Return>", self.send_message_event)
        
        # 送信ボタン
        self.send_button = ttk.Button(self.input_frame, text="送信", command=self.send_message)
        self.send_button.pack(side=tk.RIGHT)
        
        # 添付画像の情報
        self.attached_image = None
        self.attached_image_path = None
        self.image_preview_label = None
    
    def setup_context_tab(self):
        self.context_frame = ttk.Frame(self.context_tab)
        self.context_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # コンテキスト編集エリア
        ttk.Label(self.context_frame, text="コンテキスト（会話履歴）").pack(anchor=tk.W)
        self.context_text = scrolledtext.ScrolledText(self.context_frame, wrap=tk.WORD)
        self.context_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 更新ボタン
        ttk.Button(self.context_frame, text="コンテキストを更新", command=self.update_context).pack(anchor=tk.E)
    
    def setup_settings_tab(self):
        settings_frame = ttk.Frame(self.settings_tab)
        settings_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 設定フォーム
        ttk.Label(settings_frame, text="Azure OpenAI API キー").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.api_key_entry = ttk.Entry(settings_frame, width=50, show="*")
        self.api_key_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        self.api_key_entry.insert(0, self.config["api_key"])
        
        ttk.Label(settings_frame, text="エンドポイントURL").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.endpoint_entry = ttk.Entry(settings_frame, width=50)
        self.endpoint_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        self.endpoint_entry.insert(0, self.config["endpoint"])
        
        ttk.Label(settings_frame, text="APIバージョン").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.api_version_entry = ttk.Entry(settings_frame, width=50)
        self.api_version_entry.grid(row=2, column=1, sticky=tk.W, pady=5)
        self.api_version_entry.insert(0, self.config["api_version"])
        
        ttk.Label(settings_frame, text="デプロイメント名").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.deployment_entry = ttk.Entry(settings_frame, width=50)
        self.deployment_entry.grid(row=3, column=1, sticky=tk.W, pady=5)
        self.deployment_entry.insert(0, self.config["deployment_name"])
        
        ttk.Label(settings_frame, text="最大トークン数").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.max_tokens_entry = ttk.Entry(settings_frame, width=10)
        self.max_tokens_entry.grid(row=4, column=1, sticky=tk.W, pady=5)
        self.max_tokens_entry.insert(0, str(self.config["max_tokens"]))
        
        ttk.Label(settings_frame, text="温度").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.temperature_entry = ttk.Entry(settings_frame, width=10)
        self.temperature_entry.grid(row=5, column=1, sticky=tk.W, pady=5)
        self.temperature_entry.insert(0, str(self.config["temperature"]))
        
        ttk.Label(settings_frame, text="システムメッセージ").grid(row=6, column=0, sticky=tk.W, pady=5)
        self.system_message_text = scrolledtext.ScrolledText(settings_frame, wrap=tk.WORD, width=50, height=6)
        self.system_message_text.grid(row=6, column=1, sticky=tk.W, pady=5)
        self.system_message_text.insert(tk.END, self.config["system_message"])
        
        # 保存ボタン
        ttk.Button(settings_frame, text="設定を保存", command=self.save_settings).grid(row=7, column=1, sticky=tk.E, pady=10)
    
    def save_settings(self):
        # 設定の取得
        self.config["api_key"] = self.api_key_entry.get()
        self.config["endpoint"] = self.endpoint_entry.get()
        self.config["api_version"] = self.api_version_entry.get()
        self.config["deployment_name"] = self.deployment_entry.get()
        self.config["system_message"] = self.system_message_text.get("1.0", tk.END).strip()
        
        try:
            self.config["max_tokens"] = int(self.max_tokens_entry.get())
        except ValueError:
            messagebox.showerror("入力エラー", "最大トークン数には数値を入力してください")
            return
        
        try:
            self.config["temperature"] = float(self.temperature_entry.get())
            if not 0 <= self.config["temperature"] <= 2:
                messagebox.showerror("入力エラー", "温度は0から2の間で指定してください")
                return
        except ValueError:
            messagebox.showerror("入力エラー", "温度には数値を入力してください")
            return
        
        # 設定の保存
        self.save_config()
        
        # クライアントの再初期化
        self.initialize_client()
        
        messagebox.showinfo("設定", "設定を保存しました")
    
    def update_chat_history_list(self):
        # リストボックスをクリア
        self.history_listbox.delete(0, tk.END)
        
        try:
            # チャット履歴ディレクトリ内のフォルダを取得
            chat_folders = sorted([d for d in os.listdir(self.chat_history_dir) 
                               if os.path.isdir(os.path.join(self.chat_history_dir, d))],
                              reverse=True)
            
            # リストボックスに追加
            for folder in chat_folders:
                chat_file = os.path.join(self.chat_history_dir, folder, "chat.json")
                if os.path.exists(chat_file):
                    try:
                        with open(chat_file, 'r', encoding='utf-8') as f:
                            chat_data = json.load(f)
                        
                        # タイトルを表示（最初のユーザーメッセージの最初の20文字）
                        title = ""
                        for msg in chat_data.get("messages", []):
                            if msg.get("role") == "user" and msg.get("content"):
                                if isinstance(msg["content"], str):
                                    title = msg["content"][:20] + "..." if len(msg["content"]) > 20 else msg["content"]
                                    break
                                elif isinstance(msg["content"], list):
                                    for item in msg["content"]:
                                        if isinstance(item, dict) and item.get("type") == "text":
                                            title = item["text"][:20] + "..." if len(item["text"]) > 20 else item["text"]
                                            break
                                    if title:
                                        break
                        
                        if not title:
                            title = f"チャット {folder}"
                        
                        # チャットIDをリストの項目に関連付ける
                        position = self.history_listbox.size()  # 現在のリストの長さを取得
                        self.history_listbox.insert(tk.END, title)
                        setattr(self.history_listbox, f"chat_id_{position}", folder)
                        print(f"Added chat: position={position}, id={folder}, title={title}")  # デバッグ用
                        
                    except Exception as e:
                        print(f"チャットファイル読み込みエラー ({chat_file}): {str(e)}")
        
        except Exception as e:
            print(f"チャット履歴の更新エラー: {str(e)}")
    
    def new_chat(self):
        # 新しいチャットIDを生成（タイムスタンプベース）
        self.current_chat_id = datetime.now().strftime("%Y%m%d%H%M%S")
        self.current_chat_path = os.path.join(self.chat_history_dir, self.current_chat_id)
        os.makedirs(self.current_chat_path, exist_ok=True)
        
        # チャットメッセージをクリア
        self.chat_messages = []
        self.context_messages = []
        
        # システムメッセージを追加
        if self.config["system_message"]:
            self.chat_messages.append({"role": "system", "content": self.config["system_message"]})
            self.context_messages.append({"role": "system", "content": self.config["system_message"]})
        
        # UIをクリア
        self.clear_chat_display()
        self.context_text.delete("1.0", tk.END)
        
        # チャットを保存
        self.save_chat()
        
        # チャット履歴リストを更新
        self.update_chat_history_list()
    
    def load_selected_chat(self, event):
        print("=== load_selected_chat called ===")  # デバッグ用
        
        # 選択されたアイテムのインデックスを取得
        selected_idx = self.history_listbox.curselection()
        print(f"Selected index: {selected_idx}")  # デバッグ用
        
        if not selected_idx:
            print("No selection")  # デバッグ用
            return
        
        try:
            # 選択されたアイテムに関連付けられたチャットIDを取得
            position = selected_idx[0]
            chat_id = getattr(self.history_listbox, f"chat_id_{position}", None)
            print(f"Loading chat: position={position}, id={chat_id}")  # デバッグ用
            
            if not chat_id:
                print("No chat ID found for position")  # デバッグ用
                return
            
            chat_file = os.path.join(self.chat_history_dir, chat_id, "chat.json")
            if not os.path.exists(chat_file):
                print(f"Chat file not found: {chat_file}")  # デバッグ用
                return
                
            with open(chat_file, 'r', encoding='utf-8') as f:
                chat_data = json.load(f)
                print(f"Loaded chat data structure: {chat_data.keys()}")  # デバッグ追加
                print(f"Messages format: {type(chat_data.get('messages', []))}")

            self.current_chat_id = chat_id
            self.current_chat_path = os.path.join(self.chat_history_dir, chat_id)
            self.chat_messages = chat_data.get("messages", [])
            self.context_messages = self.chat_messages.copy()
            
            print(f"Loaded {len(self.chat_messages)} messages")  # デバッグ用
            
            self.clear_chat_display()
            self.display_chat_messages()
            self.update_context_display()
            
        except Exception as e:
            print(f"チャット読み込みエラー: {str(e)}")
            import traceback
            traceback.print_exc()  # スタックトレースを出力
            messagebox.showerror("読み込みエラー", f"チャットの読み込みに失敗しました: {e}")
    
    def clear_chat_display(self):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete("1.0", tk.END)
        self.chat_display.config(state=tk.DISABLED)
        
        # 添付画像をクリア
        self.attached_image = None
        self.attached_image_path = None
        if self.image_preview_label:
            self.image_preview_label.destroy()
            self.image_preview_label = None
    
    def display_chat_messages(self):
        print("Displaying chat messages...")  # デバッグ用
        try:
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete("1.0", tk.END)
            
            for msg in self.chat_messages:
                if msg["role"] == "system":
                    continue
                
                role = msg["role"]
                role_display = "ユーザー" if role == "user" else "アシスタント"
                
                # 役割の表示
                self.chat_display.insert(tk.END, f"\n{role_display}:\n", role)
                
                # コンテンツの表示
                if isinstance(msg["content"], str):
                    self.chat_display.insert(tk.END, f"{msg['content']}\n", role)
                elif isinstance(msg["content"], list):
                    for item in msg["content"]:
                        if item.get("type") == "text":
                            self.chat_display.insert(tk.END, f"{item['text']}\n", role)
                        elif item.get("type") == "image_url" and "image_path" in item:
                            try:
                                image_path = item["image_path"]
                                if os.path.exists(image_path):
                                    img = Image.open(image_path)
                                    img = self.resize_image(img, 300)
                                    photo = ImageTk.PhotoImage(img)
                                    
                                    image_label = ttk.Label(self.chat_display, image=photo)
                                    image_label.image = photo
                                    
                                    self.chat_display.insert(tk.END, "\n")
                                    self.chat_display.window_create(tk.END, window=image_label)
                                    self.chat_display.insert(tk.END, "\n")
                            except Exception as e:
                                print(f"画像表示エラー: {e}")  # デバッグ用
                                self.chat_display.insert(tk.END, f"[画像の表示に失敗しました: {e}]\n", role)
            
            self.chat_display.config(state=tk.DISABLED)
            self.chat_display.see(tk.END)
            
        except Exception as e:
            print(f"メッセージ表示エラー: {e}")  # デバッグ用
            messagebox.showerror("表示エラー", f"メッセージの表示に失敗しました: {e}")
    
    def update_context_display(self):
        self.context_text.delete("1.0", tk.END)
        
        for msg in self.context_messages:
            role = msg["role"]
            role_display = {"system": "システム", "user": "ユーザー", "assistant": "アシスタント"}.get(role, role)
            
            if isinstance(msg["content"], str):
                self.context_text.insert(tk.END, f"{role_display}: {msg['content']}\n\n")
            elif isinstance(msg["content"], list):
                content_text = []
                for item in msg["content"]:
                    if item["type"] == "text":
                        content_text.append(item["text"])
                    elif item["type"] == "image_url":
                        content_text.append("[画像]")
                self.context_text.insert(tk.END, f"{role_display}: {' '.join(content_text)}\n\n")
    
    def update_context(self):
        # コンテキストウィンドウの内容を解析
        raw_text = self.context_text.get("1.0", tk.END).strip()
        lines = raw_text.split("\n")
        
        new_messages = []
        current_role = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # ロール判定（"ロール名: "の形式を期待）
            if line.startswith("システム: "):
                # 前のメッセージがあれば保存
                if current_role:
                    content = "\n".join(current_content)
                    new_messages.append({"role": current_role, "content": content})
                
                current_role = "system"
                current_content = [line[len("システム: "):]]
            elif line.startswith("ユーザー: "):
                # 前のメッセージがあれば保存
                if current_role:
                    content = "\n".join(current_content)
                    new_messages.append({"role": current_role, "content": content})
                
                current_role = "user"
                current_content = [line[len("ユーザー: "):]]
            elif line.startswith("アシスタント: "):
                # 前のメッセージがあれば保存
                if current_role:
                    content = "\n".join(current_content)
                    new_messages.append({"role": current_role, "content": content})
                
                current_role = "assistant"
                current_content = [line[len("アシスタント: "):]]
            else:
                # 継続行
                if current_role:
                    current_content.append(line)
        
        # 最後のメッセージを保存
        if current_role:
            content = "\n".join(current_content)
            new_messages.append({"role": current_role, "content": content})
        
        # メッセージを更新
        if new_messages:
            self.context_messages = new_messages
            messagebox.showinfo("コンテキスト", "コンテキストを更新しました")
        else:
            messagebox.showerror("エラー", "有効なメッセージが見つかりませんでした")
    
    def attach_image(self):
        # 画像ファイル選択ダイアログ
        file_path = filedialog.askopenfilename(
            title="画像を選択",
            filetypes=[("画像ファイル", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )
        
        if file_path:
            try:
                # 画像を開く
                img = Image.open(file_path)
                
                # 画像のリサイズ（プレビュー用）
                img_preview = self.resize_image(img, 150)
                photo = ImageTk.PhotoImage(img_preview)
                
                # 既存のプレビューを削除
                if self.image_preview_label:
                    self.image_preview_label.destroy()
                
                # プレビュー表示
                self.image_preview_label = ttk.Label(self.input_frame, image=photo)
                self.image_preview_label.image = photo  # ガベージコレクションの防止
                self.image_preview_label.pack(side=tk.LEFT, before=self.message_entry)
                
                # 画像情報を保存
                self.attached_image = img
                self.attached_image_path = file_path
            except Exception as e:
                messagebox.showerror("画像読み込みエラー", f"画像の読み込みに失敗しました: {e}")
    
    def resize_image(self, img, max_size):
        width, height = img.size
        ratio = min(max_size / width, max_size / height)
        
        if ratio < 1:  # リサイズが必要な場合のみ
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            return img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        return img
    
    def send_message_event(self, event):
        self.send_message()
        return "break"  # イベントの伝播を停止
    
    def send_message(self):
        # メッセージテキストを取得し、入力欄をクリア
        message_text = self.message_entry.get("1.0", tk.END).strip()
        self.message_entry.delete("1.0", tk.END)
        
        if not message_text and not self.attached_image:
            messagebox.showinfo("入力エラー", "メッセージまたは画像を入力してください")
            return
        
        # 送信ボタンを無効化
        self.send_button.config(state=tk.DISABLED)
        
        # ユーザーメッセージの作成
        if self.attached_image:
            # 画像を保存
            image_filename = f"image_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
            image_path = os.path.join(self.current_chat_path, image_filename)
            self.attached_image.save(image_path)
            
            # マルチモーダルメッセージの作成
            content = []
            if message_text:
                content.append({"type": "text", "text": message_text})
            
            content.append({
                "type": "image_url",
                "image_url": f"data:image/jpeg;base64,placeholder",  # プレースホルダ
                "image_path": image_path  # ローカルパスを保存
            })
            
            user_message = {"role": "user", "content": content}
        else:
            user_message = {"role": "user", "content": message_text}
        
        # メッセージを追加
        self.chat_messages.append(user_message)
        self.context_messages.append(user_message)
        
        # チャット表示を更新
        self.clear_chat_display()
        self.display_chat_messages()
        self.update_context_display()
        
        # プレビューをクリア
        if self.image_preview_label:
            self.image_preview_label.destroy()
            self.image_preview_label = None
        self.attached_image = None
        
        # ChatGPT APIリクエストを別スレッドで実行
        threading.Thread(target=self.get_chatgpt_response).start()
    
    def get_chatgpt_response(self):
        try:
            if not self.client:
                messagebox.showerror("API接続エラー", "Azure OpenAI APIが設定されていません。設定タブで設定を行ってください。")
                self.send_button.config(state=tk.NORMAL)
                return
            
            # API用のメッセージ配列を準備
            api_messages = []
            
            # コンテキストメッセージを使用
            for msg in self.context_messages:
                # 画像を含むメッセージの変換
                if isinstance(msg["content"], list):
                    content_list = []
                    for item in msg["content"]:
                        if item["type"] == "text":
                            content_list.append({"type": "text", "text": item["text"]})
                        elif item["type"] == "image_url" and "image_path" in item:
                            # 画像ファイルを読み込んでbase64エンコード
                            with open(item["image_path"], "rb") as image_file:
                                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                            
                            content_list.append({
                                "type": "image_url",
                                "image_url": f"data:image/jpeg;base64,{base64_image}"
                            })
                    api_message = {"role": msg["role"], "content": content_list}
                else:
                    api_message = {"role": msg["role"], "content": msg["content"]}
                
                api_messages.append(api_message)
            
            # 応答の生成
            response = self.client.chat.completions.create(
                model=self.config["deployment_name"],
                messages=api_messages,
                max_completion_tokens=self.config["max_tokens"],
                
                # max_tokens=self.config["max_tokens"],
                #temperature=self.config["temperature"]
            )
            
            # 応答テキストの取得
            assistant_message = response.choices[0].message
            
            # チャットメッセージに追加
            self.chat_messages.append({"role": "assistant", "content": assistant_message.content})
            self.context_messages.append({"role": "assistant", "content": assistant_message.content})
            
            # チャットを保存
            self.save_chat()
            
            # UIを更新
            self.root.after(0, self.update_ui_after_response)
            
        except Exception as e:
            error_message = f"APIエラー: {e}"
            print(error_message)
            self.root.after(0, lambda: self.show_api_error(error_message))
        finally:
            # 送信ボタンを再有効化
            self.root.after(0, lambda: self.send_button.config(state=tk.NORMAL))
    
    def show_api_error(self, error_message):
        messagebox.showerror("API通信エラー", error_message)
    
    def update_ui_after_response(self):
        # チャット表示を更新
        self.clear_chat_display()
        self.display_chat_messages()
        self.update_context_display()
        
        # チャット履歴リストを更新
        self.update_chat_history_list()
    
    def save_chat(self):
        # チャットメッセージを保存
        chat_file = os.path.join(self.current_chat_path, "chat.json")
        
        # 保存用のデータを作成
        chat_data = {
            "id": self.current_chat_id,
            "created_at": datetime.now().isoformat(),
            "messages": self.chat_messages
        }
        
        try:
            with open(chat_file, 'w', encoding='utf-8') as f:
                json.dump(chat_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"チャット保存エラー: {e}")

def main():
    root = tk.Tk()
    app = ChatGPTApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()