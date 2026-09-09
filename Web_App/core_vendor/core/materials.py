"""Core material definitions and physical property models."""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class Material:
    """Linear isotropic material properties.

    Mechanical properties are always present. Thermal properties are *optional*
    (default ``None``) and only required by thermal studies; adding them keeps
    existing materials backward compatible while giving thermal analyses the
    data they need (see ``with_thermal_properties``).
    """
    name: str
    young_modulus: float  # Pa (or N/mm^2 depending on units)
    poisson_ratio: float
    density: float        # kg/m^3
    yield_strength: float # Pa
    source: str = "Standard Library"
    # Optional thermal properties (only needed by thermal studies).
    thermal_conductivity: float = None   # W/(m.K) — K>0 required for thermal
    specific_heat: float = None          # J/(kg.K)  — cp>=0
    thermal_expansion: float = None      # 1/K       — alpha (CTE), optional

    def __post_init__(self):
        if self.young_modulus <= 0:
            raise ValueError("Young's modulus must be positive")
        if not (-1.0 < self.poisson_ratio < 0.5):
            raise ValueError("Poisson ratio must be between -1.0 and 0.5")
        if self.density <= 0:
            raise ValueError("Density must be positive")
        if self.yield_strength <= 0:
            raise ValueError("Yield strength must be positive")
        if self.thermal_conductivity is not None and self.thermal_conductivity <= 0:
            raise ValueError("Thermal conductivity must be positive")
        if self.specific_heat is not None and self.specific_heat < 0:
            raise ValueError("Specific heat cannot be negative")
        if self.thermal_expansion is not None and self.thermal_expansion <= 0:
            raise ValueError("Thermal expansion coefficient must be positive")

    @property
    def has_thermal_properties(self) -> bool:
        """True when the data needed for a steady-state thermal analysis is set."""
        return self.thermal_conductivity is not None and self.thermal_conductivity > 0

    def with_thermal_properties(
        self,
        thermal_conductivity: float,
        specific_heat: float = None,
        thermal_expansion: float = None,
        source: str = None,
    ) -> "Material":
        """Return a copy of this material with thermal properties attached.

        Helpful to promote a mechanical material to a thermal-capable one for a
        thermal study without mutating the shared preset instances.
        """
        return Material(
            name=self.name,
            young_modulus=self.young_modulus,
            poisson_ratio=self.poisson_ratio,
            density=self.density,
            yield_strength=self.yield_strength,
            source=source or self.source,
            thermal_conductivity=thermal_conductivity,
            specific_heat=self.specific_heat if specific_heat is None else specific_heat,
            thermal_expansion=self.thermal_expansion if thermal_expansion is None else thermal_expansion,
        )

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "name": self.name,
            "young_modulus": float(self.young_modulus),
            "poisson_ratio": float(self.poisson_ratio),
            "density": float(self.density),
            "yield_strength": float(self.yield_strength),
            "source": self.source,
        }
        if self.thermal_conductivity is not None:
            d["thermal_conductivity"] = float(self.thermal_conductivity)
        if self.specific_heat is not None:
            d["specific_heat"] = float(self.specific_heat)
        if self.thermal_expansion is not None:
            d["thermal_expansion"] = float(self.thermal_expansion)
        return d


# Standard Material Presets
STANDARD_MATERIALS: Dict[str, Material] = {
    "steel": Material(
        name="Structural Steel",
        young_modulus=210e9,
        poisson_ratio=0.30,
        density=7850.0,
        yield_strength=250e6,
        source="ISO / ASTM Standard",
    ),
    "aluminum": Material(
        name="Aluminum 6061-T6",
        young_modulus=68.9e9,
        poisson_ratio=0.33,
        density=2700.0,
        yield_strength=276e6,
        source="ISO / ASTM Standard",
    ),
    "titanium": Material(
        name="Titanium Ti-6Al-4V",
        young_modulus=113.8e9,
        poisson_ratio=0.34,
        density=4430.0,
        yield_strength=880e6,
        source="ISO / ASTM Standard",
    ),
}
