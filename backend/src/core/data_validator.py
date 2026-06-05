import pandas as pd
from pathlib import Path
from loguru import logger

# ── Service validation schemas ────────────────────────────────────────────────
# Uses keyword-fuzzy matching: at least ONE keyword from each group must appear
# (case-insensitive, as a substring) in any column name.
# This handles real-world exports like "Pressure_Pa", "inlet_velocity", etc.

SERVICE_REQUIREMENTS = {
    "CFD": [
        {
            "label": "Position / coordinate (x, y, z, step, iter, node)",
            "keywords": ["x", "y", "z", "iter", "step", "node", "pos", "coord"],
        },
        {
            "label": "Flow variable (pressure, velocity, temperature, density, residual)",
            "keywords": ["press", "vel", "temp", "dens", "res", "mach", "turb", "energy", "flow", "viscosity"],
        },
    ],
    "FEA": [
        {
            "label": "Node / coordinate (x, y, z, node, element)",
            "keywords": ["x", "y", "z", "node", "elem", "coord"],
        },
        {
            "label": "Structural result (stress, strain, displacement, FOS, force)",
            "keywords": ["stress", "strain", "disp", "deflect", "fos", "safety", "mises", "force", "moment", "deform"],
        },
    ],
    "DEM": [
        {
            "label": "Spatial coordinate (x, y, lat, lon, easting, northing)",
            "keywords": ["x", "y", "lat", "lon", "east", "north", "coord"],
        },
        {
            "label": "Elevation / terrain (elev, z, height, altitude, slope, dem)",
            "keywords": ["elev", "z", "height", "alt", "slope", "dem", "terrain", "depth"],
        },
    ],
    "EFD": [
        {
            "label": "Sales / revenue column (sale, amount, revenue, gross, net)",
            "keywords": ["sale", "amount", "revenue", "gross", "net", "total", "cost", "price", "profit"],
        },
        {
            "label": "Time / date column (time, date, hour, day, shift, period)",
            "keywords": ["time", "date", "hour", "day", "shift", "period", "month", "year", "week"],
        },
    ],
    # "Process Modeling" stored normalised — lookup is case-insensitive below
    "PROCESS MODELING": [
        {
            "label": "Primary process variable (flow, temperature, pressure, concentration, level)",
            "keywords": ["flow", "temp", "press", "rate", "conc", "level", "volume", "viscosity"],
        },
        {
            "label": "Time / step axis (time, step, iteration, cycle)",
            "keywords": ["time", "step", "iter", "cycle", "t_", "timestamp", "elapsed"],
        },
    ],
}

# Alias map so users can pass any reasonable variant of a service name
_SERVICE_ALIASES = {
    "PROCESS": "PROCESS MODELING",
    "PROCESS MODELING": "PROCESS MODELING",
    "PROCESS_MODELING": "PROCESS MODELING",
    "CFD": "CFD",
    "FEA": "FEA",
    "DEM": "DEM",
    "EFD": "EFD",
}

FALLBACK_REQUIREMENT = [
    {"label": "At least one numeric column", "keywords": ["__numeric__"]},
]


class DataValidator:
    """
    Validates uploaded CSV / Excel files against service-specific column
    requirements before wasting AI tokens or processing time.

    Uses fuzzy keyword matching so real-world column names like
    'Pressure_Pa', 'inlet_velocity', or 'von_mises_stress' are accepted.
    """

    def _resolve_service(self, service: str) -> str:
        """Normalise the service name to match SERVICE_REQUIREMENTS keys."""
        return _SERVICE_ALIASES.get(service.upper().strip(), service.upper().strip())

    def _load_df(self, file_path: str) -> pd.DataFrame:
        """Load first 5 rows to check column names without reading full file."""
        suffix = Path(file_path).suffix.lower()
        if suffix in [".xlsx", ".xls"]:
            return pd.read_excel(file_path, nrows=5)
        return pd.read_csv(file_path, nrows=5)

    def validate(self, file_path: str, service: str) -> dict:
        """
        Returns a structured validation result:
        {
            "valid": bool,
            "filename": str,
            "service": str,
            "columns_found": [str],
            "checks": [{"label": str, "passed": bool, "matched_column": str|None}]
        }
        """
        filename = Path(file_path).name
        service_key = self._resolve_service(service)

        try:
            df = self._load_df(file_path)
        except Exception as e:
            return {
                "valid": False,
                "filename": filename,
                "service": service,
                "columns_found": [],
                "checks": [
                    {"label": "File readable", "passed": False, "matched_column": str(e)}
                ],
            }

        lower_cols = {c.lower(): c for c in df.columns}
        all_cols = list(df.columns)

        requirements = SERVICE_REQUIREMENTS.get(service_key, FALLBACK_REQUIREMENT)
        checks = []
        all_passed = True

        for req in requirements:
            matched = None

            if req["keywords"] == ["__numeric__"]:
                num_cols = df.select_dtypes(include=["number"]).columns.tolist()
                matched = num_cols[0] if num_cols else None
            else:
                for keyword in req["keywords"]:
                    for col_lower, col_orig in lower_cols.items():
                        if keyword in col_lower:
                            matched = col_orig
                            break
                    if matched:
                        break

            passed = matched is not None
            if not passed:
                all_passed = False

            checks.append(
                {"label": req["label"], "passed": passed, "matched_column": matched}
            )

        return {
            "valid": all_passed,
            "filename": filename,
            "service": service,
            "columns_found": all_cols,
            "checks": checks,
        }

    def validate_many(self, file_paths: list, service: str) -> dict:
        """Validate multiple files. Returns overall validity + per-file results."""
        results = [self.validate(fp, service) for fp in file_paths]
        return {
            "overall_valid": all(r["valid"] for r in results),
            "files": results,
        }
