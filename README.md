# 📻 π Radio

Raspberry Pi をネットラジオプレーヤーにする Web アプリケーションです。  
ブラウザから radiko のライブ再生・タイムフリー再生を操作できます。

![Python](https://img.shields.io/badge/Python-3.x-blue)
![Flask](https://img.shields.io/badge/Flask-2.x-lightgrey)
![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi%201B-red)

---

## 特徴

- **ライブ再生** — radiko のエリア内局をリストから選んでワンクリックで再生
- **タイムフリー再生** — 過去7日分の番組表から聴きたい番組を選んで再生（無料会員の範囲内）
- **今日のスケジュール表示** — 局をクリックするとその局の当日番組表（現在〜3時間後）を表示
- **Web UI** — 同一 LAN 内の任意のブラウザ・スマートフォンから操作可能
- **systemd 対応** — 電源投入時に自動起動


## スクリーンショット
![](https://github.com/femrik/pi-radio/blob/image/Screenshot_20260527-203527.png)

## 動作環境

- Raspberry Pi 1B（他の Pi でも動作するはず）
- Raspberry Pi OS (Debian Bookworm 系)
- Python 3.9 以上

---

## 依存ツール

| ツール | 役割 |
|---|---|
| [mpv](https://mpv.io/) | 音声再生 |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | ストリーム取得 |
| [yt-dlp-radiko](https://github.com/kikuchy/yt-dlp-radiko) | radiko 認証プラグイン |
| Flask | Web サーバー |
| requests | radiko API 通信 |

---

## インストール

### 1. リポジトリのクローン

```bash
git clone https://github.com/<yourname>/pi-radio.git
cd pi-radio
```

### 2. システムパッケージ

```bash
sudo apt update
sudo apt install -y mpv python3 python3-pip
```

### 3. Python パッケージ

```bash
pip3 install flask requests yt-dlp yt-dlp-radiko
```

> pip が古くてエラーになる場合:
> ```bash
> sudo apt install python3-flask python3-requests
> pip3 install yt-dlp yt-dlp-radiko
> ```

### 4. 動作確認

```bash
python3 app.py
```

ブラウザで `http://<Raspberry Pi の IP>:5000` にアクセスしてください。

---

## systemd への登録（自動起動）

電源投入時に自動でサービスとして起動させる場合は以下を実行します。

```bash
sudo tee /etc/systemd/system/pi-radio.service << 'EOF'
[Unit]
Description=Pi Radio - Internet Radio Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/pi-radio
ExecStart=/usr/bin/python3 /home/pi/pi-radio/app.py
Restart=on-failure
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable pi-radio
sudo systemctl start pi-radio
```

> `WorkingDirectory` / `ExecStart` のパスはご自身の環境に合わせてください。  
> `yt-dlp` をユーザーローカルにインストールした場合は `ExecStart` のパスも要確認。

### 管理コマンド

```bash
sudo systemctl status pi-radio      # 状態確認
sudo journalctl -u pi-radio -f      # リアルタイムログ
sudo systemctl restart pi-radio     # 再起動
sudo systemctl disable pi-radio     # 自動起動の解除
```

---

## ファイル構成

```
pi-radio/
├── app.py               # Flask サーバー・API ルート
├── radiko.py            # radiko エリア検出・局一覧・番組表取得
├── player.py            # yt-dlp + mpv 再生制御
├── templates/
│   └── index.html       # フロントエンド UI
└── requirements.txt
```

---

## 音が出ない場合

```bash
# サウンドデバイスの確認
aplay -l

# 音量の確認・調整
amixer sget Master
amixer sset Master 90%

# HDMI とアナログの切り替え
sudo raspi-config   # → System Options → Audio
```

---

## 注意事項

- radiko の利用には [radiko の利用規約](https://radiko.jp/rg/terms/) が適用されます。
- タイムフリーは無料会員の範囲（過去7日・1週間に3時間まで）でご利用ください。
- 本ツールは個人の私的利用を目的としています。

---

## ライセンス

MIT
