"""Presentation components for the charter concierge.

Every value interpolated into HTML goes through ``esc``. Aircraft images and specs come from
the public Flygreen Aircraft Guide (attributed in the footer and detail view).
"""

from __future__ import annotations

import hashlib
import html
from datetime import date

import streamlit as st

from services.nlp import NEED_LABELS, TripNeeds
from services.recommender import Candidate


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _html(markup: str) -> None:
    # Strip indentation and blank lines so Markdown never turns HTML into a code block.
    st.markdown("\n".join(line.strip() for line in markup.splitlines() if line.strip()), unsafe_allow_html=True)


def usd(n: int | None) -> str:
    return f"${n:,.0f}" if n is not None else "n/a"


def _img(url: str, alt: str) -> str:
    return f'<img src="{esc(url)}" alt="{esc(alt)}" loading="lazy" referrerpolicy="no-referrer"/>'


# ----------------------------------------------------------------- header ----
def header(aircraft_count: int, route_count: int) -> None:
    _html(
        f"""
        <div class="fg-hero">
          <div class="fg-hero-top">
            <span class="fg-eyebrow">Private charter · AI concierge</span>
            <span class="fg-pill" title="Not an official Flygreen product; no endorsement implied.">
              Independent demo concept · Not affiliated with Flygreen</span>
          </div>
          <p class="fg-title">AI Charter Concierge</p>
          <p class="fg-subtitle">Tell us about your trip in your own words. Our AI understands what matters to you
            and recommends the right aircraft from {aircraft_count} jets, with average prices across {route_count} routes.</p>
        </div>
        """
    )


def terms_note() -> None:
    _html(
        '<div class="fg-terms"><b>Indicative only.</b> Prices are average one-way estimates in USD (published '
        "where available, otherwise sample estimates) and exclude taxes and fees. Nothing is booked; an advisor "
        "confirms availability and the final quote.</div>"
    )


# ------------------------------------------------------ recommendation card --
def _price_caption(c: Candidate, needs: TripNeeds) -> str:
    if c.price.basis == "route_average":
        src = "published" if c.price.source == "published" else "sample"
        return f"Average one-way · {esc(needs.origin)} → {esc(needs.destination)} · {src}"
    return f"Est. {c.price.hours or 2:g} h × {usd(c.price.hourly_rate)}/hr"


def recommendation_card(c: Candidate, needs: TripNeeds, best: bool) -> None:
    pills = [f'<span class="ac-pill">{c.passengers} seats</span>',
             f'<span class="ac-pill">{c.max_range_hours:g} h range</span>',
             f'<span class="ac-pill">{c.baggage_cuft:g} ft³ bags</span>']
    if c.within_budget is True:
        pills.append('<span class="ac-pill ok">Within budget</span>')
    elif c.within_budget is False:
        pills.append('<span class="ac-pill warn">Over budget</span>')
    if c.price.basis == "route_average":
        pills.append('<span class="ac-pill ok">Nonstop</span>' if c.fuel_stops == 0
                     else f'<span class="ac-pill warn">{c.fuel_stops} fuel stop</span>')
    why = "".join(f"<li>{esc(r)}</li>" for r in c.reasons[:3])
    _html(
        f"""
        <div class="ac-card{' best' if best else ''}">
          <div class="ac-img">{_img(c.image_url, c.model_name)}<span class="ac-role">{esc(c.role or 'Option')}</span></div>
          <div class="ac-body">
            <p class="ac-name">{esc(c.model_name)}</p>
            <div class="ac-cat">{esc(c.category_label)}</div>
            <div class="ac-price">{usd(c.price.amount)}</div>
            <div class="ac-price-cap">{_price_caption(c, needs)}</div>
            <div class="ac-pills">{''.join(pills)}</div>
            <ul class="ac-why">{why}</ul>
          </div>
        </div>
        """
    )


