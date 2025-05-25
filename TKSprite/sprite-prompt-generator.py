#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
スプライト画像生成プロンプトジェネレーター
ゲーム開発用のスプライト画像をAIで生成するためのプロンプトを作成するツール
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import pyperclip  # クリップボードへのコピー用（pip install pyperclipが必要）

class SpritePromptGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("スプライト画像生成プロンプトジェネレーター")
        self.root.geometry("900x700")
        
        # データ定義
        self.define_data()
        
        # UI構築
        self.create_ui()
        
    def define_data(self):
        """プルダウンメニュー用のデータを定義"""
        # シーン設定のオプション
        self.scene_options = {
            "ファンタジー": {
                "中世ファンタジーの村": "medieval fantasy village",
                "ダークゴシック城": "dark gothic castle",
                "魔法の森": "enchanted mystical forest",
                "古代ドワーフの鉱山": "ancient dwarven mines",
                "天空神殿": "floating sky temple",
                "海底遺跡": "underwater atlantis ruins"
            },
            "SF・未来": {
                "サイバーパンクネオン街": "cyberpunk neon district",
                "宇宙ステーション内部": "space station interior",
                "異星の地表": "alien planet surface",
                "終末後の荒野": "post-apocalyptic wasteland",
                "未来的研究施設": "futuristic laboratory",
                "メカ格納庫": "mecha hangar bay"
            },
            "現代・日常": {
                "現代都市の中心街": "modern city downtown",
                "居心地の良い郊外の家": "cozy suburban home",
                "日本の学校教室": "japanese school classroom",
                "ショッピングモール": "busy shopping mall",
                "レトロアーケード": "retro arcade"
            },
            "自然・環境": {
                "トロピカルビーチ": "tropical paradise beach",
                "密林ジャングル": "dense amazon jungle",
                "凍てつく北極": "frozen arctic tundra",
                "火山溶岩洞窟": "volcanic lava caves",
                "桜の庭園": "cherry blossom garden"
            },
            "その他": {
                "白塗りつぶし": "Fill with solid white",
                "黒塗りつぶし": "Fill with solid black",
                "赤塗りつぶし": "Fill with solid Red",
                "青塗りつぶし": "Fill with solid Blue",
                "緑塗りつぶし": "Fill with solid Green",
            }
        }
        
        # アートスタイルのオプション
        self.art_styles = {
            "ピクセルアート": {
                "8ビットレトロ": "8-bit retro pixel art",
                "16ビットクラシック": "16-bit classic pixel art",
                "32ビット詳細": "32-bit detailed pixel art",
                "モダンHDピクセル": "modern HD pixel art",
                "マイクロピクセル": "micro pixel art"
            },
            "イラスト": {
                "セルシェードカートゥーン": "cel-shaded cartoon style",
                "アニメ・マンガ風": "anime/manga illustration",
                "西洋コミック風": "western comic book style",
                "ちびキャラ風": "chibi/super-deformed style",
                "フラットデザイン": "vector flat design"
            },
            "ペイント": {
                "デジタル油彩": "digital oil painting",
                "水彩画風": "watercolor wash style",
                "印象派風": "impressionist brushwork",
                "ゴシックダーク": "gothic dark art",
                "幻想的絵画": "ethereal fantasy painting"
            },
            "リアル": {
                "写実的3D": "photorealistic 3D render",
                "様式化セミリアル": "stylized semi-realistic",
                "手描きリアル": "hand-painted realistic"
            }
        }
        
        # グリッドサイズのオプション
        self.grid_sizes = [
            "16x16 pixels",
            "24x24 pixels",
            "32x32 pixels",
            "48x48 pixels",
            "64x64 pixels",
            "128x128 pixels"
        ]
        
        # グリッド配置のオプション
        self.grid_layouts = [
            "4x4 grid (16 sprites)",
            "6x4 grid (24 sprites)",
            "8x8 grid (64 sprites)",
            "10x10 grid (100 sprites)",
            "カスタム配置"
        ]
        
    def create_ui(self):
        """UIを構築"""
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # タイトルラベル
        title_label = ttk.Label(main_frame, text="スプライト画像生成プロンプトジェネレーター", 
                               font=("", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=10)
        
        # ノートブック（タブコンテナ）
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        # 各タブを作成
        self.create_character_tab()
        self.create_environment_tab()
        self.create_ui_tab()
        
        # 共通設定エリア
        common_frame = ttk.LabelFrame(main_frame, text="共通設定", padding="10")
        common_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        self.create_common_settings(common_frame)
        
        # プロンプト生成ボタン
        generate_button = ttk.Button(main_frame, text="プロンプト生成", 
                                   command=self.generate_prompt, 
                                   style="Accent.TButton")
        generate_button.grid(row=3, column=0, columnspan=2, pady=10)
        
        # 生成されたプロンプト表示エリア
        prompt_frame = ttk.LabelFrame(main_frame, text="生成されたプロンプト", padding="10")
        prompt_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        self.prompt_text = scrolledtext.ScrolledText(prompt_frame, height=8, wrap=tk.WORD)
        self.prompt_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # コピーボタン
        copy_button = ttk.Button(prompt_frame, text="クリップボードにコピー", 
                               command=self.copy_to_clipboard)
        copy_button.grid(row=1, column=0, pady=5)
        
        # グリッドの重み設定
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        prompt_frame.columnconfigure(0, weight=1)
        prompt_frame.rowconfigure(0, weight=1)
        
    def create_character_tab(self):
        """キャラクタータブを作成"""
        char_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(char_frame, text="キャラクター")
        
        # キャラクター種類
        ttk.Label(char_frame, text="キャラクター種類:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.char_type = ttk.Combobox(char_frame, values=[
            "fantasy warrior", "medieval knight", "wizard mage", "rogue thief",
            "archer ranger", "demon lord", "angel paladin", "robot mech",
            "space marine", "ninja assassin", "pirate captain", "カスタム"
        ], width=30)
        self.char_type.grid(row=0, column=1, pady=5, padx=5)
        self.char_type.set("fantasy warrior")
        
        # カスタム入力
        self.char_custom = ttk.Entry(char_frame, width=30)
        self.char_custom.grid(row=0, column=2, pady=5, padx=5)
        
        # アニメーション種類（複数選択）
        ttk.Label(char_frame, text="アニメーション:").grid(row=1, column=0, sticky=tk.NW, pady=5)
        anim_frame = ttk.Frame(char_frame)
        anim_frame.grid(row=1, column=1, columnspan=2, sticky=tk.W, pady=5)
        
        self.animations = {
            "待機": tk.BooleanVar(value=True),
            "歩行": tk.BooleanVar(value=True),
            "走行": tk.BooleanVar(value=False),
            "攻撃": tk.BooleanVar(value=True),
            "魔法": tk.BooleanVar(value=False),
            "被ダメージ": tk.BooleanVar(value=True),
            "死亡": tk.BooleanVar(value=False),
            "ジャンプ": tk.BooleanVar(value=False)
        }
        
        for i, (anim_name, var) in enumerate(self.animations.items()):
            cb = ttk.Checkbutton(anim_frame, text=anim_name, variable=var)
            cb.grid(row=i//4, column=i%4, sticky=tk.W, padx=5)
            
        # 視点角度
        ttk.Label(char_frame, text="視点角度:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.char_view = ttk.Combobox(char_frame, values=[
            "top-down view", "3/4 view", "side view", "front view", "isometric view"
        ], width=30)
        self.char_view.grid(row=2, column=1, pady=5, padx=5)
        self.char_view.set("3/4 view")
        
    def create_environment_tab(self):
        """環境タブを作成"""
        env_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(env_frame, text="環境・背景")
        
        # タイル要素（複数選択）
        ttk.Label(env_frame, text="タイル要素:").grid(row=0, column=0, sticky=tk.NW, pady=5)
        tile_frame = ttk.Frame(env_frame)
        tile_frame.grid(row=0, column=1, columnspan=2, sticky=tk.W, pady=5)
        
        self.tile_elements = {
            "地面・床": tk.BooleanVar(value=True),
            "壁": tk.BooleanVar(value=True),
            "扉・出入口": tk.BooleanVar(value=True),
            "装飾物": tk.BooleanVar(value=True),
            "植物・自然": tk.BooleanVar(value=False),
            "建物部品": tk.BooleanVar(value=False),
            "道・通路": tk.BooleanVar(value=True),
            "水・液体": tk.BooleanVar(value=False)
        }
        
        for i, (element_name, var) in enumerate(self.tile_elements.items()):
            cb = ttk.Checkbutton(tile_frame, text=element_name, variable=var)
            cb.grid(row=i//4, column=i%4, sticky=tk.W, padx=5)
            
        # タイル接続性
        ttk.Label(env_frame, text="タイル接続:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.tile_seamless = ttk.Combobox(env_frame, values=[
            "シームレス接続", "独立タイル", "自動タイル形式"
        ], width=30)
        self.tile_seamless.grid(row=1, column=1, pady=5, padx=5)
        self.tile_seamless.set("シームレス接続")
        
        # 照明設定
        ttk.Label(env_frame, text="照明方向:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.lighting = ttk.Combobox(env_frame, values=[
            "top-left lighting", "top lighting", "ambient lighting", "no shadows"
        ], width=30)
        self.lighting.grid(row=2, column=1, pady=5, padx=5)
        self.lighting.set("top-left lighting")
        
    def create_ui_tab(self):
        """UIタブを作成"""
        ui_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(ui_frame, text="UIエレメント")
        
        # UI要素種類（複数選択）
        ttk.Label(ui_frame, text="UI要素:").grid(row=0, column=0, sticky=tk.NW, pady=5)
        ui_element_frame = ttk.Frame(ui_frame)
        ui_element_frame.grid(row=0, column=1, columnspan=2, sticky=tk.W, pady=5)
        
        self.ui_elements = {
            "ボタン": tk.BooleanVar(value=True),
            "体力バー": tk.BooleanVar(value=True),
            "ダイアログ": tk.BooleanVar(value=True),
            "アイコン": tk.BooleanVar(value=True),
            "インベントリ": tk.BooleanVar(value=False),
            "メニュー枠": tk.BooleanVar(value=False),
            "通知ポップアップ": tk.BooleanVar(value=False),
            "ミニマップ": tk.BooleanVar(value=False)
        }
        
        for i, (ui_name, var) in enumerate(self.ui_elements.items()):
            cb = ttk.Checkbutton(ui_element_frame, text=ui_name, variable=var)
            cb.grid(row=i//4, column=i%4, sticky=tk.W, padx=5)
            
        # 状態バリエーション
        ttk.Label(ui_frame, text="状態表示:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.ui_states = ttk.Combobox(ui_frame, values=[
            "通常・ホバー・押下", "通常・ホバー・押下・無効", "通常のみ", "全状態アニメーション付き"
        ], width=30)
        self.ui_states.grid(row=1, column=1, pady=5, padx=5)
        self.ui_states.set("通常・ホバー・押下")
        
        # ゲームジャンル
        ttk.Label(ui_frame, text="ゲームジャンル:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.game_genre = ttk.Combobox(ui_frame, values=[
            "fantasy RPG", "sci-fi shooter", "casual puzzle", "horror survival",
            "strategy game", "platformer", "fighting game"
        ], width=30)
        self.game_genre.grid(row=2, column=1, pady=5, padx=5)
        self.game_genre.set("fantasy RPG")
        
    def create_common_settings(self, parent):
        """共通設定を作成"""
        # シーン設定
        ttk.Label(parent, text="シーン設定:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        # シーンカテゴリ
        self.scene_category = ttk.Combobox(parent, values=list(self.scene_options.keys()), width=20)
        self.scene_category.grid(row=0, column=1, pady=5, padx=5)
        self.scene_category.bind('<<ComboboxSelected>>', self.update_scene_options)
        self.scene_category.set("ファンタジー")
        
        # シーン詳細
        self.scene_detail = ttk.Combobox(parent, width=30)
        self.scene_detail.grid(row=0, column=2, pady=5, padx=5)
        self.update_scene_options()
        
        # アートスタイル
        ttk.Label(parent, text="アートスタイル:").grid(row=1, column=0, sticky=tk.W, pady=5)
        
        # スタイルカテゴリ
        self.style_category = ttk.Combobox(parent, values=list(self.art_styles.keys()), width=20)
        self.style_category.grid(row=1, column=1, pady=5, padx=5)
        self.style_category.bind('<<ComboboxSelected>>', self.update_style_options)
        self.style_category.set("ピクセルアート")
        
        # スタイル詳細
        self.style_detail = ttk.Combobox(parent, width=30)
        self.style_detail.grid(row=1, column=2, pady=5, padx=5)
        self.update_style_options()
        
        # グリッドサイズ
        ttk.Label(parent, text="グリッドサイズ:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.grid_size = ttk.Combobox(parent, values=self.grid_sizes, width=20)
        self.grid_size.grid(row=2, column=1, pady=5, padx=5)
        self.grid_size.set("32x32 pixels")
        
        # グリッド配置
        ttk.Label(parent, text="グリッド配置:").grid(row=2, column=2, sticky=tk.W, pady=5)
        self.grid_layout = ttk.Combobox(parent, values=self.grid_layouts, width=25)
        self.grid_layout.grid(row=2, column=3, pady=5, padx=5)
        self.grid_layout.set("8x8 grid (64 sprites)")
        
        # 追加オプション
        ttk.Label(parent, text="追加オプション:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.additional_options = ttk.Entry(parent, width=60)
        self.additional_options.grid(row=3, column=1, columnspan=3, pady=5, padx=5)
        self.additional_options.insert(0, "transparent background, pixel-perfect alignment")
        
    def update_scene_options(self, event=None):
        """シーンカテゴリが変更されたときに詳細オプションを更新"""
        category = self.scene_category.get()
        if category in self.scene_options:
            options = list(self.scene_options[category].keys())
            self.scene_detail['values'] = options
            if options:
                self.scene_detail.set(options[0])
                
    def update_style_options(self, event=None):
        """スタイルカテゴリが変更されたときに詳細オプションを更新"""
        category = self.style_category.get()
        if category in self.art_styles:
            options = list(self.art_styles[category].keys())
            self.style_detail['values'] = options
            if options:
                self.style_detail.set(options[0])
                
    def generate_prompt(self):
        """選択された設定に基づいてプロンプトを生成"""
        # 現在のタブを確認
        current_tab = self.notebook.index(self.notebook.select())
        
        # 共通設定を取得
        scene_category = self.scene_category.get()
        scene_detail = self.scene_detail.get()
        scene_eng = self.scene_options.get(scene_category, {}).get(scene_detail, scene_detail)
        
        style_category = self.style_category.get()
        style_detail = self.style_detail.get()
        style_eng = self.art_styles.get(style_category, {}).get(style_detail, style_detail)
        
        grid_size = self.grid_size.get()
        grid_layout = self.grid_layout.get()
        additional = self.additional_options.get()
        
        prompt = ""
        
        if current_tab == 0:  # キャラクタータブ
            # キャラクター種類を取得
            char_type = self.char_custom.get() if self.char_type.get() == "カスタム" else self.char_type.get()
            
            # アニメーションリストを作成
            animations = []
            anim_mapping = {
                "待機": "idle animation (4 frames)",
                "歩行": "walk cycle (8 frames)",
                "走行": "run cycle (8 frames)",
                "攻撃": "attack sequence (6 frames)",
                "魔法": "magic casting (6 frames)",
                "被ダメージ": "hurt reaction (2 frames)",
                "死亡": "death animation (6 frames)",
                "ジャンプ": "jump sequence (4 frames)"
            }
            
            for anim_name, var in self.animations.items():
                if var.get():
                    animations.append(anim_mapping[anim_name])
                    
            view_angle = self.char_view.get()
            
            # プロンプト構築
            prompt = f"Create a character sprite sheet for {char_type} in {scene_eng} setting, "
            prompt += f"{style_eng} style, arranged in {grid_layout}, "
            prompt += f"each sprite {grid_size}, {additional}, "
            prompt += f"showing: {', '.join(animations)}, "
            prompt += f"consistent {view_angle}, dynamic action poses"
            
        elif current_tab == 1:  # 環境タブ
            # タイル要素リストを作成
            elements = []
            element_mapping = {
                "地面・床": "ground and floor tiles",
                "壁": "wall tiles",
                "扉・出入口": "doors and entrances",
                "装飾物": "decorative elements",
                "植物・自然": "plants and nature elements",
                "建物部品": "building components",
                "道・通路": "paths and roads",
                "水・液体": "water and liquid tiles"
            }
            
            for element_name, var in self.tile_elements.items():
                if var.get():
                    elements.append(element_mapping[element_name])
                    
            seamless_mapping = {
                "シームレス接続": "seamless tile edges",
                "独立タイル": "independent tiles",
                "自動タイル形式": "auto-tile format"
            }
            seamless = seamless_mapping.get(self.tile_seamless.get(), "seamless tile edges")
            lighting = self.lighting.get()
            
            # プロンプト構築
            prompt = f"Generate {scene_eng} environment tileset sprite sheet, "
            prompt += f"{style_eng} style with {grid_size} tiles, "
            prompt += f"containing: {', '.join(elements)}, "
            prompt += f"arranged in organized tilemap format, {seamless}, "
            prompt += f"consistent {lighting}, {additional}"
            
        elif current_tab == 2:  # UIタブ
            # UI要素リストを作成
            ui_items = []
            ui_mapping = {
                "ボタン": "buttons (play, settings, inventory)",
                "体力バー": "health and mana bars",
                "ダイアログ": "dialog boxes",
                "アイコン": "skill and item icons",
                "インベントリ": "inventory slots",
                "メニュー枠": "menu frames",
                "通知ポップアップ": "notification popups",
                "ミニマップ": "minimap frame"
            }
            
            for ui_name, var in self.ui_elements.items():
                if var.get():
                    ui_items.append(ui_mapping[ui_name])
                    
            states_mapping = {
                "通常・ホバー・押下": "showing states: normal, hover, pressed",
                "通常・ホバー・押下・無効": "showing states: normal, hover, pressed, disabled",
                "通常のみ": "normal state only",
                "全状態アニメーション付き": "all states with animation frames"
            }
            states = states_mapping.get(self.ui_states.get(), "showing states: normal, hover, pressed")
            genre = self.game_genre.get()
            
            # プロンプト構築
            prompt = f"Design game UI element sprite sheet for {genre} game, "
            prompt += f"{style_eng} visual style, {scene_eng} themed, "
            prompt += f"{grid_layout} arrangement, each element {grid_size}, "
            prompt += f"including: {', '.join(ui_items)}, "
            prompt += f"{states}, consistent visual hierarchy, {additional}"
        
        # プロンプトを表示
        self.prompt_text.delete(1.0, tk.END)
        self.prompt_text.insert(1.0, prompt)
        
    def copy_to_clipboard(self):
        """生成されたプロンプトをクリップボードにコピー"""
        prompt = self.prompt_text.get(1.0, tk.END).strip()
        if prompt:
            try:
                pyperclip.copy(prompt)
                messagebox.showinfo("成功", "プロンプトをクリップボードにコピーしました！")
            except Exception as e:
                messagebox.showerror("エラー", f"クリップボードへのコピーに失敗しました: {str(e)}")
        else:
            messagebox.showwarning("警告", "コピーするプロンプトがありません。")

def main():
    """メイン関数"""
    root = tk.Tk()
    
    # スタイル設定
    style = ttk.Style()
    style.configure('Accent.TButton', foreground='blue')
    
    app = SpritePromptGenerator(root)
    root.mainloop()

if __name__ == "__main__":
    main()