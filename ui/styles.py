"""Dark private-aviation theme: night-sky background, slate cards, warm gold accent."""

NAVY = "#0A1A33"        # deep accent backgrounds (hero, table headers)
NAVY_3 = "#1D3B66"
HEAD = "#F2F5FA"        # headings and key figures
INK = "#D7DEE8"         # body text
MUTED = "#8E9BB0"
SURFACE = "#070D1A"     # page background
CARD = "#0F1829"
CARD_2 = "#142038"
BORDER = "#22314A"
GOLD = "#D4B06A"
GOLD_SOFT = "#2A2416"
GOLD_INK = "#E9CB8B"
SKY = "#6FA8EA"
GREEN_BG = "#0F2A1E"
GREEN_INK = "#6FD39F"
AMBER_BG = "#2D2210"
AMBER_INK = "#F2C26B"
PILL_BG = "#17243A"
PILL_INK = "#A9C2E6"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap');

.stApp {{ background:
  radial-gradient(1200px 500px at 90% -10%, rgba(212,176,106,.07), transparent 60%),
  radial-gradient(900px 500px at -10% 10%, rgba(111,168,234,.07), transparent 60%), {SURFACE}; }}
.block-container {{ max-width: 1180px; padding-top: 1.2rem; padding-bottom: 2rem; }}
html, body, .stApp, .stMarkdown, button, input, textarea {{ font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif; color: {INK}; }}
h1, h2, h3, h4 {{ font-family: 'Manrope', 'Inter', sans-serif; color: {HEAD}; letter-spacing: -0.015em; }}
header[data-testid="stHeader"] {{ background: transparent; }}
section[data-testid="stSidebar"] {{ background: {CARD}; border-right: 1px solid {BORDER}; }}
a {{ color: {SKY}; }}

