"""
player.py - yt-dlp-radiko + mplayer による再生制御
yt-dlp が radiko 認証・HLS取得を担い、mplayer が再生する
"""

import subprocess
import os
import time
import threading

FIFO_PATH = "/tmp/pi-radio-mplayer.fifo"


class Player:
    def __init__(self):
        self._yt_proc     = None
        self._mpv_proc    = None
        self._lock        = threading.Lock()
        self._volume      = 80
        self.is_playing   = False
        self.current_station = None
        self.current_mode    = None
        self.current_program = {}

    # ── 再生 ──────────────────────────────────────
    def play(self, radiko_url: str,
             station_info: dict = None,
             mode: str = "live",
             program_info: dict = None) -> bool:
        """
        radiko_url:
          live     → "https://radiko.jp/#!/live/TBS"
          timefree → "https://radiko.jp/#!/ts/TBS/20240501120000"
        """
        with self._lock:
            self._kill_all()
            self._ensure_fifo()


            try:
                # yt-dlp: 認証 & 実ストリーム取得
                self._yt_proc = subprocess.Popen(
                    [
                        "yt-dlp",
                        "--no-playlist",
                        "--quiet",
                        "-o", "-",
                        radiko_url,
                    ],
                    stdout=subprocess.PIPE,
                )            
                

                # mpv: yt-dlp から受け取った出力を再生
                self._mpv_proc = subprocess.Popen(
                    [
                        "mpv",
                        "--no-video",
                        f"--volume={self._volume}",
                        "-",
                    ],
                    stdin=self._yt_proc.stdout,                   
                    
                )

                self.is_playing      = True
                self.current_station = station_info or {}
                self.current_mode    = mode
                self.current_program = program_info or {}
                return True

            except FileNotFoundError as e:
                missing = "yt-dlp" if "yt-dlp" in str(e) else "mpv"
                print(f"[player] {missing} が見つかりません")
                self._kill_all()
                return False

    def stop(self):
        with self._lock:
            self._kill_all()
            self.is_playing      = False
            self.current_station = None
            self.current_mode    = None
            self.current_program = {}

    # ── 音量（mplayer slave コマンド）────────────
    def set_volume(self, vol: int) -> int:
        self._volume = max(0, min(100, int(vol)))
        self._fifo_cmd(f"volume {self._volume} 1")
        return self._volume

    def get_volume(self) -> int:
        return self._volume

    # ── 状態 ──────────────────────────────────────
    def is_alive(self) -> bool:
        # mpv が生きているかどうかで判断
        return self._mpv_proc is not None and self._mpv_proc.poll() is None

    def get_status(self) -> dict:
        if self.is_playing and not self.is_alive():
            self.is_playing = False
        return {
            "is_playing":  self.is_playing,
            "volume":      self._volume,
            "station":     self.current_station,
            "mode":        self.current_mode,
            "program":     self.current_program,
        }

    # ── 内部ヘルパー ──────────────────────────────
    def _fifo_cmd(self, cmd: str):
        """mplayer slave モードにコマンドを送る"""
        if os.path.exists(FIFO_PATH):
            try:
                # ノンブロッキング書き込み
                fd = os.open(FIFO_PATH, os.O_WRONLY | os.O_NONBLOCK)
                os.write(fd, (cmd + "\n").encode())
                os.close(fd)
            except OSError:
                pass

    def _ensure_fifo(self):
        if os.path.exists(FIFO_PATH):
            os.remove(FIFO_PATH)
        os.mkfifo(FIFO_PATH)

    def _kill_all(self):
        for proc in (self._mpv_proc, self._yt_proc):
            if proc:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
        self._mpv_proc = None
        self._yt_proc = None
        if os.path.exists(FIFO_PATH):
            try:
                os.remove(FIFO_PATH)
            except OSError:
                pass