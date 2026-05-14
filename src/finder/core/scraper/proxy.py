"""
src/finder/core/scraper/proxy.py
--------------------------------
Final Hardening: Lightweight Proxy Abstraction
Future-proof architecture for proxy support, disabled by default.
"""

import os
import logging
from typing import Optional

log = logging.getLogger("proxy")

class ProxyProvider:
    @staticmethod
    def get_proxy() -> Optional[dict]:
        """
        Returns a Playwright-compatible proxy dictionary if configured.
        Returns None to use the local connection.
        """
        proxy_url = os.getenv("PROXY_URL")
        
        if proxy_url:
            log.info("Using configured proxy server.")
            # Expected format: "http://user:pass@proxy.server.com:8080"
            return {"server": proxy_url}
            
        return None
