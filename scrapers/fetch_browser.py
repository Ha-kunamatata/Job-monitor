# -*- coding: utf-8 -*-
"""
Playwright 기반 채용 공고 수집기 (강력 버전 2)
- 실제 Chromium 브라우저를 띄워 JS 렌더링 후 페이지를 긁습니다.
- 채용 사이트 대부분이 React/Vue 기반이라 공고 제목이 <a> 텍스트가 아니라
  <div>/<span>/<li> 안에 있고, 링크는 "지원하기" 같은 별도 버튼입니다.
  → 그래서 '앵커 텍스트만' 보는 방식은 대부분의 공고를 놓칩니다.
  이 버전은 "공고 카드(리스트 항목) 텍스트"를 기준으로 관심 공고를 찾고,
  카드 안/주변의 링크를 자동으로 연결합니다.
- networkidle 은 광고/애널리틱스가 계속 도는 국내 대기업 사이트에서
  거의 항상 타임아웃 → 사이트 전체 수집 실패의 주범이라 사용하지 않습니다.
  domcontentloaded 후 명시적으로 스크롤/대기해서 지연 로딩을 유발합니다.
- iframe 안에 공고 목록이 들어있는 경우(그리팅/그린하우스 등)도 훑습니다.
- 각 사이트는 독립적으로 처리 (한 곳 실패해도 나머지 진행).

필요 패키지: playwright  (그리고 `playwright install chromium`)

로컬/샌드박스 테스트용 환경변수(선택):
  PLAYWRIGHT_CHROMIUM_PATH  - 크로미움 실행파일 경로를 직접 지정
  PLAYWRIGHT_PROXY          - 프록시 서버(http://host:port) 지정
  (둘 다 GitHub Actions 에서는 설정하지 않으므로 CI 동작에는 영향 없음)
"""

import os
import re
import sys
import html
import time

sys.path.insert(0, "..")
try:
    from config import KEYWORDS, EXCLUDE_KEYWORDS
except ImportError:
    from ..config import KEYWORDS, EXCLUDE_KEYWORDS

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# 공고가 아니라 사이트 메뉴/푸터일 확률이 높은 링크 텍스트 (노이즈 제거)
NAV_NOISE = [
    "로그인", "회원가입", "개인정보", "이용약관", "고객센터", "사이트맵",
    "menu", "login", "sign in", "sign up", "faq", "홈으로", "top", "맨위",
    "이전", "다음", "prev", "next", "검색", "search",
]

# 카드/목록 항목으로 볼 만한 요소 (사이트별 클래스명이 제각각이라 넓게 잡음)
CARD_SELECTOR = (
    "li, tr, article, "
    "[class*='job'], [class*='Job'], [class*='recruit'], [class*='Recruit'], "
    "[class*='card'], [class*='Card'], [class*='item'], [class*='Item'], "
    "[class*='list'], [class*='List'], [class*='posting'], [class*='Posting'], "
    "[class*='notice'], [class*='employ']"
)

# 관심 공고 텍스트가 지나치게 길면(=카드가 아니라 페이지 통째) 잘라냄
MAX_TITLE_LEN = 120
MIN_TITLE_LEN = 4


def _clean(text: str) -> str:
    """공백/개행 정리."""
    return re.sub(r"\s+", " ", html.unescape(text or "")).strip()


def _is_noise(text: str) -> bool:
    low = text.lower()
    return any(n.lower() in low for n in NAV_NOISE)


def _matches_interest(text: str) -> bool:
    """관심 키워드 포함 & 제외 키워드가 더 강하지 않으면 True."""
    if any(ex in text for ex in EXCLUDE_KEYWORDS):
        interest_hits = sum(1 for k in KEYWORDS if k in text)
        exclude_hits = sum(1 for ex in EXCLUDE_KEYWORDS if ex in text)
        if exclude_hits >= interest_hits:
            return False
    return any(k in text for k in KEYWORDS)


