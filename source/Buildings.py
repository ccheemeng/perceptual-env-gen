from geopandas import GeoDataFrame # type: ignore[import-untyped]
from pandas import DataFrame, concat
from shapely import MultiPolygon, Polygon

from .Attributes import Attributes

from functools import reduce

class Buildings:
    def __init__(self, polygons: GeoDataFrame) -> None:
        polygons.sindex
        self.polygons: GeoDataFrame = polygons

    def query(self, regions: list[Polygon]) -> Attributes:
        region: MultiPolygon = MultiPolygon(regions)
        within: GeoDataFrame = self.polygons.iloc[self.polygons.sindex.query(region, predicate="contains")]
        intersects: GeoDataFrame = self.polygons.iloc[self.polygons.sindex.query(region, predicate="intersects")]
        boundary: GeoDataFrame = intersects.loc[intersects.index.difference(within.index, sort=False)]

        # to remove when verified
        if len(within) + len(boundary) != len(intersects):
            print(within)
            print(boundary)
            print(intersects)

        boundaryClippedGdf: GeoDataFrame = boundary.clip(region, keep_geom_type=True)
        boundary = boundary.join(boundaryClippedGdf, lsuffix="_full")
        boundary["ratio"] = boundary["geometry"].area.div(boundary["geometry_full"].area)
        boundary[["residential_gfa", "commercial_gfa", "civic_gfa", "other_gfa"]] = boundary[["residential_gfa", "commercial_gfa", "civic_gfa", "other_gfa"]].mul(boundary["ratio"], axis=0)
        queriedGdf: GeoDataFrame = concat((within[["height", "residential_gfa", "commercial_gfa", "civic_gfa", "other_gfa", "geometry"]], boundary[["height", "residential_gfa", "commercial_gfa", "civic_gfa", "other_gfa", "geometry"]]), axis=0)
        
        # # to remove
        # print("within")
        # print(within)
        # print("boundary")
        # print(boundary)
        # print("boundaryClipped")
        # print(boundaryClippedGdf)
        # print("queried")
        # print(queriedGdf)
        
        attributes: Attributes = Attributes(
            queriedGdf["height"].max(),
            queriedGdf["residential_gfa"].sum(),
            queriedGdf["commercial_gfa"].sum(),
            queriedGdf["civic_gfa"].sum(),
            queriedGdf["other_gfa"].sum(),
            queriedGdf["geometry"].area.sum(),
            sum([region.area for region in regions])
        )
        return attributes