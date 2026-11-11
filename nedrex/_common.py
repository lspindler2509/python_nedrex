import urllib.request
from typing import Any, Callable, Dict, Generator, Optional

import cachetools
import requests  # type: ignore
from requests.adapters import HTTPAdapter  # type: ignore
from urllib3.util.retry import Retry  # type: ignore

from nedrex import config
from nedrex.exceptions import ConfigError, NeDRexError

# Start - code derived from https://findwork.dev/blog/advanced-usage-python-requests-timeouts-retries-hooks/
DEFAULT_TIMEOUT = 120


class TimeoutHTTPAdapter(HTTPAdapter):  # type: ignore
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.timeout = DEFAULT_TIMEOUT
        if "timeout" in kwargs:
            self.timeout = kwargs["timeout"]
            del kwargs["timeout"]
        super().__init__(*args, **kwargs)

    # pylint: disable=arguments-differ
    def send(self, request: requests.Request, **kwargs: Any) -> requests.Response:
        timeout = kwargs.get("timeout")
        if timeout is None:
            kwargs["timeout"] = self.timeout
        return super().send(request, **kwargs)


retry_strategy = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])

http = requests.Session()
adapter = TimeoutHTTPAdapter(max_retries=retry_strategy)
http.mount("https://", adapter)
http.mount("http://", adapter)
# End - code derived from https://findwork.dev/blog/advanced-usage-python-requests-timeouts-retries-hooks/


def check_response(resp: requests.Response, return_type: str = "json") -> Any:
    if resp.status_code == 401:
        data = resp.json()
        if data["detail"] == "An API key is required to access the requested data":
            raise ConfigError("no API key set in the configuration")

    if resp.status_code in {102, 400, 422}:
        data = resp.json()
        raise NeDRexError(data["detail"])

    if resp.status_code == 404:
        method = resp.request.method if resp.request is not None else "GET"
        raise NeDRexError(f"HTTP 404 for {method} {resp.url}")

    if return_type == "json":
        data = resp.json()
    elif return_type == "text":
        data = resp.text
    else:
        raise NeDRexError(f"invalid value for return_type ({return_type!r}) in check_response")
    return data


_pagination_limit_cache: cachetools.TTLCache = cachetools.TTLCache(1, ttl=10)


@cachetools.cached(_pagination_limit_cache)
def get_pagination_limit() -> Any:
    url = f"{config.url_base}/pagination_max"
    return requests.get(url, headers={"x-api-key": config.api_key}).json()


def check_pagination_limit(limit: Optional[int], upper_limit: int) -> None:
    if limit and upper_limit < limit:
        raise NeDRexError(f"limit={limit:,} is too great (maximum is {upper_limit:,})")


def download_file(url: str, target: str) -> None:
    if not url.lower().startswith("http"):
        raise ValueError(f"{url!r} for download_file must be http(s)")

    if config.api_key is not None:
        opener = urllib.request.build_opener()
        opener.addheaders = [("x-api-key", config.api_key)]
        urllib.request.install_opener(opener)

    try:
        urllib.request.urlretrieve(url, target)  # nosec
    except urllib.error.HTTPError as err:
        if err.code == 404:
            raise NeDRexError("not found") from err
        raise NeDRexError("unexpected failure") from err


def request(path: str, method: str = "get", return_type: str = "json", **kwargs: Any) -> Any:
    """Request a route relative to the configured instance, omitting unset fields."""
    if config.url_base is None:
        raise ConfigError("API URL is not set in the config")
    for key in ("params", "json"):
        if isinstance(kwargs.get(key), dict):
            kwargs[key] = {k: v for k, v in kwargs[key].items() if v is not None}
    response = http.request(method, config.url_base + path, headers={"x-api-key": config.api_key}, **kwargs)
    return check_response(response, return_type)


def iter_pages(
    fetch: Callable[..., Any],
    page_size: Optional[int] = None,
    offset: int = 0,
    max_records: Optional[int] = None,
) -> Generator[Dict[str, Any], None, None]:
    """Iterate offset/limit pages, optionally bounding the total output."""
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise NeDRexError("offset must be a non-negative integer")
    if max_records is not None and (
        isinstance(max_records, bool) or not isinstance(max_records, int) or max_records < 0
    ):
        raise NeDRexError("max_records must be a non-negative integer")
    if max_records == 0:
        return
    upper = get_pagination_limit()
    if page_size is not None and (isinstance(page_size, bool) or not isinstance(page_size, int) or page_size <= 0):
        raise NeDRexError("page_size must be a positive integer")
    check_pagination_limit(page_size, upper)
    size = upper if page_size is None else page_size
    count = 0
    while max_records is None or count < max_records:
        limit = size if max_records is None else min(size, max_records - count)
        data = fetch(offset=offset, limit=limit)
        if not isinstance(data, list) or len(data) > limit:
            raise NeDRexError("Expected a list containing at most the requested page size")
        yield from data
        if len(data) < limit:
            return
        count += len(data)
        offset += len(data)


def check_status_factory(url_suffix: str) -> Callable[[str], Dict[str, Any]]:
    def return_func(uid: str) -> Dict[str, Any]:
        url = f"{config.url_base}{url_suffix}"
        params = {"uid": uid}
        resp = http.get(url, params=params, headers={"x-api-key": config.api_key})
        result: Dict[str, Any] = check_response(resp)
        return result

    return return_func
