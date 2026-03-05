"""
Profile service for loading and resolving user preference profiles.
Reads the SSOT profile registry (JSON) and caches it in memory.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


class ProfileService:
    """
    Loads profiles from the static JSON registry and resolves
    a profile_id to a full profile_context dict (or None).

    Class-level cache ensures the JSON is loaded only once.
    """

    _registry_cache: Optional[Dict[str, Any]] = None
    _profiles_by_id: Optional[Dict[str, Dict[str, Any]]] = None

    def _load_registry(self) -> None:
        """Load profiles.json from the static config directory. Cache at class level."""
        if ProfileService._registry_cache is not None:
            return

        registry_path = (
            Path(__file__).resolve().parent.parent.parent / "presentation" / "static" / "config" / "profiles.json"
        )

        try:
            with open(registry_path, encoding="utf-8") as f:
                data = json.load(f)

            ProfileService._registry_cache = data
            profiles = data.get("profiles", [])
            ProfileService._profiles_by_id = {p["id"]: p for p in profiles if "id" in p}

            logger.info(
                "Profile registry loaded",
                version=data.get("version"),
                profile_count=len(profiles),
            )
        except FileNotFoundError:
            logger.error("Profile registry not found", path=str(registry_path))
            ProfileService._registry_cache = {"version": "0", "profiles": []}
            ProfileService._profiles_by_id = {}
        except json.JSONDecodeError as e:
            logger.error("Profile registry invalid JSON", error=str(e))
            ProfileService._registry_cache = {"version": "0", "profiles": []}
            ProfileService._profiles_by_id = {}

    def resolve_profile(self, profile_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Resolve a profile_id to a profile_context dict.

        Returns a dict with {id, label, prompt_directives, ranking_bias} or None.
        If profile_id is unknown, logs a warning and returns None.
        """
        if profile_id is None:
            return None

        self._load_registry()

        profile = (ProfileService._profiles_by_id or {}).get(profile_id)
        if profile is None:
            logger.warning(
                "Unknown profile_id received, treating as null",
                profile_id=profile_id,
            )
            return None

        return {
            "id": profile["id"],
            "label": profile["label"],
            "prompt_directives": profile.get("prompt_directives", []),
            "ranking_bias": profile.get("ranking_bias", {}),
        }

    def list_profiles(self) -> List[Dict[str, Any]]:
        """Return all profiles (for potential future API endpoint)."""
        self._load_registry()
        return list((ProfileService._profiles_by_id or {}).values())
