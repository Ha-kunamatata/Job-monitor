# -*- coding: utf-8 -*-
"""
상태 관리
- 이전에 본 공고를 data/seen_jobs.json 에 저장.
- 이번에 수집한 공고와 비교해서 '새 공고'만 골라냅니다.
- 공고 식별은 회사명 + 제목 조합의 해시로 (URL이 자주 바뀌어도 안정적).
"""

import os
import json
import hashlib

STATE_FILE = os.path.join(os.path.dirname(__file__), "data", "seen_jobs.json")


def _job_id(job: dict) -> str:
    """공고 고유 식별자. 회사+제목 기반 해시."""
    basis = f"{job['company']}|{job['title']}".strip()
    return hashlib.md5(basis.encode("utf-8")).hexdigest()[:12]


def load_seen() -> dict:
    """저장된 '본 공고' 딕셔너리 로드. {job_id: {company, title, first_seen}}"""
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        print("    [!] 상태 파일을 읽지 못함. 새로 시작합니다.")
        return {}


def save_seen(seen: dict):
    """본 공고 딕셔너리 저장."""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=2)


def split_new_and_known(jobs: list, seen: dict, today: str):
    """
    수집한 공고를 '새 공고'와 '기존 공고'로 분리.
    새 공고는 seen에 등록.
    반환: (new_jobs, seen_updated)
    """
    new_jobs = []
    for job in jobs:
        jid = _job_id(job)
        if jid not in seen:
            job["_id"] = jid
            job["_first_seen"] = today
            new_jobs.append(job)
            seen[jid] = {
                "company": job["company"],
                "title": job["title"],
                "first_seen": today,
            }
    return new_jobs, seen
