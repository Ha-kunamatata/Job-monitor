# 채용 공고 자동 모니터링 봇

카카오 데이터센터 서버 운영 → 데이터센터 시설/인프라 엔지니어 전환을 위한
채용 공고 자동 감시 도구.

GitHub Actions가 하루 2번(오전 9시·오후 6시, 한국시간) 자동으로:
1. 대기업 채용 페이지들을 브라우저로 긁고
2. 데이터센터·시설·전기·기계 관련 공고를 필터링하고
3. 새 공고/마감 임박을 감지하고
4. Claude API로 "당신이 준비해야 할 것"을 분석해서
5. 이메일로 보내줍니다.

---

## 무엇이 되고 무엇이 안 되는가 (먼저 읽으세요)

**됩니다**
- PC를 꺼둬도 GitHub 서버가 자동 실행 (무료)
- 새 공고가 뜨면 이메일 알림
- 마감 5일 이내 공고 알림
- 공고별 맞춤 준비사항 분석 (당신 프로필 기준)

**한계**
- "실시간 즉시"는 아님. 하루 2번 확인 (원하면 주기 조정 가능)
- 채용 사이트가 구조를 바꾸면 해당 사이트 수집이 실패할 수 있음
  → 이럴 땐 config.py의 해당 사이트 URL/설정만 손보면 됨
- 일부 사이트는 강한 봇 차단이 있어 간헐적으로 실패 가능
  → 실패해도 나머지 사이트는 정상 동작 (독립 처리)

---

## 설치 순서

### 1단계: GitHub 저장소 만들기
1. GitHub에서 새 저장소(private 권장) 생성
2. 이 폴더의 모든 파일을 업로드 (또는 git push)

### 2단계: Gmail 앱 비밀번호 발급 (이메일 발송용)
1. Gmail → Google 계정 → 보안 → 2단계 인증 켜기
2. "앱 비밀번호" 검색 → 새 앱 비밀번호 생성 (16자리)
3. 이 16자리를 EMAIL_PASSWORD로 사용 (일반 Gmail 비번 아님!)

### 3단계: Claude API 키 발급 (공고 분석용)
1. https://console.anthropic.com 접속 → 가입/로그인
2. API Keys → 새 키 생성
3. 소액 크레딧 충전 (공고 분석은 건당 비용이 매우 적음. 월 몇백 원 수준)

### 4단계: GitHub Secrets 등록 (키를 안전하게 저장)
저장소 → Settings → Secrets and variables → Actions → New repository secret
아래 4개를 각각 등록:

| 이름 | 값 |
|------|-----|
| `EMAIL_FROM` | 보내는 Gmail 주소 (예: myid@gmail.com) |
| `EMAIL_PASSWORD` | 2단계에서 만든 16자리 앱 비밀번호 |
| `EMAIL_TO` | 알림 받을 이메일 (본인 주소) |
| `ANTHROPIC_API_KEY` | 3단계에서 만든 Claude API 키 |

### 5단계: 작동 확인
- 저장소 → Actions 탭 → "채용 공고 모니터링" → Run workflow (수동 실행)
- 몇 분 후 이메일이 오는지 확인
- 처음 실행은 모든 공고가 "새 공고"로 잡혀 한 번에 옴 (정상)

### (선택) 스크래퍼만 먼저 점검하기 — 이메일/키 없이
각 채용 사이트가 실제로 공고를 긁어오는지만 빠르게 확인하고 싶다면:
- 저장소 → Actions 탭 → **"스크래퍼 점검 (수집만)"** → Run workflow
- Secrets(이메일/API 키) 없이 동작하며, 로그에 **사이트별 수집 건수**가 표로 나옵니다.
- 로그 해석:
  - `원시 후보 N개`인데 관심 공고 0건 → 지금 그 사이트에 관심 키워드에 맞는 공고가 없는 것(정상)
  - `원시 후보 0개` 또는 `로드 실패/타임아웃` → 사이트 구조 변경/차단 → 해당 사이트 손봐야 함
- 로컬에서도 동일: `python scrape_test.py`

---

## 감시 대상 조정하기 (config.py)

- **회사 추가/삭제**: `SITES` 리스트 수정
- **관심 키워드**: `KEYWORDS` 수정 (예: "수배전" 추가)
- **제외 키워드**: `EXCLUDE_KEYWORDS` 수정
- **마감 임박 기준**: `DEADLINE_ALERT_DAYS` (기본 5일)

## 실행 주기 조정하기 (.github/workflows/monitor.yml)
`cron` 부분 수정. 예를 들어 하루 3번으로 늘리려면 cron 줄을 하나 더 추가.
(UTC 기준이니 한국시간 -9시간으로 계산)

## 내 프로필 수정하기 (analyzer_ai.py)
`USER_PROFILE` 부분을 고치면 분석 기준이 바뀝니다.
자격증을 따거나 경력이 쌓이면 여기를 업데이트하세요.

---

## 로컬에서 테스트하려면
```bash
pip install -r requirements.txt
playwright install chromium

# 환경변수 설정 (임시)
export EMAIL_FROM="myid@gmail.com"
export EMAIL_PASSWORD="앱비밀번호16자리"
export EMAIL_TO="myid@gmail.com"
export ANTHROPIC_API_KEY="sk-ant-..."

python main.py
```

---

## 파일 구조
```
job-monitor/
├── config.py              # 감시 대상 회사·키워드·설정
├── main.py                # 메인 실행부
├── analyzer.py            # 규칙기반 분석 (폴백용)
├── analyzer_ai.py         # Claude API 분석 (메인)
├── state.py               # 본 공고 기록 (새 공고 판별)
├── notify.py              # 이메일 발송
├── scrape_test.py         # 스크래퍼 단독 점검 (수집만, 키 불필요)
├── scrapers/
│   ├── fetch.py           # 단순 HTTP 수집 (가벼움, 폴백)
│   └── fetch_browser.py   # Playwright 브라우저 수집 (메인)
├── tests/
│   ├── fixtures/          # 추출 로직 검증용 샘플 HTML
│   └── test_extraction.py # 추출 엔진 테스트 (네트워크 불필요)
├── data/
│   └── seen_jobs.json     # 본 공고 저장소 (자동 갱신)
├── requirements.txt
└── .github/workflows/
    ├── monitor.yml        # GitHub Actions 자동 실행 설정
    └── scrape-test.yml    # 스크래퍼 점검(수집만) 수동 실행용
```

## 스크래퍼 동작 방식 (구조가 바뀌어도 잘 버티도록)
채용 사이트 대부분이 React/Vue 기반이라 공고 제목이 `<a>` 링크 텍스트가 아니라
`<div>`/`<li>` 카드 안에 들어있고, 링크는 "지원하기" 같은 별도 버튼입니다.
그래서 이 도구는:
- 링크 텍스트만 보지 않고 **공고 카드(리스트 항목) 단위**로 제목을 읽고, 카드 안/주변의 링크를 자동 연결
- `networkidle`(국내 대기업 사이트에서 거의 항상 타임아웃) 대신 **domcontentloaded + 스크롤 대기**로 지연 로딩 유발
- `iframe` 안에 임베드된 공고 목록도 탐색
- 메뉴/푸터 링크(로그인·약관 등)와 무관 직무(영업·회계 등)는 필터링

`python tests/test_extraction.py` 로 추출 로직을 오프라인 검증할 수 있습니다.
