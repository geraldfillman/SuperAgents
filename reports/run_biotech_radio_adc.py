import subprocess
import sys

PYTHON = sys.executable
sys.stdout.reconfigure(line_buffering=True)

COMPANIES = [
    {"ticker": "LNTH", "cik": "0001521036", "name": "Lantheus Holdings", "drug": "Pylarify"},
    {"ticker": "CATX", "cik": "0000728387", "name": "Perspective Therapeutics", "drug": "VMT-alpha-NET"},
    {"ticker": "ATNM", "cik": "0001388320", "name": "Actinium Pharmaceuticals", "drug": "Iomab-B"},
    {"ticker": "ZYME", "cik": "0001937653", "name": "Zymeworks", "drug": "Zanidatamab"},
    {"ticker": "STRO", "cik": "0001382101", "name": "Sutro Biopharma", "drug": "Luveltamab tazevibulin"},
    {"ticker": "MGNX", "cik": "0001125345", "name": "Macrogenics", "drug": "Lorigerimab"},
]


def run_step(args: list[str]) -> None:
    subprocess.run([PYTHON, *args], check=True)


print("Starting Radiopharmaceuticals and ADCs Report Generation...", flush=True)

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

print("\nRadiopharmaceuticals and ADCs Report Generation Complete!", flush=True)
