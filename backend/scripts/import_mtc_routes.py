"""Download Chennai MTC route and stop information from the official website.

Official source:
https://mtcbus.tn.gov.in/Home/routewiseinfo

The script creates:

backend/data/mtc_routes.json
backend/data/mtc_stops.json

Run from the backend folder:

python scripts/import_mtc_routes.py
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any
import urllib3
import requests
from bs4 import BeautifulSoup
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

urllib3.disable_warnings(
    urllib3.exceptions.InsecureRequestWarning
)

BASE_URL = "https://mtcbus.tn.gov.in"
ROUTE_INFO_URL = f"{BASE_URL}/Home/routewiseinfo"

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "data"

ROUTES_OUTPUT = DATA_DIR / "mtc_routes.json"
STOPS_OUTPUT = DATA_DIR / "mtc_stops.json"

REQUEST_DELAY_SECONDS = 0.25
REQUEST_TIMEOUT_SECONDS = 30


def clean_text(value: str) -> str:
    """Normalize whitespace while preserving the official stop name."""
    return re.sub(r"\s+", " ", value or "").strip()


def build_session() -> Session:
    """Create a requests session with retries and browser-like headers."""
    session = requests.Session()

    retries = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "POST"}),
    )

    adapter = HTTPAdapter(max_retries=retries)

    session.mount("https://", adapter)
    session.mount("http://", adapter)

    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/150.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": BASE_URL,
        }
    )

    return session


def get_page(session: Session, url: str, **kwargs: Any) -> requests.Response:
    """Request an MTC page and raise a clear error when it fails."""
    response = session.get(
        url,
        timeout=REQUEST_TIMEOUT_SECONDS,
        verify=False,
        **kwargs,
    )

    response.raise_for_status()
    return response


def find_route_select(soup: BeautifulSoup):
    """Locate the route-number dropdown."""
    select = soup.find("select", attrs={"name": "selroute"})

    if select:
        return select

    for candidate in soup.find_all("select"):
        option_values = [
            clean_text(option.get("value", ""))
            for option in candidate.find_all("option")
        ]

        useful_values = [
            value
            for value in option_values
            if value and value.lower() not in {"select", "0", "-1"}
        ]

        if useful_values:
            return candidate

    return None


def extract_route_numbers(html: str) -> list[str]:
    """Extract all route numbers from the official route dropdown."""
    soup = BeautifulSoup(html, "lxml")
    select = find_route_select(soup)

    if not select:
        raise RuntimeError(
            "The route dropdown could not be found on the MTC page. "
            "The official website structure may have changed."
        )

    route_numbers: list[str] = []

    for option in select.find_all("option"):
        value = clean_text(option.get("value", ""))
        label = clean_text(option.get_text(" ", strip=True))

        route_number = value or label

        if not route_number:
            continue

        if route_number.casefold() in {
            "select",
            "select route",
            "--select--",
            "0",
            "-1",
        }:
            continue

        route_numbers.append(route_number)

    return sorted(
        set(route_numbers),
        key=lambda route: route.casefold(),
    )


def extract_csrf(html: str) -> tuple[str | None, str | None]:
    """Extract the CodeIgniter CSRF field name and token."""
    soup = BeautifulSoup(html, "lxml")

    token_input = soup.find(
        "input",
        attrs={
            "type": "hidden",
            "name": re.compile("csrf", re.IGNORECASE),
        },
    )

    if not token_input:
        return None, None

    name = token_input.get("name")
    value = token_input.get("value")

    if not name or not value:
        return None, None

    return clean_text(name), clean_text(value)


def extract_numbered_stops(soup: BeautifulSoup) -> list[str]:
    """Extract an ordered stop list from numbered list items or rows."""
    candidates: list[tuple[int, str]] = []

    for element in soup.find_all(["li", "tr", "p", "div"]):
        text = clean_text(element.get_text(" ", strip=True))

        match = re.fullmatch(r"(\d+)\s+(.+)", text)

        if not match:
            continue

        stage_number = int(match.group(1))
        stop_name = clean_text(match.group(2))

        if not stop_name:
            continue

        if stop_name.casefold().startswith(
            (
                "route no",
                "updated on",
                "customer care",
                "phone",
            )
        ):
            continue

        candidates.append((stage_number, stop_name))

    if not candidates:
        return []

    unique: dict[int, str] = {}

    for stage_number, stop_name in candidates:
        unique.setdefault(stage_number, stop_name)

    ordered = [
        unique[number]
        for number in sorted(unique)
    ]

    if len(ordered) < 2:
        return []

    return ordered


def find_label_value(
    soup: BeautifulSoup,
    label_pattern: str,
) -> str | None:
    """Find a value located near a heading such as Origin or Destination."""
    pattern = re.compile(label_pattern, re.IGNORECASE)

    label = soup.find(
        lambda tag: (
            tag.name in {"h1", "h2", "h3", "h4", "h5", "h6", "th", "td", "div", "span", "p"}
            and pattern.fullmatch(clean_text(tag.get_text(" ", strip=True)))
        )
    )

    if not label:
        return None

    next_element = label.find_next(
        lambda tag: (
            tag.name in {"h1", "h2", "h3", "h4", "h5", "h6", "td", "div", "span", "p"}
            and clean_text(tag.get_text(" ", strip=True))
            and not pattern.fullmatch(
                clean_text(tag.get_text(" ", strip=True))
            )
        )
    )

    if not next_element:
        return None

    return clean_text(next_element.get_text(" ", strip=True))


def parse_route_page(
    html: str,
    requested_route_number: str,
) -> dict[str, Any] | None:
    """Parse one official MTC route result page."""
    soup = BeautifulSoup(html, "lxml")

    page_text = clean_text(soup.get_text(" ", strip=True))

    if "No direct service" in page_text:
        return None

    stops = extract_numbered_stops(soup)

    if len(stops) < 2:
        return None

    route_number = (
        find_label_value(soup, r"Route\s*No\.?")
        or requested_route_number
    )

    origin = (
        find_label_value(soup, r"Origin")
        or stops[0]
    )

    destination = (
        find_label_value(soup, r"Destination")
        or stops[-1]
    )

    return {
        "route_number": clean_text(route_number),
        "origin": clean_text(origin),
        "destination": clean_text(destination),
        "stops": stops,
        "source_url": ROUTE_INFO_URL,
        "source": "Metropolitan Transport Corporation Chennai",
    }


def request_route_page(
    session: Session,
    route_number: str,
    csrf_name: str | None,
    csrf_value: str | None,
) -> requests.Response:
    """Request one route result using the official query parameters."""
    params: dict[str, str] = {
        "selroute": route_number,
        "submit": "",
    }

    if csrf_name and csrf_value:
        params[csrf_name] = csrf_value

    return get_page(
        session,
        ROUTE_INFO_URL,
        params=params,
    )


def write_json(path: Path, data: Any) -> None:
    """Write readable UTF-8 JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def main() -> None:
    print("=" * 70)
    print("BUSMATE — OFFICIAL CHENNAI MTC ROUTE IMPORTER")
    print("=" * 70)
    print(f"Source: {ROUTE_INFO_URL}")

    session = build_session()

    print("\n[1/4] Opening the official MTC route-information page...")

    landing_response = get_page(session, ROUTE_INFO_URL)
    landing_html = landing_response.text

    csrf_name, csrf_value = extract_csrf(landing_html)

    if csrf_name:
        print(f"[INFO] CSRF field found: {csrf_name}")
    else:
        print("[INFO] No CSRF field was required on the initial page.")

    print("\n[2/4] Reading route numbers...")

    route_numbers = extract_route_numbers(landing_html)

    if not route_numbers:
        raise RuntimeError(
            "No MTC route numbers were found."
        )

    print(
        f"[SUCCESS] Found {len(route_numbers)} route numbers."
    )

    imported_routes: list[dict[str, Any]] = []
    failed_routes: list[str] = []

    print("\n[3/4] Downloading route stages...")

    for index, route_number in enumerate(
        route_numbers,
        start=1,
    ):
        try:
            response = request_route_page(
                session=session,
                route_number=route_number,
                csrf_name=csrf_name,
                csrf_value=csrf_value,
            )

            parsed_route = parse_route_page(
                response.text,
                route_number,
            )

            if parsed_route:
                imported_routes.append(parsed_route)

                print(
                    f"[{index}/{len(route_numbers)}] "
                    f"{parsed_route['route_number']}: "
                    f"{parsed_route['origin']} → "
                    f"{parsed_route['destination']} "
                    f"({len(parsed_route['stops'])} stops)"
                )
            else:
                failed_routes.append(route_number)

                print(
                    f"[{index}/{len(route_numbers)}] "
                    f"{route_number}: no stages found"
                )

        except requests.RequestException as exc:
            failed_routes.append(route_number)

            print(
                f"[{index}/{len(route_numbers)}] "
                f"{route_number}: request failed — {exc}"
            )

        except Exception as exc:
            failed_routes.append(route_number)

            print(
                f"[{index}/{len(route_numbers)}] "
                f"{route_number}: parse failed — {exc}"
            )

        time.sleep(REQUEST_DELAY_SECONDS)

    unique_stops = sorted(
        {
            stop
            for route in imported_routes
            for stop in route["stops"]
        },
        key=lambda stop: stop.casefold(),
    )

    output = {
        "source": "Official Metropolitan Transport Corporation Chennai website",
        "source_url": ROUTE_INFO_URL,
        "route_count": len(imported_routes),
        "stop_count": len(unique_stops),
        "failed_route_count": len(failed_routes),
        "failed_routes": failed_routes,
        "routes": imported_routes,
    }

    print("\n[4/4] Saving BusMate route data...")

    write_json(ROUTES_OUTPUT, output)
    write_json(STOPS_OUTPUT, unique_stops)

    print("\n" + "=" * 70)
    print("IMPORT COMPLETE")
    print("=" * 70)
    print(f"Routes imported : {len(imported_routes)}")
    print(f"Unique stops    : {len(unique_stops)}")
    print(f"Failed routes   : {len(failed_routes)}")
    print(f"Routes file     : {ROUTES_OUTPUT}")
    print(f"Stops file      : {STOPS_OUTPUT}")

    if failed_routes:
        print(
            "\nSome routes could not be read. "
            "Their route numbers are recorded in mtc_routes.json."
        )


if __name__ == "__main__":
    main()