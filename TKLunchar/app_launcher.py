import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import random
from PIL import Image, ImageTk, ImageSequence
import re
import unicodedata

class AppData:
    def __init__(self, app_name="", exe_path="", description="", search_keywords="", 
                 category_group="", work_group="", category_priority=0, work_priority=0,
                 icon_path="", emoji="📄"):
        self.app_name = app_name
        self.exe_path = exe_path
        self.description = description
        self.search_keywords = search_keywords
        self.category_group = category_group
        self.work_group = work_group
        self.category_priority = category_priority
        self.work_priority = work_priority
        self.icon_path = icon_path
        self.emoji = emoji

    def to_dict(self):
        return {
            "app_name": self.app_name,
            "exe_path": self.exe_path,
            "description": self.description,
            "search_keywords": self.search_keywords,
            "category_group": self.category_group,
            "work_group": self.work_group,
            "category_priority": self.category_priority,
            "work_priority": self.work_priority,
            "icon_path": self.icon_path,
            "emoji": self.emoji
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            app_name=data.get("app_name", ""),
            exe_path=data.get("exe_path", ""),
            description=data.get("description", ""),
            search_keywords=data.get("search_keywords", ""),
            category_group=data.get("category_group", ""),
            work_group=data.get("work_group", ""),
            category_priority=data.get("category_priority", 0),
            work_priority=data.get("work_priority", 0),
            icon_path=data.get("icon_path", ""),
            emoji=data.get("emoji", "📄")
        )


