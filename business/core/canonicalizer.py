"""Canonicalizer: normalize multi-agent/tool outputs to the SSOT expected by the UI.

This module performs lightweight normalization and mapping of free-text
fields produced by tools/LLMs into the canonical keys/values used across
the application (`application.models.responses`). It intentionally keeps
the mapping rules simple and deterministic to avoid hallucinations.
"""

from __future__ import annotations

import logging
import unicodedata
from typing import Any, Dict, List, Optional

from application.models.responses import TourismData

logger = logging.getLogger(__name__)


def _normalize_text(s: Any) -> Optional[str]:
    if s is None:
        return None
    try:
        t = str(s).strip()
        # remove accents for simple matching
        t = unicodedata.normalize("NFKD", t)
        t = "".join(ch for ch in t if not unicodedata.combining(ch))
        return t
    except Exception:
        return None


FACILITY_MAP = {
    # Spanish -> canonical
    "rampas": "wheelchair_ramps",
    "rampas de acceso": "wheelchair_ramps",
    "rampas de acceso para sillas": "wheelchair_ramps",
    "baños adaptados": "adapted_bathrooms",
    "bano adaptado": "adapted_bathrooms",
    "audioguia": "audio_guides",
    "audioguia audio": "audio_guides",
    "audioguia en espanol": "audio_guides",
    "interpretacion en lengua de signos": "sign_language_interpreters",
    "bucle auditivo": "hearing_loops",
    "ascensor": "elevator_access",
    "plazas sillas de ruedas": "wheelchair_spaces",
}

LEVEL_MAP = {
    "full_wheelchair_access": "full_wheelchair_access",
    "acceso completo": "full_wheelchair_access",
    "acceso total": "full_wheelchair_access",
    "partial_wheelchair_access": "partial_wheelchair_access",
    "acceso parcial": "partial_wheelchair_access",
    "varies_by_location": "varies_by_location",
    "varia por ubicacion": "varies_by_location",
    "partial_access": "partial_access",
    "sin informacion": "partial_access",
}


def _canonicalize_facilities(raw: Any) -> Optional[List[str]]:
    if raw is None:
        return None
    # if already list
    if isinstance(raw, list):
        items = raw
    else:
        txt = _normalize_text(raw)
        if not txt:
            return None
        # split by common separators
        if "," in txt:
            items = [p.strip() for p in txt.split(",") if p.strip()]
        else:
            items = [p.strip() for p in txt.split(";") if p.strip()]

    out: List[str] = []
    for it in items:
        t = _normalize_text(it)
        if not t:
            continue
        tl = t.lower()
        # try direct map
        mapped = FACILITY_MAP.get(tl)
        if not mapped:
            # try token-based match
            for k, v in FACILITY_MAP.items():
                if k in tl:
                    mapped = v
                    break
        if not mapped:
            # fallback: make a safe snake case token
            mapped = tl.replace(" ", "_")[:60]
        out.append(mapped)
    return out or None


def _canonicalize_level(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    t = _normalize_text(raw)
    if not t:
        return None
    tl = t.lower()
    # direct match
    mapped = LEVEL_MAP.get(tl)
    if mapped:
        return mapped
    # token heuristics
    if "completo" in tl or "total" in tl or "wheelchair" in tl:
        return "full_wheelchair_access"
    if "parcial" in tl or "partial" in tl:
        return "partial_wheelchair_access"
    if "varia" in tl or "vari" in tl:
        return "varies_by_location"
    return tl[:60]


def canonicalize_tourism_data(raw: Any) -> Optional[Dict[str, Any]]:
    """Return a canonicalized tourism_data dict or None.

    This function performs conservative normalization and then validates
    the result with the Pydantic `TourismData` model. If validation fails
    it returns None to avoid exposing hallucinated or invalid content.
    """
    if not raw or not isinstance(raw, dict):
        return None

    try:
        venue_raw = raw.get("venue")
        routes_raw = raw.get("routes")
        accessibility_raw = raw.get("accessibility")

        venue = None
        if isinstance(venue_raw, dict):
            v = {}
            # canonicalize common fields
            v["name"] = _normalize_text(venue_raw.get("name")) or venue_raw.get("name")
            v["type"] = _normalize_text(venue_raw.get("type")) or venue_raw.get("type")
            # accessibility_score or score
            v["accessibility_score"] = venue_raw.get("accessibility_score") or venue_raw.get("score")
            v["certification"] = _normalize_text(venue_raw.get("certification")) or venue_raw.get("certification")
            v["facilities"] = _canonicalize_facilities(venue_raw.get("facilities") or venue_raw.get("services"))
            v["opening_hours"] = venue_raw.get("opening_hours")
            v["pricing"] = venue_raw.get("pricing")
            venue = v

        routes = None
        if routes_raw:
            # ensure it's a list of dicts
            if isinstance(routes_raw, dict) and "routes" in routes_raw:
                routes_list = routes_raw.get("routes")
            elif isinstance(routes_raw, list):
                routes_list = routes_raw
            else:
                routes_list = None

            if isinstance(routes_list, list):
                r_out = []
                for r in routes_list:
                    if not isinstance(r, dict):
                        continue
                    rr = {}
                    rr["transport"] = _normalize_text(r.get("transport")) or r.get("transport")
                    rr["line"] = _normalize_text(r.get("line")) or r.get("line")
                    rr["duration"] = _normalize_text(r.get("duration")) or r.get("duration")
                    rr["accessibility"] = _canonicalize_level(r.get("accessibility") or r.get("accessibility_level"))
                    rr["cost"] = _normalize_text(r.get("cost")) or r.get("cost")
                    rr["steps"] = r.get("steps")
                    r_out.append(rr)
                routes = r_out or None

        accessibility = None
        if isinstance(accessibility_raw, dict):
            a = {}
            level_val = accessibility_raw.get("accessibility_level") or accessibility_raw.get("level")
            a["level"] = _canonicalize_level(level_val)
            score_val = accessibility_raw.get("accessibility_score") or accessibility_raw.get("score")
            a["score"] = score_val
            cert_raw = accessibility_raw.get("certification")
            a["certification"] = _normalize_text(cert_raw) or cert_raw
            facilities_val = accessibility_raw.get("facilities") or accessibility_raw.get("services")
            a["facilities"] = _canonicalize_facilities(facilities_val)
            a["services"] = accessibility_raw.get("services")
            accessibility = a

        candidate = {"venue": venue, "routes": routes, "accessibility": accessibility}

        # Validate with Pydantic; if invalid, return None
        td = TourismData.parse_obj(candidate)
        return td.dict()
    except Exception as e:
        logger.warning("Canonicalization failed", error=str(e))
        return None
