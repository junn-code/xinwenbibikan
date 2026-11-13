
import json
import re
import html
import time
import xml.etree.ElementTree as ET

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from urllib.parse import urlsplit, urlunsplit


# ==========================================
# 新闻来源
# ==========================================

SOURCES = [

    # MALAYSIA - ENGLISH

    {
        "name": "The Star",
        "urls": ["https://www.thestar.com.my/rss/News"],
        "lang": "en", "country": "my"
    },
    {
        "name": "New Straits Times",
        "urls": ["https://www.nst.com.my/rss"],
        "lang": "en", "country": "my"
    },
    {
        "name": "Free Malaysia Today",
        "urls": ["https://www.freemalaysiatoday.com/feed/"],
        "lang": "en", "country": "my"
    },
    {
        "name": "Malay Mail",
        "urls": ["https://www.malaymail.com/feed/rss/malaysia"],
        "lang": "en", "country": "my"
    },
    {
        "name": "Bernama English",
        "urls": ["https://www.bernama.com/en/rss.php"],
        "lang": "en", "country": "my"
    },

    # MALAYSIA - BAHASA MELAYU

    {
        "name": "Berita Harian",
        "urls": ["https://www.bharian.com.my/rss.xml"],
        "lang": "bm", "country": "my"
    },
    {
        "name": "Harian Metro",
        "urls": ["https://www.hmetro.com.my/rss"],
        "lang": "bm", "country": "my"
    },
    {
        "name": "Utusan Malaysia",
        "urls": ["https://www.utusan.com.my/feed/"],
        "lang": "bm", "country": "my"
    },
    {
        "name": "Sinar Harian",
        "urls": ["https://www.sinarharian.com.my/rss"],
        "lang": "bm", "country": "my"
    },
    {
        "name": "Bernama BM",
        "urls": ["https://www.bernama.com/bm/rss.php"],
        "lang": "bm", "country": "my"
    },

    # MALAYSIA - CHINESE

    {
        "name": "星洲日报",
        "urls": [
            "https://www.sinchew.com.my/feed/",
            "https://rsshub.app/sinchew/latest"
        ],
        "lang": "zh", "country": "my"
    },
    {
        "name": "中国报",
        "urls": [
            "https://www.chinapress.com.my/feed/"
        ],
        "lang": "zh", "country": "my"
    },
    {
        "name": "南洋商报",
        "urls": [
            "https://www.enanyang.my/feed/"
        ],
        "lang": "zh", "country": "my"
    },

    # MALAYSIA - TAMIL

    {
        "name": "Makkal Osai",
        "urls": ["https://makkalosai.com.my/feed/"],
        "lang": "ta", "country": "my"
    },

    # JAPAN

    {
        "name": "NHK World",
        "urls": [
            "https://www3.nhk.or.jp/nhkworld/en/news/feeds/"
        ],
        "lang": "en", "country": "japan"
    },
    {
        "name": "The Japan Times",
        "urls": ["https://www.japantimes.co.jp/feed/"],
        "lang": "en", "country": "japan"
    },

    # SOUTH KOREA

    {
        "name": "Yonhap News",
        "urls": ["https://en.yna.co.kr/RSS/news.xml"],
        "lang": "en", "country": "korea"
    },
    {
        "name": "Korea Herald",
        "urls": [
            "https://www.koreaherald.com/rss/koreaherald.xml"
        ],
        "lang": "en", "country": "korea"
    },

    # CHINA

    {
        "name": "China Daily",
        "urls": [
            "https://www.chinadaily.com.cn/rss/world_rss.xml"
        ],
        "lang": "en", "country": "china"
    },
    {
        "name": "Xinhua",
        "urls": [
            "https://english.news.cn/rss/worldrss.xml"
        ],
        "lang": "en", "country": "china"
    },

    # TAIWAN

    {
        "name": "Focus Taiwan",
        "urls": ["https://focustaiwan.tw/rss"],
        "lang": "en", "country": "taiwan"
    },

    # SINGAPORE

    {
        "name": "Channel News Asia",
        "urls": [
            "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml"
        ],
        "lang": "en", "country": "singapore"
    },

    # USA

    {
        "name": "NPR",
        "urls": ["https://feeds.npr.org/1001/rss.xml"],
        "lang": "en", "country": "usa"
    },

    # UK

    {
        "name": "BBC News",
        "urls": [
            "https://feeds.bbci.co.uk/news/world/rss.xml"
        ],
        "lang": "en", "country": "uk"
    },
    {
        "name": "The Guardian",
        "urls": ["https://www.theguardian.com/world/rss"],
        "lang": "en", "country": "uk"
    },

    # EUROPEAN UNION

    {
        "name": "Euronews",
        "urls": [
            "https://www.euronews.com/rss?level=theme&name=news"
        ],
        "lang": "en", "country": "eu"
    },
    {
        "name": "Politico Europe",
        "urls": ["https://www.politico.eu/feed/"],
        "lang": "en", "country": "eu"
    }
]


# ==========================================
# 通用工具
# ==========================================

def local_name(tag):
    return tag.split("}")[-1].lower()


def clean_text(value):

    if not value:
        return ""

    value = html.unescape(str(value))

    value = re.sub(
        r"<(script|style)[^>]*>.*?</\1>",
        " ",
        value,
        flags=re.I | re.S
    )

    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def normalize_date(value):

    if not value:
        return datetime.now(timezone.utc).isoformat()

    try:

        try:
            date = parsedate_to_datetime(value)
        except Exception:
            date = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )

        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)

        return date.astimezone(timezone.utc).isoformat()

    except Exception:
        return datetime.now(timezone.utc).isoformat()


