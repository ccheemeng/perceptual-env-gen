from numpy import float64, ndarray, atan2
from scipy.linalg import svd # type: ignore
from scipy.stats import wasserstein_distance_nd # type: ignore
from shapely import MultiPoint, Point, Polygon

from .Sample import Sample

from collections.abc import Collection
from math import pi as PI, cos, sin
from random import Random
from typing import Self
from queue import PriorityQueue

class Perception:
    def __init__(self, sample: Sample, radius: float,
                 samples: Collection[Sample],
                 random: Random = Random(0)) -> None:
        self.id: str = sample.getId()
        self.sample: Sample = sample
        self.radius: float = radius
        self.samples: list[Sample] = list(samples)
        sampleMap: dict[int, tuple[Sample, ...]] = Perception.mapSamples(samples)
        self.sampleMap: dict[int, tuple[Sample, ...]] = sampleMap
        # dict[cluster, tuple[tuple[singlularValue, rightSingularVector], ...]]
        self.svd: dict[int, tuple[tuple[float64, ndarray], ...]] =\
            Perception.initSvd(sample, sampleMap, random)

    def __repr__(self) -> str:
        return (
            f"{self.sample.__repr__()}: "
            f"r={self.radius}, {len(self.samples)} samples"
        )
    
    @staticmethod
    def mapSamples(samples: Collection[Sample]) ->\
        dict[int, tuple[Sample, ...]]:
        sampleMap: dict[int, list[Sample]] = dict()
        sample: Sample
        for sample in samples:
            if not sample.getCluster() in sampleMap:
                sampleMap[sample.getCluster()] = []
            sampleMap[sample.getCluster()].append(sample)
        sampleImMap: dict[int, tuple[Sample, ...]] = dict()
        cluster: int
        for cluster in sampleMap:
            sampleImMap[cluster] = tuple(sampleMap[cluster])
        return sampleImMap

    @staticmethod
    def initSvd(sample: Sample, sampleMap: dict[int, tuple[Sample, ...]],
                random: Random = Random(0)) -> dict[int, tuple[tuple[float64, ndarray], ...]]:
        clusterSvd: dict[int, tuple[tuple[float64, ndarray], ...]] = dict()
        cluster: int
        samples: tuple[Sample, ...]
        for cluster, samples in sampleMap.items():
            points: list[Point] = [sample.getPoint() for sample in samples]
            origin: Point = sample.getPoint()
            a: list[tuple[float, float]] = [(point.x - origin.x, point.y - origin.y) for point in points]
            U: ndarray
            s: ndarray
            Vh: ndarray
            U, s, Vh = svd(a)
            sVh: list[tuple[float64, ndarray]] = list(zip(s, Vh))
            sVh.sort(reverse=True)
            clusterSvd[cluster] = tuple(sVh)
        return clusterSvd
    
    # asymmetric
    @staticmethod
    def distance(p1: Self, p2: Self, rotation: float) -> float: # type: ignore[misc]
        totalDistance: float = 0
        clusters: set[int] = set(p1.sampleMap.keys()).union(set(p2.sampleMap.keys()))
        for cluster in clusters:
            clusterRotation: float = rotation
            p1Points: list[tuple[float, float]]
            p2Points: list[tuple[float, float]]
            if not (cluster in p1.sampleMap and cluster in p2.sampleMap):
                hasCluster: Perception
                if not cluster in p1.sampleMap:
                    hasCluster = p2
                else:
                    hasCluster = p1
                centre: Point = hasCluster.sample.getPoint()
                shapelyPoints: list[Point] = [sample.getPoint() for sample in hasCluster.sampleMap[cluster]]
                points: list[tuple[float, float]] = [(point.x - centre.x, point.y - centre.y) for point in shapelyPoints]
                shapelyCentroid: Point = MultiPoint(shapelyPoints).centroid
                centroid: tuple[float, float] = (shapelyCentroid.x - centre.x, shapelyCentroid.y - centre.y)
                dummyPoints: list[tuple[float, float]] = [centroid for i in range(len(points))]
                p1Points = points
                p2Points = dummyPoints
                clusterRotation = 0.0
            else:
                p1Point: Point = p1.sample.getPoint()
                p1ShapelyPoints: list[Point] = [sample.getPoint() for sample in p1.sampleMap[cluster]]
                p1Points = [(point.x - p1Point.x, point.y - p1Point.y) for point in p1ShapelyPoints]
                p2Point: Point = p2.sample.getPoint()
                p2ShapelyPoints: list[Point] = [sample.getPoint() for sample in p2.sampleMap[cluster]]
                p2Points = [(point.x - p2Point.x, point.y - p2Point.y) for point in p2ShapelyPoints]
                if len(p1Points) < len(p2Points):
                    p2ShapelyCentroid: Point = MultiPoint(p2ShapelyPoints).centroid
                    p2Centroid: tuple[float, float] = (p2ShapelyCentroid.x - p2Point.x, p2ShapelyCentroid.y - p2Point.y)
                    p1Points.extend([p2Centroid for i in range(len(p2Points) - len(p1Points))])
                else:
                    p1ShapelyCentroid: Point = MultiPoint(p1ShapelyPoints).centroid
                    p1Centroid: tuple[float, float] = (p1ShapelyCentroid.x - p1Point.x, p1ShapelyCentroid.y - p1Point.y)
                    p2Points.extend([p1Centroid for i in range(len(p1Points) - len(p2Points))])
            p2Points = [Perception.rotate(point, clusterRotation) for point in p2Points]
            distance: float = wasserstein_distance_nd(p1Points, p2Points)
            totalDistance += distance
        return totalDistance

    # returns angle p2 must rotate about its sample centre counterclockwise
    @staticmethod
    def rotation(p1: Self, p2: Self) -> float: # type: ignore[misc]
        p1SampleCounts: dict[int, int] = p1.sampleCounts()
        p2SampleCounts: dict[int, int] = p2.sampleCounts()
        clusterIntersection: set[int] = set(p1SampleCounts.keys())\
            .intersection(set(p2SampleCounts.keys()))
        
        if len(clusterIntersection) <= 0:
            return 0.0

        cluster: int
        if p1.sample.getCluster() in clusterIntersection:
            cluster = p1.sample.getCluster()
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
        p1Point: Point = p1.sample.getPoint()
        p1ShapelyPoints: list[Point] = [sample.getPoint() for sample in p1.sampleMap[cluster]]
        p1Points: list[tuple[float, float]] = [(point.x - p1Point.x, point.y - p1Point.y) for point in p1ShapelyPoints]
        p2Point: Point = p2.sample.getPoint()
        p2ShapelyPoints: list[Point] = [sample.getPoint() for sample in p2.sampleMap[cluster]]
        p2Points: list[tuple[float, float]] = [(point.x - p2Point.x, point.y - p2Point.y) for point in p2ShapelyPoints]
        p2Points = [Perception.rotate(point, angle) for point in p2Points]
        p2PointsRotated = [Perception.rotate(point, PI) for point in p2Points]
        distance: float = wasserstein_distance_nd(p1Points, p2Points)
        distanceRotated: float = wasserstein_distance_nd(p1Points, p2PointsRotated)
        if distance <= distanceRotated:
            return angle
        else:
            return angle + PI

    # counterclockwise rotation of 2d point about origin
    @staticmethod
    def rotate(point: tuple[float, float], theta: float) -> tuple[float, float]:
        x: float = point[0]
        y: float = point[1]
        return (x * cos(theta) - y * sin(theta), x * sin(theta) + y * cos(theta))

    def getSamples(self) -> list[Sample]:
        return self.samples
    
    def within(self, polygon: Polygon) -> bool:
        return self.sample.within(polygon)

    def distanceTo(self, other: Self, rotation: float) -> float:
        return Perception.distance(self, other, rotation)

    def rotationTo(self, other: Self) -> float:
        return Perception.rotation(self, other)

    def sampleCounts(self) -> dict[int, int]:
        sampleCounts: dict[int, int] = dict()
        cluster: int
        samples: tuple[Sample, ...]
        for cluster, samples in self.sampleMap.items():
            sampleCounts[cluster] = len(samples)
        return sampleCounts