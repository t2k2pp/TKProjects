import os
import sys
import io
import json
import base64
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk  # Pillow が必要です
# ↓↓↓ OpenAI v1.x のインポートに変更 ↓↓↓
from openai import AzureOpenAI, APIError
# ↑↑↑ OpenAI v1.x のインポートに変更 ↑↑↑

#
# 1) 設定／セッション保存先ディレクトリ (変更なし)
#
if sys.platform.startswith("win"):
    APPDATA = os.getenv("APPDATA")
    BASE_DIR = os.path.join(APPDATA, "tkchatgpt")
else:
    BASE_DIR = os.path.expanduser("~/.tkchatgpt")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)

#
# 2) 設定ロード／保存 (変更なし)
#
def load_config():
    default = {
        "api_base": "https://YOUR_RESOURCE.openai.azure.com/", # api_type は不要に
        "api_version": "2024-03-15-preview",
        "api_key": "",
        "deployment": "o3-mini", # モデル名 (デプロイ名)
        "system_message": "You are a helpful assistant."
    }
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        # 古い api_type キーがあれば削除
        cfg.pop("api_type", None)
        default.update(cfg)
    except FileNotFoundError:
        pass
    return default

def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    # 古い api_type キーがあれば削除してから保存
    cfg.pop("api_type", None)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

#
# 3) OpenAI(Azure) 初期化 (関数自体を削除し、ChatApp 内でクライアントを作成)
#
# def init_openai(cfg): <-- この関数は不要になる

