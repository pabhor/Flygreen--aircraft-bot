"""Soft-glass theme: pastel lavender/mint backdrop, frosted white panels, blue accent."""

INK = "#1F2330"
MUTED = "#7A7F8E"
BLUE = "#3B82F6"
GLASS = "rgba(255,255,255,.55)"
GLASS_STRONG = "rgba(255,255,255,.78)"
EDGE = "rgba(255,255,255,.85)"
LINE = "rgba(31,35,48,.08)"
MINT = "#DDF3E4"
LILAC = "#ECE6FA"
GOLD = "#B88A2E"
OK_BG, OK_INK = "#E3F6EA", "#1D6A43"
WARN_BG, WARN_INK = "#FFF3DE", "#8A5A00"
SHADOW = "0 30px 60px -38px rgba(80,60,140,.38)"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap');

.stApp {{ background:
  radial-gradient(1100px 650px at 8% 0%, #E7E1FA 0%, transparent 60%),
  radial-gradient(900px 600px at 100% 100%, #FBE6EF 0%, transparent 55%),
  radial-gradient(800px 520px at 62% 38%, #E3F4EC 0%, transparent 60%), #F3F1F8; }}
.block-container {{ max-width: 1400px; padding: 1rem 1.6rem 1.5rem; }}
html, body, .stApp, .stMarkdown, button, input, textarea {{ font-family: 'Outfit', system-ui, -apple-system, 'Segoe UI', sans-serif; color: {INK}; }}
header[data-testid="stHeader"] {{ background: transparent; }}
h1, h2, h3, h4 {{ font-family: 'Outfit', sans-serif; color: {INK}; font-weight: 500; letter-spacing: -.01em; }}

/* ---------- glass panels ---------- */
.st-key-rail, .st-key-history_panel, .st-key-main_panel {{
  background: {GLASS}; backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px);
  border: 1px solid {EDGE}; box-shadow: {SHADOW};
}}
.st-key-rail {{ border-radius: 30px; padding: 1rem .35rem; align-items: center; gap: .55rem; min-height: 78vh; }}
.st-key-history_panel, .st-key-main_panel {{ border-radius: 34px; padding: 1.5rem 1.5rem 1.2rem; min-height: 78vh; }}

/* ---------- top bar ---------- */
.topbar {{ display: flex; justify-content: space-between; align-items: center; margin: 0 .2rem .8rem; flex-wrap: wrap; gap: .6rem; }}
.brand {{ display: flex; align-items: center; gap: .6rem; font-weight: 700; font-size: 1.2rem; }}
.brand-mark {{ width: 2.2rem; height: 2.2rem; border-radius: 12px; background: {INK}; color: #fff; display: flex;
  align-items: center; justify-content: center; font-size: 1.15rem; transform: rotate(-8deg); }}
.legal-pill {{ font-size: .74rem; color: {MUTED}; background: {GLASS_STRONG}; border: 1px solid {EDGE};
  border-radius: 999px; padding: .25rem .8rem; }}

/* ---------- rail ---------- */
.st-key-rail div.stButton > button {{ width: 46px; height: 46px; min-height: 46px; padding: 0; border-radius: 50%;
  border: none; background: transparent; color: {INK}; box-shadow: none; }}
.st-key-rail div.stButton > button:hover {{ background: {GLASS_STRONG}; color: {BLUE}; }}
.st-key-rail div.stButton > button[kind="primary"] {{ background: {BLUE}; color: #fff;
  box-shadow: 0 10px 22px -10px rgba(59,130,246,.9); }}
.st-key-rail [data-testid="stIconMaterial"] {{ font-size: 1.35rem; }}
.rail-spacer {{ height: 32vh; }}

/* ---------- panel headings ---------- */
.panel-head {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: .6rem; }}
.panel-title {{ font-size: 2rem; font-weight: 500; margin: 0; line-height: 1.1; }}
.panel-title.center {{ text-align: center; flex: 1; }}
.panel-spark {{ width: 2.6rem; height: 2.6rem; border-radius: 50%; background: {GLASS_STRONG}; display: flex;
  align-items: center; justify-content: center; font-size: 1.1rem; }}
.group-label {{ font-size: 1.35rem; font-weight: 500; margin: 1rem 0 .6rem .2rem; }}

/* ---------- history cards ---------- */
.h-card {{ background: rgba(255,255,255,.62); border: 1px solid {EDGE}; border-radius: 28px; padding: .7rem;
  margin-bottom: .8rem; }}
.h-top {{ display: flex; align-items: center; gap: .7rem; padding: .3rem .4rem .6rem; }}
.h-ico {{ width: 2.4rem; height: 2.4rem; border-radius: 50%; background: #fff; display: flex; align-items: center;
  justify-content: center; font-size: 1.05rem; flex: none; }}
.h-title {{ font-weight: 500; font-size: .98rem; }}
.h-date {{ color: {MUTED}; font-size: .76rem; }}
.h-arrow {{ margin-left: auto; width: 2.2rem; height: 2.2rem; border-radius: 50%; background: #fff; display: flex;
  align-items: center; justify-content: center; color: {INK}; }}
.h-media {{ display: grid; grid-template-columns: 1fr 74px; gap: .5rem; border-radius: 22px; padding: .6rem;
  background: linear-gradient(180deg, #fff 0%, {MINT} 100%); }}
.h-main {{ border-radius: 16px; overflow: hidden; aspect-ratio: 4/3; }}
.h-main img, .h-thumb img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
.h-thumbs {{ display: flex; flex-direction: column; gap: .45rem; }}
.h-thumb {{ width: 74px; height: 58px; border-radius: 50%; overflow: hidden; background: #fff; }}
.h-more {{ width: 74px; height: 58px; border-radius: 50%; background: rgba(255,255,255,.8); display: flex;
  align-items: center; justify-content: center; font-weight: 500; }}
.h-foot {{ display: flex; gap: .6rem; align-items: center; background: rgba(255,255,255,.7); border-radius: 18px;
  padding: .55rem .7rem; margin-top: .5rem; }}
.h-foot b {{ font-weight: 500; }}
.h-foot small {{ color: {MUTED}; display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 22rem; }}
.h-row {{ display: flex; gap: .6rem; align-items: center; background: rgba(255,255,255,.75); border-radius: 18px;
  padding: .6rem .8rem; margin-bottom: .45rem; font-size: .9rem; }}
.h-row small {{ color: {MUTED}; display: block; }}
.h-empty {{ text-align: center; color: {MUTED}; padding: 2.2rem 1rem; border: 1px dashed rgba(31,35,48,.14);
  border-radius: 26px; background: rgba(255,255,255,.4); }}
.h-empty .big {{ font-size: 2.6rem; }}

/* ---------- profile ---------- */
.pf-row {{ display: flex; justify-content: space-between; gap: .6rem; padding: .35rem .2rem; border-bottom: 1px solid {LINE}; font-size: .86rem; }}
.pf-row span:first-child {{ color: {MUTED}; }}
.pf-row span:last-child {{ font-weight: 500; text-align: right; }}
.pf-chip {{ display: inline-block; font-size: .74rem; background: {LILAC}; color: #4B3E8F; border-radius: 999px;
  padding: .14rem .6rem; margin: .2rem .2rem 0 0; }}
.pf-small {{ color: {MUTED}; font-size: .76rem; line-height: 1.5; }}

/* ---------- greeting ---------- */
.greet {{ display: flex; align-items: center; gap: 1.2rem; margin: .4rem 0 1rem; }}
.greet-avatar {{ width: 5.2rem; height: 5.2rem; border-radius: 50%; flex: none; display: flex; align-items: center;
  justify-content: center; font-size: 2.3rem; color: #fff;
  background: radial-gradient(circle at 30% 25%, #9CC3FF, {BLUE} 55%, #5B3FD9); box-shadow: 0 16px 30px -14px rgba(59,130,246,.8); }}
.greet-hi {{ font-size: 1.45rem; color: #3A3F4E; }}
.greet-q {{ font-size: 1.6rem; font-weight: 600; }}

/* ---------- chat bubbles ---------- */
[data-testid="stChatMessage"] {{ background: rgba(255,255,255,.62); border: 1px solid {EDGE}; border-radius: 26px;
  padding: 1rem 1.1rem; margin-bottom: .6rem; }}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {{
  background: linear-gradient(135deg, rgba(255,255,255,.75), rgba(236,230,250,.6)); }}
[data-testid="stChatMessageAvatarAssistant"], [data-testid="stChatMessageAvatarUser"] {{ border-radius: 50%; }}
[data-testid="stChatMessageAvatarAssistant"] {{ background: radial-gradient(circle at 30% 25%, #9CC3FF, {BLUE} 60%, #5B3FD9); color: #fff; }}
[data-testid="stChatMessageAvatarUser"] {{ background: {INK}; color: #fff; }}
.engine-tag {{ display: inline-block; font-size: .68rem; letter-spacing: .06em; text-transform: uppercase; color: {MUTED};
  background: rgba(255,255,255,.7); border-radius: 999px; padding: .1rem .55rem; }}

/* ---------- action tiles ---------- */
[class*="st-key-tile_"] div.stButton > button {{ height: 112px; border-radius: 24px; background: rgba(255,255,255,.66);
  border: 1px solid {EDGE}; display: flex; flex-direction: column; align-items: flex-start; justify-content: space-between;
  padding: .85rem .9rem; box-shadow: 0 16px 30px -24px rgba(80,60,140,.5); color: {INK}; font-weight: 500; }}
[class*="st-key-tile_"] div.stButton > button:hover {{ background: #fff; border-color: #fff; transform: translateY(-2px); }}
[class*="st-key-tile_"] [data-testid="stIconMaterial"] {{ font-size: 2.1rem; color: {BLUE}; }}
.st-key-tile_guide [data-testid="stIconMaterial"] {{ color: #E0613B; }}
.st-key-tile_routes [data-testid="stIconMaterial"] {{ color: #1FA37A; }}
.st-key-tile_value [data-testid="stIconMaterial"] {{ color: {GOLD}; }}

/* ---------- input ---------- */
[data-testid="stChatInput"] {{ border-radius: 999px; background: {GLASS_STRONG}; border: 1px solid {EDGE};
  box-shadow: 0 14px 30px -22px rgba(80,60,140,.6); }}
[data-testid="stChatInput"] textarea {{ font-size: .98rem; }}
[data-testid="stChatInputSubmitButton"] {{ border-radius: 50%; background: #fff; }}

/* ---------- recommendation cards ---------- */
.ac-card {{ background: rgba(255,255,255,.8); border: 1px solid {EDGE}; border-radius: 24px; overflow: hidden;
  height: 100%; margin-bottom: .4rem; box-shadow: 0 18px 34px -28px rgba(80,60,140,.6); }}
.ac-card.best {{ border: 1.5px solid {BLUE}; box-shadow: 0 20px 40px -24px rgba(59,130,246,.55); }}
.ac-img {{ position: relative; aspect-ratio: 16/9; background: linear-gradient(180deg, #fff, {MINT}); overflow: hidden; }}
.ac-img img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
.ac-role {{ position: absolute; top: .6rem; left: .6rem; background: rgba(255,255,255,.9); color: {INK}; font-size: .7rem;
  font-weight: 600; padding: .22rem .6rem; border-radius: 999px; }}
.ac-card.best .ac-role {{ background: {BLUE}; color: #fff; }}
.ac-body {{ padding: .8rem .95rem .7rem; }}
.ac-name {{ font-weight: 600; font-size: 1.12rem; margin: 0; }}
.ac-cat {{ color: {MUTED}; font-size: .8rem; margin-bottom: .3rem; }}
.ac-price {{ font-size: 1.5rem; font-weight: 600; line-height: 1.1; }}
.ac-price-cap {{ color: {MUTED}; font-size: .72rem; margin-bottom: .5rem; }}
.ac-pills {{ display: flex; flex-wrap: wrap; gap: .3rem; margin: .2rem 0 .5rem; }}
.ac-pill {{ font-size: .72rem; color: #3E4A63; background: #EEF1F8; border-radius: 999px; padding: .14rem .55rem; }}
.ac-pill.ok {{ color: {OK_INK}; background: {OK_BG}; }}
.ac-pill.warn {{ color: {WARN_INK}; background: {WARN_BG}; }}
.ac-why {{ margin: .1rem 0 0; padding-left: 1rem; font-size: .8rem; }}

/* ---------- comparison ---------- */
.cmp-wrap {{ overflow-x: auto; }}
.cmp {{ width: 100%; border-collapse: separate; border-spacing: 0; background: rgba(255,255,255,.8); border-radius: 20px;
  overflow: hidden; font-size: .88rem; border: 1px solid {EDGE}; }}
.cmp th, .cmp td {{ padding: .55rem .8rem; border-bottom: 1px solid {LINE}; text-align: left; }}
.cmp th {{ background: {LILAC}; font-weight: 600; }}
.cmp td:first-child {{ color: {MUTED}; font-size: .78rem; text-transform: uppercase; letter-spacing: .05em; width: 8.5rem; }}
.cmp img {{ width: 100%; max-width: 200px; border-radius: 12px; display: block; }}

/* ---------- guide gallery ---------- */
.gl-section {{ font-size: 1.35rem; font-weight: 500; border-bottom: 1px solid {LINE}; padding-bottom: .35rem; margin: 1rem 0 .7rem; }}
.gl-card {{ background: rgba(255,255,255,.75); border: 1px solid {EDGE}; border-radius: 22px; overflow: hidden;
  margin-bottom: .3rem; transition: transform .15s ease; }}
.gl-card:hover {{ transform: translateY(-2px); }}
.gl-card .ac-img {{ aspect-ratio: 2/1; }}
.gl-meta {{ display: flex; justify-content: space-between; align-items: center; padding: .6rem .8rem; }}
.gl-name {{ font-weight: 500; color: #1F6B4E; }}
.gl-seats {{ color: {MUTED}; font-size: .9rem; white-space: nowrap; }}

/* ---------- detail dialog ---------- */
.spec-title {{ text-align: center; font-size: 1.8rem; font-weight: 400; margin: 0 0 .7rem; display: flex; align-items: center; gap: 1rem; }}
.spec-title::before, .spec-title::after {{ content: ""; flex: 1; border-top: 1px dashed rgba(31,35,48,.2); }}
.spec-strip {{ display: grid; grid-template-columns: repeat(5, 1fr); background: #fff; border-radius: 16px;
  box-shadow: 0 12px 26px -18px rgba(31,35,48,.35); margin-bottom: 1rem; }}
.spec-item {{ text-align: center; padding: .8rem .4rem; border-right: 1px dashed rgba(31,35,48,.15); }}
.spec-item:last-child {{ border-right: none; }}
.spec-label {{ font-size: .66rem; letter-spacing: .14em; text-transform: uppercase; color: #1F6B4E; font-weight: 600; }}
.spec-value {{ font-size: 1.05rem; font-weight: 500; margin-top: .3rem; }}
.spec-img {{ width: 100%; border-radius: 16px; display: block; }}
.spec-desc {{ font-weight: 600; line-height: 1.6; }}
.spec-src {{ color: {MUTED}; font-size: .74rem; }}

/* ---------- advisor brief ---------- */
.brief-head {{ display: flex; justify-content: space-between; gap: 1rem; flex-wrap: wrap; align-items: center;
  background: {INK}; color: #fff; border-radius: 16px 16px 0 0; padding: .65rem 1rem; }}
.brief-head span {{ font-size: .78rem; color: rgba(255,255,255,.75); }}
.next-steps {{ list-style: none; padding: 0; margin: .4rem 0 0; counter-reset: s; }}
.next-steps li {{ counter-increment: s; position: relative; padding: .4rem 0 .4rem 2rem; font-size: .86rem; }}
.next-steps li::before {{ content: counter(s); position: absolute; left: 0; top: .35rem; width: 1.4rem; height: 1.4rem;
  border-radius: 50%; background: {LILAC}; color: #4B3E8F; font-weight: 700; font-size: .75rem;
  display: flex; align-items: center; justify-content: center; }}

/* ---------- misc ---------- */
.fg-terms {{ font-size: .8rem; color: {MUTED}; background: rgba(255,255,255,.55); border-radius: 16px; padding: .5rem .8rem; margin-bottom: .6rem; }}
.fg-footer {{ color: {MUTED}; font-size: .74rem; line-height: 1.5; margin: 1.2rem .4rem 0; }}
.fg-footer a {{ color: {BLUE}; text-decoration: none; }}
div.stButton > button {{ border-radius: 999px; font-weight: 500; }}
div.stButton > button[kind="primary"] {{ background: {BLUE}; border-color: {BLUE}; color: #fff; }}
div.stButton > button[kind="primary"]:hover {{ background: #2563EB; border-color: #2563EB; }}
div[data-testid="stExpander"] details {{ background: rgba(255,255,255,.55); border-radius: 18px; border-color: {EDGE}; }}

@media (max-width: 900px) {{
  .st-key-rail {{ min-height: 0; flex-direction: row; justify-content: center; }}
  .rail-spacer {{ display: none; }}
  .st-key-history_panel, .st-key-main_panel {{ min-height: 0; }}
  .spec-strip {{ grid-template-columns: repeat(2, 1fr); }}
}}
</style>
"""
