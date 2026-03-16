"""
AACT fallback helpers for ClinicalTrials data.
Builds a local SQLite index from the downloaded AACT flatfile snapshot and
queries it when the live ClinicalTrials.gov API is unavailable.
"""

from __future__ import annotations

import csv
import io
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile

RAW_DIR = Path("data/raw/clinicaltrials")
AACT_DIR = RAW_DIR / "aact"
AACT_INDEX_PATH = AACT_DIR / "aact_trials.sqlite3"
AACT_INDEX_METADATA_PATH = AACT_DIR / "aact_index_metadata.json"
BATCH_SIZE = 1000
CORPORATE_STOP_WORDS = {
    "and",
    "biopharma",
    "biopharmaceuticals",
    "company",
    "corp",
    "corporation",
    "group",
    "holdings",
    "inc",
    "incorporated",
    "limited",
    "llc",
    "ltd",
    "pharmaceutical",
    "pharmaceuticals",
    "plc",
    "sa",
    "therapeutics",
}
STATUS_SORT_ORDER = (
    "RECRUITING",
    "ACTIVE_NOT_RECRUITING",
    "ENROLLING_BY_INVITATION",
    "NOT_YET_RECRUITING",
    "COMPLETED",
    "SUSPENDED",
    "TERMINATED",
    "WITHDRAWN",
    "UNKNOWN",
)


def normalize_text(value: str | None) -> str:
    """Normalize text for broad LIKE-based matching."""
    if not value:
        return ""
    normalized = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return re.sub(r"\s+", " ", normalized).strip()


def sponsor_search_terms(value: str | None) -> list[str]:
    """Return ordered sponsor variants for resilient matching."""
    normalized = normalize_text(value)
    if not normalized:
        return []

    terms = [normalized]
    tokens = [token for token in normalized.split() if token and token not in CORPORATE_STOP_WORDS]
    stripped = " ".join(tokens)
    if stripped and stripped != normalized:
        terms.append(stripped)

    for token in tokens:
        if len(token) >= 5:
            terms.append(token)

    unique_terms: list[str] = []
    for term in terms:
        if term and term not in unique_terms:
            unique_terms.append(term)
    return unique_terms


def find_latest_aact_archive() -> Path | None:
    """Return the newest downloaded AACT zip archive."""
    archives = sorted(AACT_DIR.glob("*_export_ctgov.zip"), key=lambda path: path.stat().st_mtime, reverse=True)
    return archives[0] if archives else None


def ensure_aact_index(force_rebuild: bool = False) -> Path | None:
    """Build the local AACT SQLite index when a downloaded archive is present."""
    archive_path = find_latest_aact_archive()
    if archive_path is None:
        return None

    if not force_rebuild and AACT_INDEX_PATH.exists() and _metadata_matches_archive(archive_path):
        return AACT_INDEX_PATH

    return build_aact_index(archive_path)


def build_aact_index(archive_path: Path) -> Path:
    """Create a local SQLite search index from an AACT zip archive."""
    AACT_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = AACT_INDEX_PATH.with_suffix(".tmp")
    if temp_path.exists():
        temp_path.unlink()

    if AACT_INDEX_PATH.exists():
        AACT_INDEX_PATH.unlink()

    conn = sqlite3.connect(temp_path)
    try:
        _configure_connection(conn)
        _create_schema(conn)

        with ZipFile(archive_path) as archive:
            print(f"Building AACT index from {archive_path.name}...", flush=True)
            _import_studies(conn, archive)
            _import_sponsors(conn, archive)
            _import_conditions(conn, archive)
            _import_interventions(conn, archive)
            _import_primary_outcomes(conn, archive)
            _create_indexes(conn)
            conn.commit()
    finally:
        conn.close()

    temp_path.replace(AACT_INDEX_PATH)
    metadata = {
        "archive_name": archive_path.name,
        "archive_size": archive_path.stat().st_size,
        "built_at": datetime.now().isoformat(),
    }
    AACT_INDEX_METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"AACT index ready: {AACT_INDEX_PATH}", flush=True)
    return AACT_INDEX_PATH


