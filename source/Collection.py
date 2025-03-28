from geopandas import GeoDataFrame # type: ignore[import-untyped]
from shapely import MultiPolygon, Point, Polygon, union_all
from tqdm import tqdm

from .Attributes import Attributes
from .Buildings import Buildings
from .Geometric import Geometric
from .Perception import Perception
from .Sample import Sample

from typing import Collection as CollectionType, Self, Sequence

class Collection:
    PERCEPTION_RADIUS: float = 100
    NUM_CONSIDERED_PERCEPTIONS: int = 20

    def __init__(self, perceptions: CollectionType[Perception]) -> None:
        self.perceptions: tuple[Perception, ...] = tuple(perceptions)

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

    def query(self, query: Perception, queryPolygon: Polygon, queryBuildings: Buildings, target: Attributes) -> tuple[Perception, float, list[Polygon], Attributes]:
        print(f"Querying {self.__repr__()} with {query}")
        perceptionRotations: list[tuple[Perception, float]] = self.findRotations(query)
        destination: tuple[float, float] = (query.getPoint().x, query.getPoint().y)
        perceptionStats: list[tuple[float, Perception, float, list[Polygon], Attributes]] = list()
        attributesDistance: float
        siteRegion: Polygon
        achievable: Attributes
        print("Calculating attributes with found perceptions...")
        perception: Perception
        rotation: float
        for perception, rotation in tqdm(perceptionRotations):
            translation: tuple[float, float] = (destination[0] - perception.getPoint().x, destination[1] - perception.getPoint().y)
            siteRegion = Geometric.rotateAboutTuple(Geometric.translateVectorTuple(perception.getRegion(), translation), destination, rotation).intersection(queryPolygon) # type: ignore[attr-defined]
            siteRegions: list[Polygon] = Geometric.geometryToPolygons(siteRegion)
            siteRegions = list(filter(lambda p: not p.is_empty, siteRegions))
            if len(siteRegions) <= 0:
                achievable = Attributes.withMaxHeight(target)
            else:
                queryRegions: list[Polygon] = [Geometric.translateVectorTuple(Geometric.rotateAboutTuple(region, destination, -rotation), (-translation[0], -translation[1])) for region in siteRegions] # type: ignore[misc]
                achievable = queryBuildings.query(queryRegions)
            attributesDistance = target.distanceTo(achievable)
            perceptionStats.append((attributesDistance, perception, rotation, siteRegions, achievable))
        perceptionStats.sort(key=lambda x: x[0])
        perceptionStats = perceptionStats[:self.NUM_CONSIDERED_PERCEPTIONS]
        perceptionDistances: list[tuple[float, Perception, float, list[Polygon], Attributes]] = list()
        print(f"Calculating distances for up to top {self.NUM_CONSIDERED_PERCEPTIONS} perceptions...")
        for attributesDistance, perception, rotation, siteRegions, achievable in tqdm(perceptionStats):
            distance: float = perception.distanceTo(query, rotation)
            perceptionDistances.append((distance, perception, rotation, siteRegions, achievable))
        perceptionDistances.sort(key=lambda x: x[0])
        return perceptionDistances[0][1:]
    
    def findRotations(self, query: Perception) -> list[tuple[Perception, float]]:
        perceptionRotations: list[tuple[Perception, float]] = list()
        print("Calculating rotations for perceptions in query with same cluster...")
        perception: Perception
        for perception in tqdm(self.perceptions):
            if perception.getCluster() != query.getCluster():
                continue
            rotation: float = perception.rotationTo(query)
            perceptionRotations.append((perception, rotation))
        if len(perceptionRotations) <= 0:
            perceptionRotations = self.findRotationsSlow(query)
        return perceptionRotations
    
    def findRotationsSlow(self, query: Perception) -> list[tuple[Perception, float]]:
        perceptionRotations: list[tuple[Perception, float]] = list()
        print(
            "No perceptions with same cluster found.\n"
            "Calculating rotations for all perceptions in query..."
        )
        perception: Perception
        for perception in tqdm(self.perceptions):
            rotation: float = perception.rotationTo(query)
            perceptionRotations.append((perception, rotation))
        if len(perceptionRotations) <= 0:
            perceptionRotations = self.findRotationsSlow(query)
        return perceptionRotations

    def filter(self, sitePolygons: list[Polygon]) -> Self:
        sitePerceptionZones: list[Polygon] = Geometric.geometryToPolygons(union_all([sitePolygon.buffer(self.PERCEPTION_RADIUS) for sitePolygon in sitePolygons]))
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