from geopandas import GeoDataFrame # type: ignore[import-untyped]
from pandas import DataFrame, Series
from shapely import Geometry, MultiPoint, MultiPolygon, Point, Polygon, difference, intersection, union_all, voronoi_polygons
from sklearn.cluster import DBSCAN # type: ignore[import-untyped]

from .Collection import Collection
from .Geometric import Geometric
from .Perception import Perception
from .Sample import Sample

from queue import Queue
import random
import math

class Simulator:
    MAX_GEN_DIST: float = 40
    MIN_POLYGON_AREA: float = 5
    EPS: float = 10

    def __init__(self, queryCollection: Collection, max_gen_dist: float = MAX_GEN_DIST, min_polygon_area: float = MIN_POLYGON_AREA, eps: float = EPS):
        self.queryCollection: Collection = queryCollection
        self.max_gen_dist: float = max_gen_dist
        self.min_polygon_area: float = min_polygon_area
        self.eps: float = eps

    def run(self, site: Polygon, siteCollection: Collection) -> list[tuple[Perception, Point, float, tuple[Polygon, ...]]]:
        polygonQueue: Queue[Polygon] = Queue()
        polygonQueue.put(site)
        # list[tuple[queryPerception, destination, rotation, generatedPolygon]]
        generation: list[tuple[Perception, Point, float, tuple[Polygon, ...]]] = list()
        while not polygonQueue.empty():
            print("=========================")
            polygon: Polygon = polygonQueue.get()
            print(f"Generating for {polygon.__repr__()}")
            print(f"{polygonQueue.qsize()} left in queue")
            print(f"Site: {siteCollection}")
            if polygon.area < self.min_polygon_area:
                print(f"Skipping {polygon.__repr__()}: smaller than 5 m2")
                continue
            generated: list[tuple[Perception, Point, float, tuple[Polygon, ...]]]
            remainingPolygons: list[Polygon]
            newCollection: Collection
            generated, remainingPolygons, newCollection = self.generate(polygon, siteCollection)
            generation.extend(generated)
            remainingPolygon: Polygon
            for remainingPolygon in remainingPolygons:
                if not (remainingPolygon.is_empty or remainingPolygon.equals(polygon)):
                    polygonQueue.put(remainingPolygon)
                    print(f"{remainingPolygon.__repr__()} put in queue")
            siteCollection = newCollection
            print(f"Site: {siteCollection}")
        return generation
    
    def generate(self, polygon: Polygon, siteCollection: Collection) -> tuple[list[tuple[Perception, Point, float, tuple[Polygon, ...]]], list[Polygon], Collection]:
        generators: list[tuple[Perception, Polygon]] = self.findGenerators(polygon, siteCollection)
        print(generators)
        querySamplesAdded: set[Sample] = set()
        newIds: list[str] = list()
        newPoints: list[Point] = list()
        newRegions: list[Polygon] = list()
        newSamples: list[Sample] = list()
        generated: list[tuple[Perception, Point, float, tuple[Polygon, ...]]] = list()
        leftoverPolygons: list[Polygon] = list()
        generator: tuple[Perception, Polygon]
        for generator in generators:
            sitePerception: Perception = generator[0]
            generatingPolygon: Polygon = generator[1]
            distance: float
            queryPerception: Perception
            rotation: float
            distance, queryPerception, rotation = self.queryCollection.findSimilar(sitePerception)
            # queryPerception, rotation = (random.choice(self.queryCollection.getPerceptions()), random.random() * 2 * math.pi)
            origin: Point = queryPerception.getPoint()
            destination: Point = sitePerception.getPoint()
            transformedQueryPolygon: Polygon = Geometric.rotateAboutShapely(Geometric.translateOD(queryPerception.getRegion(), origin, destination), destination, rotation) # type: ignore[assignment]
            generatedPolygon: Geometry = intersection(transformedQueryPolygon, generatingPolygon)
            generatedPolygons: list[Polygon] = Geometric.geometryToPolygons(generatedPolygon)
            generatedPolygons = list(filter(lambda p: not p.is_empty, generatedPolygons))
            if len(generatedPolygons) <= 0:
                leftoverPolygons.append(generatingPolygon)
                continue
            remainingPolygons: list[Polygon] = Geometric.geometryToPolygons(difference(generatingPolygon, MultiPolygon(generatedPolygons)))
            remainingPolygons = list(filter(lambda p: not p.is_empty, remainingPolygons))
            clippingPolygons: list[Polygon] = [Geometric.translateOD(Geometric.rotateAboutShapely(polygon, destination, -rotation), destination, origin) for polygon in generatedPolygons] # type: ignore[misc]
            sampleSetInClip: set[Sample] = set()
            for polygon in clippingPolygons:
                samples: list[Sample] = self.queryCollection.samplesInPolygon(polygon)
                sampleSetInClip.update(samples)
            samplesInClip: list[Sample] = list(filter(lambda s: not s in querySamplesAdded, sampleSetInClip))
            querySamplesAdded.update(samplesInClip)
            sampleInClip: Sample
            for sampleInClip in samplesInClip:
                associatedPerception: Perception = self.queryCollection.perceptionFromSample(sampleInClip)
                newSample = sampleInClip.translate(origin, destination).rotate(destination, rotation)
                newId: str = associatedPerception.getId()
                newPoint: Point = newSample.getPoint()
                newRegion: Polygon = associatedPerception.getRegion()
                newRegion = Geometric.rotateAboutShapely(Geometric.translateOD(newRegion, origin, destination), destination, rotation) # type: ignore[assignment]
                newIds.append(newId)
                newPoints.append(newPoint)
                newRegions.append(newRegion)
                newSamples.append(newSample)
            generated.append((queryPerception, destination, rotation, tuple(generatedPolygons)))
            leftoverPolygons.extend(remainingPolygons)
        leftoverPolygons = Geometric.geometryToPolygons(union_all(leftoverPolygons))
        newSiteCollection = siteCollection.update(newIds, newPoints, newRegions, newSamples)
        return (generated, leftoverPolygons, newSiteCollection)
    
    def findGenerators(self, polygon: Polygon, siteCollection: Collection) -> list[tuple[Perception, Polygon]]:
        generators: list[tuple[Perception, Polygon]] = list()
        sitePerceptions: list[Perception] = siteCollection.getPerceptions()
        perceptionsGdf: GeoDataFrame = GeoDataFrame(data={"perception": sitePerceptions}, geometry=[perception.getPoint() for perception in sitePerceptions])
        perceptionsGdf["distToPolygon"] = perceptionsGdf["geometry"].distance(polygon)
        perceptionsGdf = perceptionsGdf.drop(perceptionsGdf.loc[perceptionsGdf["distToPolygon"] > self.max_gen_dist].index)
        perceptionsGdf = perceptionsGdf.drop_duplicates(subset="geometry")
        perceptionsGdf["cluster"] = perceptionsGdf["perception"].apply(lambda p: p.getCluster())
        cluster_group = perceptionsGdf.groupby("cluster")
        def filterCorePoints(group: DataFrame) -> DataFrame:
            X: list[tuple[float, float]] = [(point.x, point.y) for point in group["geometry"]]
            dbscan: DBSCAN = DBSCAN(eps=self.eps, min_samples=1)
            dbscan.fit(X)
            group["label"] = dbscan.labels_
            core = group.groupby("label")
            def getCore(group: DataFrame) -> DataFrame:
                points: Series = group["geometry"]
                xs: list[float] = [point.x for point in points]
                ys: list[float] = [point.y for point in points]
                centroid: Point = Point(sum(xs) / len(xs), sum(ys) / len(ys))
                group["distance"] = group["geometry"].distance(centroid)
                group = group.sort_values("distance", axis=0)
                group = group.drop(columns="distance")
                return group.head(1)
            return core.apply(getCore, include_groups=False).reset_index(level=0)
        perceptionsGdf = cluster_group.apply(filterCorePoints, include_groups=False).reset_index(level=0)
        perceptionPoints: list[tuple[Perception, Point]] = list()
        for index, row in perceptionsGdf.iterrows():
            perceptionPoints.append((row["perception"], row["geometry"]))
        if len(perceptionPoints) <= 1:
            return [(perceptionPoint[0], polygon) for perceptionPoint in perceptionPoints]
        voronoiPolygons: list[Polygon] = Geometric.voronoiPolygons([perceptionPoint[1] for perceptionPoint in perceptionPoints], extendTo=polygon)
        i: int
        for i in range(len(perceptionPoints)):
            perception: Perception = perceptionPoints[i][0]
            voronoiPolygon: Polygon = voronoiPolygons[i]
            sitePolygons: list[Polygon] = Geometric.geometryToPolygons(intersection(voronoiPolygon, polygon))
            sitePolygon: Polygon
            for sitePolygon in sitePolygons:
                if sitePolygon.is_empty:
                    continue
                generators.append((perception, sitePolygon))
        return generators