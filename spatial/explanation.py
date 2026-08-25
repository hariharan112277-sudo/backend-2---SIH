"""
OTE - Observation Trust Engine
Member 2: Spatial & Cross-Station Analytics
Module: Deterministic Explanation Generator (Phase 8)
Authoritative Source: OTE_Member2_Implementation_Bible.pdf (Phase 8 & Section 9.2)
"""

from typing import Any, Dict, List


def build_explanation(evidence: Dict[str, Any]) -> str:
    """
    Generate deterministic, template-based human-readable explanation text
    directly from Section 9.2 spatial evidence contract dictionary.

    Scenario-Independent: Operates purely on evidence dictionary fields.
    """
    stn_id = evidence.get("station_id", "UNKNOWN")
    spatial_status = evidence.get("spatial_status", "INSUFFICIENT_SPATIAL_EVIDENCE")
    evidence_strength = evidence.get("evidence_strength", "NONE")
    variables = evidence.get("variables", {})
    included_neighbors = evidence.get("included_neighbors", [])
    excluded_neighbors = evidence.get("excluded_neighbors", [])

    # Categorize variables by status
    agree_vars: List[str] = []
    disagree_vars: List[str] = []
    insufficient_vars: List[str] = []

    for var_name, var_data in variables.items():
        v_status = var_data.get("status")
        t_val = var_data.get("target_value")
        c_val = var_data.get("consensus")
        z_val = var_data.get("standardized_residual")

        if v_status == "AGREEMENT":
            detail = f"{var_name}"
            if t_val is not None and c_val is not None and z_val is not None:
                detail += f" (target={t_val}, consensus={c_val}, z={z_val:.2f})"
            agree_vars.append(detail)
        elif v_status == "DISAGREEMENT":
            detail = f"{var_name}"
            if t_val is not None and c_val is not None and z_val is not None:
                detail += f" (target={t_val}, consensus={c_val}, z={z_val:.2f})"
            disagree_vars.append(detail)
        else:
            insufficient_vars.append(var_name)

    parts: List[str] = []

    # 1. Primary Status Clause
    if spatial_status == "DISAGREEMENT":
        parts.append(
            f"Target station {stn_id} exhibits spatial disagreement with nearby stations "
            f"(evidence strength: {evidence_strength})."
        )
        if disagree_vars:
            parts.append(f"Variables in disagreement: {', '.join(disagree_vars)}.")
        if agree_vars:
            agree_names = [v.split()[0] for v in agree_vars]
            parts.append(f"Variables in agreement: {', '.join(agree_names)}.")
    elif spatial_status == "AGREEMENT":
        parts.append(
            f"Target station {stn_id} observations are spatially corroborated by nearby stations "
            f"with {evidence_strength} evidence strength."
        )
        if agree_vars:
            parts.append(f"Variables in agreement: {', '.join(agree_vars)}.")
    else:
        parts.append(
            f"Target station {stn_id} has insufficient spatial evidence available from nearby stations "
            f"(evidence strength: {evidence_strength})."
        )
        if insufficient_vars:
            parts.append(f"Insufficient variables: {', '.join(insufficient_vars)}.")

    # 2. Neighbor & Contamination Clause
    valid_count = len(included_neighbors)
    excluded_count = len(excluded_neighbors)

    if spatial_status != "INSUFFICIENT_SPATIAL_EVIDENCE" or valid_count > 0:
        neighbor_clause = f"Evaluated using {valid_count} valid neighbors"
        if excluded_count > 0:
            neighbor_clause += f" ({excluded_count} candidate neighbor(s) excluded due to data quality/outlier checks)"
        parts.append(f"{neighbor_clause}.")
    else:
        parts.append(f"Evaluated using {valid_count} valid neighbors.")

    # 3. Correlated-Fault Caveat per Bible
    if spatial_status == "AGREEMENT":
        parts.append("Spatial corroboration provides supporting evidence.")

    return " ".join(parts)
