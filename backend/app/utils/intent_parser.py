"""
Rule-based intent parser for the AI Assistant.
Open/Closed Principle: add new IntentHandler subclasses without modifying IntentParser.
Each handler is a Strategy — swappable independently.
"""
from __future__ import annotations
import re
from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass


@dataclass
class ParsedIntent:
    intent: str
    entities: dict
    confidence: float


class IntentHandler(ABC):
    """Base strategy class. Each subclass handles one intent family."""

    @abstractmethod
    def matches(self, query: str) -> bool:
        ...

    @abstractmethod
    def parse(self, query: str) -> ParsedIntent:
        ...


class SeatLocationHandler(IntentHandler):
    """Handles: 'Where is X seated?', 'Find seat of X', 'seat of employee X'"""

    PATTERNS = [
        re.compile(r"where\s+is\s+(.+?)\s+seat", re.I),
        re.compile(r"seat\s+of\s+(?:employee\s+)?(.+)", re.I),
        re.compile(r"find\s+(?:seat|location)\s+(?:for|of)\s+(.+)", re.I),
        re.compile(r"where\s+(?:am\s+i|is\s+(.+?))\s+(?:seated|sitting|located)", re.I),
    ]
    EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[a-z]+", re.I)

    def matches(self, query: str) -> bool:
        keywords = ["seat", "seated", "sitting", "where", "location", "floor", "zone", "bay"]
        return any(k in query.lower() for k in keywords)

    def parse(self, query: str) -> ParsedIntent:
        email = self.EMAIL_RE.search(query)
        name = None

        for pattern in self.PATTERNS:
            m = pattern.search(query)
            if m:
                name = m.group(1).strip() if m.lastindex and m.group(1) else None
                break

        # strip "my email is" prefix from email context
        email_val = email.group(0) if email else None

        return ParsedIntent(
            intent="find_seat",
            entities={"name": name, "email": email_val},
            confidence=0.9 if (name or email_val) else 0.6,
        )


class ProjectAssignmentHandler(IntentHandler):
    """Handles: 'which project is X on?', 'project assignment of X'"""

    PATTERNS = [
        re.compile(r"which\s+project\s+(?:is\s+)?(.+?)\s+(?:on|assigned|working)", re.I),
        re.compile(r"project\s+(?:of|for|assignment\s+of)\s+(.+)", re.I),
        re.compile(r"(.+?)\s+project\s+assignment", re.I),
    ]
    EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[a-z]+", re.I)

    def matches(self, query: str) -> bool:
        keywords = ["project", "assigned", "assignment", "working on", "team"]
        return any(k in query.lower() for k in keywords)

    def parse(self, query: str) -> ParsedIntent:
        email = self.EMAIL_RE.search(query)
        name = None
        for p in self.PATTERNS:
            m = p.search(query)
            if m:
                name = m.group(1).strip()
                break
        return ParsedIntent(
            intent="find_project",
            entities={"name": name, "email": email.group(0) if email else None},
            confidence=0.85,
        )


class AvailableSeatsHandler(IntentHandler):
    """Handles: 'show available seats on floor 3', 'free seats in zone B'"""

    FLOOR_RE = re.compile(r"floor\s*(\d+)", re.I)
    ZONE_RE = re.compile(r"zone\s*([a-z])", re.I)

    def matches(self, query: str) -> bool:
        keywords = ["available", "free", "empty", "vacant", "show seats", "list seats"]
        return any(k in query.lower() for k in keywords)

    def parse(self, query: str) -> ParsedIntent:
        floor_m = self.FLOOR_RE.search(query)
        zone_m = self.ZONE_RE.search(query)
        return ParsedIntent(
            intent="available_seats",
            entities={
                "floor": int(floor_m.group(1)) if floor_m else None,
                "zone": zone_m.group(1).upper() if zone_m else None,
            },
            confidence=0.9,
        )


class SeatUtilizationHandler(IntentHandler):
    """Handles: 'how many seats occupied for Project Indigo?', 'utilization of floor 2'"""

    PROJECT_RE = re.compile(r"project\s+(\w+)", re.I)
    FLOOR_RE = re.compile(r"floor\s*(\d+)", re.I)

    def matches(self, query: str) -> bool:
        keywords = ["how many", "utilization", "occupied", "count", "seats for project"]
        return any(k in query.lower() for k in keywords)

    def parse(self, query: str) -> ParsedIntent:
        proj_m = self.PROJECT_RE.search(query)
        floor_m = self.FLOOR_RE.search(query)
        return ParsedIntent(
            intent="seat_utilization",
            entities={
                "project_name": proj_m.group(1) if proj_m else None,
                "floor": int(floor_m.group(1)) if floor_m else None,
            },
            confidence=0.95,
        )


class AllocateSeatHandler(IntentHandler):
    """Handles: 'allocate a seat for new employee joining today'"""

    def matches(self, query: str) -> bool:
        keywords = ["allocate", "assign seat", "new joiner", "new employee", "joining"]
        return any(k in query.lower() for k in keywords)

    def parse(self, query: str) -> ParsedIntent:
        EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[a-z]+", re.I)
        email = EMAIL_RE.search(query)
        return ParsedIntent(
            intent="allocate_seat",
            entities={"email": email.group(0) if email else None},
            confidence=0.8,
        )


class NeighborHandler(IntentHandler):
    """Handles: 'who is sitting near me?', 'neighbors of Amit'"""

    def matches(self, query: str) -> bool:
        keywords = ["near me", "sitting near", "neighbor", "next to", "around me"]
        return any(k in query.lower() for k in keywords)

    def parse(self, query: str) -> ParsedIntent:
        EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[a-z]+", re.I)
        email = EMAIL_RE.search(query)
        NAME_RE = re.compile(r"near\s+(?:me|(.+?))\b", re.I)
        m = NAME_RE.search(query)
        name = m.group(1) if m and m.lastindex and m.group(1) else None
        return ParsedIntent(
            intent="find_neighbors",
            entities={"name": name, "email": email.group(0) if email else None},
            confidence=0.95,
        )


class IntentParser:
    """
    Orchestrates all handlers.
    Open/Closed: add new handlers to _handlers list, no other changes needed.
    """

    def __init__(self):
        self._handlers: list[IntentHandler] = [
            # Higher-specificity handlers first to win on overlapping keywords
            SeatUtilizationHandler(),    # "how many", "utilization" — before project handler
            NeighborHandler(),           # "near me", "sitting near" — before seat location
            SeatLocationHandler(),
            ProjectAssignmentHandler(),
            AvailableSeatsHandler(),
            AllocateSeatHandler(),
        ]

    def parse(self, query: str) -> ParsedIntent:
        query_clean = query.strip()
        best: Optional[ParsedIntent] = None
        best_conf = 0.0

        for handler in self._handlers:
            if handler.matches(query_clean):
                result = handler.parse(query_clean)
                if result.confidence > best_conf:
                    best = result
                    best_conf = result.confidence

        if best:
            return best

        return ParsedIntent(
            intent="unknown",
            entities={},
            confidence=0.0,
        )
