"""AI Charter Concierge - Streamlit entry point.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime

import streamlit as st

st.set_page_config(page_title="AI Charter Concierge", page_icon="✈️", layout="wide")


def _promote_streamlit_secrets() -> None:
    """On hosts like Streamlit Community Cloud, accessing st.secrets copies root-level
    string secrets (e.g. OPENAI_API_KEY) into os.environ. Locally this is a no-op."""
    try:
        st.secrets.load_if_toml_exists()
    except FileNotFoundError:
        pass


_promote_streamlit_secrets()

from config import get_log_level  # noqa: E402
from services.charter_db import CATEGORY_ORDER, get_db  # noqa: E402
from services.sales_agent import AgentState, SalesAgent  # noqa: E402
from ui import components as ui  # noqa: E402
from ui.styles import CSS  # noqa: E402

logging.basicConfig(level=get_log_level(), format="%(asctime)s %(levelname)s %(name)s: %(message)s")

db = get_db()
agent = SalesAgent(db)
ss = st.session_state
for key, default in {"messages": [], "agent_state": AgentState(), "pending": None, "detail_slug": None,
                     "topics": (), "engine": "-", "view": "chat"}.items():
    ss.setdefault(key, default)

SUGGESTIONS = [
    "It's our anniversary - 2 of us, New York to Nassau, something special",
    "6 executives, Chicago to Aspen, lots of ski gear, under $40k",
    "Family of 4 with kids, Los Angeles to Las Vegas, best value",
    "12 people, about a 5 hour flight, luxury cabin",
]
TYPING_DELAY = 0.008


# ------------------------------------------------------------- actions ------
def queue(text: str) -> None:
    ss.pending, ss.view = text, "chat"


def set_view(view: str) -> None:
    ss.view = view


def open_details(slug: str) -> None:
    ss.detail_slug = slug


def reset_chat() -> None:
    ss.messages, ss.agent_state, ss.topics, ss.engine, ss.view = [], AgentState(), (), "-", "chat"


def _now() -> str:
    return datetime.now().strftime("Today · %H:%M")


def _typing(text: str):
    for token in re.split(r"(\s+)", text):
        yield token
        time.sleep(TYPING_DELAY)


@st.dialog("Aircraft details", width="large")
def show_details(slug: str) -> None:
    a = db.aircraft_by_slug(slug)
    if a is None:
        st.write("Aircraft not found.")
        return
    ui.spec_panel(a)
    c1, c2 = st.columns(2)
    if c1.button("Choose this aircraft", type="primary", key=f"dlg_choose_{slug}", width="stretch"):
        queue(f"I'll take the {a['model_name']}")
        st.rerun()
    if c2.button("Ask the concierge about it", key=f"dlg_ask_{slug}", width="stretch"):
        queue(f"Tell me about the {a['model_name']}")
        st.rerun()


def render_extras(msg: dict, idx: int) -> None:
    needs = msg["needs"]
    cards = msg.get("cards") or []
    if cards:
        cols = st.columns(len(cards), gap="small")
        for i, (col, c) in enumerate(zip(cols, cards)):
            with col:
                ui.recommendation_card(c, needs, best=i == 0)
                b1, b2 = st.columns(2)
                b1.button("Details", key=f"det_{idx}_{c.slug}", on_click=open_details, args=(c.slug,), width="stretch")
                b2.button("Choose this aircraft", key=f"cho_{idx}_{c.slug}", type="primary", width="stretch",
                          on_click=queue, args=(f"I'll take the {c.model_name}",))
    comparison = msg.get("comparison") or []
    if len(comparison) > 1:
        ui.comparison_table(comparison, needs)
    if comparison:
        cols = st.columns(len(comparison))
        for col, c in zip(cols, comparison):
            col.button(f"Choose {c.model_name}", key=f"cmp_{idx}_{c.slug}", type="primary", width="stretch",
                       on_click=queue, args=(f"I'll take the {c.model_name}",))
    if msg.get("chosen"):
        ui.advisor_brief(msg["chosen"], needs)
    st.markdown(f'<span class="engine-tag">{msg.get("engine", "")}</span>', unsafe_allow_html=True)


def handle(text: str, container) -> None:
    history = [{"role": m["role"], "content": m["content"]} for m in ss.messages]
    ss.messages.append({"role": "user", "content": text, "time": _now()})
    with container:
        with st.chat_message("user", avatar=":material/person:"):
            st.markdown(text)
        with st.chat_message("assistant", avatar=":material/flight:"):
            with st.spinner("Finding the right aircraft for you..."):
                reply, new_state = agent.respond(text, ss.agent_state, history)
            st.write_stream(_typing(reply.text))
            engine = f"OpenAI · {agent.settings.model}" if reply.engine == "openai" else "Built-in AI"
            msg = {"role": "assistant", "content": reply.text, "cards": reply.cards, "time": _now(),
                   "comparison": reply.comparison, "chosen": reply.chosen, "needs": new_state.needs,
                   "engine": engine}
            render_extras(msg, len(ss.messages))
    ss.agent_state = new_state
    ss.topics = reply.parsed.topics if reply.parsed else ()
    ss.engine = engine
    ss.messages.append(msg)


# ------------------------------------------------------------- panels -------
def rail() -> None:
    with st.container(key="rail"):
        st.button("", icon=":material/add:", key="rail_new", help="New conversation", on_click=reset_chat)
        for view, icon, tip in (("chat", ":material/chat_bubble:", "Concierge chat"),
                                ("guide", ":material/flight:", "Aircraft guide"),
                                ("routes", ":material/route:", "Route prices")):
            st.button("", icon=icon, key=f"rail_{view}", help=tip, on_click=set_view, args=(view,),
                      type="primary" if ss.view == view else "secondary")
        st.markdown('<div class="rail-spacer"></div>', unsafe_allow_html=True)
        st.button("", icon=":material/savings:", key="rail_value", help="Best value option",
                  on_click=queue, args=("Show me the best value option",))


def history_panel() -> None:
    with st.container(key="history_panel"):
        ui.panel_head("Flight Matches")
        ui.group_label("Today")
        matches = [(i, m) for i, m in enumerate(ss.messages) if m["role"] == "assistant" and m.get("cards")]
        if not matches:
            ui.history_empty()
        for i, m in reversed(matches[-3:]):
            query = ss.messages[i - 1]["content"] if i > 0 else ""
            ui.history_card(m["cards"], query, m.get("time", ""))
            st.button("View best match", key=f"hist_{i}", on_click=open_details, args=(m["cards"][0].slug,),
                      width="stretch")
        questions = [m for m in ss.messages if m["role"] == "user"][-4:]
        if questions:
            ui.group_label("Recent questions")
            for q in reversed(questions):
                ui.history_row(q["content"], q.get("time", ""))
        with st.expander("What the AI understood", expanded=bool(ss.messages)):
            ui.profile_panel(ss.agent_state.needs, ss.topics, ss.engine)
        with st.expander("How the AI works"):
            ui.ai_methods_note()


def chat_view() -> None:
    ui.panel_head("Charter Concierge", spark=True)
    ui.greeting(len(db.aircraft))
    box = st.container()
    with box:
        if not ss.messages:
            with st.chat_message("assistant", avatar=":material/flight:"):
                st.markdown(agent.greeting())
                st.caption("Try one of these:")
                cols = st.columns(2)
                for i, s in enumerate(SUGGESTIONS):
                    cols[i % 2].button(s, key=f"sugg_{i}", on_click=queue, args=(s,), width="stretch")
        for i, m in enumerate(ss.messages):
            avatar = ":material/flight:" if m["role"] == "assistant" else ":material/person:"
            with st.chat_message(m["role"], avatar=avatar):
                st.markdown(m["content"])
                if m["role"] == "assistant":
                    render_extras(m, i)
    if ss.pending:
        pending, ss.pending = ss.pending, None
        handle(pending, box)
    tiles = st.columns(4, gap="small")
    tiles[0].button("Compare jets", icon=":material/compare_arrows:", key="tile_compare", width="stretch",
                    on_click=queue, args=("Compare Phenom 300 vs Citation CJ3",))
    tiles[1].button("Aircraft guide", icon=":material/flight:", key="tile_guide", width="stretch",
                    on_click=set_view, args=("guide",))
    tiles[2].button("Route prices", icon=":material/route:", key="tile_routes", width="stretch",
                    on_click=set_view, args=("routes",))
    tiles[3].button("Best value", icon=":material/savings:", key="tile_value", width="stretch",
                    on_click=queue, args=("Show me the best value option",))
    ui.terms_note()
    prompt = st.chat_input("Ask me anything... e.g. 6 of us, NYC to Aspen, lots of ski gear, under $40k")
    if prompt:
        handle(prompt, box)


def guide_view() -> None:
    ui.panel_head("Aircraft Guide")
    st.caption(f"{len(db.aircraft)} aircraft across 6 categories. Open one for full specifications.")
    labels = {c: db.category_label(c) for c in CATEGORY_ORDER}
    picked = st.segmented_control("Category", ["all", *CATEGORY_ORDER], default="all", key="guide_cat",
                                  format_func=lambda c: "All" if c == "all" else labels[c])
    f1, f2 = st.columns([2, 1])
    query = f1.text_input("Search", placeholder="e.g. Gulfstream", key="guide_q")
    min_seats = f2.number_input("Min. seats", min_value=1, max_value=db.max_capacity, value=1, key="guide_seats")
    for cat in CATEGORY_ORDER:
        if picked not in (None, "all") and picked != cat:
            continue
        df = db.aircraft_in(cat)
        df = df[df.passengers >= min_seats]
        if query:
            df = df[df.model_name.str.contains(query, case=False, regex=False)]
        if df.empty:
            continue
        ui.section_title(labels[cat])
        rows = df.to_dict("records")
        for start in range(0, len(rows), 3):
            cols = st.columns(3, gap="small")
            for col, a in zip(cols, rows[start:start + 3]):
                with col:
                    ui.gallery_card(a)
                    st.button("View details", key=f"gal_{a['slug']}", on_click=open_details,
                              args=(a["slug"],), width="stretch")


def routes_view() -> None:
    ui.panel_head("Route Prices")
    st.caption("Average one-way prices per aircraft category (published Flygreen estimates where available, "
               "otherwise sample estimates).")
    cities = db.cities()
    r1, r2 = st.columns(2)
    origin = r1.selectbox("From", cities, index=cities.index("New York"), key="rp_from")
    dest_options = [c for c in cities if c != origin]
    destination = r2.selectbox("To", dest_options, key="rp_to",
                               index=dest_options.index("Miami") if "Miami" in dest_options else 0)
    info = db.route(origin, destination)
    prices = db.route_prices(origin, destination)
    if info is not None:
        st.caption(f"{info.distance_nm:,} nm" + (" · ocean crossing: heavy and long-range jets only" if info.crosses_ocean else ""))
    table = prices.assign(
        Category=prices.label,
        **{"Average price (USD)": prices.avg_price_usd.map(lambda v: "Not offered" if v is None or v != v else f"${int(v):,}"),
           "Est. flight time": prices.est_flight_hours.map(lambda h: f"{h:g} h"),
           "Fuel stops": prices.fuel_stops},
        Source=prices.price_source.map({"published": "Published", "sample_estimate": "Sample estimate",
                                        "published_na": "Published N/A", "not_offered": "Not offered"}),
    )[["Category", "Average price (USD)", "Est. flight time", "Fuel stops", "Source"]]
    st.dataframe(table, hide_index=True, width="stretch")
    st.button(f"Find the best jet for {origin} → {destination}", type="primary",
              on_click=queue, args=(f"Recommend a jet from {origin} to {destination}",))


# ---------------------------------------------------------------- page ------
st.markdown(CSS, unsafe_allow_html=True)
ui.topbar()
c_rail, c_hist, c_main = st.columns([0.06, 0.32, 0.62], gap="medium")
with c_rail:
    rail()
with c_hist:
    history_panel()
with c_main:
    with st.container(key="main_panel"):
        {"chat": chat_view, "guide": guide_view, "routes": routes_view}[ss.view]()

if ss.detail_slug:
    slug, ss.detail_slug = ss.detail_slug, None
    show_details(slug)

ui.footer(db.scraped_on)
