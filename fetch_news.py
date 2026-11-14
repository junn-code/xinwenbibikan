import json
import re
import html
import xml.etree.ElementTree as ET

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from urllib.parse import urlsplit, urlunsplit


# ==========================================================
# NEWS COMPARE - 新闻比比看！
# Version 5.0
# ==========================================================

MAX_WORKERS = 12
TIMEOUT = 25
MAX_ARTICLES_PER_SOURCE = 200
OUTPUT_FILE = "news.json"


# ==========================================================
# RSS Feed 配置工具
# ==========================================================

def feed(url, kind="official"):
    return {
        "url": url,
        "kind": kind
    }


def source(name, country, lang, feeds=None, source_type="local"):
    return {
        "name": name,
        "country": country,
        "lang": lang,
        "source_type": source_type,
        "feeds": feeds or []
    }


# ==========================================================
# 全球新闻来源目录
#
# country:
# my        Malaysia
# singapore Singapore
# china     China
# taiwan    Taiwan
# hongkong  Hong Kong
# japan     Japan
# korea     South Korea
# usa       United States
# uk        United Kingdom
# int       International
#
# lang:
# zh / en / bm / ta / ja / ko
# ==========================================================

SOURCES = [

    # ======================================================
    # MALAYSIA - 21
    # ======================================================

    # 中文
    source("星洲日报", "my", "zh", [
        feed("https://rsshub.app/sinchew/latest", "third_party")
    ]),

    source("中国报", "my", "zh"),
    source("南洋商报", "my", "zh"),
    source("东方日报", "my", "zh"),
    source("光明日报", "my", "zh"),
    source("光华日报", "my", "zh"),
    source("当今大马中文版", "my", "zh"),

    # 英文
    source("The Star", "my", "en", [
        feed("https://www.thestar.com.my/rss/News")
    ]),

    source("New Straits Times", "my", "en", [
        feed("https://www.nst.com.my/rss")
    ]),

    source("Free Malaysia Today", "my", "en", [
        feed("https://www.freemalaysiatoday.com/feed/")
    ]),

    source("Bernama English", "my", "en", [
        feed("https://www.bernama.com/en/rssfeed.php/")
    ]),

    source("Malay Mail", "my", "en", [
        feed("https://www.malaymail.com/feed/rss/malaysia")
    ]),

    source("The Edge Malaysia", "my", "en"),

    source("Malaysiakini English", "my", "en"),

    # 马来文
    source("Berita Harian", "my", "bm", [
        feed("https://www.bharian.com.my/rss.xml")
    ]),

    source("Astro Awani", "my", "bm"),

    source("Utusan Malaysia", "my", "bm", [
        feed("https://www.utusan.com.my/feed/")
    ]),

    source("Bernama Melayu", "my", "bm", [
        feed("https://www.bernama.com/bm/rssfeed.php/")
    ]),

    source("Sinar Harian", "my", "bm"),

    # 淡米尔文
    source("Tamil Malar", "my", "ta"),

    source("Malaysia Nanban", "my", "ta"),


    # ======================================================
    # SINGAPORE - 10
    # ======================================================

    # 中文
    source("联合早报", "singapore", "zh", [
        feed("https://www.zaobao.com.sg/rss.xml")
    ]),

    source("8视界新闻", "singapore", "zh"),

    source("新明日报", "singapore", "zh"),

    source("联合晚报", "singapore", "zh"),

    # 英文
    source("CNA", "singapore", "en", [
        feed(
            "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml"
        )
    ]),

    source("The Straits Times", "singapore", "en", [
        feed("https://www.straitstimes.com/news/singapore/rss.xml")
    ]),

    source("TODAY", "singapore", "en"),

    source("Mothership", "singapore", "en"),

    # 马来文
    source("Berita Harian Singapore", "singapore", "bm"),

    # 淡米尔文
    source("Tamil Murasu", "singapore", "ta"),


    # ======================================================
    # CHINA - 10
    # ======================================================

    source("新华社", "china", "zh"),

    source("人民日报", "china", "zh"),

    source("央视新闻", "china", "zh"),

    source("中国新闻网", "china", "zh", [
        feed("https://www.chinanews.com.cn/rss/scroll-news.xml"),
        feed("https://www.chinanews.com.cn/rss/china.xml")
    ]),

    source("环球时报", "china", "zh"),

    source("澎湃新闻", "china", "zh"),

    source("中国日报 China Daily", "china", "en"),

    source("财新网", "china", "zh"),

    source("第一财经", "china", "zh"),

    source("CGTN", "china", "en"),


    # ======================================================
    # TAIWAN - 11
    # ======================================================

    source("中央通讯社 CNA", "taiwan", "zh", [
        feed("https://feeds.feedburner.com/rsscna/politics"),
        feed("https://feeds.feedburner.com/rsscna/intworld"),
        feed("https://feeds.feedburner.com/rsscna/finance")
    ]),

    source("联合新闻网 UDN", "taiwan", "zh"),

    source("自由时报", "taiwan", "zh", [
        feed("https://news.ltn.com.tw/rss/all.xml")
    ]),

    source("中国时报", "taiwan", "zh"),

    source("风传媒", "taiwan", "zh"),

    source("公视新闻网 PNN", "taiwan", "zh"),

    source("TVBS 新闻", "taiwan", "zh"),

    source("东森新闻", "taiwan", "zh"),

    source("三立新闻网", "taiwan", "zh"),

    source("经济日报", "taiwan", "zh"),

    source("科技新报 TechNews", "taiwan", "zh"),


    # ======================================================
    # HONG KONG - 10
    # ======================================================

    source("香港电台 RTHK", "hongkong", "zh"),

    source("香港01", "hongkong", "zh"),

    source("明报", "hongkong", "zh"),

    source("星岛头条", "hongkong", "zh"),

    source("Now 新闻", "hongkong", "zh"),

    source("无线新闻 TVB News", "hongkong", "zh"),

    source("South China Morning Post", "hongkong", "en"),

    source("Hong Kong Free Press", "hongkong", "en"),

    source("信报财经新闻", "hongkong", "zh"),

    source("经济日报（香港）", "hongkong", "zh"),


    # ======================================================
    # JAPAN - 10
    # ======================================================

    # 日文
    source("NHK 新闻", "japan", "ja", [
        feed("https://www.nhk.or.jp/rss/news/cat0.xml"),
        feed("https://www.nhk.or.jp/rss/news/cat1.xml")
    ]),

    source("共同通信社 Kyodo News", "japan", "ja"),

    source("朝日新闻", "japan", "ja", [
        feed("https://www.asahi.com/rss/asahi/newsheadlines.rdf")
    ]),

    source("每日新闻 Mainichi", "japan", "ja"),

    source("读卖新闻 Yomiuri", "japan", "ja"),

    source("日本经济新闻 Nikkei", "japan", "ja"),

    # 英文版仍然属于日本媒体
    source("The Japan Times", "japan", "en", [
        feed("https://www.japantimes.co.jp/feed/")
    ]),

    source("NHK World-Japan", "japan", "en"),

    source("Japan Today", "japan", "en"),

    source("Kyodo News English", "japan", "en"),


    # ======================================================
    # SOUTH KOREA - 10
    # ======================================================

    # 韩文
    source("韩联社 Yonhap News", "korea", "ko", [
        feed("https://www.yna.co.kr/rss/news.xml"),
        feed("https://www.yna.co.kr/rss/international.xml"),
        feed("https://www.yna.co.kr/rss/economy.xml")
    ]),

    source("KBS 新闻", "korea", "ko"),

    source("MBC 新闻", "korea", "ko"),

    source("SBS 新闻", "korea", "ko"),

    source("JTBC 新闻", "korea", "ko"),

    source("YTN", "korea", "ko"),

    # 英文版仍然属于韩国媒体
    source("The Korea Herald", "korea", "en", [
        feed("https://www.koreaherald.com/rss/koreaherald.xml")
    ]),

    source("The Korea Times", "korea", "en"),

    source("Yonhap News English", "korea", "en", [
        feed("https://en.yna.co.kr/RSS/news.xml")
    ]),

    source("Korea Economic Daily", "korea", "ko"),


    # ======================================================
    # UNITED STATES - 14
    # ======================================================

    source("Associated Press", "usa", "en"),

    source("The New York Times", "usa", "en", [
        feed("https://rss.nytimes.com/services/xml/rss/nyt/World.xml")
    ]),

    source("The Washington Post", "usa", "en"),

    source("The Wall Street Journal", "usa", "en"),

    source("CNN", "usa", "en"),

    source("NBC News", "usa", "en"),

    source("ABC News", "usa", "en"),

    source("CBS News", "usa", "en"),

    source("NPR", "usa", "en", [
        feed("https://feeds.npr.org/1001/rss.xml")
    ]),

    source("Bloomberg", "usa", "en"),

    source("CNBC", "usa", "en"),

    source("The Verge", "usa", "en", [
        feed("https://www.theverge.com/rss/index.xml")
    ]),

    source("TechCrunch", "usa", "en", [
        feed("https://techcrunch.com/feed/")
    ]),

    source("Fox News", "usa", "en"),


    # ======================================================
    # UNITED KINGDOM - 11
    # ======================================================

    source("BBC News", "uk", "en", [
        feed("https://feeds.bbci.co.uk/news/world/rss.xml")
    ]),

    source("The Guardian", "uk", "en", [
        feed("https://www.theguardian.com/world/rss")
    ]),

    source("Sky News", "uk", "en"),

    source("The Independent", "uk", "en"),

    source("The Telegraph", "uk", "en"),

    source("Financial Times", "uk", "en"),

    source("The Economist", "uk", "en"),

    source("ITV News", "uk", "en"),

    source("Channel 4 News", "uk", "en"),

    source("The Register", "uk", "en"),

    source("Wired UK", "uk", "en"),


    # ======================================================
    # INTERNATIONAL - 不归属美国
    # ======================================================

    source(
        "Reuters",
        "int",
        "en",
        [],
        source_type="international"
    )

]