# ==========================================
# XML 字段读取
# ==========================================

def get_child_text(element, names):

    names = {name.lower() for name in names}

    for child in element:

        if local_name(child.tag) in names:

            value = "".join(child.itertext()).strip()

            if value:
                return value

    for child in element.iter():

        if child is element:
            continue

        if local_name(child.tag) in names:

            value = "".join(child.itertext()).strip()

            if value:
                return value

    return ""


def get_link(entry):

    for child in entry.iter():

        if child is entry:
            continue

        tag = local_name(child.tag)

        if tag == "link":

            href = child.attrib.get("href", "").strip()

            if href.startswith(("http://", "https://")):
                return href

            value = "".join(child.itertext()).strip()

            if value.startswith(("http://", "https://")):
                return value

        if tag == "guid":

            value = "".join(child.itertext()).strip()

            if value.startswith(("http://", "https://")):
                return value

    return ""


# ==========================================
# 解析 RSS / Atom / RDF
# ==========================================

def parse_feed(raw_data, source):

    root = ET.fromstring(raw_data)

    entries = []

    for element in root.iter():

        if local_name(element.tag) in ("item", "entry"):
            entries.append(element)

    results = []

    for entry in entries:

        title = clean_text(
            get_child_text(entry, {"title"})
        )

        link = get_link(entry)

        if not title or not link:
            continue

        if not link.startswith(("http://", "https://")):
            continue

        summary = clean_text(
            get_child_text(
                entry,
                {
                    "description",
                    "summary",
                    "encoded",
                    "content"
                }
            )
        )

        published = get_child_text(
            entry,
            {
                "pubdate",
                "published",
                "updated",
                "date",
                "date.issued"
            }
        )

        results.append({

            "h": title,
            "u": link,
            "o": source["name"],
            "t": normalize_date(published),
            "l": source["lang"],
            "country": source["country"],
            "summary": summary[:700]

        })

    return results


# ==========================================
# 抓取单一来源
# ==========================================

def fetch_source(source):

    print("\n正在抓取：", source["name"])

    errors = []

    for feed_url in source["urls"]:

        try:

            request = Request(
                feed_url,
                headers={
                    "User-Agent": "Mozilla/5.0 NewsCompare/1.0",
                    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"
                }
            )

            with urlopen(request, timeout=25) as response:

                raw_data = response.read()
                status = response.status

            if not raw_data:
                raise ValueError("服务器返回空内容")

            preview = raw_data[:500].lstrip().lower()

            if (
                preview.startswith(b"<!doctype html")
                or preview.startswith(b"<html")
            ):
                raise ValueError("服务器返回 HTML，不是 RSS XML")

            results = parse_feed(raw_data, source)

            if results:

                print(
                    "[成功]",
                    source["name"],
                    len(results),
                    "篇",
                    "| HTTP:",
                    status
                )

                return results

            raise ValueError(
                "RSS XML 已读取，但没有找到有效新闻"
            )

        except Exception as error:

            message = str(error)

            errors.append(
                feed_url + " -> " + message
            )

            print(
                "[备用地址失败]",
                source["name"],
                message
            )

    raise Exception("；".join(errors))


# ==========================================
# 新闻去重
# ==========================================

def normalize_url(url):

    try:

        parts = urlsplit(url)

        return urlunsplit((
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path.rstrip("/"),
            "",
            ""
        ))

    except Exception:

        return url


# ==========================================
# 主程序
# ==========================================

def main():

    all_news = []
    success_sources = []
    failed_sources = []

    print("\n===================================")
    print("       NEWS COMPARE")
    print("       新闻抓取系统")
    print("===================================")

    print("\n新闻来源总数：", len(SOURCES))

    with ThreadPoolExecutor(max_workers=8) as executor:

        futures = {
            executor.submit(fetch_source, source): source
            for source in SOURCES
        }

        for future in as_completed(futures):

            source = futures[future]

            try:

                result = future.result()

                all_news.extend(result)

                success_sources.append({
                    "source": source["name"],
                    "count": len(result)
                })

            except Exception as error:

                failed_sources.append({
                    "source": source["name"],
                    "error": str(error)
                })

                print(
                    "[失败]",
                    source["name"],
                    error
                )

    # 去重

    seen = set()
    unique_news = []

    for item in all_news:

        url = normalize_url(item["u"])

        if not url or url in seen:
            continue

        seen.add(url)
        unique_news.append(item)

    # 排序

    unique_news.sort(
        key=lambda item: item["t"],
        reverse=True
    )

    # 输出 JSON

    output = {

        "updated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "items": unique_news,

        "sources_ok": sorted(
            success_sources,
            key=lambda x: x["source"]
        ),

        "sources_failed": sorted(
            failed_sources,
            key=lambda x: x["source"]
        )

    }

    with open(
        "news.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2
        )

    # 报告

    print("\n===================================")
    print("新闻抓取完成")
    print("-----------------------------------")

    print("新闻总数：", len(unique_news))
    print("成功来源：", len(success_sources))
    print("失败来源：", len(failed_sources))

    print("-----------------------------------")

    print("\n中文新闻统计：")

    for item in unique_news:

        if item["l"] == "zh":
            print(
                item["o"],
                "|",
                item["h"]
            )

    print("\n中文新闻总数：", sum(
        1 for item in unique_news
        if item["l"] == "zh"
    ))

    print("\n已生成 news.json")
    print("===================================")


if __name__ == "__main__":
    main()
