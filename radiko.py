"""
radiko.py - 局一覧・番組表のみ（認証は yt-dlp-radiko に任せる）
"""

import requests
import xml.etree.ElementTree as ET
import re
from datetime import datetime, timedelta


class RadikoClient:
    def __init__(self):
        self.area_id = None
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (X11; Linux armv6l) AppleWebKit/537.36"
        })
        self._stations_cache = []

    # エリア検出（認証不要）
    def detect_area(self) -> str:
        try:
            r = self.session.get("https://radiko.jp/area", timeout=5)
            
            # レスポンス例: document.write('<span class="JP13">TOKYO JAPAN</span>');
            self.area_id = re.search(r'class="([^"]+)"', r.text).group(1)
            print(f"[radiko] エリア検出: {self.area_id}")
            return self.area_id
            
        except Exception as e:
            print(f"[radiko] エリア検出失敗: {e}")
            self.area_id = "JP13"  # 失敗時は東京にフォールバック
            return self.area_id

    def ensure_area(self):
        if not self.area_id:
            self.detect_area()

    # 局一覧（認証不要）
    def get_stations(self) -> list:
        self.ensure_area()
        if self._stations_cache:
            return self._stations_cache
        try:
            r = self.session.get(
                f"https://radiko.jp/v2/station/list/{self.area_id}.xml",
                timeout=10,
            )
            r.raise_for_status()
            root = ET.fromstring(r.content)
            stations = []
            for st in root.findall(".//station"):
                sid  = st.findtext("id", "")
                name = st.findtext("name", "")
                logo = ""
                for w in ("47", "55", "90"):
                    el = st.find(f'.//logo[@width="{w}"]')
                    if el is not None and el.text:
                        logo = el.text.strip()
                        break
                if sid and name:
                    stations.append({"id": sid, "name": name, "logo": logo})
            self._stations_cache = stations
            return stations
        except Exception as e:
            print(f"[radiko] 局一覧取得失敗: {e}")
            return []

    # 現在放送中の番組（認証不要）
    def get_nowplaying(self, station_id: str) -> dict:
        self.ensure_area()
        try:
            r = self.session.get(
                f"https://radiko.jp/v3/program/now/{self.area_id}.xml",
                timeout=5,
            )
            root = ET.fromstring(r.content)
            for st in root.findall(".//station"):
                if st.get("id") == station_id:
                    prog = st.find(".//prog")
                    if prog is not None:
                        return {
                            "title": prog.findtext("title", ""),
                            "pfm":   prog.findtext("pfm",   ""),
                            "ft":    prog.get("ft", ""),
                            "to":    prog.get("to", ""),
                        }
        except Exception as e:
            print(f"[radiko] nowplaying取得失敗: {e}")
        return {"title": "", "pfm": "", "ft": "", "to": ""}

    # タイムフリー番組表（認証不要）
    def get_programs(self, station_id: str, date: str = None) -> list:
        self.ensure_area()
        results = []
        now = datetime.now()
        target_dates = []
        if date:
            try:
                target_dates = [datetime.strptime(date, "%Y%m%d")]
            except ValueError:
                pass
        if not target_dates:
            target_dates = [now - timedelta(days=i) for i in range(7)]

        for d in target_dates:
            date_str = d.strftime("%Y%m%d")
            try:
                r = self.session.get(
                    f"https://radiko.jp/v3/program/station/date/{date_str}/{station_id}.xml",
                    timeout=8,
                )
                if r.status_code != 200:
                    continue
                root = ET.fromstring(r.content)
                for prog in root.findall(".//prog"):
                    ft_str = prog.get("ft", "")
                    to_str = prog.get("to", "")
                    if not ft_str or not to_str:
                        continue
                    try:
                        ft_dt = datetime.strptime(ft_str, "%Y%m%d%H%M%S")
                        to_dt = datetime.strptime(to_str, "%Y%m%d%H%M%S")
                    except ValueError:
                        continue
                    if ft_dt > now or ft_dt < now - timedelta(days=7):
                        continue
                    results.append({
                        "ft":           ft_str,
                        "to":           to_str,
                        "ft_display":   ft_dt.strftime("%H:%M"),
                        "to_display":   to_dt.strftime("%H:%M"),
                        "date_display": ft_dt.strftime("%m/%d"),
                        "title":        prog.findtext("title", ""),
                        "pfm":          prog.findtext("pfm",   ""),
                        "info":         (prog.findtext("info", "") or "")[:80],
                    })
            except Exception as e:
                print(f"[radiko] 番組取得失敗 {date_str}: {e}")

        results.sort(key=lambda x: x["ft"], reverse=True)
        return results