# OTE Member 2 — Spatial & Cross-Station Analytics Public Contract Specification
**Authoritative Source:** `OTE_Member2_Implementation_Bible.pdf`  
**Phase:** 9 (Contract Finalization)  
**Status:** FROZEN & AUTHORITATIVE

---

## 1. System Scope & Boundaries

### 1.1 Purpose
Member 2 provides deterministic, multi-variable spatial evidence regarding whether a weather observation reported by an Automatic Weather Station (AWS) is corroborated or contradicted by observations from neighboring physical stations.

### 1.2 Upstream & Downstream Boundaries
* **Upstream Inputs:** Station coordinate metadata from `StationRegistry` and time-synchronized sensor readings from `ObservationSnapshot`.
* **Output Deliverable:** A deterministic Section 9.2-compliant dictionary containing variable-level consensus, standardized residuals, status classifications, fleet-level rollups, and natural language explanations.
* **Downstream Evidence Boundary:** Member 2 generates **Spatial Evidence**. It does **not** produce final OTE trust states
  (such as `NORMALX
, `WEATHER_EVENT`, `SENSOR_ANOMALY`, `COMMUNICATION_FAILURE`, `UNCERTAIN`). Final decision classification is performed exclusively by the downstream evidence fusion layer.

---

## 2. Public Interface Reference

### 2.1 SpatialAnalyzer
The primary analysis engine.

```python
class SpatialAnalyzer:
    def __init__(
        self,
        registry: StationRegistry,
        config: SpatialConfig = DEFAULT_SPATIAL_CONFIG,
    ) -> None:
        ...

    def analyze(
        self,
        target_id: str,
        station_snapshots: Dict[str, ObservationSnapshot],
    ) -> Dict[str, Any]:
        ...
```(Parameters: `target_id` (str), `station_snapshots` (Dict[str, ObservationSnapshot]); Returns: Section 9.2 dictionary).

### 2.2 Explanation Generator
```python
def build_explanation(evidence: Dict[str, Any]) -> str:
    ...
```(Parameters: Section 9.2 evidence dictionary; Returns: deterministic template string).

### 2.3 Station Registry
```python
class StationRegistry(ABC):
    abstractmethod
    def register_station(self, station: Station) -> None: ...
    abstractmethod
    def get_station(self, station_id: str) -> Optional[Station]: ...
    abstractmethod
    def get_all_stations(self) -> List[Station]: ...
    abstractmethod
    def get_valid_stations(self) -> List[Station]: ...
```

---

## 3. Data Models

### 3.1 Station
* `station_id: str` — Unique station identifier.
* `latitude: float` — Geographic latitude in degrees (in [-90.0, 90.0]).
* `longitude: float` — Geographic longitude in degrees (in [-180.0, 180.0]).
* `elevation_m: Optional[float] = None` — Elevation above sea level in meters.

### 3.2 ObservationSnapshot
* `timestamp: float` — Unix epoch timestamp in seconds.
* `values: Dict[str, Optional[float]]` — Mapping of variable names ("temperature", "humidity", "pressure") to numerical readings.
* `valid: bool = True` — Upstream validation flag.

3## 3.3 SpatialNeighbor
* `station_id: str` — Neighbor station identifier.
* `distance_km: float` — Great-circle distance to target station.
+ `observed_value: float` — Variable value observed at the neighbor station.
* `weight: float` — Normalized IDW weight (sum w_i = 1.0).

---

## 4. Section 9.2 Spatial Evidence Schema

The canonical evidence dictionary exported by `SpatialAnalyzer.analyze()`:

* **Top-Level Fields:** `station_id`, jvariables`, `spatial_status`, `evidence_strength`, `included_neighbors`, `excluded_neighbors`, `explanation`.
* **Variable-Level Fields:** `neighbor_count`, `valid_neighbor_count`, `agreement_count`, `disagreement_score`, `consensus`, `target_value`, `standardized_residual`, `status`.

---

## 5. Status & Hierarchy Semantics

### 5.1 Variable Status Classification
* **AGREEMENT**: |z| <= 2.5. Target aligns with local consensus.
* **DISAGREEMENT**: |z| > 2.5. Target deviates significantly from local consensus.
+ **INSUFFCIENT_SPATIAL_EVIDENCE**: Missing target data, invalid snapshot, or < 2 valid neighbors.

### 5.2 Fleet Status Rollup
Rollup follows the most-severe hierarchy: DISAGREEMENT > AGREEMENT > INSUFFICIENT_SPATIAL_EVIDENCE.

### 5.3 Evidence Strength
 3 valid variables => "HIGH", 2 => "MEDIUM", 1 => "LOW", 0 => "NONE".

---

## 6. Contamination Defense

Candidate neighbors are filtered prior to consensus. Excluded stations are tracked in `excluded_neighbors`.
+ Exclusion reasons (`ExclusionReason`): `MISSING_OBSERVATION`, `INVALID_OBSERVATION`, `INVALID_COORDINATES`, `SELF_OUTLIER_Z_SCORE`.

---

## 7. Mathematical Formulations

### 7.1 Distance
Haversine great-circle distance with Earth radius R = 6371.0 km.

### 7.2 IDTS Spatial Consensus
c = sum(w_i * x_i), w_i = d_i^("p) / sum(d_j^("p)). Co-located stations (d = 0.0) receive dominant equal weights.

### 7.3 Reference Scale & Standardized Residual
s = sqrt(sum((x_i - mean_x)^z2) / (n - 1)) + epsilon, z = (x_target - c) / s.

---

## 8. Centralized Calibration Registry (`spatial/config.py`)
* `config.k_neighbors = 5` *Candidate neighbor limit*)
* `config.max_radius_km = 50.0` *Maximum search distance*)
* `config.idw_power = 2.0` *IDW power exponent*)
* `config.min_valid_neighbors = 2` *Minimum valid neighbors required*)
* `config.self_outlier_z_threshold = 3.0` *Neighbor outlier cutoff*)
* `config.anomaly_threshold_z = 2.5` *Disagreement ze-threshold*)
* `config.variance_epsilon = 1e-6` (Zero-dispersion denominator guard*)

---

## 9. Determinism & Performance
* Determinism: Seeded, pure functional calculations produce bitwise identical outputs.
* Performance: Sub-millisecond evaluation per station snapshot.
* Dependencies: Python standard library only (no external GIS/ML libraries).
