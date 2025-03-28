from shapely import Point, Polygon

from source import Attributes, Buildings, Collection, IO, Perception, Simulator

from argparse import ArgumentParser, Namespace

def main(args: Namespace) -> None:
    queryCollection: Collection = IO.initCollection(args.query[0], args.query[1], args.query[2])
    siteCollection: Collection = IO.initCollection(args.site[0], args.site[1], args.site[2])
    sitePolygons: list[tuple[str, Polygon, Attributes]] = IO.initPolygons(args.polygons, args.target)
    queryBuildings: Buildings = IO.initBuildings(args.buildings)
    siteCollection = siteCollection.filter([polygon for id, polygon, attributes in sitePolygons])
    simulator: Simulator = Simulator(queryCollection, queryBuildings)
    generations: list[tuple[str, list[tuple[Perception, Point, float, tuple[Polygon, ...], Attributes]]]] = list()
    id: str
    sitePolygon: Polygon
    for id, sitePolygon, siteAttributes in sitePolygons:
        generations.append((id, simulator.run(sitePolygon, siteAttributes, siteCollection)))
    generation: tuple[str, list[tuple[Perception, Point, float, tuple[Polygon, ...], Attributes]]]
    for generation in generations:
        IO.write(args.out, generation[0], generation[1])

if __name__ == "__main__":
    parser: ArgumentParser = ArgumentParser()
    parser.add_argument(
        "-q", "--query", nargs=3, type=str, required=True,
        help = (
            "(1) query points GeoJSON, (2) query regions GeoJSON, "
            "and (3) query sample clusters CSV.\n"
            "(1) and (2) must have matching members with the name \"id\", "
            "and (3) must have a matching id column and cluster column."
        )
    )
    parser.add_argument(
        "-s", "--site", nargs=3, type=str, required=True,
        help = (
            "(1) site points GeoJSON, (2) site regions GeoJSON, "
            "and (3) site sample clusters CSV.\n"
            "(1) and (2) must have matching members with the name \"id\", "
            "and (3) must have a matching id column and cluster column."
        )
    )
    parser.add_argument(
        "-p", "--polygons", type=str, required=True,
        help="Site polygons GeoJSON.\n"
        "Generations for each feature will be named"
        "after the \"id\" member if present."
    )
    parser.add_argument(
        "-t", "--target", type=str, required=True,
        help=(
            "CSV with targets as the following columns:\n"
            "(1) residential_gfa\n"
            "(2) commercial_gfa\n"
            "(3) civic_gfa\n"
            "(4) other_gfa\n"
            "(5) site_coverage\n"
            "(6) max_height\n"
            "and id column corresponding to site polygons."
        )
    )
    parser.add_argument(
        "-a", "--buildings", type=str, required=True,
        help=(
            "GeoJSON of polygons corresponding to query.\n"
            "The following attributes will be taken from feature attributes if present:\n"
            "(1) height\n"
            "(2) residential_gfa\n"
            "(3) commercial_gfa\n"
            "(4) civic_gfa\n"
            "(5) other_gfa"
        )
    )
    parser.add_argument(
        "-o", "--out", type=str, default="out",
        help="Output directory"
    )
    args: Namespace = parser.parse_args()
    main(args)