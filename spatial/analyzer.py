"""
OTE - Observation Trust Engine
Member 2: Spatial & Cross-Station Analytics
Module: SpatialAnalyzer (Phase 7)
Authoritative Source: OTE_Member2_Implementation_Bible.pdf (Phase 7 & Section 9.2)
"""

import math
from typing import Any, Dict, List, Optional, Set, Tuple
from spatial.interfaces import Station, ObservationSnapshot, SpatialNeighbor, SpatialStatus
from spatial.config import SpatialConfig, DEFAULT_SPATIAL_CONFIG
from spatial.station_registry import StationRegistry
from spatial.neighbors import NeighborCandidate, find_k_nearest_neighbors
from spatial.idw import compute_idw_consensus
from spatial.residual import compute_spatial_residual, classify_spatial_status
from spatial.contamination import filter_valid_neighbors, ExclusionReason

SUPPORTED_VARIABLES: Tuple[str, ...] = ("temperature", "humidity", "pressure")


class SpatialAnalyzer:
    """
    Unified multi-variable spatial analysis engine.
    Orchestrates neighbor discovery, contamination filtering, IDW consensus,
    residual standardization, Section 9.2 evidence assembly, and fleet-level rollup.
    """

    def __init__(
        self,
        registry: StationRegistry,
        config: SpatialConfig = DEFAULT_SPATIAL_CONFIG,
    ) -> None:
        self.registry = registry
        self.config = config

    def _analyze_single_variable(
        self,
        target_station: Station,
        target_snapshot: Optional[ObservationSnapshot],
        candidate_neighbors: List[NeighborCandidate],
        station_snapshots: Dict[str, ObservationSnapshot],
        variable: str,
    ) -> Tuple[Dict[str, Any], List[str], List[str]]:
        """
        Generic single-variable spatial evaluation pipeline.
        Reused identically across temperature, humidity, and pressure.
        """
        candidate_count = len(candidate_neighbors)

        # 1. Target observation retrieval & validity
        target_val: Optional[float] = None
        if (
            target_snapshot is not None
            and target_snapshot.valid
            and target_snapshot.values is not None
            and variable in target_snapshot.values
        ):
            raw_target = target_snapshot.values[variable]
            if isinstance(raw_target, (int, float)) and math.isfinite(raw_target):
                target_val = float(raw_target)

        # 2. Contamination filtering (Mandatory Pre-Step)
        self_outlier_thresh = getattr(self.config, "self_outlier_z_threshold", 3.0)
        eps = getattr(self.config, "variance_epsilon", 1e-6)

        valid_candidates, excluded = filter_valid_neighbors(
            candidate_neighbors,
            station_snapshots,
            variable,
            self_outlier_z_threshold=self_outlier_thresh,
            variance_epsilon=eps,
        )

        valid_count = len(valid_candidates)
        excluded_ids = [ex[0].station.station_id for ex in excluded]

        # 3. IDW Consensus using valid candidates
        consensus: Optional[float] = None
        used_neighbors: List[SpatialNeighbor] = []
        power_val = getattr(self.config, "idw_power_p", getattr(self.config, "idw_power", 2.0))

        if valid_count > 0:
            consensus, used_neighbors = compute_idw_consensus(
                target_station.station_id,
                valid_candidates,
                station_snapshots,
                variable,
                power_p=power_val,
            )

        included_ids = [n.station_id for n in used_neighbors]

        # 4. Residual and Spatial Status
        raw_res, std_res, scale = compute_spatial_residual(
            target_value=target_val,
            consensus=consensus,
            used_neighbors=used_neighbors,
            variance_epsilon=eps,
        )

        z_thresh = getattr(self.config, "spatial_z_threshold", getattr(self.config, "anomaly_threshold_z", 2.5))
        internal_status = classify_spatial_status(
            standardized_residual=std_res,
            used_neighbors=used_neighbors,
            spatial_z_threshold=z_thresh,
        )

        # Map to Section 9.2 contract status strings
        if internal_status == SpatialStatus.CONSISTENT:
            contract_status = "AGREEMENT"
        elif internal_status == SpatialStatus.SUSPECT:
            contract_status = "DISAGREEMENT"
        else:
            contract_status = "INSUFFICIENT_SPATIAL_EVIDENCE"

        # 5. Agreement count and disagreement score
        # [ASSUMPTION -- PROJECT OWNER CONFIRMATION REQUIRED: disagreement_score definition]
        agreement_count = 0
        disagreement_score = 0.0

        if contract_status == "INSUFFICIENT_SPATIAL_EVIDENCE":
            agreement_count = 0
            disagreement_score = 0.0
        else:
            if target_val is not None:
                for n in used_neighbors:
                    diff = abs(n.observed_value - target_val)
                    if scale > 0.0 and (diff / scale) <= z_thresh:
                        agreement_count += 1
                    elif scale == 0.0 and math.isclose(diff, 0.0, abs_tol=1e-6):
                        agreement_count += 1

            if std_res is not None:
                norm_z = abs(std_res) / (2.0 * z_thresh)
                disagreement_score = round(min(1.0, max(0.0, norm_z)), 2)

        var_evidence: Dict[str, Any] = {
            "neighbor_count": candidate_count,
            "valid_neighbor_count": valid_count,
            "agreement_count": agreement_count,
            "disagreement_score": disagreement_score,
            "consensus": round(consensus, 2) if consensus is not None else None,
            "target_value": round(target_val, 2) if target_val is not None else None,
            "standardized_residual": round(std_res, 2) if std_res is not None else None,
            "status": contract_status,
        }

        return var_evidence, included_ids, excluded_ids

    def _rollup_fleet_status_and_strength(
        self,
        variables_evidence: Dict[str, Any],
    ) -> Tuple[str, str]:
        """
        Roll up variable-level evidence into fleet spatial_status and evidence_strength.

        [ASSUMPTION -- PROJECT OWNER CONFIRMATION REQUIRED: Fleet-level spatial_status & evidence_strength rollup logic]
        Development Hierarchy Rule per Bible Section 9.4:
        DISAGREEMENT > AGREEMENT > INSUFFICIENT_SPATIAL_EVIDENCE
        """
        statuses = [
            var_ev["status"]
            for var_ev in variables_evidence.values()
        ]

        valid_statuses = [
            s for s in statuses
            if s != "INSUFFICIENT_SPATIAL_EVIDENCE"
        ]

        # 1. Fleet Spatial Status Rollup
        if any(s == "DISAGREEMENT" for s in valid_statuses):
            fleet_status = "DISAGREEMENT"
        elif any(s == "AGREEMENT" for s in valid_statuses):
            fleet_status = "AGREEMENT"
        else:
            fleet_status = "INSUFFICIENT_SPATIAL_EVIDENCE"

        # 2. Evidence Strength Rollup
        valid_count = len(valid_statuses)
        if valid_count == 3:
            evidence_strength = "HIGH"
        elif valid_count == 2:
            evidence_strength = "MEDIUM"
        elif valid_count == 1:
            evidence_strength = "LOW"
        else:
            evidence_strength = "NONE"

        return fleet_status, evidence_strength

    def analyze(
        self,
        target_id: str,
        station_snapshots: Dict[str, ObservationSnapshot],
    ) -> Dict[str, Any]:
        """
        Execute multi-variable spatial analysis for target station.
        Produces Section 9.2 compliant contract dictionary.
        """
        target_station = self.registry.get_station(target_id)
        if target_station is None:
            return {
                "station_id": target_id,
                "variables": {
                    var: {
                        "neighbor_count": 0,
                        "valid_neighbor_count": 0,
                        "agreement_count": 0,
                        "disagreement_score": 0.0,
                        "consensus": None,
                        "target_value": None,
                        "standardized_residual": None,
                        "status": "INSUFFICIENT_SPATIAL_EVIDENCE",
                    }
                    for var in SUPPORTED_VARIABLES
                },
                "spatial_status": "INSUFFICIENT_SPATIAL_EVIDENCE",
                "evidence_strength": "NONE",
                "included_neighbors": [],
                "excluded_neighbors": [],
                "explanation": "Target station not found in registry.",
            }

        target_snapshot = station_snapshots.get(target_id)

        # Candidate discovery
        k_val = getattr(self.config, "k_neighbors", 5)
        max_rad = getattr(self.config, "max_radius_km", 100.0)

        candidate_neighbors = find_k_nearest_neighbors(
            target_station=target_station,
            registry=self.registry,
            k=k_val,
            max_radius_km=max_rad,
        )

        variables_evidence: Dict[str, Any] = {}
        all_included: Set[str] = set()
        all_excluded: Set[str] = set()

        # Generic loop over supported variables
        for var in SUPPORTED_VARIABLES:
            var_ev, inc_ids, exc_ids = self._analyze_single_variable(
                target_station=target_station,
                target_snapshot=target_snapshot,
                candidate_neighbors=candidate_neighbors,
                station_snapshots=station_snapshots,
                variable=var,
            )
            variables_evidence[var] = var_ev
            all_included.update(inc_ids)
            all_excluded.update(exc_ids)

        # Fleet-level rollup
        fleet_status, evidence_strength = self._rollup_fleet_status_and_strength(variables_evidence)

        # Contract explanation string placeholder (Full explanation generation belongs to Phase 8)
        if fleet_status == "DISAGREEMENT":
            explanation = "Target observation is not corroborated by nearby stations."
        elif fleet_status == "AGREEMENT":
            explanation = "Target observation is corroborated by nearby stations."
        else:
            explanation = "Insufficient spatial evidence available from nearby stations."

        return {
            "station_id": target_id,
            "variables": variables_evidence,
            "spatial_status": fleet_status,
            "evidence_strength": evidence_strength,
            "included_neighbors": sorted(list(all_included)),
            "excluded_neighbors": sorted(list(all_excluded)),
            "explanation": explanation,
        }
