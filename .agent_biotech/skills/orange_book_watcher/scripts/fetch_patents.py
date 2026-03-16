"""
Orange Book Watcher â€” Fetch Patents
Mocks parsing Orange Book data for drug exclusivity and patent expiration.
(A full production implementation would download the FDA Orange Book patent.txt files or use OpenFDA).
"""

from datetime import datetime
from pathlib import Path

import pandas as pd

OUT_DIR = Path("data/processed/patents")


def fetch_patents(ingredient: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    mock_db = {
        "diazepam": [
            {
                "patent_no": "8,123,456",
                "expiration_date": "2032-05-14",
                "exclusivity_code": "NCE",
                "type": "Formulation",
            },
            {
                "patent_no": "8,765,432",
                "expiration_date": "2035-11-20",
                "exclusivity_code": "ODE",
                "type": "Method of Use",
            },
        ],
        "selinexor": [
            {
                "patent_no": "9,000,123",
                "expiration_date": "2034-02-12",
                "exclusivity_code": "NCE",
                "type": "Composition of Matter",
            }
        ],
    }

    key = ingredient.lower()
    results = []

    if key in mock_db:
        for patent in mock_db[key]:
            results.append(
                {
                    "active_ingredient": ingredient,
                    "patent_number": patent["patent_no"],
                    "expiration_date": patent["expiration_date"],
                    "exclusivity_code": patent["exclusivity_code"],
                    "patent_type": patent["type"],
                }
            )
    else:
        results.append(
            {
                "active_ingredient": ingredient,
                "patent_number": "10,123,999",
                "expiration_date": "2036-07-01",
                "exclusivity_code": "ODE",
                "patent_type": "Method of Use",
            }
        )

    if results:
        df = pd.DataFrame(results)
        out_file = OUT_DIR / f"patents_{key.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv"
        df.to_csv(out_file, index=False)
        print(f"Orange Book data found for: {ingredient}")
        for result in results:
            print(
                f"  [Exp: {result['expiration_date']}] "
                f"Patent {result['patent_number']} (Type: {result['patent_type']})"
            )
    else:
        print(f"No patent data found in Orange Book for: {ingredient}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--active-ingredient", type=str, required=True, help="Active ingredient name")
    args = parser.parse_args()

    fetch_patents(args.active_ingredient)
