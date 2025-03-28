from geopandas import GeoDataFrame, GeoSeries, read_file # type: ignore[import-untyped]
from pandas import DataFrame, Series, read_csv
from shapely import MultiPolygon, Point, Polygon

from .Attributes import Attributes
from .Buildings import Buildings
from .Collection import Collection
from .Perception import Perception
from .Sample import Sample

from csv import reader, writer
from json import dump, load
from os import walk
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
                print(f"{id} not in {regions_geojson}!")
                continue
            if not id in clusterDf.index:
                print(f"{id} not in {cluster_csv}!")
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
    def initPolygons(polygons_geojson: str, target_csv: str) -> list[tuple[str, Polygon, Attributes]]:
        featureCollectionJson: str
        with open(polygons_geojson, 'r') as fp:
            featureCollectionJson = load(fp)
        ids: list[str]
        try:
            ids = [feature["id"] for feature in featureCollectionJson["features"]]
        except IndexError:
            ids = list()        
        polygonsGdf: GeoDataFrame = GeoDataFrame.from_features(featureCollectionJson)
        if len(ids) > 0:
            polygonsGdf.index = ids
        targetDf: DataFrame
        with open(target_csv, 'r') as fp:
            targetDf = read_csv(fp, header=0, index_col=0)
        if not polygonsGdf.index.sort_values().equals(targetDf.index.sort_values()):
            polygonsGdf = polygonsGdf.reset_index()
            targetDf = targetDf.reset_index()
        polygonsGdf = polygonsGdf.merge(targetDf)
        polygons: list[tuple[str, Polygon]] = list()
        row: GeoSeries
        for id, row in polygonsGdf.iterrows():
            polygon: Polygon = row["geometry"]
            assert isinstance(polygon, Polygon)
            footprintArea: float = row["site_coverage"] * polygon.area
            attributes: Attributes = Attributes(
                row["max_height"],
                row["residential_gfa"],
                row["commercial_gfa"],
                row["civic_gfa"],
                row["other_gfa"],
                footprintArea,
                polygon.area
            )
            polygons.append((str(id), polygon, attributes))
        return polygons
    
    @staticmethod
    def initBuildings(buildings_geojson: str) -> Buildings:
        buildingsGdf: GeoDataFrame
        with open(buildings_geojson, 'r') as fp:
            buildingsGdf = read_file(fp)
        if not "height" in buildingsGdf.columns:
            buildingsGdf["height"] = 0
        if not "residential_gfa" in buildingsGdf.columns:
            buildingsGdf["residential_gfa"] = 0
        if not "commercial_gfa" in buildingsGdf.columns:
            buildingsGdf["commercial_gfa"] = 0
        if not "civic_gfa" in buildingsGdf.columns:
            buildingsGdf["civic_gfa"] = 0
        if not "other_gfa" in buildingsGdf.columns:
            buildingsGdf["other_gfa"] = 0
        return Buildings(buildingsGdf)

    @staticmethod
    def write(dir: str, siteId: str, generation: list[tuple[Perception, Point, float, tuple[Polygon, ...]]]) -> None:
        outputDir: str = join("runs", dir)
        Path(outputDir).mkdir(parents=True, exist_ok=True)
        rows: list[tuple[str, str, float, float, float, float, float, float, float]] = [
            (str(i), generation[i][0].getId(), generation[i][0].getPoint().x, generation[i][0].getPoint().y,
            generation[i][1].x, generation[i][1].y,
            generation[i][1].x - generation[i][0].getPoint().x,
            generation[i][1].y - generation[i][0].getPoint().y, generation[i][2])
            for i in range(len(generation))
        ]
        id: list[str] = [row[0] for row in rows]
        multiPolygons: list[MultiPolygon] = [MultiPolygon(g[3]) for g in generation]
        polygonsGdf: GeoDataFrame = GeoDataFrame(geometry=multiPolygons, index=id)
        with open(join(outputDir, f"{siteId}.csv"), 'w') as fp:
            csvwriter = writer(fp)
            csvwriter.writerow(("id", "perceptionId", "originX", "originY", "destinationX", "destinationY", "translationX", "translationY", "rotationCCW"))
            csvwriter.writerows(rows)
        with open(join(outputDir, f"{siteId}.geojson"), 'w') as fp:
            dump(polygonsGdf.to_geo_dict(), fp)

    @staticmethod
    def collectRuns(genDir: str) -> list[str]:
        runNames: set[str] = set()
        dirpath: str
        dirnames: list[str]
        filenames: list[str]
        for dirpath, dirnames, filenames in walk(genDir):
            filename: str
            for filename in filenames:
                runNames.add('.'.join(filename.split('.')[:-1]))
        return list(runNames)