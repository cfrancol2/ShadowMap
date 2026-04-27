"""Scraper .onion para capa de ingesta con logging, resiliencia y anti-baneo."""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import logging
import os
import random
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from requests_tor import RequestsTor

try:
    from telegram import Bot
except Exception:  # pragma: no cover
    Bot = None

try:
    import telegram_config
except Exception:  # pragma: no cover
    telegram_config = None

try:
    from anonymizer import PIIAnonymizer
except Exception:  # pragma: no cover
    PIIAnonymizer = None


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (X11; Linux x86_64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
]

FIELDNAMES = [
    "message_id",
    "thread_id",
    "parent_message_id",
    "forum_name",
    "category",
    "username",
    "user_role",
    "timestamp",
    "title",
    "body",
    "quoted_text",
    "extracted_entities",
    "raw_url",
]


def setup_logger(log_file: str) -> logging.Logger:
    os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
    logger = logging.getLogger("forum_scraper")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


def load_lines(filepath: str) -> List[str]:
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def normalize_url(url: str) -> Optional[str]:
    url = url.split("#")[0].split("?")[0].strip()
    if ".onion" not in url:
        return None
    if url.endswith((".css", ".js", ".png", ".jpg", ".gif", ".pdf", ".svg")):
        return None
    if not url.startswith(("http://", "https://")):
        return f"http://{url}"
    return url


def detect_forum_name(url: str) -> str:
    low = url.lower()
    if "ramp" in low:
        return "RAMP"
    if "xss" in low:
        return "XSS"
    return "UNKNOWN_FORUM"


