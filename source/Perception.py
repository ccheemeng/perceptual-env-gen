from geopandas import GeoDataFrame # type: ignore[import-untyped]
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
        samplesClip: tuple[Sample, ...] = tuple(Perception.clipSamples(samples, region))
        sampleMap: dict[int, tuple[Sample, ...]] = Perception.mapSamples(samples)
        self.id: str = id
        self.point: Point = point
        self.cluster: int = Perception.findCluster(point, samplesClip)
        self.region: Polygon = region
        self.samples: tuple[Sample, ...] = tuple(samplesClip)
        self.sampleMap: dict[int, tuple[Sample, ...]] = sampleMap
        # dict[cluster, tuple[singularValue, rightSingularVector]]
        self.svd: dict[int, tuple[float64, ndarray, float]] = Perception.initSvd(point, sampleMap)

    def __repr__(self) -> str:
        return f"Perception {self.id}: cluster {self.cluster} @ {self.point.__repr__()}"
    
    @staticmethod
    def clipSamples(samples: Collection[Sample], polygon: Polygon) -> list[Sample]:
        samplesList: list[Sample] = list(samples)
        return GeoDataFrame(data={"sample": samplesList}, geometry=[sample.getPoint() for sample in samplesList]).clip(polygon, keep_geom_type=True)["sample"].to_list()

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
        sampleDistances.sort(key=lambda x: x[0])
        return sampleDistances[0][1].getCluster()
    
    @staticmethod
    def initSvd(origin: Point, sampleMap: dict[int, tuple[Sample, ...]]) -> dict[int, tuple[float64, ndarray, float]]:
        clusterSvd: dict[int, tuple[float64, ndarray, float]] = dict()
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
            angle: float = atan2(sVh[0][1][1], sVh[0][1][0])
            clusterSvd[cluster] = (sVh[0][0], sVh[0][1], angle)
        return clusterSvd
    
    def rotationTo(self, other: Self) -> float:
        selfSampleCounts: dict[int, int] = self.sampleCounts()
        otherSampleCounts: dict[int, int] = other.sampleCounts()
        clusterIntersection: set[int] = set(selfSampleCounts.keys()).intersection(set(selfSampleCounts.keys()))
        if len(clusterIntersection) <= 0:
            return 0
        cluster: int
        if self.cluster in clusterIntersection:
            cluster = self.cluster
        else:
            maxCount: int = 0
            currCluster: int
            for currCluster in clusterIntersection:
                count: int = min(selfSampleCounts[currCluster], otherSampleCounts[currCluster])
                if count > maxCount:
                    maxCount = count
                    cluster = currCluster
        selfVector: ndarray = self.svd[cluster][1]
        selfAngle: float = other.svd[cluster][2]
        otherVector: ndarray = self.svd[cluster][1]
        otherAngle: float = other.svd[cluster][2]
        angle: float = selfAngle - otherAngle
        return angle
    
    def distanceRotationTo(self, other: Self) -> tuple[float, float]:
        rotation: float = self.rotationTo(other)
        totalDistance1: float = 0
        totalDistance2: float = 0
        clusters: set[int] = set(self.sampleMap.keys()).union(set(other.sampleMap.keys()))
        cluster: int
        for cluster in clusters:
            selfPoints: list[tuple[float, float]]
            otherPoints: list[tuple[float, float]]
            if not (cluster in self.sampleMap and cluster in other.sampleMap):
                hasCluster: Perception
                if not cluster in self.sampleMap:
                    hasCluster = other
                else:
                    hasCluster = self
                shapelyPoints: list[Point] = [sample.getPoint() for sample in hasCluster.sampleMap[cluster]]
                points: list[tuple[float, float]] = [(point.x - hasCluster.point.x, point.y - hasCluster.point.y) for point in shapelyPoints]
                shapelyCentroid: Point = MultiPoint(shapelyPoints).centroid
                centroid: tuple[float, float] = (shapelyCentroid.x - hasCluster.point.x, shapelyCentroid.y - hasCluster.point.y)
                dummyPoints: list[tuple[float, float]] = [centroid for i in range(len(points))]
                selfPoints = points
                otherPoints = dummyPoints
            else:
                selfShapelyPoints: list[Point] = [sample.getPoint() for sample in self.sampleMap[cluster]]
                selfPoints = [(point.x - self.point.x, point.y - self.point.y) for point in selfShapelyPoints]
                otherShapelyPoints: list[Point] = [sample.getPoint() for sample in other.sampleMap[cluster]]
                otherPoints = [(point.x - other.point.x, point.y - other.point.y) for point in otherShapelyPoints]
                if len(selfPoints) < len(otherPoints):
                    otherShapelyCentroid: Point = MultiPoint(otherShapelyPoints).centroid
                    otherCentroid: tuple[float, float] = (otherShapelyCentroid.x - other.point.x, otherShapelyCentroid.y - other.point.y)
                    selfPoints.extend([otherCentroid for i in range(len(otherPoints) - len(otherPoints))])
                else:
                    selfShapelyCentroid: Point = MultiPoint(selfShapelyPoints).centroid
                    selfCentroid: tuple[float, float] = (selfShapelyCentroid.x - self.point.x, selfShapelyCentroid.y - self.point.y)
                    otherPoints.extend([selfCentroid for i in range(len(selfPoints) - len(selfPoints))])
            otherPointsRot1 = [Geometric.rotateTuple(point, (0, 0), rotation) for point in otherPoints] # type: ignore[misc]
            otherPointsRot2 = [Geometric.rotateTuple(point, (0, 0), rotation + PI) for point in otherPoints] # type: ignore[misc]
            distance1: float = wasserstein_distance_nd(selfPoints, otherPointsRot1)
            distance2: float = wasserstein_distance_nd(selfPoints, otherPointsRot2)
            totalDistance1 += distance1
            totalDistance2 += distance2
        if totalDistance1 <= totalDistance2:
            return (totalDistance1, rotation)
        else:
            return (totalDistance2, rotation + PI)
    
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