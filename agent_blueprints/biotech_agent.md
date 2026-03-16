# Project: Micro Biotech / Pharma / Healthcare Product Tracker

## Purpose
Build a research-first tracking system for publicly traded micro-cap and small-cap biotechnology, pharmaceutical, and healthcare companies where the **primary unit of analysis is the product**, not the company.

This project is designed to monitor:
- FDA approvals
- Pending FDA decisions and anticipated catalysts
- Advisory committee meetings
- Clinical trial progression
- Post-approval obligations
- Device clearances and classifications
- Next expected research or regulatory stage

The goal is **portfolio breadth across many names**, with the expectation that some companies will fail, dilute, delay, or go to zero. The database is meant to surface a wide field of candidates so product-level wins can outweigh single-name blowups.

---

## Core Research Philosophy
1. **Track the asset, not the story.**
   - Drug, device, diagnostic, biologic, platform, or program first.
2. **Treat regulatory movement as the spine of the database.**
   - Approvals, submissions, FDA meetings, trial readouts, label expansions, confirmatory work.
3. **Separate fact from sponsor language.**
   - FDA pages, ClinicalTrials.gov, SEC filings, company press releases, conference abstracts.
4. **Assume attrition.**
   - Wide coverage matters more than being “right” on every ticker.
5. **Do not optimize for near-term profitability.**
   - The system focuses on what the product is, what stage it is in, and what evidence supports the next step.

---

## Scope
### Company universe
Publicly traded U.S. and non-U.S. companies listed on:
- Nasdaq
- NYSE
- NYSE American
- OTCQB / OTCQX / select OTC names

### Included categories
- Oncology biotech
- Rare disease biotech
- CNS / neuro
- Immunology / inflammation
- Infectious disease
- Metabolic / endocrine
- Cell therapy
- Gene therapy
- RNA / oligo / antisense
- Radiopharma
- Diagnostics
- Medical devices
- Digital therapeutics / software as a medical device when relevant
- Specialty pharma with active regulatory pipelines

### Excluded or deprioritized categories
- Pure services businesses with no meaningful proprietary product pipeline
- Providers whose story is mainly margin / roll-up / reimbursement arbitrage
- Mature large-cap pharma unless needed as comparison, partner, or acquirer context

---

## What counts as a tracked “product”
A product record may represent:
- Single drug candidate
- Combination therapy
- Biologic
- Vaccine
- Cell therapy program
- Gene therapy program
- Diagnostic test
- Class II or Class III device
- Software-driven regulated device
- New indication for an already approved product
- Reformulation / delivery system upgrade if it materially changes regulatory path

Each product should have its own timeline even if the same company has multiple programs.

---

## Research Sources
### Tier 1: Primary regulatory sources
These should be treated as highest-confidence sources.

#### Drugs / biologics
- **Drugs@FDA**
- **NDA and BLA Calendar Year Approvals**
- **This Week’s Drug Approvals**
- **Purple Book** for FDA-licensed biologics
- **Postmarketing Requirements and Commitments Database**
- **Drug Trials Snapshots**
- **Oncology / Hematologic Malignancies Approval Notifications**

#### Devices
- **510(k) database**
- **PMA database**
- **De Novo database**
- **Medical Device Databases** overview
- **Humanitarian Device Exemption (HDE)** where relevant

#### Advisory / public meeting sources
- **FDA Advisory Committee Calendar**
- Recently updated committee materials

### Tier 2: Clinical research sources
- **ClinicalTrials.gov**
- Trial registry identifiers (NCT number)
- Conference abstracts / poster archives
- Publications / preprints

### Tier 3: Company disclosure sources
- SEC 8-K, 10-Q, 10-K, 20-F, 6-K
- Investor presentations
- Press releases
- Earnings call transcripts

### Tier 4: Secondary structuring sources
- Exchange listings
- FDA labels / label repository
- Specialist pipeline pages
- Disease foundation or therapy-area calendars

---

## Key truth about “pending FDA announcements”
There is no single official FDA master page listing every pending decision date for every sponsor. In practice, the tracker should infer and classify “pending” status from combinations of:
- sponsor-disclosed PDUFA target dates,
- advisory committee scheduling,
- accepted NDA/BLA/PMA/De Novo submissions,
- rolling submission updates,
- trial completion and topline timing,
- and SEC or press release disclosures.

