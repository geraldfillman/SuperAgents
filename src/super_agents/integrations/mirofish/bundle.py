"""Utilities for building MiroFish-compatible simulation bundles."""

from __future__ import annotations

import csv
import json
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_BUNDLES_DIR = PROJECT_ROOT / "data" / "processed" / "mirofish_simulations"


def _slugify(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "agent"


def _coerce_float(value: Any, default: float) -> float:
    if value is None:
        return default
    return float(value)


def _coerce_int(value: Any, default: int) -> int:
    if value is None:
        return default
    return int(value)


def _coerce_list_of_ints(value: Any, default: list[int]) -> list[int]:
    if value is None:
        return list(default)
    return [int(item) for item in value]


@dataclass(slots=True)
class MiroFishAgentProfile:
    """Portable simulation agent profile used to generate MiroFish bundle files."""

    agent_id: int
    name: str
    username: str
    bio: str
    persona: str
    age: int = 30
    gender: str = "other"
    mbti: str = "ISTJ"
    country: str = "United States"
    profession: str | None = None
    interested_topics: list[str] = field(default_factory=list)
    karma: int = 1000
    friend_count: int = 100
    follower_count: int = 150
    statuses_count: int = 500
    activity_level: float = 0.5
    posts_per_hour: float = 1.0
    comments_per_hour: float = 2.0
    active_hours: list[int] = field(default_factory=lambda: list(range(8, 23)))
    response_delay_min: int = 5
    response_delay_max: int = 60
    sentiment_bias: float = 0.0
    stance: str = "neutral"
    influence_weight: float = 1.0
    entity_uuid: str = ""
    entity_type: str = "Participant"
    created_at: str = "2025-01-01"

    @classmethod
    def from_mapping(cls, data: dict[str, Any], agent_id: int) -> "MiroFishAgentProfile":
        name = str(data.get("name") or f"Agent {agent_id}")
        username = str(data.get("username") or f"{_slugify(name)}_{100 + agent_id}")
        bio = str(data.get("bio") or f"{name} participates in online discussion.")
        persona = str(data.get("persona") or bio)
        return cls(
            agent_id=agent_id,
            name=name,
            username=username,
            bio=bio,
            persona=persona,
            age=_coerce_int(data.get("age"), 30),
            gender=str(data.get("gender") or "other"),
            mbti=str(data.get("mbti") or "ISTJ"),
            country=str(data.get("country") or "United States"),
            profession=data.get("profession"),
            interested_topics=[str(item) for item in data.get("interested_topics", [])],
            karma=_coerce_int(data.get("karma"), 1000),
            friend_count=_coerce_int(data.get("friend_count"), 100),
            follower_count=_coerce_int(data.get("follower_count"), 150),
            statuses_count=_coerce_int(data.get("statuses_count"), 500),
            activity_level=_coerce_float(data.get("activity_level"), 0.5),
            posts_per_hour=_coerce_float(data.get("posts_per_hour"), 1.0),
            comments_per_hour=_coerce_float(data.get("comments_per_hour"), 2.0),
            active_hours=_coerce_list_of_ints(data.get("active_hours"), list(range(8, 23))),
            response_delay_min=_coerce_int(data.get("response_delay_min"), 5),
            response_delay_max=_coerce_int(data.get("response_delay_max"), 60),
            sentiment_bias=_coerce_float(data.get("sentiment_bias"), 0.0),
            stance=str(data.get("stance") or "neutral"),
            influence_weight=_coerce_float(data.get("influence_weight"), 1.0),
            entity_uuid=str(data.get("entity_uuid") or f"entity_{uuid.uuid4().hex[:12]}"),
            entity_type=str(data.get("entity_type") or "Participant"),
            created_at=str(data.get("created_at") or "2025-01-01"),
        )

    def to_agent_config(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "entity_uuid": self.entity_uuid,
            "entity_name": self.name,
            "entity_type": self.entity_type,
            "activity_level": self.activity_level,
            "posts_per_hour": self.posts_per_hour,
            "comments_per_hour": self.comments_per_hour,
            "active_hours": list(self.active_hours),
            "response_delay_min": self.response_delay_min,
            "response_delay_max": self.response_delay_max,
            "sentiment_bias": self.sentiment_bias,
            "stance": self.stance,
            "influence_weight": self.influence_weight,
        }

    def to_reddit_profile(self) -> dict[str, Any]:
        data = {
            "user_id": self.agent_id,
            "username": self.username,
            "name": self.name,
            "bio": self.bio[:150],
            "persona": self.persona,
            "karma": self.karma,
            "created_at": self.created_at,
            "age": self.age,
            "gender": self._normalize_gender(),
            "mbti": self.mbti,
            "country": self.country,
        }
        if self.profession:
            data["profession"] = self.profession
        if self.interested_topics:
            data["interested_topics"] = list(self.interested_topics)
        return data

    def twitter_csv_row(self) -> list[Any]:
        user_char = self.bio
        if self.persona and self.persona != self.bio:
            user_char = f"{self.bio} {self.persona}"
        user_char = user_char.replace("\n", " ").replace("\r", " ")
        description = self.bio.replace("\n", " ").replace("\r", " ")
        return [self.agent_id, self.name, self.username, user_char, description]

    def _normalize_gender(self) -> str:
        mapping = {
            "male": "male",
            "female": "female",
            "other": "other",
            "man": "male",
            "woman": "female",
            "m": "male",
            "f": "female",
        }
        return mapping.get(self.gender.strip().lower(), "other")


@dataclass(slots=True)
class MiroFishBundleSpec:
    """High-level portable input for creating a MiroFish simulation bundle."""

    simulation_id: str
    project_id: str
    graph_id: str
    simulation_requirement: str
    agent_profiles: list[MiroFishAgentProfile]
    time_config: dict[str, Any] = field(default_factory=dict)
    event_config: dict[str, Any] = field(default_factory=dict)
    twitter_config: dict[str, Any] = field(default_factory=dict)
    reddit_config: dict[str, Any] = field(default_factory=dict)
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = ""
    generation_reasoning: str = "Prepared by Super_Agents portable MiroFish bundle builder."

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "MiroFishBundleSpec":
        raw_profiles = data.get("agent_profiles") or data.get("profiles") or []
        if not raw_profiles:
            raise ValueError("Bundle spec must include at least one agent profile.")

        simulation_id = str(data.get("simulation_id") or f"sim_{uuid.uuid4().hex[:12]}")
        project_id = str(data.get("project_id") or simulation_id)
        graph_id = str(data.get("graph_id") or data.get("graph_name") or f"graph_{simulation_id}")
        requirement = str(
            data.get("simulation_requirement")
            or data.get("requirement")
            or "Portable MiroFish simulation prepared by Super_Agents."
        )

        profiles = [
            MiroFishAgentProfile.from_mapping(profile, agent_id=index)
            for index, profile in enumerate(raw_profiles)
        ]

        return cls(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=graph_id,
            simulation_requirement=requirement,
            agent_profiles=profiles,
            time_config=_merge_time_defaults(data.get("time_config")),
            event_config=_merge_event_defaults(data.get("event_config")),
            twitter_config=_merge_platform_defaults("twitter", data.get("twitter_config")),
            reddit_config=_merge_platform_defaults("reddit", data.get("reddit_config")),
            llm_model=str(data.get("llm_model") or "gpt-4o-mini"),
            llm_base_url=str(data.get("llm_base_url") or ""),
            generation_reasoning=str(
                data.get("generation_reasoning")
                or "Prepared by Super_Agents portable MiroFish bundle builder."
            ),
        )

    def to_config(self) -> dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "simulation_requirement": self.simulation_requirement,
            "time_config": self.time_config,
            "agent_configs": [profile.to_agent_config() for profile in self.agent_profiles],
            "event_config": self.event_config,
            "twitter_config": self.twitter_config,
            "reddit_config": self.reddit_config,
            "llm_model": self.llm_model,
            "llm_base_url": self.llm_base_url,
            "generation_reasoning": self.generation_reasoning,
        }