def search_aact_trials(
    sponsor: str | None = None,
    nct_id: str | None = None,
    condition: str | None = None,
    intervention: str | None = None,
    phase: str | None = None,
    status: str | None = None,
    page_size: int = 50,
) -> list[dict]:
    """Query the local AACT index and return trial records in tracker format."""
    index_path = ensure_aact_index()
    if index_path is None:
        print("AACT fallback is not available locally. No archive was found in data/raw/clinicaltrials/aact/.")
        return []

    conn = sqlite3.connect(index_path)
    conn.row_factory = sqlite3.Row
    try:
        params: list[str | int] = []
        query = [
            """
            SELECT
                s.nct_id,
                COALESCE(NULLIF(s.brief_title, ''), NULLIF(s.official_title, ''), '') AS title,
                COALESCE(s.phase, '') AS phase,
                COALESCE(s.overall_status, '') AS status,
                COALESCE(
                    (
                        SELECT sp.name
                        FROM sponsors sp
                        WHERE sp.nct_id = s.nct_id AND sp.lead_or_collaborator = 'lead'
                        ORDER BY sp.rowid
                        LIMIT 1
                    ),
                    (
                        SELECT sp.name
                        FROM sponsors sp
                        WHERE sp.nct_id = s.nct_id
                        ORDER BY CASE WHEN sp.lead_or_collaborator = 'lead' THEN 0 ELSE 1 END, sp.rowid
                        LIMIT 1
                    ),
                    COALESCE(s.source, '')
                ) AS sponsor,
                COALESCE(
                    (
                        SELECT GROUP_CONCAT(name, ', ')
                        FROM (
                            SELECT DISTINCT c.name AS name
                            FROM conditions c
                            WHERE c.nct_id = s.nct_id
                            ORDER BY c.name
                        )
                    ),
                    ''
                ) AS indication,
                COALESCE(
                    (
                        SELECT po.title
                        FROM primary_outcomes po
                        WHERE po.nct_id = s.nct_id
                        LIMIT 1
                    ),
                    ''
                ) AS primary_endpoint,
                COALESCE(s.primary_completion_date, '') AS estimated_primary_completion,
                COALESCE(s.completion_date, '') AS estimated_study_completion,
                CASE WHEN COALESCE(s.results_first_posted_date, '') != '' THEN 1 ELSE 0 END AS results_posted
            FROM studies s
            WHERE 1 = 1
            """
        ]

        if nct_id:
            query.append("AND s.nct_id = ?")
            params.append(nct_id.upper())

        if sponsor:
            sponsor_terms = sponsor_search_terms(sponsor)
            if sponsor_terms:
                query.append(
                    "AND EXISTS (SELECT 1 FROM sponsors sp WHERE sp.nct_id = s.nct_id AND ("
                    + " OR ".join("sp.normalized_name LIKE ?" for _ in sponsor_terms)
                    + "))"
                )
                params.extend(f"%{term}%" for term in sponsor_terms)

        if condition:
            condition_term = normalize_text(condition)
            if condition_term:
                query.append(
                    "AND EXISTS (SELECT 1 FROM conditions c WHERE c.nct_id = s.nct_id AND c.normalized_name LIKE ?)"
                )
                params.append(f"%{condition_term}%")

        if intervention:
            intervention_term = normalize_text(intervention)
            if intervention_term:
                query.append(
                    "AND EXISTS (SELECT 1 FROM interventions i WHERE i.nct_id = s.nct_id AND i.normalized_name LIKE ?)"
                )
                params.append(f"%{intervention_term}%")

        if phase:
            query.append("AND UPPER(COALESCE(s.phase, '')) LIKE ?")
            params.append(f"%{phase.upper()}%")

        if status:
            query.append("AND UPPER(COALESCE(s.overall_status, '')) = ?")
            params.append(status.upper())

        status_case = " ".join(
            f"WHEN '{status_name}' THEN {index}" for index, status_name in enumerate(STATUS_SORT_ORDER)
        )
        query.append(
            f"""
            ORDER BY
                CASE UPPER(COALESCE(s.overall_status, '')) {status_case} ELSE 99 END,
                COALESCE(s.primary_completion_date, s.completion_date, s.study_first_submitted_date, '') DESC,
                s.nct_id DESC
            LIMIT ?
            """
        )
        params.append(page_size)

        rows = conn.execute("\n".join(query), params).fetchall()
    finally:
        conn.close()

    return [_row_to_trial(row) for row in rows]


