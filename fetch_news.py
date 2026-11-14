
import json
import re
import html
import xml.etree.ElementTree as ET

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from urllib.parse import urlsplit, urlunsplit, quote


# ==========================================================
# NEWS COMPARE - 新闻抓取系统
# Version 4.0
# ==========================================================

MAX_WORKERS = 10
TIMEOUT = 25
MAX_ARTICLES_PER_SOURCE = 200


# ==========================================================
# RSS 地址生成
# ==========================================================

def google_rss(query, language="zh-CN", country="MY"):
    return (
        "https://news.google.com/rss/search?q="
        + quote(query)
        + "&hl=" + language
        + "&gl=" + country
        + "&ceid=" + country + ":" + language
    )


def feed(url, kind="official"):
    return {
        "url": url,
        "kind": kind
    }


def google_source(name, query, language="zh-CN", country="MY"):
    return {
        "name": name,
        "feeds": [
            feed(
                google_rss(query, language, country),
                "google_news"
            )
        ],
        "lang": "zh",
        "country": "my"
    }


# ==========================================================
# 新闻来源
# ==========================================================

SOURCES = [

    # ======================================================
    # MALAYSIA - ENGLISH
    # ======================================================

    {
        "name": "The Star",
        "feeds": [
            feed("https://www.thestar.com.my/rss/News")
        ],
        "lang": "en", "country": "my"
    },
    {
        "name": "New Straits Times",
        "feeds": [
            feed("https://www.nst.com.my/rss")
        ],
        "lang": "en", "country": "my"
    },
    {
        "name": "Free Malaysia Today",
        "feeds": [
            feed("https://www.freemalaysiatoday.com/feed/")
        ],
        "lang": "en", "country": "my"
    },
    {
        "name": "Malay Mail",
        "feeds": [
            feed("https://www.malaymail.com/feed/rss/malaysia")
        ],
        "lang": "en", "country": "my"
    },
    {
        "name": "Bernama English",
        "feeds": [
            feed("https://www.bernama.com/en/rssfeed.php/")
        ],
        "lang": "en", "country": "my"
    },

    # ======================================================
    # MALAYSIA - BAHASA MELAYU
    # ======================================================

    {
        "name": "Berita Harian",
        "feeds": [
            feed("https://www.bharian.com.my/rss.xml")
        ],
        "lang": "bm", "country": "my"
    },
    {
        "name": "Harian Metro",
        "feeds": [
            feed("https://www.hmetro.com.my/rss")
        ],
        "lang": "bm", "country": "my"
    },
    {
        "name": "Utusan Malaysia",
        "feeds": [
            feed("https://www.utusan.com.my/feed/")
        ],
        "lang": "bm", "country": "my"
    },
    {
        "name": "Sinar Harian",
        "feeds": [
            feed("https://www.sinarharian.com.my/rss")
        ],
        "lang": "bm", "country": "my"
    },
    {
        "name": "Bernama BM",
        "feeds": [
            feed("https://www.bernama.com/bm/rssfeed.php/")
        ],
        "lang": "bm", "country": "my"
    },

    # ======================================================
    # MALAYSIA - CHINESE
    # ======================================================

    # 星洲日报
    {
        "name": "星洲日报",
        "feeds": [
            feed(
                "https://rsshub.app/sinchew/latest",
                "third_party"
            ),
            feed(
                google_rss(
                    "site:sinchew.com.my",
                    "zh-CN", "MY"
                ),
                "google_news"
            )
        ],
        "lang": "zh",
        "country": "my",
        "require_chinese": True
    },

    # 中国报
    google_source(
        "Google News 搜索：中国报",
        "site:chinapress.com.my",
        "zh-CN", "MY"
    ),

    # 南洋商报
    google_source(
        "Google News 搜索：南洋商报",
        "site:enanyang.my",
        "zh-CN", "MY"
    ),

    # 东方日报
    google_source(
        "Google News 搜索：东方日报",
        "site:orientaldaily.com.my",
        "zh-CN", "MY"
    ),

    # 光华日报
    google_source(
        "Google News 搜索：光华日报",
        "site:kwongwah.com.my",
        "zh-CN", "MY"
    ),

    # 光明日报
    google_source(
        "Google News 搜索：光明日报",
        "site:guangming.com.my",
        "zh-CN", "MY"
    ),

    # 诗华日报
    google_source(
        "Google News 搜索：诗华日报",
        "site:seehua.com.my",
        "zh-CN", "MY"
    ),

    # BERNAMA 中文
    # 暂时没有确认公开的中文 RSS，先用 Google News 搜索
    google_source(
        "Google News 搜索：BERNAMA 中文",
        'site:bernama.com 中文 OR 华文 OR Mandarin',
        "zh-CN", "MY"
    ),

    # ======================================================
    # MALAYSIA - TAMIL
    # ======================================================

    {
        "name": "Makkal Osai",
        "feeds": [
            feed("https://makkalosai.com.my/feed/")
        ],
        "lang": "ta", "country": "my"
    },

    # ======================================================
    # SINGAPORE - CHINESE
    # ======================================================

    {
        "name": "联合早报",
        "feeds": [
            feed("https://www.zaobao.com.sg/rss.xml"),
            feed(
                google_rss(
                    "site:zaobao.com.sg",
                    "zh-CN", "SG"
                ),
                "google_news"
            )
        ],
        "lang": "zh",
        "country": "singapore",
        "require_chinese": True
    },
    {
        "name": "8视界",
        "feeds": [
            feed(
                "https://www.8world.com/api/v1/rss-outbound-feed?_format=xml&category=176"
            )
        ],
        "lang": "zh",
        "country": "singapore",
        "require_chinese": True
    },

    # ======================================================
    # SINGAPORE - ENGLISH
    # ======================================================

    {
        "name": "CNA Singapore",
        "feeds": [
            feed(
                "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml&category=10416"
            )
        ],
        "lang": "en", "country": "singapore"
    },
    {
        "name": "The Straits Times",
        "feeds": [
            feed(
                "https://www.straitstimes.com/news/singapore/rss.xml"
            )
        ],
        "lang": "en", "country": "singapore"
    },

    # ======================================================
    # JAPAN - JAPANESE
    # ======================================================

    {
        "name": "NHK 日本放送协会",
        "feeds": [
            feed("https://www.nhk.or.jp/rss/news/cat0.xml"),
            feed("https://www.nhk.or.jp/rss/news/cat1.xml")
        ],
        "lang": "ja",
        "country": "japan",
        "require_japanese": True
    },
    {
        "name": "朝日新闻",
        "feeds": [
            feed("https://www.asahi.com/rss/asahi/newsheadlines.rdf")
        ],
        "lang": "ja",
        "country": "japan",
        "require_japanese": True
    },

    # ======================================================
    # JAPAN - ENGLISH
    # ======================================================

    {
        "name": "The Japan Times",
        "feeds": [
            feed("https://www.japantimes.co.jp/feed/")
        ],
        "lang": "en", "country": "japan"
    },
    {
        "name": "NHK World",
        "feeds": [
            feed("https://www3.nhk.or.jp/nhkworld/en/news/feeds/")
        ],
        "lang": "en", "country": "japan"
    },

    # ======================================================
    # SOUTH KOREA - KOREAN
    # ======================================================

    {
        "name": "韩联社",
        "feeds": [
            feed("https://www.yna.co.kr/rss/news.xml"),
            feed("https://www.yna.co.kr/rss/international.xml"),
            feed("https://www.yna.co.kr/rss/economy.xml")
        ],
        "lang": "ko",
        "country": "korea",
        "require_korean": True
    },

    # ======================================================
    # SOUTH KOREA - ENGLISH
    # ======================================================

    {
        "name": "Yonhap English",
        "feeds": [
            feed("https://en.yna.co.kr/RSS/news.xml")
        ],
        "lang": "en", "country": "korea"
    },
    {
        "name": "Korea Herald",
        "feeds": [
            feed("https://www.koreaherald.com/rss/koreaherald.xml")
        ],
        "lang": "en", "country": "korea"
    },

    # ======================================================
    # CHINA - SIMPLIFIED CHINESE
    # ======================================================

    {
        "name": "中国新闻网",
        "feeds": [
            feed("https://www.chinanews.com.cn/rss/scroll-news.xml"),
            feed("https://www.chinanews.com.cn/rss/china.xml"),
            feed(
                google_rss(
                    "site:chinanews.com.cn",
                    "zh-CN", "CN"
                ),
                "google_news"
            )
        ],
        "lang": "zh", "country": "china"
    },
    google_source(
        "Google News 搜索：人民网",
        "site:people.com.cn",
        "zh-CN", "CN"
    ),
    google_source(
        "Google News 搜索：新华网",
        "site:news.cn",
        "zh-CN", "CN"
    ),

    # ======================================================
    # TAIWAN - TRADITIONAL CHINESE
    # ======================================================

    {
        "name": "中央社",
        "feeds": [
            feed("https://feeds.feedburner.com/rsscna/politics"),
            feed("https://feeds.feedburner.com/rsscna/intworld"),
            feed("https://feeds.feedburner.com/rsscna/finance"),
            feed(
                google_rss(
                    "site:cna.com.tw",
                    "zh-TW", "TW"
                ),
                "google_news"
            )
        ],
        "lang": "zh", "country": "taiwan"
    },
    {
        "name": "自由时报",
        "feeds": [
            feed("https://news.ltn.com.tw/rss/all.xml"),
            feed(
                google_rss(
                    "site:ltn.com.tw",
                    "zh-TW", "TW"
                ),
                "google_news"
            )
        ],
        "lang": "zh", "country": "taiwan"
    },
    google_source(
        "Google News 搜索：联合新闻网",
        "site:udn.com",
        "zh-TW", "TW"
    ),
    google_source(
        "Google News 搜索：TVBS新闻网",
        "site:news.tvbs.com.tw",
        "zh-TW", "TW"
    ),

    # ======================================================
    # USA
    # ======================================================

    {
        "name": "NPR",
        "feeds": [
            feed("https://feeds.npr.org/1001/rss.xml")
        ],
        "lang": "en", "country": "usa"
    },

    # ======================================================
    # UK
    # ======================================================

    {
        "name": "BBC News",
        "feeds": [
            feed("https://feeds.bbci.co.uk/news/world/rss.xml")
        ],
        "lang": "en", "country": "uk"
    },
    {
        "name": "The Guardian",
        "feeds": [
            feed("https://www.theguardian.com/world/rss")
        ],
        "lang": "en", "country": "uk"
    },

    # ======================================================
    # EUROPEAN UNION
    # ======================================================

    {
        "name": "Euronews",
        "feeds": [
            feed("https://www.euronews.com/rss?level=theme&name=news")
        ],
        "lang": "en", "country": "eu"
    },
    {
        "name": "Politico Europe",
        "feeds": [
            feed("https://www.politico.eu/feed/")
        ],
        "lang": "en", "country": "eu"
    }
]