# 페이지(프레임) 안의 (텍스트, 링크) 후보를 뽑아내는 JS.
# 1) 모든 <a> → {text, href}
# 2) '잎(leaf) 카드' 요소 → {자기 텍스트, 카드 안(없으면 조상)의 <a> href}
#    - 카드 안에 또 다른 카드가 있으면(=목록 컨테이너) 건너뜀.
#      그래야 <ul class=list> 같은 컨테이너가 자식 전부를 하나로 뭉쳐
#      거대한 가짜 공고가 되는 것을 막는다.
# 파이썬으로 돌리면 요소별 왕복이 많아 느리고 잘 끊기므로 한 번에 evaluate.
_HARVEST_JS = """
(cardSelector) => {
  const out = [];
  const seen = new Set();
  const push = (text, href) => {
    if (!text) return;
    const key = text + '\\u0000' + (href || '');
    if (seen.has(key)) return;
    seen.add(key);
    out.push({ text, href: href || '' });
  };

  // 1) 앵커 자체
  document.querySelectorAll('a[href]').forEach(a => {
    push(a.innerText || a.textContent || '', a.href);
  });

  // 2) 잎 카드만: 자기 텍스트 + 카드 내부(없으면 조상) 링크
  let cards = [];
  try { cards = document.querySelectorAll(cardSelector); } catch (e) { cards = []; }
  cards.forEach(el => {
    // 하위에 또 카드가 있으면 컨테이너이므로 건너뜀 (잎 카드만 사용)
    let hasChildCard = false;
    try { hasChildCard = !!el.querySelector(cardSelector); } catch (e) {}
    if (hasChildCard) return;
    const t = (el.innerText || el.textContent || '');
    if (!t) return;
    if (t.length > 400) return;
    let a = el.querySelector('a[href]');
    if (!a) a = el.closest('a[href]');
    push(t, a ? a.href : '');
  });

  return out;
}
"""

# 카드 끝에 붙는 버튼/부가 문구 (제목에서 제거)
CTA_TOKENS = ["지원하기", "상세보기", "자세히보기", "자세히", "바로가기", "지원", "보기", "more", "apply"]


def _title_from_text(raw: str) -> str:
    """카드 원문 텍스트에서 사람이 읽을 제목 한 줄을 뽑음.
    - 첫 번째 의미있는 줄을 제목으로 (제목은 대개 카드 최상단).
    - 첫 줄이 배지(NEW, D-7, 신입 등)처럼 너무 짧으면 다음 줄과 합침.
    """
    lines = [ln.strip() for ln in re.split(r"[\r\n]+", raw) if ln.strip()]
    if not lines:
        return _clean(raw)
    title = lines[0]
    idx = 1
    # 첫 줄이 배지/짧은 라벨이면 다음 줄 이어붙임
    while len(title) < MIN_TITLE_LEN and idx < len(lines):
        title = (title + " " + lines[idx]).strip()
        idx += 1
    title = _clean(title)
    # 끝에 붙은 CTA 문구 제거
    for cta in CTA_TOKENS:
        if title.lower().endswith(cta.lower()):
            title = title[: -len(cta)].strip(" ·-|>")
    # 끝에 붙은 마감일/상태 꼬리 제거 (마감일은 _context 에 남아있음)
    #  예: "... ~2026.08.26", "... ~08/26", "... D-7", "... 상시"
    title = re.sub(r"\s*~?\s*20\d{2}[.\-/]\d{1,2}[.\-/]\d{1,2}\s*$", "", title)
    title = re.sub(r"\s*~\s*\d{1,2}[./]\d{1,2}\s*$", "", title)
    title = re.sub(r"\s*D-\s*\d+\s*$", "", title)
    title = re.sub(r"\s*(상시|채용시\s*마감|수시)\s*$", "", title)
    return title.strip(" ·-|>")


def _harvest_frame(frame, cardSelector: str):
    try:
        return frame.evaluate(_HARVEST_JS, cardSelector) or []
    except Exception:
        return []


def _settle(page):
    """지연 로딩 유발: 아래로 몇 번 스크롤하며 대기."""
    try:
        page.wait_for_selector("body", timeout=8000)
    except Exception:
        pass
    for _ in range(4):
        try:
            page.mouse.wheel(0, 3000)
        except Exception:
            pass
        time.sleep(1.2)
    # 맨 위로 복귀 (일부 사이트는 상단 목록만 렌더)
    try:
        page.mouse.wheel(0, -12000)
    except Exception:
        pass
    time.sleep(0.5)


