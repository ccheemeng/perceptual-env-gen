from typing import Self

class Attributes:
    def __init__(self, height: float, residentialGfa: float, commercialGfa: float, civicGfa: float, otherGfa: float, footprintArea: float, siteArea: float) -> None:
        self.height: float = height
        self.residentialGfa: float = residentialGfa
        self.commercialGfa: float = commercialGfa
        self.civicGfa: float = civicGfa
        self.otherGfa: float = otherGfa
        self.footprintArea: float = footprintArea
        self.siteArea: float = siteArea

    @classmethod
    def of(cls) -> Self:
        return cls(0, 0, 0, 0, 0, 0, 0)

    @classmethod
    def withMaxHeight(cls, attributes: Self) -> Self:
        return cls(attributes.height, 0, 0, 0, 0, 0, 0)
    
    def accummulate(self, other: Self) -> Self:
        return Attributes(
            max(self.height, other.height),
            self.residentialGfa + other.residentialGfa,
            self.commercialGfa + other.commercialGfa,
            self.civicGfa + other.civicGfa,
            self.otherGfa + other.otherGfa,
            self.footprintArea + other.footprintArea,
            self.siteArea + other.siteArea
        )
    
    def subtract(self, other: Self) -> Self:
        return Attributes(
            self.height,
            max(self.residentialGfa - other.residentialGfa, 0),
            max(self.commercialGfa - other.commercialGfa, 0),
            max(self.civicGfa - other.civicGfa, 0),
            max(self.footprintArea - other.footprintArea, 0),
            max(self.siteArea - other.siteArea, 0),
        )
    
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
        )
    
    def distanceTo(self, other: Self) -> float:
        