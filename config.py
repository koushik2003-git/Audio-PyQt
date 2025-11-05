# config.py — configure your API root here
BASE_URL = "http://localhost:8000"  # change to your real backend base URL

def url(path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if not path.startswith("/"):
        path = "/" + path
    return BASE_URL.rstrip("/") + path