def fetch_site_browser(page, site: dict) -> list:
    """브라우저 page 객체로 사이트 하나를 긁음."""
    print(f"  → {site['name']} 수집 중 (브라우저)...")

    # networkidle 은 국내 대기업 사이트에서 거의 항상 타임아웃 →
    # domcontentloaded 로 열고, 실패하면 한 번 더 관대하게 재시도.
    loaded = False
    for attempt, wait_mode in enumerate(("domcontentloaded", "commit")):
        try:
            page.goto(site["url"], timeout=45000, wait_until=wait_mode)
            loaded = True
            break
        except PWTimeout:
            print(f"    [!] {site['name']} goto 타임아웃({wait_mode}) - 재시도")
        except Exception as e:
            print(f"    [!] {site['name']} 페이지 로드 실패({wait_mode}): {e}")
    if not loaded:
        return []

    _settle(page)

    # 메인 프레임 + 모든 하위 프레임(iframe) 훑기
    candidates = []
    frames = [page.main_frame] + [f for f in page.frames if f != page.main_frame]
    for fr in frames:
        candidates.extend(_harvest_frame(fr, CARD_SELECTOR))

    # 진단용: 페이지가 실제로 렌더돼 후보가 잡혔는지 (0이면 로드/차단 의심)
    print(f"    (원시 후보 {len(candidates)}개 / 프레임 {len(frames)}개)")

    results = []
    seen_titles = set()
    for c in candidates:
        raw = c.get("text", "")
        context = _clean(raw)
        title = _title_from_text(raw)
        href = c.get("href", "") or site["url"]

        # 관심 여부는 카드 전체 텍스트로 판단(제목에 키워드가 없고 본문에만 있어도 잡힘)
        if not _matches_interest(context):
            continue
        # 제목 자체가 메뉴/푸터 성격이면 제외
        if _is_noise(title):
            continue
        if len(title) < MIN_TITLE_LEN:
            continue
        if len(title) > MAX_TITLE_LEN:
            title = title[:MAX_TITLE_LEN].rstrip() + "…"

        # 제목 정규화 기준 중복 제거 (다른 카드가 같은 공고를 가리키는 경우 병합)
        norm = re.sub(r"\s+", "", title.lower())
        if norm in seen_titles:
            continue
        seen_titles.add(norm)

        if href.startswith("/"):
            from urllib.parse import urljoin
            href = urljoin(site["url"], href)

        results.append({
            "title": title,
            "href": href,
            "company": site["name"],
            "note": site.get("note", ""),
            "priority": site.get("priority", 2),
            "_context": context,  # 마감일 추출 등에 활용
        })

    print(f"    ✓ {site['name']}: 관심 공고 {len(results)}건")
    return results


def _launch_kwargs():
    """CI/로컬 겸용 브라우저 실행 옵션."""
    kwargs = dict(
        headless=True,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
    )
    exe = os.environ.get("PLAYWRIGHT_CHROMIUM_PATH")
    if exe:
        kwargs["executable_path"] = exe
    proxy = os.environ.get("PLAYWRIGHT_PROXY")
    if proxy:
        kwargs["proxy"] = {"server": proxy}
    return kwargs


def fetch_all_browser(sites: list) -> list:
    """모든 사이트를 브라우저로 순회."""
    if not PLAYWRIGHT_AVAILABLE:
        print("  [!] Playwright가 설치되지 않았습니다.")
        print("      pip install playwright && playwright install chromium")
        return []

    all_jobs = []
    with sync_playwright() as p:
        browser = p.chromium.launch(**_launch_kwargs())
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            ),
            viewport={"width": 1366, "height": 768},
            locale="ko-KR",
            ignore_https_errors=True,
        )
        context.set_default_timeout(45000)
        page = context.new_page()

        for site in sites:
            try:
                jobs = fetch_site_browser(page, site)
                all_jobs.extend(jobs)
            except Exception as e:
                print(f"    [!] {site['name']} 처리 오류 (건너뜀): {e}")
            time.sleep(2)

        browser.close()
    return all_jobs


if __name__ == "__main__":
    from config import SITES
    print("=== Playwright 스크래퍼 테스트 ===")
    jobs = fetch_all_browser(SITES)
    print(f"\n총 {len(jobs)}건 수집")
    for j in jobs[:20]:
        print(f"  [{j['company']}] {j['title'][:50]}")
