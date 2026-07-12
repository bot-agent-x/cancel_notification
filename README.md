# Cancel Notification - セラピスト予約空き監視プログラム

セラピストの予約サイトを監視し、キャンセルによる空き枠が発生したときにDiscordへ通知するPythonプログラムです。

## 機能

- 指定したセラピストの予約空きを10分間隔で自動チェック
- 今日から翌週の金曜日までの期間を監視
- 90分コースの空き枠を検出
- 新しく空いた枠（キャンセル発生）のみをDiscordへ通知（一括通知対応）
- 土日空き枠の通知を除外
- プログラム停止時にDiscordで通知

## 前提条件

- Python 3.8以上
- pip（Pythonパッケージマネージャー）

## セットアップ手順

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. Playwrightブラウザのインストール

```bash
playwright install chromium
```

### 3. 環境変数の設定

`.env.example` を `.env` にコピーし、必要な情報を入力してください：

```bash
cp .env.example .env
```

`.env` ファイルを編集：

```env
LOGIN_ID=your_login_id
PASSWORD=your_password
DISCORD_WEBHOOK_URL=your_discord_webhook_url
```

- **LOGIN_ID**: 予約サイトのログインID
- **PASSWORD**: 予約サイトのパスワード
- **DISCORD_WEBHOOK_URL**: 通知先DiscordチャンネルのWebhook URL

### 4. 監視対象セラピストの設定

`therapists.csv` を編集して、監視したいセラピストを追加してください：

```csv
therapist_id,therapist_name
1,市ヶ谷　胡桃ゆの
2,セラピスト名2
3,セラピスト名3
```

- `therapist_id`: 識別用ID（任意の番号）
- `therapist_name`: 予約サイトに表示されるセラピスト名（完全一致または部分一致）

## 実行方法

### ローカルでの手動実行（推奨）

プロジェクトディレクトリで以下のコマンドを実行：

```bash
python monitor.py
```

**実行時の注意点：**
- プログラムは10分間隔で監視を継続します
- 停止する場合は `Ctrl + C` を押してください
- 停止時にDiscordで通知が送信されます
- PCをシャットダウンするとプログラムも停止します（通知は送信されません）

### 通常実行（フォアグラウンド）

```bash
python monitor.py
```

### バックグラウンド実行（Windows）

PowerShellを使用：

```powershell
Start-Process python -ArgumentList "monitor.py" -WindowStyle Hidden
```

または、バックグラウンドジョブとして実行：

```powershell
Start-Job -ScriptBlock { python monitor.py }
```

### バックグラウンド実行（Linux/macOS）

```bash
nohup python monitor.py > monitor.log 2>&1 &
```

### 停止方法

- フォアグラウンド実行の場合: `Ctrl + C`（Discordで停止通知が送信されます）
- バックグラウンド実行の場合: プロセスをkill

## 動作仕様

### 監視期間

- 常に「今日」から「翌週の金曜日」までを監視
- 日付は動的に計算されるため、手動更新不要

### チェック間隔

- デフォルト: 10分ごと
- `monitor.py` の `CHECK_INTERVAL_MINUTES` 定数で変更可能

### 空き枠検出ロジック

1. セラピストを選択
2. 90分コースを選択可能か確認
3. 施術開始時間の選択肢を確認
4. 選択肢がある場合 → 空き枠あり
5. コース選択不可または時間選択肢なし → 満席

### 通知内容

**空き枠検出時：**
新しい空き枠が検出された場合、以下の内容でDiscord通知（セラピストごとに一括）：

```
[NEW] キャンセル空き発生！
セラピスト: セラピスト名
  2026-07-06 19:30
  2026-07-06 20:00

予約ページ: https://za-gin.mplus-system.info/guest/reservation.php
```

**プログラム開始時：**
```
[START] キャンセル監視開始
時間: 2026-07-10 08:00:00
監視期間: 2026-07-10 ～ 2026-07-17
対象セラピスト: 11名
チェック間隔: 10分
```

**プログラム停止時：**
```
[STOP] キャンセル監視停止
時間: 2026-07-10 18:30:00
理由: ユーザーによる手動停止
```

**エラー発生時：**
```
[ERROR] キャンセル監視エラー停止
時間: 2026-07-10 18:30:00
エラー: エラー内容
```

### 状態管理

- `availability_state.json` ファイルで前回の空き状況を記録
- プログラム再起動後も状態を維持
- 新しく空いた枠のみを通知（重複通知なし）

## ファイル構成

```
cancel_notification/
├── monitor.py              # メイン監視プログラム
├── requirements.txt        # Python依存パッケージ
├── .env                    # 環境変数設定（作成が必要）
├── .env.example           # 環境変数テンプレート
├── therapists.csv         # 監視対象セラピストリスト
├── availability_state.json # 空き状況状態ファイル（自動生成）
├── test_playwright.py     # 参考用スクリプト
└── README.md              # このファイル
```

## 注意事項

- **このプログラムは予約の確認・完了を行いません**。空き枠の検出と通知のみです。
- 予約サイトの構造変更により動作しなくなる可能性があります。
- 過度なアクセスを避けるため、チェック間隔を短くしすぎないでください。
- ログイン情報は `.env` ファイルに含まれるため、このファイルを公開リポジトリにコミットしないでください。

## トラブルシューティング

### Playwright関連エラー

```bash
playwright install chromium
```

### ログインエラー

- `.env` ファイルのLOGIN_IDとPASSWORDが正しいか確認
- 予約サイトでパスワードが変更されていないか確認

### Discord通知が来ない

- `.env` ファイルのDISCORD_WEBHOOK_URLが正しいか確認
- Webhook URLが有効か確認

### セラピストが見つからない

- `therapists.csv` のセラピスト名が予約サイトの表示と完全一致しているか確認
- 部分一致で検索するため、名前の一部でも動作します

## ライセンス

このプロジェクトは個人的な使用を目的としています。
