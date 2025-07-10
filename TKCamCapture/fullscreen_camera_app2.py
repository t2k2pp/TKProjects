import cv2
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import threading
import time

class FullscreenCameraApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("フルスクリーンカメラビューアー")
        
        # フルスクリーン設定
        self.root.attributes('-fullscreen', True)
        self.root.configure(bg='black')
        
        # カメラ関連の変数
        self.current_camera = 0
        self.cap = None
        self.available_cameras = [0]  # デフォルトでカメラ0を設定
        self.running = False
        self.camera_search_complete = False
        
        # 解像度設定（4K対応）
        self.target_resolutions = [
            (3840, 2160),  # 4K UHD
            (2560, 1440),  # 1440p (2K)
            (1920, 1080),  # Full HD
            (1280, 720),   # HD
            (640, 480)     # VGA
        ]
        self.current_resolution_index = 2  # Full HDで開始（4Kは重いため）
        
        # ローディング表示用ラベル
        self.loading_label = tk.Label(
            self.root, 
            text="カメラを初期化中...", 
            fg='white', 
            bg='black', 
            font=('Arial', 24)
        )
        self.loading_label.pack(expand=True)
        
        # ラベルの作成（映像表示用）
        self.video_label = tk.Label(self.root, bg='black')
        
        # キーバインド
        self.root.bind('<KeyPress>', self.on_key_press)
        self.root.focus_set()
        
        # 最初に画面を表示してから初期化を開始
        self.root.after(50, self.initialize_app)
        
    def initialize_app(self):
        """アプリケーションの初期化（非同期）"""
        # まずデフォルトカメラで開始
        if self.init_camera_quick():
            self.start_video_display()
            
            # バックグラウンドで他のカメラを検索
            threading.Thread(target=self.find_available_cameras_background, daemon=True).start()
        else:
            # デフォルトカメラが使えない場合は全検索
            self.loading_label.config(text="利用可能なカメラを検索中...")
            threading.Thread(target=self.find_all_cameras_and_init, daemon=True).start()
    
    def init_camera_quick(self):
        """デフォルトカメラで素早く初期化"""
        try:
            self.cap = cv2.VideoCapture(0)
            if self.cap.isOpened():
                # Full HDで起動（安定性優先）
                target_width, target_height = self.target_resolutions[self.current_resolution_index]
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, target_width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, target_height)
                
                print("カメラ 0 で素早く初期化完了（Full HD）")
                print("Rキーで4K/1440p/HD/VGAに変更可能")
                return True
            else:
                self.cap.release()
                return False
        except Exception as e:
            print(f"クイック初期化エラー: {e}")
            return False
    
    def start_video_display(self):
        """映像表示を開始"""
        self.loading_label.pack_forget()  # ローディング表示を隠す
        self.video_label.pack(expand=True, fill='both')  # 映像表示を開始
        
        self.running = True
        self.update_video()
    
    def find_available_cameras_background(self):
        """バックグラウンドで利用可能なカメラを検索"""
        found_cameras = [0]  # カメラ0は既に確認済み
        
        # カメラ1-5のみチェック（範囲を限定して高速化）
        for i in range(1, 6):
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    # 接続テストのためのフレーム読み込み
                    ret, _ = cap.read()
                    if ret:
                        found_cameras.append(i)
                cap.release()
            except Exception:
                continue
        
        self.available_cameras = found_cameras
        self.camera_search_complete = True
        print(f"バックグラウンド検索完了: {self.available_cameras}")
    
    def find_all_cameras_and_init(self):
        """全カメラ検索後に初期化（フォールバック）"""
        self.available_cameras = []
        
        for i in range(6):  # 範囲を6個に限定
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    ret, _ = cap.read()
                    if ret:
                        self.available_cameras.append(i)
                cap.release()
            except Exception:
                continue
        
        if self.available_cameras:
            self.current_camera = self.available_cameras[0]
            # UIスレッドで初期化を実行
            self.root.after(0, self.init_camera_and_start)
        else:
            self.root.after(0, self.show_no_camera_error)
    
    def init_camera_and_start(self):
        """カメラ初期化と映像開始"""
        if self.init_camera():
            self.start_video_display()
        else:
            self.show_no_camera_error()
    
    def show_no_camera_error(self):
        """カメラなしエラー表示"""
        self.loading_label.config(text="利用可能なカメラが見つかりません")
        self.root.after(3000, self.quit_app)
    
    def init_camera(self):
        """カメラを初期化"""
        if self.cap:
            self.cap.release()
        
        try:
            self.cap = cv2.VideoCapture(self.current_camera)
            if not self.cap.isOpened():
                return False
            
            # 解像度設定
            target_width, target_height = self.target_resolutions[self.current_resolution_index]
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, target_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, target_height)
            
            # 4K使用時はフレームレートを調整
            if target_width >= 3840:
                self.cap.set(cv2.CAP_PROP_FPS, 30)  # 4Kでは30fps制限
            
            # 実際の設定値を確認
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = int(self.cap.get(cv2.CAP_PROP_FPS))
            
            # 解像度名を表示
            resolution_names = {
                (3840, 2160): "4K UHD",
                (2560, 1440): "1440p (2K)",
                (1920, 1080): "Full HD",
                (1280, 720): "HD",
                (640, 480): "VGA"
            }
            
            target_name = resolution_names.get((target_width, target_height), f"{target_width}x{target_height}")
            actual_name = resolution_names.get((actual_width, actual_height), f"{actual_width}x{actual_height}")
            
            print(f"カメラ {self.current_camera}: {target_name} → {actual_name} @ {actual_fps}fps")
            
            # 4K使用時の注意表示
            if actual_width >= 3840:
                print("⚠️  4K解像度使用中 - 高いCPU/GPU性能が必要です")
                
            return True
        except Exception as e:
            print(f"カメラ初期化エラー: {e}")
            return False
    
    def switch_camera(self):
        """次のカメラに切り替え"""
        if not self.camera_search_complete:
            print("カメラ検索中です。しばらくお待ちください。")
            return
            
        if len(self.available_cameras) > 1:
            current_index = self.available_cameras.index(self.current_camera)
            next_index = (current_index + 1) % len(self.available_cameras)
            self.current_camera = self.available_cameras[next_index]
            
            print(f"カメラを {self.current_camera} に切り替えます")
            self.init_camera()
    
    def switch_resolution(self):
        """解像度を切り替え"""
        self.current_resolution_index = (self.current_resolution_index + 1) % len(self.target_resolutions)
        target_width, target_height = self.target_resolutions[self.current_resolution_index]
        
        resolution_names = {
            (3840, 2160): "4K UHD",
            (2560, 1440): "1440p (2K)", 
            (1920, 1080): "Full HD",
            (1280, 720): "HD",
            (640, 480): "VGA"
        }
        resolution_name = resolution_names.get((target_width, target_height), f"{target_width}x{target_height}")
        
        print(f"解像度を {resolution_name} に変更します")
        if target_width >= 3840:
            print("⚠️  4K解像度 - 処理が重い場合はHDに戻してください")
            
        self.init_camera()
    
    def update_video(self):
        """映像を更新"""
        if not self.running:
            return
        
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                # フレームをRGBに変換
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # ウィンドウサイズを取得
                window_width = self.root.winfo_width()
                window_height = self.root.winfo_height()
                
                if window_width > 1 and window_height > 1:
                    # アスペクト比を維持しながらフルスクリーンに拡大
                    frame_height, frame_width = frame_rgb.shape[:2]
                    
                    # アスペクト比を計算
                    frame_aspect = frame_width / frame_height
                    window_aspect = window_width / window_height
                    
                    if frame_aspect > window_aspect:
                        # フレームの方が横長の場合、幅に合わせる
                        new_width = window_width
                        new_height = int(window_width / frame_aspect)
                    else:
                        # ウィンドウの方が横長の場合、高さに合わせる
                        new_height = window_height
                        new_width = int(window_height * frame_aspect)
                    
                    # リサイズ
                    frame_resized = cv2.resize(frame_rgb, (new_width, new_height))
                    
                    # PILイメージに変換
                    image = Image.fromarray(frame_resized)
                    photo = ImageTk.PhotoImage(image)
                    
                    # ラベルを更新
                    self.video_label.configure(image=photo)
                    self.video_label.image = photo  # 参照を保持
        
        # 次の更新をスケジュール（解像度に応じてフレームレート調整）
        if self.cap:
            current_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            if current_width >= 3840:  # 4K
                update_interval = 50  # 20fps (4K用)
            elif current_width >= 2560:  # 1440p
                update_interval = 40  # 25fps (1440p用)  
            else:  # Full HD以下
                update_interval = 33  # 30fps (通常)
        else:
            update_interval = 33
            
        self.root.after(update_interval, self.update_video)
    
    def on_key_press(self, event):
        """キーボードイベントを処理"""
        if event.keysym == 'Escape':
            self.quit_app()
        elif event.keysym == 'space':
            self.switch_camera()
        elif event.keysym == 'r' or event.keysym == 'R':
            self.switch_resolution()
    
    def quit_app(self):
        """アプリケーションを終了"""
        self.running = False
        if self.cap:
            self.cap.release()
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        """アプリケーションを開始"""
        self.root.mainloop()

if __name__ == "__main__":
    try:
        app = FullscreenCameraApp()
        app.run()
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        messagebox.showerror("エラー", f"アプリケーションの実行中にエラーが発生しました:\n{e}")
