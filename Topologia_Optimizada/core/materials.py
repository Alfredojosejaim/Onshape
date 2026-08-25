"""Core material definitions and physical property models."""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class Material:
    """Linear isotropic material properties."""
    name: str
    young_modulus: float  # Pa (or N/mm^2 depending on units)
    poisson_ratio: float
    density: float        # kg/m^3
    yield_strength: float # Pa
    source: str = "Standard Library"

    def __post_init__(self):
        if self.young_modulus <= 0:
            raise ValueError("Young's modulus must be positive")
        if not (-1.0 < self.poisson_ratio < 0.5):
            raise ValueError("Poisson ratio must be between -1.0 and 0.5")
        if self.density <= 0:
            raise ValueError("Density must be positive")
        if self.yield_strength <= 0:
            raise ValueError("Yield strength must be positive")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "young_modulus": float(self.young_modulus),
            "poisson_ratio": float(self.poisson_ratio),
            "density": float(self.density),
            "yield_strength": float(self.yield_strength),
            "source": self.source,
        }


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
