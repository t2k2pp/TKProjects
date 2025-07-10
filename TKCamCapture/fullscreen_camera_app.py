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
        self.available_cameras = []
        self.running = False
        
        # 解像度設定 (用途に応じて変更可能)
        self.target_resolutions = [
            (1920, 1080),  # Full HD
            (1280, 720),   # HD
            (640, 480)     # VGA
        ]
        self.current_resolution_index = 0
        
        # ラベルの作成（映像表示用）
        self.video_label = tk.Label(self.root, bg='black')
        self.video_label.pack(expand=True, fill='both')
        
        # キーバインド
        self.root.bind('<KeyPress>', self.on_key_press)
        self.root.focus_set()  # キーイベントを受け取るためにフォーカスを設定
        
        # 利用可能なカメラを検索
        self.find_available_cameras()
        
        # カメラを初期化
        self.init_camera()
        
        # 映像更新を開始
        self.running = True
        self.update_video()
        
    def find_available_cameras(self):
        """利用可能なカメラを検索"""
        self.available_cameras = []
        
        # 最大10個のカメラをチェック
        for i in range(10):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                self.available_cameras.append(i)
                cap.release()
        
        if not self.available_cameras:
            messagebox.showerror("エラー", "利用可能なカメラが見つかりません")
            self.root.quit()
            return
        
        print(f"利用可能なカメラ: {self.available_cameras}")
    
    def init_camera(self):
        """カメラを初期化"""
        if self.cap:
            self.cap.release()
        
        if self.available_cameras:
            self.cap = cv2.VideoCapture(self.current_camera)
            if not self.cap.isOpened():
                print(f"カメラ {self.current_camera} を開けませんでした")
                return False
            
            # 現在の解像度設定を適用
            target_width, target_height = self.target_resolutions[self.current_resolution_index]
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, target_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, target_height)
            
            # 実際に設定された解像度を確認
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(self.cap.get(cv2.CAP_PROP_FPS))
            
            print(f"カメラ {self.current_camera} を初期化しました")
            print(f"目標解像度: {target_width}x{target_height}")
            print(f"実際の解像度: {actual_width}x{actual_height} @ {fps}fps")
            
            return True
        return False
    
    def switch_resolution(self):
        """解像度を切り替え"""
        self.current_resolution_index = (self.current_resolution_index + 1) % len(self.target_resolutions)
        target_width, target_height = self.target_resolutions[self.current_resolution_index]
        print(f"解像度を {target_width}x{target_height} に変更します")
        self.init_camera()
    
    def switch_camera(self):
        """次のカメラに切り替え"""
        if len(self.available_cameras) > 1:
            current_index = self.available_cameras.index(self.current_camera)
            next_index = (current_index + 1) % len(self.available_cameras)
            self.current_camera = self.available_cameras[next_index]
            
            print(f"カメラを {self.current_camera} に切り替えます")
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
        
        # 次の更新をスケジュール（約30fps）
        self.root.after(33, self.update_video)
    
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
        # ウィンドウが完全に表示されるまで少し待つ
        self.root.after(100, lambda: None)
        self.root.mainloop()

if __name__ == "__main__":
    try:
        app = FullscreenCameraApp()
        app.run()
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        messagebox.showerror("エラー", f"アプリケーションの実行中にエラーが発生しました:\n{e}")