def _configure_connection(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=OFF")
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA cache_size=-200000")


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE studies (
            nct_id TEXT PRIMARY KEY,
            study_first_submitted_date TEXT,
            brief_title TEXT,
            official_title TEXT,
            overall_status TEXT,
            phase TEXT,
            primary_completion_date TEXT,
            completion_date TEXT,
            results_first_posted_date TEXT,
            source TEXT,
            source_class TEXT
        );

        CREATE TABLE sponsors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nct_id TEXT NOT NULL,
            lead_or_collaborator TEXT,
            name TEXT,
            normalized_name TEXT
        );

        CREATE TABLE conditions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nct_id TEXT NOT NULL,
            name TEXT,
            normalized_name TEXT
        );

        CREATE TABLE interventions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nct_id TEXT NOT NULL,
            name TEXT,
            normalized_name TEXT
        );

        CREATE TABLE primary_outcomes (
            nct_id TEXT PRIMARY KEY,
            title TEXT
        );
        """
    )


def _create_indexes(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE INDEX idx_studies_status ON studies(overall_status);
        CREATE INDEX idx_studies_phase ON studies(phase);
        CREATE INDEX idx_sponsors_nct_id ON sponsors(nct_id);
        CREATE INDEX idx_sponsors_normalized_name ON sponsors(normalized_name);
        CREATE INDEX idx_conditions_nct_id ON conditions(nct_id);
        CREATE INDEX idx_conditions_normalized_name ON conditions(normalized_name);
        CREATE INDEX idx_interventions_nct_id ON interventions(nct_id);
        CREATE INDEX idx_interventions_normalized_name ON interventions(normalized_name);
        """
    )


