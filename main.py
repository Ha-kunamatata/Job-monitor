# -*- coding: utf-8 -*-
"""
메인 실행부
흐름: 수집 → 새 공고 판별 → 공고별 준비사항 분석 → 마감 임박 체크 → 이메일 발송

GitHub Actions가 이 파일을 주기적으로 실행합니다.
로컬 테스트: python main.py
"""

import sys
from datetime import datetime, date

from config import SITES, DEADLINE_ALERT_DAYS
from scrapers.fetch_browser import fetch_all_browser
from state import load_seen, save_seen, split_new_and_known
from analyzer import analyze  # 마감일 추출·규칙 폴백용
from analyzer_ai import analyze_job  # Claude API 분석 (폴백 내장)
from notify import build_email_html, send_email


def compute_days_left(deadline_str: str):
    """'2026.08.26' 형태 마감일 → 남은 일수. 파싱 실패 시 None."""
    if not deadline_str:
        return None
    try:
        # '2026.08.26' 형태만 처리 (연도 미상은 skip)
        parts = deadline_str.replace("-", ".").split(".")
        if len(parts) == 3 and parts[0].isdigit() and len(parts[0]) == 4:
            y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            delta = (date(y, m, d) - date.today()).days
            return delta
    except (ValueError, IndexError):
        pass
    return None


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"=== 채용 모니터링 실행: {today} ===\n")

    # 1) 수집 (브라우저 구동)
    print("[1/5] 공고 수집")
    all_jobs = fetch_all_browser(SITES)
    print(f"  총 {len(all_jobs)}건 수집\n")

    # 2) 새 공고 판별
    print("[2/5] 새 공고 판별")
    seen = load_seen()
    new_jobs, seen = split_new_and_known(all_jobs, seen, today)
    print(f"  새 공고 {len(new_jobs)}건\n")

    # 3) 공고별 준비사항 분석
    print("[3/5] 공고 분석")
    new_with_analysis = []
    for job in new_jobs:
        # Claude API로 맞춤 분석 (실패 시 규칙기반 자동 폴백)
        analysis_text = analyze_job(job["title"], job.get("note", ""))
        new_with_analysis.append((job, analysis_text))
        # 마감일은 규칙기반 추출기로 별도 확보 (4단계에서 사용)
        job_text = job.get("note", "") + " " + job.get("_context", "")
        job["_deadline"] = analyze(job["title"], job_text).get("deadline")
    print(f"  {len(new_with_analysis)}건 분석 완료\n")

    # 4) 마감 임박 체크 (전체 수집분 대상)
    print("[4/5] 마감 임박 체크")
    deadline_jobs = []
    for job in all_jobs:
        job_text = job.get("note", "") + " " + job.get("_context", "")
        result = analyze(job["title"], job_text)
        days_left = compute_days_left(result.get("deadline"))
        if days_left is not None and 0 <= days_left <= DEADLINE_ALERT_DAYS:
            deadline_jobs.append((job, days_left))
    deadline_jobs.sort(key=lambda x: x[1])
    print(f"  마감 임박 {len(deadline_jobs)}건\n")

    # 5) 이메일 발송 (새 공고 or 마감 임박이 있을 때만)
    print("[5/5] 이메일 발송")
    if new_with_analysis or deadline_jobs:
        subject = f"[채용알림] 새 공고 {len(new_with_analysis)}건 · 마감임박 {len(deadline_jobs)}건 ({today})"
        html_body = build_email_html(new_with_analysis, deadline_jobs)
        send_email(subject, html_body)
    else:
        print("  발송할 내용 없음 (새 공고/마감임박 모두 없음)")

    # 상태 저장 (새 공고를 '본 것'으로 기록)
    save_seen(seen)
    print("\n=== 완료 ===")


if __name__ == "__main__":
    main()
