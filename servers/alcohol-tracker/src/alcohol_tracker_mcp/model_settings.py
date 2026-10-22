"""Vendored from the Alcohol Tracker app (alcohol_tracker/core/settings.py), Qt-free. Keep in sync."""

from __future__ import annotations

from dataclasses import dataclass

BAC_MODEL_WATSON = "watson"
BAC_MODEL_WIDMARK = "widmark"


@dataclass(frozen=True)
class EstimateSettings:
    # --- Absorption / elimination (one-compartment pharmacokinetics) ---
    absorption_minutes: int = 45
    absorption_lag_minutes: float = 15.0
    elimination_standard_drinks_per_hour: float = 0.67

    # --- Tolerance model ---
    tolerance_half_life_days: float = 7.0
    tolerance_max_extra_dose: float = 1.0
    tolerance_half_saturation_exposure: float = 3.0

    # --- What counts as one "standard drink" for this user ---
    standard_drink_volume_oz: float = 1.5
    standard_drink_abv_percent: float = 40.0

    # --- Body model (drives BAC) ---
    user_weight_lbs: float = 150.0
    user_gender: str = "M"
    user_height_cm: float = 178.0
    user_age_years: float = 30.0
    bac_model: str = BAC_MODEL_WATSON

    @property
    def standard_drink_pure_alcohol_oz(self) -> float:
        return self.standard_drink_volume_oz * (self.standard_drink_abv_percent / 100.0)
