import shapely

from .Geometric import Geometric

from typing import Self, Union

class Sample:
    def __init__(self, point: shapely.Point, cluster: int) -> None:
        self.point: shapely.Point = point
        self.cluster: int = cluster

    def __repr__(self) -> str:
        return (f"Cluster {self.cluster} @ {self.point.__repr__()}")
    
    def __eq__(self, other: object) -> bool:
        if isinstance(other, Sample):
            return (
                self.point.equals(other.point)
                and self.cluster == other.cluster)
        return False
    
    def __hash__(self):
        return hash(self.__repr__())
    
    def translate(self,
        originOrVector: object,
        destination: object = None
    ) -> Self:
        newPoint: object = Geometric.translate(
            self.point,
            originOrVector,
            destination
        )
        assert isinstance(newPoint, shapely.Point)
        return Sample(newPoint, self.cluster) # type: ignore[return-value]
    
    def rotate(self, origin: object, rotation: float) -> Self:
        newPoint: object = Geometric.rotate(self.point, origin, rotation)
        assert isinstance(newPoint, shapely.Point)
        return Sample(newPoint, self.cluster) # type: ignore[return-value]
    
    def within(self, 
        polygon: Union[shapely.Polygon, shapely.MultiPolygon]
    ) -> bool:
        return self.point.within(polygon)

    def getPoint(self) -> shapely.Point:
        return self.point

    def getCluster(self) -> int:
        return self.cluster