def _merge_time_defaults(data: Any) -> dict[str, Any]:
    defaults = {
        "total_simulation_hours": 72,
        "minutes_per_round": 60,
        "agents_per_hour_min": 5,
        "agents_per_hour_max": 20,
        "peak_hours": [19, 20, 21, 22],
        "peak_activity_multiplier": 1.5,
        "off_peak_hours": [0, 1, 2, 3, 4, 5],
        "off_peak_activity_multiplier": 0.05,
        "morning_hours": [6, 7, 8],
        "morning_activity_multiplier": 0.4,
        "work_hours": [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
        "work_activity_multiplier": 0.7,
    }
    if data:
        defaults.update(data)
    return defaults


def _merge_event_defaults(data: Any) -> dict[str, Any]:
    defaults = {
        "initial_posts": [],
        "scheduled_events": [],
        "hot_topics": [],
        "narrative_direction": "",
    }
    if data:
        defaults.update(data)
    return defaults


def _merge_platform_defaults(platform: str, data: Any) -> dict[str, Any]:
    defaults = {
        "platform": platform,
        "recency_weight": 0.4,
        "popularity_weight": 0.3,
        "relevance_weight": 0.3,
        "viral_threshold": 10,
        "echo_chamber_strength": 0.5,
    }
    if data:
        defaults.update(data)
    return defaults


def load_bundle_spec(spec_path: Path | str) -> MiroFishBundleSpec:
    """Load a bundle spec from JSON or YAML."""

    path = Path(spec_path)
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() in {".yaml", ".yml"}:
        data = yaml.safe_load(text) or {}
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("Bundle spec root must be a mapping.")
    return MiroFishBundleSpec.from_mapping(data)


def create_bundle_from_spec(
    spec: MiroFishBundleSpec,
    output_dir: Path | str | None = None,
    *,
    overwrite: bool = False,
) -> Path:
    """Write a MiroFish-compatible bundle to disk and return the bundle directory."""

    bundle_dir = Path(output_dir) if output_dir is not None else DEFAULT_BUNDLES_DIR / spec.simulation_id
    if bundle_dir.exists() and any(bundle_dir.iterdir()) and not overwrite:
        raise FileExistsError(f"Bundle directory already exists: {bundle_dir}")

    bundle_dir.mkdir(parents=True, exist_ok=True)

    config_path = bundle_dir / "simulation_config.json"
    reddit_profiles_path = bundle_dir / "reddit_profiles.json"
    twitter_profiles_path = bundle_dir / "twitter_profiles.csv"
    summary_path = bundle_dir / "bundle_summary.json"

    config_path.write_text(
        json.dumps(spec.to_config(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    reddit_profiles_path.write_text(
        json.dumps(
            [profile.to_reddit_profile() for profile in spec.agent_profiles],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    with twitter_profiles_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["user_id", "name", "username", "user_char", "description"])
        for profile in spec.agent_profiles:
            writer.writerow(profile.twitter_csv_row())

    summary = {
        "simulation_id": spec.simulation_id,
        "bundle_dir": str(bundle_dir),
        "agent_count": len(spec.agent_profiles),
        "files": {
            "simulation_config": str(config_path),
            "reddit_profiles": str(reddit_profiles_path),
            "twitter_profiles": str(twitter_profiles_path),
        },
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return bundle_dir


def read_bundle(bundle_dir: Path | str) -> dict[str, Any]:
    """Read an existing bundle and summarize its contents."""

    root = Path(bundle_dir)
    config_path = root / "simulation_config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Missing simulation_config.json in {root}")

    config = json.loads(config_path.read_text(encoding="utf-8"))
    return {
        "bundle_dir": str(root),
        "simulation_id": config.get("simulation_id"),
        "project_id": config.get("project_id"),
        "graph_id": config.get("graph_id"),
        "agent_count": len(config.get("agent_configs", [])),
        "has_twitter_profiles": (root / "twitter_profiles.csv").exists(),
        "has_reddit_profiles": (root / "reddit_profiles.json").exists(),
        "time_config": config.get("time_config", {}),
    }
