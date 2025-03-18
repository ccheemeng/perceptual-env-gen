from geopandas import GeoDataFrame
from pandas import DataFrame
from pyproj import CRS
from shapely import Point, Polygon

from .Perception import Perception
from .Collection import Collection

class Simulator:
    SG_CRS: CRS = CRS.from_user_input(3414)
    MAX_GENERATION_DISTANCE: float = 100
    MIN_POLYGON_AREA: float = 10

    def __init__(self, queryCollection: Collection, siteCollection: Collection, crs: CRS = SG_CRS):
        self.queryCollection: Collection = queryCollection
        self.siteCollection: Collection = siteCollection
        self.crs: CRS = crs

    def run(self, polygon: Polygon) -> None:
        points: dict[str, Point] = {id: perception.getSample().getPoint()\
                                    for id, perception in self.siteCollection.items()}
        pointsGdf: GeoDataFrame = GeoDataFrame(DataFrame.from_dict(points, orient="index", columns=["geometry"]), crs=crs).clip(polygon.buffer(MAX_GENERATION_DISTANCE), keep_geom_type=True)
        pointsGdf.sindex
        return