/* ---------- hero ---------- */
.fg-hero {{
  position: relative; overflow: hidden; border-radius: 18px; padding: 1.4rem 1.7rem 1.25rem; margin-bottom: .6rem;
  border: 1px solid {BORDER};
  background:
    radial-gradient(900px 260px at 85% -40%, rgba(212,176,106,.30), transparent 60%),
    radial-gradient(700px 300px at -10% 120%, rgba(111,168,234,.28), transparent 60%),
    linear-gradient(135deg, #081427 0%, {NAVY} 55%, {NAVY_3} 100%);
  color: #fff; box-shadow: 0 20px 50px -28px rgba(0,0,0,.9);
}}
.fg-hero::after {{ content: "✈"; position: absolute; right: 1.4rem; bottom: -1rem; font-size: 7rem;
  color: rgba(255,255,255,.07); transform: rotate(-18deg); pointer-events: none; }}
.fg-hero-top {{ display: flex; justify-content: space-between; align-items: center; gap: .8rem; flex-wrap: wrap; }}
.fg-eyebrow {{ font-size: .72rem; letter-spacing: .16em; text-transform: uppercase; color: {GOLD}; font-weight: 600; }}
.fg-title {{ font-family: 'Manrope', sans-serif; font-size: 2rem; font-weight: 800; color: #fff; margin: .3rem 0 .2rem; line-height: 1.1; }}
.fg-subtitle {{ color: rgba(255,255,255,.78); font-size: .98rem; margin: 0; max-width: 44rem; }}
.fg-pill {{ display: inline-block; border: 1px solid rgba(255,255,255,.25); color: #fff; background: rgba(255,255,255,.06);
  border-radius: 999px; padding: .2rem .7rem; font-size: .74rem; white-space: nowrap; }}

/* ---------- tabs ---------- */
.stTabs [data-baseweb="tab-list"] {{ gap: .4rem; border-bottom: 1px solid {BORDER}; }}
.stTabs [data-baseweb="tab"] {{ font-weight: 600; padding: .55rem 1rem; color: {MUTED}; }}
.stTabs [aria-selected="true"] {{ color: {GOLD}; }}
.stTabs [data-baseweb="tab-highlight"] {{ background-color: {GOLD}; }}

/* ---------- chat ---------- */
[data-testid="stChatMessage"] {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 16px; padding: .9rem 1rem; }}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {{ background: {CARD_2}; border-color: #2B3F60; }}
[data-testid="stChatInput"] {{ border-color: {BORDER}; }}
[data-testid="stChatInput"] textarea {{ font-size: .98rem; }}
.engine-tag {{ display: inline-block; font-size: .68rem; letter-spacing: .08em; text-transform: uppercase; color: {MUTED};
  border: 1px solid {BORDER}; border-radius: 999px; padding: .05rem .5rem; margin-top: .2rem; }}

/* ---------- recommendation card ---------- */
.ac-card {{ background: {CARD_2}; border: 1px solid {BORDER}; border-radius: 16px; overflow: hidden; height: 100%;
  box-shadow: 0 14px 30px -22px rgba(0,0,0,.9); margin-bottom: .4rem; }}
.ac-card.best {{ border: 1.5px solid {GOLD}; box-shadow: 0 16px 40px -22px rgba(212,176,106,.45); }}
.ac-img {{ position: relative; aspect-ratio: 16/9; background: linear-gradient(135deg, #1a2740, #0e1626); overflow: hidden; }}
.ac-img img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
.ac-role {{ position: absolute; top: .6rem; left: .6rem; background: rgba(7,13,26,.85); color: {HEAD}; font-size: .66rem;
  font-weight: 700; letter-spacing: .1em; text-transform: uppercase; padding: .22rem .55rem; border-radius: 6px;
  border: 1px solid {BORDER}; }}
.ac-card.best .ac-role {{ background: {GOLD}; color: {NAVY}; border-color: {GOLD}; }}
.ac-body {{ padding: .8rem .95rem .7rem; }}
.ac-name {{ font-family: 'Manrope', sans-serif; font-weight: 800; font-size: 1.12rem; color: {HEAD}; margin: 0; }}
.ac-cat {{ color: {MUTED}; font-size: .8rem; margin-bottom: .35rem; }}
.ac-price {{ font-family: 'Manrope', sans-serif; font-size: 1.5rem; font-weight: 800; color: {GOLD_INK}; line-height: 1.1; }}
.ac-price-cap {{ color: {MUTED}; font-size: .72rem; margin-bottom: .5rem; }}
.ac-pills {{ display: flex; flex-wrap: wrap; gap: .3rem; margin: .2rem 0 .5rem; }}
.ac-pill {{ font-size: .72rem; color: {PILL_INK}; background: {PILL_BG}; border-radius: 999px; padding: .14rem .5rem; }}
.ac-pill.ok {{ color: {GREEN_INK}; background: {GREEN_BG}; }}
.ac-pill.warn {{ color: {AMBER_INK}; background: {AMBER_BG}; }}
.ac-why {{ margin: .1rem 0 0; padding-left: 1rem; font-size: .8rem; color: {INK}; }}
.ac-why li {{ margin: .1rem 0; }}

/* ---------- comparison ---------- */
.cmp-wrap {{ overflow-x: auto; }}
.cmp {{ width: 100%; border-collapse: separate; border-spacing: 0; background: {CARD_2}; border: 1px solid {BORDER};
  border-radius: 14px; overflow: hidden; font-size: .88rem; }}
.cmp th, .cmp td {{ padding: .55rem .8rem; border-bottom: 1px solid {BORDER}; text-align: left; color: {INK}; }}
.cmp th {{ background: {NAVY_3}; color: {HEAD}; font-family: 'Manrope', sans-serif; }}
.cmp td:first-child {{ color: {MUTED}; font-size: .78rem; text-transform: uppercase; letter-spacing: .06em; width: 9rem; }}
.cmp b {{ color: {GOLD_INK}; }}
.cmp img {{ width: 100%; max-width: 220px; border-radius: 8px; display: block; }}

/* ---------- aircraft guide gallery ---------- */
.gl-section {{ font-family: 'Manrope', sans-serif; font-size: 1.5rem; font-weight: 700; color: {HEAD};
  border-bottom: 1px solid {BORDER}; padding-bottom: .4rem; margin: 1.2rem 0 .8rem; }}
.gl-card {{ background: {CARD_2}; border: 1px solid {BORDER}; border-radius: 14px; overflow: hidden; margin-bottom: .3rem;
  transition: transform .15s ease, box-shadow .15s ease, border-color .15s ease; }}
.gl-card:hover {{ transform: translateY(-2px); border-color: {GOLD}; box-shadow: 0 16px 34px -20px rgba(0,0,0,.9); }}
.gl-card .ac-img {{ aspect-ratio: 2/1; }}
.gl-meta {{ display: flex; justify-content: space-between; align-items: center; padding: .6rem .8rem; }}
.gl-name {{ font-weight: 600; color: {GOLD_INK}; font-size: .98rem; }}
.gl-seats {{ color: {MUTED}; font-size: .9rem; white-space: nowrap; }}

/* ---------- aircraft detail (spec strip like the guide) ---------- */
.spec-title {{ text-align: center; font-family: 'Manrope', sans-serif; font-size: 1.7rem; font-weight: 700; color: {HEAD};
  margin: 0 0 .7rem; display: flex; align-items: center; gap: 1rem; }}
.spec-title::before, .spec-title::after {{ content: ""; flex: 1; border-top: 1px dashed {BORDER}; }}
.spec-strip {{ display: grid; grid-template-columns: repeat(5, 1fr); background: {CARD_2}; border: 1px solid {BORDER};
  border-radius: 12px; margin-bottom: 1rem; }}
.spec-item {{ text-align: center; padding: .8rem .4rem; border-right: 1px dashed {BORDER}; }}
.spec-item:last-child {{ border-right: none; }}
.spec-label {{ font-size: .66rem; letter-spacing: .14em; text-transform: uppercase; color: {GOLD}; font-weight: 600; }}
.spec-value {{ font-size: 1.05rem; font-weight: 600; color: {HEAD}; margin-top: .3rem; }}
.spec-img {{ width: 100%; border-radius: 12px; display: block; }}
.spec-desc {{ font-weight: 600; line-height: 1.6; color: {INK}; }}
.spec-src {{ color: {MUTED}; font-size: .74rem; }}

/* ---------- advisor brief ---------- */
.brief-head {{ display: flex; justify-content: space-between; gap: 1rem; flex-wrap: wrap; align-items: center;
  background: {NAVY_3}; color: #fff; border-radius: 12px 12px 0 0; padding: .65rem 1rem; }}
.brief-head b {{ font-family: 'Manrope', sans-serif; }}
.brief-head span {{ font-size: .78rem; color: rgba(255,255,255,.75); }}
.next-steps {{ list-style: none; padding: 0; margin: .4rem 0 0; counter-reset: s; }}
.next-steps li {{ counter-increment: s; position: relative; padding: .4rem 0 .4rem 2rem; font-size: .86rem; }}
.next-steps li::before {{ content: counter(s); position: absolute; left: 0; top: .35rem; width: 1.4rem; height: 1.4rem;
  border-radius: 50%; background: {GOLD_SOFT}; color: {GOLD_INK}; font-weight: 700; font-size: .75rem;
  display: flex; align-items: center; justify-content: center; }}

/* ---------- sidebar profile ---------- */
.pf-row {{ display: flex; justify-content: space-between; gap: .6rem; padding: .35rem 0; border-bottom: 1px solid {BORDER}; font-size: .86rem; }}
.pf-row span:first-child {{ color: {MUTED}; }}
.pf-row span:last-child {{ font-weight: 600; text-align: right; color: {HEAD}; }}
.pf-chip {{ display: inline-block; font-size: .72rem; background: {GOLD_SOFT}; color: {GOLD_INK}; border-radius: 999px;
  padding: .12rem .55rem; margin: .15rem .2rem 0 0; }}
.pf-small {{ color: {MUTED}; font-size: .74rem; line-height: 1.45; }}
.pf-small b {{ color: {INK}; }}

/* ---------- notices & footer ---------- */
.fg-terms {{ background: {CARD}; border: 1px solid {BORDER}; border-left: 4px solid {GOLD}; border-radius: 12px;
  padding: .6rem .9rem; font-size: .84rem; margin: .2rem 0 .8rem; color: {INK}; }}
.fg-footer {{ color: {MUTED}; font-size: .76rem; line-height: 1.5; border-top: 1px solid {BORDER}; margin-top: 2rem; padding-top: .9rem; }}
.fg-footer b {{ color: {INK}; }}
.fg-footer a {{ color: {SKY}; text-decoration: none; }}

/* ---------- buttons: gold primary call-to-action ---------- */
div.stButton > button, div.stDownloadButton > button {{ border-radius: 10px; font-weight: 600; border-color: {BORDER}; }}
div.stButton > button[kind="primary"] {{ background: {GOLD}; border: 1px solid {GOLD}; color: {NAVY}; }}
div.stButton > button[kind="primary"]:hover {{ background: {GOLD_INK}; border-color: {GOLD_INK}; color: {NAVY}; }}
div.stButton > button[kind="secondary"]:hover {{ border-color: {GOLD}; color: {GOLD_INK}; }}

@media (max-width: 720px) {{
  .block-container {{ padding-left: 1rem; padding-right: 1rem; }}
  .fg-title {{ font-size: 1.5rem; }}
  .spec-strip {{ grid-template-columns: repeat(2, 1fr); }}
  .spec-item {{ border-right: none; border-bottom: 1px dashed {BORDER}; }}
}}
</style>
"""