# ==========================================================
# 文字处理
# ==========================================================

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


def get_actual_publisher(entry):
    for child in entry.iter():
        if local_name(child.tag) == "source":
            name = (
                child.attrib.get("title")
                or "".join(child.itertext())
            )

            name = clean_text(name)

            if name:
                return name

    return ""


# ==========================================================
# 语言检查
# ==========================================================

def contains_chinese_title(text):
    han_count = sum(
        1 for ch in text
        if (
            "\u3400" <= ch <= "\u4dbf"
            or "\u4e00" <= ch <= "\u9fff"
            or "\uf900" <= ch <= "\ufaff"
        )
    )

    meaningful_count = sum(
        1 for ch in text if ch.isalnum()
    )

    return (
        han_count >= 2
        and meaningful_count > 0
        and han_count / meaningful_count >= 0.20
    )


def contains_japanese_title(text):
    return bool(
        re.search(r"[\u3040-\u30ff]", text)
    )


def contains_korean_title(text):
    return bool(
        re.search(r"[\uac00-\ud7af]", text)
    )


def check_language(title, source):
    if source.get("require_chinese"):
        return contains_chinese_title(title)

    if source.get("require_japanese"):
        return contains_japanese_title(title)

    if source.get("require_korean"):
        return contains_korean_title(title)

    return True


