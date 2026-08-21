# -*- coding: utf-8 -*-
"""
공고 분석기
- 공고 제목/내용을 보고 (1) 신입 가능 여부 (2) 필요 자격증
  (3) 사용자가 준비해야 할 것을 자동 매칭합니다.
- 사용자 프로필: 카카오 데이터센터 서버 운영 경력, 4년제 대졸, 전기 지식 없음
"""

import re
from config import NEWCOMER_KEYWORDS

# 자격증/역량 키워드 → 사용자 관점 조언 매핑
CERT_HINTS = {
    "전기기사": "전기기사 필요. 대졸이라 바로 응시 가능하지만 미보유 상태 → 우선 준비 대상.",
    "전기산업기사": "전기산업기사 언급 → 전기기사로 상위 대응 가능.",
    "공조냉동": "공조냉동기계기사 우대. 데이터센터 냉각 핵심 → 전기 다음 2순위 자격.",
    "냉동": "냉동공조 역량 요구 → 공조냉동기계기사가 강점이 됨.",
    "소방": "소방설비기사 우대 가능성 → 초고층/대형시설이면 가점.",
    "산업안전": "산업안전(산업안전기사) 언급 → 안전관리 선임 요건일 수 있음.",
    "에너지관리": "에너지관리기사 우대 → 있으면 플러스, 필수는 드묾.",
    "건축설비": "건축설비기사 우대 → 설비 종합관리 자리.",
}

# 사용자가 이미 가진 강점 (공고에 이게 있으면 '어필 포인트'로 표시)
USER_STRENGTHS = {
    "데이터센터": "★ 강점: 현재 데이터센터 근무 중 → 환경 이해도 직접 어필 가능.",
    "서버": "★ 강점: 서버 물리장애·운영 경험 보유 → 직접 관련.",
    "운영": "★ 강점: 24/7 무중단 운영 문화 경험 → 시설 운영에도 통용.",
    "장애": "★ 강점: 물리장애 처리 경험 → 장애관리 업무에 바로 연결.",
    "이중화": "★ 강점: 이중화/무중단 개념 이해 → 인프라 신뢰성 업무에 유리.",
    "IT": "★ 강점: IT 백그라운드 → IT+시설 융합 자리에 적합.",
}


def is_newcomer_ok(text: str) -> bool:
    """신입/전환자 지원 가능 여부"""
    t = text.lower()
    return any(k.lower() in t for k in NEWCOMER_KEYWORDS)


def extract_deadline(text: str):
    """공고 텍스트에서 마감일(YYYY.MM.DD 또는 MM/DD 등) 추출 시도"""
    # 2026.07.31 / 2026-07-31 형태
    m = re.search(r"(20\d{2})[.\-/](\d{1,2})[.\-/](\d{1,2})", text)
    if m:
        y, mo, d = m.groups()
        return f"{y}.{int(mo):02d}.{int(d):02d}"
    # ~07/31 형태
    m = re.search(r"~\s*(\d{1,2})[/.](\d{1,2})", text)
    if m:
        mo, d = m.groups()
        return f"(연도미상) {int(mo):02d}.{int(d):02d}"
    return None


def analyze(title: str, content: str = "") -> dict:
    """공고 하나를 분석해서 준비사항 딕셔너리 반환"""
    text = f"{title} {content}"

    # 1) 신입 가능 여부
    newcomer = is_newcomer_ok(text)

    # 2) 필요 자격증 매칭
    certs = []
    for key, hint in CERT_HINTS.items():
        if key in text:
            certs.append(hint)

    # 3) 사용자 강점 어필 포인트
    strengths = []
    for key, hint in USER_STRENGTHS.items():
        if key in text:
            strengths.append(hint)

    # 4) 마감일
    deadline = extract_deadline(text)

    # 5) 종합 액션 제안
    actions = []
    if newcomer:
        actions.append("→ 신입/전환 지원 가능. 지금 바로 지원서 준비 가능.")
    else:
        actions.append("→ 경력 대상으로 보임. 현 데이터센터 경력을 '관련 경력'으로 강조 필요.")

    if not certs:
        actions.append("→ 자격증 명시 없음. 기본 이력서 + 데이터센터 경험 강조로 지원 시도.")
    else:
        actions.append("→ 자격증 요구/우대 있음. 전기기사 준비 병행 권장.")

    if not strengths:
        strengths.append("(공고에서 직접 매칭되는 강점 키워드는 적음 - 자소서에서 연결 서술 필요)")

    return {
        "newcomer": newcomer,
        "certs": certs,
        "strengths": strengths,
        "deadline": deadline,
        "actions": actions,
    }


def format_analysis(a: dict) -> str:
    """분석 결과를 사람이 읽는 텍스트로"""
    lines = []
    lines.append("  [지원 가능] " + ("✅ 신입/전환 가능" if a["newcomer"] else "⚠️ 경력 위주"))
    if a["deadline"]:
        lines.append(f"  [마감] {a['deadline']}")
    if a["certs"]:
        lines.append("  [필요/우대 자격]")
        for c in a["certs"]:
            lines.append(f"    · {c}")
    lines.append("  [내 강점 어필 포인트]")
    for s in a["strengths"]:
        lines.append(f"    · {s}")
    lines.append("  [다음 할 일]")
    for act in a["actions"]:
        lines.append(f"    · {act}")
    return "\n".join(lines)


if __name__ == "__main__":
    # 테스트
    sample_title = "[Enterprise부문] AIDC 전기/기계 엔지니어 경력채용"
    sample_content = "AI 데이터센터 전력 및 기계 설비 운영. 전기기사 우대. 대졸 이상 경력직."
    result = analyze(sample_title, sample_content)
    print("=== 분석 테스트 ===")
    print(f"제목: {sample_title}")
    print(format_analysis(result))
