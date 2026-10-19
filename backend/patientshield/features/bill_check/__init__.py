"""Bill check: compare a provider's bill with the insurer's Explanation of Benefits (EOB).

Importing this package registers the "eob" and "bill" extractors with the core document pipeline.
"""

from patientshield.features.bill_check import extraction as _extraction  # noqa: F401  (registers the extractors)
from patientshield.features.bill_check.routes import router

ROUTERS = [router]