# ==========================================================
# RSS 解析
# ==========================================================

def parse_feed(raw_data, source, feed_info):

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

        if not check_language(title, source):
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
                "date"
            }
        )

        actual_publisher = get_actual_publisher(entry)

        # Google News 必须尽量识别实际媒体
        if feed_info["kind"] == "google_news":
            publisher = actual_publisher or "Google News"
        else:
            publisher = actual_publisher or source["name"]

        results.append({
            "h": title,
            "u": link,
            "o": publisher,
            "t": normalize_date(published),
            "l": source["lang"],
            "country": source["country"],
            "summary": summary[:700],
            "source_type": feed_info["kind"],
            "source_group": source["name"]
        })

    return results


# ==========================================================
# 抓取单一来源
# ==========================================================

def fetch_source(source):

    print("\n正在抓取：", source["name"])

    all_results = []
    errors = []
    success_feeds = 0

    for feed_info in source["feeds"]:

        feed_url = feed_info["url"]

        try:
            request = Request(
                feed_url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 "
                        "(compatible; NewsCompare/4.0)"
                    ),
                    "Accept": (
                        "application/rss+xml, "
                        "application/atom+xml, "
                        "application/xml, "
                        "text/xml, */*"
                    )
                }
            )

            with urlopen(request, timeout=TIMEOUT) as response:
                raw_data = response.read()
                status = response.status
                content_type = response.headers.get(
                    "Content-Type", ""
                )

            if not raw_data:
                raise ValueError("服务器返回空内容")

            preview = raw_data[:500].lstrip().lower()

            if (
                preview.startswith(b"<!doctype html")
                or preview.startswith(b"<html")
            ):
                raise ValueError(
                    "服务器返回 HTML，不是 RSS XML"
                )

            results = parse_feed(
                raw_data,
                source,
                feed_info
            )

            if not results:
                raise ValueError(
                    "没有符合条件的新闻"
                )

            all_results.extend(results)
            success_feeds += 1

            print(
                "[成功]",
                source["name"],
                len(results),
                "篇",
                "| 类型:", feed_info["kind"],
                "| HTTP:", status
            )

        except Exception as error:

            errors.append(
                feed_url + " -> " + str(error)
            )

            print(
                "[失败]",
                source["name"],
                "|",
                str(error)
            )

    if not all_results:
        raise Exception(
            "；".join(errors) or "没有取得新闻"
        )

    # 单一来源限制数量
    all_results = all_results[:MAX_ARTICLES_PER_SOURCE]

    return {
        "items": all_results,
        "success_feeds": success_feeds,
        "errors": errors
    }


