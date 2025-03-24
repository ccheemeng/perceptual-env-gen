from geopandas import GeoDataFrame, GeoSeries, read_file # type: ignore[import-untyped]
from pandas import DataFrame, Series, read_csv
from shapely import MultiPolygon, Point, Polygon

from .Collection import Collection
from .Perception import Perception
from .Sample import Sample

from csv import reader, writer
from json import dump, load
from os.path import join
from pathlib import Path

class IO:
    @staticmethod
    def initCollection(points_geojson: str, regions_geojson: str, cluster_csv: str) -> Collection:
        pointsGdf: GeoDataFrame
        with open(points_geojson, 'r') as fp:
            pointsGdf = read_file(fp)
            pointsGdf = pointsGdf.set_index("id", drop=True)
        regionsGdf: GeoDataFrame
        with open(regions_geojson, 'r') as fp:
            regionsGdf = read_file(fp)
            regionsGdf = regionsGdf.set_index("id", drop=True)
        clusterDf: DataFrame
        with open(cluster_csv, 'r') as fp:
            clusterDf = read_csv(fp, header=0, index_col="id")
        ids: list[str] = list()
        points: list[Point] = list()
        regions: list[Polygon] = list()
        samples: list[Sample] = list()
        row: Series
        for id, row in pointsGdf.iterrows():
            if not id in regionsGdf.index:
                print(f"{id} in {points_geojson} not in {regions_geojson}!")
                continue
            if not id in clusterDf.index:
                print(f"{id} in {points_geojson} not in {cluster_csv}!")
                continue
            point: Point = row["geometry"]
            assert isinstance(point, Point)
            region: Polygon = regionsGdf.loc[id]["geometry"]
            assert isinstance(region, Polygon)
            cluster = clusterDf.loc[id]["cluster"]
            try:
                int(cluster)
            except ValueError:
                raise ValueError("Cluster values must be castable to int!")
            sample: Sample = Sample(point, int(cluster))
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
        polygons: list[tuple[str, Polygon]] = list()
        row: GeoSeries
        for id, row in polygonsGdf.iterrows():
            polygon: Polygon = row["geometry"]
            assert isinstance(polygon, Polygon)
            polygons.append((str(id), polygon))
        return polygons

    @staticmethod
    def write(dir: str, siteId: str, generation: list[tuple[Perception, Point, float, tuple[Polygon, ...]]]) -> None:
        outputDir: str = join("runs", dir)
        Path(outputDir).mkdir(parents=True, exist_ok=True)
        rows: list[tuple[str, float, float, float, float, float, float, float]] = [
            (g[0].getId(), g[0].getPoint().x, g[0].getPoint().y, g[1].x, g[1].y,
            g[1].x - g[0].getPoint().x, g[1].y - g[0].getPoint().y, g[2])
            for g in generation
        ]
        perceptionId: list[str] = [row[0] for row in rows]
        multiPolygons: list[MultiPolygon] = [MultiPolygon(g[3]) for g in generation]
        polygonsGdf: GeoDataFrame = GeoDataFrame(geometry=multiPolygons, index=perceptionId)
        print(polygonsGdf)
        with open(join(outputDir, f"{siteId}.csv"), 'w') as fp:
            csvwriter = writer(fp)
            csvwriter.writerow(("id", "originX", "originY", "destinationX", "destinationY", "translationX", "translationY", "rotationCCW"))
            csvwriter.writerows(rows)
        with open(join(outputDir, f"{siteId}.geojson"), 'w') as fp:
            dump(polygonsGdf.to_geo_dict(), fp)