# ==========================================================
# 基础工具
# ==========================================================

def local_name(tag):
    return tag.split("}")[-1].lower()


def clean_text(value):
    if not value:
        return ""

    value = html.unescape(str(value))

    value = re.sub(
        r"<(script|style)[^>]*>.*?</\\1>",
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

        if local_name(child.tag) == "link":

            href = child.attrib.get("href", "").strip()

            if href.startswith(("http://", "https://")):
                return href

            value = "".join(child.itertext()).strip()

            if value.startswith(("http://", "https://")):
                return value

        if local_name(child.tag) == "guid":

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
# RSS 解析
# ==========================================================

def parse_feed(raw_data, source_info, feed_info):

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
                "date"
            }
        )

        actual_publisher = get_actual_publisher(entry)

        publisher = actual_publisher or source_info["name"]

        results.append({

            "h": title,

            "u": link,

            "o": publisher,

            "t": normalize_date(published),

            "l": source_info["lang"],

            # 国家永远跟随媒体来源
            "country": source_info["country"],

            "summary": summary[:700],

            "source_type": feed_info["kind"],

            "source_group": source_info["name"]

        })

    return results


# ==========================================================
# 抓取单一媒体
# ==========================================================

def fetch_source(source_info):

    print("\n正在抓取：", source_info["name"])

    all_results = []
    errors = []
    success_feeds = 0

    if not source_info["feeds"]:

        return {
            "items": [],
            "success_feeds": 0,
            "errors": ["尚未配置可用 RSS Feed"],
            "status": "pending"
        }

    for feed_info in source_info["feeds"]:

        feed_url = feed_info["url"]

        try:

            request = Request(
                feed_url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 "
                        "(compatible; NewsCompare/5.0)"
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
                status_code = response.status

            if not raw_data:
                raise ValueError("服务器返回空内容")

            preview = raw_data[:500].lstrip().lower()

            if (
                preview.startswith(b"<!doctype html")
                or preview.startswith(b"<html")
            ):
                raise ValueError("返回 HTML，不是 RSS XML")

            results = parse_feed(
                raw_data,
                source_info,
                feed_info
            )

            if not results:
                raise ValueError("没有有效新闻")

            all_results.extend(results)
            success_feeds += 1

            print(
                "[成功]",
                source_info["name"],
                len(results),
                "篇",
                "| HTTP:",
                status_code
            )

        except Exception as error:

            errors.append(
                feed_url + " -> " + str(error)
            )

            print(
                "[失败]",
                source_info["name"],
                str(error)
            )

    all_results = all_results[:MAX_ARTICLES_PER_SOURCE]

    if all_results:
        status = "success"
    else:
        status = "failed"

    return {
        "items": all_results,
        "success_feeds": success_feeds,
        "errors": errors,
        "status": status
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
    pending_sources = []

    print("\n===================================")
    print("       新闻比比看！")
    print("       NEWS COMPARE V5.0")
    print("===================================")

    print("媒体目录数量：", len(SOURCES))

    with ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:

        futures = {
            executor.submit(fetch_source, item): item
            for item in SOURCES
        }

        for future in as_completed(futures):

            source_info = futures[future]

            try:

                result = future.result()

                all_news.extend(result["items"])

                record = {
                    "source": source_info["name"],
                    "country": source_info["country"],
                    "language": source_info["lang"],
                    "count": len(result["items"]),
                    "feeds_ok": result["success_feeds"],
                    "errors": result["errors"]
                }

                if result["status"] == "success":

                    success_sources.append(record)

                elif result["status"] == "pending":

                    pending_sources.append(record)

                else:

                    failed_sources.append(record)

            except Exception as error:

                failed_sources.append({
                    "source": source_info["name"],
                    "country": source_info["country"],
                    "language": source_info["lang"],
                    "error": str(error)
                })

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
        ),

        "sources_pending": sorted(
            pending_sources,
            key=lambda x: x["source"]
        ),

        "source_directory": [
            {
                "name": item["name"],
                "country": item["country"],
                "language": item["lang"],
                "source_type": item["source_type"],
                "feed_count": len(item["feeds"])
            }
            for item in SOURCES
        ]

    }

    with open(
        OUTPUT_FILE,
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

    print("媒体目录：", len(SOURCES))
    print("新闻总数：", len(unique_news))
    print("成功来源：", len(success_sources))
    print("失败来源：", len(failed_sources))
    print("待配置来源：", len(pending_sources))

    print("\n语言统计：")

    for lang in ["zh", "en", "bm", "ta", "ja", "ko"]:

        count = sum(
            1 for item in unique_news
            if item["l"] == lang
        )

        print(lang, ":", count, "篇")

    print("\n国家／地区统计：")

    country_names = {
        "my": "马来西亚",
        "singapore": "新加坡",
        "china": "中国",
        "taiwan": "台湾",
        "hongkong": "香港",
        "japan": "日本",
        "korea": "韩国",
        "usa": "美国",
        "uk": "英国",
        "int": "国际"
    }

    for country, name in country_names.items():

        count = sum(
            1 for item in unique_news
            if item["country"] == country
        )

        print(name, ":", count, "篇")

    print("\nJSON 文件已生成：", OUTPUT_FILE)


if __name__ == "__main__":
    main()
    