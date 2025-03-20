from geopandas import GeoDataFrame # type: ignore[import-untyped]
from pandas import DataFrame
from pyproj import CRS
from shapely import Geometry, GeometryCollection, MultiPoint, MultiPolygon, Point, Polygon,\
    difference, intersection, voronoi_polygons

from .Perception import Perception
from .Collection import Collection

from math import ceil
from queue import Queue
from typing import Union

class Simulator:
    SG_CRS: CRS = CRS.from_user_input(3414)
    MAX_GEN_DIST: float = 100
    MEAN_POLYGON_AREA: float = 500

    def __init__(self, queryCollection: Collection, siteCollection: Collection,
                 crs: CRS = SG_CRS, max_gen_dist: float = MAX_GEN_DIST,
                 mean_polygon_area: float = MEAN_POLYGON_AREA):
        self.queryCollection: Collection = queryCollection
        self.siteCollection: Collection = siteCollection
        self.crs: CRS = crs
        self.max_gen_dist = max_gen_dist
        self.mean_polygon_area = mean_polygon_area

    def run(self, site: Polygon) -> list[tuple[Point, Point, float, Polygon]]:
        polygonQueue: Queue[Polygon] = Queue()
        polygonQueue.put(site)
        # list[tuple[sampleId, sitePolygon, translationXY, ccwRotation]]
        generation: list[tuple[Point, Point, float, Polygon]] = list()
        while not polygonQueue.empty():
            polygon: Polygon = polygonQueue.get()
            generated: list[tuple[Point, Point, float, Polygon]]
            remainingPolygons: list[Polygon]
            generated, remainingPolygons = self.generate(polygon)
            generation.extend(generated)
            remainingPolygon: Polygon
            for remainingPolygon in remainingPolygons:
                polygonQueue.put(remainingPolygon)
            print("===========================================")
        return generation

    def generate(self, polygon: Polygon) ->\
        tuple[list[tuple[Point, Point, float, Polygon]], list[Polygon]]:
        generators: list[tuple[str, Polygon]] = self.findGenerators(polygon)
        generated: list[tuple[Point, Point, float, Polygon]] = list()
        leftoverPolygons: list[Polygon] = list()
        generator: tuple[str, Polygon]
        for generator in generators:
            perceptionId: str = generator[0]
            generatingPolygon: Polygon = generator[1]
            sitePerception: Perception = self.siteCollection.getPerception(perceptionId)
            generatedPolygon: Geometry = intersection(
                sitePerception.perceptionZone(), generatingPolygon) # guaranteed Polygon
            assert(isinstance(generatedPolygon, Polygon))
            if generatedPolygon.is_empty:
                # assigned generating Perception is out of range
                # add to leftovers for next iter of finding
                leftoverPolygons.append(generatingPolygon)
                continue
            print(f"querying for {generator}")
            similarPerception: Perception
            rotation: float
            similarPerception, rotation = self.queryCollection.findSimilar(sitePerception) # type: ignore[assignment]

            remainingPolygons: list[Polygon] = Simulator.geometryToPolygons(difference(generatingPolygon, sitePerception.perceptionZone()))
            remainingPolygons = list(filter(lambda p: not p.is_empty, remainingPolygons))
            leftoverPolygons.extend(remainingPolygons)
            generated.append((similarPerception.getPoint(), sitePerception.getPoint(), rotation, generatedPolygon))
        print(f"Leftover: {leftoverPolygons}")
        return (generated, leftoverPolygons)

    def findGenerators(self, polygon: Polygon) -> list[tuple[str, Polygon]]:
        print(polygon)
        points: dict[str, Point] = {id: perception.getPoint()\
                                    for id, perception in self.siteCollection.getPerceptions().items()}
        pointsGdf: GeoDataFrame = GeoDataFrame(DataFrame\
                .from_dict(points, orient="index", columns=["geometry"]), crs=self.crs)
        pointsGdf["distanceToPolygon"] = pointsGdf.apply(lambda row: row["geometry"].distance(polygon), axis=1)
        numPoints = ceil(polygon.area / self.mean_polygon_area)
        pointsGdf = pointsGdf.loc[pointsGdf["distanceToPolygon"] <= self.max_gen_dist].sort_values("distanceToPolygon", axis=0).head(numPoints)
        voronoiPolygons: list[Polygon] = Simulator.geometryToPolygons(voronoi_polygons(MultiPoint(list(pointsGdf.geometry)), extend_to=polygon))
        ids: list[str] = list(pointsGdf.index)
        assert len(voronoiPolygons) == len(ids),\
            "No 1:1 mapping between site points and site polygons!"
        generators: list[tuple[str, Polygon]] = list()
        for i in range(len(ids)):
            id: str = ids[i]
            voronoiPolygon: Polygon = voronoiPolygons[i]
            sitePolygons: list[Polygon] = Simulator.geometryToPolygons(intersection(voronoiPolygon, polygon))
            sitePolygon: Polygon
            for sitePolygon in sitePolygons:
                if sitePolygon.is_empty:
                    continue
                generators.append((id, sitePolygon))
        return generators

    # to delegate to geometry helper class
    @staticmethod
    def geometryToPolygons(geometry: Geometry) -> list[Polygon]:
        if isinstance(geometry, Polygon):
            return [geometry]
        if isinstance(geometry, MultiPolygon):
            return list(geometry.geoms)
        if isinstance(geometry, GeometryCollection):
            newPolygons: list[Polygon] = list()
            for geom in geometry.geoms:
                newPolygons.extend(Simulator.geometryToPolygons(geom))
            return newPolygons
        return list()