def comparison_table(items: list[Candidate], needs: TripNeeds) -> None:
    head = "".join(f"<th>{esc(c.model_name)}</th>" for c in items)
    rows = [
        ("", [_img(c.image_url, c.model_name) for c in items]),
        ("Category", [esc(c.category_label) for c in items]),
        ("Average price", [f"<b>{usd(c.price.amount)}</b>" for c in items]),
        ("Passengers", [str(c.passengers) for c in items]),
        ("Cabin size", [esc(c.cabin) for c in items]),
        ("Max range", [f"{c.max_range_hours:g} hours" for c in items]),
        ("Baggage", [f"{c.baggage_cuft:g} ft³" for c in items]),
        ("Lavatory", [esc(c.lavatory) for c in items]),
        ("Budget", ["Within" if c.within_budget else "Over" if c.within_budget is False else "-" for c in items]),
    ]
    body = "".join(f"<tr><td>{label}</td>{''.join(f'<td>{v}</td>' for v in vals)}</tr>" for label, vals in rows)
    _html(f'<div class="cmp-wrap"><table class="cmp"><tr><th></th>{head}</tr>{body}</table></div>')


# ----------------------------------------------------------- detail panel ---
def spec_panel(a: dict) -> None:
    """Mirrors the Aircraft Guide detail page: title, spec strip, image, description."""
    def val(key: str, fmt: str) -> str:
        v = a.get(key)
        return fmt.format(v) if v == v and v not in (None, "") else "Not listed"  # v == v filters NaN

    cabin = ("Not listed" if a.get("cabin_height_ft") != a.get("cabin_height_ft")
             else f"{a['cabin_height_ft']:g}' h x {a['cabin_width_ft']:g}' w x {a['cabin_length_ft']:g}' l")
    _html(
        f"""
        <div class="spec-title">{esc(a['model_name'])}</div>
        <div class="spec-strip">
          <div class="spec-item"><div class="spec-label">Passengers</div><div class="spec-value">{int(a['passengers'])}</div></div>
          <div class="spec-item"><div class="spec-label">Cabin size</div><div class="spec-value">{esc(cabin)}</div></div>
          <div class="spec-item"><div class="spec-label">Maximum range</div><div class="spec-value">{val('max_range_hours', '{:g} hours')}</div></div>
          <div class="spec-item"><div class="spec-label">Baggage space</div><div class="spec-value">{val('baggage_cuft', '{:g} ft³')}</div></div>
          <div class="spec-item"><div class="spec-label">Lavatory</div><div class="spec-value">{esc(a.get('lavatory') or 'Not listed')}</div></div>
        </div>
        """
    )
    left, right = st.columns([1.35, 1], gap="large")
    with left:
        _html(f'<img class="spec-img" src="{esc(a["image_url"])}" alt="{esc(a["model_name"])}" referrerpolicy="no-referrer"/>')
    with right:
        _html(f'<p class="spec-desc">{esc(a.get("description") or "")}</p>')
        _html(f'<p class="spec-src">Category: {esc(a.get("category_label", ""))}<br>Specs &amp; image: '
              f'<a href="{esc(a["detail_url"])}" target="_blank" rel="noopener noreferrer">Flygreen Aircraft Guide</a></p>')


def gallery_card(a: dict) -> None:
    _html(
        f"""
        <div class="gl-card">
          <div class="ac-img">{_img(a['image_url'], a['model_name'])}</div>
          <div class="gl-meta"><span class="gl-name">{esc(a['model_name'])}</span>
            <span class="gl-seats">👤 {int(a['passengers'])}</span></div>
        </div>
        """
    )


def section_title(text: str) -> None:
    _html(f'<div class="gl-section">{esc(text)}</div>')


# ----------------------------------------------------------- advisor brief --
def inquiry_ref(c: Candidate, needs: TripNeeds) -> str:
    raw = f"{c.slug}|{needs.passengers}|{needs.origin}|{needs.destination}|{needs.budget_usd}"
    return "INQ-" + hashlib.sha256(raw.encode()).hexdigest()[:6].upper()


def brief_text(c: Candidate, needs: TripNeeds) -> str:
    lines = [
        f"CHARTER INQUIRY BRIEF  {inquiry_ref(c, needs)}  (prepared {date.today():%d %b %Y})",
        f"Selected aircraft: {c.model_name} ({c.category_label}), {c.passengers} seats",
        f"Indicative average price: {usd(c.price.amount)} "
        + (f"one-way {needs.origin} -> {needs.destination}" if c.price.basis == "route_average"
           else f"(est. {c.price.hours or 2:g} h at {usd(c.price.hourly_rate)}/hr)"),
        f"Passengers: {needs.passengers or 'to confirm'}",
        f"Route: {needs.origin or 'to confirm'} -> {needs.destination or 'to confirm'}",
        f"Budget: {usd(needs.budget_usd) if needs.budget_usd else 'not stated'}",
        "Priorities: " + (", ".join(NEED_LABELS[n] for n in sorted(needs.needs)) or "none stated"),
        "Why this aircraft: " + "; ".join(c.reasons),
        "Advisor to confirm: availability, dates, final all-in quote (taxes & fees), airports, catering.",
        "Not a booking or quote. Independent demo concept, not affiliated with Flygreen.",
    ]
    return "\n".join(lines)


