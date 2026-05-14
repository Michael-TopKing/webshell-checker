#!/usr/bin/env python3
import argparse
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple

import requests
from tqdm import tqdm


class WebshellChecker:
    def __init__(self, args):
        self.args = args
        self.setup_logging()
        self.session = self.create_session()

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

    def load_file(self, filepath: str) -> List[str]:
        path = Path(filepath)
        if not path.exists():
            self.logger.error(f"File not found: {filepath}")
            raise FileNotFoundError(f"File not found: {filepath}")
        
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]

    def generate_urls(self, directories: List[str], filenames: List[str]) -> List[str]:
        urls = []
        for dir_path in directories:
            # 確保目錄以 / 結尾
            if not dir_path.endswith('/'):
                dir_path += '/'
            for filename in filenames:
                urls.append(dir_path + filename)
        return urls

    def check_url(self, url: str) -> Tuple[str, bool, int, int]:
        try:
            # 先用 HEAD 快速檢查，失敗再 GET
            response = self.session.head(url, timeout=self.args.timeout, allow_redirects=self.args.allow_redirect)
            
            if response.status_code == 405:  # Method Not Allowed
                response = self.session.get(url, timeout=self.args.timeout, allow_redirects=self.args.allow_redirect)

            size = len(response.content) if hasattr(response, 'content') else 0
            
            # 簡單內容過濾（避免假陽性）
            is_webshell = (
                response.status_code == 200 and
                size > 100  # 避免空頁面或錯誤頁
            )
            
            if is_webshell:
                self.logger.info(f"✅ Found: {url} | Code: {response.status_code} | Size: {size}")
            
            return url, is_webshell, response.status_code, size

        except requests.exceptions.RequestException as e:
            self.logger.debug(f"Error checking {url}: {e}")
            return url, False, 0, 0
        except Exception as e:
            self.logger.warning(f"Unexpected error with {url}: {e}")
            return url, False, 0, 0

    def run(self):
        self.logger.info("=== Webshell Checker Started ===")
        
        directories = self.load_file(self.args.directories)
        filenames = self.load_file(self.args.dictionary)
        
        self.logger.info(f"Loaded {len(directories)} directories and {len(filenames)} filenames")
        
        urls = self.generate_urls(directories, filenames)
        self.logger.info(f"Total URLs to check: {len(urls):,}")
        
        found = []
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=self.args.threads) as executor:
            future_to_url = {executor.submit(self.check_url, url): url for url in urls}
            
            for future in tqdm(as_completed(future_to_url), total=len(urls), desc="Scanning"):
                url, is_found, status, size = future.result()
                if is_found:
                    found.append(url)

        # 輸出結果
        output_path = Path(self.args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for url in found:
                f.write(url + '\n')

        elapsed = time.time() - start_time
        self.logger.info(f"=== Scan Completed in {elapsed:.1f} seconds ===")
        self.logger.info(f"Found {len(found)} webshell(s) → {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Webshell Checker - Directory + Filename Brute Forcer")
    parser.add_argument('--directories', '-d', required=True, help='Directory list file (from Script 1)')
    parser.add_argument('--dictionary', '-w', required=True, help='Webshell filename dictionary')
    parser.add_argument('--output', '-o', default='found_webshells.txt', help='Output file')
    parser.add_argument('--threads', '-t', type=int, default=20, help='Number of threads (default: 20)')
    parser.add_argument('--timeout', type=int, default=10, help='Request timeout in seconds')
    parser.add_argument('--user-agent', default='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', 
                        help='Custom User-Agent')
    parser.add_argument('--proxy', help='Proxy (e.g. http://127.0.0.1:8080)')
    parser.add_argument('--delay', type=float, default=0, help='Delay between requests (seconds)')
    parser.add_argument('--allow-redirect', action='store_true', help='Allow HTTP redirects')

    args = parser.parse_args()
    
    checker = WebshellChecker(args)
    checker.run()


if __name__ == "__main__":
    main()