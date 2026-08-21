# -*- coding: utf-8 -*-
"""
스크래퍼 단독 점검 (이메일/AI 없이 수집만).

각 채용 사이트가 실제로 공고를 긁어오는지 확인하는 용도.
- 로컬:  python scrape_test.py
- CI:    .github/workflows/scrape-test.yml 에서 수동 실행(Run workflow)
         → 로그에서 사이트별 수집 건수를 확인

Secrets(이메일/API 키)가 전혀 필요 없습니다.
"""

import sys
from config import SITES
from scrapers.fetch_browser import fetch_all_browser


def main():
    print("=== 스크래퍼 단독 점검 (수집만) ===\n")
    all_jobs = fetch_all_browser(SITES)

    # 사이트별 집계
    counts = {s["name"]: 0 for s in SITES}
    for j in all_jobs:
        counts[j["company"]] = counts.get(j["company"], 0) + 1

    print("\n" + "=" * 52)
    print(" 사이트별 수집 결과")
    print("=" * 52)
    for s in SITES:
        n = counts.get(s["name"], 0)
        mark = "✓" if n > 0 else "·"
        print(f"  {mark} {s['name']:<16} {n:>3} 건")
    print("=" * 52)
    print(f"  합계 {len(all_jobs)} 건\n")

    # 샘플 출력
    if all_jobs:
        print("수집 샘플 (최대 25건):")
        for j in all_jobs[:25]:
            print(f"  [{j['company']}] {j['title'][:60]}")
            print(f"      {j['href']}")

    # 0건인 사이트 안내 (반드시 '고장'은 아님 - 현재 관심 공고가 없을 수도 있음)
    zero = [s["name"] for s in SITES if counts.get(s["name"], 0) == 0]
    if zero:
        print("\n[참고] 수집 0건 사이트:", ", ".join(zero))
        print("  - 위 로그에서 '원시 후보 0개' 또는 '로드 실패/타임아웃'이면 → 사이트 구조/차단 문제")
        print("  - '원시 후보 N개'인데 0건이면 → 현재 관심 키워드에 맞는 공고가 없는 것(정상)")

    # 점검 목적이므로 항상 0으로 종료 (로그 확인용)
    return 0


if __name__ == "__main__":
    sys.exit(main())
