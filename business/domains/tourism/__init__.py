"""Tourism domain: Accessible tourism in Madrid."""

from __future__ import annotations

from importlib import import_module


def __getattr__(name: str):
	if name == "TourismMultiAgent":
		return import_module("business.domains.tourism.agent").TourismMultiAgent
	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["TourismMultiAgent"]
