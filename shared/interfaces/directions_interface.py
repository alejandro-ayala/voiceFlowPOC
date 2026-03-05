"""Directions service interface contract for route calculation."""

from abc import ABC, abstractmethod
from typing import Optional

from shared.models.tool_models import RouteOption


class DirectionsServiceInterface(ABC):
    """Contract for route/directions services (Google Routes, OpenRouteService, etc.)."""

    @abstractmethod
    async def get_directions(
        self,
        origin: str,
        destination: str,
        mode: str = "transit",
        accessibility_profile: Optional[str] = None,
        language: str = "es",
    ) -> list[RouteOption]:
        """Get directions between two points with accessibility options."""
        ...

    @abstractmethod
    def is_service_available(self) -> bool:
        """Report if the provider is ready (API key set, etc.)."""
        ...

    @abstractmethod
    def get_service_info(self) -> dict:
        """Return provider metadata: name, status, supported modes."""
        ...
