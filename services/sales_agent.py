"""Conversational sales agent: understands the customer, recommends an aircraft, persuades,
handles objections and closes by handing a brief to an advisor.

Pipeline per message:
  NLP (services.nlp)  ->  intent + merged TripNeeds
  Recommender         ->  ranked aircraft with prices from the CSV database
  Writer              ->  OpenAI (grounded on the facts JSON) or a built-in template fallback

The writer may only use numbers present in the facts; an LLM reply that mentions any other
money amount is discarded and the template is used instead.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field, replace
from typing import Any, Callable

import openai

from config import LLMSettings, get_llm_settings
from services.charter_db import CharterDB
from services.nlp import NEED_LABELS, ParsedMessage, TripNeeds, parse_message
from services.recommender import Candidate, Recommendation, candidate_for, compare, recommend

logger = logging.getLogger("charter.agent")

GREETING = (
    "Hello, and welcome aboard! ✈️ I'm your private charter concierge. Tell me a little about your trip - "
    "**how many people are flying**, roughly **where to**, and **what matters most** (budget, space, luggage, "
    "a special occasion...). I'll match you with the right aircraft from our guide of {count} jets."
)

SYSTEM_PROMPT = """You are a warm, confident private-jet charter sales concierge for an independent demo app.
Goal: help the customer choose the right aircraft and feel great about it, then invite them to click
"Choose this aircraft" so an advisor can confirm availability and the final quote.

Rules:
1. Use ONLY the facts in the JSON. Never invent prices, specs, availability or features.
2. Prices are indicative averages in USD; repeat them exactly as given. Never compute new prices.
3. Match the customer's mood: if "stressed", be calm and reassuring first; if "celebrating", be warm
   and celebratory; otherwise upbeat and professional.
4. Lead with the best match and the 2-3 reasons it fits THIS customer. Then mention the other options
   in one sentence each (upgrade for more space, best value to save).
