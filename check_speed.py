import sqlite3, statistics as st
con = sqlite3.connect("gdr.db")
rows = con.execute("""
  SELECT substr(s.session_date,1,10) d, sh.club_code, sh.head_speed
  FROM shots sh JOIN sessions s USING(source_id)
  WHERE sh.head_speed > 0 AND sh.ball_path_sub != 11
""").fetchall()

g = {}
for d, c, hs in rows:
    g.setdefault((d, c), []).append(hs / 10)

print(f"{'date':10}{'club':9}{'n':>4}{'min':>7}{'p10':>7}{'median':>8}{'max':>7}{'slow<70%':>10}")
for (d, c), v in sorted(g.items()):
    if len(v) < 5: continue
    v = sorted(v); med = st.median(v)
    slow = sum(1 for x in v if x < med * 0.7)
    if slow:                      # 느린 샷이 섞인 날만 출력
        print(f"{d:10}club_{c:<4}{len(v):>4}{v[0]:>7.1f}{v[len(v)//10]:>7.1f}{med:>8.1f}{v[-1]:>7.1f}{slow:>10}")