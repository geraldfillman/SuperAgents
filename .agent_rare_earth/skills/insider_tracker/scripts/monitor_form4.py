"""
Insider Tracker -- Monitor Form 4
Detects and summarizes recent Form 4 insider transactions from cached SEC
filings for mining and critical minerals companies.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

RAW_SEC_DIR = Path("data/raw/sec")
OUT_DIR = Path("data/processed/rare_earth/insider_trades")


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


def check_recent_insider_trades(days: int = 14) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cutoff = datetime.now() - timedelta(days=days)
    trades = []

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

            if filing_date >= cutoff and form == "4":
                doc_url = (
                    "https://www.sec.gov/Archives/edgar/data/"
                    f"{cik}/{recent['accessionNumber'][index].replace('-', '')}/{recent['primaryDocument'][index]}"
                )
                trades.append(
                    {
                        "ticker": ticker,
                        "company_cik": cik,
                        "filing_date": filing_date_str,
                        "form_type": form,
                        "transaction_type": "UNKNOWN (Requires XML Parse)",
                        "insider_name": "UNKNOWN",
                        "transaction_value": 0.0,
                        "source_url": doc_url,
                        "source_type": "SEC",
                        "source_confidence": "secondary",
                    }
                )

    if trades:
        df = pd.DataFrame(trades)
        out_file = OUT_DIR / f"insider_trades_{datetime.now().strftime('%Y%m%d')}.csv"
        df.to_csv(out_file, index=False)
        print(f"FOUND {len(trades)} FORM 4 FILINGS IN LAST {days} DAYS")
        for trade in trades[:10]:
            print(f"[{trade['filing_date']}] {trade['ticker']} - Form 4 filed")
        if len(trades) > 10:
            print(f"... and {len(trades) - 10} more.")
    else:
        print(f"No Form 4 insider trades detected in the last {days} days.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=14, help="Lookback window in days")
    args = parser.parse_args()
    check_recent_insider_trades(days=args.days)
