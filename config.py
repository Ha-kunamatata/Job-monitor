# -*- coding: utf-8 -*-
"""
채용 공고 모니터링 설정
- 여기서 감시할 회사, 키워드, 조건을 관리합니다.
- 회사 채용 페이지 구조가 바뀌면 SITES 항목을 수정하세요.
"""

# ─────────────────────────────────────────────────────────
# 1. 관심 직무 키워드 (공고 제목/내용에 이 단어가 있으면 "관심 공고"로 필터)
# ─────────────────────────────────────────────────────────
KEYWORDS = [
    "데이터센터", "데이터 센터", "IDC", "AIDC",
    "시설관리", "시설 운영", "설비",
    "전기", "기계", "공조", "냉동", "항온항습",
    "MEP", "인프라", "FM", "기전",
    "DCO", "DCEO", "Data Center", "Facility",
]

# 제외 키워드 (이 단어가 제목에 있으면 거름 - 반도체 설계직 등 방향이 다른 것)
EXCLUDE_KEYWORDS = [
    "반도체 설계", "소자", "양산기술", "웨이퍼",
    "영업", "세일즈", "마케팅", "회계", "세무",
]

# ─────────────────────────────────────────────────────────
# 2. 신입 지원 가능 여부 판단 키워드
# ─────────────────────────────────────────────────────────
NEWCOMER_KEYWORDS = ["신입", "학력무관", "인턴", "trainee", "re-start", "career", "초대졸", "무관"]

# ─────────────────────────────────────────────────────────
# 3. 감시 대상 사이트
#    - type: "list_page" (채용 목록 페이지를 긁음)
#    - 각 사이트는 크롤링 방식이 조금씩 달라서 parser에서 개별 처리
# ─────────────────────────────────────────────────────────
SITES = [
    {
        "name": "LG유플러스",
        "url": "https://careers.lg.com/channel/detail/lgu/job_openings",
        "priority": 2,  # 주로 경력
        "note": "AIDC 전기/기계 엔지니어 - 정기 재공고",
    },
    {
        "name": "에스원",
        "url": "https://www.jobkorea.co.kr/Company/1892636/Recruit",
        "priority": 1,  # 신입 FM 채용
        "note": "4급 시설관리(FM) 기계/전기 신입",
    },
    {
        "name": "SK커리어스",
        "url": "https://www.skcareers.com/Recruit",
        "priority": 2,
        "note": "SK C&C 데이터센터 MEP / 기계공조",
    },
    {
        "name": "네이버클라우드",
        "url": "https://recruit.navercloudcorp.com/rcrt/list.do",
        "priority": 1,
        "note": "데이터센터 각 - 건축/전기/기계/소방/안전",
    },
    {
        "name": "삼성SDS",
        "url": "https://www.samsungsds.com/kr/careers/recruitment.html",
        "priority": 2,
        "note": "데이터센터 구축/운영 (경력 위주)",
    },
]

# ─────────────────────────────────────────────────────────
# 4. 마감 임박 기준 (며칠 이내면 알림)
# ─────────────────────────────────────────────────────────
DEADLINE_ALERT_DAYS = 5

# ─────────────────────────────────────────────────────────
# 5. 이메일 설정 (실제 값은 GitHub Secrets/환경변수로 주입)
# ─────────────────────────────────────────────────────────
import os

EMAIL_FROM = os.environ.get("EMAIL_FROM", "")        # 보내는 Gmail 주소
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "") # Gmail 앱 비밀번호
EMAIL_TO = os.environ.get("EMAIL_TO", "")            # 받을 주소 (본인)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
