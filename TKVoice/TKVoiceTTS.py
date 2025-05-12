import os
import sys
import json
import configparser
import datetime
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import tempfile
from pathlib import Path
import uuid
import pygame
from openai import AzureOpenAI
import time
from collections import OrderedDict

class AzureTTSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Azure OpenAI 音声合成アプリ")
        self.root.geometry("1000x800")
        
        pygame.mixer.init()
        
        self.config_file = os.path.join(os.path.expanduser("~"), "azure_tts_config.ini")
        self.default_chunk_size = 1000
        
        # TTS音声リスト
        self.voices = ["alloy", "echo", "fable", "nova", "onyx", "shimmer"]
        
        # 音声スタイル（instructions用）
        self.voice_styles = {
            "シニア男性ナレーション": "You are a senior male narrator with a deep, authoritative voice. Speak clearly and professionally.",
            "シニア女性ナレーション": "You are a senior female narrator with a warm, experienced voice. Speak clearly and professionally.",
            "若者男性カジュアル": "You are a young man speaking casually with friends. Your tone is energetic and relaxed.",
            "若者女性カジュアル": "You are a young woman speaking casually with friends. Your tone is energetic and friendly.",
            "子供男の子": "You are a cheerful young boy with a high-pitched voice full of excitement and wonder.",
            "子供女の子": "You are a cheerful young girl with a sweet voice full of excitement and curiosity.",
            "オーディオブック男性": "You are a professional male audiobook narrator. Read with clear pacing and subtle character distinctions.",
            "オーディオブック女性": "You are a professional female audiobook narrator. Read with clear pacing and subtle character distinctions.",
            "ニュースキャスター": "You are a professional news broadcaster. Speak clearly and objectively with a formal tone.",
            "感情豊かな語り手": "Speak with a wide range of emotional expression, varying your tone to match the content's mood."
        }

        # 単語置換辞書
        self.word_replacements = {
            "PMBOK": "ピンボック",
        }

        self.audio_formats = ["mp3", "opus", "aac", "flac"]
        self.generated_audio_files = []
        # self.word_replacements = {}
        
        self.config = configparser.ConfigParser()
        self.config.optionxform = str  # キーの大文字小文字を保持
        self.load_config()
        
        self.create_ui()
        
    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                self.config.read(self.config_file, encoding='utf-8')
                if not self.config.has_section('Azure'):
                    self.config.add_section('Azure')
                if not self.config.has_section('Settings'):
                    self.config.add_section('Settings')
                if not self.config.has_section('VoiceStyles'):
                    self.config.add_section('VoiceStyles')
                    for style_name, prompt in self.voice_styles.items():
                        self.config.set('VoiceStyles', style_name, prompt)
                    self.save_config()

                if not self.config.has_section('WordReplacements'):
                    self.config.add_section('WordReplacements')
                    for word, replacement in self.word_replacements.items():
                        self.config.set('WordReplacements', word, replacement)
                    self.save_config()
                                            
                # 既存の値を優先して復元
                if self.config.has_section('VoiceStyles'):
                    self.voice_styles = OrderedDict(self.config.items('VoiceStyles'))
                if self.config.has_section('WordReplacements'):
                    self.word_replacements = OrderedDict(self.config.items('WordReplacements'))
            except Exception as e:
                messagebox.showerror("設定読み込みエラー", f"設定ファイルの読み込み中にエラーが発生しました: {str(e)}")
                self.initialize_default_config()
        else:
            self.initialize_default_config()

    def initialize_default_config(self):
        if not self.config.has_section('Azure'):
            self.config.add_section('Azure')
            self.config.set('Azure', 'endpoint', '')
            self.config.set('Azure', 'api_key', '')
            self.config.set('Azure', 'api_version', '2025-03-01-preview')
            self.config.set('Azure', 'deployment_name', 'gpt-4o-mini-tts')
        if not self.config.has_section('Settings'):
            self.config.add_section('Settings')
            self.config.set('Settings', 'output_dir', os.path.join(os.path.expanduser("~"), "azure_tts_output"))
            self.config.set('Settings', 'chunk_size', str(self.default_chunk_size))
            self.config.set('Settings', 'audio_format', 'mp3')
            self.config.set('Settings', 'speed', '1.0')
            self.config.set('Settings', 'voice', 'alloy')
        if not self.config.has_section('VoiceStyles') or not dict(self.config.items('VoiceStyles')):
            self.config.add_section('VoiceStyles')
            for style_name, prompt in self.voice_styles.items():
                self.config.set('VoiceStyles', style_name, prompt)
        if not self.config.has_section('WordReplacements') or not dict(self.config.items('WordReplacements')):
            self.config.add_section('WordReplacements')
            for word, replacement in self.word_replacements.items():
                self.config.set('WordReplacements', word, replacement)
            if not self.word_replacements:
                self.config.set('WordReplacements', 'PMBOK', 'ピンボック')
        self.save_config()
        if self.config.has_section('VoiceStyles'):
            self.voice_styles = OrderedDict(self.config.items('VoiceStyles'))
        if self.config.has_section('WordReplacements'):
            self.word_replacements = OrderedDict(self.config.items('WordReplacements'))
            
    def save_config(self):
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            # VoiceStyles, WordReplacementsの順序を維持して保存
            if self.config.has_section('VoiceStyles'):
                self.config.remove_section('VoiceStyles')
                self.config.add_section('VoiceStyles')
                for k, v in self.voice_styles.items():
                    self.config.set('VoiceStyles', k, v)
            if self.config.has_section('WordReplacements'):
                self.config.remove_section('WordReplacements')
                self.config.add_section('WordReplacements')
                for k, v in self.word_replacements.items():
                    self.config.set('WordReplacements', k, v)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
        except Exception as e:
            messagebox.showerror("設定保存エラー", f"設定ファイルの保存中にエラーが発生しました: {str(e)}")
            
    def update_azure_settings(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Azure設定")
        dialog.geometry("500x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(dialog, text="エンドポイント:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        endpoint_var = tk.StringVar(value=self.config.get('Azure', 'endpoint', fallback=''))
        endpoint_entry = tk.Entry(dialog, textvariable=endpoint_var, width=50)
        endpoint_entry.grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(dialog, text="APIキー:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        api_key_var = tk.StringVar(value=self.config.get('Azure', 'api_key', fallback=''))
        api_key_entry = tk.Entry(dialog, textvariable=api_key_var, width=50, show="*")
        api_key_entry.grid(row=1, column=1, padx=5, pady=5)
        
        tk.Label(dialog, text="APIバージョン:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        api_version_var = tk.StringVar(value=self.config.get('Azure', 'api_version', fallback='2025-03-01-preview'))
        api_version_entry = tk.Entry(dialog, textvariable=api_version_var, width=50)
        api_version_entry.grid(row=2, column=1, padx=5, pady=5)
        
        tk.Label(dialog, text="デプロイ名:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        deployment_name_var = tk.StringVar(value=self.config.get('Azure', 'deployment_name', fallback='gpt-4o-mini-tts'))
        deployment_name_entry = tk.Entry(dialog, textvariable=deployment_name_var, width=50)
        deployment_name_entry.grid(row=3, column=1, padx=5, pady=5)
        
        status_label = tk.Label(dialog, text="")
        status_label.grid(row=5, column=0, columnspan=2, pady=5)
        
        def save_settings():
            self.config.set('Azure', 'endpoint', endpoint_var.get())
            self.config.set('Azure', 'api_key', api_key_var.get())
            self.config.set('Azure', 'api_version', api_version_var.get())
            self.config.set('Azure', 'deployment_name', deployment_name_var.get())
            self.save_config()
            dialog.destroy()
            
        def test_connection():
            status_label.config(text="接続テスト中...", fg="blue")
            dialog.update()
            
            endpoint = endpoint_var.get()
            api_key = api_key_var.get()
            api_version = api_version_var.get()
            deployment_name = deployment_name_var.get()
            
            if not endpoint or not api_key or not api_version or not deployment_name:
                status_label.config(text="すべての設定を入力してください", fg="red")
                return
                
            try:
                client = AzureOpenAI(
                    azure_endpoint=endpoint,
                    api_key=api_key,
                    api_version=api_version
                )
                
                models = client.models.list()
                if models:
                    status_label.config(text="接続成功！", fg="green")
                else:
                    status_label.config(text="接続できましたが、モデルリストの取得に失敗しました", fg="orange")
            except Exception as e:
                error_message = str(e)
                status_label.config(text=f"接続エラー: {error_message[:50]}...", fg="red")
                
                error_dialog = tk.Toplevel(dialog)
                error_dialog.title("エラー詳細")
                error_dialog.geometry("600x400")
                
                error_text = scrolledtext.ScrolledText(error_dialog, wrap=tk.WORD)
                error_text.pack(expand=True, fill="both", padx=10, pady=10)
                error_text.insert(tk.END, str(e))
                error_text.config(state="disabled")
                
                copy_button = tk.Button(error_dialog, text="コピー", 
                                      command=lambda: self.copy_to_clipboard(str(e)))
                copy_button.pack(pady=10)
        
        test_button = tk.Button(dialog, text="接続テスト", command=test_connection)
        test_button.grid(row=4, column=0, pady=10, padx=5, sticky="w")
        
        save_button = tk.Button(dialog, text="保存", command=save_settings)
        save_button.grid(row=4, column=1, pady=10, padx=5, sticky="e")
        
    def copy_to_clipboard(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        messagebox.showinfo("コピー", "クリップボードにコピーしました")
        
    def create_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ファイル", menu=file_menu)
        file_menu.add_command(label="テキストを開く", command=self.load_text_file)
        file_menu.add_command(label="設定", command=self.update_azure_settings)
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.root.quit)
        
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="設定", menu=settings_menu)
        settings_menu.add_command(label="単語置換辞書", command=self.manage_word_replacements)
        settings_menu.add_command(label="音声スタイルプロンプト", command=self.manage_voice_styles)
        settings_menu.add_command(label="出力設定", command=self.update_output_settings)
        
        control_frame = ttk.LabelFrame(main_frame, text="音声設定")
        control_frame.pack(fill=tk.X, pady=5)
        
        # 音声（voice）の選択
        ttk.Label(control_frame, text="音声:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.voice_var = tk.StringVar(value=self.config.get('Settings', 'voice', fallback='alloy'))
        voice_combo = ttk.Combobox(control_frame, textvariable=self.voice_var, width=15)
        voice_combo['values'] = self.voices
        voice_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # 音声スタイルの選択
        ttk.Label(control_frame, text="音声スタイル:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.voice_style_var = tk.StringVar()
        self.voice_style_combo = ttk.Combobox(control_frame, textvariable=self.voice_style_var, width=30)
        self.voice_style_combo['values'] = list(self.voice_styles.keys())
        if self.voice_style_combo['values']:
            self.voice_style_combo.current(0)
        self.voice_style_combo.grid(row=1, column=1, padx=5, pady=5, columnspan=3, sticky="w")
        
        ttk.Label(control_frame, text="指示プロンプト:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.voice_prompt_text = tk.Text(control_frame, height=3, width=60, wrap=tk.WORD)
        self.voice_prompt_text.grid(row=2, column=1, columnspan=3, sticky="ew", padx=5, pady=5)
        
        def update_prompt(*args):
            selected_style = self.voice_style_var.get()
            if selected_style in self.voice_styles:
                self.voice_prompt_text.delete(1.0, tk.END)
                self.voice_prompt_text.insert(tk.END, self.voice_styles[selected_style])
        
        self.voice_style_var.trace_add("write", update_prompt)
        update_prompt()
        
        ttk.Label(control_frame, text="音声フォーマット:").grid(row=0, column=2, sticky="w", padx=5, pady=5)
        self.audio_format_var = tk.StringVar(value=self.config.get('Settings', 'audio_format', fallback='mp3'))
        audio_format_combo = ttk.Combobox(control_frame, textvariable=self.audio_format_var, width=10)
        audio_format_combo['values'] = self.audio_formats
        audio_format_combo.grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(control_frame, text="速度:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.speed_var = tk.StringVar(value=self.config.get('Settings', 'speed', fallback='1.0'))
        speed_values = ["0.5", "0.8", "1.0", "1.2", "1.5", "2.0"]
        speed_combo = ttk.Combobox(control_frame, textvariable=self.speed_var, width=10, values=speed_values)
        speed_combo.grid(row=3, column=1, padx=5, pady=5)
        
        ttk.Label(control_frame, text="分割文字数:").grid(row=3, column=2, sticky="w", padx=5, pady=5)
        self.chunk_size_var = tk.StringVar(value=self.config.get('Settings', 'chunk_size', fallback=str(self.default_chunk_size)))
        chunk_size_entry = ttk.Entry(control_frame, textvariable=self.chunk_size_var, width=10)
        chunk_size_entry.grid(row=3, column=3, padx=5, pady=5)

        # 分割ON/OFFチェックボックス追加
        self.split_by_chunk_var = tk.BooleanVar(value=True)
        split_by_chunk_check = ttk.Checkbutton(control_frame, text="分割文字数で分割する", variable=self.split_by_chunk_var)
        split_by_chunk_check.grid(row=3, column=4, padx=5, pady=5, sticky="w")
        
        ttk.Label(control_frame, text="出力先:").grid(row=4, column=0, sticky="w", padx=5, pady=5)
        self.output_dir_var = tk.StringVar(value=self.config.get('Settings', 'output_dir', fallback=os.path.join(os.path.expanduser("~"), "azure_tts_output")))
        output_dir_entry = ttk.Entry(control_frame, textvariable=self.output_dir_var, width=50)
        output_dir_entry.grid(row=4, column=1, columnspan=2, sticky="ew", padx=5, pady=5)
        
        output_dir_button = ttk.Button(control_frame, text="...", command=self.select_output_dir, width=3)
        output_dir_button.grid(row=4, column=3, padx=5, pady=5)

        # ファイル名先頭テキストボックス追加
        ttk.Label(control_frame, text="ファイル名(先頭):").grid(row=5, column=0, sticky="w", padx=5, pady=5)
        self.audio_filename_prefix_var = tk.StringVar(value="audio")
        audio_filename_prefix_entry = ttk.Entry(control_frame, textvariable=self.audio_filename_prefix_var, width=30)
        audio_filename_prefix_entry.grid(row=5, column=1, padx=5, pady=5, sticky="w")
        
        text_frame = ttk.LabelFrame(main_frame, text="テキスト")
        text_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.text_area = tk.Text(text_frame, wrap=tk.WORD, height=15)
        text_scrollbar = ttk.Scrollbar(text_frame, command=self.text_area.yview)
        self.text_area.config(yscrollcommand=text_scrollbar.set)
        
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

        # 文字数ラベル追加
        self.char_count_var = tk.StringVar(value="文字数: 0")
        char_count_label = ttk.Label(text_frame, textvariable=self.char_count_var, anchor=tk.E)
        char_count_label.pack(side=tk.BOTTOM, anchor=tk.E, padx=5, pady=2)
        
        def update_char_count(event=None):
            text = self.text_area.get(1.0, tk.END)
            self.char_count_var.set(f"文字数: {len(text.strip())}")
        
        self.text_area.bind("<KeyRelease>", update_char_count)
        update_char_count()
        
        text_area_frame = ttk.Frame(main_frame)
        text_area_frame.pack( fill=tk.X, pady=5)

        text_open_button = ttk.Button(text_area_frame, text="テキストを開く", command=self.load_text_file)
        preview_button = ttk.Button(text_area_frame, text="分割プレビュー", command=self.preview_splitting)        
        generate_button = ttk.Button(text_area_frame, text="音声生成", command=self.generate_audio)
        text_open_button.pack(side=tk.LEFT,  padx=2)
        preview_button.pack(side=tk.LEFT,  padx=2)
        generate_button.pack(side=tk.RIGHT,  padx=2)
        
        audio_files_frame = ttk.LabelFrame(main_frame, text="生成された音声ファイル")
        audio_files_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.audio_files_listbox = tk.Listbox(audio_files_frame, selectmode=tk.EXTENDED)
        audio_files_scrollbar = ttk.Scrollbar(audio_files_frame, command=self.audio_files_listbox.yview)
        self.audio_files_listbox.config(yscrollcommand=audio_files_scrollbar.set)
        
        self.audio_files_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        audio_files_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        audio_control_frame = ttk.Frame(main_frame)
        audio_control_frame.pack(fill=tk.X, pady=5)
        
        play_selected_button = ttk.Button(audio_control_frame, text="選択再生", command=self.play_selected_audio)
        play_selected_button.pack(side=tk.LEFT, padx=5)
        
        play_all_button = ttk.Button(audio_control_frame, text="全て再生", command=self.play_all_audio)
        play_all_button.pack(side=tk.LEFT, padx=5)
        
        stop_button = ttk.Button(audio_control_frame, text="再生停止", command=self.stop_audio)
        stop_button.pack(side=tk.LEFT, padx=5)
        
        clear_list_button = ttk.Button(audio_control_frame, text="リストをクリア", command=self.clear_audio_list)
        clear_list_button.pack(side=tk.LEFT, padx=5)
        
        self.status_var = tk.StringVar(value="準備完了")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.text_area.tag_configure("chunk1", background="#E6F3FF")
        self.text_area.tag_configure("chunk2", background="#F5F5DC")
        
        self.text_area.bind("<Button-3>", self.show_text_context_menu)
        
        self.audio_files_listbox.bind("<Double-Button-1>", lambda e: self.play_selected_audio())
        
    def select_output_dir(self):
        directory = filedialog.askdirectory(initialdir=self.output_dir_var.get())
        if directory:
            self.output_dir_var.set(directory)
            self.config.set('Settings', 'output_dir', directory)
            self.save_config()
            
    def load_text_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[ ("マークダウンファイル", "*.md"),("テキストファイル", "*.txt"), ("すべてのファイル", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.text_area.delete(1.0, tk.END)
                    self.text_area.insert(tk.END, f.read())
                self.status_var.set(f"ファイルを読み込みました: {os.path.basename(file_path)}")
                # ファイル名(拡張子なし)をファイル名先頭テキストボックスにセット
                base = os.path.splitext(os.path.basename(file_path))[0]
                self.audio_filename_prefix_var.set(base)
            except Exception as e:
                messagebox.showerror("ファイル読み込みエラー", f"ファイルの読み込み中にエラーが発生しました: {str(e)}")
                
    def show_text_context_menu(self, event):
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="区切り線を挿入", command=lambda: self.insert_separator(event))
        context_menu.post(event.x_root, event.y_root)
        
    def insert_separator(self, event):
        cursor_pos = self.text_area.index(tk.INSERT)
        self.text_area.insert(cursor_pos, "\n---\n")
        
    def preview_splitting(self):
        text = self.text_area.get(1.0, tk.END)
        try:
            chunk_size = int(self.chunk_size_var.get())
            if chunk_size <= 0:
                raise ValueError("Chunk size must be positive")
        except ValueError as e:
            messagebox.showerror("分割エラー", f"無効な分割サイズ: {str(e)}")
            return
            
        self.text_area.tag_remove("chunk1", "1.0", tk.END)
        self.text_area.tag_remove("chunk2", "1.0", tk.END)
        
        chunks = self.split_text(text)
        
        start_index = "1.0"
        for i, chunk in enumerate(chunks):
            chunk_end = self.text_area.search(chunk, start_index, stopindex=tk.END, exact=True)
            if not chunk_end:
                continue
                
            chunk_end_line, chunk_end_char = map(int, chunk_end.split('.'))
            end_index = f"{chunk_end_line}.{chunk_end_char + len(chunk)}"
            
            tag = "chunk1" if i % 2 == 0 else "chunk2"
            self.text_area.tag_add(tag, chunk_end, end_index)
            
            start_index = end_index
            
        self.status_var.set(f"分割プレビュー: {len(chunks)}チャンク")
        
    def split_text(self, text):
        # 分割ON/OFF対応
        if not getattr(self, 'split_by_chunk_var', None) or not self.split_by_chunk_var.get():
            # 分割しない場合は全文を1チャンク
            for word, replacement in self.word_replacements.items():
                text = re.sub(re.escape(word), replacement, text, flags=re.IGNORECASE)
            return [text.strip()] if text.strip() else []

        try:
            chunk_size = int(self.chunk_size_var.get())
        except ValueError:
            chunk_size = self.default_chunk_size

        # 大文字小文字を区別せずに置換
        for word, replacement in self.word_replacements.items():
            # re.IGNORECASE で全ての大文字小文字パターンを置換
            text = re.sub(re.escape(word), replacement, text, flags=re.IGNORECASE)

        if "---" in text:
            chunks = [chunk.strip() for chunk in text.split("---") if chunk.strip()]
        else:
            chunks = []
            current_chunk = ""
            sentences = re.split(r'([。．！？\.!\?])', text)
            for i in range(0, len(sentences), 2):
                if i < len(sentences):
                    sentence = sentences[i]
                    if i + 1 < len(sentences):
                        sentence += sentences[i + 1]
                    if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
                        chunks.append(current_chunk)
                        current_chunk = sentence
                    else:
                        current_chunk += sentence
            if current_chunk:
                chunks.append(current_chunk)
        return chunks
        
    def generate_audio(self):
        text = self.text_area.get(1.0, tk.END).strip()
        # マークダウン記号を除去
        text = re.sub(r'[\#\*\-~`>\[\]_\|\=\+\!\$\^\<\>]', '', text)
        if not text:
            messagebox.showerror("エラー", "テキストを入力してください")
            return
            
        endpoint = self.config.get('Azure', 'endpoint', fallback='')
        api_key = self.config.get('Azure', 'api_key', fallback='')
        api_version = self.config.get('Azure', 'api_version', fallback='')
        deployment_name = self.config.get('Azure', 'deployment_name', fallback='')
        
        if not endpoint or not api_key or not api_version or not deployment_name:
            messagebox.showerror("エラー", "Azure設定が不完全です。設定メニューから構成してください。")
            return
            
        output_dir = self.output_dir_var.get()
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = self.audio_filename_prefix_var.get().strip() or "audio"
        # フォルダ名もprefixに
        output_folder = os.path.join(output_dir, f"{prefix}_{timestamp}")
        try:
            os.makedirs(output_folder, exist_ok=True)
        except Exception as e:
            messagebox.showerror("エラー", f"出力フォルダの作成に失敗しました: {str(e)}")
            return
            
        audio_format = self.audio_format_var.get()
        speed = float(self.speed_var.get())
        # 指示プロンプトはTextから取得
        voice_instructions = self.voice_prompt_text.get(1.0, tk.END).strip()
        
        chunks = self.split_text(text)
        if not chunks:
            messagebox.showerror("エラー", "テキストの分割に失敗しました")
            return
            
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Button) and widget.cget("text") == "音声生成":
                widget.config(state="disabled")
                
        self.generated_audio_files = []
        self.audio_files_listbox.delete(0, tk.END)
        
        threading.Thread(target=self._generate_audio_thread, 
                        args=(endpoint, api_key, api_version, deployment_name, 
                              chunks, output_folder, audio_format, speed, voice_instructions)).start()
        
    def _generate_audio_thread(self, endpoint, api_key, api_version, deployment_name, 
                              chunks, output_folder, audio_format, speed, voice_instructions):
        total_chunks = len(chunks)
        failed_chunks = []
        self.status_var.set(f"音声生成中... (0/{total_chunks})")
        self.root.update_idletasks()
        
        try:
            client = AzureOpenAI(
                azure_endpoint=endpoint,
                api_key=api_key,
                api_version=api_version
            )
            prefix = self.audio_filename_prefix_var.get().strip() or "audio"

            for i, chunk in enumerate(chunks):
                if not chunk.strip():
                    continue
                    
                try:
                    self.status_var.set(f"音声生成中... ({i+1}/{total_chunks})")
                    self.root.update_idletasks()
                    
                    filename = f"{prefix}_{i+1:03d}.{audio_format}"
                    output_path = os.path.join(output_folder, filename)
                    
                    response = client.audio.speech.create(
                        model=deployment_name,
                        voice=self.voice_var.get(),
                        input=chunk,
                        response_format=audio_format,
                        speed=speed,
                        instructions=voice_instructions
                    )
                    
                    with open(output_path, "wb") as file:
                        file.write(response.content)
                        
                    self.generated_audio_files.append(output_path)
                    
                    self.audio_files_listbox.insert(tk.END, f"チャンク {i+1}: {os.path.basename(output_path)}")
                    
                except Exception as e:
                    error_msg = f"チャンク {i+1} の処理中にエラーが発生しました: {str(e)}"
                    print(error_msg)
                    failed_chunks.append((i+1, str(e)))
            
            if failed_chunks:
                error_message = "以下のチャンクの処理に失敗しました:\n"
                for chunk_num, error in failed_chunks:
                    error_message += f"チャンク {chunk_num}: {error}\n"
                
                self.root.after(0, lambda: messagebox.showerror("エラー", error_message))
                
            successful = total_chunks - len(failed_chunks)
            self.status_var.set(f"音声生成完了: {successful}/{total_chunks} チャンク成功")
            
        except Exception as e:
            error_msg = f"音声生成に失敗しました: {str(e)}"
            print(error_msg)
            self.root.after(0, lambda: messagebox.showerror("エラー", error_msg))
            self.status_var.set("音声生成失敗")
            
        finally:
            for widget in self.root.winfo_children():
                if isinstance(widget, ttk.Button) and widget.cget("text") == "音声生成":
                    self.root.after(0, lambda w=widget: w.config(state="normal"))
        
    def play_selected_audio(self):
        selected_indices = self.audio_files_listbox.curselection()
        if not selected_indices:
            messagebox.showinfo("情報", "再生するファイルを選択してください")
            return
            
        index = selected_indices[0]
        file_path = self.generated_audio_files[index]
        
        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
        except Exception as e:
            messagebox.showerror("再生エラー", f"ファイルの再生中にエラーが発生しました: {str(e)}")
            
    def play_all_audio(self):
        if not self.generated_audio_files:
            messagebox.showinfo("情報", "音声ファイルがありません")
            return
            
        try:
            pygame.mixer.music.load(self.generated_audio_files[0])
            pygame.mixer.music.play()
        except Exception as e:
            messagebox.showerror("再生エラー", f"ファイルの再生中にエラーが発生しました: {str(e)}")
            
    def stop_audio(self):
        try:
            pygame.mixer.music.stop()
        except Exception as e:
            messagebox.showerror("停止エラー", f"音声の停止中にエラーが発生しました: {str(e)}")
            
    def clear_audio_list(self):
        self.audio_files_listbox.delete(0, tk.END)
        self.generated_audio_files = []
        self.status_var.set("準備完了")
        
    def manage_word_replacements(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("単語置換辞書")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()


        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        list_frame = ttk.LabelFrame(frame, text="置換リスト")
        list_frame.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=5, pady=5)
        
        replacements_listbox = tk.Listbox(list_frame, width=30)
        replacements_scrollbar = ttk.Scrollbar(list_frame, command=replacements_listbox.yview)
        replacements_listbox.config(yscrollcommand=replacements_scrollbar.set)
        
        replacements_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        replacements_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # 最新のself.word_replacementsでリストを初期化
        for word, replacement in self.word_replacements.items():
            replacements_listbox.insert(tk.END, f"{word} → {replacement}")

        # 並び替えボタン追加
        move_frame = ttk.Frame(list_frame)
        move_frame.pack(side=tk.RIGHT, fill=tk.X, pady=2)
        def move_item(direction):
            sel = replacements_listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            items = list(self.word_replacements.items())
            if direction == 'up' and idx > 0:
                items[idx-1], items[idx] = items[idx], items[idx-1]
                idx_new = idx-1
            elif direction == 'down' and idx < len(items)-1:
                items[idx+1], items[idx] = items[idx], items[idx+1]
                idx_new = idx+1
            elif direction == 'top' and idx > 0:
                item = items.pop(idx)
                items.insert(0, item)
                idx_new = 0
            elif direction == 'bottom' and idx < len(items)-1:
                item = items.pop(idx)
                items.append(item)
                idx_new = len(items)-1
            else:
                return
            self.word_replacements = OrderedDict(items)
            self.save_config()
            replacements_listbox.delete(0, tk.END)
            for w, r in self.word_replacements.items():
                replacements_listbox.insert(tk.END, f"{w} → {r}")
            replacements_listbox.selection_set(idx_new)
            replacements_listbox.activate(idx_new)
            replacements_listbox.see(idx_new)
        ttk.Button(move_frame, text="↑ 上へ", command=lambda: move_item('up')).pack(side=tk.TOP, padx=2)
        ttk.Button(move_frame, text="↓ 下へ", command=lambda: move_item('down')).pack(side=tk.TOP, padx=2)
        ttk.Button(move_frame, text="⇑ 一番上", command=lambda: move_item('top')).pack(side=tk.TOP, padx=2)
        ttk.Button(move_frame, text="⇓ 一番下", command=lambda: move_item('bottom')).pack(side=tk.TOP, padx=2)

        edit_frame = ttk.LabelFrame(frame, text="編集")
        edit_frame.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT, padx=5, pady=5)
        
        ttk.Label(edit_frame, text="元の単語:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        word_var = tk.StringVar()
        word_entry = ttk.Entry(edit_frame, textvariable=word_var, width=20)
        word_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(edit_frame, text="置換後:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        replacement_var = tk.StringVar()
        replacement_entry = ttk.Entry(edit_frame, textvariable=replacement_var, width=20)
        replacement_entry.grid(row=1, column=1, padx=5, pady=5)
        
        def on_select(event):
            selection = replacements_listbox.curselection()
            if selection:
                text = replacements_listbox.get(selection[0])
                word, replacement = text.split(" → ")
                word_var.set(word)
                replacement_var.set(replacement)
                
        replacements_listbox.bind('<<ListboxSelect>>', on_select)
        
        def add_replacement():
            word = word_var.get().strip().upper()  # 常に大文字で登録
            replacement = replacement_var.get().strip()
            if not word or not replacement:
                messagebox.showerror("エラー", "単語と置換後の文字列を入力してください")
                return
            self.word_replacements[word] = replacement  # まずメモリ上で追加
            self.config.set('WordReplacements', word, replacement)  # 永続化
            self.save_config()

            # terahara add
            if self.config.has_section('WordReplacements'):
                self.replacements_listbox = dict(self.config.items('WordReplacements'))


            replacements_listbox.delete(0, tk.END)
            for w, r in self.word_replacements.items():
                replacements_listbox.insert(tk.END, f"{w} → {r}")
            word_var.set("")
            replacement_var.set("")
        
        def delete_replacement():
            selection = replacements_listbox.curselection()
            if selection:
                text = replacements_listbox.get(selection[0])
                word, _ = text.split(" → ")
                if word in self.word_replacements:
                    del self.word_replacements[word]  # メモリ上から削除
                    self.config.remove_option('WordReplacements', word)  # 永続化
                    self.save_config()
                    replacements_listbox.delete(selection[0])
                word_var.set("")
                replacement_var.set("")
                
        add_button = ttk.Button(edit_frame, text="追加/更新", command=add_replacement)
        add_button.grid(row=2, column=0, columnspan=2, pady=10)
        
        delete_button = ttk.Button(edit_frame, text="削除", command=delete_replacement)
        delete_button.grid(row=3, column=0, columnspan=2, pady=5)
        
        # 説明ラベル追加
        info_label = ttk.Label(dialog, text="※大文字小文字は同じ扱いになります。登録時は自動的に大文字化されます。", foreground="blue")
        info_label.pack(pady=(10, 0))

        close_button = ttk.Button(dialog, text="閉じる", command=dialog.destroy)
        close_button.pack(side=tk.RIGHT, pady=10)
        
    def manage_voice_styles(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("音声スタイルプロンプト")
        dialog.geometry("600x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        list_frame = ttk.LabelFrame(frame, text="スタイルリスト")
        list_frame.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=5, pady=5)
        
        styles_listbox = tk.Listbox(list_frame, width=30)
        styles_scrollbar = ttk.Scrollbar(list_frame, command=styles_listbox.yview)
        styles_listbox.config(yscrollcommand=styles_scrollbar.set)
        
        styles_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        styles_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # 最新のself.voice_stylesでリストを初期化
        for style_name in self.voice_styles.keys():
            styles_listbox.insert(tk.END, style_name)

        # 並び替えボタン追加
        move_frame = ttk.Frame(list_frame)
        move_frame.pack(side=tk.RIGHT, fill=tk.X, pady=2)
        def move_item(direction):
            sel = styles_listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            items = list(self.voice_styles.items())
            if direction == 'up' and idx > 0:
                items[idx-1], items[idx] = items[idx], items[idx-1]
                idx_new = idx-1
            elif direction == 'down' and idx < len(items)-1:
                items[idx+1], items[idx] = items[idx], items[idx+1]
                idx_new = idx+1
            elif direction == 'top' and idx > 0:
                item = items.pop(idx)
                items.insert(0, item)
                idx_new = 0
            elif direction == 'bottom' and idx < len(items)-1:
                item = items.pop(idx)
                items.append(item)
                idx_new = len(items)-1
            else:
                return
            self.voice_styles = OrderedDict(items)
            self.save_config()
            styles_listbox.delete(0, tk.END)
            for name, _ in self.voice_styles.items():
                styles_listbox.insert(tk.END, name)
            styles_listbox.selection_set(idx_new)
            styles_listbox.activate(idx_new)
            styles_listbox.see(idx_new)
        ttk.Button(move_frame, text="↑ 上へ", command=lambda: move_item('up')).pack(side=tk.TOP, padx=2)
        ttk.Button(move_frame, text="↓ 下へ", command=lambda: move_item('down')).pack(side=tk.TOP, padx=2)
        ttk.Button(move_frame, text="⇑ 一番上", command=lambda: move_item('top')).pack(side=tk.TOP, padx=2)
        ttk.Button(move_frame, text="⇓ 一番下", command=lambda: move_item('bottom')).pack(side=tk.TOP, padx=2)
            
        edit_frame = ttk.LabelFrame(frame, text="編集")
        edit_frame.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT, padx=5, pady=5)
        
        ttk.Label(edit_frame, text="スタイル名:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        style_name_var = tk.StringVar()
        style_name_entry = ttk.Entry(edit_frame, textvariable=style_name_var, width=30)
        style_name_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(edit_frame, text="プロンプト:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        prompt_text = tk.Text(edit_frame, height=10, width=30, wrap=tk.WORD)
        prompt_text.grid(row=1, column=1, padx=5, pady=5)
        
        def on_select(event):
            selection = styles_listbox.curselection()
            if selection:
                style_name = styles_listbox.get(selection[0])
                style_name_var.set(style_name)
                
                prompt_text.delete(1.0, tk.END)
                if style_name in self.voice_styles:
                    prompt_text.insert(tk.END, self.voice_styles[style_name])
                
        styles_listbox.bind('<<ListboxSelect>>', on_select)
        
        def add_style():
            style_name = style_name_var.get().strip()
            prompt = prompt_text.get(1.0, tk.END).strip()
            
            if not style_name or not prompt:
                messagebox.showerror("エラー", "スタイル名とプロンプトを入力してください")
                return
                
            self.voice_styles[style_name] = prompt
            self.config.set('VoiceStyles', style_name, prompt)
            self.save_config()
            
            # configから再構築して最新化
            if self.config.has_section('VoiceStyles'):
                self.voice_styles = dict(self.config.items('VoiceStyles'))
                
            styles_listbox.delete(0, tk.END)
            for name in self.voice_styles.keys():
                styles_listbox.insert(tk.END, name)
                
            self.voice_style_combo['values'] = list(self.voice_styles.keys())
            
            style_name_var.set("")
            prompt_text.delete(1.0, tk.END)
            
        def delete_style():
            selection = styles_listbox.curselection()
            if selection:
                style_name = styles_listbox.get(selection[0])
                
                if style_name in self.voice_styles:
                    del self.voice_styles[style_name]
                    self.config.remove_option('VoiceStyles', style_name)
                    self.save_config()
                    
                    # configから再構築して最新化
                    if self.config.has_section('VoiceStyles'):
                        self.voice_styles = dict(self.config.items('VoiceStyles'))
                    else:
                        self.voice_styles = {}
                        
                    styles_listbox.delete(selection[0])
                    self.voice_style_combo['values'] = list(self.voice_styles.keys())
                    
                style_name_var.set("")
                prompt_text.delete(1.0, tk.END)
                
        add_button = ttk.Button(edit_frame, text="追加/更新", command=add_style)
        add_button.grid(row=2, column=0, columnspan=2, pady=10)
        
        delete_button = ttk.Button(edit_frame, text="削除", command=delete_style)
        delete_button.grid(row=3, column=0, columnspan=2, pady=5)
        
        close_button = ttk.Button(dialog, text="閉じる", command=dialog.destroy)
        close_button.pack(side=tk.RIGHT, pady=10)
        
    def update_output_settings(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("出力設定")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="出力フォルダ:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        output_dir_var = tk.StringVar(value=self.output_dir_var.get())
        output_dir_entry = ttk.Entry(frame, textvariable=output_dir_var, width=30)
        output_dir_entry.grid(row=0, column=1, padx=5, pady=5)
        
        def select_dir():
            directory = filedialog.askdirectory(initialdir=output_dir_var.get())
            if directory:
                output_dir_var.set(directory)
                
        browse_button = ttk.Button(frame, text="...", command=select_dir, width=3)
        browse_button.grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Label(frame, text="音声:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        voice_var = tk.StringVar(value=self.voice_var.get())
        voice_combo = ttk.Combobox(frame, textvariable=voice_var, width=15)
        voice_combo['values'] = self.voices
        voice_combo.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        ttk.Label(frame, text="音声フォーマット:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        audio_format_var = tk.StringVar(value=self.audio_format_var.get())
        audio_format_combo = ttk.Combobox(frame, textvariable=audio_format_var, width=10)
        audio_format_combo['values'] = self.audio_formats
        audio_format_combo.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        
        ttk.Label(frame, text="分割文字数:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        chunk_size_var = tk.StringVar(value=self.chunk_size_var.get())
        chunk_size_entry = ttk.Entry(frame, textvariable=chunk_size_var, width=10)
        chunk_size_entry.grid(row=3, column=1, padx=5, pady=5, sticky="w")
        
        ttk.Label(frame, text="速度:").grid(row=4, column=0, sticky="w", padx=5, pady=5)
        speed_var = tk.StringVar(value=self.speed_var.get())
        speed_values = ["0.5", "0.8", "1.0", "1.2", "1.5", "2.0"]
        speed_combo = ttk.Combobox(frame, textvariable=speed_var, width=10, values=speed_values)
        speed_combo.grid(row=4, column=1, padx=5, pady=5, sticky="w")
        
        def save_settings():
            self.output_dir_var.set(output_dir_var.get())
            self.audio_format_var.set(audio_format_var.get())
            self.chunk_size_var.set(chunk_size_var.get())
            self.speed_var.set(speed_var.get())
            self.voice_var.set(voice_var.get())
            
            self.config.set('Settings', 'output_dir', output_dir_var.get())
            self.config.set('Settings', 'audio_format', audio_format_var.get())
            self.config.set('Settings', 'chunk_size', chunk_size_var.get())
            self.config.set('Settings', 'speed', speed_var.get())
            self.config.set('Settings', 'voice', voice_var.get())
            self.save_config()
            
            dialog.destroy()
            
        save_button = ttk.Button(frame, text="保存", command=save_settings)
        save_button.grid(row=4, column=0, columnspan=3, pady=20)

if __name__ == "__main__":
    root = tk.Tk()
    app = AzureTTSApp(root)
    root.mainloop()