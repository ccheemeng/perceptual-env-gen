from geopandas import GeoDataFrame, read_file # type: ignore[import-untyped]
from shapely import Geometry, GeometryCollection, MultiPolygon, Point, Polygon

from source import Collection, Perception, Sample, Simulator, Writer

from argparse import ArgumentParser, Namespace
from csv import reader as csvReader
from json import load
from os import walk
from random import Random

def main(args: Namespace) -> None:
    random: Random = Random(args.seed)
    queryCollection: Collection = initCollection(args.query_fps)
    siteCollection: Collection = initCollection(args.site_fps)
    sitePolygons: list[tuple[str, Polygon]] = initSitePolygons(args.site_polygons)
    simulator: Simulator = Simulator(queryCollection)
    output: list[tuple[Polygon, list[tuple[Point, Point, float, Polygon]]]] = list()
    # sitePolygon: Polygon
    # for sitePolygon in sitePolygons:
    #     output.append((polygon, simulator.run(polygon)))
    # Writer(args.out).write(output)
    return

def initCollection(fps: tuple[str, str, str]) -> Collection:
    perceptions: list[Perception] = list()
    pointsGdf: GeoDataFrame
    with open(fps[0], 'r') as fp:
        pointsGdf = GeoDataFrame.from_features(load(fp))
    regionsGdf: GeoDataFrame
    with open(fps[1], 'r') as fp:
        regionsGdf = GeoDataFrame.from_features(load(fp))
    clusters: dict[str, int] = dict()
    with open(fps[2], 'r') as fp:
        reader = csvReader(fp)
        for row in reader:
            id: str = str(row[0])
            cluster: int = int(row[1])
            clusters[id] = cluster
    return Collection.fromPointsRegionsClusters(pointsGdf, regionsGdf, clusters)

def initSitePolygons(path: str) -> list[tuple[str, Polygon]]:
    polygonsGdf: GeoDataFrame
    with open(path, 'r') as fp:
        polygonsGdf = GeoDataFrame.from_features(load(fp))
    return list(zip(polygonsGdf.index.to_list(), polygonsGdf["geometry"].to_list()))

# to delegate to geometry helper class
def geometryToPolygons(geometry: Geometry) -> list[Polygon]:
    if isinstance(geometry, Polygon):
        return [geometry]
    if isinstance(geometry, MultiPolygon):
        return list(geometry.geoms)
    if isinstance(geometry, GeometryCollection):
        newPolygons: list[Polygon] = list()
        for geom in geometry.geoms:
            newPolygons.extend(geometryToPolygons(geom))
        return newPolygons
    return list()

if __name__ == "__main__":
    parser: ArgumentParser = ArgumentParser()
    parser.add_argument(
        "--query-fps", nargs=3, type=str, required=True,
        help=(
            "(1) query points GeoJSON, (2) query regions GeoJSON,"
            " and (3) query sample clusters CSV"
        )
    )
    parser.add_argument(
        "--site-fps", nargs=3, type=str, required=True,
        help=(
            "(1) site points GeoJSON, (2) site regions GeoJSON,"
            " and (3) site sample clusters CSV"
        )
    )
    parser.add_argument(
        "--site-polygons", type=str, required=True,
        help=("Site polygons GeoJSON")
    )
    parser.add_argument(
        "--out", type=str, default="out",
        help="output directory"
    )
    parser.add_argument(
        "--seed", type=str, required=False, default='0'
    )
    args: Namespace = parser.parse_args()
    main(args)