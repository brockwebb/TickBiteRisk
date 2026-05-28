from __future__ import annotations

import math
from dataclasses import dataclass

from tickbiterisk.runtime.risk_lookup import (
    CLINICAL_DISCLAIMER,
    GUIDANCE_LINKS,
    CountyWeekRiskResponse,
)


CDC_PROPHYLAXIS_LINKS = [
    {
        "title": "CDC: Guidance for clinicians after a tick bite",
        "url": "https://www.cdc.gov/lyme/media/pdfs/Caring-for-Patients-after-a-Tick-Bite.pdf",
    },
    {
        "title": "CDC: Lyme disease prophylaxis after tick bite",
        "url": "https://www.cdc.gov/lyme/media/pdfs/Lyme-Disease-Prophylaxis-After-Tick-Bite-Poster.pdf",
    },
]

SPECIES_ALIASES = {
    "ixodes_scapularis": "ixodes_scapularis",
    "ixodes": "ixodes_scapularis",
    "blacklegged": "ixodes_scapularis",
    "blacklegged_tick": "ixodes_scapularis",
    "deer_tick": "ixodes_scapularis",
    "possible_ixodes": "possible_ixodes",
    "possible_blacklegged": "possible_ixodes",
    "unknown": "unknown",
    "tick_unavailable": "unknown",
    "not_ixodes": "not_ixodes",
    "dog_tick": "not_ixodes",
    "american_dog_tick": "not_ixodes",
    "lone_star": "not_ixodes",
    "lone_star_tick": "not_ixodes",
}

STAGE_ALIASES = {
    "nymph": "nymph",
    "nymphal": "nymph",
    "adult": "adult",
    "adult_female": "adult",
    "adult_male": "adult",
    "larva": "larva",
    "larval": "larva",
    "unknown": "unknown",
}

ENGORGEMENT_ALIASES = {
    "flat": "flat",
    "unfed": "flat",
    "slightly_engorged": "slightly_engorged",
    "partly_engorged": "slightly_engorged",
    "engorged": "engorged",
    "blood_fed": "engorged",
    "unknown": "unknown",
}


class SingleBiteRiskInputError(ValueError):
    """Raised when single-bite risk inputs are invalid."""


@dataclass(frozen=True)
class SingleBiteRiskResponse:
    county_fips: str
    county_name: str
    query_date: str
    mmwr_year: int
    mmwr_week: int
    disease: str
    single_bite_risk_score: int
    single_bite_risk_band: str
    single_bite_risk_score_raw: float
    pep_consideration: str
    pep_criteria: list[dict[str, str]]
    forecast_context: dict[str, object]
    input_summary: dict[str, object]
    evidence_modifiers: dict[str, float]
    caveats: list[str]
    risk_interpretation: str
    clinical_disclaimer: str
    guidance_links: list[dict[str, str]]


