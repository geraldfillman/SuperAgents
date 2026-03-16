import subprocess
import sys

PYTHON = sys.executable
sys.stdout.reconfigure(line_buffering=True)

COMPANIES = [
    {"ticker": "KYMR", "cik": "0001815442", "name": "Kymera", "drug": "KT-474"},
    {"ticker": "NRIX", "cik": "0001549595", "name": "Nurix", "drug": "NX-2127"},
    {"ticker": "GLUE", "cik": "0001826457", "name": "Monte Rosa", "drug": "MRT-2359"},
    {"ticker": "ARVN", "cik": "0001655759", "name": "Arvinas", "drug": "Vepdegestrant"},
    {"ticker": "CCCC", "cik": "0001662579", "name": "C4 Therapeutics", "drug": "CFT7455"},
]


def run_step(args: list[str]) -> None:
    subprocess.run([PYTHON, *args], check=True)


print("Starting Targeted Protein Degradation (TPD) Report Generation...", flush=True)

for company in COMPANIES:
    print(f"\n--- Processing {company['ticker']} ({company['name']}) ---", flush=True)

    print("1. Fetching SEC Filings...", flush=True)
    run_step([".agent_biotech/skills/sec_filings_parser/scripts/search_edgar.py", "--cik", company["cik"]])

    print("2. Fetching Clinical Trials...", flush=True)
    run_step([".agent_biotech/skills/clinicaltrials_scraper/scripts/fetch_trials.py", "--sponsor", company["name"]])

print("\n--- Running Global Extractors ---", flush=True)
print("3. Extracting SEC Catalysts...", flush=True)
run_step([".agent_biotech/skills/sec_filings_parser/scripts/extract_catalysts.py", "--batch"])

print("4. Updating Catalyst Calendar...", flush=True)
run_step([".agent_biotech/skills/catalyst_calendar/scripts/build_calendar.py", "--days", "90"])

print("5. Processing Financial Runways...", flush=True)
run_step([".agent_biotech/skills/financial_monitor/scripts/fetch_financials.py", "--batch"])
run_step([".agent_biotech/skills/financial_monitor/scripts/flag_offerings.py", "--days", "30"])

print("6. Checking Insider Trades...", flush=True)
run_step([".agent_biotech/skills/insider_tracker/scripts/monitor_form4.py", "--days", "60"])

print("7. Scraping Conferences for key drugs...", flush=True)
drugs = ",".join([company["drug"] for company in COMPANIES])
run_step([".agent_biotech/skills/conference_scraper/scripts/scrape_abstracts.py", "--keywords", drugs])

print("8. Checking Orange Book for Exclusivity...", flush=True)
for company in COMPANIES:
    run_step([".agent_biotech/skills/orange_book_watcher/scripts/fetch_patents.py", "--active-ingredient", company["drug"]])

print("\nTPD Report Generation Complete!", flush=True)
