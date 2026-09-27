from abc import ABC, abstractmethod
from typing import List
from playwright.sync_api import Page


class BasePersona(ABC):
    """Abstract base class for all synthetic chaos personas."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.actions_log: List[str] = []

    def log_action(self, action: str):
        """Records an action taken by this persona during the session."""
        self.actions_log.append(action)

    @abstractmethod
    def attack(self, page: Page, duration: int):
        """Executes the chaotic behavioral pattern on the target page."""
        pass