So the system should maintain **two separate fields**:
- `official_fda_source_present` = Yes / No
- `sponsor_disclosed_target_date` = date / blank

This prevents sponsor optimism from masquerading as official FDA publication.

---

## Status taxonomy
Use a crisp status ladder so every product can be filtered quickly.

### Regulatory status
- Discovery / Preclinical
- IND-enabling
- IND cleared / first-in-human pending
- Phase 1
- Phase 1/2
- Phase 2
- Phase 2b
- Phase 3
- Pivotal trial ongoing
- Topline data pending
- Topline data reported
- NDA/BLA submitted
- NDA/BLA accepted for review
- Priority review
- Fast Track
- Breakthrough Therapy
- Accelerated approval candidate
- Advisory committee scheduled
- FDA decision pending
- Approved
- Complete response letter / rejection
- Label expansion under review
- Postmarketing confirmatory study required
- Withdrawn / discontinued / terminated

### Device status
- Concept / prototype
- Feasibility study
- Pivotal device study
- 510(k) submitted
- 510(k) cleared
- De Novo submitted
- De Novo granted / declined
- PMA submitted
- PMA advisory panel pending
- PMA approved
- HDE granted
- Postmarket study ongoing

---

## Database design

### Table 1: `companies`
| Field | Type | Description |
|---|---|---|
| company_id | text | Unique identifier |
| ticker | text | Trading symbol |
| exchange | text | Listing venue |
| company_name | text | Legal name |
| country | text | Domicile |
| sector_bucket | text | biotech / pharma / medtech / diagnostics |
| market_cap_bucket | text | nano / micro / small / mid |
| lead_focus | text | main disease or modality focus |
| notes | text | useful background only |

### Table 2: `products`
| Field | Type | Description |
|---|---|---|
| product_id | text | Unique identifier |
| company_id | text | Link to company |
| product_name | text | Asset / candidate / device name |
| generic_or_code | text | generic name or internal code |
| modality | text | small molecule / antibody / cell therapy / device / etc. |
| disease_area | text | oncology / rare disease / etc. |
| target_or_mechanism | text | mechanism or intended function |
| lead_indication | text | primary indication |
| secondary_indications | text | list |
| regulatory_center | text | CDER / CBER / CDRH |
| active | boolean | whether still in pipeline |

### Table 3: `regulatory_events`
| Field | Type | Description |
|---|---|---|
| event_id | text | Unique identifier |
| product_id | text | Link to product |
| event_type | text | approval / submission / adcom / clearance / CRL / etc. |
| event_date | date | date of event |
| jurisdiction | text | FDA / EMA / MHRA / etc. |
| pathway | text | NDA / BLA / PMA / 510(k) / De Novo / HDE |
| designation_flags | text | priority, fast track, BTD, accelerated, orphan |
| source_type | text | FDA / SEC / PR / ClinicalTrials.gov |
| source_url | text | source link |
| source_confidence | text | primary / secondary / sponsor |
| summary | text | plain-English description |
| next_expected_step | text | what comes next |
| next_expected_date | date | if known |
| official_fda_source_present | boolean | yes/no |
| sponsor_disclosed_target_date | date | if announced by company |

### Table 4: `clinical_trials`
| Field | Type | Description |
|---|---|---|
| trial_id | text | internal id |
| product_id | text | link to product |
| nct_id | text | ClinicalTrials.gov ID |
| phase | text | phase |
| status | text | recruiting / active / completed / terminated |
| title | text | protocol title |
| indication | text | disease focus |
| primary_endpoint | text | key endpoint |
| estimated_primary_completion | date | milestone |
| estimated_study_completion | date | milestone |
| topline_expected_window | text | sponsor-estimated timing |
| results_posted | boolean | yes/no |
| source_url | text | trial link |

### Table 5: `advisory_meetings`
| Field | Type | Description |
|---|---|---|
| adcom_id | text | unique id |
| product_id | text | link to product |
| committee_name | text | committee or panel |
| meeting_date | date | scheduled date |
| topic | text | indication / question |
| materials_posted | boolean | yes/no |
| vote_outcome | text | if meeting occurred |
| source_url | text | FDA calendar or materials |

