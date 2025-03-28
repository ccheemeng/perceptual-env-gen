from geopandas import GeoDataFrame
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
        boundary: GeoDataFrame = self.polygons.iloc[self.polygons.sindex.query(region, predicate="overlaps")]

        # to remove when verified
        intersects: GeoDataFrame = self.polygons.iloc[self.polygons.sindex.query(region, predicate="intersects")]
        assert(len(within) + len(boundary) == len(intersects))

        boundaryClipped: GeoDataFrame = boundary.clip(region, keep_geom_type=True)
        boundary = boundary.merge(boundaryClipped, suffixes=("_full", ''))
        boundary["ratio"] = boundary.apply(lambda row: row["geometry"].area / row["geometry_full"].area, axis=1)
        boundary[["residential_gfa", "commercial_gfa", "civic_gfa", "other_gfa"]] = boundary[["residential_gfa", "commercial_gfa", "civic_gfa", "other_gfa"]].mul(boundary["ratio"], axis=0)
        queriedGdf: GeoDataFrame = concat((within[["height", "residential_gfa", "commercial_gfa", "civic_gfa", "other_gfa", "geometry"]], boundary[["height", "residential_gfa", "commercial_gfa", "civic_gfa", "other_gfa", "geometry"]]), axis=0)
        attributes: Attributes = Attributes(
            queriedGdf["height"].max(),
            queriedGdf["residential_gfa"].sum(),
            queriedGdf["commercial_gfa"].sum(),
            queriedGdf["civic_gfa"].sum(),
            queriedGdf["other_gfa"].sum(),
            queriedGdf["geometry"].apply(lambda p: p.area).sum(),
            sum([region.area for region in regions])
        )
        return attributes