def extract_onion_links(html: str) -> Set[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: Set[str] = set()

    for tag in soup.find_all(["a", "link", "iframe"], href=True):
        norm = normalize_url(tag.get("href", ""))
        if norm:
            links.add(norm)

    for tag in soup.find_all(["a", "link", "iframe"], src=True):
        norm = normalize_url(tag.get("src", ""))
        if norm:
            links.add(norm)

    text = soup.get_text(" ", strip=True)
    for m in re.findall(r"https?://[^\s\"']+\.onion[^\s\"']*", text):
        norm = normalize_url(m)
        if norm:
            links.add(norm)
    return links


def infer_thread_id(url: str, html: str) -> str:
    match = re.search(r"(?:thread|topic|t|showtopic|viewtopic)[=/](\d+)", url, flags=re.IGNORECASE)
    if match:
        return f"thread_{match.group(1)}"

    soup = BeautifulSoup(html, "html.parser")
    for key in ["data-thread-id", "data-topic-id", "data-thread"]:
        node = soup.find(attrs={key: True})
        if node:
            return f"thread_{node.get(key)}"

    return "thread_" + hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def infer_category(soup: BeautifulSoup) -> str:
    breadcrumb = soup.select(".breadcrumb li, .breadcrumbs li, nav.breadcrumb a, .nav-breadcrumb a")
    if breadcrumb:
        txt = breadcrumb[-1].get_text(" ", strip=True)
        if txt:
            return txt
    return "unknown_category"


def parse_timestamp(raw_ts: str) -> str:
    if not raw_ts:
        return datetime.now(timezone.utc).isoformat()

    raw_ts = raw_ts.strip()
    for fmt in [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%Y/%m/%d %H:%M:%S",
    ]:
        try:
            dt = datetime.strptime(raw_ts, fmt)
            return dt.replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            pass
    return datetime.now(timezone.utc).isoformat()


def extract_entities(text: str) -> Dict[str, List[str]]:
    if not text:
        return {}
    cves = sorted(set(re.findall(r"CVE-\d{4}-\d{4,7}", text, flags=re.IGNORECASE)))
    tools = []
    for t in ["metasploit", "cobalt strike", "mimikatz", "powershell", "rclone", "bloodhound", "empire", "sliver", "nmap", "masscan"]:
        if t in text.lower():
            tools.append(t)
    out: Dict[str, List[str]] = {}
    if cves:
        out["cves"] = cves
    if tools:
        out["tools"] = sorted(set(tools))
    return out


def pick_first_text(node, selectors: List[str]) -> str:
    for sel in selectors:
        found = node.select_one(sel)
        if found:
            txt = found.get_text(" ", strip=True)
            if txt:
                return txt
    return ""


def extract_posts_from_html(url: str, html: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    forum_name = detect_forum_name(url)
    category = infer_category(soup)
    thread_id = infer_thread_id(url, html)
    page_title = pick_first_text(soup, ["h1", "h2", "title"]) or "sin_titulo"

    containers = soup.select(".post, .message, article, .comment, .reply, [data-post-id], [id^='post-'], [class*='post']")
    if not containers:
        containers = [soup.body] if soup.body else []

    records: List[Dict[str, Any]] = []
    for idx, post in enumerate(containers):
        if post is None:
            continue

        raw_msg_id = post.get("data-post-id") or post.get("data-id") or post.get("id") or f"{thread_id}_{idx}"
        message_id = "msg_" + hashlib.sha1(f"{url}|{raw_msg_id}|{idx}".encode("utf-8")).hexdigest()[:16]

        parent_raw = post.get("data-parent-id") or post.get("data-reply-to")
        parent_message_id = None
        if parent_raw:
            parent_message_id = "msg_" + hashlib.sha1(f"{url}|{parent_raw}".encode("utf-8")).hexdigest()[:16]

        username = pick_first_text(post, [".author", ".username", ".user", "[class*='author']", "[class*='user']"]) or "unknown_user"
        user_role = pick_first_text(post, [".role", ".rank", ".badge", "[class*='role']", "[class*='rank']"]) or "unknown_role"

        ts_raw = ""
        time_tag = post.select_one("time")
        if time_tag:
            ts_raw = time_tag.get("datetime") or time_tag.get_text(" ", strip=True)
        if not ts_raw:
            ts_raw = pick_first_text(post, [".date", ".timestamp", "[class*='time']", "[class*='date']"])
        timestamp = parse_timestamp(ts_raw)

        body = pick_first_text(post, [".content", ".body", ".message", ".postbody", "[class*='content']", "[class*='body']"]) or post.get_text(" ", strip=True)
        if len(body) < 20:
            continue

        quoted_text = pick_first_text(post, ["blockquote", ".quote", "[class*='quote']"]) or None
        entities = extract_entities(body)

        records.append(
            {
                "message_id": message_id,
                "thread_id": thread_id,
                "parent_message_id": parent_message_id,
                "forum_name": forum_name,
                "category": category,
                "username": username,
                "user_role": user_role,
                "timestamp": timestamp,
                "title": page_title,
                "body": body,
                "quoted_text": quoted_text,
                "extracted_entities": entities,
                "raw_url": url,
            }
        )
    return records


def save_jsonl(records: List[Dict[str, Any]], path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def save_csv(records: List[Dict[str, Any]], path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for r in records:
            row = dict(r)
            row["extracted_entities"] = json.dumps(row.get("extracted_entities", {}), ensure_ascii=False)
            writer.writerow({k: row.get(k) for k in FIELDNAMES})


def save_keyword_report(matches: List[Dict[str, str]], path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for m in matches:
            f.write(f"{m['keyword']} | {m['url']}\n")


def save_checkpoint(path: str, pending: List[Tuple[str, int]], visited: Set[str]) -> None:
    data = {
        "pending": [{"url": u, "depth": d} for u, d in pending],
        "visited": list(visited),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_checkpoint(path: str) -> Tuple[List[Tuple[str, int]], Set[str]]:
    if not os.path.exists(path):
        return [], set()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    pending = [(x["url"], int(x["depth"])) for x in data.get("pending", [])]
    visited = set(data.get("visited", []))
    return pending, visited


def is_ban_or_honeypot(status_code: int, requested_url: str, final_url: str) -> bool:
    if status_code == 403:
        return True
    req = urlparse(requested_url)
    final = urlparse(final_url)
    if requested_url != final_url and req.netloc == final.netloc:
        suspicious_req = any(x in req.path.lower() for x in ["thread", "topic", "post", "viewtopic"])
        redirected_home = final.path.lower() in ["", "/", "/index.php", "/home", "/forum", "/login"]
        if suspicious_req and redirected_home:
            return True
    return False


def rotate_tor_circuit(logger: logging.Logger, rtor: RequestsTor) -> RequestsTor:
    logger.warning("Rotando circuito Tor por posible baneo...")
    try:
        if hasattr(rtor, "reset_identity"):
            rtor.reset_identity()
            time.sleep(5)
            return rtor
        if hasattr(rtor, "new_identity"):
            rtor.new_identity()
            time.sleep(5)
            return rtor
    except Exception as e:  # pragma: no cover
        logger.error("No se pudo rotar identidad con instancia actual: %s", e)

    # fallback: recrear cliente tor
    time.sleep(5)
    return RequestsTor(tor_ports=(9050,), tor_cport=9051, autochange_id=5)


def fetch_with_resilience(
    logger: logging.Logger,
    rtor: RequestsTor,
    url: str,
    timeout: int,
    max_retries: int,
) -> Tuple[Optional[Any], RequestsTor, bool]:
    """Retorna (response, rtor, banned_detected)."""
    for attempt in range(1, max_retries + 1):
        try:
            response = rtor.get(url, headers={"User-Agent": random.choice(USER_AGENTS)}, timeout=timeout)
            if is_ban_or_honeypot(response.status_code, url, response.url):
                logger.warning("Posible baneo detectado en %s (status=%s, final=%s)", url, response.status_code, response.url)
                rtor = rotate_tor_circuit(logger, rtor)
                return None, rtor, True

            if response.status_code >= 500:
                logger.error("Error servidor %s en %s (intento %s/%s)", response.status_code, url, attempt, max_retries)
                time.sleep(min(30, attempt * 5))
                continue

            if response.status_code != 200:
                logger.warning("HTTP %s en %s", response.status_code, url)
                return None, rtor, False

            return response, rtor, False
        except Exception as e:
            logger.error("Timeout/conexión fallida en %s (intento %s/%s): %s", url, attempt, max_retries, e)
            time.sleep(min(30, attempt * 5))
    return None, rtor, False


def check_tor_connection(logger: logging.Logger, rtor: RequestsTor) -> None:
    logger.info("--- Verificando conexión Tor ---")
    try:
        resp = rtor.get("https://icanhazip.com", timeout=15)
        if resp.status_code == 200:
            logger.info("IP de salida Tor: %s", resp.text.strip())
        else:
            logger.warning("Error verificando Tor: %s", resp.status_code)
    except Exception as e:
        logger.error("No fue posible verificar Tor: %s", e)


async def send_report_telegram(path: str, logger: logging.Logger) -> None:
    if Bot is None or telegram_config is None:
        logger.warning("Telegram no disponible (falta dependencia/configuración).")
        return
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        logger.warning("El reporte no existe o está vacío. No se envía Telegram.")
        return

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    bot = Bot(token=telegram_config.BOT_TOKEN)
    for p in [content[i : i + 3800] for i in range(0, len(content), 3800)]:
        await bot.send_message(chat_id=telegram_config.CHAT_ID, text=p)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scraper de foros .onion con resiliencia")
    parser.add_argument("--seeds", default="seeds.txt")
    parser.add_argument("--keywords", default="identifiers.txt")
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--delay", type=int, default=5)
    parser.add_argument("--timeout", type=int, default=35)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--failure-threshold", type=int, default=10)
    parser.add_argument("--pause-hours", type=float, default=1.0)
    parser.add_argument("--checkpoint-file", default="output/checkpoint.json")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--jsonl-out", default="output/forum_records.jsonl")
    parser.add_argument("--csv-out", default="output/forum_records.csv")
    parser.add_argument("--report-out", default="output/report.txt")
    parser.add_argument("--log-file", default="output/scraper.log")
    parser.add_argument("--send-telegram", action="store_true")
    args = parser.parse_args()

    logger = setup_logger(args.log_file)
    logger.info("Iniciando scraper con parámetros: %s", vars(args))

    seeds = [normalize_url(s) for s in load_lines(args.seeds)]
    seeds = [s for s in seeds if s]
    keywords = load_lines(args.keywords)
    if not seeds and not args.resume:
        raise SystemExit("[!] No hay seeds para iniciar el rastreo.")

    pending: List[Tuple[str, int]] = []
    visited: Set[str] = set()
    if args.resume:
        pending, visited = load_checkpoint(args.checkpoint_file)
        logger.info("Checkpoint cargado: pending=%s visited=%s", len(pending), len(visited))
    if not pending:
        pending = [(u, 0) for u in seeds]

    rtor = RequestsTor(tor_ports=(9050,), tor_cport=9051, autochange_id=5)
    check_tor_connection(logger, rtor)
    anonymizer = PIIAnonymizer() if PIIAnonymizer is not None else None

    records: List[Dict[str, Any]] = []
    keyword_matches: List[Dict[str, str]] = []
    consecutive_failures = 0

    while pending:
        current_url, depth = pending.pop(0)
        if depth > args.max_depth or current_url in visited:
            continue

        logger.info("Visitando depth=%s url=%s", depth, current_url)
        response, rtor, banned = fetch_with_resilience(
            logger=logger,
            rtor=rtor,
            url=current_url,
            timeout=args.timeout,
            max_retries=args.max_retries,
        )

        if banned:
            # Reintentar URL después de rotar circuito
            pending.append((current_url, depth))
            save_checkpoint(args.checkpoint_file, pending, visited)
            time.sleep(10)
            continue

        if response is None:
            consecutive_failures += 1
            logger.error("Fallo procesando %s (consecutivos=%s)", current_url, consecutive_failures)
            if consecutive_failures >= args.failure_threshold:
                pause_seconds = int(args.pause_hours * 3600)
                logger.warning("Umbral de fallos alcanzado. Pausando %s segundos.", pause_seconds)
                save_checkpoint(args.checkpoint_file, pending, visited)
                time.sleep(max(60, pause_seconds))
                consecutive_failures = 0
            continue

        consecutive_failures = 0
        visited.add(current_url)
        html = response.text

        for kw in keywords:
            if kw.lower() in html.lower():
                keyword_matches.append({"keyword": kw, "url": current_url})

        page_records = extract_posts_from_html(current_url, html)
        if anonymizer:
            page_records = [anonymizer.anonymize_record(r) for r in page_records]
        records.extend(page_records)
        logger.info("Registros extraídos en página: %s", len(page_records))

        for link in extract_onion_links(html):
            if link not in visited:
                pending.append((link, depth + 1))

        save_checkpoint(args.checkpoint_file, pending, visited)
        time.sleep(args.delay)

    unique = {r["message_id"]: r for r in records}
    final_records = list(unique.values())
    save_jsonl(final_records, args.jsonl_out)
    save_csv(final_records, args.csv_out)
    save_keyword_report(keyword_matches, args.report_out)

    logger.info("Ingesta completada. Registros únicos=%s", len(final_records))
    logger.info("Salidas: %s | %s | %s", args.jsonl_out, args.csv_out, args.report_out)

    if args.send_telegram:
        asyncio.run(send_report_telegram(args.report_out, logger))


if __name__ == "__main__":
    main()