def advisor_brief(c: Candidate, needs: TripNeeds) -> None:
    left, right = st.columns([1.6, 1], gap="large")
    with left:
        _html(f'<div class="brief-head"><b>Advisor brief · {inquiry_ref(c, needs)}</b>'
              "<span>Copy into your CRM or send to an advisor</span></div>")
        text = brief_text(c, needs)
        st.code(text, language=None, wrap_lines=True)
        st.download_button("Download brief (.txt)", data=text.encode("utf-8"),
                           file_name=f"{inquiry_ref(c, needs).lower()}-brief.txt", mime="text/plain",
                           key=f"dl_{inquiry_ref(c, needs)}")
    with right:
        _html(
            '<b>What happens next</b><ol class="next-steps">'
            "<li>An advisor checks live availability of this aircraft for your dates.</li>"
            "<li>You receive a firm all-in quote, including taxes and fees.</li>"
            "<li>Nothing is charged until you approve the quote.</li></ol>"
        )


# ----------------------------------------------------------- sidebar --------
MOOD_LABELS = {"neutral": "Neutral", "positive": "Positive 🙂", "stressed": "Needs reassurance 🤝",
               "celebrating": "Celebrating 🎉"}


def profile_panel(needs: TripNeeds, topics: tuple[str, ...], engine: str) -> None:
    route = f"{needs.origin} → {needs.destination}" if needs.origin and needs.destination else (
        f"~{needs.flight_hours:g} h flight" if needs.flight_hours else "-")
    rows = [
        ("Passengers", needs.passengers or "-"),
        ("Route", route),
        ("Budget", (("≤ " if needs.budget_is_cap else "~ ") + usd(needs.budget_usd)) if needs.budget_usd else "-"),
        ("Mood", f"{MOOD_LABELS.get(needs.mood, needs.mood)} ({needs.polarity:+.2f})"),
    ]
    _html("".join(f'<div class="pf-row"><span>{esc(k)}</span><span>{esc(v)}</span></div>' for k, v in rows))
    if needs.needs:
        _html("".join(f'<span class="pf-chip">{esc(NEED_LABELS[n])}</span>' for n in sorted(needs.needs)))
    if topics:
        _html('<div class="pf-small" style="margin-top:.5rem">Topics (TextBlob): ' + esc(", ".join(topics)) + "</div>")
    _html(f'<div class="pf-small" style="margin-top:.6rem">Reply engine: <b>{esc(engine)}</b></div>')


def ai_methods_note() -> None:
    _html(
        '<div class="pf-small"><b>AI methods</b><br>'
        "• TextBlob sentiment → reply tone<br>"
        "• TextBlob spelling correction<br>"
        "• Regex entity extraction (group, budget, hours)<br>"
        "• Fuzzy matching for cities &amp; aircraft names<br>"
        "• Intent classification (compare, cheaper, upgrade, choose)<br>"
        "• Weighted multi-criteria aircraft ranking<br>"
        "• OpenAI LLM sales copy, grounded on database facts (optional)</div>"
    )


def footer(scraped_on: str) -> None:
    _html(
        f"""
        <div class="fg-footer">
          <b>Legal notice.</b> Independent demonstration concept. Not an official Flygreen product and not endorsed by
          or affiliated with Flygreen. Aircraft names, specifications and images are from the public
          <a href="https://www.flygreen.co/aircraft-guide" target="_blank" rel="noopener noreferrer">Flygreen Aircraft Guide</a>
          (retrieved {esc(scraped_on)}) and remain the property of their owners. Prices are indicative averages, not
          offers or quotes, and exclude taxes and fees; non-published prices are sample estimates. No booking, payment
          or availability check takes place. No personal contact details are collected; the conversation stays in this
          browser session (and, if AI replies are enabled, trip details are sent to OpenAI to write the reply).
        </div>
        """
    )
