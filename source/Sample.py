from shapely import Point, Polygon

class Sample:
    def __init__(self, id: str, point: Point,
                 radius: float, cluster: int) -> None:
        self.id: str = id
        self.point: Point = point
        self.radius: float = radius
        self.cluster: int = cluster

    def __repr__(self) -> str:
        return (
            f"{self.id}: cluster {self.cluster} "
            f"@ {self.point.__repr__()} of r={self.radius}"
        )
    
    def getId(self) -> str:
        return self.id

    def getCluster(self) -> int:
        return self.cluster
    
    def within(self, polygon: Polygon) -> bool:
        return self.point.within(polygon)