#
# 4) メイン App
#
class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Tk-Azure ChatGPT (v1.x)") # タイトル変更
        self.config = load_config()
        # ↓↓↓ クライアント初期化処理を追加 ↓↓↓
        self.client = self._create_openai_client(self.config)
        # ↑↑↑ クライアント初期化処理を追加 ↑↑↑

        self.current_session = None
        self.messages = []
        self._img_refs = [] # 画像参照を保持するリストを初期化

        self._build_main_ui()
        self._load_session_list()

    # ↓↓↓ OpenAI クライアント作成メソッドを追加 ↓↓↓
    def _create_openai_client(self, cfg):
        try:
            # AzureOpenAI クライアントを作成
            client = AzureOpenAI(
                azure_endpoint=cfg["api_base"],
                api_key=cfg["api_key"],
                api_version=cfg["api_version"]
            )
            return client
        except Exception as e:
            messagebox.showerror("Initialization Error", f"Failed to initialize OpenAI client: {e}")
            return None
    # ↑↑↑ OpenAI クライアント作成メソッドを追加 ↑↑↑

    def _build_main_ui(self):
        # (UI構築部分は変更なし)
        frm = ttk.Frame(self.root)
        frm.pack(fill="both", expand=True)

        # 左：セッション一覧
        left = ttk.Frame(frm, width=200)
        left.pack(side="left", fill="y")
        ttk.Label(left, text="Sessions").pack(pady=5)
        self.session_list = tk.Listbox(left)
        self.session_list.pack(fill="y", expand=True, padx=5)
        self.session_list.bind("<<ListboxSelect>>", self.on_select_session)
        ttk.Button(left, text="New", command=self.new_session).pack(pady=5)

        # 右：チャット表示
        right = ttk.Frame(frm)
        right.pack(side="right", fill="both", expand=True)
        self.txt_chat = tk.Text(right, state="disabled", wrap="word")
        self.txt_chat.pack(fill="both", expand=True, padx=5, pady=5)

        # 下：入力＋ボタン群
        bottom = ttk.Frame(self.root)
        bottom.pack(fill="x")
        self.entry = tk.Entry(bottom)
        self.entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        ttk.Button(bottom, text="Attach Image", command=self.attach_image).pack(side="left", padx=5)
        ttk.Button(bottom, text="Context", command=self.open_context).pack(side="left")
        ttk.Button(bottom, text="Settings", command=self.open_settings).pack(side="left")
        ttk.Button(bottom, text="Send", command=self.send_message).pack(side="left", padx=5)

    def _load_session_list(self): # (変更なし)
        self.session_list.delete(0, tk.END)
        for fname in sorted(os.listdir(SESSIONS_DIR)):
            if fname.endswith(".json"):
                self.session_list.insert(tk.END, fname[:-5])

    def new_session(self): # (変更なし)
        idx = len([f for f in os.listdir(SESSIONS_DIR) if f.endswith(".json")]) + 1
        name = f"chat_{idx}"
        self.current_session = name
        self.messages = [
            {"role": "system", "content": self.config["system_message"]}
        ]
        self._save_current_session()
        self._load_session_list()
        self.session_list.selection_clear(0, tk.END)
        # 新しいセッションを選択状態にする (リストの最後に追加されるため tk.END を使う)
        try:
            last_index = self.session_list.size() - 1
            if last_index >= 0:
                self.session_list.selection_set(last_index)
                self.session_list.activate(last_index)
                self.session_list.see(last_index)
        except tk.TclError:
            pass # リストが空の場合など
        self.refresh_chat()

    def _save_current_session(self): # (変更なし)
        if not self.current_session:
            return
        path = os.path.join(SESSIONS_DIR, self.current_session + ".json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.messages, f, indent=2, ensure_ascii=False)

    def on_select_session(self, evt): # (変更なし)
        sel = self.session_list.curselection()
        if not sel:
            return
        name = self.session_list.get(sel[0])
        path = os.path.join(SESSIONS_DIR, name + ".json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.messages = json.load(f)
            self.current_session = name
            self.refresh_chat()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load session {name}: {e}")

    # ↓↓↓ refresh_chat: 画像メッセージ形式の変更に対応 ↓↓↓
    def refresh_chat(self):
        self.txt_chat.config(state="normal")
        self.txt_chat.delete("1.0", tk.END)
        self._img_refs = [] # 既存画像参照をクリア
        for msg in self.messages:
            role = msg.get("role")
            content = msg.get("content")
            if role == "system":
                continue

            self.txt_chat.insert(tk.END, f"{role}: ")
            # content がリスト形式か (画像を含むか) 文字列かをチェック
            if isinstance(content, list):
                for item in content:
                    if item.get("type") == "text":
                        self.txt_chat.insert(tk.END, f"{item.get('text', '')}\n")
                    elif item.get("type") == "image_url":
                        img_data = item.get("image_url", {}).get("url", "")
                        if img_data.startswith("data:image"):
                            # Base64 データ部分を取得 (ヘッダを除く)
                            try:
                                header, b64_data = img_data.split(",", 1)
                                # 画像を表示
                                b = base64.b64decode(b64_data)
                                img = Image.open(io.BytesIO(b))
                                img.thumbnail((200, 200)) # 縮小表示
                                photo = ImageTk.PhotoImage(img)
                                self.txt_chat.image_create(tk.END, image=photo)
                                self.txt_chat.insert(tk.END, "\n")
                                self._img_refs.append(photo) # 参照を保持
                            except Exception as e:
                                print(f"Error decoding/displaying image: {e}")
                                self.txt_chat.insert(tk.END, "[Error displaying image]\n")
                        else:
                             self.txt_chat.insert(tk.END, "[Image URL (not displayed)]\n") # Base64でない場合
            elif isinstance(content, str):
                 self.txt_chat.insert(tk.END, f"{content}\n")
            else:
                 self.txt_chat.insert(tk.END, "[Invalid content format]\n")

            self.txt_chat.insert(tk.END, "\n") # メッセージ間のスペース

        self.txt_chat.see(tk.END) # スクロール
        self.txt_chat.config(state="disabled")
    # ↑↑↑ refresh_chat: 画像メッセージ形式の変更に対応 ↑↑↑

    # ↓↓↓ send_message: 画像メッセージ形式の変更に対応 ↓↓↓
    def send_message(self):
        text = self.entry.get().strip()
        image_path = getattr(self, "_pending_image", None)

        if not text and not image_path:
            return
        if not self.client:
             messagebox.showerror("Error", "OpenAI client is not initialized.")
             return
        if not self.current_session:
            messagebox.showinfo("Info", "Please select or create a new session.")
            return

        user_content = []
        # テキストを追加
        if text:
            user_content.append({"type": "text", "text": text})

        # 画像を追加
        if image_path:
            try:
                # 画像をBase64エンコード
                with open(image_path, "rb") as image_file:
                    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                # 画像形式を判定 (簡易的に拡張子から)
                ext = os.path.splitext(image_path)[1].lower()
                mime_type = f"image/{ext[1:]}" if ext in ['.png', '.jpeg', '.jpg', '.gif', '.webp'] else "image/jpeg" # 不明ならjpeg

                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}
                })
                # 保留画像をクリア
                del self._pending_image
                # エントリーの内容もクリア (画像添付表示を消す)
                self.entry.delete(0, tk.END)
            except Exception as e:
                 messagebox.showerror("Image Error", f"Failed to process image: {e}")
                 # 画像処理に失敗したらメッセージ送信を中断することもある
                 return

        # メッセージリストに追加
        self.messages.append({"role": "user", "content": user_content})

        self.entry.delete(0, tk.END) # テキスト入力欄をクリア
        self.refresh_chat()
        self._save_current_session()

        # 非同期 API 呼び出し
        threading.Thread(target=self._call_api, daemon=True).start()
    # ↑↑↑ send_message: 画像メッセージ形式の変更に対応 ↑↑↑

    # ↓↓↓ _call_api: API呼び出しの変更 ↓↓↓
    def _call_api(self):
        if not self.client:
            print("API call skipped: client not initialized.")
            return

        # APIに渡すメッセージリストを作成 (表示用とは別に)
        # 画像データが大きすぎる場合、ここでリサイズや圧縮が必要になる可能性あり
        api_messages = self._prepare_api_messages()

        try:
            # init_openai は不要
            # API 呼び出し
            response = self.client.chat.completions.create(
                model=self.config["deployment"], # deployment_id ではなく model
                messages=api_messages,
                # max_tokens=800, # 必要なら追加
                # temperature=0.7 # 必要なら追加
            )
            # レスポンス取得
            choice = response.choices[0].message
            assistant_content = choice.content # content を直接取得
            # メッセージリストに追加 (role は response から取得)
            self.messages.append({"role": choice.role or "assistant", "content": assistant_content}) # role が None の場合もあるのでフォールバック
            self._save_current_session()
            # UI 更新はメインスレッドで行う
            self.root.after(0, self.refresh_chat)
        except APIError as e:
            # APIエラーの詳細を表示
            err_msg = f"API Error: {e.status_code}\n{e.message}"
            # Azure特有のエラー情報があれば表示
            if e.body and "message" in e.body:
                 err_msg += f"\nDetails: {e.body['message']}"
            self.root.after(0, lambda: messagebox.showerror("API Error", err_msg))
        except Exception as e:
            # その他のエラー
            self.root.after(0, lambda: messagebox.showerror("Error", f"An unexpected error occurred: {e}"))
    # ↑↑↑ _call_api: API呼び出しの変更 ↑↑↑

    # ↓↓↓ APIに渡すメッセージ形式を整えるヘルパーメソッド ↓↓↓
    def _prepare_api_messages(self):
        # 現在の self.messages をAPIが受け付ける形式に変換
        # 特に、古い形式の画像データ ('image'キー) が残っている場合に備える (基本的には不要はず)
        api_msgs = []
        for msg in self.messages:
            role = msg.get("role")
            content = msg.get("content")
            image_b64 = msg.get("image") # 古い形式のチェック

            if role and content:
                # 新しい形式 (contentがリスト) またはテキストのみ
                if isinstance(content, list) or isinstance(content, str):
                    api_msgs.append({"role": role, "content": content})
                # 古い画像形式の互換性 (もしセッションファイルに残っていた場合)
                elif image_b64 and isinstance(content, str):
                     # 画像形式を推測 (例: jpeg)
                     mime_type = "image/jpeg"
                     new_content = [
                         {"type": "text", "text": content},
                         {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_b64}"}}
                     ]
                     api_msgs.append({"role": role, "content": new_content})
                else:
                     print(f"Skipping message with unexpected format: {msg}")
            elif role and image_b64 and not content: # 画像のみ (古い形式)
                 mime_type = "image/jpeg"
                 new_content = [
                     {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_b64}"}}
                 ]
                 api_msgs.append({"role": role, "content": new_content})

        return api_msgs
    # ↑↑↑ APIに渡すメッセージ形式を整えるヘルパーメソッド ↑↑↑


    def attach_image(self): # (変更なし)
        path = filedialog.askopenfilename(
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.webp")] # webp 追加
        )
        if not path:
            return
        self._pending_image = path
        # 入力欄に画像ファイル名を表示（オプション）
        self.entry.delete(0, tk.END)
        self.entry.insert(0, f"[Image Attached: {os.path.basename(path)}]")

    def open_settings(self): # (変更なし)
        # SettingsWindow 内でクライアント再生成処理を行う
        SettingsWindow(self)

    def open_context(self): # (変更なし)
        if not self.current_session:
            messagebox.showinfo("Info", "Please select or create a new session first.")
            return
        ContextWindow(self)

