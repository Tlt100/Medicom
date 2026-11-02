"""Medicare reference amounts for common services, from CMS's 2026 physician fee schedule (RVU26D).

How each amount is made (CMS's own formula, in RVU26D.pdf):
    [(work RVU x work GPCI) + (PE RVU x PE GPCI) + (MP RVU x MP GPCI)] x conversion factor
using the facility or non-facility practice expense (PE) RVU for the setting, New Jersey's two Medicare localities,
and the non-QP conversion factor. Amounts are rounded to the nearest cent.

RVUs were copied from PPRRVU2026_Oct_nonQPP.csv (global rows, no modifier) on 2026-10-19. None of these codes appear
in the OPPS imaging cap file (OPPSCAP_Oct.csv), so no cap applies.

Descriptions are Medicom's own plain-language wording, not CPT descriptors.
These are physician fee schedule amounts only. Hospital facility payments are set under other Medicare systems and
are not included; each service says what its amount covers.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Dict, List, Literal, Tuple

VERSION = "RVU26D"
FILE_UPDATED = "2026-08-26"
RETRIEVED = "2026-10-19"
YEAR = 2026
CONVERSION_FACTOR = Decimal("33.4009")
SOURCE_IDS = ["cms-pfs-rvu26d", "cms-pfs-2026-final-rule"]

# (work, PE, MP) GPCIs from GPCI2026.csv.
GPCI: Dict[str, Tuple[Decimal, Decimal, Decimal]] = {
    "01": (Decimal("1.063"), Decimal("1.160"), Decimal("1.068")),
    "99": (Decimal("1.040"), Decimal("1.092"), Decimal("1.097")),
}
LOCALITY_NAMES = {"01": "Northern New Jersey", "99": "Rest of New Jersey"}
# 26LOCCO.csv: counties in locality 01. Every other New Jersey county is in locality 99.
NORTHERN_NJ_COUNTIES = ["Bergen", "Essex", "Hudson", "Hunterdon", "Middlesex", "Morris", "Passaic", "Somerset", "Sussex", "Union", "Warren"]
NJ_COUNTIES = sorted(
    NORTHERN_NJ_COUNTIES
    + ["Atlantic", "Burlington", "Camden", "Cape May", "Cumberland", "Gloucester", "Mercer", "Monmouth", "Ocean", "Salem"]
)

Setting = Literal["nonfacility", "facility"]
Category = Literal["office", "emergency", "imaging", "therapy"]

COVERS: Dict[str, str] = {
    "office": "The Medicare amount for this service in a doctor’s office.",
    "emergency": (
        "The doctor’s fee for the visit only, at Medicare’s facility rate. The hospital’s own emergency room charges are not included."
    ),
    "imaging": (
        "The Medicare amount at an office or independent imaging center, including the reading. "
        "Hospital outpatient payments are not included."
    ),
    "therapy": "The Medicare amount in an office or outpatient therapy practice, for each 15 minutes.",
}


@dataclass(frozen=True)
class Service:
    code: str
    label: str
    category: Category
    setting: Setting
    work: Decimal
    pe_nonfacility: Decimal
    pe_facility: Decimal
    mp: Decimal

    @property
    def pe(self) -> Decimal:
        return self.pe_facility if self.setting == "facility" else self.pe_nonfacility


def _s(code: str, label: str, category: Category, setting: Setting, work: str, pe_nf: str, pe_f: str, mp: str) -> Service:
    return Service(code, label, category, setting, Decimal(work), Decimal(pe_nf), Decimal(pe_f), Decimal(mp))


SERVICES: List[Service] = [
    _s("99203", "New patient office visit (low complexity)", "office", "nonfacility", "1.60", "1.76", "0.38", "0.16"),
    _s("99204", "New patient office visit (moderate complexity)", "office", "nonfacility", "2.60", "2.47", "0.66", "0.24"),
    _s("99213", "Established patient office visit (low complexity)", "office", "nonfacility", "1.30", "1.46", "0.33", "0.09"),
    _s("99214", "Established patient office visit (moderate complexity)", "office", "nonfacility", "1.92", "2.00", "0.47", "0.14"),
    _s("99215", "Established patient office visit (high complexity)", "office", "nonfacility", "2.80", "2.75", "0.75", "0.21"),
    _s("99283", "Emergency department visit (low complexity)", "emergency", "facility", "1.60", "0.28", "0.28", "0.20"),
    _s("99284", "Emergency department visit (moderate complexity)", "emergency", "facility", "2.74", "0.45", "0.45", "0.35"),
    _s("99285", "Emergency department visit (high complexity)", "emergency", "facility", "4.00", "0.65", "0.65", "0.48"),
    _s("71046", "Chest X-ray, 2 views", "imaging", "nonfacility", "0.21", "0.76", "0.76", "0.02"),
    _s("70450", "CT scan of the head, without contrast", "imaging", "nonfacility", "0.83", "2.30", "2.30", "0.06"),
    _s("72148", "MRI of the lower back (lumbar spine), without contrast", "imaging", "nonfacility", "1.44", "4.20", "4.20", "0.10"),
    _s("73721", "MRI of a leg joint such as the knee, without contrast", "imaging", "nonfacility", "1.32", "4.71", "4.71", "0.09"),
    _s("74177", "CT of the abdomen and pelvis, with contrast", "imaging", "nonfacility", "1.77", "7.09", "7.09", "0.13"),
    _s("76700", "Ultrasound of the abdomen, complete", "imaging", "nonfacility", "0.79", "2.57", "2.57", "0.06"),
    _s("93000", "Electrocardiogram (ECG) with reading", "imaging", "nonfacility", "0.17", "0.27", "0.27", "0.02"),
    _s("97110", "Therapeutic exercise (physical therapy), 15 minutes", "therapy", "nonfacility", "0.45", "0.41", "0.41", "0.01"),
]
SERVICES_BY_CODE: Dict[str, Service] = {s.code: s for s in SERVICES}


def amount_cents(service: Service, locality: str) -> int:
    """CMS's formula for one locality, rounded to the nearest cent."""
    pw, pe, mp = GPCI[locality]
    dollars = (service.work * pw + service.pe * pe + service.mp * mp) * CONVERSION_FACTOR
    return int((dollars * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))
