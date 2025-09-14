import geopandas # type: ignore[import-untyped]
import pandas as pd
import shapely

from .Attributes import Attributes
from .Buildings import Buildings
from .Collection import Collection
from .Geometric import Geometric
from .Perception import Perception
from .Sample import Sample

import csv
import json
import os
from os import path
import pathlib

class IO:
    @staticmethod
    def initCollection(
        points_geojson: str,
        regions_geojson: str,
        cluster_csv: str
    ) -> Collection:
        pointsGdf: geopandas.GeoDataFrame
        with open(points_geojson, 'r') as fp:
            pointsGdf = geopandas.read_file(fp)
            pointsGdf = pointsGdf.set_index("id", drop=True)
        regionsGdf: geopandas.GeoDataFrame
        with open(regions_geojson, 'r') as fp:
            regionsGdf = geopandas.read_file(fp)
            regionsGdf = regionsGdf.set_index("id", drop=True)
        clusterDf: pd.DataFrame
        with open(cluster_csv, 'r') as fp:
            clusterDf = pd.read_csv(fp, header=0, index_col="id")
        ids: list[str] = list()
        points: list[shapely.Point] = list()
        regions: list[shapely.Polygon] = list()
        samples: list[Sample] = list()
        row: pd.Series
        for id, row in pointsGdf.iterrows():
            if not id in regionsGdf.index:
                print(f"{id} not in {regions_geojson}!")
                continue
            if not id in clusterDf.index:
                print(f"{id} not in {cluster_csv}!")
                continue
            point: shapely.Point = row["geometry"]
            assert isinstance(point, shapely.Point)
            region: shapely.Polygon = regionsGdf.loc[id]["geometry"]
            assert isinstance(region, shapely.Polygon)
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
        return Collection.fromIdsPointsRegionsSamples(
            ids, points, regions, samples)

    @staticmethod
    def initPolygons(
        polygons_geojson: str,
        target_csv: str
    ) -> list[tuple[str, shapely.Polygon, Attributes]]:
        featureCollectionJson: dict
        with open(polygons_geojson, 'r') as fp:
            featureCollectionJson = json.load(fp)
        ids: list[str]
        try:
            ids = [
                feature["id"]
                for feature in featureCollectionJson["features"]] # type: ignore[index]
        except IndexError:
            print([feature for feature in featureCollectionJson["features"]])
            ids = list()        
        polygonsGdf: geopandas.GeoDataFrame = (
            geopandas.GeoDataFrame.from_features(featureCollectionJson))
        if len(ids) > 0:
            polygonsGdf.index = ids
        targetDf: pd.DataFrame
        with open(target_csv, 'r') as fp:
            targetDf = pd.read_csv(fp, header=0, index_col=0)
        if not polygonsGdf.index.sort_values().equals(
            targetDf.index.sort_values()
        ):
            polygonsGdf = polygonsGdf.reset_index()
            targetDf = targetDf.reset_index()
        polygonsGdf = polygonsGdf.join(targetDf)
        polygons: list[tuple[str, shapely.Polygon, Attributes]] = list()
        row: geopandas.GeoSeries
        for id, row in polygonsGdf.iterrows():
            polygon: shapely.Polygon = row["geometry"]
            assert isinstance(polygon, shapely.Polygon)
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
        buildingsGdf: geopandas.GeoDataFrame
        with open(buildings_geojson, 'r') as fp:
            buildingsGdf = geopandas.read_file(fp)
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
    def write(dir: str, siteId: str, generation: list[tuple[
        Perception,
        shapely.Point,
        float,
        tuple[shapely.Polygon, ...],
        Attributes,
        Buildings
    ]]) -> None:
        outputDir: str = path.join(dir, siteId)
        pathlib.Path(outputDir).mkdir(parents=True, exist_ok=True)
        rows: list[tuple[
            str,
            str,
            float,
            float,
            float,
            float,
            float,
            float,
            float,
            int
        ]] = [(
            str(i),
            generation[i][0].getId(),
            generation[i][0].getPoint().x,
            generation[i][0].getPoint().y,
            generation[i][1].x, generation[i][1].y,
            generation[i][1].x - generation[i][0].getPoint().x,
            generation[i][1].y - generation[i][0].getPoint().y,
            generation[i][2],
            generation[i][0].getCluster()
        ) for i in range(len(generation))]
        with open(path.join(outputDir, "perceptions.csv"), 'w') as fp:
            csvwriter = csv.writer(fp)
            csvwriter.writerow((
                "id",
                "perceptionId",
                "originX",
                "originY",
                "destinationX",
                "destinationY",
                "translationX",
                "translationY",
                "rotationCCW",
                "cluster"
            ))
            csvwriter.writerows(rows)
        ids: list[str] = [row[0] for row in rows]
        multiPolygons: list[shapely.MultiPolygon] = [
            Geometric.translateOD( # type: ignore[misc]
                Geometric.rotateAboutShapely(
                    shapely.MultiPolygon(g[3]), g[1], -g[2]),
                g[1],
                g[0].getPoint()
            )
            for g in generation]
        polygonsGdf: geopandas.GeoDataFrame = geopandas.GeoDataFrame(
            geometry=multiPolygons, index=ids)
        with open(path.join(outputDir, "polygons.geojson"), 'w') as fp:
            json.dump(polygonsGdf.to_geo_dict(), fp)
        samples: list[list[Sample]] = [
            perception.samplesInPolygon(multiPolygon)
            for perception, multiPolygon in zip(
                [g[0] for g in generation], multiPolygons)]
        sampleRows: list[tuple[str, float, float, int]] = list()
        id: str
        polygonSamples: list[Sample]
        for id, polygonSamples in zip(ids, samples):
            polygonSample: Sample
            for polygonSample in polygonSamples:
                point: shapely.Point = polygonSample.getPoint()
                cluster: int = polygonSample.getCluster()
                sampleRows.append((id, point.x, point.y, cluster))
        with open(path.join(outputDir, f"samples.csv"), 'w') as fp:
            csvwriter = csv.writer(fp)
            csvwriter.writerow(("id", 'x', 'y', "cluster"))
            csvwriter.writerows(sampleRows)
        attributes: list[Attributes] = [g[4] for g in generation]
        with open(path.join(outputDir, "attributes.csv"), 'w') as fp:
            csvwriter = csv.writer(fp)
            csvwriter.writerow((["id"] + list(attributes[0].csvHeader())))
            attribute: Attributes
            for id, attribute in zip(ids, attributes):
                csvwriter.writerow([id] + list(attribute.toCsvRow()))
        buildingsPolygons: list[geopandas.GeoDataFrame] = [
            g[5].getBuildings()
            for g in generation]
        buildingPolygon: geopandas.GeoDataFrame
        for id, buildingPolygon in zip(ids, buildingsPolygons):
            buildingPolygon["id"] = id
        buildings: geopandas.GeoDataFrame = pd.concat(buildingsPolygons)
        with open(path.join(outputDir, "buildings.geojson"), 'w') as fp:
            json.dump(buildings.to_geo_dict(), fp)