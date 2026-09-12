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
