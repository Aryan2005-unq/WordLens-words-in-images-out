"""Lightweight query parsing and transparent synonym-based expansion."""

from dataclasses import dataclass
from datetime import date, timedelta
import calendar
import re


@dataclass(frozen=True)
class SearchPlan:
    semantic_query: str
    start_date: date | None = None
    end_date: date | None = None
    date_expression: str | None = None


YEAR = r"(?:19|20)\d{2}"
MONTHS = {name.lower(): number for number, name in enumerate(calendar.month_name) if name}
MONTHS.update({name.lower(): number for number, name in enumerate(calendar.month_abbr) if name})


def _year_bounds(year: int) -> tuple[date, date]:
    return date(year, 1, 1), date(year, 12, 31)


def parse_search_query(query: str, today: date | None = None) -> SearchPlan:
    """Extract common date phrases and leave the remaining words for CLIP."""
    reference = today or date.today()
    patterns = (
        (rf"\bbetween\s+({YEAR})\s+and\s+({YEAR})\b", "year_range"),
        (rf"\bfrom\s+({YEAR})\s+to\s+({YEAR})\b", "year_range"),
        (r"\b(?:on|from|during|in)?\s*(\d{4}-\d{2}-\d{2})\b", "iso_date"),
        (r"\b(?:on\s+)?([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?[,]?\s+(\d{4})\b", "month_day_year"),
        (r"\b(?:in|during|from|on)?\s*([A-Za-z]+)\s+(\d{4})\b", "month_year"),
        (r"\b(?:in|during|from)?\s*(last year|this year|last month|this month|yesterday|today)\b", "relative"),
        (rf"\b(?:in|during|from)\s+({YEAR})\b", "year"),
        (rf"\b({YEAR})\b", "year"),
    )

    for pattern, kind in patterns:
        match = re.search(pattern, query, flags=re.IGNORECASE)
        if not match:
            continue
        expression = match.group(0).strip()
        start: date
        end: date
        try:
            if kind == "year_range":
                first, second = sorted((int(match.group(1)), int(match.group(2))))
                start, _ = _year_bounds(first)
                _, end = _year_bounds(second)
            elif kind == "iso_date":
                start = end = date.fromisoformat(match.group(1))
            elif kind == "month_day_year":
                month = MONTHS.get(match.group(1).lower())
                if month is None:
                    continue
                start = end = date(int(match.group(3)), month, int(match.group(2)))
            elif kind == "month_year":
                month = MONTHS.get(match.group(1).lower())
                if month is None:
                    continue
                year = int(match.group(2))
                start = date(year, month, 1)
                end = date(year, month, calendar.monthrange(year, month)[1])
            elif kind == "relative":
                phrase = match.group(1).lower()
                if phrase in {"this year", "last year"}:
                    year = reference.year - (phrase == "last year")
                    start, end = _year_bounds(year)
                elif phrase in {"this month", "last month"}:
                    year, month = reference.year, reference.month
                    if phrase == "last month":
                        month -= 1
                        if month == 0:
                            year -= 1
                            month = 12
                    start = date(year, month, 1)
                    end = date(year, month, calendar.monthrange(year, month)[1])
                else:
                    day = reference + timedelta(days=-1 if phrase == "yesterday" else 0)
                    start = end = day
            else:
                start, end = _year_bounds(int(match.group(1)))
        except (ValueError, OverflowError):
            continue

        semantic_query = (query[: match.start()] + " " + query[match.end() :]).strip()
        semantic_query = re.sub(r"[\s,.;:]+", " ", semantic_query).strip()
        return SearchPlan(semantic_query or "photo", start, end, expression)

    return SearchPlan(query.strip() or "photo")


# Small, transparent English synonym map. Expansions are shown in the UI so users
# can see what changed; original query is always retained as the first variant.
SYNONYMS = {
    "beach": ("shore", "seaside"),
    "bird": ("flying bird",),
    "boat": ("sailboat", "ship"),
    "cake": ("dessert",),
    "car": ("automobile",),
    "cat": ("kitten",),
    "celebration": ("party", "festive gathering"),
    "college": ("university",),
    "dog": ("puppy",),
    "festival": ("celebration", "festive event"),
    "flower": ("blossom",),
    "forest": ("woods",),
    "friends": ("group of people",),
    "mountain": ("mountain peak",),
    "ocean": ("sea",),
    "people": ("crowd", "group of people"),
    "puppy": ("dog",),
    "snow": ("snowy winter scene",),
    "sunrise": ("dawn",),
    "sunset": ("dusk",),
    "tree": ("woodland",),
}


def expand_query(query: str, max_variants: int = 4) -> list[str]:
    """Create deterministic synonym variants without replacing the original."""
    original = query.strip()
    if not original:
        return ["photo"]
    variants = [original]
    for match in re.finditer(r"[A-Za-z]+", original):
        word = match.group(0).lower()
        key = word
        if key not in SYNONYMS:
            if key.endswith("ies"):
                key = key[:-3] + "y"
            elif key.endswith("es"):
                key = key[:-2]
            elif key.endswith("s"):
                key = key[:-1]
        alternatives = SYNONYMS.get(key, ())
        for alternative in alternatives:
            variant = original[: match.start()] + alternative + original[match.end() :]
            if variant.casefold() not in {item.casefold() for item in variants}:
                variants.append(variant)
            if len(variants) >= max_variants:
                return variants
    return variants