def estimate_single_bite_risk(
    *,
    baseline: CountyWeekRiskResponse,
    tick_species: str,
    tick_stage: str = "unknown",
    attachment_hours: float | None = None,
    engorgement: str = "unknown",
    hours_since_removal: float | None = None,
    doxycycline_safe: bool | None = None,
    tick_count: int = 1,
) -> SingleBiteRiskResponse:
    species = _normalize_choice(tick_species, SPECIES_ALIASES, "tick_species")
    stage = _normalize_choice(tick_stage, STAGE_ALIASES, "tick_stage")
    engorgement_level = _normalize_choice(
        engorgement,
        ENGORGEMENT_ALIASES,
        "engorgement",
    )
    attachment = _validate_optional_hours(
        attachment_hours,
        "attachment_hours",
        maximum=240,
    )
    removal_window = _validate_optional_hours(
        hours_since_removal,
        "hours_since_removal",
        maximum=24 * 30,
    )
    if tick_count < 1 or tick_count > 20:
        raise SingleBiteRiskInputError("tick_count must be between 1 and 20")

    modifiers = {
        "location_season": _location_season_modifier(baseline),
        "tick_species": _species_modifier(species),
        "tick_stage": _stage_modifier(stage),
        "attachment": _attachment_modifier(attachment, engorgement_level),
    }
    raw_single = (
        modifiers["location_season"]
        * modifiers["tick_species"]
        * modifiers["tick_stage"]
        * modifiers["attachment"]
    )
    raw_single = max(0.0, min(1.0, raw_single))
    combined = 1 - ((1 - raw_single) ** tick_count)
    score_raw = round(combined * 10, 6)
    score = max(1, min(10, math.ceil(score_raw)))
    pep_criteria = _pep_criteria(
        baseline=baseline,
        species=species,
        stage=stage,
        attachment_hours=attachment,
        engorgement=engorgement_level,
        hours_since_removal=removal_window,
        doxycycline_safe=doxycycline_safe,
    )
    return SingleBiteRiskResponse(
        county_fips=baseline.county_fips,
        county_name=baseline.county_name,
        query_date=baseline.query_date,
        mmwr_year=baseline.mmwr_year,
        mmwr_week=baseline.mmwr_week,
        disease="lyme",
        single_bite_risk_score=score,
        single_bite_risk_band=_risk_band(score),
        single_bite_risk_score_raw=score_raw,
        pep_consideration=_pep_consideration(pep_criteria),
        pep_criteria=pep_criteria,
        forecast_context={
            "county_week_risk_score": baseline.risk_score,
            "county_week_risk_category": baseline.risk_category,
            "data_year": baseline.data_year,
            "model_name": baseline.model_name,
            "seasonality_source_id": baseline.seasonality_source_id,
            "predicted_weekly_incidence_per_100k": (
                baseline.predicted_weekly_incidence_per_100k
            ),
            "score_interpretation": baseline.score_interpretation,
        },
        input_summary={
            "tick_species": species,
            "tick_stage": stage,
            "attachment_hours": attachment,
            "engorgement": engorgement_level,
            "hours_since_removal": removal_window,
            "doxycycline_safe": doxycycline_safe,
            "tick_count": tick_count,
        },
        evidence_modifiers=modifiers,
        caveats=_caveats(species=species, stage=stage, baseline=baseline),
        risk_interpretation=(
            "Single-bite Lyme decision-support score on a 1-10 scale. It uses "
            "the county-week forecast as location/season context and adjusts "
            "for tick identity, life stage, attachment time, engorgement, and "
            "tick count. This is not an absolute infection probability, "
            "diagnosis, or treatment recommendation."
        ),
        clinical_disclaimer=CLINICAL_DISCLAIMER,
        guidance_links=[*GUIDANCE_LINKS, *CDC_PROPHYLAXIS_LINKS],
    )


def _pep_criteria(
    *,
    baseline: CountyWeekRiskResponse,
    species: str,
    stage: str,
    attachment_hours: float | None,
    engorgement: str,
    hours_since_removal: float | None,
    doxycycline_safe: bool | None,
) -> list[dict[str, str]]:
    return [
        {
            "criterion": "lyme_common_area",
            "status": "meets" if baseline.county_fips.startswith("24") else "uncertain",
            "explanation": (
                "Maryland is treated as a Lyme-common geography for this v0 "
                "Maryland-only product; local county-week forecast is included "
                "separately as context."
            ),
        },
        _tick_identity_criterion(species=species, stage=stage),
        _attachment_criterion(
            attachment_hours=attachment_hours,
            engorgement=engorgement,
        ),
        {
            "criterion": "removal_window",
            "status": _removal_window_status(hours_since_removal),
            "explanation": (
                "CDC prophylaxis guidance is most relevant when prophylaxis can "
                "start within 72 hours after tick removal."
            ),
        },
        {
            "criterion": "doxycycline_safety",
            "status": _doxycycline_status(doxycycline_safe),
            "explanation": (
                "A healthcare professional must determine whether doxycycline "
                "is safe for the person."
            ),
        },
    ]


def _tick_identity_criterion(*, species: str, stage: str) -> dict[str, str]:
    if species == "ixodes_scapularis" and stage in {"nymph", "adult"}:
        status = "meets"
    elif species == "not_ixodes" or stage == "larva":
        status = "not_met"
    else:
        status = "uncertain"
    return {
        "criterion": "tick_identity",
        "status": status,
        "explanation": (
            "CDC prophylaxis guidance focuses on adult or nymphal blacklegged "
            "ticks for Lyme disease."
        ),
    }


