"""Medicare reference amounts: CMS's formula, constants traced to source text, and honest labels."""

import re

import pytest

from patientshield.core.benchmarks import data
from patientshield.core.benchmarks.routes import benchmarks
from patientshield.core.sources.service import get_source


def excerpts(source_id: str) -> str:
    return " ".join(e.text for e in get_source(source_id).excerpts)  # type: ignore[union-attr]


# Computed independently from PPRRVU2026_Oct_nonQPP.csv and GPCI2026.csv on 2026-10-19 (locality 01, locality 99).
EXPECTED = {
    "99203": (13071, 12564),
    "99204": (19657, 18920),
    "99213": (10593, 10171),
    "99214": (15065, 14477),
    "99215": (21345, 20526),
    "99283": (7479, 7312),
    "99284": (12720, 12442),
    "99285": (18433, 18024),
    "71046": (3762, 3575),
    "70450": (12072, 11492),
    "72148": (21742, 20688),
    "73721": (23257, 22094),
    "74177": (34218, 32485),
    "76700": (12976, 12338),
    "93000": (1721, 1649),
    "97110": (3222, 3095),
}


def test_ten_to_twenty_distinct_services():
    codes = [s.code for s in data.SERVICES]
    assert 10 <= len(codes) <= 20 and len(set(codes)) == len(codes)
    assert set(codes) == set(EXPECTED)


@pytest.mark.parametrize("code", sorted(EXPECTED))
def test_amounts_follow_cms_formula_for_both_new_jersey_localities(code):
    service = data.SERVICES_BY_CODE[code]
    assert (data.amount_cents(service, "01"), data.amount_cents(service, "99")) == EXPECTED[code]


def test_formula_by_hand_for_one_service():
    # 99214 in Northern NJ: (1.92*1.063 + 2.00*1.160 + 0.14*1.068) * 33.4009 = 150.648... -> $150.65
    assert round((1.92 * 1.063 + 2.00 * 1.160 + 0.14 * 1.068) * 33.4009, 2) == 150.65


def test_constants_trace_to_the_source_text():
    rvu = excerpts("cms-pfs-rvu26d")
    assert str(data.CONVERSION_FACTOR) in rvu
    for loc, (pw, pe, mp) in data.GPCI.items():
        assert f"12402,NJ,{loc}," in rvu and f",{pw},{pe},{mp}" in rvu
    assert ", ".join(c.upper() for c in data.NORTHERN_NJ_COUNTIES[:-1]) + " AND WARREN" in rvu
    assert "RVU26D - Updated 08/26/2026" in rvu and data.FILE_UPDATED == "2026-08-26"
    assert "$33.40" in excerpts("cms-pfs-2026-final-rule")


def test_new_jersey_has_21_counties_split_between_two_localities():
    assert len(data.NJ_COUNTIES) == 21 and set(data.NORTHERN_NJ_COUNTIES) < set(data.NJ_COUNTIES)


def test_emergency_visits_use_the_facility_rate_and_say_what_is_left_out():
    for s in data.SERVICES:
        if s.category == "emergency":
            assert s.setting == "facility"
            assert "not included" in data.COVERS[s.category]
    assert "not included" in data.COVERS["imaging"]


def test_endpoint_serves_rates_with_dates_sources_and_claims(api_client):
    body = api_client.get("/api/benchmarks").json()
    assert body["year"] == 2026 and body["version"] == "RVU26D" and body["retrieved"] == "2026-10-19"
    assert body["conversion_factor"] == "33.4009"
    rate = next(r for r in body["rates"] if r["code"] == "72148")
    assert rate["amounts_cents"] == {"01": 21742, "99": 20688} and rate["comparable"] is True
    assert not any(r["comparable"] for r in body["rates"] if r["category"] == "emergency")
    assert set(body["claims"]) == {
        "medicare_estimate_how",
        "medicare_facility_rate",
        "price_transparency_list",
        "price_transparency_shoppable",
        "price_terms",
        "nj_uninsured_cap",
    }
    assert all(get_source(sid) for sid in body["source_ids"])


def test_wording_is_context_not_accusation():
    text = benchmarks().disclaimer + " " + " ".join(data.COVERS.values())
    assert "not what you owe" in text
    assert not re.search(r"overcharg|illegal|unlawful|rip-?off|gouging|fair price", text, re.I)
