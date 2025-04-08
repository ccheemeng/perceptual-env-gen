from typing import Self

class Attributes:
    HEIGHT_WEIGHT: float = 0.05
    RESIDENTIAL_WEIGHT: float = 0.05
    COMMERCIAL_WEIGHT: float = 0.05
    CIVIC_WEIGHT: float = 0.05
    OTHER_WEIGHT: float = 0.05
    FOOTPRINT_WEIGHT: float = 0.75

    def __init__(self, height: float, residentialGfa: float, commercialGfa: float, civicGfa: float, otherGfa: float, footprintArea: float, siteArea: float) -> None:
        self.height: float = height
        self.residentialGfa: float = residentialGfa
        self.commercialGfa: float = commercialGfa
        self.civicGfa: float = civicGfa
        self.otherGfa: float = otherGfa
        self.footprintArea: float = footprintArea
        self.siteArea: float = siteArea

    def __repr__(self) -> str:
        return (
            "Attributes:\n"
            f"Max height     : {self.height}\n"
            f"Residential GFA: {self.residentialGfa}\n"
            f"Commercial GFA : {self.commercialGfa}\n"
            f"Civic GFA      : {self.civicGfa}\n"
            f"Other GFA      : {self.otherGfa}\n"
            f"Footprint area : {self.footprintArea}\n"
            f"Site area      : {self.siteArea}"
        )

    @classmethod
    def of(cls) -> Self:
        return cls(0, 0, 0, 0, 0, 0, 0)

    @classmethod
    def withMaxHeight(cls, attributes: Self) -> Self:
        return cls(attributes.height, 0, 0, 0, 0, 0, 0)

    @staticmethod
    def csvHeader() -> tuple[str, ...]:
        return (
            "maxHeight",
            "totalGFA",
            "residentialGFA",
            "commercialGFA",
            "civicGFA",
            "otherGFA",
            "siteCoverage",
            "footprintArea",
            "siteArea"
        )
    
    def accumulate(self, other: Self) -> Self:
        return Attributes(
            max(self.height, other.height),
            self.residentialGfa + other.residentialGfa,
            self.commercialGfa + other.commercialGfa,
            self.civicGfa + other.civicGfa,
            self.otherGfa + other.otherGfa,
            self.footprintArea + other.footprintArea,
            self.siteArea + other.siteArea
        ) # type: ignore[return-value]
    
    def subtract(self, other: Self) -> Self:
        return Attributes(
            self.height,
            max(self.residentialGfa - other.residentialGfa, 0),
            max(self.commercialGfa - other.commercialGfa, 0),
            max(self.civicGfa - other.civicGfa, 0),
            max(self.otherGfa - other.otherGfa, 0),
            max(self.footprintArea - other.footprintArea, 0),
            max(self.siteArea - other.siteArea, 0),
        ) # type: ignore[return-value]
    
    def ratio(self, ratio: float) -> Self:
        if ratio < 0:
            ratio = 0
        return Attributes(
            self.height,
            self.residentialGfa * ratio,
            self.commercialGfa * ratio,
            self.civicGfa * ratio,
            self.otherGfa * ratio,
            self.footprintArea * ratio,
            self.siteArea * ratio
        ) # type: ignore[return-value]
    
    def distanceTo(self, other: Self) -> float:
        return sum([
            self.HEIGHT_WEIGHT * max(other.height - self.height, 0),
            self.RESIDENTIAL_WEIGHT * abs(other.residentialGfa - self.residentialGfa),
            self.COMMERCIAL_WEIGHT * abs(other.commercialGfa - self.commercialGfa),
            self.CIVIC_WEIGHT * abs(other.civicGfa - self.civicGfa),
            self.OTHER_WEIGHT * abs(other.otherGfa - self.otherGfa),
            self.FOOTPRINT_WEIGHT * abs(other.footprintArea - self.footprintArea)
        ])

    def toCsvRow(self) -> tuple:
        return (
            self.height,
            sum((self.residentialGfa, self.commercialGfa, self.civicGfa, self.otherGfa)),
            self.residentialGfa,
            self.commercialGfa,
            self.civicGfa,
            self.otherGfa,
            self.footprintArea / self.siteArea if self.siteArea > 0 else 0,
            self.footprintArea,
            self.siteArea
        )