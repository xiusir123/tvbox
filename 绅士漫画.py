# -*- coding: utf-8 -*-
# 无聊自制 · 紳士漫畫 (修复列表解析)
# 站点: https://www.wnacg.com/

import sys
import re
import json
import requests
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def getName(self):
        return "紳士漫畫"

    def init(self, extend=""):
        self.host = "https://www.wnacg.com"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": self.host + "/",
        })
        self.classes = [
            {"type_id": "index", "type_name": "推荐"},
            {"type_id": "albums", "type_name": "更新"},
            {"type_id": "ranking", "type_name": "排行"},
            {"type_id": "cate_5", "type_name": "同人志"},
            {"type_id": "cate_6", "type_name": "單行本"},
            {"type_id": "cate_7", "type_name": "雜誌·短篇"},
            {"type_id": "cate_19", "type_name": "韓漫"},
        ]

    def _fetch(self, url):
        try:
            r = self.session.get(url, timeout=15)
            r.encoding = "utf-8"
            return r.text
        except Exception as e:
            print(f"[绅士漫画] 请求失败: {url} -> {e}")
            return ""

    def _fix_url(self, url):
        if not url:
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.host + url
        return url

    def _clean(self, text):
        if not text:
            return ""
        return re.sub(r"\s+", " ", text.strip())

    # ---------- 修复列表解析 ----------
    def _parse_comic_list(self, html):
        videos = []
        if not html:
            return videos

        soup = BeautifulSoup(html, "html.parser")
        seen = set()

        # 策略1：查找 ul.col_3_2 下的 li
        container = soup.select_one("ul.col_3_2")
        if container:
            items = container.select("li")
        else:
            # 策略2：查找 .gallary_list 或 .photo_ullist
            container = soup.select_one(".gallary_list, .photo_ullist")
            if container:
                items = container.select("li")
            else:
                # 策略3：直接找包含 ImgA 的 li
                items = soup.select("li:has(a.ImgA)")

        for li in items:
            try:
                a_img = li.find("a", class_="ImgA")
                if not a_img:
                    continue
                href = a_img.get("href")
                if not href:
                    continue
                # 只保留漫画链接
                if "photos-index-aid-" not in href and "albums-index-aid-" not in href:
                    continue

                # 标题（a.txtA 或 a[title]）
                a_title = li.find("a", class_="txtA")
                if not a_title:
                    a_title = li.find("a", title=True)
                if not a_title:
                    continue
                title = self._clean(a_title.get("title") or a_title.get_text(strip=True) or "")

                if not title:
                    continue

                # 封面图（支持 data-original 和 src）
                img = a_img.find("img")
                pic = ""
                if img:
                    pic = img.get("data-original") or img.get("src") or ""
                    # 过滤掉占位图
                    if "loading" in pic or "placeholder" in pic:
                        pic = img.get("data-original") or ""
                pic = self._fix_url(pic)

                # 备注（info 或 span）
                info = li.find("span", class_="info")
                remark = self._clean(info.get_text(strip=True)) if info else ""
                if not remark:
                    # 尝试获取集数
                    count_span = li.find("span", class_="count")
                    if count_span:
                        remark = self._clean(count_span.get_text(strip=True))

                # 去重
                if href in seen:
                    continue
                seen.add(href)

                videos.append({
                    "vod_id": href,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remark,
                })
            except Exception as e:
                print(f"[绅士漫画] 解析卡片失败: {e}")
                continue

        # 如果还没匹配到，用正则兜底
        if not videos:
            videos = self._parse_by_regex(html)

        return videos

    def _parse_by_regex(self, html):
        """正则兜底解析"""
        videos = []
        seen = set()

        # 匹配卡片块
        pattern = r'<li[^>]*>.*?<a[^>]+class="ImgA"[^>]+href="([^"]+)"[^>]*>.*?<img[^>]+(?:data-original|src)="([^"]+)"[^>]*>.*?</a>.*?<a[^>]+class="txtA"[^>]+(?:title="([^"]+)")?[^>]*>([^<]*)</a>.*?<span[^>]+class="info"[^>]*>([^<]*)</span>'
        for m in re.finditer(pattern, html, re.S):
            href = m.group(1)
            pic = m.group(2)
            title = m.group(3) or self._clean(m.group(4)) or ""
            remark = self._clean(m.group(5)) or ""

            if not href or "photos-index-aid-" not in href:
                continue
            if href in seen:
                continue
            seen.add(href)

            pic = self._fix_url(pic)
            videos.append({
                "vod_id": href,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": remark,
            })

        return videos

    def _get_pagination(self, html):
        soup = BeautifulSoup(html, "html.parser")
        max_page = 1
        for a in soup.select(".pagination a, .page a"):
            href = a.get("href", "")
            m = re.search(r"page[_-]?(\d+)", href)
            if m:
                num = int(m.group(1))
                if num > max_page:
                    max_page = num
        next_btn = soup.select_one(".pagination .next, .page .next")
        if next_btn and max_page == 1:
            max_page = 2
        return max_page

    # ---------- 分类 ----------
    def homeContent(self, filter=False):
        return {"class": self.classes}

    def homeVideoContent(self):
        html = self._fetch(self.host + "/")
        if not html:
            return {"list": []}
        videos = self._parse_comic_list(html)
        return {"list": videos[:20]}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        pg = int(pg) if pg else 1
        if tid == "index":
            url = self.host + "/"
        elif tid == "albums":
            url = self.host + "/albums.html"
        elif tid == "ranking":
            url = self.host + "/albums-favorite_ranking.html"
        elif tid.startswith("cate_"):
            cate_id = tid.replace("cate_", "")
            url = self.host + f"/albums-index-cate-{cate_id}.html"
        else:
            return {"list": [], "page": pg, "pagecount": 1, "limit": 0, "total": 0}

        if pg > 1:
            if "?" in url:
                url += f"&page={pg}"
            else:
                if ".html" in url:
                    url = url.replace(".html", f".html?page={pg}")
                else:
                    url += f"?page={pg}"

        html = self._fetch(url)
        if not html:
            return {"list": [], "page": pg, "pagecount": 1, "limit": 0, "total": 0}

        videos = self._parse_comic_list(html)
        pagecount = self._get_pagination(html) or (pg + 1 if len(videos) >= 20 else pg)
        return {
            "list": videos,
            "page": pg,
            "pagecount": max(pagecount, pg),
            "limit": len(videos),
            "total": max(pagecount, pg) * 20,
        }

    # ---------- 详情 ----------
    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, list) else ids
        if not vid.startswith("http"):
            if not vid.startswith("/photos-index-aid-"):
                vid = f"/photos-index-aid-{vid}.html"
            url = self.host + vid
        else:
            url = vid

        html = self._fetch(url)
        if not html:
            return {"list": []}

        soup = BeautifulSoup(html, "html.parser")

        title = ""
        h1 = soup.find("h1")
        if h1:
            title = self._clean(h1.get_text(strip=True))
        if not title:
            og_title = soup.find("meta", property="og:title")
            if og_title:
                title = self._clean(og_title.get("content", ""))

        # 提取所有图片
        img_list = []
        # 方式1: ul.photo_ullist
        container = soup.select_one("ul.photo_ullist")
        if container:
            for img in container.find_all("img"):
                src = img.get("src") or img.get("data-src") or ""
                if src:
                    img_list.append(self._fix_url(src))

        # 方式2: 直接找图片
        if not img_list:
            for img in soup.find_all("img"):
                src = img.get("src") or img.get("data-src") or ""
                if src and "logo" not in src and "loading" not in src and "icon" not in src:
                    if src.startswith("/themes/") or src.startswith("//t4.qy0.ru/data/t/"):
                        img_list.append(self._fix_url(src))

        pic = img_list[0] if img_list else ""

        desc = ""
        desc_tag = soup.find("meta", attrs={"name": "description"})
        if desc_tag:
            desc = desc_tag.get("content", "")

        if img_list:
            play_url = "pics://" + "&&".join(img_list)
        else:
            play_url = url

        vod = {
            "vod_id": vid,
            "vod_name": title or "未知漫画",
            "vod_pic": pic,
            "vod_content": desc,
            "vod_play_from": "紳士漫畫",
            "vod_play_url": f"全集${play_url}",
        }
        return {"list": [vod]}

    # ---------- 播放 ----------
    def playerContent(self, flag, id, vipFlags=None):
        if id and id.startswith("pics://"):
            return {"parse": 0, "playUrl": "", "url": id, "header": ""}
        if id and re.search(r"\.(jpg|png|webp)", id, re.I):
            return {"parse": 0, "playUrl": "", "url": f"pics://{id}", "header": ""}
        return {"parse": 1, "url": id, "header": {"Referer": self.host + "/"}}

    # ---------- 搜索 ----------
    def searchContent(self, key, quick=False, pg="1"):
        pg = int(pg) if pg else 1
        enc_key = quote(key)
        url = self.host + f"/q/?q={enc_key}&page={pg}"
        html = self._fetch(url)
        if not html:
            return {"list": [], "page": pg, "pagecount": 1, "limit": 0, "total": 0}
        videos = self._parse_comic_list(html)
        pagecount = self._get_pagination(html) or (pg + 1 if len(videos) >= 20 else pg)
        return {
            "list": videos,
            "page": pg,
            "pagecount": max(pagecount, pg),
            "limit": len(videos),
            "total": max(pagecount, pg) * 20,
        }

    def isVideoFormat(self, url):
        return url and (url.startswith("pics://") or re.search(r"\.(jpg|png|webp)", url, re.I))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        if self.session:
            self.session.close()

    def localProxy(self, param):
        return None