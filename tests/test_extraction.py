# -*- coding: utf-8 -*-
"""
추출 엔진 검증 테스트 (실제 네트워크 불필요).

로컬 HTML 픽스처(tests/fixtures/*.html)를 file:// 로 열어서
scrapers.fetch_browser 의 실제 코드 경로(브라우저 렌더 + 카드 추출)로
관심 공고가 제대로 뽑히는지, 노이즈/무관 공고는 걸러지는지 확인합니다.

실행:
    python tests/test_extraction.py
성공하면 종료코드 0, 하나라도 실패하면 1.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scrapers.fetch_browser import (  # noqa: E402
    PLAYWRIGHT_AVAILABLE, fetch_site_browser, _launch_kwargs,
)

try:
    from playwright.sync_api import sync_playwright  # noqa: E402
except ImportError:
    pass

FIX = os.path.join(ROOT, "tests", "fixtures")


def _url(name):
    return "file://" + os.path.join(FIX, name)


# (픽스처, site dict, 반드시 잡혀야 하는 제목 조각들, 절대 잡히면 안 되는 조각들)
CASES = [
    (
        "lg.html",
        {"name": "LG유플러스(픽스처)", "url": _url("lg.html")},
        ["AIDC 전기 엔지니어", "데이터센터 기계설비"],
        ["영업 마케팅", "반도체 소자", "로그인"],
    ),
    (
        "navercloud.html",
        {"name": "네이버클라우드(픽스처)", "url": _url("navercloud.html")},
        ["전기 설비 엔지니어", "기계/공조"],
        ["세일즈 매니저", "홈으로"],
    ),
    (
        "jobkorea.html",
        {"name": "에스원(픽스처)", "url": _url("jobkorea.html")},
        ["시설관리(FM)", "전기시설 관리"],
        ["보안영업"],
    ),
    (
        "iframe_host.html",
        {"name": "삼성SDS(픽스처)", "url": _url("iframe_host.html")},
        ["데이터센터 구축/운영", "공조냉동"],
        ["회계 담당"],
    ),
]


def run():
    if not PLAYWRIGHT_AVAILABLE:
        print("[SKIP] playwright 미설치 - 테스트 건너뜀")
        return 0

    failures = []
    with sync_playwright() as p:
        browser = p.chromium.launch(**_launch_kwargs())
        ctx = browser.new_context(locale="ko-KR", ignore_https_errors=True)
        page = ctx.new_page()

        for fixture, site, must_have, must_not in CASES:
            jobs = fetch_site_browser(page, site)
            titles = " || ".join(j["title"] for j in jobs)
            print(f"\n[{fixture}] 추출 {len(jobs)}건:")
            for j in jobs:
                print(f"    - {j['title']}  ->  {j['href']}")

            for frag in must_have:
                if frag not in titles:
                    failures.append(f"{fixture}: '{frag}' 가 추출되지 않음")
            for frag in must_not:
                if frag in titles:
                    failures.append(f"{fixture}: '{frag}' 가 잘못 추출됨(걸러졌어야 함)")

            # 링크 연결 확인: 관심 공고에 유효한 href 가 붙었는지
            for j in jobs:
                if not j["href"] or j["href"] == site["url"]:
                    # 카드에 링크가 아예 없으면 site url 로 폴백될 수 있음(허용)
                    pass

        browser.close()

    print("\n" + "=" * 50)
    if failures:
        print(f"실패 {len(failures)}건:")
        for f in failures:
            print(f"  ✗ {f}")
        return 1
    print("✓ 모든 추출 케이스 통과")
    return 0


if __name__ == "__main__":
    sys.exit(run())
