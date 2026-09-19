import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def get_http_session():
    session = requests.Session()

    retries = Retry(
        total=4,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504]
    )

    adapter = HTTPAdapter(max_retries=retries)

    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session

HTTP = get_http_session()
