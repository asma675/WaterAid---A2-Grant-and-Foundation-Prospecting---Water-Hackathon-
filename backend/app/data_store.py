from __future__ import annotations
import csv
import json
from functools import lru_cache
from typing import Any
from .config import DATA_DIR


def read_csv(name: str) -> list[dict[str, str]]:
    path = DATA_DIR / name
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = [line for line in fh if not line.lstrip().startswith("#")]
    return list(csv.DictReader(rows))


def read_json(name: str, default: Any = None) -> Any:
    path = DATA_DIR / name
    if not path.exists():
        return [] if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def profile() -> dict[str, Any]:
    return read_json("water_care_profile.json", {})

@lru_cache(maxsize=1)
def test_cases() -> list[dict[str, str]]:
    return read_csv("L4_test_cases.csv")

@lru_cache(maxsize=1)
def expected_behaviour() -> list[dict[str, str]]:
    return read_csv("L4_expected_behaviour.csv")

@lru_cache(maxsize=1)
def funders() -> list[dict[str, str]]:
    return read_csv("L2_funder_registry.csv")

@lru_cache(maxsize=1)
def sources() -> list[dict[str, str]]:
    return read_csv("L2_source_register.csv")

@lru_cache(maxsize=1)
def relationships() -> list[dict[str, str]]:
    return read_csv("L1_relationships.csv")

@lru_cache(maxsize=1)
def ranking_scenario() -> list[dict[str, str]]:
    return read_csv("L4_ranking_scenario.csv")

@lru_cache(maxsize=1)
def ranking_reference() -> list[dict[str, str]]:
    return read_csv("L4_ranking_reference_answer.csv")

@lru_cache(maxsize=1)
def controls() -> list[dict[str, str]]:
    return read_csv("L3_controls.csv")

@lru_cache(maxsize=1)
def metrics() -> list[dict[str, str]]:
    return read_csv("L4_success_metrics.csv")

@lru_cache(maxsize=1)
def real_public_demo() -> list[dict[str, Any]]:
    return read_json("real_public_demo.json", [])

@lru_cache(maxsize=1)
def public_sources() -> list[dict[str, Any]]:
    return read_json("public_sources.json", [])

@lru_cache(maxsize=1)
def public_opportunities() -> list[dict[str, Any]]:
    return read_json("public_opportunities.json", [])

@lru_cache(maxsize=1)
def public_funders() -> list[dict[str, Any]]:
    return read_json("public_funders.json", [])

@lru_cache(maxsize=1)
def gift_signals() -> list[dict[str, Any]]:
    return read_json("gift_signals.json", [])


@lru_cache(maxsize=1)
def wateraid_target_countries() -> list[dict[str, Any]]:
    return read_json("wateraid_target_countries.json", [])

@lru_cache(maxsize=1)
def wateraid_live_profile() -> dict[str, Any]:
    return read_json("wateraid_live_profile.json", {})

@lru_cache(maxsize=1)
def public_contacts() -> list[dict[str, Any]]:
    return read_json("public_contacts.json", [])
