#!/usr/bin/env python3
"""
gdr_sync.py — 골프존 GDR 연습 데이터 수집 + 클럽별 일관성 분석

사용법
  1) DevTools > Network > progress?size=10 요청 > Request Headers 에서
     Cookie 값(또는 Authorization 값)을 복사해서 환경변수로 넣는다.
       export GDR_TOKEN='eyJ...'          # authorization 헤더의 Bearer 뒤 토큰 (24시간 유효)
       export GDR_USER_ID='123456'        # 같은 요청 URL/응답에 보이는 본인 회원 번호
  2) python gdr_sync.py sync      # 세션 목록 + 샷 JSON 받아서 gdr.db 에 저장
     python gdr_sync.py report    # 날짜별/클럽별 통계 출력 + report.csv
     python gdr_sync.py report 2026-09-07   # 특정 날짜만

단위 (앱 화면과 대조해서 확인한 값)
  - 거리(carry, total, apex, ipDistance*)  : 미터 x10   -> /10 * 1.0936 = yd
  - 속도(ballSpeed, headSpeed)              : m/s x10
  - 각도(launch, face, path, direction)     : 도 x10     (face 음수 = 닫힘)
"""
import csv
import json
import os
import sqlite3
import statistics as st
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

USER_ID = os.getenv("GDR_USER_ID")
API = "https://gdrapi.golfzon.com/api/v1/progress"
SHOT_URL = "https://image.global.golfzon.com/global/ca/upload/progress/shots/gdr_{y}_{m:02d}_{uid}_{sid}.json"
DB = Path("gdr.db")
RAW = Path("raw")           # 원본 JSON 보관
YD = 0.10936                # dm -> yd

CLUB = {"1": "Driver", "26": "Utility4",
        "12": "Iron5", "13": "Iron6", "14": "Iron7", "15": "Iron8", "16": "Iron9"}
# 다른 코드(우드/웨지 등)는 데이터 쌓이면 앱 화면과 대조해서 채워 넣기


def headers():
    h = {"Origin": "https://www.global.golfzon.com",
         "Referer": "https://www.global.golfzon.com/progress",
         "User-Agent": "Mozilla/5.0"}
    if os.getenv("GDR_COOKIE"):
        h["Cookie"] = os.environ["GDR_COOKIE"]
    if os.getenv("GDR_TOKEN"):                 # DevTools의 authorization 값에서 'Bearer ' 뒤 부분만
        tok = os.environ["GDR_TOKEN"].removeprefix("Bearer ").strip()
        h["Authorization"] = f"Bearer {tok}"
        h["gz_session_id"] = tok
    return h


def db():
    con = sqlite3.connect(DB)
    con.executescript("""
    CREATE TABLE IF NOT EXISTS sessions(
        source_id TEXT PRIMARY KEY, session_date TEXT, total_shots INT,
        most_club TEXT, status TEXT, downloaded INT DEFAULT 0);
    CREATE TABLE IF NOT EXISTS shots(
        source_id TEXT, shot_no INT, club_code TEXT, shot_type INT,
        ball_speed INT, head_speed INT, launch_angle INT, face_angle INT,
        club_path INT, carry INT, total INT, apex INT, back_spin INT, side_spin INT,
        ip_out INT, ip_tb INT, direction_angle INT, ball_path_code INT,
        ball_path_sub INT, raw TEXT,
        PRIMARY KEY(source_id, shot_no));
    """)
    return con


# ---------------------------------------------------------------- sync
def fetch_sessions():
    cursor, out = None, []
    while True:
        p = {"size": 50}
        if cursor:
            p["cursor"] = cursor
        r = requests.get(API, params=p, headers=headers(), timeout=20)
        if r.status_code != 200:
            sys.exit(f"세션 목록 실패 {r.status_code}: {r.text[:300]}")
        body = r.json()["data"]
        rows = body["data"]
        out += rows
        if not body.get("hasMore") or not rows:
            break
        cursor = rows[-1]["sourceId"]
        time.sleep(0.5)                      # 서버 예의
    return out


def fetch_shots(sess):
    d = datetime.fromisoformat(sess["sessionDate"])
    url = SHOT_URL.format(y=d.year, m=d.month, uid=USER_ID, sid=sess["sourceId"])
    r = requests.get(url, headers=headers(), timeout=30)
    if r.status_code == 404 and d.day <= 2:  # 월초 세션은 전월 파일에 있을 수 있음
        m = d.month - 1 or 12
        y = d.year - (1 if d.month == 1 else 0)
        r = requests.get(SHOT_URL.format(y=y, m=m, uid=USER_ID, sid=sess["sourceId"]),
                         headers=headers(), timeout=30)
    r.raise_for_status()
    return r.json()