#
# 5) 設定ウインドウ
#
class SettingsWindow:
    def __init__(self, app: ChatApp):
        self.app = app
        cfg = app.config
        self.win = tk.Toplevel(app.root) # 親ウィンドウを指定
        self.win.title("Settings")
        #モーダルにする (設定画面表示中はメイン画面を操作不可に)
        self.win.grab_set()
        self.win.focus_set()
        self.win.transient(self.app.root) # メインウィンドウの上に表示

        frm = ttk.Frame(self.win, padding=10)
        frm.pack(fill="both", expand=True)

        self.vars = {}
        # api_type は削除
        for i, (key, label) in enumerate([
            ("api_base",    "API Base URL (Endpoint)"), # ラベル変更
            ("api_version", "API Version"),
            ("api_key",     "API Key"),
            ("deployment",  "Deployment Name (Model)"), # ラベル変更
        ]):
            ttk.Label(frm, text=label).grid(row=i, column=0, sticky="w", padx=5, pady=4) # sticky e -> w
            v = tk.StringVar(value=cfg.get(key, ""))
            self.vars[key] = v
            # API Key は伏字にする
            show_char = "*" if key == "api_key" else ""
            ttk.Entry(frm, textvariable=v, width=50, show=show_char).grid(row=i, column=1, padx=5, pady=4)

        row_idx = len(self.vars) # 次の行インデックス

        ttk.Label(frm, text="System Message").grid(row=row_idx, column=0, sticky="nw", padx=5, pady=4) # sticky ne -> nw
        self.sys_txt = tk.Text(frm, height=4, width=50)
        self.sys_txt.grid(row=row_idx, column=1, padx=5, pady=4, sticky="ew") # sticky 追加
        self.sys_txt.insert("1.0", cfg.get("system_message", ""))

        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=row_idx + 1, column=0, columnspan=2, pady=10, sticky="e")
        ttk.Button(btn_frame, text="Save", command=self.on_save).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.win.destroy).pack(side="right")

        # Enterキーで保存、Escapeキーでキャンセル
        self.win.bind('<Return>', lambda event: self.on_save())
        self.win.bind('<Escape>', lambda event: self.win.destroy())


    def on_save(self):
        # 設定値を更新
        for k, v in self.vars.items():
            self.app.config[k] = v.get().strip()
        self.app.config["system_message"] = self.sys_txt.get("1.0", "end-1c").strip() # end-1c で末尾改行除去

        # 設定を保存
        save_config(self.app.config)

        # ↓↓↓ OpenAI クライアントを再生成 ↓↓↓
        new_client = self.app._create_openai_client(self.app.config)
        if new_client:
            self.app.client = new_client
            messagebox.showinfo("Settings", "Settings saved and OpenAI client updated.", parent=self.win)
             # 現在のセッションの system メッセージも更新
            if self.app.messages and self.app.messages[0]["role"] == "system":
                 self.app.messages[0]["content"] = self.app.config["system_message"]
                 self.app._save_current_session()
                 # refresh_chat はメインアプリ側で行うのでここでは呼ばない
                 # 必要であれば、設定保存後にメイン画面でリフレッシュするフラグを立てるなど
            self.win.destroy()
        else:
             # クライアント初期化失敗のメッセージは _create_openai_client 内で表示されるはず
             messagebox.showerror("Error", "Failed to update OpenAI client with new settings.", parent=self.win)
        # ↑↑↑ OpenAI クライアントを再生成 ↑↑↑

