# lounge-monitor

JCBパークラウンジ予約ページなど、指定したURLの変化を監視するCLIツールです。

## 機能

- URLを一定間隔でポーリング
- 前回取得した内容との差分（ハッシュ）を検知
- 指定キーワードの出現有無の変化を検知
- 変化時にログ出力
- オプションでWebhook通知（JSON: `{ "text": "..." }`）
- オプションでSMTPメール通知

## 使い方

```bash
python3 monitor.py --once
```

初回実行時は `.monitor/state.json` にスナップショットを保存します。2回目以降、変化があれば通知します。

### 例: 5分ごとに監視

```bash
python3 monitor.py \
  --interval 300 \
  --keyword "空き" \
  --keyword "予約可能"
```

### 例: Webhook通知

```bash
python3 monitor.py --webhook-url "https://example.com/hooks/xxxx"
```

### 例: メール通知

```bash
python3 monitor.py \
  --smtp-host smtp.example.com \
  --smtp-port 465 \
  --smtp-user your_user \
  --smtp-password your_password \
  --email-from from@example.com \
  --email-to to@example.com
```

環境変数でも設定できます。

- `MONITOR_WEBHOOK_URL`
- `MONITOR_SMTP_HOST`
- `MONITOR_SMTP_PORT`
- `MONITOR_SMTP_USER`
- `MONITOR_SMTP_PASSWORD`
- `MONITOR_EMAIL_FROM`
- `MONITOR_EMAIL_TO`

## 補足

監視対象ページがログインセッション前提・JavaScript描画前提の場合、HTTP取得結果では実際の表示状態と一致しない可能性があります。
その場合はPlaywright/Seleniumでログイン状態を維持した監視へ拡張してください。