def _attachment_criterion(
    *,
    attachment_hours: float | None,
    engorgement: str,
) -> dict[str, str]:
    if engorgement == "engorged" or (
        attachment_hours is not None and attachment_hours >= 36
    ):
        status = "meets"
    elif engorgement == "flat" or (
        attachment_hours is not None and attachment_hours < 24
    ):
        status = "not_met"
    else:
        status = "uncertain"
    return {
        "criterion": "attachment_duration",
        "status": status,
        "explanation": (
            "CDC clinician guidance uses estimated attachment of at least 36 "
            "hours or engorgement as a key Lyme prophylaxis consideration."
        ),
    }


def _pep_consideration(criteria: list[dict[str, str]]) -> str:
    statuses = {criterion["status"] for criterion in criteria}
    if statuses == {"meets"}:
        return "meets_cdc_consideration_criteria"
    if "not_met" in statuses:
        return "does_not_meet_cdc_consideration_criteria"
    return "partially_meets_cdc_consideration_criteria"


def _removal_window_status(hours_since_removal: float | None) -> str:
    if hours_since_removal is None:
        return "uncertain"
    return "meets" if hours_since_removal <= 72 else "not_met"


def _doxycycline_status(doxycycline_safe: bool | None) -> str:
    if doxycycline_safe is None:
        return "uncertain"
    return "meets" if doxycycline_safe else "not_met"


def _species_modifier(species: str) -> float:
    return {
        "ixodes_scapularis": 1.0,
        "possible_ixodes": 0.75,
        "unknown": 0.5,
        "not_ixodes": 0.05,
    }[species]


def _stage_modifier(stage: str) -> float:
    return {
        "nymph": 1.0,
        "adult": 0.85,
        "unknown": 0.7,
        "larva": 0.1,
    }[stage]


def _attachment_modifier(
    attachment_hours: float | None,
    engorgement: str,
) -> float:
    if attachment_hours is None:
        base = 0.7
    elif attachment_hours < 24:
        base = 0.15
    elif attachment_hours < 36:
        base = 0.45
    elif attachment_hours < 48:
        base = 1.0
    elif attachment_hours < 72:
        base = 1.25
    else:
        base = 1.4

    if engorgement == "flat":
        return min(base, 0.2)
    if engorgement == "slightly_engorged":
        return max(base, 0.75)
    if engorgement == "engorged":
        return max(base, 1.15)
    return base


def _risk_band(score: int) -> str:
    if score >= 9:
        return "high"
    if score >= 7:
        return "elevated"
    if score >= 5:
        return "moderate"
    if score >= 3:
        return "low"
    return "very_low"


def _location_season_modifier(baseline: CountyWeekRiskResponse) -> float:
    baseline_modifier = baseline.risk_score / 10
    if baseline.county_fips.startswith("24"):
        return round(max(baseline_modifier, 0.45), 6)
    return round(baseline_modifier, 6)


def _caveats(
    *,
    species: str,
    stage: str,
    baseline: CountyWeekRiskResponse,
) -> list[str]:
    caveats = [
        "not_calibrated_absolute_probability",
        "not_diagnosis_or_treatment_recommendation",
        "symptoms_override_model_seek_care",
    ]
    if species == "not_ixodes":
        caveats.append("non_ixodes_lyme_vector_unlikely")
    if stage == "unknown" or species in {"unknown", "possible_ixodes"}:
        caveats.append("tick_identification_uncertain")
    if "using_latest_available_year" in baseline.data_quality_flags:
        caveats.append("using_latest_available_forecast_year")
    if baseline.county_fips.startswith("24") and baseline.risk_score < 5:
        caveats.append("maryland_high_incidence_geography_floor")
    return caveats


def _normalize_choice(
    value: str,
    aliases: dict[str, str],
    field_name: str,
) -> str:
    normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    try:
        return aliases[normalized]
    except KeyError as exc:
        allowed = ", ".join(sorted(set(aliases)))
        raise SingleBiteRiskInputError(
            f"{field_name} must be one of: {allowed}"
        ) from exc


def _validate_optional_hours(
    value: float | None,
    field_name: str,
    *,
    maximum: float,
) -> float | None:
    if value is None:
        return None
    parsed = float(value)
    if parsed < 0 or parsed > maximum:
        raise SingleBiteRiskInputError(
            f"{field_name} must be between 0 and {int(maximum)}"
        )
    return parsed
