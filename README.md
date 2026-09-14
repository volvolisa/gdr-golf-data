# gdr-golf-data

골프존 GDR(Golfzon Practice) 연습 데이터를 개인 계정으로 내려받아 SQLite에 저장하고,
날짜별·클럽별 샷 일관성(구질, 스매쉬팩터, 발사각/스핀 적정 범위 진입률 등)을 분석하는 개인용 스크립트입니다.

> **비공식 도구입니다.** 골프존(Golfzon)과 관련이 없으며, 공개 API 문서가 아닌 웹앱 네트워크 요청을 참고해 만들었습니다.
> 본인 계정의 데이터를 개인적으로 백업/분석하는 용도로만 사용하세요. 토큰 유효 기간, 요청 형식 등은
> 예고 없이 바뀔 수 있고, 과도한 요청은 계정 정지 등의 사유가 될 수 있습니다.

## 하는 일

- `python gdr_sync.py sync` — 본인 GDR 세션 목록과 샷 JSON을 받아 `gdr.db`(SQLite)에 저장하고 원본 JSON을 `raw/`에 보관
- `python gdr_sync.py report [YYYY-MM-DD]` — 날짜/클럽별 통계(캐리 거리·편차, 페이스/패스 각도, 스매쉬팩터,
  발사각·백스핀이 적정 범위에 들어간 비율 등)를 콘솔에 출력하고 `report.csv`로 저장
  
## 출력 예시

````
       date     club   n carry_yd carry_sd  best good_pct face_mean face_sd  spin in_window_pct
 2026-09-10    Iron7  10    141.2     11.2   153       60       1.4     3.1  3266            80
 2026-09-10    Iron8  10    129.6     10.2   150       20      -1.3     3.4  4326            60
 2026-09-10   Driver  11    182.5     25.1   209       45      -1.0     8.9  1938            18
````

- `carry_sd` — 캐리 표준편차. 같은 클럽인데 거리가 얼마나 들쭉날쭉한지
- `good_pct` — 그날 최고 캐리의 90% 이상 나온 샷 비율
- `face_sd` / `closed_pct` — 방향 일관성의 실제 원인
- `in_window_pct` — 발사각과 백스핀이 모두 적정 범위에 든 샷 비율

평균 거리만 봐서는 알 수 있는 게 많지 않습니다. 잘 맞은 공 하나가 기억에 남을 뿐입니다.
그래서 편차와 일관성 위주로 지표를 잡았습니다.
````
````

**맨 아래, 라이선스 앞에 넣을 것:**

````markdown
## 만든 이유

10월 대회를 앞두고 연습이 실제로 늘고 있는지 확인하고 싶었습니다.
만드는 과정과 시행착오는 여기에 적었습니다.

- [앱에 갇힌 골프 연습 데이터를 꺼내서 분석하기까지](https://velog.io/@volvolisa/golf-data-1-extract)
````

velog 링크 주소가 맞는지만 확인해주세요. 그리고 출력 예시는 실제 report 결과에서 몇 줄 골라 쓰신 거라 그대로 두셔도 되고, 컬럼이 더 있으면 실제 출력에 맞춰 조정하시면 됩니다.

## 준비물

- Python 3.9+
- `pip install -r requirements.txt`
- 본인 계정으로 로그인한 상태에서 브라우저 DevTools로 확인하는 두 값
  1. **GDR_TOKEN** — Network 탭에서 `progress?size=10` 같은 요청의 Request Headers 중
     `authorization: Bearer eyJ...` 값. `Bearer ` 뒤 토큰만 복사하면 됩니다. **24시간 정도만 유효**합니다.
  2. **GDR_USER_ID** — 같은 요청의 URL 파라미터나 응답 본문에 보이는 본인 회원 번호

이 값들은 모두 **환경변수**로만 넣고 코드나 저장소에는 절대 커밋하지 마세요.

```bash
# macOS/Linux
export GDR_TOKEN='eyJ...'
export GDR_USER_ID='123456'
```

```powershell
# Windows PowerShell
$env:GDR_TOKEN = 'eyJ...'
$env:GDR_USER_ID = '123456'
```

## 사용법

```bash
python gdr_sync.py sync            # 데이터 수집/업데이트
python gdr_sync.py report          # 전체 기간 리포트
python gdr_sync.py report 2026-09-07   # 특정 날짜만
```

`check_speed.py`는 헤드스피드가 평소보다 많이 느린 샷이 섞인 날짜를 찾는 보조 스크립트입니다
(`gdr.db`가 이미 있어야 합니다).

## 데이터 단위

앱 화면과 대조해 확인한 값 기준입니다.

| 항목 | 단위 |
|---|---|
| 거리 (carry, total, apex, ipDistance*) | 미터 x10 → `/10 * 1.0936` = yd |
| 속도 (ballSpeed, headSpeed) | m/s x10 |
| 각도 (launch, face, path, direction) | 도 x10 (face 음수 = 닫힘) |

클럽 코드는 `gdr_sync.py`의 `CLUB` 딕셔너리에 확인된 만큼만 채워져 있습니다.
새로운 코드를 쓰는 클럽(우드, 웨지 등)은 데이터가 쌓이면 앱 화면과 대조해서 추가하면 됩니다.

## 저장소에 포함되지 않는 것

`.gitignore`에 의해 아래 항목은 커밋되지 않습니다. 실제로 수집한 개인 연습 데이터이기 때문입니다.

- `gdr.db` (수집된 세션/샷 데이터)
- `raw/` (세션별 원본 응답 JSON)
- `report.csv` / 기타 `*.csv`

## 라이선스

MIT