### Table 6: `postmarketing`
| Field | Type | Description |
|---|---|---|
| pmr_id | text | unique id |
| product_id | text | link to product |
| approval_context | text | accelerated / standard / supplement |
| commitment_type | text | PMR / PMC / postmarket study |
| requirement_summary | text | confirmatory burden |
| deadline | date | if listed |
| status | text | pending / fulfilled / delayed |
| source_url | text | official source |

---

## Critical views to build

### 1. Master Catalyst Calendar
Purpose: watch the whole pond for splashes before they happen.

Columns:
- date
- ticker
- company
- product
- indication
- catalyst type
- source confidence
- official vs sponsor-disclosed
- next step after outcome

### 2. Product Quality Dashboard
Purpose: compare products without drifting into balance-sheet worship.

Columns:
- modality
- phase
- evidence quality
- regulatory designations
- unmet need level
- trial size
- endpoint clarity
- prior data readout strength
- binary risk rating

### 3. Failure / Delay Log
Purpose: remember that biotech is a hallway full of trap doors.

Columns:
- ticker
- product
- event date
- failed milestone
- reason category
- safety / efficacy / CMC / enrollment / financing / strategy
- whether program still alive

### 4. Device Pathway Board
Purpose: separate 510(k) treadmill stories from true PMA / De Novo novelty.

Columns:
- device name
- sponsor
- product code
- pathway
- intended use
- submission date
- clearance / approval date
- predicate risk

### 5. Indication Heatmap
Purpose: cluster crowded spaces and neglected niches.

Examples:
- obesity
- glioblastoma
- sickle cell disease
- NASH / MASH
- Parkinson’s disease
- lupus
- sepsis diagnostics

---

## Product scoring model
This should not score the stock. It should score the **product setup**.

### Suggested fields (1 to 5 scale unless noted)
- Evidence maturity
- Endpoint clarity
- Trial design quality
- Regulatory advantage
- Unmet need severity
- Mechanism plausibility
- Manufacturing complexity risk
- Safety uncertainty
- Sponsor disclosure quality
- Near-term catalyst density

### Derived flags
- `binary_event_risk` = Low / Medium / High
- `regulatory_visibility` = Low / Medium / High
- `science_readthrough_value` = Low / Medium / High
- `crowded_indication_penalty` = Low / Medium / High
- `approval_path_complexity` = Low / Medium / High

---

## Research workflow

### Daily workflow
1. Pull FDA approvals / clearances / committee updates.
2. Check sponsor 8-Ks and major press releases for accepted filings, PDUFA dates, CRLs, topline data.
3. Update ClinicalTrials.gov records for newly completed or newly recruiting studies.
4. Refresh catalyst calendar.
5. Tag each change as primary-source confirmed or sponsor-only.

### Weekly workflow
1. Add newly listed or newly interesting micro-cap names.
2. Review all upcoming catalyst dates over the next 90 days.
3. Re-rank products by evidence maturity and regulatory visibility.
4. Audit stale records with no updates in 60 to 90 days.

### Monthly workflow
1. Reconcile product records against 10-Q / 10-K / 20-F pipeline disclosures.
2. Archive discontinued assets.
3. Rebuild indication-level coverage to avoid overconcentration.
4. Summarize regulatory wins, misses, and slips by modality.

---

## Data ingestion priorities

### Priority 1: official FDA structured pages
Use first whenever possible.
- Drugs@FDA
- approval reports
- Purple Book
- PMA / 510(k) / De Novo databases
- advisory committee calendar
- postmarketing requirements database

### Priority 2: ClinicalTrials.gov
Use to populate:
- phase
- recruitment status
- primary completion timing
- official protocol summaries

### Priority 3: SEC filings
Use to confirm:
- acceptance for review
- target action dates disclosed by sponsor
- trial delays
- discontinuations
- manufacturing issues
- partnership-related product transfers

### Priority 4: press releases
Useful but must be tagged as sponsor narrative unless corroborated.

---

## Important distinctions to preserve