def _metadata_matches_archive(archive_path: Path) -> bool:
    if not AACT_INDEX_METADATA_PATH.exists():
        return False

    try:
        metadata = json.loads(AACT_INDEX_METADATA_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False

    return (
        metadata.get("archive_name") == archive_path.name
        and metadata.get("archive_size") == archive_path.stat().st_size
    )


def _open_reader(archive: ZipFile, member_name: str) -> csv.DictReader:
    text_stream = io.TextIOWrapper(archive.open(member_name), encoding="utf-8", newline="")
    return csv.DictReader(text_stream, delimiter="|")


def _import_studies(conn: sqlite3.Connection, archive: ZipFile) -> None:
    print("Importing studies...", flush=True)
    reader = _open_reader(archive, "studies.txt")
    batch: list[tuple[str, ...]] = []
    count = 0
    for row in reader:
        batch.append(
            (
                row["nct_id"],
                row["study_first_submitted_date"],
                row["brief_title"],
                row["official_title"],
                row["overall_status"],
                row["phase"],
                row["primary_completion_date"],
                row["completion_date"],
                row["results_first_posted_date"],
                row["source"],
                row["source_class"],
            )
        )
        if len(batch) >= BATCH_SIZE:
            conn.executemany(
                """
                INSERT INTO studies (
                    nct_id,
                    study_first_submitted_date,
                    brief_title,
                    official_title,
                    overall_status,
                    phase,
                    primary_completion_date,
                    completion_date,
                    results_first_posted_date,
                    source,
                    source_class
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                batch,
            )
            count += len(batch)
            batch.clear()
            if count % 100000 == 0:
                print(f"  studies imported: {count}", flush=True)

    if batch:
        conn.executemany(
            """
            INSERT INTO studies (
                nct_id,
                study_first_submitted_date,
                brief_title,
                official_title,
                overall_status,
                phase,
                primary_completion_date,
                completion_date,
                results_first_posted_date,
                source,
                source_class
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            batch,
        )
        count += len(batch)

    print(f"  studies imported: {count}", flush=True)


def _import_sponsors(conn: sqlite3.Connection, archive: ZipFile) -> None:
    print("Importing sponsors...", flush=True)
    reader = _open_reader(archive, "sponsors.txt")
    batch: list[tuple[str, str, str, str]] = []
    count = 0
    for row in reader:
        batch.append(
            (
                row["nct_id"],
                row["lead_or_collaborator"],
                row["name"],
                normalize_text(row["name"]),
            )
        )
        if len(batch) >= BATCH_SIZE:
            conn.executemany(
                "INSERT INTO sponsors (nct_id, lead_or_collaborator, name, normalized_name) VALUES (?, ?, ?, ?)",
                batch,
            )
            count += len(batch)
            batch.clear()
            if count % 100000 == 0:
                print(f"  sponsors imported: {count}", flush=True)

    if batch:
        conn.executemany(
            "INSERT INTO sponsors (nct_id, lead_or_collaborator, name, normalized_name) VALUES (?, ?, ?, ?)",
            batch,
        )
        count += len(batch)

    print(f"  sponsors imported: {count}", flush=True)


def _import_conditions(conn: sqlite3.Connection, archive: ZipFile) -> None:
    print("Importing conditions...", flush=True)
    reader = _open_reader(archive, "conditions.txt")
    batch: list[tuple[str, str, str]] = []
    count = 0
    for row in reader:
        batch.append((row["nct_id"], row["name"], normalize_text(row["name"])))
        if len(batch) >= BATCH_SIZE:
            conn.executemany(
                "INSERT INTO conditions (nct_id, name, normalized_name) VALUES (?, ?, ?)",
                batch,
            )
            count += len(batch)
            batch.clear()
            if count % 100000 == 0:
                print(f"  conditions imported: {count}", flush=True)

    if batch:
        conn.executemany(
            "INSERT INTO conditions (nct_id, name, normalized_name) VALUES (?, ?, ?)",
            batch,
        )
        count += len(batch)

    print(f"  conditions imported: {count}", flush=True)


def _import_interventions(conn: sqlite3.Connection, archive: ZipFile) -> None:
    print("Importing interventions...", flush=True)
    reader = _open_reader(archive, "interventions.txt")
    batch: list[tuple[str, str, str]] = []
    count = 0
    for row in reader:
        batch.append((row["nct_id"], row["name"], normalize_text(row["name"])))
        if len(batch) >= BATCH_SIZE:
            conn.executemany(
                "INSERT INTO interventions (nct_id, name, normalized_name) VALUES (?, ?, ?)",
                batch,
            )
            count += len(batch)
            batch.clear()
            if count % 100000 == 0:
                print(f"  interventions imported: {count}", flush=True)

    if batch:
        conn.executemany(
            "INSERT INTO interventions (nct_id, name, normalized_name) VALUES (?, ?, ?)",
            batch,
        )
        count += len(batch)

    print(f"  interventions imported: {count}", flush=True)


def _import_primary_outcomes(conn: sqlite3.Connection, archive: ZipFile) -> None:
    print("Importing primary outcomes...", flush=True)
    reader = _open_reader(archive, "outcomes.txt")
    batch: list[tuple[str, str]] = []
    count = 0
    for row in reader:
        if row["outcome_type"] != "PRIMARY" or not row["title"]:
            continue

        batch.append((row["nct_id"], row["title"]))
        if len(batch) >= BATCH_SIZE:
            conn.executemany("INSERT OR IGNORE INTO primary_outcomes (nct_id, title) VALUES (?, ?)", batch)
            count += len(batch)
            batch.clear()
            if count % 100000 == 0:
                print(f"  primary outcomes imported: {count}", flush=True)

    if batch:
        conn.executemany("INSERT OR IGNORE INTO primary_outcomes (nct_id, title) VALUES (?, ?)", batch)
        count += len(batch)

    print(f"  primary outcomes imported: {count}", flush=True)


def _row_to_trial(row: sqlite3.Row) -> dict:
    nct_id = row["nct_id"] or ""
    return {
        "nct_id": nct_id,
        "title": row["title"] or "",
        "phase": row["phase"] or "",
        "status": row["status"] or "",
        "sponsor": row["sponsor"] or "",
        "indication": row["indication"] or "",
        "primary_endpoint": row["primary_endpoint"] or "",
        "estimated_primary_completion": row["estimated_primary_completion"] or "",
        "estimated_study_completion": row["estimated_study_completion"] or "",
        "results_posted": bool(row["results_posted"]),
        "source_url": f"https://clinicaltrials.gov/study/{nct_id}" if nct_id else "",
        "source_type": "AACT",
        "source_confidence": "secondary",
    }
