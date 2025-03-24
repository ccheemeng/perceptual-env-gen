from numpy import float64, ndarray, atan2
from scipy.linalg import svd # type: ignore[import-untyped]
from scipy.stats import wasserstein_distance_nd # type: ignore[import-untyped]
from shapely import MultiPoint, Point, Polygon

from .Geometric import Geometric
from .Sample import Sample
from math import cos, sin, pi as PI
from typing import Collection, Self

class Perception:
    def __init__(self, id: str, point: Point, region: Polygon, samples: Collection[Sample]) -> None:
        samplesClip: tuple[Sample, ...] = tuple(filter(lambda s: s.getPoint().within(region), samples))
        sampleMap: dict[int, tuple[Sample, ...]] = Perception.mapSamples(samples)
        self.id: str = id
        self.point: Point = point
        self.cluster: int = Perception.findCluster(point, samplesClip)
        self.region: Polygon = region
        self.samples: tuple[Sample, ...] = tuple(samplesClip)
        self.sampleMap: dict[int, tuple[Sample, ...]] = sampleMap
        # dict[cluster, tuple[tuple[singularValue, rightSingularVector], ...]]
        self.svd: dict[int, tuple[tuple[float64, ndarray], ...]] = Perception.initSvd(point, sampleMap)

    def __repr__(self) -> str:
        return f"Perception: {len(self.samples)} in {self.region.__repr__()}"
    
    @staticmethod
    def mapSamples(samples: Collection[Sample]) -> dict[int, tuple[Sample, ...]]:
        sampleMap: dict[int, set[Sample]] = dict()
        sample: Sample
        for sample in samples:
            if not sample.getCluster() in sampleMap:
                sampleMap[sample.getCluster()] = set()
            sampleMap[sample.getCluster()].add(sample)
        return {cluster: tuple(sampleSet) for cluster, sampleSet in sampleMap.items()}
    
    @staticmethod
    def findCluster(point: Point, samples: Collection[Sample]) -> int:
        sampleDistances: list[tuple[float, Sample]] = [(point.distance(sample.getPoint()), sample) for sample in samples]
        sampleDistances.sort()
        return sampleDistances[0][1].getCluster()
    
    @staticmethod
    def initSvd(origin: Point, sampleMap: dict[int, tuple[Sample, ...]]) -> dict[int, tuple[tuple[float64, ndarray], ...]]:
        clusterSvd: dict[int, tuple[tuple[float64, ndarray], ...]] = dict()
        cluster: int
        samples: tuple[Sample, ...]
        for cluster, samples in sampleMap.items():
            points: list[Point] = [sample.getPoint() for sample in samples]
            a: list[tuple[float, float]] = [(point.x - origin.x, point.y - origin.y) for point in points]
            U: ndarray
            s: ndarray
            Vh: ndarray
            U, s, Vh = svd(a)
            sVh: list[tuple[float64, ndarray]] = list(zip(s, Vh))
            sVh.sort(reverse=True)
            clusterSvd[cluster] = tuple(sVh)
        return clusterSvd
    
    @staticmethod
    def rotation(p1: Self, p2: Self) -> float: # type: ignore[misc]
        p1SampleCounts: dict[int, int] = p1.sampleCounts()
        p2SampleCounts: dict[int, int] = p2.sampleCounts()
        clusterIntersection: set[int] = set(p1SampleCounts.keys()).intersection(set(p2SampleCounts.keys()))
        if len(clusterIntersection) <= 0:
            return 0
        cluster: int
        if p1.cluster in clusterIntersection:
            cluster = p1.cluster
        else:
            maxCount: int = 0
            currCluster: int
            for currCluster in clusterIntersection:
                count: int = min(p1SampleCounts[currCluster], p2SampleCounts[currCluster])
                if count > maxCount:
                    maxCount = count
                    cluster = currCluster
        p1Vector: ndarray = p1.svd[cluster][0][1]
        p2Vector: ndarray = p2.svd[cluster][0][1]
        angle: float = atan2(p1Vector[1], p1Vector[0]) - atan2(p2Vector[1], p2Vector[0])
        if PI < angle <= 1.5 * PI:
            angle = angle - PI
        elif 1.5 * PI < angle:
            angle = angle - 2 * PI
        p1ShapelyPoints: list[Point] = [sample.getPoint() for sample in p1.sampleMap[cluster]]
        p1Points: list[tuple[float, float]] = [(point.x - p1.point.x, point.y - p1.point.y) for point in p1ShapelyPoints]
        p2ShapelyPoints: list[Point] = [sample.getPoint() for sample in p2.sampleMap[cluster]]
        p2Points: list[tuple[float, float]] = [(point.x - p2.point.x, point.y - p2.point.y) for point in p2ShapelyPoints]
        p2PointsRot1 = [Geometric.rotate(point, (0, 0), angle) for point in p2Points]
        p2PointsRot2 = [Geometric.rotate(point, (0, 0), angle + PI) for point in p2Points]
        distance1: float = wasserstein_distance_nd(p1Points, p2PointsRot1)
        distance2: float = wasserstein_distance_nd(p1Points, p2PointsRot2)
        if distance1 <= distance2:
            return angle
        else:
            return angle + PI
    
    @staticmethod
    def distance(p1: Self, p2: Self, rotation: float) -> float: # type: ignore[misc]
        totalDistance: float = 0
        clusters: set[int] = set(p1.sampleMap.keys()).union(set(p2.sampleMap.keys()))
        cluster: int
        for cluster in clusters:
            p1Points: list[tuple[float, float]]
            p2Points: list[tuple[float, float]]
            if not (cluster in p1.sampleMap and cluster in p2.sampleMap):
                hasCluster: Perception
                if not cluster in p1.sampleMap:
                    hasCluster = p2
                else:
                    hasCluster = p1
                shapelyPoints: list[Point] = [sample.getPoint() for sample in hasCluster.sampleMap[cluster]]
                points: list[tuple[float, float]] = [(point.x - hasCluster.point.x, point.y - hasCluster.point.y) for point in shapelyPoints]
                shapelyCentroid: Point = MultiPoint(shapelyPoints).centroid
                centroid: tuple[float, float] = (shapelyCentroid.x - hasCluster.point.x, shapelyCentroid.y - hasCluster.point.y)
                dummyPoints: list[tuple[float, float]] = [centroid for i in range(len(points))]
                p1Points = points
                p2Points = dummyPoints
            else:
                p1ShapelyPoints: list[Point] = [sample.getPoint() for sample in p1.sampleMap[cluster]]
                p1Points = [(point.x - p1.point.x, point.y - p1.point.y) for point in p1ShapelyPoints]
                p2ShapelyPoints: list[Point] = [sample.getPoint() for sample in p2.sampleMap[cluster]]
                p2Points = [(point.x - p2.point.x, point.y - p2.point.y) for point in p2ShapelyPoints]
                if len(p1Points) < len(p2Points):
                    p2ShapelyCentroid: Point = MultiPoint(p2ShapelyPoints).centroid
                    p2Centroid: tuple[float, float] = (p2ShapelyCentroid.x - p2.point.x, p2ShapelyCentroid.y - p2.point.y)
                    p1Points.extend([p2Centroid for i in range(len(p2Points) - len(p1Points))])
                else:
                    p1ShapelyCentroid: Point = MultiPoint(p1ShapelyPoints).centroid
                    p1Centroid: tuple[float, float] = (p1ShapelyCentroid.x - p1.point.x, p1ShapelyCentroid.y - p1.point.y)
                    p2Points.extend([p1Centroid for i in range(len(p1Points) - len(p2Points))])
            p2Points = [Geometric.rotate(point, (0, 0), rotation) for point in p2Points] # type: ignore[misc]
            distance: float = wasserstein_distance_nd(p1Points, p2Points)
            totalDistance += distance
        return totalDistance
    
    def rotationTo(self, other: Self) -> float:
        return Perception.rotation(self, other)
    
    def distanceTo(self, other: Self, rotation: float) -> float:
        return Perception.distance(self, other, rotation)
    
    def samplesInPolygon(self, polygon: Polygon) -> list[Sample]:
        samplesWithin: list[Sample] = list()
        sample: Sample
        for sample in self.samples:
            if sample.within(polygon):
                samplesWithin.append(sample)
        return samplesWithin
    
    def getId(self) -> str:
        return self.id
    
    def getPoint(self) -> Point:
        return self.point
    
    def getCluster(self) -> int:
        return self.cluster
    
    def getRegion(self) -> Polygon:
        return self.region
    
    def getSamples(self) -> tuple[Sample, ...]:
        return self.samples

    def sampleCounts(self) -> dict[int, int]:
        return {cluster: len(samples) for cluster, samples in self.sampleMap.items()}