from geojson import Feature, FeatureCollection, Point, Polygon
from geopandas import GeoDataFrame, GeoSeries, clip
from shapely import Point as ShapelyPoint, Polygon as ShapelyPolygon

from argparse import ArgumentParser, Namespace
import csv
from json import load
from math import sin, cos
from os import walk
from os.path import join
from typing import Optional

def main(args: Namespace):
    points: list[ShapelyPoint] = list()
    fps: list[str] = list()
    for root, dir, files in walk(args.dir):
        for file in files:
            points.append(ShapelyPoint([float(x) for x in '.'.join(file.split('.')[:-1]).split('_')[:2]]))
        fps.extend(files)
        break
    fileGdf: GeoDataFrame = GeoDataFrame(data={"fp": fps}, geometry=points)
    fileGdf.sindex

    simulations = []
    with open(args.fp, 'r') as fp:
        simulations = load(fp)
    simulationFeatureCollection: FeatureCollection
    for simulationFeatureCollection in simulations:
        originPoint: Point = getFeatureType(simulationFeatureCollection, "origin")["geometry"]
        destinationPoint: Point = getFeatureType(simulationFeatureCollection, "destination")["geometry"]
        rotation: float = getFeatureType(simulationFeatureCollection, "origin")["properties"]["rotation"]
        maskPolygon: Polygon = getFeatureType(simulationFeatureCollection, "mask")["geometry"]
        originShapelyPoint: ShapelyPoint = ShapelyPoint(originPoint["coordinates"])
        destinationShapelyPoint: ShapelyPoint = ShapelyPoint(destinationPoint["coordinates"])
        exterior = maskPolygon["coordinates"][0]
        interiors = []
        for ring in maskPolygon["coordinates"][1:]:
            interiors.append(ring)
        maskShapelyPolygon: ShapelyPolygon = ShapelyPolygon(shell=exterior, holes=interiors)
        pcFp: str = fileGdf.iloc[fileGdf.sindex.nearest(originShapelyPoint, return_all=False, max_distance=100)[1]]["fp"].values[0]
        points = list()
        labels: list[int] = list()
        # with open(join(args.dir, pcFp), 'r') as fp:
        #     reader = csv.reader(fp)
        #     for row in reader:
        #         points.append(transform(ShapelyPoint((row[0], row[1], row[2])),
        #                                 originShapelyPoint, destinationShapelyPoint, rotation))
        #         labels.append(row[3])
        # stopgap
        with open(join(args.dir, pcFp), 'r') as fp:
            reader = csv.reader(fp)
            for row in reader:
                points.append((row[0], row[1], row[2]))
                labels.append(row[3])
        destx = sum([float(p[0]) for p in points]) / len(points)
        desty = sum([float(p[1]) for p in points]) / len(points)
        originShapelyPoint = ShapelyPoint((destx, desty, 0))
        points = [transform(ShapelyPoint((float(p[0]), float(p[1]), float(p[2]))), originShapelyPoint, destinationShapelyPoint, rotation) for p in points]
        pcGdf: GeoDataFrame = GeoDataFrame(data={"label": labels}, geometry=points, crs=3414)
        mask: GeoSeries = GeoSeries(maskShapelyPolygon, crs=3414)
        pcGdf.to_file(f"{pcFp}_pc.geojson")
        GeoSeries(destinationShapelyPoint, crs=3414).to_file(f"{pcFp}_dest.geojson")
        mask.to_file(f"{pcFp}_mask.geojson")
        print(originPoint, destinationPoint)
        print(mask)
        pcGdf = clip(pcGdf, mask, keep_geom_type=True)
        print(pcGdf)
        rows = []
        for index, row in pcGdf.iterrows():
            rows.append([row["geometry"].x, row["geometry"].y, row["geometry"].z, row["label"]])
        print(f"writing {pcFp}")
        with open(args.out, 'a') as fp:
            writer = csv.writer(fp)
            writer.writerows(rows)

def getFeatureType(featureCollection: FeatureCollection, type: str) -> Optional[Feature]:
    feature: Feature
    for feature in featureCollection["features"]:
        if type == feature["properties"]["type"]:
            return feature
    return None

# applies translation then rotates about destination point
def transform(point: ShapelyPoint, origin: ShapelyPoint, destination: ShapelyPoint, rotation: float) -> ShapelyPoint:
    dx: float = destination.x - origin.x
    dy: float = destination.y - origin.y
    x0: float = point.x + dx - destination.x
    y0: float = point.y + dy - destination.y
    xrot: float = x0 * cos(rotation) - y0 * sin(rotation)
    yrot: float = y0 * cos(rotation) + x0 * sin(rotation)
    x: float = xrot + destination.x
    y: float = yrot + destination.y
    return ShapelyPoint((x, y, point.z))

if __name__ == "__main__":
    parser: ArgumentParser = ArgumentParser()
    parser.add_argument(
        "--fp", type=str, required=True,
        help="JSON generation file"
    )
    parser.add_argument(
        "--dir", type=str, required=True,
        help="point cloud sample directory"
    )
    parser.add_argument(
        "--out", type=str, default="out.csv",
        help="output file"
    )
    args: Namespace = parser.parse_args()
    main(args)