"""Natural-language understanding for the charter sales assistant.

AI methods used (all local, no API needed):
* TextBlob sentiment polarity + a small travel-domain lexicon -> customer mood (tone of reply)
* TextBlob spelling correction -> tolerant keyword and city matching ("Lodnon" -> London)
* TextBlob noun phrases (when the corpora are installed) -> shown as extracted topics
* Regex entity extraction -> passengers, budget, flight hours
* Fuzzy matching (difflib) -> cities and aircraft model names despite typos
* Keyword intent classification -> recommend / cheaper / upgrade / compare / details / choose / reset
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field, replace

from textblob import TextBlob

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "a couple": 2, "couple": 2, "a dozen": 12, "dozen": 12,
}
_NUM = r"(\d{1,2}|" + "|".join(sorted(NUMBER_WORDS, key=len, reverse=True)) + r")"

CITY_ALIASES = {
    "nyc": "New York", "new york city": "New York", "manhattan": "New York", "teterboro": "New York",
    "la": "Los Angeles", "lax": "Los Angeles", "vegas": "Las Vegas", "sf": "San Francisco",
    "san fran": "San Francisco", "fort lauderdale": "South Florida", "palm beach": "South Florida",
    "bahamas": "Nassau", "milano": "Milan", "roma": "Rome", "eivissa": "Ibiza",
}

# What each "need" means and the words that signal it.
NEED_KEYWORDS = {
    "value": ["cheap", "cheapest", "affordable", "budget-friendly", "save", "saving", "economical",
              "low cost", "inexpensive", "best price", "best deal", "value", "tight budget"],
    "luxury": ["luxury", "luxurious", "vip", "premium", "comfort", "comfortable", "spacious", "roomy",
               "stand up", "standup", "impress", "elegant", "first class", "best jet", "top of the line"],
    "baggage": ["luggage", "baggage", "bags", "suitcase", "suitcases", "golf", "ski", "skis",
                "equipment", "gear", "cargo"],
    "lavatory": ["toilet", "lavatory", "restroom", "bathroom", "washroom"],
    "speed": ["fast", "faster", "fastest", "quick", "quickest", "asap", "urgent", "hurry"],
    "nonstop": ["nonstop", "non-stop", "non stop", "direct", "no stops", "without stopping"],
    "family": ["kids", "children", "child", "family", "baby", "toddler", "pets", "pet", "dog", "elderly",
               "grandparents", "parents"],
    "business": ["business", "meeting", "work", "conference", "clients", "executives", "board", "team"],
    "long_haul": ["overnight", "sleep", "long flight", "long-haul", "long haul", "transatlantic", "across the"],
}
NEED_LABELS = {
    "value": "Best value", "luxury": "Luxury & cabin space", "baggage": "Extra luggage",
    "lavatory": "Private lavatory", "speed": "Speed", "nonstop": "Nonstop",
    "family": "Family-friendly", "business": "Work-friendly cabin", "long_haul": "Long-haul comfort",
}

STRESS_WORDS = ["stress", "stressed", "stressful", "nightmare", "worried", "anxious", "nervous", "urgent",
                "emergency", "frustrated", "annoyed", "upset", "disappointed", "funeral", "sick", "medical",
                "hospital", "terrible", "awful", "scared", "afraid"]
CELEBRATE_WORDS = ["honeymoon", "birthday", "anniversary", "wedding", "celebrate", "celebration",
                   "vacation", "holiday", "bachelor", "bachelorette", "graduation", "proposal", "getaway"]

INTENT_KEYWORDS = {
    "reset": ["start over", "reset", "new search", "clear", "begin again"],
    "choose": ["i'll take", "i will take", "i'll go with", "go with", "choose", "select", "book",
               "reserve", "let's do", "i want the", "sounds good", "perfect, ", "i'll choose", "lock in"],
    "compare": [" vs ", " versus ", "compare", "difference between", "which is better"],
    "cheaper": ["too expensive", "cheaper", "lower price", "less expensive", "over budget",
                "out of budget", "can't afford", "cannot afford", "cost less", "something cheaper"],
    "upgrade": ["bigger", "larger", "more space", "more room", "upgrade", "more luxurious", "nicer",
                "better jet", "something bigger", "more comfortable"],
    "details": ["tell me about", "more about", "details", "specs", "what about", "info on", "describe"],
}


@dataclass(frozen=True)
class TripNeeds:
    """Everything the assistant has understood so far (merged across turns)."""

    passengers: int | None = None
    budget_usd: int | None = None
    budget_is_cap: bool = False
    origin: str | None = None
    destination: str | None = None
    flight_hours: float | None = None
    needs: frozenset[str] = frozenset()
    mood: str = "neutral"          # neutral | positive | stressed | celebrating
    polarity: float = 0.0

    def merge(self, newer: "TripNeeds") -> "TripNeeds":
        return replace(
            self,
            passengers=newer.passengers or self.passengers,
            budget_usd=newer.budget_usd or self.budget_usd,
            budget_is_cap=newer.budget_is_cap if newer.budget_usd else self.budget_is_cap,
            origin=newer.origin or self.origin,
            destination=newer.destination or self.destination,
            flight_hours=newer.flight_hours or self.flight_hours,
            needs=self.needs | newer.needs,
            mood=newer.mood if newer.mood != "neutral" else self.mood,
            polarity=newer.polarity,
        )


@dataclass(frozen=True)
class ParsedMessage:
    needs: TripNeeds
    intent: str
    aircraft_mentions: tuple[str, ...]   # slugs, in order of mention
    corrected_text: str
    topics: tuple[str, ...] = field(default_factory=tuple)


# ------------------------------------------------------------------ helpers -
def _to_int(token: str) -> int | None:
    token = token.lower().strip()
    if token.isdigit():
        return int(token)
    return NUMBER_WORDS.get(token)


def _contains(text: str, phrase: str) -> bool:
    return re.search(r"(?<![a-z])" + re.escape(phrase) + r"(?![a-z])", text) is not None


def correct_spelling(text: str) -> str:
    """TextBlob spelling correction, applied word-by-word only to plain lowercase words so that
    numbers, money, and capitalised names (aircraft models) are left untouched."""
    if len(text) > 400:
        return text
    out = []
    for word in re.findall(r"\S+|\s+", text):
        core = word.strip(".,!?;:")
        if core.isalpha() and core.islower() and len(core) > 3:
            fixed = str(TextBlob(core).correct())
            out.append(word.replace(core, fixed))
        else:
            out.append(word)
    return "".join(out)


def extract_passengers(text: str) -> int | None:
    t = text.lower()
    patterns = [
        rf"(?:family|group|party|team) of {_NUM}",
        rf"{_NUM}\s+(?:of us|people|persons|person|passengers|passenger|pax|guests|adults|travell?ers"
        rf"|seats|friends|colleagues|executives|members|guys|girls|ladies)",
        rf"(?:we are|we're|there are|there will be) {_NUM}",
        rf"for {_NUM}(?!\s*(?:hours?|hrs?|days?|nights?|k\b|m\b|thousand|million|grand|\$|usd|dollars))\b",
    ]
    for pattern in patterns:
        m = re.search(pattern, t)
        if m and (n := _to_int(m.group(1))):
            return n
    if re.search(r"\b(me and my (wife|husband|partner|girlfriend|boyfriend|fianc[eé]e?)|my (wife|husband) and i|couple)\b", t):
        return 2
    if re.search(r"\b(just me|only me|solo|alone|by myself|myself only)\b", t):
        return 1
    return None


_MONEY = re.compile(
    r"(?P<dollar>\$|usd\s?)?\s?(?P<num>\d[\d,]*(?:\.\d+)?)\s*(?P<unit>k|m|thousand|million|grand|mil)?\b"
    r"\s*(?P<word>usd|dollars|bucks)?",
    re.IGNORECASE,
)


def extract_budget(text: str) -> tuple[int | None, bool]:
    """Returns (amount, is_hard_cap). Only numbers that look like money are considered."""
    t = text.lower()
    best: int | None = None
    for m in _MONEY.finditer(t):
        has_money_marker = bool(m.group("dollar") or m.group("unit") or m.group("word"))
        if not has_money_marker:
            continue
        value = float(m.group("num").replace(",", ""))
        unit = (m.group("unit") or "").lower()
        if unit in ("k", "thousand", "grand"):
            value *= 1_000
        elif unit in ("m", "million", "mil"):
            value *= 1_000_000
        if value < 1_000:  # "$500" is not a charter budget; avoids matching hours etc.
            continue
        best = max(best or 0, int(value))
    if best is None:
        return None, False
    cap = bool(re.search(r"\b(under|below|max|maximum|up to|less than|no more than|at most|within|cap)\b", t))
    return best, cap


def extract_hours(text: str) -> float | None:
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|to)?\s*(?:hours?|hrs?|h)\b\s*(?:flight|trip|journey|long)?", text.lower())
    return float(m.group(1)) if m else None


def extract_cities(text: str, known_cities: list[str]) -> tuple[str | None, str | None]:
    """Find cities (exact, alias or fuzzy) and decide origin/destination from 'from'/'to' cues."""
    t = " " + text.lower() + " "
    lookup = {c.lower(): c for c in known_cities}
    lookup.update({k: v for k, v in CITY_ALIASES.items() if v in known_cities})
    hits: list[tuple[int, str]] = []
    for phrase in sorted(lookup, key=len, reverse=True):
        for m in re.finditer(r"(?<![a-z])" + re.escape(phrase) + r"(?![a-z])", t):
            if not any(start <= m.start() < start + 30 and city == lookup[phrase] for start, city in hits):
                hits.append((m.start(), lookup[phrase]))
    if len({c for _, c in hits}) < 2:  # fuzzy pass for typos on single words
        names = [c.lower() for c in known_cities]
        for m in re.finditer(r"[a-z]{4,}", t):
            match = difflib.get_close_matches(m.group(), names, n=1, cutoff=0.8)
            if match and lookup[match[0]] not in {c for _, c in hits}:
                hits.append((m.start(), lookup[match[0]]))
    hits.sort()
    unique: list[tuple[int, str]] = []
    for pos, city in hits:
        if city not in [c for _, c in unique]:
            unique.append((pos, city))
    origin = destination = None
    for pos, city in unique:
        before = t[max(0, pos - 8):pos]
        if re.search(r"\b(to|into|towards|toward|arrive|arriving)\s*$", before):
            destination = destination or city
        elif re.search(r"\b(from|leaving|depart|departing|out of)\s*$", before):
            origin = origin or city
    rest = [c for _, c in unique if c not in (origin, destination)]
    if origin is None and rest:
        origin = rest.pop(0)
    if destination is None and rest:
        destination = rest.pop(0)
    return origin, destination


def extract_needs(text: str) -> frozenset[str]:
    t = text.lower()
    return frozenset(need for need, words in NEED_KEYWORDS.items() if any(_contains(t, w) for w in words))


def detect_mood(text: str) -> tuple[str, float]:
    polarity = float(TextBlob(text).sentiment.polarity)
    t = text.lower()
    # Price words ("expensive") are objections, not distress - only clear signals count.
    if any(_contains(t, w) for w in STRESS_WORDS) or polarity <= -0.6:
        return "stressed", polarity
    if any(_contains(t, w) for w in CELEBRATE_WORDS):
        return "celebrating", polarity
    if polarity >= 0.35:
        return "positive", polarity
    return "neutral", polarity


def detect_intent(text: str, aircraft_mentions: tuple[str, ...]) -> str:
    t = " " + text.lower() + " "
    for intent in ("reset", "compare", "cheaper", "upgrade", "choose", "details"):
        if any(k in t for k in INTENT_KEYWORDS[intent]):
            if intent == "compare" and len(aircraft_mentions) < 2:
                continue
            if intent in ("choose", "details") and not aircraft_mentions:
                continue
            return intent
    if len(aircraft_mentions) >= 2:
        return "compare"
    if len(aircraft_mentions) == 1 and len(t.split()) <= 8:
        return "details"
    return "recommend"


def find_aircraft(text: str, models: dict[str, str]) -> tuple[str, ...]:
    """models: {model_name: slug}. Matches full names, distinctive short names ("CJ3", "XLS"),
    Gulfstream shorthand ("G650"), and typos."""
    t = re.sub(r"(?<![a-z0-9])g[- ]?(\d{3})(?![0-9])", r"gulfstream \1", text.lower())
    found: list[tuple[int, str]] = []
    spans: list[tuple[int, int]] = []
    for name, slug in models.items():
        m = re.search(r"(?<![a-z0-9])" + re.escape(name.lower()) + r"(?![a-z0-9])", t)
        if m:
            found.append((m.start(), slug))
            spans.append(m.span())
    for name, slug in models.items():
        if slug in [s for _, s in found]:
            continue
        # The name without its maker prefix - only if it is distinctive (not a bare number).
        short = re.sub(r"^(citation|gulfstream|challenger|falcon|global|lear|hawker|king air|"
                       r"phenom|legacy|beechjet|premier|nextant|praetor)\s+", "", name.lower())
        if short == name.lower() or short.isdigit() or len(short) < 3:
            continue
        m = re.search(r"(?<![a-z0-9])" + re.escape(short) + r"(?![a-z0-9])", t)
        if m and not any(a <= m.start() < b for a, b in spans):
            found.append((m.start(), slug))
            spans.append(m.span())
    if not found:  # typo-tolerant pass over 2-3 word windows
        words = re.findall(r"[a-z0-9/]+", t)
        names = {n.lower(): s for n, s in models.items()}
        for size in (3, 2):
            for i in range(len(words) - size + 1):
                window = " ".join(words[i:i + size])
                match = difflib.get_close_matches(window, names, n=1, cutoff=0.86)
                if match and names[match[0]] not in [s for _, s in found]:
                    found.append((i, names[match[0]]))
    return tuple(s for _, s in sorted(found))


def noun_phrases(text: str) -> tuple[str, ...]:
    try:
        return tuple(dict.fromkeys(str(p) for p in TextBlob(text).noun_phrases))[:6]
    except Exception:  # corpora not downloaded - optional feature
        return ()


def parse_message(text: str, known_cities: list[str], models: dict[str, str]) -> ParsedMessage:
    corrected = correct_spelling(text)
    both = f"{text} \n {corrected}"
    mentions = find_aircraft(text, models) or find_aircraft(corrected, models)
    origin, destination = extract_cities(text, known_cities)
    if not (origin and destination):
        o2, d2 = extract_cities(corrected, known_cities)
        origin, destination = origin or o2, destination or d2
    if origin and destination == origin:
        destination = None
    budget, cap = extract_budget(text)
    mood, polarity = detect_mood(corrected)
    needs = TripNeeds(
        passengers=extract_passengers(both),
        budget_usd=budget,
        budget_is_cap=cap,
        origin=origin,
        destination=destination,
        flight_hours=extract_hours(text),
        needs=extract_needs(both),
        mood=mood,
        polarity=polarity,
    )
    return ParsedMessage(needs, detect_intent(both, mentions), mentions, corrected, noun_phrases(corrected))
