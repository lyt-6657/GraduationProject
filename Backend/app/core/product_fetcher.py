import re
import json
import logging
import httpx
from bs4 import BeautifulSoup
from typing import Optional

logger = logging.getLogger(__name__)


class ProductFetcher:
    """从URL抓取产品信息，支持静态页面及淘宝/天猫内嵌JSON数据"""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.taobao.com/",
    }

    async def fetch(self, url: str) -> Optional[dict]:
        try:
            async with httpx.AsyncClient(
                headers=self.HEADERS, timeout=30, follow_redirects=True
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                html = resp.text
            return self._parse_html(html, url)
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP{e.response.status_code} URL={url}")
            return None
        except Exception as e:
            logger.error(f"fetch failed URL={url}: {e}")
            return None

    @staticmethod
    def _decode_unicode(s: str) -> str:
        """将字符串中的 \\uXXXX 转义序列解码为中文"""
        try:
            return s.encode('raw_unicode_escape').decode('unicode_escape')
        except Exception:
            return s

    def _parse_html(self, html: str, url: str) -> dict:
        soup = BeautifulSoup(html, "lxml")
        title = ""
        description = ""
        parameters: dict = {}

        # 1. JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, list):
                    data = data[0]
                if data.get("name") and not title:
                    title = data["name"].strip()
                if data.get("description") and not description:
                    description = data["description"].strip()
            except Exception:
                continue

        # 2. 淘宝/天猫内嵌JS数据
        if not title:
            patterns = [
                r'"title"\s*:\s*"([^"]{5,200})"',
                r'"itemTitle"\s*:\s*"([^"]{5,200})"',
                r'"name"\s*:\s*"([^"]{5,200})"',
                r'skuTitle\s*[=:]\s*["\']([^"\']{5,200})["\']]',
            ]
            for script in soup.find_all("script"):
                text = script.string or ""
                for pat in patterns:
                    m = re.search(pat, text)
                    if m:
                        candidate = self._decode_unicode(m.group(1))
                        if len(candidate) > 4:
                            title = candidate.strip()
                            break
                if title:
                    break

        # 3. 淘宝/天猫 props 规格
        if not parameters:
            for script in soup.find_all("script"):
                text = script.string or ""
                m = re.search(r'"props"\s*:\s*(\[\{.*?\}\])', text, re.DOTALL)
                if m:
                    try:
                        props = json.loads(m.group(1))
                        for p in props:
                            if isinstance(p, dict) and p.get("name") and p.get("value"):
                                parameters[p["name"]] = p["value"]
                    except Exception:
                        pass
                if parameters:
                    break

        # 4. og:title / <title>
        if not title:
            og = soup.find("meta", property="og:title")
            if og and og.get("content"):
                title = og["content"].strip()
        if not title and soup.title:
            raw = soup.title.get_text(strip=True)
            title = re.split(r'[-_|]\s*(\u5929\u732b|\u6de1\u5b9d|Tmall|Taobao|\u4eac\u4e1c|JD)', raw)[0].strip()

        # 5. og:description / meta description
        if not description:
            og_d = soup.find("meta", property="og:description")
            if og_d and og_d.get("content"):
                description = og_d["content"].strip()
        if not description:
            meta_d = soup.find("meta", attrs={"name": "description"})
            if meta_d and meta_d.get("content"):
                description = meta_d["content"].strip()
        if not description:
            description = soup.get_text(separator=" ", strip=True)[:500]

        # 6. <table> 规格
        if not parameters:
            for table in soup.find_all("table"):
                for row in table.find_all("tr"):
                    cells = row.find_all(["td", "th"])
                    if len(cells) == 2:
                        k = cells[0].get_text(strip=True)
                        v = cells[1].get_text(strip=True)
                        if k and v and len(k) < 50:
                            parameters[k] = v
                if parameters:
                    break

        # 7. <dl>/<dt>/<dd> 规格
        if not parameters:
            for dl in soup.find_all("dl"):
                for dt, dd in zip(dl.find_all("dt"), dl.find_all("dd")):
                    k = dt.get_text(strip=True)
                    v = dd.get_text(strip=True)
                    if k and v and len(k) < 50:
                        parameters[k] = v

        logger.info(f"parse done URL={url[:80]} title={title[:40]} params={len(parameters)}")
        return {
            "title": title,
            "description": description,
            "parameters": parameters,
            "competitor_features": [],
        }
