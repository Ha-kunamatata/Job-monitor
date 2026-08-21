# -*- coding: utf-8 -*-
"""
이메일 알림 발송
- Gmail SMTP 사용 (앱 비밀번호 필요).
- 새 공고 + 마감 임박 공고를 하나의 HTML 메일로 정리해 발송.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate

from config import (
    EMAIL_FROM, EMAIL_PASSWORD, EMAIL_TO,
    SMTP_SERVER, SMTP_PORT,
)


def _job_card_html(job: dict, analysis_text: str) -> str:
    """공고 하나를 HTML 카드로."""
    prio_badge = "🟢 신입가능 1순위" if job.get("priority") == 1 else "🔵 경력 2순위"
    # 분석 텍스트의 줄바꿈을 <br>로
    analysis_html = analysis_text.replace("\n", "<br>")
    return f"""
    <div style="border:1px solid #ddd; border-radius:8px; padding:16px; margin:12px 0; background:#fafafa;">
        <div style="font-size:12px; color:#888;">{prio_badge} · {job['company']}</div>
        <div style="font-size:16px; font-weight:bold; margin:6px 0;">{job['title']}</div>
        <div style="font-size:12px; color:#666;">{job.get('note','')}</div>
        <a href="{job['href']}" style="font-size:13px; color:#2b6cb0;">공고 바로가기 →</a>
        <div style="margin-top:10px; padding:10px; background:#fff; border-radius:6px; font-size:13px; line-height:1.7; color:#333;">
            {analysis_html}
        </div>
    </div>
    """


def build_email_html(new_jobs_with_analysis: list, deadline_jobs: list) -> str:
    """
    new_jobs_with_analysis: [(job, analysis_text), ...]
    deadline_jobs: [(job, days_left), ...]
    """
    parts = []
    parts.append("""
    <div style="font-family:'Apple SD Gothic Neo','Malgun Gothic',sans-serif; max-width:640px; margin:0 auto;">
        <h2 style="color:#1a202c;">📢 채용 공고 모니터링 리포트</h2>
    """)

    # 마감 임박 섹션 (제일 위 - 급하니까)
    if deadline_jobs:
        parts.append('<h3 style="color:#c53030;">⏰ 마감 임박</h3>')
        for job, days_left in deadline_jobs:
            parts.append(
                f'<div style="padding:10px; border-left:4px solid #c53030; margin:8px 0; background:#fff5f5;">'
                f'<b>D-{days_left}</b> · [{job["company"]}] {job["title"]}<br>'
                f'<a href="{job["href"]}" style="font-size:13px;">공고 바로가기 →</a></div>'
            )

    # 새 공고 섹션
    if new_jobs_with_analysis:
        parts.append(f'<h3 style="color:#2f855a;">🆕 새 공고 {len(new_jobs_with_analysis)}건</h3>')
        for job, analysis_text in new_jobs_with_analysis:
            parts.append(_job_card_html(job, analysis_text))
    else:
        parts.append('<p style="color:#888;">이번 확인에서 새로 올라온 공고는 없습니다.</p>')

    parts.append("""
        <hr style="margin:20px 0; border:none; border-top:1px solid #eee;">
        <p style="font-size:11px; color:#aaa;">
        이 메일은 GitHub Actions로 자동 발송되었습니다.<br>
        공고 분석은 참고용이며, 실제 자격요건은 원문 공고를 확인하세요.
        </p>
    </div>
    """)
    return "".join(parts)


def send_email(subject: str, html_body: str) -> bool:
    """이메일 발송. 성공하면 True."""
    if not (EMAIL_FROM and EMAIL_PASSWORD and EMAIL_TO):
        print("    [!] 이메일 환경변수가 설정되지 않음. 발송 건너뜀.")
        print("        (EMAIL_FROM / EMAIL_PASSWORD / EMAIL_TO 확인)")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg["Date"] = formatdate(localtime=True)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.send_message(msg)
        print("    ✓ 이메일 발송 성공")
        return True
    except Exception as e:
        print(f"    [!] 이메일 발송 실패: {e}")
        return False
