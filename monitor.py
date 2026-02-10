#!/usr/bin/env python3
"""指定URLの変化を監視するシンプルなモニターツール。"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import smtplib
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable


DEFAULT_URL = "https://parklounge.reservation.jcb/lounge/member/ja/tdr/reserve/loungeReserveRegistCalendar.html"


@dataclass
class Snapshot:
    checksum: str
    matched_keywords: tuple[str, ...]


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def fetch_page(url: str, timeout: int, user_agent: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        body = response.read().decode(charset, errors="replace")
    return body


def normalize_content(content: str) -> str:
    return "\n".join(line.strip() for line in content.splitlines() if line.strip())


def hash_content(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def match_keywords(content: str, keywords: Iterable[str]) -> tuple[str, ...]:
    lowered = content.lower()
    hits = [keyword for keyword in keywords if keyword.lower() in lowered]
    return tuple(sorted(set(hits)))


def build_snapshot(content: str, keywords: Iterable[str]) -> Snapshot:
    normalized = normalize_content(content)
    return Snapshot(
        checksum=hash_content(normalized),
        matched_keywords=match_keywords(normalized, keywords),
    )


def load_snapshot(path: Path) -> Snapshot | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return Snapshot(
        checksum=data["checksum"],
        matched_keywords=tuple(data.get("matched_keywords", [])),
    )


def save_snapshot(path: Path, snapshot: Snapshot) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "checksum": snapshot.checksum,
                "matched_keywords": list(snapshot.matched_keywords),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def post_webhook(webhook_url: str, message: str, timeout: int) -> None:
    payload = json.dumps({"text": message}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout):
        pass


def send_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    sender: str,
    recipient: str,
    subject: str,
    body: str,
) -> None:
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as smtp:
        smtp.login(smtp_user, smtp_password)
        smtp.send_message(msg)


def notify(message: str, args: argparse.Namespace) -> None:
    logging.info(message)

    if args.webhook_url:
        post_webhook(args.webhook_url, message, args.timeout)
        logging.info("Webhookへ通知しました。")

    if args.smtp_host:
        required = [
            args.smtp_port,
            args.smtp_user,
            args.smtp_password,
            args.email_from,
            args.email_to,
        ]
        if not all(required):
            raise ValueError("メール通知を使う場合はSMTP関連引数を全て指定してください。")

        send_email(
            smtp_host=args.smtp_host,
            smtp_port=args.smtp_port,
            smtp_user=args.smtp_user,
            smtp_password=args.smtp_password,
            sender=args.email_from,
            recipient=args.email_to,
            subject=args.email_subject,
            body=message,
        )
        logging.info("メール通知を送信しました。")


def monitor_once(args: argparse.Namespace) -> int:
    try:
        content = fetch_page(args.url, args.timeout, args.user_agent)
    except urllib.error.URLError as exc:
        logging.error("ページ取得に失敗: %s", exc)
        return 1

    current = build_snapshot(content, args.keywords)
    previous = load_snapshot(args.state_file)

    if previous is None:
        save_snapshot(args.state_file, current)
        logging.info("初回スナップショットを保存しました。")
        return 0

    changed = current.checksum != previous.checksum
    keywords_changed = current.matched_keywords != previous.matched_keywords

    if changed or keywords_changed:
        message = (
            "[ページ変化検知]\n"
            f"URL: {args.url}\n"
            f"checksum: {previous.checksum[:12]} -> {current.checksum[:12]}\n"
            f"keyword: {previous.matched_keywords} -> {current.matched_keywords}"
        )
        notify(message, args)
        save_snapshot(args.state_file, current)
    else:
        logging.info("変化なし")

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Webページ監視ツール")
    parser.add_argument("--url", default=DEFAULT_URL, help="監視対象URL")
    parser.add_argument("--interval", type=int, default=300, help="監視間隔（秒）")
    parser.add_argument("--timeout", type=int, default=20, help="通信タイムアウト（秒）")
    parser.add_argument(
        "--state-file",
        type=Path,
        default=Path(".monitor/state.json"),
        help="前回状態を保存するファイル",
    )
    parser.add_argument(
        "--keyword",
        action="append",
        default=[],
        dest="keywords",
        help="監視したいキーワード（複数指定可）",
    )
    parser.add_argument("--webhook-url", default=os.getenv("MONITOR_WEBHOOK_URL"))
    parser.add_argument("--smtp-host", default=os.getenv("MONITOR_SMTP_HOST"))
    parser.add_argument("--smtp-port", type=int, default=int(os.getenv("MONITOR_SMTP_PORT", "465")))
    parser.add_argument("--smtp-user", default=os.getenv("MONITOR_SMTP_USER"))
    parser.add_argument("--smtp-password", default=os.getenv("MONITOR_SMTP_PASSWORD"))
    parser.add_argument("--email-from", default=os.getenv("MONITOR_EMAIL_FROM"))
    parser.add_argument("--email-to", default=os.getenv("MONITOR_EMAIL_TO"))
    parser.add_argument("--email-subject", default="[監視通知] ページの状態が更新されました")
    parser.add_argument(
        "--user-agent",
        default="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36",
        help="HTTP User-Agent",
    )
    parser.add_argument("--once", action="store_true", help="1回だけチェックして終了")
    parser.add_argument("--verbose", action="store_true", help="デバッグログを有効化")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)

    if args.once:
        return monitor_once(args)

    while True:
        code = monitor_once(args)
        if code != 0:
            return code
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