def sync():
    if not os.getenv("GDR_TOKEN"):
        sys.exit("GDR_TOKEN 환경변수가 없습니다. cmd: set GDR_TOKEN=eyJ...  /  PowerShell: $env:GDR_TOKEN='eyJ...'")
    if not USER_ID:
        sys.exit("GDR_USER_ID 환경변수가 없습니다. cmd: set GDR_USER_ID=123456  /  PowerShell: $env:GDR_USER_ID='123456'")
    con = db()
    RAW.mkdir(exist_ok=True)
    sessions = fetch_sessions()
    print(f"세션 {len(sessions)}개 확인")
    for s in sessions:
        con.execute("INSERT OR IGNORE INTO sessions VALUES(?,?,?,?,?,0)",
                    (s["sourceId"], s["sessionDate"], s["totalShots"],
                     s["mostClub"], s["processingStatus"]))
    con.commit()
    todo = con.execute("SELECT source_id, session_date, total_shots FROM sessions "
                       "WHERE downloaded=0 AND status='done' ORDER BY session_date").fetchall()
    for sid, sdate, n in todo:
        try:
            data = fetch_shots({"sourceId": sid, "sessionDate": sdate})
        except Exception as e:
            print(f"  {sid} ({sdate[:10]}) 실패: {e}")
            continue
        (RAW / f"{sid}.json").write_text(json.dumps(data, ensure_ascii=False))
        for x in data["shots"]:
            con.execute("INSERT OR REPLACE INTO shots VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (sid, x["shotNo"], x["clubCode"], x["shotType"],
                         x["ballSpeed"], x["headSpeed"], x["launchAngle"], x["faceAngle"],
                         x["clubPath"], x["carry"], x["total"], x["apex"], x["backSpin"],
                         x["sideSpin"], x["ipDistanceOut"], x["ipDistanceTb"],
                         x["directionAngle"], x["ballPathCode"], x["ballPathSubCode"],
                         json.dumps(x)))
        con.execute("UPDATE sessions SET downloaded=1 WHERE source_id=?", (sid,))
        con.commit()
        print(f"  {sid} {sdate[:10]} {n:>4}샷 저장")
        time.sleep(0.5)
    print("완료")


# ---------------------------------------------------------------- report
# 클럽별 이상적인 발사 조건 (발사각 deg, 백스핀 rpm)
WINDOW = {"Driver": ((12, 18), (1800, 3000)), "Utility4": ((14, 20), (2500, 4500))}
IRON_W = ((15, 24), (3000, 6500))          # 아이언 공통 기준


def window(club):
    return WINDOW.get(club, IRON_W)


def report(day=None):
    con = db()
    q = """SELECT substr(s.session_date,1,10) d, sh.club_code, sh.carry, sh.face_angle,
                  sh.club_path, sh.ip_out, sh.ball_path_sub, sh.launch_angle,
                  sh.back_spin, sh.ball_speed, sh.head_speed
           FROM shots sh JOIN sessions s USING(source_id)"""
    if day:
        q += f" WHERE substr(s.session_date,1,10)='{day}'"
    groups = {}
    for d, c, carry, fa, cp, out, sub, la, spin, bs, hs in con.execute(q):
        if sub == 11 or carry < 100:          # 탑볼/헛스윙 제외 (10m 미만)
            continue
        smash = bs / hs if hs else 0
        groups.setdefault((d, c), []).append(
            (carry * YD, fa / 10, cp / 10, out * YD, la / 10, spin, smash))

    cols = ["date", "club", "n", "carry_yd", "carry_sd", "best", "good_pct",
            "face_mean", "face_sd", "path_mean", "closed_pct",
            "launch", "spin", "smash", "in_window_pct"]
    out_rows = []
    for (d, c), v in sorted(groups.items()):
        if len(v) < 3:
            continue
        name = CLUB.get(c, f"club_{c}")
        (lo, hi), (slo, shi) = window(name)
        car, fa, cp, lr, la, sp, sm = zip(*v)
        best = max(car)
        inwin = sum(lo <= a <= hi and slo <= s2 <= shi for a, s2 in zip(la, sp))
        out_rows.append([d, name, len(v),
                         round(st.mean(car), 1), round(st.pstdev(car), 1), round(best),
                         round(sum(x >= best * .9 for x in car) / len(car) * 100),
                         round(st.mean(fa), 1), round(st.pstdev(fa), 1),
                         round(st.mean(cp), 1),
                         round(sum(x <= -5 for x in fa) / len(fa) * 100),
                         round(st.mean(la), 1), round(st.mean(sp)),
                         round(st.mean(sm), 3),
                         round(inwin / len(v) * 100)])
    w = [11, 9, 4, 9, 9, 6, 9, 10, 8, 10, 11, 7, 6, 7, 14]
    print("".join(f"{h:>{n}}" for h, n in zip(cols, w)))
    for r in out_rows:
        print("".join(f"{str(x):>{n}}" for x, n in zip(r, w)))
    with open("report.csv", "w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerows([cols] + out_rows)
    print("\nreport.csv 저장")
    print("in_window_pct = 발사각·백스핀이 모두 이상 범위에 든 샷 비율 (핵심 지표)")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    if cmd == "sync":
        sync()
    else:
        report(sys.argv[2] if len(sys.argv) > 2 else None)