"""
src/finder/core/scraper/normalization.py
----------------------------------------
Phase D: Duplicate Normalization Hardening
canonicalize_url() ensures that tracking parameters and query strings are
stripped from apply URLs so duplicate jobs are reliably detected.
"""

import urllib.parse
import logging

log = logging.getLogger("normalization")

def canonicalize_url(url: str, platform: str) -> str:
    """
    Cleans and canonicalizes a URL to prevent duplicates caused by tracking parameters.
    """
    if not url:
        return ""

    try:
        parsed = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed.query)
        
        # Parameters to remove
        junk_params = [
            "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
            "refId", "trackingId", "session_id", "eBP", "recommendedFlavor"
        ]

        if platform == "linkedin":
            # LinkedIn specific tracking
            junk_params.extend(["currentJobId", "position", "pageNum", "f_AL"])
            # Sometimes LinkedIn job URLs are like /jobs/view/123456/
            # We want to ensure we just keep the base path without query if it identifies the job
            
        for param in junk_params:
            if param in query_params:
                del query_params[param]

        # Reconstruct URL
        clean_query = urllib.parse.urlencode(query_params, doseq=True)
        clean_url = urllib.parse.urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            clean_query,
            "" # Fragment
        ))

        # Ensure trailing slash normalization
        clean_url = clean_url.rstrip("/")
        
        return clean_url
    except Exception as exc:
        log.warning(f"Failed to canonicalize URL {url}: {exc}")
        return url
