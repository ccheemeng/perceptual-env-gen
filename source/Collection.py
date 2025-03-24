from shapely import Point, Polygon

from .Perception import Perception
from .Sample import Sample

from time import time
from typing import Collection as CollectionType, Self, Sequence

class Collection:
    def __init__(self, perceptions: CollectionType[Perception]) -> None:
        self.perceptions: tuple[Perception, ...] = tuple(perceptions)

    def __repr__(self) -> str:
        return f"Collection: {len(self.perceptions)}"

    @classmethod
    def fromIdsPointsRegionsSamples(cls, ids: Sequence[str], points: Sequence[Point], regions: Sequence[Polygon], samples: CollectionType[Sample]) -> Self:
        if len(ids) != len(points) or len(ids) != len(regions):
            raise ValueError("Number of ids, points, and regions must match!")
        perceptions: list[Perception] = list()
        i: int
        for i in range(len(ids)):
            perceptions.append(Perception(ids[i], points[i], regions[i], samples))
        return cls(perceptions)
    
    @staticmethod
    def calculateDistance(p1: Perception, p2: Perception) -> tuple[float, float]:
        rotation: float = p1.rotationTo(p2)
        distance: float = p1.distanceTo(p2, rotation)
        return (rotation, distance)
    
    def findSimilar(self, query: Perception) -> tuple[float, Perception, float]:
        return self.findSimilarAll(query)[0]

    def findSimilarAll(self, query: Perception) -> tuple[tuple[float, Perception, float], ...]:
        print(f"Querying {self.__repr__()} with {query}")
        start = time()
        perceptionDistances: list[tuple[float, Perception, float]] = list()
        perception: Perception
        for perception in self.perceptions:
            rotation: float
            distance: float
            rotation, distance = Collection.calculateDistance(perception, query)
            perceptionDistances.append((distance, perception, rotation))
        perceptionDistances.sort()
        end = time()
        print(f"Query took {end - start} s")
        return tuple(perceptionDistances)
    
    def update(self, newIds: Sequence[str], newPoints: Sequence[Point], newRegions: Sequence[Polygon], newSamples: CollectionType[Sample]) -> Self:
        ids: list[str] = [perception.getId() for perception in self.perceptions]
        points: list[Point] = [perception.getPoint() for perception in self.perceptions]
        regions: list[Polygon] = [perception.getRegion() for perception in self.perceptions]
        samples: set[Sample] = set(self.getSamples())
        ids.extend(newIds)
        points.extend(newPoints)
        regions.extend(newRegions)
        samples.update(newSamples)
        return Collection.fromIdsPointsRegionsSamples(ids, points, regions, samples) # type: ignore[return-value]
    
    def getSamples(self) -> list[Sample]:
        sampleSet: set[Sample] = set()
        perception: Perception
        for perception in self.perceptions:
            sampleSet.update(perception.getSamples())
        return list(sampleSet)
    
    def samplesInPolygon(self, polygon: Polygon) -> list[Sample]:
        sampleSet: set[Sample] = set()
        perception: Perception
        for perception in self.perceptions:
            sampleSet.update(perception.samplesInPolygon(polygon))
        return list(sampleSet)
    
    def perceptionFromSample(self, sample: Sample) -> Perception:
        matchingPerceptions: list[Perception] = list(filter((lambda p: Sample(p.getPoint(), p.getCluster()) == sample), self.perceptions))
        if len(matchingPerceptions) <= 0:
            raise IndexError(f"No perception in {self.__repr__()} found from {sample.__repr__()}!")
        perceptionDistances: list[tuple[float, Perception]] = [(perception.getPoint().distance(sample.getPoint()), perception) for perception in matchingPerceptions]
        perceptionDistances.sort()
        return perceptionDistances[0][1]
    
    def getPerceptions(self) -> list[Perception]:
        return list(self.perceptions)