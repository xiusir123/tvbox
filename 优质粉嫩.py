# -*- coding: utf-8 -*-
# TVBox爬虫 - 优质粉嫩鲍
# 目标: https://fcy.yzfnb8.lat/yzfnb/

import re
import json
import urllib.parse
from base.spider import Spider
from bs4 import BeautifulSoup
import requests


class Spider(Spider):
    def __init__(self):
        self.host = "https://fcy.yzfnb8.lat/cn/home/web/"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8,application/signed-exchange;v=b3",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept-Encoding": "gzip, deflate",
        })
        self.class_map = {
            "20": "熟母少妇",
            "21": "网红直播",
            "22": "自拍偷拍",
            "23": "强奸乱伦",
            "24": "高清国产",
            "25": "韩国专区",
            "26": "日本有码",
            "27": "日本无码",
            "28": "欧美情色",
            "29": "动漫卡通",
            "30": "三级伦理"
        }

    def init(self, extend=""):
        try:
            config = json.loads(extend) if extend else {}
            if config.get("proxy"):
                self.session.proxies = {"http": config["proxy"], "https": config["proxy"]}
        except:
            pass

    def getName(self):
        return "优质粉嫩鲍"

    def isVideoFormat(self, url):
        return any(text in url for text in ["m3u8", ".mp4", ".flv", ".ts"])

    def manualVideoCheck(self):
        return False

    def _fix_url(self, url):
        if not url:
            return ""
        if url.startswith("http"):
            return url
        if url.startswith("/"):
            return "https:" + url
        return urllib.parse.urljoin(self.host, url)

    def homeContent(self, filter):
        classes = []
        for tid, name in self.class_map.items():
            classes.append({"type_id": tid, "type_name": name})
        return {"class": classes}

    def homeVideoContent(self):
        return self.categoryContent("24", "1", None, {})

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg) if pg else 1
        url = f"{self.host}?cat={tid}&page={pg}"
        try:
            r = self.session.get(url, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
            items = soup.select('.video-item')
            videos = []
            for item in items:
                a_tag = item.select_one('a')
                if not a_tag:
                    continue
                href = a_tag.get('href', '')
                vid = re.search(r'/video/(\d+)', href)
                if not vid:
                    continue
                vid = vid.group(1)
                title = a_tag.get('title', '')
                img = item.select_one('img')
                pic = img.get('src', '') if img else ''
                if pic.startswith('//'):
                    pic = 'https:' + pic
                videos.append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": ''
                })
            return {"list": videos, "page": pg, "pagecount": 10, "limit": 30, "total": 300}
        except Exception as e:
            return {"list": []}

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        vid = ids[0]
        url = f"{self.host}/video/{vid}"
        try:
            r = self.session.get(url, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
            title = soup.select_one('h1')
            title = title.text.strip() if title else ''
            play_url = ''
            source = soup.select_one('source')
            if source and source.get('src'):
                play_url = source.get('src')
            if not play_url:
                video = soup.select_one('video')
                if video and video.get('src'):
                    play_url = video.get('src')
            if not play_url:
                script = soup.find('script', string=re.compile(r'var\s+player_aaaa'))
                if script:
                    m = re.search(r'var\s+player_aaaa\s*=\s*({.*?})', script.text, re.S)
                    if m:
                        try:
                            data = json.loads(m.group(1))
                            play_url = data.get('url', '')
                        except:
                            pass
            pic = ''
            img = soup.select_one('.video-cover img')
            if img:
                pic = img.get('src', '')
                if pic.startswith('//'):
                    pic = 'https:' + pic

            play_url = self._fix_url(play_url)
            return {
                "list": [{
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_content": '',
                    "vod_play_from": "优质粉嫩鲍",
                    "vod_play_url": f"第1集${play_url}" if play_url else ''
                }]
            }
        except Exception:
            return {"list": []}

    def playerContent(self, flag, id, vipFlags=None):
        if id.startswith('http'):
            return {"parse": 0, "url": id, "header": {"User-Agent": "Mozilla/5.0", "Referer": self.host}}
        return {"parse": 0, "url": id, "header": {"User-Agent": "Mozilla/5.0", "Referer": self.host}}

    def searchContent(self, key, quick=False, pg="1"):
        pg = int(pg) if pg else 1
        enc_key = urllib.parse.quote(key)
        url = f"{self.host}search?q={enc_key}&page={pg}"
        try:
            r = self.session.get(url, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
            items = soup.select('.video-item')
            videos = []
            for item in items:
                a_tag = item.select_one('a')
                if not a_tag:
                    continue
                href = a_tag.get('href', '')
                vid = re.search(r'/video/(\d+)', href)
                if not vid:
                    continue
                vid = vid.group(1)
                title = a_tag.get('title', '')
                img = item.select_one('img')
                pic = img.get('src', '') if img else ''
                if pic.startswith('//'):
                    pic = 'https:' + pic
                videos.append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": ''
                })
            return {"list": videos, "page": pg, "pagecount": 10, "limit": 30, "total": 300}
        except Exception:
            return {"list": []}

    def localProxy(self, param):
        pass
