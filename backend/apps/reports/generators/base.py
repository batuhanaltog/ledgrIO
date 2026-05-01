from abc import ABC, abstractmethod
from typing import Any


class BaseReportGenerator(ABC):
    def __init__(self, user, parameters: dict):
        self.user = user
        self.parameters = parameters

    @abstractmethod
    def generate(self) -> bytes:
        """Generate and return the report content as bytes."""

    @abstractmethod
    def get_filename(self) -> str:
        """Return the suggested filename for this report."""

    def get_date_range(self) -> tuple[str, str]:
        date_from = self.parameters.get("date_from", "2000-01-01")
        date_to = self.parameters.get("date_to", "2099-12-31")
        return date_from, date_to
