"""
app.py - π Radio メインサーバー
起動: python3 app.py
アクセス: http://<Raspberry Pi の IP>:5000
"""

import threading
from flask import Flask, render_template, jsonify, request
from radiko import RadikoClient
from player import Player

app    = Flask(__name__)
radiko = RadikoClient()
player = Player()

_stations = []
_init_done = threading.Event()


def _init():
    global _stations
    print("[app] エリア検出中...")
    radiko.detect_area()           # ← authenticate() から変更
    _stations = radiko.get_stations()
    print(f"[app] 局数: {len(_stations)}")
    _init_done.set()


# ---------------------------------------------------------------
# ページ
# ---------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------
# API: 局一覧
# ---------------------------------------------------------------
@app.route("/api/stations")
def api_stations():
    _init_done.wait(timeout=15)
    return jsonify(_stations)


@app.route("/api/station_info/<station_id>")
def api_station_info(station_id):
    """局クリック時: 現在番組 + 今日のスケジュール一括取得"""
    return jsonify(radiko.get_schedule(station_id))


# ---------------------------------------------------------------
# API: 再生
# ---------------------------------------------------------------
@app.route("/api/play", methods=["POST"])
def api_play():
    data       = request.get_json(force=True)
    station_id = data.get("station_id", "")
    mode       = data.get("mode", "live")

    station = next((s for s in _stations if s["id"] == station_id), None)
    if not station:
        return jsonify({"error": "station not found"}), 404

    if mode == "live":
        radiko_url = f"https://radiko.jp/#!/live/{station_id}"
        program    = radiko.get_nowplaying(station_id)
        ok = player.play(radiko_url, station, "live", program)
    else:
        ft = data.get("ft", "")
        # タイムフリー: #!/ts/局ID/開始時刻(YYYYMMDDHHmmSS)
        radiko_url   = f"https://radiko.jp/#!/ts/{station_id}/{ft}"
        program_info = {"title": data.get("program_title",""), "pfm": data.get("pfm","")}
        ok = player.play(radiko_url, station, "timefree", program_info)

    if ok:
        return jsonify({"status": "playing", **player.get_status()})
    else:
        return jsonify({"error": "mpv の起動に失敗しました"}), 500


# ---------------------------------------------------------------
# API: 停止
# ---------------------------------------------------------------
@app.route("/api/stop", methods=["POST"])
def api_stop():
    player.stop()
    return jsonify({"status": "stopped"})


# ---------------------------------------------------------------
# API: 音量
# ---------------------------------------------------------------
@app.route("/api/volume", methods=["POST"])
def api_volume():
    vol = request.get_json(force=True).get("volume", 80)
    return jsonify({"volume": player.set_volume(vol)})


# ---------------------------------------------------------------
# API: 状態
# ---------------------------------------------------------------
@app.route("/api/status")
def api_status():
    status = player.get_status()
    # ライブ再生中は番組情報を更新
    if status["is_playing"] and status["mode"] == "live" and status.get("station"):
        try:
            status["program"] = radiko.get_nowplaying(status["station"]["id"])
        except Exception:
            pass
    return jsonify(status)


# ---------------------------------------------------------------
# API: タイムフリー番組一覧
# ---------------------------------------------------------------
@app.route("/api/programs/<station_id>")
def api_programs(station_id):
    date     = request.args.get("date", None)
    programs = radiko.get_programs(station_id, date)
    return jsonify(programs)


# ---------------------------------------------------------------
# エントリポイント
# ---------------------------------------------------------------
if __name__ == "__main__":
    t = threading.Thread(target=_init, daemon=True)
    t.start()
    # threaded=True にすると Pi 1B でも複数リクエストを捌ける
    app.run(host="0.0.0.0", port=5000, threaded=True, debug=False)
