import logging
import httpx
from bs4 import BeautifulSoup
from typing import Optional

logger = logging.getLogger(__name__)


class ProductFetcher:
    """从URL抓取产品信息"""

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    async def fetch(self, url: str) -> Optional[dict]:
        """
        从给定URL抓取页面并提取产品信息
        :param url: 商品页面URL
        :return: 包含 title/description/parameters 的字典，失败返回 None
        """
        try:
            async with httpx.AsyncClient(
                headers=self.HEADERS, timeout=20, follow_redirects=True
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                html = resp.text

            return self._parse_html(html, url)
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP错误 {e.response.status_code}，URL={url}")
            return None
        except Exception as e:
            logger.error(f"抓取失败 URL={url}: {e}")
            return None

    def _parse_html(self, html: str, url: str) -> dict:
        """解析HTML，提取标题、描述、规格参数"""
        soup = BeautifulSoup(html, "lxml")

        # ---- 标题 ----
        title = ""
        # 优先 og:title
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = og_title["content"].strip()
        if not title and soup.title:
            title = soup.title.get_text(strip=True)

        # ---- 描述 ----
        description = ""
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            description = og_desc["content"].strip()
        if not description:
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and meta_desc.get("content"):
                description = meta_desc["content"].strip()
        # 兜底：取正文前500字
        if not description:
            body_text = soup.get_text(separator=" ", strip=True)
            description = body_text[:500]

        # ---- 规格参数 ----
        parameters: dict = {}
        # 尝试抓取 <table> 中的规格行
        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                if len(cells) == 2:
                    key = cells[0].get_text(strip=True)
                    val = cells[1].get_text(strip=True)
                    if key and val and len(key) < 50:
                        parameters[key] = val
            if parameters:
                break  # 找到一张有效参数表即停止

        logger.info(f"抓取成功 URL={url} title={title[:40]}")
        return {
            "title": title,
            "description": description,
            "parameters": parameters,
            "competitor_features": [],
        }
