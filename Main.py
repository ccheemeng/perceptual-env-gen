from geopandas import GeoDataFrame, read_file # type: ignore[import-untyped]
from shapely import Geometry, GeometryCollection, MultiPolygon, Polygon

from source import Collection, Simulator

from argparse import ArgumentParser, Namespace
from json import load
from random import Random

def main(args: Namespace) -> None:
    random: Random = Random(args.seed)
    querySamples: GeoDataFrame = read_file(args.fp[0])
    siteSamples: GeoDataFrame = read_file(args.fp[1])
    site: list[Polygon] = list()
    geometry: Geometry
    for geometry in read_file(args.fp[2])["geometry"].values:
        site.extend(geometryToPolygons(geometry))
    validateInput(querySamples, siteSamples, site)
    queryCollection: Collection = Collection.fromGeoDataFrame(querySamples, random=random)
    siteCollection: Collection = Collection.fromGeoDataFrame(siteSamples, random=random)
    simulator: Simulator = Simulator(queryCollection, siteCollection)
    polygon: Polygon
    for polygon in site:
        simulator.run(polygon)
    return

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

def validateInput(
        querySamples: GeoDataFrame,
        siteSamples: GeoDataFrame,
        site: list[Polygon]
) -> None:
    validateSamples(querySamples)
    validateSamples(siteSamples)
    validateSite(site)

def validateSamples(samples: GeoDataFrame) -> None:
    exception: bool = False
    try:
        samples["geometry"]
    except KeyError:
        print("Input file has no geometry!")
        exception = True
    try:
        samples["cluster"]
    except KeyError:
        print("Input file has no cluster!")
        exception = True
    if exception:
        exit()

def validateSite(site: list[Polygon]) -> None:
    if len(site) <= 0:
        raise ValueError("No input polygons found!")

if __name__ == "__main__":
    parser: ArgumentParser = ArgumentParser()
    parser.add_argument(
        "--fp", nargs=3, type=str, required=True,
        help=(
            "GeoJSON filepaths for (1) query samples, "
            "(2) site samples, and (3) site (multi)polygon"
        )
    )
    parser.add_argument(
        "--seed", type=str, required=False, default='0',
        help=("Seed for RNG")
    )
    args: Namespace = parser.parse_args()
    main(args)