"""Scraper parsing, tested offline against HTML that mirrors the live page structure."""

from bs4 import BeautifulSoup

from scraper.flygreen_scraper import parse_detail, parse_guide, parse_routes

GUIDE_HTML = """
<div class="plane-guide-list products">
  <div class="product"><div class="plane-guide-section-title">Turboprop</div>
    <div class="plane-guide-item"><a href="/aircraft-guide/king-air-90">
      <div class="guide-img-wrap"><img src="/images-webp/jets/king-air-90.webp" alt="King Air 90"/></div>
      <div class="plane-guide-specs"><div class="plane-guide-specs-item">King Air 90</div>
      <div class="plane-guide-specs-item"><span class="material-icons">person</span> <!-- -->5</div></div></a></div>
  </div>
  <div class="product"><div class="plane-guide-section-title">Long Range Jet</div>
    <div class="plane-guide-item"><a href="/aircraft-guide/global-6000">
      <div class="guide-img-wrap"><img src="/images-webp/jets/global-6000.webp" alt="Global 6000"/></div>
      <div class="plane-guide-specs"><div class="plane-guide-specs-item">Global 6000</div>
      <div class="plane-guide-specs-item"><span class="material-icons">person</span> 14</div></div></a></div>
  </div>
</div>"""

DETAIL_HTML = """
<div class="jet-info-specs">
  <div class="jet-info-item"><span class="title">Passengers</span><span class="spec">7</span></div>
  <div class="jet-info-item"><span class="title">Cabin size</span><span class="spec size">4.8&#x27; h x 4.9&#x27; w x 17.8&#x27; l</span></div>
  <div class="jet-info-item"><span class="title">Maximum Range</span><span class="spec">3.8<!-- --> <!-- -->hours</span></div>
  <div class="jet-info-item"><span class="title">Baggage space</span><span class="spec">69<!-- -->  <!-- -->ft<sup>3</sup></span></div>
  <div class="jet-info-item"><span class="title">lavatory</span><span class="spec">Full</span></div>
</div>
<div class="jet-specs-right"><p><strong>The Citation Encore is a Light Jet available for charter.</strong></p>
<p>To charter this aircraft, call us at +1-888-000-0000.</p></div>"""

ROUTES_HTML = """
<div class="our-aircrafts-caption-item"><div class="our-aircrafts-caption-title">Light Jets</div>
  <div class="our-aircrafts-caption-cost">$<!-- -->3,000<!-- -->/hr</div></div>
<div class="table"><div class="th"><div class="td">US</div><div class="td">Light</div><div class="td">Mid-Size</div>
  <div class="td">Super Mid-Size</div><div class="td">Heavy</div></div>
  <div class="tr"><div class="td">NEW YORK - SOUTH FLORIDA</div><div class="td">$13,000</div><div class="td">$15,000</div>
  <div class="td">$20,000</div><div class="td">$25,000</div></div></div>
<div class="table"><div class="th"><div class="td">TRANSATLANTIC</div><div class="td">Light</div><div class="td">Mid-Size</div>
  <div class="td">Super Mid-Size</div><div class="td">Heavy</div></div>
  <div class="tr"><div class="td">NEW YORK - LONDON</div><div class="td">N/A</div><div class="td">N/A</div>
  <div class="td">N/A</div><div class="td">$95,000</div></div></div>"""


def test_parse_guide_reads_every_card_with_category():
    rows = parse_guide(BeautifulSoup(GUIDE_HTML, "html.parser"))
    assert [(r["model_name"], r["category"], r["passengers"]) for r in rows] == [
        ("King Air 90", "turboprop", 5), ("Global 6000", "long_range_jet", 14)]
    assert rows[0]["image_url"] == "https://www.flygreen.co/images-webp/jets/king-air-90.webp"
    assert rows[1]["detail_url"].endswith("/aircraft-guide/global-6000")


def test_parse_detail_extracts_specs_and_drops_contact_paragraph():
    d = parse_detail(BeautifulSoup(DETAIL_HTML, "html.parser"))
    assert d["passengers"] == 7
    assert (d["cabin_height_ft"], d["cabin_width_ft"], d["cabin_length_ft"]) == (4.8, 4.9, 17.8)
    assert d["max_range_hours"] == 3.8 and d["baggage_cuft"] == 69 and d["lavatory"] == "Full"
    assert "Light Jet" in d["description"] and "call us" not in d["description"]


def test_parse_routes_keeps_na_empty_and_reads_rates():
    routes, rates = parse_routes(BeautifulSoup(ROUTES_HTML, "html.parser"))
    assert rates == [{"category": "light_jet", "hourly_rate_usd": 3000}]
    assert routes[0] == {"region": "US", "origin": "New York", "destination": "South Florida",
                         "light_jet": 13000, "mid_size_jet": 15000, "super_mid_size_jet": 20000, "heavy_jet": 25000}
    assert routes[1]["light_jet"] == "" and routes[1]["heavy_jet"] == 95000
