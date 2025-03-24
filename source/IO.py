from geopandas import GeoDataFrame, GeoSeries # type: ignore[import-untyped]
from pandas import DataFrame, Series, read_csv
from shapely import Point, Polygon

from .Collection import Collection
from .Perception import Perception
from .Sample import Sample

from csv import reader
from json import load

class IO:
    @staticmethod
    def initCollection(points_geojson: str, regions_geojson: str, cluster_csv: str) -> Collection:
        pointsGdf: GeoDataFrame
        with open(points_geojson, 'r') as fp:
            pointsGdf = GeoDataFrame.from_features(load(fp))
        regionsGdf: GeoDataFrame
        with open(regions_geojson, 'r') as fp:
            regionsGdf = GeoDataFrame.from_features(load(fp))
        clustersDf: DataFrame
        with open(cluster_csv, 'r') as fp:
            clusterDf = read_csv(fp, header=0, index_col="id")
        ids: list[str] = list()
        points: list[Point] = list()
        regions: list[Polygon] = list()
        samples: list[Sample] = list()
        row: Series
        for id, row in pointsGdf.iterrows():
            point: Point = row["geometry"].values[0]
            assert isinstance(point, Point)
            region: Polygon = regionsGdf.loc[id]["geometry"].values[0]
            assert isinstance(region, Polygon)
            cluster: int = clusterDf.loc[id]["cluster"].values[0]
            assert isinstance(cluster, int)
            sample: Sample = Sample(point, cluster)
            ids.append(str(id))
            points.append(point)
            regions.append(region)
            samples.append(sample)
        return Collection.fromIdsPointsRegionsSamples(ids, points, regions, samples)

    @staticmethod
    def initPolygons(polygons_geojson: str) -> list[tuple[str, Polygon]]:
        polygonsGdf: GeoDataFrame
        with open(polygons_geojson, 'r') as fp:
            polygonsGdf = GeoDataFrame.from_features(load(fp))
        polygons: list[tuple[str, Polygon]]
        row: GeoSeries
        for id, row in polygonsGdf.iterrows():
            polygon: Polygon = row["geometry"].values[0]
            assert isinstance(polygon, Polygon)
            polygons.append((str(id), polygon))
        return polygons

    @staticmethod
    def write(id: str, generation: list[tuple[Perception, Point, float, Polygon]]) -> None:
        return