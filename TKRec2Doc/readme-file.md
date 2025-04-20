# スクリーンショット分析ツール

このツールは、連続したスクリーンショットを分析して、パソコン操作の手順を自動的に生成するためのアプリケーションです。Azure OpenAI APIのGPT-4 Vision機能を使用して、画像から操作内容を検出し、詳細な操作マニュアルを作成します。

## 必要要件

- Python 3.7以上
- Azure OpenAIサービスのアカウントとAPIキー
- 以下のPythonパッケージ：
  - tkinter
  - Pillow (PIL)
  - requests

## セットアップ方法

1. 必要なパッケージをインストールします：

```bash
pip install pillow requests
```

2. `config.py`ファイルを編集して、Azure OpenAI APIの設定を行います：
   - `API_ENDPOINT`：Azure OpenAIリソースのエンドポイントURL
   - `API_KEY`：APIキー
   - `API_VERSION`：使用するAPIバージョン
   - `MODEL`：デプロイメント名

3. 必要に応じて、分析用のプロンプトを調整します。

## 使用方法

1. プログラムを実行します：

```bash
python main.py
```

2. GUIが起動したら、以下の手順で操作します：
   - 「画像フォルダ」ボタンをクリックして、分析対象の画像が含まれるフォルダを選択します。
   - 「出力フォルダ」ボタンをクリックして、分析結果を保存するフォルダを選択します。
   - 「開