### 1. Approval vs clearance vs classification
- **Drug / biologic approval** is not the same as **device clearance**.
- 510(k) usually means substantial equivalence, not necessarily novel clinical superiority.
- PMA and De Novo often deserve separate handling.

### 2. Designation vs approval
- Fast Track, Breakthrough Therapy, Orphan, Priority Review, and Accelerated Approval are not identical outcomes.
- These should be stored as flags, not mistaken for final approval.

### 3. Sponsor timeline vs official FDA publication
- A company can announce an action date or submission milestone before the FDA publishes anything visible to the public.
- Do not collapse these into one “pending” field.

### 4. Trial completion vs data release
- A trial marked complete on ClinicalTrials.gov does not guarantee topline data are public yet.

### 5. One product, many indications
- Treat each major indication path as its own sub-timeline when regulatory outcomes differ.

---

## Suggested tagging system
- `oncology`
- `rare-disease`
- `cns`
- `autoimmune`
- `infectious-disease`
- `cell-therapy`
- `gene-therapy`
- `radiopharma`
- `device`
- `diagnostic`
- `priority-review`
- `adcom`
- `pdufa-pending`
- `accelerated-approval`
- `confirmatory-study`
- `crl-history`
- `topline-soon`
- `platform-risk`
- `single-asset-company`
- `multi-asset-company`

---

## Minimum viable build

### MVP goal
Create a living database that covers **as many publicly traded product stories as possible** with enough structure to filter by:
- ticker
- product
- indication
- modality
- stage
- next catalyst
- FDA pathway
- official-vs-sponsor source quality

### MVP stack options
#### Option A: fast and practical
- Airtable or Baserow for the main database
- Python ETL scripts
- CSV snapshots for audit trail
- Notion or Obsidian for analyst notes

#### Option B: more durable
- PostgreSQL
- Python ingestion jobs
- dbt or lightweight transformation layer
- Streamlit / Retool / Metabase dashboard

#### Option C: spreadsheet-first prototype
- Google Sheets / Excel master workbook
- one sheet per table
- Apps Script or Python updater
- easiest to start, weakest for scale

---

## Recommended file structure
```text
micro-biotech-tracker/
├── README.md
├── project.md
├── data/
│   ├── raw/
│   │   ├── fda/
│   │   ├── clinicaltrials/
│   │   ├── sec/
│   │   └── press_releases/
│   ├── processed/
│   └── snapshots/
├── schema/
│   ├── companies.csv
│   ├── products.csv
│   ├── regulatory_events.csv
│   ├── clinical_trials.csv
│   ├── advisory_meetings.csv
│   └── postmarketing.csv
├── scripts/
│   ├── ingest_fda.py
│   ├── ingest_clinicaltrials.py
│   ├── ingest_sec.py
│   ├── normalize_products.py
│   └── build_catalyst_calendar.py
├── dashboards/
│   ├── catalyst_calendar.md
│   ├── failures_delays.md
│   └── indication_heatmap.md
└── notes/
    ├── company_notes/
    └── product_notes/
```

---

## Suggested CSV headers

### `companies.csv`
```csv
ticker,exchange,company_name,country,sector_bucket,market_cap_bucket,lead_focus,notes
```

### `products.csv`
```csv
product_id,ticker,product_name,generic_or_code,modality,disease_area,target_or_mechanism,lead_indication,secondary_indications,regulatory_center,active
```

### `regulatory_events.csv`
```csv
event_id,product_id,event_date,event_type,jurisdiction,pathway,designation_flags,source_type,source_url,source_confidence,official_fda_source_present,sponsor_disclosed_target_date,summary,next_expected_step,next_expected_date
```

### `clinical_trials.csv`
```csv
trial_id,product_id,nct_id,phase,status,title,indication,primary_endpoint,estimated_primary_completion,estimated_study_completion,topline_expected_window,results_posted,source_url
```

### `advisory_meetings.csv`
```csv
adcom_id,product_id,committee_name,meeting_date,topic,materials_posted,vote_outcome,source_url
```

### `postmarketing.csv`
```csv
pmr_id,product_id,approval_context,commitment_type,requirement_summary,deadline,status,source_url
```

---

## Example record logic