#
# 6) コンテキスト編集ウインドウ (変更なし、ただし表示内容は新フォーマットになる可能性あり)
#
class ContextWindow:
    def __init__(self, app: ChatApp):
        self.app = app
        self.win = tk.Toplevel(app.root)
        self.win.title("Context Editor")
        self.win.geometry("600x400") # サイズ調整
        #モーダルにする
        self.win.grab_set()
        self.win.focus_set()
        self.win.transient(self.app.root)

        # スクロールバー付きテキストエリア
        text_frame = ttk.Frame(self.win)
        text_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.txt = tk.Text(text_frame, wrap="word", undo=True) # undo有効化
        ys = ttk.Scrollbar(text_frame, orient='vertical', command=self.txt.yview)
        xs = ttk.Scrollbar(text_frame, orient='horizontal', command=self.txt.xview)
        self.txt['yscrollcommand'] = ys.set
        self.txt['xscrollcommand'] = xs.set
        xs.pack(side='bottom', fill='x')
        ys.pack(side='right', fill='y')
        self.txt.pack(side='left', fill='both', expand=True)

        # JSON を整形して表示
        try:
            # messages が空でないことを確認
            if self.app.messages:
                json_str = json.dumps(self.app.messages, indent=2, ensure_ascii=False)
                self.txt.insert("1.0", json_str)
            else:
                self.txt.insert("1.0", "[]") # 空のリストを表示
        except Exception as e:
             self.txt.insert("1.0", f"Error displaying context: {e}")


        btn_frame = ttk.Frame(self.win)
        btn_frame.pack(fill="x", padx=5, pady=5)
        ttk.Button(btn_frame, text="Apply", command=self.apply).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Close", command=self.win.destroy).pack(side="right")

        # Escapeキーで閉じる
        self.win.bind('<Escape>', lambda event: self.win.destroy())

    def apply(self):
        try:
            # テキストエリアからJSON文字列を取得
            json_str = self.txt.get("1.0", "end-1c").strip()
            if not json_str:
                raise ValueError("Context cannot be empty.")

            data = json.loads(json_str) # JSONとしてパース

            # 簡単なバリデーション
            if not isinstance(data, list):
                 raise ValueError("Context must be a JSON list.")
            if not data: # 空リストは許可する場合もあるが、ここではシステムメッセージ必須とする
                 raise ValueError("Context cannot be empty list.")
            if not isinstance(data[0], dict) or data[0].get("role") != "system":
                # 既存の system メッセージを使うか、エラーにするか選択
                # ここではエラーとする
                raise ValueError("The first message must be a system message ({'role': 'system', ...}).")

            # 問題なければ適用
            self.app.messages = data
            self.app._save_current_session()
            self.app.refresh_chat() # メイン画面の表示を更新
            self.win.destroy() # 画面を閉じる
        except json.JSONDecodeError as e:
             messagebox.showerror("JSON Error", f"Invalid JSON format: {e}", parent=self.win)
        except ValueError as e:
             messagebox.showerror("Validation Error", str(e), parent=self.win)
        except Exception as e:
             messagebox.showerror("Error", f"Failed to apply context: {e}", parent=self.win)


#
# 7) 起動 (変更なし)
#
if __name__ == "__main__":
    root = tk.Tk()
    app = ChatApp(root)
    root.mainloop()