class AppDataManager:
    def __init__(self, file_path="app_data.json"):
        self.file_path = file_path
        self.apps = []
        self.load_data()
    
    def load_data(self):
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    self.apps = [AppData.from_dict(app_dict) for app_dict in data]
            else:
                self.apps = []
        except Exception as e:
            messagebox.showerror("データ読み込みエラー", f"データの読み込み中にエラーが発生しました: {e}")
            self.apps = []
    
    def save_data(self):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as file:
                json.dump([app.to_dict() for app in self.apps], file, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("データ保存エラー", f"データの保存中にエラーが発生しました: {e}")
    
    def add_app(self, app):
        self.apps.append(app)
        self.save_data()
    
    def update_app(self, index, app):
        self.apps[index] = app
        self.save_data()
    
    def delete_app(self, index):
        del self.apps[index]
        self.save_data()
    
    def get_categories(self):
        categories = set()
        for app in self.apps:
            if app.category_group:
                categories.add(app.category_group)
        return sorted(list(categories))
    
    def get_work_groups(self):
        work_groups = set()
        for app in self.apps:
            if app.work_group:
                work_groups.add(app.work_group)
        return sorted(list(work_groups))
    
    def get_apps_by_category(self, category=None):
        if category is None:
            # Get apps without category
            apps = [app for app in self.apps if not app.category_group]
        else:
            apps = [app for app in self.apps if app.category_group == category]
        
        # Sort by category_priority
        return sorted(apps, key=lambda x: x.category_priority)
    
    def get_apps_by_work_group(self, work_group=None):
        if work_group is None:
            # Get apps without work_group
            apps = [app for app in self.apps if not app.work_group]
        else:
            apps = [app for app in self.apps if app.work_group == work_group]
        
        # Sort by work_priority
        return sorted(apps, key=lambda x: x.work_priority)
    
    def search_apps(self, query):
        if not query:
            return sorted(self.apps, key=lambda x: unicodedata.normalize('NFKC', x.app_name))
        
        query = query.lower()
        result = []
        
        for app in self.apps:
            if (query in app.app_name.lower() or 
                query in app.description.lower() or 
                query in app.search_keywords.lower()):
                result.append(app)
        
        return sorted(result, key=lambda x: unicodedata.normalize('NFKC', x.app_name))


class AnimatedGifLabel(tk.Label):
    def __init__(self, master=None, image_path=None, **kwargs):
        super().__init__(master, **kwargs)
        self.frames = []
        self.current_frame = 0
        self.is_animated = False
        self.delay = 100  # Default delay between frames (ms)
        
        if image_path:
            self.load_image(image_path)
    
    def load_image(self, image_path):
        self.stop_animation()
        self.frames = []
        self.current_frame = 0
        
        try:
            with Image.open(image_path) as img:
                # Check if it's an animated GIF
                if getattr(img, "is_animated", False):
                    self.is_animated = True
                    # Extract delay from the first frame or use default
                    self.delay = img.info.get('duration', 100)
                    if self.delay < 20:  # Some GIFs have very small values
                        self.delay = 100
                    
                    # Load all frames
                    for frame in ImageSequence.Iterator(img):
                        frame_copy = frame.copy()
                        frame_copy = frame_copy.resize((48, 48), Image.LANCZOS)
                        photo_image = ImageTk.PhotoImage(frame_copy)
                        self.frames.append(photo_image)
                    
                    # Start with the first frame
                    if self.frames:
                        self.config(image=self.frames[0])
                        self.start_animation()
                else:
                    # For static images
                    self.is_animated = False
                    img = img.resize((48, 48), Image.LANCZOS)
                    photo_image = ImageTk.PhotoImage(img)
                    self.config(image=photo_image)
                    self.image = photo_image  # Keep a reference to prevent garbage collection
        except Exception as e:
            print(f"Error loading image {image_path}: {e}")
            self.config(image="")
            self.is_animated = False
    
    def start_animation(self):
        if self.is_animated and self.frames:
            self._animate()
    
    def _animate(self):
        if not self.is_animated:
            return
        
        if self.frames:
            self.current_frame = (self.current_frame + 1) % len(self.frames)
            self.config(image=self.frames[self.current_frame])
            self.after_id = self.after(self.delay, self._animate)
    
    def stop_animation(self):
        if hasattr(self, 'after_id'):
            self.after_cancel(self.after_id)
            self.after_id = None


class AppTile(tk.Frame):
    def __init__(self, master, app_data, launch_callback, pastel_bg="#F0F0FF", **kwargs):
        super().__init__(master, **kwargs)
        self.app_data = app_data
        self.launch_callback = launch_callback
        
        # Set background color
        self.config(bg=pastel_bg, padx=5, pady=5, relief=tk.RAISED, borderwidth=1)
        
        # Create layout
        self.icon_frame = tk.Frame(self, bg=pastel_bg, width=50, height=50)
        self.icon_frame.pack(pady=(5, 2))
        self.icon_frame.pack_propagate(False)  # Maintain size
        
        # Check if we should use image or emoji
        if app_data.icon_path and os.path.exists(app_data.icon_path):
            self.icon_label = AnimatedGifLabel(self.icon_frame, image_path=app_data.icon_path, bg=pastel_bg)
        else:
            # Use emoji
            self.icon_label = tk.Label(self.icon_frame, text=app_data.emoji, font=("Segoe UI Emoji", 24), bg=pastel_bg)
        
        self.icon_label.pack(fill=tk.BOTH, expand=True)
        
        # App name
        self.name_label = tk.Label(self, text=app_data.app_name, 
                                 wraplength=120, justify=tk.CENTER, 
                                 bg=pastel_bg, font=("Segoe UI", 9))
        self.name_label.pack(pady=(0, 5), fill=tk.X)
        
        # Tooltip
        self.tooltip = None
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        
        # Click event
        self.bind("<Button-1>", self._on_click)
        self.icon_label.bind("<Button-1>", self._on_click)
        self.name_label.bind("<Button-1>", self._on_click)
    
    def _on_enter(self, event):
        if self.app_data.description:
            x, y, _, _ = self.bbox("all")
            x = x + self.winfo_rootx()
            y = y + self.winfo_rooty() + self.winfo_height()
            
            self.tooltip = tk.Toplevel(self)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")
            
            label = tk.Label(self.tooltip, text=self.app_data.description, 
                           justify=tk.LEFT, background="#FFFFCC", 
                           relief=tk.SOLID, borderwidth=1,
                           font=("Segoe UI", 9), wraplength=250, padx=5, pady=3)
            label.pack()
    
    def _on_leave(self, event):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None
    
    def _on_click(self, event):
        if self.launch_callback:
            self.launch_callback(self.app_data)


class GroupTile(tk.Frame):
    def __init__(self, master, group_name, select_callback, pastel_bg="#F0F0FF", **kwargs):
        super().__init__(master, **kwargs)
        self.group_name = group_name
        self.select_callback = select_callback
        
        # Extract emoji from the beginning of group name
        emoji = group_name[0] if group_name and re.match(r'^\p{Emoji}', group_name, re.UNICODE) else "📁"
        display_name = group_name[1:] if emoji != "📁" else group_name
        
        # Set background color
        self.config(bg=pastel_bg, padx=5, pady=5, relief=tk.RAISED, borderwidth=1)
        
        # Create layout
        self.icon_frame = tk.Frame(self, bg=pastel_bg, width=50, height=50)
        self.icon_frame.pack(pady=(5, 2))
        self.icon_frame.pack_propagate(False)  # Maintain size
        
        # Use emoji
        self.icon_label = tk.Label(self.icon_frame, text=emoji, font=("Segoe UI Emoji", 24), bg=pastel_bg)
        self.icon_label.pack(fill=tk.BOTH, expand=True)
        
        # Group name
        self.name_label = tk.Label(self, text=display_name, 
                                 wraplength=120, justify=tk.CENTER, 
                                 bg=pastel_bg, font=("Segoe UI", 9))
        self.name_label.pack(pady=(0, 5), fill=tk.X)
        
        # Click event
        self.bind("<Button-1>", self._on_click)
        self.icon_label.bind("<Button-1>", self._on_click)
        self.name_label.bind("<Button-1>", self._on_click)
    
    def _on_click(self, event):
        if self.select_callback:
            self.select_callback(self.group_name)


class AppLauncherGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("アプリケーションランチャー")
        self.root.geometry("800x600")
        self.data_manager = AppDataManager()
        
        # Set pastel background colors for different modes
        self.bg_colors = {
            "alphabetical": "#F0F0FF",  # Light blue
            "category": "#FFF0F0",      # Light pink
            "work_group": "#F0FFF0"     # Light green
        }
        
        self.current_mode = "alphabetical"
        self.current_category = None
        self.current_work_group = None
        
        self.create_widgets()
        self.show_alphabetical()
    
    def create_widgets(self):
        # Top frame with mode buttons
        self.top_frame = tk.Frame(self.root, pady=10)
        self.top_frame.pack(fill=tk.X)
        
        self.btn_alphabetical = ttk.Button(self.top_frame, text="文字コード順", 
                                        command=self.show_alphabetical)
        self.btn_alphabetical.pack(side=tk.LEFT, padx=5)
        
        self.btn_category = ttk.Button(self.top_frame, text="カテゴリグループ", 
                                     command=self.show_categories)
        self.btn_category.pack(side=tk.LEFT, padx=5)
        
        self.btn_work_group = ttk.Button(self.top_frame, text="作業グループ", 
                                       command=self.show_work_groups)
        self.btn_work_group.pack(side=tk.LEFT, padx=5)
        
        # Search frame (visible only in alphabetical mode)
        self.search_frame = tk.Frame(self.root, pady=5)
        self.search_frame.pack(fill=tk.X)
        
        tk.Label(self.search_frame, text="検索:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.on_search_change)
        self.search_entry = ttk.Entry(self.search_frame, textvariable=self.search_var, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        
        # Navigation frame
        self.nav_frame = tk.Frame(self.root, pady=5)
        self.nav_frame.pack(fill=tk.X)
        
        self.back_button = ttk.Button(self.nav_frame, text="← 戻る", command=self.go_back)
        # Only show back button when in a category or work group
        
        # Edit button
        self.edit_button = ttk.Button(self.nav_frame, text="アプリ管理", command=self.open_app_manager)
        self.edit_button.pack(side=tk.RIGHT, padx=10)
        
        # Title label
        self.title_label = tk.Label(self.nav_frame, text="すべてのアプリ", font=("Segoe UI", 12, "bold"))
        self.title_label.pack(side=tk.LEFT, padx=10)
        
        # Scrollable content area
        self.canvas = tk.Canvas(self.root)
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Make sure the canvas expands with the window
        self.root.bind("<Configure>", self.on_window_resize)
        
        # Mouse wheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
    
    def on_window_resize(self, event):
        # Update the canvas's width when the window is resized
        if event.widget == self.root:
            self.canvas.itemconfig(self.canvas_frame, width=event.width-20)  # Account for scrollbar
    
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def set_background_color(self):
        bg_color = self.bg_colors.get(self.current_mode, "#FFFFFF")
        self.root.configure(bg=bg_color)
        self.top_frame.configure(bg=bg_color)
        self.search_frame.configure(bg=bg_color)
        self.nav_frame.configure(bg=bg_color)
        self.canvas.configure(bg=bg_color)
        self.scrollable_frame.configure(bg=bg_color)
        self.title_label.configure(bg=bg_color)
    
    def clear_content(self):
        # Clear the current content
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
    
    def show_alphabetical(self):
        self.current_mode = "alphabetical"
        self.current_category = None
        self.current_work_group = None
        
        # Update UI
        self.search_frame.pack(fill=tk.X)
        self.title_label.config(text="すべてのアプリ")
        
        # Hide back button
        if self.back_button.winfo_manager():
            self.back_button.pack_forget()
        
        self.set_background_color()
        self.display_apps(self.data_manager.search_apps(self.search_var.get()))
    
    def show_categories(self):
        self.current_mode = "category"
        self.current_category = None
        self.current_work_group = None
        
        # Update UI
        self.search_frame.pack_forget()  # Hide search in category mode
        self.title_label.config(text="カテゴリ一覧")
        
        # Hide back button initially
        if self.back_button.winfo_manager():
            self.back_button.pack_forget()
        
        self.set_background_color()
        
        # Display categories
        self.clear_content()
        categories = self.data_manager.get_categories()
        
        grid_frame = tk.Frame(self.scrollable_frame, bg=self.bg_colors[self.current_mode])
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Add root apps first (without category)
        row, col = 0, 0
        max_cols = 5  # Number of tiles per row
        
        root_apps = self.data_manager.get_apps_by_category(None)
        for app in root_apps:
            app_tile = AppTile(grid_frame, app, self.launch_app, pastel_bg=self.bg_colors[self.current_mode])
            app_tile.grid(row=row, column=col, padx=5, pady=5)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        # Add category tiles
        for category in categories:
            group_tile = GroupTile(grid_frame, category, self.select_category, 
                                 pastel_bg=self.bg_colors[self.current_mode])
            group_tile.grid(row=row, column=col, padx=5, pady=5)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
    
    def show_work_groups(self):
        self.current_mode = "work_group"
        self.current_category = None
        self.current_work_group = None
        
        # Update UI
        self.search_frame.pack_forget()  # Hide search in work group mode
        self.title_label.config(text="作業グループ一覧")
        
        # Hide back button initially
        if self.back_button.winfo_manager():
            self.back_button.pack_forget()
        
        self.set_background_color()
        
        # Display work groups
        self.clear_content()
        work_groups = self.data_manager.get_work_groups()
        
        grid_frame = tk.Frame(self.scrollable_frame, bg=self.bg_colors[self.current_mode])
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Add root apps first (without work group)
        row, col = 0, 0
        max_cols = 5  # Number of tiles per row
        
        root_apps = self.data_manager.get_apps_by_work_group(None)
        for app in root_apps:
            app_tile = AppTile(grid_frame, app, self.launch_app, pastel_bg=self.bg_colors[self.current_mode])
            app_tile.grid(row=row, column=col, padx=5, pady=5)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        # Add work group tiles
        for work_group in work_groups:
            group_tile = GroupTile(grid_frame, work_group, self.select_work_group, 
                                 pastel_bg=self.bg_colors[self.current_mode])
            group_tile.grid(row=row, column=col, padx=5, pady=5)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
    
    def select_category(self, category):
        self.current_category = category
        self.title_label.config(text=f"カテゴリ: {category}")
        
        # Show back button
        self.back_button.pack(side=tk.LEFT, padx=5, before=self.title_label)
        
        # Display apps in this category
        self.display_apps(self.data_manager.get_apps_by_category(category))
    
    def select_work_group(self, work_group):
        self.current_work_group = work_group
        self.title_label.config(text=f"作業グループ: {work_group}")
        
        # Show back button
        self.back_button.pack(side=tk.LEFT, padx=5, before=self.title_label)
        
        # Display apps in this work group
        self.display_apps(self.data_manager.get_apps_by_work_group(work_group))
    
    def go_back(self):
        if self.current_mode == "category":
            self.show_categories()
        elif self.current_mode == "work_group":
            self.show_work_groups()
    
    def on_search_change(self, *args):
        if self.current_mode == "alphabetical":
            self.display_apps(self.data_manager.search_apps(self.search_var.get()))
    
    def display_apps(self, apps):
        self.clear_content()
        
        grid_frame = tk.Frame(self.scrollable_frame, bg=self.bg_colors[self.current_mode])
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        row, col = 0, 0
        max_cols = 5  # Number of tiles per row
        
        for app in apps:
            app_tile = AppTile(grid_frame, app, self.launch_app, pastel_bg=self.bg_colors[self.current_mode])
            app_tile.grid(row=row, column=col, padx=5, pady=5)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
    
    def launch_app(self, app_data):
        if not app_data.exe_path:
            messagebox.showwarning("実行エラー", "実行ファイルのパスが設定されていません。")
            return
        
        try:
            os.startfile(app_data.exe_path)
        except Exception as e:
            messagebox.showerror("実行エラー", f"アプリケーションの起動に失敗しました: {e}")
    
    def open_app_manager(self):
        app_manager = AppManagerWindow(self.root, self.data_manager)
        self.root.wait_window(app_manager)
        
        # Refresh display after editing
        if self.current_mode == "alphabetical":
            self.show_alphabetical()
        elif self.current_mode == "category" and self.current_category:
            self.select_category(self.current_category)
        elif self.current_mode == "category":
            self.show_categories()
        elif self.current_mode == "work_group" and self.current_work_group:
            self.select_work_group(self.current_work_group)
        elif self.current_mode == "work_group":
            self.show_work_groups()


class AppManagerWindow(tk.Toplevel):
    def __init__(self, parent, data_manager):
        super().__init__(parent)
        self.title("アプリケーション管理")
        self.geometry("800x600")
        self.data_manager = data_manager
        
        # Make it modal
        self.transient(parent)
        self.grab_set()
        
        self.create_widgets()
        self.populate_app_list()
    
    def create_widgets(self):
        # App list on the left
        list_frame = tk.Frame(self)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=10, pady=10)
        
        tk.Label(list_frame, text="アプリ一覧").pack(fill=tk.X)
        
        self.app_listbox = tk.Listbox(list_frame, width=30, height=20)
        self.app_listbox.pack(fill=tk.BOTH, expand=True)
        self.app_listbox.bind('<<ListboxSelect>>', self.on_app_select)
        
        button_frame = tk.Frame(list_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        self.add_button = ttk.Button(button_frame, text="追加", command=self.add_app)
        self.add_button.pack(side=tk.LEFT, padx=2)
        
        self.edit_button = ttk.Button(button_frame, text="編集", command=self.edit_app, state=tk.DISABLED)
        self.edit_button.pack(side=tk.LEFT, padx=2)
        
        self.delete_button = ttk.Button(button_frame, text="削除", command=self.delete_app, state=tk.DISABLED)
        self.delete_button.pack(side=tk.LEFT, padx=2)
        
        # App details form on the right
        form_frame = tk.Frame(self)
        form_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tk.Label(form_frame, text="アプリ情報", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        
        # App name
        tk.Label(form_frame, text="アプリ名:").grid(row=1, column=0, sticky="w", pady=2)
        self.app_name_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.app_name_var, width=40).grid(row=1, column=1, sticky="w", pady=2)
        
        # Exe path
        tk.Label(form_frame, text="実行ファイルパス:").grid(row=2, column=0, sticky="w", pady=2)
        path_frame = tk.Frame(form_frame)
        path_frame.grid(row=2, column=1, sticky="w", pady=2)
        
        self.exe_path_var = tk.StringVar()
        ttk.Entry(path_frame, textvariable=self.exe_path_var, width=32).pack(side=tk.LEFT)
        ttk.Button(path_frame, text="...", width=3, command=self.browse_exe).pack(side=tk.LEFT, padx=2)
        
        # Description
        tk.Label(form_frame, text="説明:").grid(row=3, column=0, sticky="w", pady=2)
        self.description_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.description_var, width=40).grid(row=3, column=1, sticky="w", pady=2)
        
        # Search keywords
        tk.Label(form_frame, text="検索用ワード:").grid(row=4, column=0, sticky="w", pady=2)
        self.search_keywords_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.search_keywords_var, width=40).grid(row=4, column=1, sticky="w", pady=2)
        
        # Category group
        tk.Label(form_frame, text="カテゴリグループ:").grid(row=5, column=0, sticky="w", pady=2)
        self.category_group_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.category_group_var, width=40).grid(row=5, column=1, sticky="w", pady=2)
        
        # Work group
        tk.Label(form_frame, text="作業グループ:").grid(row=6, column=0, sticky="w", pady=2)
        self.work_group_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.work_group_var, width=40).grid(row=6, column=1, sticky="w", pady=2)
        
        # Category priority
        tk.Label(form_frame, text="カテゴリ内表示優先度:").grid(row=7, column=0, sticky="w", pady=2)
        self.category_priority_var = tk.IntVar()
        ttk.Spinbox(form_frame, from_=0, to=999, textvariable=self.category_priority_var, width=5).grid(row=7, column=1, sticky="w", pady=2)
        
        # Work priority
        tk.Label(form_frame, text="作業グループ内表示優先度:").grid(row=8, column=0, sticky="w", pady=2)
        self.work_priority_var = tk.IntVar()
        ttk.Spinbox(form_frame, from_=0, to=999, textvariable=self.work_priority_var, width=5).grid(row=8, column=1, sticky="w", pady=2)
        
        # Icon path
        tk.Label(form_frame, text="アイコン画像パス:").grid(row=9, column=0, sticky="w", pady=2)
        icon_frame = tk.Frame(form_frame)
        icon_frame.grid(row=9, column=1, sticky="w", pady=2)
        
        self.icon_path_var = tk.StringVar()
        ttk.Entry(icon_frame, textvariable=self.icon_path_var, width=32).pack(side=tk.LEFT)
        ttk.Button(icon_frame, text="...", width=3, command=self.browse_icon).pack(side=tk.LEFT, padx=2)
        
        # Emoji
        tk.Label(form_frame, text="アイコン代替絵文字:").grid(row=10, column=0, sticky="w", pady=2)
        self.emoji_var = tk.StringVar(value="📄")  # Default emoji
        ttk.Entry(form_frame, textvariable=self.emoji_var, width=5).grid(row=10, column=1, sticky="w", pady=2)
        
        # Preview frame
        preview_frame = tk.LabelFrame(form_frame, text="プレビュー")
        preview_frame.grid(row=11, column=0, columnspan=2, sticky="ew", pady=10)
        
        self.preview_icon = tk.Label(preview_frame, text="📄", font=("Segoe UI Emoji", 24))
        self.preview_icon.pack(pady=5)
        
        # Action Buttons
        button_frame2 = tk.Frame(form_frame)
        button_frame2.grid(row=12, column=0, columnspan=2, sticky="ew", pady=10)
        
        self.save_button = ttk.Button(button_frame2, text="保存", command=self.save_app)
        self.save_button.pack(side=tk.LEFT, padx=5)
        
        self.cancel_button = ttk.Button(button_frame2, text="キャンセル", command=self.cancel_edit)
        self.cancel_button.pack(side=tk.LEFT, padx=5)
        
        # Disable form initially
        self.set_form_state(tk.DISABLED)
        
        # Variables to keep track of editing state
        self.editing_index = None
        self.is_adding = False
    
    def populate_app_list(self):
        self.app_listbox.delete(0, tk.END)
        for app in self.data_manager.apps:
            self.app_listbox.insert(tk.END, app.app_name)
    
    def on_app_select(self, event=None):
        selection = self.app_listbox.curselection()
        if selection:
            self.edit_button.config(state=tk.NORMAL)
            self.delete_button.config(state=tk.NORMAL)
        else:
            self.edit_button.config(state=tk.DISABLED)
            self.delete_button.config(state=tk.DISABLED)
    
    def add_app(self):
        self.is_adding = True
        self.editing_index = None
        
        # Clear and enable form
        self.clear_form()
        self.set_form_state(tk.NORMAL)
        
        # Set focus on app name
        self.app_name_var.set("新しいアプリ")
    
    def edit_app(self):
        selection = self.app_listbox.curselection()
        if not selection:
            return
        
        self.is_adding = False
        self.editing_index = selection[0]
        app = self.data_manager.apps[self.editing_index]
        
        # Fill form with app data
        self.app_name_var.set(app.app_name)
        self.exe_path_var.set(app.exe_path)
        self.description_var.set(app.description)
        self.search_keywords_var.set(app.search_keywords)
        self.category_group_var.set(app.category_group)
        self.work_group_var.set(app.work_group)
        self.category_priority_var.set(app.category_priority)
        self.work_priority_var.set(app.work_priority)
        self.icon_path_var.set(app.icon_path)
        self.emoji_var.set(app.emoji)
        
        # Update preview
        self.update_preview()
        
        # Enable form
        self.set_form_state(tk.NORMAL)
    
    def delete_app(self):
        selection = self.app_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        app = self.data_manager.apps[index]
        
        if messagebox.askyesno("確認", f"アプリ '{app.app_name}' を削除しますか？"):
            self.data_manager.delete_app(index)
            self.populate_app_list()
            self.clear_form()
    
    def browse_exe(self):
        filepath = filedialog.askopenfilename(
            title="実行ファイルを選択",
            filetypes=[("実行ファイル", "*.exe"), ("すべてのファイル", "*.*")]
        )
        if filepath:
            self.exe_path_var.set(filepath)
    
    def browse_icon(self):
        filepath = filedialog.askopenfilename(
            title="アイコン画像を選択",
            filetypes=[("画像ファイル", "*.png *.jpg *.jpeg *.gif *.ico"), ("すべてのファイル", "*.*")]
        )
        if filepath:
            self.icon_path_var.set(filepath)
            self.update_preview()
    
    def update_preview(self):
        icon_path = self.icon_path_var.get()
        emoji = self.emoji_var.get()
        
        # Clear current preview
        self.preview_icon.config(image="", text="")
        
        if icon_path and os.path.exists(icon_path):
            try:
                # Check if it's an animated GIF
                with Image.open(icon_path) as img:
                    if getattr(img, "is_animated", False):
                        # For simplicity, just show the first frame in preview
                        img.seek(0)
                        img = img.resize((48, 48), Image.LANCZOS)
                    else:
                        img = img.resize((48, 48), Image.LANCZOS)
                    
                    photo_image = ImageTk.PhotoImage(img)
                    self.preview_icon.config(image=photo_image)
                    self.preview_icon.image = photo_image  # Keep a reference
            except Exception as e:
                print(f"Error loading preview image: {e}")
                self.preview_icon.config(text=emoji, font=("Segoe UI Emoji", 24))
        else:
            self.preview_icon.config(text=emoji, font=("Segoe UI Emoji", 24))
    
    def save_app(self):
        # Validate inputs
        app_name = self.app_name_var.get().strip()
        if not app_name:
            messagebox.showerror("エラー", "アプリ名を入力してください")
            return
        
        # Create AppData object
        app = AppData(
            app_name=app_name,
            exe_path=self.exe_path_var.get().strip(),
            description=self.description_var.get().strip(),
            search_keywords=self.search_keywords_var.get().strip(),
            category_group=self.category_group_var.get().strip(),
            work_group=self.work_group_var.get().strip(),
            category_priority=self.category_priority_var.get(),
            work_priority=self.work_priority_var.get(),
            icon_path=self.icon_path_var.get().strip(),
            emoji=self.emoji_var.get() or "📄"
        )
        
        # Save to data manager
        if self.is_adding:
            self.data_manager.add_app(app)
        else:
            self.data_manager.update_app(self.editing_index, app)
        
        # Update UI
        self.populate_app_list()
        self.clear_form()
        self.set_form_state(tk.DISABLED)
        self.is_adding = False
        self.editing_index = None
    
    def cancel_edit(self):
        self.clear_form()
        self.set_form_state(tk.DISABLED)
        self.is_adding = False
        self.editing_index = None
    
    def clear_form(self):
        self.app_name_var.set("")
        self.exe_path_var.set("")
        self.description_var.set("")
        self.search_keywords_var.set("")
        self.category_group_var.set("")
        self.work_group_var.set("")
        self.category_priority_var.set(0)
        self.work_priority_var.set(0)
        self.icon_path_var.set("")
        self.emoji_var.set("📄")
        
        # Reset preview
        self.preview_icon.config(image="", text="📄")
    
    def set_form_state(self, state):
        # Enable/disable all form elements
        for child in self.winfo_children():
            for widget in child.winfo_children():
                if isinstance(widget, (ttk.Entry, ttk.Spinbox, ttk.Button)):
                    widget.config(state=state)
                elif isinstance(widget, tk.Frame):
                    for w in widget.winfo_children():
                        if isinstance(w, (ttk.Entry, ttk.Spinbox, ttk.Button)):
                            w.config(state=state)
        
        # Always enable add/edit/delete buttons
        self.add_button.config(state=tk.NORMAL)
        
        if state == tk.DISABLED:
            self.save_button.config(state=tk.DISABLED)
            self.cancel_button.config(state=tk.DISABLED)
        else:
            self.save_button.config(state=tk.NORMAL)
            self.cancel_button.config(state=tk.NORMAL)


def main():
    root = tk.Tk()
    app = AppLauncherGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
