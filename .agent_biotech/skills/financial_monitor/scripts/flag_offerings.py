"""
Financial Monitor â€” Flag Offerings
Monitors recent filings for S-3 (Shelf Registrations) and 424B5 (Prospectus Supplements)
which indicate immediate or pending equity dilution.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

RAW_SEC_DIR = Path("data/raw/sec")


def normalize_cik(cik: str) -> str:
    """Return the unpadded CIK used in SEC archive URLs."""
    digits = "".join(ch for ch in str(cik) if ch.isdigit())
    if not digits:
        raise ValueError("CIK must contain at least one digit")
    return digits.lstrip("0") or "0"


def latest_sec_cache_files() -> list[Path]:
    """Return only the most recent SEC submissions cache file for each CIK."""
    latest_by_cik: dict[str, Path] = {}
    for path in RAW_SEC_DIR.glob("filings_*.json"):
        cik = normalize_cik(path.stem.split("_")[1])
        previous = latest_by_cik.get(cik)
        if previous is None or path.stat().st_mtime > previous.stat().st_mtime:
            latest_by_cik[cik] = path
    return sorted(latest_by_cik.values(), key=lambda path: path.name)


def detect_offerings(days: int = 7) -> None:
    cutoff = datetime.now() - timedelta(days=days)
    found_offerings = []

    for path in latest_sec_cache_files():
        data = json.loads(path.read_text())
        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])

        ticker = ",".join(data.get("tickers", []))
        cik = normalize_cik(str(data.get("cik", "")))

        for index, form in enumerate(forms):
            filing_date_str = dates[index]
            try:
                filing_date = datetime.strptime(filing_date_str, "%Y-%m-%d")
            except ValueError:
                continue

            if filing_date < cutoff:
                continue

            if form in ["S-3", "S-3ASR", "424B5"]:
                found_offerings.append(
                    {
                        "ticker": ticker,
                        "form": form,
                        "date": filing_date_str,
                        "type": "ATM or Secondary Offering" if form == "424B5" else "Shelf Registration",
                        "url": (
                            "https://www.sec.gov/Archives/edgar/data/"
                            f"{cik}/{recent['accessionNumber'][index].replace('-', '')}/{recent['primaryDocument'][index]}"
                        ),
                    }
                )

    if found_offerings:
        print(f"FOUND {len(found_offerings)} DILUTION EVENTS IN LAST {days} DAYS")
        for offering in found_offerings:
            print(f"[{offering['date']}] {offering['ticker']} - {offering['form']} ({offering['type']})")
    else:
        print(f"No dilution events (S-3, 424B5) detected in the last {days} days.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7, help="Lookback window in days")
    args = parser.parse_args()
    detect_offerings(days=args.days)
