from geopandas import GeoDataFrame # type: ignore[import-untyped]
from shapely import MultiPolygon, Point, Polygon, union_all
from tqdm import tqdm

from .Geometric import Geometric
from .Perception import Perception
from .Sample import Sample

from typing import Collection as CollectionType, Self, Sequence

class Collection:
    PERCEPTION_RADIUS: float = 100

    def __init__(self, perceptions: CollectionType[Perception], perception_radius: float = PERCEPTION_RADIUS) -> None:
        self.perceptions: tuple[Perception, ...] = tuple(perceptions)
        self.perception_radius = perception_radius

    def __repr__(self) -> str:
        return f"Collection: {len(self.perceptions)}"

    @classmethod
    def fromIdsPointsRegionsSamples(cls, ids: Sequence[str], points: Sequence[Point], regions: Sequence[Polygon], samples: CollectionType[Sample]) -> Self:
        print("Initialising collection...")
        if len(ids) != len(points) or len(ids) != len(regions):
            raise ValueError("Number of ids, points, and regions must match!")
        samplesList: list[Sample] = list(samples)
        samplesGdf: GeoDataFrame = GeoDataFrame(data={"sample": samplesList}, geometry=[sample.getPoint() for sample in samplesList])
        samplesGdf.sindex
        perceptions: list[Perception] = list()
        i: int
        for i in range(len(ids)):
            region: Polygon = regions[i]
            samplesInRegion: list[Sample] = samplesGdf.iloc[samplesGdf.sindex.query(region, predicate="intersects")]["sample"].to_list()
            perceptions.append(Perception(ids[i], points[i], regions[i], samplesInRegion))
        return cls(perceptions)
    
    @staticmethod
    def calculateDistance(p1: Perception, p2: Perception) -> tuple[float, float]:
        rotation: float = p1.rotationTo(p2)
        distance: float = p1.distanceTo(p2, rotation)
        return (rotation, distance)
    
    def findSimilar(self, query: Perception) -> tuple[float, Perception, float]:
        print(f"Querying {self.__repr__()} with {query}")
        similar: tuple[float, Perception, float] = self.findSimilarFast(query)[0]
        return similar

    def findSimilarFast(self, query: Perception) -> tuple[tuple[float, Perception, float], ...]:
        perceptionDistances: list[tuple[float, Perception, float]] = list()
        perception: Perception
        for perception in tqdm(self.perceptions):
            if query.getCluster() != perception.getCluster():
                continue
            rotation: float
            distance: float
            rotation, distance = Collection.calculateDistance(perception, query)
            perceptionDistances.append((distance, perception, rotation))
        if len(perceptionDistances) <= 0:
            return self.findSimilarAll(query)
        perceptionDistances.sort(key=lambda x: x[0])
        return tuple(perceptionDistances)

    def findSimilarAll(self, query: Perception) -> tuple[tuple[float, Perception, float], ...]:
        perceptionDistances: list[tuple[float, Perception, float]] = list()
        perception: Perception
        for perception in tqdm(self.perceptions):
            rotation: float
            distance: float
            rotation, distance = Collection.calculateDistance(perception, query)
            perceptionDistances.append((distance, perception, rotation))
        perceptionDistances.sort(key=lambda x: x[0])
        return tuple(perceptionDistances)

    def filter(self, sitePolygons: list[Polygon]) -> Self:
        sitePerceptionZones: list[Polygon] = Geometric.geometryToPolygons(union_all([sitePolygon.buffer(self.perception_radius) for sitePolygon in sitePolygons]))
        sitePerceptionZone: MultiPolygon = MultiPolygon(sitePerceptionZones)
        newPerceptions: list[Perception] = list()
        perception: Perception
        for perception in self.perceptions:
            if perception.getPoint().within(sitePerceptionZone):
                newPerceptions.append(perception)
        sampleSet: set[Sample] = set()
        for perception in newPerceptions:
            sampleSet.update(perception.getSamples())
        return Collection.fromIdsPointsRegionsSamples(
            [perception.getId() for perception in newPerceptions],
            [perception.getPoint() for perception in newPerceptions],
            [perception.getRegion() for perception in newPerceptions],
            sampleSet
        ) # type: ignore[return-value]
        
    
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
        perceptionDistances.sort(key=lambda x: x[0])
        return perceptionDistances[0][1]
    
    def getPerceptions(self) -> list[Perception]:
        return list(self.perceptions)