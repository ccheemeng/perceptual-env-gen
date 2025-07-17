from geopandas import GeoDataFrame # type: ignore[import-untyped]
from pandas import concat
from shapely import MultiPolygon, Polygon

from .Attributes import Attributes

from typing import Self

class Buildings:
    def __init__(self, polygons: GeoDataFrame) -> None:
        self.polygons: GeoDataFrame = polygons

    @classmethod
    def empty(cls) -> Self:
        return cls(GeoDataFrame())

    def query(self, regions: list[Polygon]) -> tuple[Attributes, Self]:
        region: MultiPolygon = MultiPolygon(regions)
        within: GeoDataFrame = self.polygons.iloc[self.polygons.sindex.query(region, predicate="contains")]
        intersects: GeoDataFrame = self.polygons.iloc[self.polygons.sindex.query(region, predicate="intersects")]
        boundary: GeoDataFrame = intersects.loc[intersects.index.difference(within.index, sort=False)]

        boundary = boundary[boundary.is_valid]
        boundaryClippedGdf: GeoDataFrame
        try:
            boundaryClippedGdf = boundary.clip(region, keep_geom_type=True)
        except Exception as e:
            boundaryClippedGdf = boundary[0:0]
            print(e)
        boundaryClippedGdf = boundaryClippedGdf[boundaryClippedGdf.is_valid]
        boundary = boundary.join(boundaryClippedGdf, lsuffix="_full")
        boundary["ratio"] = boundary["geometry"].area.div(boundary["geometry_full"].area)
        boundary[["residential_gfa", "commercial_gfa", "civic_gfa", "other_gfa"]] = boundary[["residential_gfa", "commercial_gfa", "civic_gfa", "other_gfa"]].mul(boundary["ratio"], axis=0)
        queriedGdf: GeoDataFrame = concat((within[["height", "residential_gfa", "commercial_gfa", "civic_gfa", "other_gfa", "geometry"]], boundary[["height", "residential_gfa", "commercial_gfa", "civic_gfa", "other_gfa", "geometry"]]), axis=0)
        
        attributes: Attributes = Attributes(
            queriedGdf["height"].max(),
            queriedGdf["residential_gfa"].sum(),
            queriedGdf["commercial_gfa"].sum(),
            queriedGdf["civic_gfa"].sum(),
            queriedGdf["other_gfa"].sum(),
            queriedGdf["geometry"].area.sum(),
            sum([region.area for region in regions])
        )
        return attributes, Buildings(queriedGdf) # type: ignore[return-value]

    def getBuildings(self) -> GeoDataFrame:
        return self.polygons.copy()