"""Shared utilities for all sector agents.

Core modules (always available):
  - cik, env, io_utils, paths — original utilities
  - confidence — source provenance tagging (SourceConfidence, tag_source)
  - data_result — pipeline contracts (DataResult, Signal, RunMetadata)
  - http_client — resilient HTTP with retry (resilient_get, resilient_post)
  - validate — shared source validation across agents
  - registry — runtime AgentRegistry for programmatic agent discovery
  - run_summary, status — dashboard output writers
"""

from .cik import normalize_cik
from .confidence import SourceConfidence, SourceType, is_sponsor_only, tag_source, validate_source_fields
from .data_result import DataResult, RunMetadata, Signal
from .env import optional_env, require_env, validate_env_block
from .http_client import head_check, resilient_get, resilient_post
from .io_utils import load_json_records, read_json, write_json
from .paths import agent_data_dir, ensure_directory, project_path, slugify
from .run_summary import write_run_summary
from .status import write_current_status
from .validate import print_report, validate_sources

__all__ = [
    # cik
    "normalize_cik",
    # confidence
    "SourceConfidence",
    "SourceType",
    "tag_source",
    "validate_source_fields",
    "is_sponsor_only",
    # data_result
    "DataResult",
    "RunMetadata",
    "Signal",
    # env
    "require_env",
    "optional_env",
    "validate_env_block",
    # http_client
    "resilient_get",
    "resilient_post",
    "head_check",
    # io_utils
    "read_json",
    "write_json",
    "load_json_records",
    # paths
    "project_path",
    "ensure_directory",
    "slugify",
    "agent_data_dir",
    # run_summary
    "write_run_summary",
    # status
    "write_current_status",
    # validate
    "validate_sources",
    "print_report",
]
