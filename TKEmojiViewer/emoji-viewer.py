import tkinter as tk
from tkinter import ttk, scrolledtext, StringVar, messagebox
import unicodedata
import re
import pyperclip
import json
from functools import lru_cache
import platform # OS判定のために追加

class EmojiViewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("絵文字ビューア＆コピーツール")
        self.geometry("800x600")

        # 絵文字のサイズ設定
        self.size_options = {"小": 12, "中": 18, "大": 24}
        self.current_size = StringVar(value="中")

        # 絵文字データの初期化
        self.emoji_data, self.potential_emoji_ranges = self.load_emoji_data()
        self.group_names = ["All"] + list(self.emoji_data.keys())
        # === 変更点: デフォルトグループを 'Smileys & Emotion' に ===
        default_group = "Smileys & Emotion"
        if default_group not in self.group_names: # 念のため存在確認
             default_group = "All" # 存在しなければAllに戻す
        self.current_group = StringVar(value=default_group)
        # ========================================================

        # OSに応じた絵文字フォント選択
        self.emoji_font_family = self.get_default_emoji_font()

        # UIの作成
        self.create_ui()

        # 初期表示
        self.update_display()

    def get_default_emoji_font(self):
        """OSに応じてデフォルトのカラー絵文字フォントを返す"""
        os_name = platform.system()
        if os_name == "Windows":
            print("Windows detected") # デバッグ用
            # Windows 10以降では Segoe UI Emoji がカラー絵文字をサポート
            return "Segoe UI Emoji"
        elif os_name == "Darwin": # macOS
            print("macOS detected") # デバッグ用
            # macOSでは Apple Color Emoji がデフォルト
            return "Apple Color Emoji"
        else: # Linuxなど
            print("Linux or other OS detected") # デバッグ用
            # Noto Color Emoji が一般的だが、インストールされているとは限らない
            # フォントが存在しない場合、システムが代替を探すことを期待
            return "Noto Color Emoji" # 代替として "sans-serif" も考慮

    def load_emoji_data(self):
        """絵文字データと予約/未割り当ての可能性のある範囲を準備する (変更なし)"""
        # --- (前回のコードと同じ) ---
        emoji_groups = {
            "Smileys & Emotion": [(0x1F600, 0x1F64F), (0x1F910, 0x1F92F), (0x1F970, 0x1F97A)],
            "People & Body": [(0x1F440, 0x1F487), (0x1F4AA, 0x1F4AA), (0x1F9B0, 0x1F9DB)],
            "Animals & Nature": [(0x1F400, 0x1F43F), (0x1F980, 0x1F9A2), (0x1F330, 0x1F335)],
            "Food & Drink": [(0x1F336, 0x1F37F), (0x1F950, 0x1F96B)],
            "Travel & Places": [(0x1F680, 0x1F6FF), (0x1F30D, 0x1F320)],
            "Activities": [(0x1F380, 0x1F3C4), (0x1F6B2, 0x1F6B6), (0x26BD, 0x26BE), (0x1F93A, 0x1F94B)],
            "Objects": [(0x1F488, 0x1F4A9), (0x1F4DC, 0x1F53D), (0x1F5A5, 0x1F5FA)],
            "Symbols": [(0x2600, 0x27BF), (0x1F100, 0x1F1FF), (0x1F300, 0x1F30C), (0x1F5FB, 0x1F5FF)],
            "Flags": [(0x1F1E6, 0x1F1FF)],
            "Component": [(0x1F3FB, 0x1F3FF)],
            "Supplemental Symbols": [(0x1F900, 0x1F9FF)],
            "Extended Pictographic": [(0x1FA70, 0x1FAFF)],
        }
        potential_ranges = [
            (0x1F900, 0x1F9FF),
            (0x1FA70, 0x1FAFF),
        ]
        return emoji_groups, potential_ranges
        # --- (ここまで変更なし) ---

    @lru_cache(maxsize=None)
    def get_emoji_ranges_for_group(self, group_name):
        """指定されたグループのUnicode範囲リストを取得する (変更なし)"""
        # --- (前回のコードと同じ) ---
        if group_name == "All":
            all_ranges = []
            for ranges in self.emoji_data.values():
                all_ranges.extend(ranges)
            all_ranges.extend(self.potential_emoji_ranges)
            unique_ranges_dict = {}
            for start, end in all_ranges:
                if start not in unique_ranges_dict or end > unique_ranges_dict[start]:
                     unique_ranges_dict[start] = end
            unique_ranges = sorted(unique_ranges_dict.items())
            return unique_ranges
        else:
            return self.emoji_data.get(group_name, [])
        # --- (ここまで変更なし) ---

    @lru_cache(maxsize=2048)
    def is_emoji(self, char):
        """文字が絵文字として一般的に認識されるか判定（簡易版・変更なし）"""
        # --- (前回のコードと同じ) ---
        try:
            code = ord(char)
            name = unicodedata.name(char, '').lower()
            if unicodedata.category(char) == 'So':
                if 'arrow' in name or 'mathematical' in name:
                     if 'dingbat' not in name: # Dingbatsは絵文字扱いとする
                         return False
                return True
            if 'emoji' in name: return True
            if 0x1F1E6 <= code <= 0x1F1FF: return True # Flags
            if 0x1F3FB <= code <= 0x1F3FF: return True # Skin Tone Modifiers
        except (ValueError, TypeError):
            return False
        return False
        # --- (ここまで変更なし) ---

    def get_emoji_group(self, char_or_code):
        """絵文字またはコードポイントが属する可能性のあるグループを取得 (変更なし)"""
        # --- (前回のコードと同じ) ---
        if isinstance(char_or_code, str):
             try: code = ord(char_or_code)
             except TypeError: return "Invalid"
        else: code = char_or_code
        for group_name, ranges in self.emoji_data.items():
            for start, end in ranges:
                if start <= code <= end:
                    if group_name != "Component" and 0x1F3FB <= code <= 0x1F3FF: continue
                    if group_name == "Component" and not (0x1F3FB <= code <= 0x1F3FF): continue
                    return group_name
        return "Other"
        # --- (ここまで変更なし) ---

    def is_in_potential_range(self, code_point):
        """指定コードポイントがプレースホルダ表示対象の範囲内か (変更なし)"""
        # --- (前回のコードと同じ) ---
        for start, end in self.potential_emoji_ranges:
            if start <= code_point <= end: return True
        return False
        # --- (ここまで変更なし) ---

    def create_ui(self):
        """UIを作成する (変更なし)"""
        # --- (前回のコードと同じ) ---
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(top_frame, text="グループ:").pack(side=tk.LEFT, padx=(0, 5))
        group_combo = ttk.Combobox(top_frame,textvariable=self.current_group,values=self.group_names,state="readonly",width=20)
        group_combo.pack(side=tk.LEFT, padx=(0, 10))
        group_combo.bind("<<ComboboxSelected>>", self.on_group_selected)
        ttk.Label(top_frame, text="検索:").pack(side=tk.LEFT, padx=(10, 5))
        self.search_var = StringVar()
        self.search_var.trace_add("write", self.on_search_changed)
        search_entry = ttk.Entry(top_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        ttk.Label(top_frame, text="サイズ:").pack(side=tk.LEFT, padx=(10, 5))
        for size_name, size_value in self.size_options.items():
            ttk.Radiobutton(top_frame,text=size_name,value=size_name,variable=self.current_size,command=self.update_display).pack(side=tk.LEFT, padx=5)
        self.emoji_frame = ttk.Frame(self)
        self.emoji_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.canvas = tk.Canvas(self.emoji_frame, borderwidth=0, background="#ffffff")
        scrollbar = ttk.Scrollbar(self.emoji_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.emoji_container = ttk.Frame(self.canvas, style="Emoji.TFrame")
        self.style = ttk.Style(self)
        self.style.configure("Emoji.TFrame", background="#ffffff")
        self.canvas_window = self.canvas.create_window((0, 0), window=self.emoji_container, anchor="nw")
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        self.emoji_container.bind("<Configure>", self.on_frame_configure)
        self.status_var = StringVar()
        status_bar = ttk.Label(self, textvariable=self.status_var, anchor=tk.W, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, padx=10, pady=(0, 5))
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind_all("<Button-4>", self.on_mousewheel_linux)
        self.canvas.bind_all("<Button-5>", self.on_mousewheel_linux)
        # --- (UI作成ここまで変更なし) ---

    def on_canvas_configure(self, event):
        """キャンバスのサイズが変更されたときの処理"""
        # === 変更点: コンテナ幅の強制設定を削除 ===
        # self.canvas.itemconfig(self.canvas_window, width=event.width) # この行を削除またはコメントアウト
        # =========================================
        # コンテナ自身のサイズに追従させるため上記は不要
        # ただし、リサイズ時に再描画して列数を調整する必要はある
        self.update_display()

    def on_frame_configure(self, event):
        """内部フレームのサイズが変更されたときの処理"""
        # フレーム（コンテナ）のサイズ変更に合わせてスクロール領域を更新
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_mousewheel(self, event):
        """マウスホイールでスクロールする (Windows/macOS)"""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_mousewheel_linux(self, event):
        """マウスホイールでスクロールする (Linux)"""
        if event.num == 4: self.canvas.yview_scroll(-1, "units")
        elif event.num == 5: self.canvas.yview_scroll(1, "units")

    def on_search_changed(self, *args):
        """検索テキストが変更されたときの処理"""
        self.update_display()

    def on_group_selected(self, event=None):
        """グループが選択されたときの処理"""
        self.update_display()

    def update_display(self):
        """表示を更新する"""
        selected_group = self.current_group.get()
        search_text = self.search_var.get().lower().strip()
        font_size = self.size_options[self.current_size.get()]
        # === 変更点: OS依存のフォントを使用 ===
        font_family = self.emoji_font_family
        # print(f"Using font: {font_family}") # デバッグ用
        # ===================================

        # クリア
        for widget in self.emoji_container.winfo_children():
            widget.destroy()

        # === 変更点: リサイズ時のちらつき防止のため、描画前に幅を取得 ===
        # update_idletasks() を呼んで最新のサイズ情報を取得
        self.canvas.update_idletasks()
        canvas_width = self.canvas.winfo_width()
        # ===========================================================
        # ボタンの推定幅（文字サイズとパディングに基づく）
        # 少し余裕を持たせる（環境による文字幅の違いを考慮）
        button_width_estimate = font_size * 2 + 15 # パディングを少し詰める
        max_cols = max(1, canvas_width // button_width_estimate)

        row, col = 0, 0
        displayed_count = 0
        processed_codepoints = set()

        target_ranges = self.get_emoji_ranges_for_group(selected_group)

        for range_start, range_end in target_ranges:
            if range_start > range_end: continue

            for code_point in range(range_start, range_end + 1):
                if code_point in processed_codepoints: continue

                char = None
                name = ""
                is_renderable = False
                actual_group = "Unknown"

                try:
                    char = chr(code_point)
                    if self.is_emoji(char):
                        is_renderable = True
                        name = unicodedata.name(char, '').lower()
                        actual_group = self.get_emoji_group(char)
                    # else: is_renderable は False のまま
                except (ValueError, TypeError):
                    # is_renderable は False のまま
                    pass

                # --- フィルタリング ---
                display_this = False
                is_placeholder = False

                if is_renderable:
                    if selected_group == "All" or actual_group == selected_group:
                        if not search_text or (search_text in name or search_text in f"{code_point:x}" or search_text == char):
                            display_this = True
                else:
                    if self.is_in_potential_range(code_point):
                        potential_group = self.get_emoji_group(code_point)
                        if selected_group == "All" or potential_group == selected_group:
                            hex_code = f"{code_point:x}"
                            if not search_text or search_text in hex_code:
                                display_this = True
                                is_placeholder = True

                # --- ボタン作成 または スキップ ---
                if display_this:
                    button_font = (font_family, font_size) # フォント指定
                    if is_placeholder:
                        # --- プレースホルダボタン作成 ---
                        placeholder_button = tk.Button(
                            self.emoji_container, text="?", font=button_font, # フォント適用
                            state=tk.DISABLED, width=2, height=1, relief=tk.FLAT,
                            bg="#e0e0e0", fg="#808080"
                        )
                        placeholder_button.grid(row=row, column=col, padx=2, pady=2, sticky="nsew") # パディング縮小
                        tooltip_text = f"U+{code_point:04X}: Reserved/Unassigned"
                        self.create_tooltip(placeholder_button, tooltip_text)
                    else:
                        # --- 通常の絵文字ボタン作成 ---
                        # === 変更点: ボタンの見た目を調整 ===
                        emoji_button = tk.Button(
                            self.emoji_container, text=char, font=button_font, # フォント適用
                            command=lambda c=char, cp=code_point: self.copy_emoji(c, cp),
                            width=2, height=1,
                            relief=tk.FLAT, # 枠線を消す
                            borderwidth=0,  # 枠線幅を0に
                            bg="#ffffff",   # 背景を白に
                            fg="#000000",   # 文字色（通常は絵文字色になる）
                            activebackground="#f0f0f0" # クリック時の背景色
                        )
                        # ==================================
                        emoji_button.grid(row=row, column=col, padx=2, pady=2, sticky="nsew") # パディング縮小
                        tooltip_text = f"U+{code_point:04X}: {unicodedata.name(char, 'Unknown')}"
                        self.create_tooltip(emoji_button, tooltip_text)

                    processed_codepoints.add(code_point)
                    displayed_count += 1

                    # 次の描画位置へ
                    col += 1
                    if col >= max_cols:
                        col = 0
                        row += 1

        # --- 表示完了後 ---
        self.status_var.set(f"グループ: {selected_group} | 表示: {displayed_count}個 | サイズ: {self.current_size.get()}")
        # === 変更点: スクロール領域更新のタイミング調整 ===
        # grid描画が完了してから update_idletasks を呼び、bbox を計算する
        self.emoji_container.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        # ================================================
        # スクロール位置リセットはしない（リサイズ時に位置が飛ぶのを防ぐ）
        # self.canvas.yview_moveto(0)


    def copy_emoji(self, char, code_point):
        """絵文字をクリップボードにコピー (変更なし)"""
        # --- (前回のコードと同じ) ---
        try:
            pyperclip.copy(char)
            group = self.get_emoji_group(char)
            name = unicodedata.name(char, 'Unknown')
            self.status_var.set(f"コピー: {char} (U+{code_point:04X} {name}) | グループ: {group}")
        except pyperclip.PyperclipException as e:
            messagebox.showerror("コピーエラー", f"クリップボードへのコピーに失敗しました:\n{e}")
        except Exception as e:
             messagebox.showerror("エラー", f"予期せぬエラーが発生しました:\n{e}")
        # --- (ここまで変更なし) ---

    def create_tooltip(self, widget, text):
        """ツールチップを作成 (変更なし)"""
        # --- (前回のコードと同じ) ---
        tooltip = None
        tooltip_label = None
        def enter(event):
            nonlocal tooltip, tooltip_label
            if tooltip: return
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + widget.winfo_height() + 5
            tooltip = tk.Toplevel(widget)
            tooltip.wm_overrideredirect(True); tooltip.wm_geometry(f"+{x}+{y}"); tooltip.attributes("-topmost", True)
            tooltip_label = ttk.Label(tooltip, text=text, justify=tk.LEFT, background="#ffffe0", relief=tk.SOLID, borderwidth=1, padding=(4, 2))
            tooltip_label.pack(ipadx=1)
        def leave(event):
            nonlocal tooltip
            if tooltip: tooltip.destroy(); tooltip = None
        widget.bind("<Enter>", enter, add='+'); widget.bind("<Leave>", leave, add='+')
        # --- (ここまで変更なし) ---


if __name__ == "__main__":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except ImportError:
        pass

    app = EmojiViewer()
    app.mainloop()