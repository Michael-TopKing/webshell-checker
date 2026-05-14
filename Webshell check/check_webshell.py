#!/usr/bin/env python3
import argparse
import logging
import time
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Tuple
from urllib.parse import urljoin, urlparse

import requests
from tqdm import tqdm
from bs4 import BeautifulSoup

# ====================== 配置 ======================
WEBSHELL_KEYWORDS = [
    # 常見 Webshell 名稱/特徵
    "wso", "filesman", "b374k", "c99", "r57", "sym", "shell", "cmd", "exec", 
    "passthru", "system", "eval", "base64_decode", "gzinflate",
    "upload files", "file manager", "command", "terminal", "backdoor",
    "webshell", "hack", "anonymous", "madspot", "priv8", "indoxploit",
    # 常見介面文字
    "execute command", "upload file", "select file", "server info",
    "php version", "uname -a", "directory", "permission"
]

RISK_SCORES = {
    "wso": 50, "filesman": 45, "b374k": 50, "c99": 40, "r57": 40,
    "upload files": 25, "file manager": 20, "execute command": 30,
    "cmd=": 15, "system(": 10, "eval(": 15, "base64_decode": 12,
}

class WebshellChecker:
    def __init__(self, args):
        self.args = args
        self.setup_logging()
        self.session = self.create_session()
        self.found = []

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)s | %(message)s',
            handlers=[
                logging.FileHandler('webshell_checker.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def create_session(self):
        session = requests.Session()
        session.headers.update({
            'User-Agent': self.args.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        })
        if self.args.proxy:
            session.proxies = {'http': self.args.proxy, 'https': self.args.proxy}
        return session

    def normalize_url(self, base_url: str, path: str) -> str:
        if not base_url.endswith('/'):
            base_url += '/'
        full_url = urljoin(base_url, path.lstrip('/'))
        # 去除重複斜線
        parsed = urlparse(full_url)
        cleaned = parsed._replace(path = '/'.join(filter(None, parsed.path.split('/'))))
        return cleaned.geturl()

    def load_file(self, filepath: str) -> List[str]:
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]

    def calculate_score(self, text: str, title: str = "") -> Tuple[int, List[str]]:
        text_lower = text.lower()
        title_lower = title.lower() if title else ""
        matched = []
        score = 0

        # Title 檢測
        for kw in ["wso", "shell", "b374k", "c99", "r57"]:
            if kw in title_lower:
                score += 35
                matched.append(f"Title:{kw}")

        # 關鍵字檢測
        for kw in WEBSHELL_KEYWORDS:
            if kw.lower() in text_lower:
                score += RISK_SCORES.get(kw.lower(), 15)
                matched.append(kw)

        # 常見 Webshell 結構特徵
        if "<textarea" in text_lower:
            score += 12
            matched.append("textarea")
        if "password" in text_lower and "type=" in text_lower:
            score += 8
            matched.append("login_form")

        return min(score, 100), matched

    def check_url(self, base_url: str, filename: str) -> Dict:
        url = self.normalize_url(base_url, filename)
        
        try:
            # 第一步：HEAD 快速過濾
            head_resp = self.session.head(url, timeout=self.args.timeout, allow_redirects=self.args.allow_redirect)
            
            if head_resp.status_code not in [200, 403, 500]:
                return {"url": url, "found": False, "score": 0}

            # 第二步：GET 獲取內容
            resp = self.session.get(url, timeout=self.args.timeout, allow_redirects=self.args.allow_redirect)
            
            if resp.status_code != 200:
                return {"url": url, "found": False, "score": 0}

            content = resp.text
            size = len(resp.content)

            # 解析 Title
            soup = BeautifulSoup(content, 'html.parser')
            title = soup.title.string.strip() if soup.title and soup.title.string else ""

            score, matched = self.calculate_score(content, title)

            result = {
                "url": url,
                "found": score >= self.args.min_score,
                "score": score,
                "status": resp.status_code,
                "size": size,
                "title": title[:100],
                "matched": matched[:10]  # 最多記錄10個
            }

            if result["found"]:
                self.logger.info(f"🚨 WEBSHELL FOUND! Score: {score} | {url}")
                print(f"\033[1;32m[+] WEBSHELL [{score}] → {url}\033[0m")

            return result

        except requests.exceptions.RequestException:
            return {"url": url, "found": False, "score": 0}
        except Exception as e:
            self.logger.debug(f"Error {url}: {e}")
            return {"url": url, "found": False, "score": 0}

    def run(self):
        self.logger.info("=== Advanced Webshell Detection Started ===")
        
        directories = self.load_file(self.args.directories)
        filenames = self.load_file(self.args.dictionary)

        self.logger.info(f"Directories: {len(directories)} | Filenames: {len(filenames)}")

        # 生成唯一 URL
        tasks = []
        seen = set()
        for d in directories:
            for f in filenames:
                url = self.normalize_url(d, f)
                if url not in seen:
                    seen.add(url)
                    tasks.append((d, f))

        self.logger.info(f"Total unique URLs to check: {len(tasks):,}")

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=self.args.threads) as executor:
            future_to_task = {executor.submit(self.check_url, d, f): (d, f) for d, f in tasks}
            
            for future in tqdm(as_completed(future_to_task), total=len(tasks), desc="Webshell Detection"):
                result = future.result()
                if result["found"]:
                    self.found.append(result)

        # 輸出結果
        output_path = Path(self.args.output)
        with open(output_path, 'w', encoding='utf-8') as f:
            for item in self.found:
                f.write(f"{item['url']}|score={item['score']}|title={item.get('title','')}\n")

        elapsed = time.time() - start_time
        self.logger.info(f"Scan completed in {elapsed:.1f}s | Found {len(self.found)} Webshell(s)")


def main():
    parser = argparse.ArgumentParser(description="Advanced Webshell Detection Framework")
    parser.add_argument('--directories', '-d', required=True, help='Directory list file')
    parser.add_argument('--dictionary', '-w', required=True, help='Webshell filename dictionary')
    parser.add_argument('--output', '-o', default='found_webshells.txt')
    parser.add_argument('--threads', '-t', type=int, default=25)
    parser.add_argument('--timeout', type=int, default=10)
    parser.add_argument('--min-score', type=int, default=45, help='Minimum risk score to report (default:45)')
    parser.add_argument('--user-agent', default='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    parser.add_argument('--proxy')
    parser.add_argument('--allow-redirect', action='store_true')

    args = parser.parse_args()
    
    checker = WebshellChecker(args)
    checker.run()


if __name__ == "__main__":
    main()
