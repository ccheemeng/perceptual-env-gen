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
    MAX_GEN_DIST: float = 40

    def __init__(self, queryCollection: Collection, siteCollection: Collection,
                 crs: CRS = SG_CRS, max_gen_dist: float = MAX_GEN_DIST) -> None:
        self.queryCollection: Collection = queryCollection
        self.crs: CRS = crs
        self.max_gen_dist = max_gen_dist

    def run(self, site: Polygon, siteCollection: Collection) -> list[tuple[Point, Point, float, Polygon]]:
        polygonQueue: Queue[Polygon] = Queue()
        polygonQueue.put(site)
        # list[tuple[sampleId, sitePolygon, translationXY, ccwRotation]]
        generation: list[tuple[Point, Point, float, Polygon]] = list()
        while not polygonQueue.empty():
            polygon: Polygon = polygonQueue.get()
            generated: list[tuple[Point, Point, float, Polygon]]
            remainingPolygons: list[Polygon]
            newCollection: Collection
            generated, remainingPolygons, newCollection = self.generate(polygon, siteCollection)
            generation.extend(generated)
            remainingPolygon: Polygon
            for remainingPolygon in remainingPolygons:
                polygonQueue.put(remainingPolygon)
            siteCollection = newCollection
            print("===========================================")
        return generation

    def generate(self, polygon: Polygon, siteCollection: Collection) ->\
        tuple[list[tuple[Perception, Perception, float, Polygon]], list[Polygon], Collection]:
        generators: list[tuple[Perception, Polygon]] = self.findGenerators(polygon, siteCollection)
        generated: list[tuple[Perception, Perception, float, Polygon]] = list()
        leftoverPolygons: list[Polygon] = list()
        generator: tuple[Perception, Polygon]
        for generator in generators:
            sitePerception: Perception = generator[0]
            generatingPolygon: Polygon = generator[1]
            print(f"querying for {generator}")
            similarPerception: Perception
            rotation: float
            similarPerception, rotation = self.queryCollection.findSimilar(sitePerception) # type: ignore[assignment]
            generatedPolygon: Polygon = Simulator.rotate(similarPerception.getRegion(), similarPerception.getPoint(), rotation)
            generatedPolygon = intersection(generatedPolygon, generatingPolygon) # guaranteed Polygon
            assert(isinstance(generatedPolygon, Polygon))
            if generatedPolygon.is_empty:
                # assigned generating Perception is out of range
                # add to leftovers for next iter of finding
                leftoverPolygons.append(generatingPolygon)
                continue
            generated.append((similarPerception, sitePerception, rotation, generatedPolygon))
            remainingPolygons: list[Polygon] = Simulator.geometryToPolygons(difference(generatingPolygon, generatedPolygon))
            remainingPolygons = list(filter(lambda p: not p.is_empty, remainingPolygons))
            leftoverPolygons.extend(remainingPolygons)
        siteCollection = siteCollection.update(generated, self.queryCollection)
        # for each added perception (translate and rotate)
        # consider all samples within the generated polygon
        # (except the sample associated with the site perception if it is within the generated polygon).
        # take the region of the perception associated with that sample (translated and rotated)
        # and create a new perception
        # with svds calculated from the translated and rotated region
        # and samples in the translated and rotated region (including added samples within all generatedPolygons).
        # add that perception to the sitecollection
        # be careful of existing ids
        # perception shouldnt provide some kind of translation and rotation function
        # ideally collection gets the region from perception
        # and a geometry helper class translates and rotates the region
        return (generated, leftoverPolygons, siteCollection)

    def findGenerators(self, polygon: Polygon) -> list[tuple[str, Polygon]]:
        points: dict[str, Point] = {id: perception.getPoint()\
                                    for id, perception in self.siteCollection.getPerceptions().items()}
        pointsGdf: GeoDataFrame = GeoDataFrame(DataFrame\
                .from_dict(points, orient="index", columns=["geometry"]), crs=self.crs)
        pointsGdf["distanceToPolygon"] = pointsGdf.apply(lambda row: row["geometry"].distance(polygon.centroid), axis=1)
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