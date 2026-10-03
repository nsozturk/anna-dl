import socket
from typing import List

# Verified active mirrors (2026 post-takedown):
# Note: annas-archive.org and annas-archive.se were seized/blocked in mid-2026.
ANNA_MIRRORS: List[str] = [
    'annas-archive.gl',  # Primary verified mirror
    'annas-archive.pk',  # Secondary mirror
    'annas-archive.gd',  # Tertiary mirror
    'annas-archive.vg'
]

LIBGEN_MIRRORS: List[str] = [
    'libgen.la',
    'libgen.gl',
    'libgen.vg',
    'libgen.is',
    'libgen.rs'
]

LIBGEN_SEARCH: str = 'http://libgen.li'
DEFAULT_OUTPUT_DIR: str = './downloads'
DEFAULT_QUEUE_FILE: str = './books_queue.json'
DEFAULT_LOG_FILE: str = './download_log.json'

HEADERS: dict = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    )
}

MIN_FILE_SIZE: int = 10000  # 10 KB cutoff for valid documents vs error pages

def enable_dns_bypass(ip: str = '104.21.34.70') -> None:
    """
    Monkey-patches socket.getaddrinfo to bypass ISP/DNS blocks for LibGen and Anna mirrors.
    Directs queries directly to Cloudflare edge IPs.
    """
    print(f"[*] DNS bypass active: resolving shadow library hosts via edge IP {ip}")
    _original_getaddrinfo = socket.getaddrinfo

    def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        if 'booksdl' in host or 'libgen' in host or 'annas-archive' in host:
            return _original_getaddrinfo(ip, port, family, type, proto, flags)
        return _original_getaddrinfo(host, port, family, type, proto, flags)

    socket.getaddrinfo = _patched_getaddrinfo
