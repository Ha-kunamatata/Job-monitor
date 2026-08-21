# -*- coding: utf-8 -*-
"""
Claude API 기반 공고 분석기
- 공고 제목/내용을 Claude에게 보내 사용자 맞춤 준비사항을 받아옵니다.
- 사용자 프로필을 시스템 프롬프트에 고정.
- API 키가 없거나 호출 실패 시 규칙기반(analyzer.py)으로 자동 폴백.

필요: ANTHROPIC_API_KEY 환경변수, requests 패키지
"""

import os
import json
import urllib.request
import urllib.error

# 규칙기반 폴백
from analyzer import analyze as rule_analyze, format_analysis as rule_format

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-opus-4-8"

# 사용자 프로필 - 분석의 기준점
USER_PROFILE = """
[지원자 프로필]
- 현재 카카오 데이터센터에서 서버 엔지니어(운영)로 근무 중
- 주 업무: 서버 물리장애 처리, 서버 운영
- 학력: 4년제 대졸 (전공 무관 - 전기기사 응시 자격 있음)
- 자격증: 없음. 전기 지식 없음 (이제 공부 시작 단계)
- 목표: 데이터센터 시설/인프라 엔지니어(전기·기계·공조) 또는 대형빌딩 시설관리로 전환
- 강점: 데이터센터 환경 이해, 24/7 무중단 운영 문화 경험, 물리장애 대응 경험
- 약점: 전력/기계 설비를 직접 운전·정비한 경험은 아직 없음
"""

SYSTEM_PROMPT = f"""당신은 커리어 전환을 돕는 채용 공고 분석 전문가입니다.
아래 지원자 프로필을 기준으로, 주어진 채용 공고를 분석해 실질적인 조언을 제공합니다.

{USER_PROFILE}

각 공고에 대해 다음을 간결하게 분석하세요:
1. 지원 가능성: 이 지원자가 지금 지원 가능한지 (신입/전환 가능 여부, 경력 요건)
2. 필요/우대 자격증: 공고에서 요구하거나 우대하는 자격증
3. 강점 어필 포인트: 이 지원자의 어떤 경험을 이 공고에 연결할 수 있는지
4. 준비사항: 지금 당장 준비할 것과 중기적으로 준비할 것 (구체적으로)
5. 종합 판단: 지원 우선순위 (지금 바로 / 자격증 취득 후 / 경력 더 쌓은 후)

한국어로, 실용적이고 솔직하게. 과장 없이. 각 항목 2-3줄 이내로."""


def _call_claude(title: str, content: str) -> str:
    """Claude API 호출. 실패 시 None 반환."""
    if not ANTHROPIC_API_KEY:
        return None

    user_message = f"""다음 채용 공고를 분석해주세요.

[공고 제목]
{title}

[공고 내용/메모]
{content or "(상세 내용 없음 - 제목 기준으로 분석)"}"""

    payload = {
        "model": MODEL,
        "max_tokens": 1024,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_message}],
    }

    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        # content 블록에서 텍스트만 추출
        texts = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
        return "\n".join(texts).strip()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"    [!] Claude API 오류 {e.code}: {body[:200]}")
        return None
    except Exception as e:
        print(f"    [!] Claude API 호출 실패: {e}")
        return None


def analyze_job(title: str, content: str = "") -> str:
    """
    공고 분석. Claude API 우선, 실패 시 규칙기반 폴백.
    반환: 사람이 읽는 분석 텍스트.
    """
    ai_result = _call_claude(title, content)
    if ai_result:
        return ai_result
    # 폴백
    print("    (규칙기반 분석으로 폴백)")
    rule_result = rule_analyze(title, content)
    return rule_format(rule_result)


if __name__ == "__main__":
    print("=== Claude 분석기 테스트 ===")
    if not ANTHROPIC_API_KEY:
        print("[!] ANTHROPIC_API_KEY 없음 → 규칙기반 폴백으로 테스트")
    title = "[Enterprise부문] AIDC 전기/기계 엔지니어 경력채용"
    content = "AI 데이터센터 전력 및 기계 설비 운영. 전기기사 우대. 대졸 이상 경력직."
    print(analyze_job(title, content))
