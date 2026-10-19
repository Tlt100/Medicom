"""Uninsured New Jersey patients: published rules for Charity Care and the 2008 charge limit.

The eligibility math runs in the browser, so household income never reaches the server.
"""

from patientshield.features.uninsured.routes import router

ROUTERS = [router]
