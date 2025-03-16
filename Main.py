from geopandas import read_file, GeoDataFrame # type: ignore
from shapely import Geometry, GeometryCollection, MultiPolygon, Polygon

from source import Collection, Simulator

from argparse import ArgumentParser, Namespace
from json import load

def main(args: Namespace) -> None:
    samples: GeoDataFrame = read_file(args.fp[0])
    site: list[Polygon] = list()
    geometry: Geometry
    for geometry in read_file(args.fp[1])["geometry"].values:
        site.extend(geometryToPolygons(geometry))
    validateInput(samples, site)
    queryCollection: Collection = Collection.fromGeoDataFrame(samples)
    siteCollection: Collection = Collection.fromGeoDataFrame()
    simulator: Simulator = Simulator(readCollection)
    polygon: Polygon
    for polygon in site:
        simulator.run(polygon)
    return

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
        samples: GeoDataFrame,
        site: list[Polygon]
) -> None:
    validateSamples(samples)
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
        "--fp", nargs=2, type=str, required=True,
        help="GeoJSON filepaths for (1) samples and (2) site (multi)polygon"
    )
    args: Namespace = parser.parse_args()
    main(args)