# ==========================================================
# 新闻去重
# ==========================================================

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


# ==========================================================
# 主程序
# ==========================================================

def main():

    all_news = []
    success_sources = []
    failed_sources = []

    print("\n===================================")
    print("       NEWS COMPARE V4.0")
    print("       新闻抓取系统")
    print("===================================")

    print("\n新闻来源总数：", len(SOURCES))

    with ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:

        futures = {
            executor.submit(fetch_source, source): source
            for source in SOURCES
        }

        for future in as_completed(futures):

            source = futures[future]

            try:
                result = future.result()

                all_news.extend(result["items"])

                success_sources.append({
                    "source": source["name"],
                    "count": len(result["items"]),
                    "feeds_ok": result["success_feeds"],
                    "status": "success",
                    "errors": result["errors"]
                })

            except Exception as error:

                failed_sources.append({
                    "source": source["name"],
                    "error": str(error)
                })

                print(
                    "[来源失败]",
                    source["name"],
                    error
                )

    # ======================================================
    # 去重
    # ======================================================

    seen = set()
    unique_news = []

    for item in all_news:

        url = normalize_url(item["u"])

        if not url or url in seen:
            continue

        seen.add(url)
        unique_news.append(item)

    # ======================================================
    # 排序
    # ======================================================

    unique_news.sort(
        key=lambda item: item["t"],
        reverse=True
    )

    # ======================================================
    # 输出 JSON
    # ======================================================

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

    # ======================================================
    # 统计
    # ======================================================

    print("\n===================================")
    print("新闻抓取完成")
    print("-----------------------------------")

    print("新闻总数：", len(unique_news))
    print("成功来源：", len(success_sources))
    print("失败来源：", len(failed_sources))

    print("\n语言统计：")

    for lang in ["zh", "en", "bm", "ta", "ja", "ko"]:

        count = sum(
            1 for item in unique_news
            if item["l"] == lang
        )

        print(lang, ":", count, "篇")

    print("\n地区统计：")

    for country in sorted(
        set(item["country"] for item in unique_news)
    ):

        count = sum(
            1 for item in unique_news
            if item["country"] == country
        )

        print(country, ":", count, "篇")

    # ======================================================
    # 中文新闻统计
    # ======================================================

    print("\n马来西亚中文新闻统计：")

    chinese_sources = {}

    for item in unique_news:

        if (
            item["l"] == "zh"
            and item["country"] == "my"
        ):

            name = item["source_group"]

            chinese_sources[name] = (
                chinese_sources.get(name, 0) + 1
            )

    for name, count in sorted(
        chinese_sources.items()
    ):

        print(name, ":", count, "篇")

    print("\n中文新闻标题：")

    for item in unique_news:

        if (
            item["l"] == "zh"
            and item["country"] == "my"
        ):

            print(
                item["o"],
                "|",
                item["source_type"],
                "|",
                item["h"]
            )

    print("\n已生成 news.json")
    print("===================================")


if __name__ == "__main__":
    main()