5. If within_budget is false for every option, be honest and recommend the closest option.
6. If "missing_info" is not empty, end with ONE friendly question asking for the first missing item.
7. Never claim a booking, hold or confirmed availability. 90-160 words. Use **bold** for aircraft names.
   No headings, no tables."""

_MONEY_RE = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)\s*([kKmM])?\b")
_CHOOSE_PRONOUN = re.compile(
    r"\b(take it|book it|that one|this one|go with (it|that|this)|first one|best match|let'?s do it|"
    r"sounds (good|great|perfect)|i'?ll take|lock it in|choose it|we'?ll take)\b", re.I)
_OPTION_N = re.compile(r"\b(?:option|number|#)\s*([123])\b", re.I)


@dataclass(frozen=True)
class AgentState:
    needs: TripNeeds = TripNeeds()
    last_picks: tuple[str, ...] = ()
    chosen: str | None = None


@dataclass
class AgentReply:
    text: str
    cards: list[Candidate] = field(default_factory=list)
    comparison: list[Candidate] = field(default_factory=list)
    chosen: Candidate | None = None
    engine: str = "template"          # "openai" | "template"
    parsed: ParsedMessage | None = None


ClientFactory = Callable[[LLMSettings], Any]


def _fmt(n: int | None) -> str:
    return f"${n:,.0f}" if n is not None else "n/a"


def missing_info(needs: TripNeeds) -> list[str]:
    out = []
    if not needs.passengers:
        out.append("passengers")
    if not (needs.origin and needs.destination) and not needs.flight_hours:
        out.append("route")
    if not needs.budget_usd:
        out.append("budget")
    return out


def _price_basis(c: Candidate, needs: TripNeeds) -> str:
    if c.price.basis == "route_average":
        return f"average one-way price for {needs.origin} → {needs.destination}"
    hours = c.price.hours or 2
    return f"estimate for a {hours:g}-hour flight at {_fmt(c.price.hourly_rate)}/hr"


# --------------------------------------------------------------- facts ------
def candidate_facts(c: Candidate, needs: TripNeeds) -> dict:
    return {
        "role": c.role, "model": c.model_name, "category": c.category_label, "seats": c.passengers,
        "price_usd": c.price.amount, "price_basis": _price_basis(c, needs), "within_budget": c.within_budget,
        "max_range_hours": c.max_range_hours, "baggage_cuft": c.baggage_cuft, "cabin": c.cabin,
        "lavatory": c.lavatory, "fuel_stops_on_route": c.fuel_stops, "why_it_fits": list(c.reasons),
        "match_score": c.score,
    }


def build_facts(needs: TripNeeds, intent: str, cards: list[Candidate], comparison: list[Candidate],
                chosen: Candidate | None, notes: tuple[str, ...]) -> dict:
    return {
        "customer": {
            "passengers": needs.passengers, "budget_usd": needs.budget_usd,
            "budget_is_hard_cap": needs.budget_is_cap, "origin": needs.origin, "destination": needs.destination,
            "flight_hours": needs.flight_hours, "priorities": [NEED_LABELS[n] for n in sorted(needs.needs)],
            "mood": needs.mood,
        },
        "intent": intent,
        "options": [candidate_facts(c, needs) for c in cards],
        "comparison": [candidate_facts(c, needs) for c in comparison],
        "chosen_aircraft": candidate_facts(chosen, needs) if chosen else None,
        "notes": list(notes),
        "missing_info": missing_info(needs) if intent not in ("choose",) else [],
        "disclaimer": "Indicative average prices; availability and final quote confirmed by an advisor.",
    }


def _allowed_amounts(obj: Any, out: set[float]) -> set[float]:
    if isinstance(obj, bool):
        return out
    if isinstance(obj, (int, float)):
        out.add(float(obj))
    elif isinstance(obj, str):
        for m in _MONEY_RE.finditer(obj):
            out.add(float(m.group(1).replace(",", "")))
    elif isinstance(obj, dict):
        for v in obj.values():
            _allowed_amounts(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _allowed_amounts(v, out)
    return out


def ungrounded_amounts(text: str, facts: dict) -> list[str]:
    allowed = _allowed_amounts(facts, set())
    bad = []
    for m in _MONEY_RE.finditer(text):
        value = float(m.group(1).replace(",", ""))
        suffix = (m.group(2) or "").lower()
        value *= 1_000 if suffix == "k" else 1_000_000 if suffix == "m" else 1
        if value not in allowed:
            bad.append(m.group(0))
    return bad


# ------------------------------------------------------------ templates -----
OPENERS = {
    "stressed": "I completely understand - let me take the stress out of this for you. Here's the option I'd trust:",
    "celebrating": "What a wonderful reason to fly private! 🎉 Here's the jet I'd pick to make it unforgettable:",
    "positive": "Love it - let's find your perfect jet. My top pick:",
    "neutral": "Thanks - based on what you've told me, here's my recommendation:",
}
FOLLOW_UPS = {
    "passengers": "How many passengers will be flying? I'll make sure everyone has a comfortable seat.",
    "route": "Where are you flying from and to? I'll swap in the average price for that exact route.",
    "budget": "Do you have a budget in mind? I'll find the most aircraft for your money.",
}


def template_reply(facts: dict) -> str:
    intent, cust = facts["intent"], facts["customer"]
    opts, comp, chosen = facts["options"], facts["comparison"], facts["chosen_aircraft"]
    lines: list[str] = []

    if chosen:
        lines.append(f"Excellent choice - the **{chosen['model']}** is a superb fit. ✨")
        lines.append(f"{chosen['seats']} seats, {chosen['max_range_hours']:g} h range and "
                     f"{chosen['baggage_cuft']:g} ft³ of baggage space, at an average of "
                     f"**{_fmt(chosen['price_usd'])}** ({chosen['price_basis']}).")
        lines.append("I've prepared your **advisor brief** below. A private aviation advisor will confirm live "
                     "availability and your final all-in quote - no commitment until you approve it.")
        return "\n\n".join(lines)

    if intent == "compare" and comp:
        lines.append("Here's how they stack up side by side:")
        lines.append("\n".join(
            f"- **{c['model']}** ({c['category']}): {c['seats']} seats, {c['max_range_hours']:g} h range, "
            f"{c['baggage_cuft']:g} ft³ baggage, {c['lavatory'].lower() or 'unlisted'} lavatory - "
            f"{_fmt(c['price_usd'])} average" for c in comp))
        best = max(comp, key=lambda c: (c["within_budget"] is not False, c["match_score"]))
        others = [c for c in comp if c is not best]
        why = "it scores higher on what matters to you"
        if others and best["price_usd"] < others[0]["price_usd"]:
            why = f"it does the job for {_fmt(others[0]['price_usd'] - best['price_usd'])} less"
        elif others and best["seats"] > others[0]["seats"]:
            why = f"it gives you {best['seats'] - others[0]['seats']} more seat(s) of breathing room"
        lines.append(f"For your trip I'd lean towards the **{best['model']}** - {why}.")
        lines.append("Want me to put it forward? Just say **“I'll take the " + best["model"] + "”**.")
        return "\n\n".join(lines)

    if intent == "details" and comp:
        c = comp[0]
        lines.append(f"The **{c['model']}** is a {c['category']} that seats {c['seats']}.")
        lines.append(f"- Cabin: {c['cabin']}\n- Range: up to {c['max_range_hours']:g} hours nonstop\n"
                     f"- Baggage: {c['baggage_cuft']:g} ft³\n- Lavatory: {c['lavatory']}\n"
                     f"- Average price: **{_fmt(c['price_usd'])}** ({c['price_basis']})")
        lines.append("Shall I check how it compares with my top pick for you, or put it forward to an advisor?")
        return "\n\n".join(lines)

    if not opts:
        lines.append(" ".join(facts["notes"]) or "I couldn't find an aircraft that matches yet.")
        lines.append("Could you tell me a little more - group size, route or budget?")
        return "\n\n".join(lines)

    best = opts[0]
    if intent == "cheaper":
        lines.append("Absolutely - let's bring the cost down without compromising the experience.")
    elif intent == "upgrade":
        lines.append("Let's treat you to a bit more space and comfort.")
    else:
        lines.append(OPENERS.get(cust["mood"], OPENERS["neutral"]))
    lines.extend(f"_{n}_" for n in facts["notes"])

    all_over = intent == "recommend" and cust["budget_usd"] and all(o["within_budget"] is False for o in opts)
    if all_over:
        lines.append(f"Honest take: nothing in the guide fits **{_fmt(cust['budget_usd'])}** on this trip. "
                     f"The closest is the **{best['model']}** at **{_fmt(best['price_usd'])}** - "
                     "an advisor may find a better rate on a repositioning (empty-leg) flight.")
    else:
        lines.append(f"**{best['model']}** ({best['category']}) - **{_fmt(best['price_usd'])}** average "
                     f"({best['price_basis']}).")
    lines.append("\n".join(f"- {r}" for r in best["why_it_fits"]))

    extras = []
    for o in opts[1:]:
        if o["role"] == "Upgrade":
            extras.append(f"want more room? The **{o['model']}** ({o['category']}, {o['seats']} seats) "
                          f"is {_fmt(o['price_usd'])}")
        elif o["role"] == "Best value":
            extras.append(f"prefer to save? The **{o['model']}** is {_fmt(o['price_usd'])}")
        else:
            extras.append(f"the **{o['model']}** is a strong alternative at {_fmt(o['price_usd'])}")
    if extras:
        lines.append("Also worth a look: " + "; ".join(extras) + ".")

    lines.append(f"If the **{best['model']}** feels right, tap **Choose this aircraft** and I'll prepare your advisor brief.")
    if facts["missing_info"]:
        lines.append(FOLLOW_UPS[facts["missing_info"][0]])
    return "\n\n".join(lines)


# ---------------------------------------------------------------- agent -----
class SalesAgent:
    def __init__(self, db: CharterDB, settings: LLMSettings | None = None,
                 client_factory: ClientFactory | None = None) -> None:
        self.db = db
        self.settings = settings or get_llm_settings()
        self._client_factory = client_factory or (
            lambda s: openai.OpenAI(api_key=s.api_key, timeout=s.timeout_seconds, max_retries=1))
        self._client: Any = None
        self.models = dict(zip(db.aircraft.model_name, db.aircraft.slug))

    @property
    def llm_enabled(self) -> bool:
        return self.settings.enabled

    def greeting(self) -> str:
        return GREETING.format(count=len(self.db.aircraft))

    # ----- main entry ---------------------------------------------------
    def respond(self, message: str, state: AgentState, history: list[dict] | None = None) -> tuple[AgentReply, AgentState]:
        parsed = parse_message(message, self.db.cities(), self.models)
        intent = parsed.intent
        if intent == "reset":
            return AgentReply(self.greeting(), parsed=parsed), AgentState()

        needs = state.needs.merge(parsed.needs)
        mentions = parsed.aircraft_mentions
        option_n = _OPTION_N.search(message)
        if intent != "choose" and state.last_picks and (_CHOOSE_PRONOUN.search(message) or option_n):
            idx = int(option_n.group(1)) - 1 if option_n else 0
            if idx < len(state.last_picks):
                mentions, intent = (state.last_picks[idx],), "choose"

        cards: list[Candidate] = []
        comparison: list[Candidate] = []
        chosen: Candidate | None = None
        notes: tuple[str, ...] = ()
        new_state = replace(state, needs=needs)

        if intent == "choose" and mentions:
            chosen = candidate_for(self.db, mentions[0], needs)
            if chosen is None:
                notes = ("That aircraft isn't suitable for this route (range or capacity).",)
                intent = "recommend"
            else:
                new_state = replace(new_state, chosen=chosen.slug)
        elif intent in ("compare", "details") and mentions:
            comparison = compare(self.db, mentions[:3], needs)
            if not comparison:
                notes = ("Those aircraft can't fly this route nonstop, so here are ones that can.",)
                intent = "recommend"

        if intent in ("recommend", "cheaper", "upgrade"):
            if not (needs.passengers or needs.needs or needs.budget_usd or needs.origin or needs.flight_hours):
                text = ("I'd love to help! To recommend the right aircraft, could you tell me how many people are "
                        "flying and what matters most to you - price, space, luggage or a special occasion?")
                return AgentReply(text, parsed=parsed), new_state
            shift = intent if intent in ("cheaper", "upgrade") else None
            rec: Recommendation = recommend(self.db, needs, shift=shift,
                                            anchor_slug=state.last_picks[0] if state.last_picks and shift else None)
            cards = list(rec.picks)
            notes = notes + rec.notes
            if cards:
                new_state = replace(new_state, last_picks=tuple(c.slug for c in cards))

        facts = build_facts(needs, intent, cards, comparison, chosen, notes)
        text, engine = self._write(facts, history or [])
        return AgentReply(text, cards, comparison, chosen, engine, parsed), new_state

    # ----- writer -------------------------------------------------------
    def _write(self, facts: dict, history: list[dict]) -> tuple[str, str]:
        fallback = template_reply(facts)
        if not self.llm_enabled:
            return fallback, "template"
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for h in history[-6:]:
            if h.get("role") in ("user", "assistant") and h.get("content"):
                messages.append({"role": h["role"], "content": str(h["content"])[:800]})
        messages.append({"role": "user", "content": "FACTS (JSON):\n" + json.dumps(facts, ensure_ascii=False)})
        try:
            if self._client is None:
                self._client = self._client_factory(self.settings)
            resp = self._client.chat.completions.create(
                model=self.settings.model, messages=messages,
                max_completion_tokens=self.settings.max_output_tokens,
            )
            text = (resp.choices[0].message.content or "").strip()
        except (openai.OpenAIError, AttributeError, IndexError, TypeError) as exc:
            logger.warning("llm unavailable (%s) - using template", type(exc).__name__)
            return fallback, "template"
        if not text:
            return fallback, "template"
        if bad := ungrounded_amounts(text, facts):
            logger.warning("llm reply rejected: %d ungrounded amounts", len(bad))
            return fallback, "template"
        return text, "openai"
