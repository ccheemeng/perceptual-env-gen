from shapely import Point, Polygon

from math import cos, sin
from typing import Self

class Sample:
    def __init__(self, id: str, point: Point, cluster: int) -> None:
        self.id: str = id
        self.point: Point = point
        self.cluster: int = cluster

    def __repr__(self) -> str:
        return (
            f"{self.id}: cluster {self.cluster} @ {self.point.__repr__()}"
        )
    
    def translate(self, translation: tuple[float, float]) -> Self:
        return Sample(self.id, Point(self.point.x + translation[0], self.point.y + translation[1]), self.cluster)

    def rotate(self, origin: tuple[float, float], rotation: float) -> Self:
        dx: float = origin[0] - self.point.x
        dy: float = origin[1] - self.point.y
        x0: float = self.point.x - dx
        y0: float = self.point.y - dy
        xRot: float = x0 * cos(rotation) - y0 * sin(rotation)
        yRot: float = x0 * sin(rotation) + y0 * cos(rotation)
        xNew: float = xRot + dx
        yNew: float = yRot + dy
        return Sample(self.id, Point(xNew, yNew), self.cluster)

    def getId(self) -> str:
        return self.id

    def getPoint(self) -> Point:
        return self.point

    def getCluster(self) -> int:
        return self.cluster
    
    def within(self, polygon: Polygon) -> bool:
        return self.point.within(polygon)