import geopandas
import pandas as pd
import shapely

from source import Geometric

import argparse
import csv
import os
from os import path

def main(args: argparse.Namespace) -> None:
    dirpath: str
    runs: list[str]
    filenames: list[str]
    for dirpath, runs, filenames in os.walk(args.gen_dir):
        break
    run: str
    for run in runs:
        transformationDf: pd.DataFrame
        with open(
            path.join(args.gen_dir, run, "perceptions.csv"), 'r') as fp:
            transformationDf = pd.read_csv(
                fp, header=0, index_col=0).rename(index=(lambda i: str(i)))
        multiPolygonGdf: geopandas.GeoDataFrame
        with open(
            path.join(args.gen_dir, run, "polygons.geojson"), 'r') as fp:
            multiPolygonGdf = geopandas.read_file(fp)
            multiPolygonGdf = multiPolygonGdf.set_index(
                "id", drop=True).rename(index=(lambda i: str(i)))
        index: str
        multiPolygon: geopandas.GeoSeries
        for index, multiPolygon in multiPolygonGdf.iterrows():
            perceptionId: str = transformationDf.loc[index]["perceptionId"]
            translation: tuple[float, float] = tuple(
                transformationDf.loc[index][["translationX", "translationY"]])
            destination: tuple[float, float] = tuple(
                transformationDf.loc[index][["destinationX", "destinationY"]])
            rotation: float = transformationDf.loc[index]["rotationCCW"]
            multiPolygon: shapely.MultiPolygon = multiPolygon["geometry"]
            points: list[shapely.Point] = list()
            labels: list[shapely.Point] = list()
            with open(
                path.join(args.pc_dir, f"{perceptionId}.csv"), 'r') as fp:
                csvreader = csv.reader(fp)
                for row in csvreader:
                    pointxy = Geometric.rotateTuple(
                        Geometric.translateTuple(
                            (float(row[0]), float(row[1])), translation),
                        destination,
                        rotation
                    )
                    points.append(shapely.Point(pointxy[0], pointxy[1], row[2]))
                    labels.append(int(row[3]))
            pointsGdf: geopandas.GeoDataFrame = geopandas.GeoDataFrame(
                data={"label": labels}, geometry=points).clip(
                    Geometric.rotateAboutTuple(
                        Geometric.translateVectorTuple(
                            multiPolygon, translation),
                        destination,
                        rotation
                    ), keep_geom_type=True)
            print(len(pointsGdf), multiPolygon.__repr__())
            rows: list[tuple[float, float, float, int]] = list()
            pointLabel: geopandas.GeoSeries
            for _, pointLabel in pointsGdf.iterrows():
                point: shapely.Point = pointLabel["geometry"]
                label: int = pointLabel["label"]
                rows.append((point.x, point.y, point.z, label))
            with open(path.join(args.gen_dir, run, "points.csv"), 'a') as fp:
                csvwriter = csv.writer(fp)
                csvwriter.writerows(rows)

if __name__ == "__main__":
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument(
        "--gen-dir", type=str, required=True,
        help = (
            "Directory containing directories for each site polygon.\n" \
            "Each site polygon directory must contain\n" \
            "(1) perceptions.csv\n" \
            "(2) polygons.geojson"))
    parser.add_argument(
        "--pc-dir", type=str, required=True,
        help = (
            "Directory containing query point cloud CSVs "
            "with no header and 4 columns:\n"
            "    x: float\n"
            "    y: float\n"
            "    z: float\n"
            "label: int\n"
            "CSVs must have filenames corresponding to values in "
            "perceptionId column in query point cloud transformation CSV."))
    args: argparse.Namespace = parser.parse_args()
    main(args)