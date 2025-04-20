import tkinter as tk
from PIL import ImageGrab
import datetime
import os

class ScreenshotApp:
    def __init__(self, root):
        """アプリケーションの初期化"""
        self.root = root
        self.root.title("スクリーンショットアプリ")
        
        # ウィンドウのサイズと位置を設定
        self.root.geometry("400x200")
        self.root.resizable(False, False)
        
        # スクリーンショットボタンの作成
        self.screenshot_button = tk.Button(
            root, 
            text="スクリーンショットを撮影", 
            command=self.take_screenshot,
            font=("Helvetica", 12),
            height=2,
            width=20
        )
        self.screenshot_button.pack(pady=30)
        
        # ステータスラベルの作成
        self.status_label = tk.Label(
            root, 
            text="ボタンをクリックしてスクリーンショットを撮影してください",
            font=("Helvetica", 10)
        )
        self.status_label.pack(pady=10)
        
        # 保存先フォルダの作成（存在しない場合）
        self.screenshots_folder = "screenshots"
        if not os.path.exists(self.screenshots_folder):
            os.makedirs(self.screenshots_folder)
            
        # 保存先パスを表示
        self.path_label = tk.Label(
            root, 
            text=f"保存先: {os.path.abspath(self.screenshots_folder)}",
            font=("Helvetica", 9)
        )
        self.path_label.pack(pady=10)
        
    def take_screenshot(self):
        """スクリーンショットを撮影して保存する関数"""
        try:
            # アプリを最小化してスクリーンショットを撮影できるようにする
            self.root.iconify()
            
            # 少し待機してアプリが最小化されるのを確認
            self.root.after(500, self._capture_screenshot)
        except Exception as e:
            self.status_label.config(text=f"エラー: {str(e)}", fg="red")
            self.root.deiconify()  # エラーが発生した場合はウィンドウを元に戻す
    
    def _capture_screenshot(self):
        """実際のスクリーンショット撮影処理"""
        try:
            # 現在の日時を取得
            now = datetime.datetime.now()
            timestamp = now.strftime("%Y%m%d_%H%M%S")  # 年月日_時分秒のフォーマット
            
            # スクリーンショットを撮影
            screenshot = ImageGrab.grab()
            
            # ファイル名と保存先パスを作成
            filename = f"screenshot_{timestamp}.png"
            filepath = os.path.join(self.screenshots_folder, filename)
            
            # スクリーンショットを保存
            screenshot.save(filepath)
            
            # 成功メッセージの表示
            self.status_label.config(text=f"スクリーンショットを保存しました: {filename}", fg="green")
        except Exception as e:
            self.status_label.config(text=f"エラー: {str(e)}", fg="red")
        finally:
            # スクリーンショット後にアプリウィンドウを元に戻す
            self.root.deiconify()

if __name__ == "__main__":
    # メインウィンドウの作成
    root = tk.Tk()
    app = ScreenshotApp(root)
    
    # アプリケーションを実行
    root.mainloop()