### Example: drug candidate
- Company: micro-cap oncology biotech
- Product: antibody-drug conjugate
- Indication: platinum-resistant ovarian cancer
- Current stage: Phase 2
- Catalyst: topline ORR data expected Q3 2026
- Next regulatory path: meeting with FDA if endpoint clears threshold
- Source confidence: sponsor press release + ClinicalTrials.gov trial record

### Example: device
- Company: micro-cap medtech
- Product: AI-enabled imaging triage device
- Pathway: De Novo
- Current status: FDA under review
- Catalyst: advisory panel possible, not guaranteed
- Next stage: grant or additional information request
- Source confidence: company 8-K + FDA device database once visible

---

## Watchlist construction strategy
To offset wipeouts, the watchlist should intentionally include:
- many single-asset companies with asymmetric catalysts,
- some multi-asset small caps with multiple shots on goal,
- different therapeutic areas,
- different regulatory pathways,
- a mix of drugs, biologics, and devices.

Suggested buckets:
- 30% oncology / hematology
- 15% rare disease
- 10% CNS
- 10% immunology
- 10% infectious disease
- 10% devices / diagnostics
- 15% flexible opportunistic bucket

This should be adjusted over time based on actual catalyst density, not theory.

---

## Quality control rules
1. Never overwrite an old catalyst without keeping history.
2. Store the exact source URL for every regulatory event.
3. Mark whether a date came from FDA, ClinicalTrials.gov, SEC, or a press release.
4. Keep company-level notes separate from product-level evidence.
5. When a product changes name, preserve aliases.
6. When a company merges or reverse-splits, keep product continuity intact.
7. Flag stale records if no source has changed in 90+ days.
8. Flag “sponsor-only” milestones until externally corroborated.

---

## Nice-to-have features
- RSS or scraping layer for FDA weekly approvals
- SEC filing parser for catalyst extraction
- Trial change detector for ClinicalTrials.gov updates
- automatic “next likely milestone” inference engine
- product similarity map by indication / mechanism / pathway
- binary-event calendar with confidence scoring
- company-to-product dependency ratio
- “science survives even if company fails” acquisition watch flag

---

## Practical first milestone
Build version 0.1 around these deliverables:
1. master `companies` table with 300 to 1,000 names
2. `products` table with at least lead asset for each company
3. `regulatory_events` table populated from official FDA sources where possible
4. `clinical_trials` table with NCT links for active lead programs
5. rolling 90-day catalyst calendar
6. clear source-confidence tags

That gets you a working radar screen instead of a biotech haunted house made of disconnected bookmarks.

---

## Public source references to wire in first
- FDA Drug Approvals and Databases: https://www.fda.gov/drugs/development-approval-process-drugs/drug-approvals-and-databases
- FDA NDA and BLA Calendar Year Approvals: https://www.fda.gov/drugs/nda-and-bla-approvals/nda-and-bla-calendar-year-approvals
- FDA Fast Track Approvals: https://www.fda.gov/drugs/nda-and-bla-approvals/fast-track-approvals
- FDA Purple Book: https://purplebooksearch.fda.gov/
- FDA Advisory Committee Calendar: https://www.fda.gov/advisory-committees/advisory-committee-calendar
- FDA Medical Device Databases: https://www.fda.gov/medical-devices/device-advice-comprehensive-regulatory-assistance/medical-device-databases
- FDA 510(k) Database: https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm
- FDA PMA Database: https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpma/pma.cfm
- FDA De Novo Database: https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/denovo.cfm
- FDA CBER Product Approval Information: https://www.fda.gov/vaccines-blood-biologics/center-biologics-evaluation-and-research-cber-product-approval-information
- ClinicalTrials.gov API: https://clinicaltrials.gov/data-api/api
- SEC EDGAR: https://www.sec.gov/edgar/search/

---

## Final note
This project is best thought of as a **regulatory intelligence map for products** moving through medicine, devices, and research, with enough breadth to survive inevitable wreckage among individual names.

The database should answer:
- What is the product?
- What problem is it trying to solve?
- Where is it in the evidence and regulatory chain?
- What is the next real milestone?
- Is that milestone supported by official sources or only sponsor language?
- If it works, what is the next stage?
- If it fails, is the product dead, delayed, or simply rerouted?
