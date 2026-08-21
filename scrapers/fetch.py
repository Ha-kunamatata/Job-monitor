# -*- coding: utf-8 -*-
"""
채용 공고 수집기
- 각 사이트를 개별적으로 긁습니다. 한 곳이 실패해도 나머지는 계속 진행.
- 사이트 구조가 제각각이라, 우선 범용 HTML 파싱으로 '공고처럼 보이는 링크'를 모읍니다.
- 정교한 개별 파서는 사이트별로 점진적으로 추가하세요 (아래 SITE_PARSERS).
"""

import re
import sys
import time
import html
import urllib.request
import urllib.error

# 상위 폴더의 config를 import 하기 위한 경로 처리
sys.path.insert(0, "..")
try:
    from config import KEYWORDS, EXCLUDE_KEYWORDS
except ImportError:
    from ..config import KEYWORDS, EXCLUDE_KEYWORDS

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


def _http_get(url: str, timeout: int = 20) -> str:
    """단순 GET 요청. 실패하면 빈 문자열 반환."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            return resp.read().decode(charset, errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"    [!] 요청 실패: {url} ({e})")
        return ""
    except Exception as e:
        print(f"    [!] 예상치 못한 오류: {url} ({e})")
        return ""


def _strip_tags(raw: str) -> str:
    """HTML 태그 제거 후 텍스트만."""
    no_script = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", no_script)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _matches_interest(text: str) -> bool:
    """관심 키워드 포함 & 제외 키워드 미포함이면 True."""
    if any(ex in text for ex in EXCLUDE_KEYWORDS):
        # 제외 키워드가 있어도, 관심 키워드가 더 강하게 있으면 살림
        interest_hits = sum(1 for k in KEYWORDS if k in text)
        exclude_hits = sum(1 for ex in EXCLUDE_KEYWORDS if ex in text)
        if exclude_hits >= interest_hits:
            return False
    return any(k in text for k in KEYWORDS)


def _extract_candidate_blocks(raw_html: str):
    """
    공고 후보 추출 (범용).
    <a> 태그의 텍스트를 훑어서 관심 키워드가 있는 링크를 공고 후보로 봅니다.
    """
    candidates = []
    # <a ...>텍스트</a> 패턴
    for m in re.finditer(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', raw_html, re.DOTALL | re.IGNORECASE):
        href = m.group(1)
        inner = _strip_tags(m.group(2))
        if not inner or len(inner) < 4:
            continue
        if _matches_interest(inner):
            candidates.append({"title": inner, "href": href})
    return candidates


def fetch_site(site: dict) -> list:
    """
    사이트 하나에서 관심 공고 목록을 수집.
    반환: [{title, href, company, note, priority}, ...]
    """
    print(f"  → {site['name']} 수집 중...")
    raw = _http_get(site["url"])
    if not raw:
        print(f"    [!] {site['name']}: 페이지를 가져오지 못함 (JS 렌더링이거나 차단일 수 있음)")
        return []

    candidates = _extract_candidate_blocks(raw)

    # 중복 제거 (제목 기준)
    seen = set()
    results = []
    for c in candidates:
        key = c["title"]
        if key in seen:
            continue
        seen.add(key)

        href = c["href"]
        # 상대경로 → 절대경로 보정
        if href.startswith("/"):
            from urllib.parse import urljoin
            href = urljoin(site["url"], href)

        results.append({
            "title": c["title"],
            "href": href,
            "company": site["name"],
            "note": site.get("note", ""),
            "priority": site.get("priority", 2),
        })

    print(f"    ✓ {site['name']}: 관심 공고 {len(results)}건 발견")
    return results


def fetch_all(sites: list) -> list:
    """모든 사이트를 순회. 사이트 간 예의상 간격을 둠."""
    all_jobs = []
    for site in sites:
        try:
            jobs = fetch_site(site)
            all_jobs.extend(jobs)
        except Exception as e:
            print(f"    [!] {site['name']} 처리 중 오류 (건너뜀): {e}")
        time.sleep(2)  # 사이트에 부담 주지 않도록
    return all_jobs


if __name__ == "__main__":
    # 단독 테스트: config의 사이트를 실제로 긁어봄
    from config import SITES
    print("=== 스크래퍼 테스트 (실제 네트워크 요청) ===")
    jobs = fetch_all(SITES)
    print(f"\n총 {len(jobs)}건 수집")
    for j in jobs[:15]:
        print(f"  [{j['company']}] {j['title'][:50]}")
