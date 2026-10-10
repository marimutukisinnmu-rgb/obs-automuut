# PikaStream Key v1.0

Scroll Lock キーの状態に合わせて、OBS Studio の「デスクトップ音声」をミュート／ミュート解除する Windows 向け Python ツールです。

## 動作

- **Scroll Lock ON** → OBS「デスクトップ音声」をミュート
- **Scroll Lock OFF** → OBS「デスクトップ音声」のミュートを解除
- キー状態を 0.25 秒ごとに確認
- 起動時と OBS 再接続時は、現在の Scroll Lock 状態を読み取って OBS に反映
- OBS WebSocket が切断された場合は、自動で再接続を試行
- ログをターミナルと `pistream_key.log` に出力

## 必要なもの

- Windows
- Python 3.10 以降を推奨
- OBS Studio の WebSocket サーバー（OBS Studio 28 以降に標準搭載）
- Python パッケージ `obsws-python`

## セットアップ

1. このリポジトリをダウンロードまたは clone します。
2. リポジトリのフォルダーで、依存パッケージをインストールします。

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. OBS Studio を開き、**ツール → WebSocket サーバー設定**で WebSocket サーバーを有効にします。
4. OBS のポート番号とパスワードを確認します（通常のポート番号は `4455`）。
5. 次のコマンドで起動します。

   ```powershell
   python .\pistream_key.py
   ```

6. 初回起動時に `config.ini` が作成されます。設定ファイルを開き、OBS の設定に合わせて値を保存してから、もう一度起動してください。

## config.ini

```ini
[obs]
host = 127.0.0.1
port = 4455
password = OBSのWebSocketパスワード
input_name = デスクトップ音声
poll_interval = 0.25
```

- `host`: OBS が動作している PC のアドレス
- `port`: OBS WebSocket のポート
- `password`: OBS WebSocket のパスワード。パスワード認証を使わない場合は空欄
- `input_name`: OBS の音声入力名。初期値は `デスクトップ音声`
- `poll_interval`: Scroll Lock の確認間隔（秒）。初期値は 0.25 秒

## 注意

- OBS 内の音声入力名が `デスクトップ音声` と異なる場合は、`input_name` を実際の名前に変更してください。
- `config.ini` にはパスワードを保存するため、公開・共有しないでください。Git 管理対象外に設定済みです。
- このツールは OBS のミュート状態を切り替えるのではなく、キー状態に対応する状態を明示的に設定します。
- 終了するにはターミナルで **Ctrl+C** を押してください。
