if __name__ == "__main__":
    root = tk.Tk()
    app = KeyLoggerApp(root)
    
    # アプリケーション終了時の確認
    def on_closing():
        if messagebox.askokcancel("終了確認", "アプリケーションを終了してもよろしいですか？"):
            if app.is_recording:
                app.toggle_recording()  # 記録中なら停止
                
            if app.log_entries and messagebox.askyesno("保存確認", "ログを保存しますか？"):
                app.save_to_csv()
                
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # 使用説明を表示
    instruction_text = """
使用方法:
1.「記録開始」ボタンをクリックして操作の記録を開始します。
2. 通常通りアプリケーションを操作してください。キーボード入力やマウスクリックが記録されます。
3.「記録停止」ボタンをクリックして記録を終了します。
4.「CSVに保存」ボタンでデータを保存できます。

記録される情報:
・キーボード操作（すべてのキー押下）
・マウスクリック（左、中、右ボタン）
・マウスリリース
・マウス座標
・アクティブウィンドウの情報

※このツールはテスト目的でのみ使用してください。個人情報等が記録される可能性があるため、取り扱いに注意してください。
"""
    messagebox.showinfo("使用方法", instruction_text)
    
    # グローバルホットキーの設定（Windowsのみ）
    if platform.system() == "Windows":
        try:
            # Windowsの場合はグローバルホットキーを設定する方法を追加
            # これは一例で、実際の実装は環境によって異なる場合があります
            def register_hotkeys():
                try:
                    # ホットキー登録は本格的に実装する場合は別途ライブラリを使用することを推奨
                    # 例: keyboard, pynput などのライブラリ
                    pass
                except Exception as e:
                    print(f"ホットキー登録エラー: {str(e)}")
            
            register_hotkeys()
        except:
            pass

    # フルスクリーンアプリケーションのサポート（オプション）
    def check_fullscreen_apps():
        """フルスクリーンアプリケーションでも記録できるように定期チェック"""
        if app.is_recording:
            # フルスクリーンアプリの検出とイベント処理の調整
            # 実際の実装はOS依存となるため、ここでは概念実装のみ
            if platform.system() == "Windows":
                try:
                    # Windowsの場合、フルスクリーンアプリケーションの検出
                    foreground_hwnd = app.user32.GetForegroundWindow()
                    
                    # ウィンドウの位置とサイズを取得
                    rect = ctypes.wintypes.RECT()
                    app.user32.GetWindowRect(foreground_hwnd, ctypes.byref(rect))
                    
                    # 画面サイズ取得
                    screen_width = app.user32.GetSystemMetrics(0)  # SM_CXSCREEN
                    screen_height = app.user32.GetSystemMetrics(1)  # SM_CYSCREEN
                    
                    # フルスクリーンかどうかの判定
                    is_fullscreen = (rect.left == 0 and rect.top == 0 and 
                                    rect.right >= screen_width and rect.bottom >= screen_height)
                    
                    if is_fullscreen:
                        # フルスクリーンアプリの場合、特別な処理を行う
                        app.status_label.config(text="フルスクリーンモード中")
                except:
                    pass
        
        # 1秒後に再度チェック
        root.after(1000, check_fullscreen_apps)
    
    # フルスクリーンチェックを開始
    root.after(1000, check_fullscreen_apps)
    
    # トレイアイコンの追加（オプション）
    try:
        # トレイアイコンのサポートはオプションで、PySimpleGUIトレイなどのライブラリが必要
        # ここではサンプルコードのみ提供
        def setup_tray():
            try:
                # 実際にはこれを実装するには追加ライブラリが必要です
                pass
            except Exception as e:
                print(f"トレイアイコン設定エラー: {str(e)}")
        
        # 必要に応じてトレイアイコンをセットアップ
        # setup_tray()
    except:
        pass
    
    # 詳細設定ウィンドウを作成する関数
    def open_settings():
        settings_window = tk.Toplevel(root)
        settings_window.title("詳細設定")
        settings_window.geometry("400x300")
        settings_window.transient(root)
        
        # 設定オプション
        tk.Label(settings_window, text="ログ設定", font=("", 12, "bold")).pack(pady=10)
        
        # マウス移動の記録
        record_mouse_move_var = tk.BooleanVar(value=False)
        tk.Checkbutton(settings_window, text="マウス移動を記録する（注：データ量が増加します）", 
                     variable=record_mouse_move_var).pack(anchor="w", padx=20)
        
        # サンプリングレート
        tk.Label(settings_window, text="サンプリングレート:").pack(anchor="w", padx=20, pady=(10, 0))
        sampling_rate = tk.Scale(settings_window, from_=10, to=1000, orient="horizontal", 
                               label="ミリ秒", length=300)
        sampling_rate.set(100)
        sampling_rate.pack(padx=20)
        
        # 他のオプション...
        
        # 適用ボタン
        def apply_settings():
            # ここで設定を適用する処理を実装
            settings_window.destroy()
            
        tk.Button(settings_window, text="適用", command=apply_settings).pack(pady=20)
        
    # メニューバーの追加
    menu_bar = tk.Menu(root)
    
    # ファイルメニュー
    file_menu = tk.Menu(menu_bar, tearoff=0)
    file_menu.add_command(label="新規記録", command=lambda: (app.clear_log(), app.toggle_recording() if not app.is_recording else None))
    file_menu.add_command(label="CSVに保存", command=app.save_to_csv)
    file_menu.add_separator()
    file_menu.add_command(label="終了", command=on_closing)
    menu_bar.add_cascade(label="ファイル", menu=file_menu)
    
    # 設定メニュー
    settings_menu = tk.Menu(menu_bar, tearoff=0)
    settings_menu.add_command(label="詳細設定", command=open_settings)
    menu_bar.add_cascade(label="設定", menu=settings_menu)
    
    # ヘルプメニュー
    help_menu = tk.Menu(menu_bar, tearoff=0)
    help_menu.add_command(label="使い方", command=lambda: messagebox.showinfo("使用方法", instruction_text))
    help_menu.add_command(label="バージョン情報", command=lambda: messagebox.showinfo("バージョン情報", "テスト用キーロガー v1.0\n\n単体テスト・結合テスト用のイベントログツール"))
    menu_bar.add_cascade(label="ヘルプ", menu=help_menu)
    
    root.config(menu=menu_bar)
    
    # アプリケーションの実行
    root.mainloop()
