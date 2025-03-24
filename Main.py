from shapely import Point, Polygon

from source import Collection, IO, Perception, Simulator

from argparse import ArgumentParser, Namespace

def main(args: Namespace) -> None:
    queryCollection: Collection = IO.initCollection(args.query_fps[0], args.query_fps[1], args.query_fps[2])
    siteCollection: Collection = IO.initCollection(args.site_fps[0], args.site_fps[1], args.site_fps[2])
    sitePolygons: list[tuple[str, Polygon]] = IO.initPolygons(args.polygon_fp)
    simulator: Simulator = Simulator(queryCollection)
    generations: list[tuple[str, list[tuple[Perception, Point, float, Polygon]]]]
    id: str
    sitePolygon: Polygon
    for id, sitePolygon in sitePolygons:
        generations.append((id, simulator.run(sitePolygon, siteCollection)))
    generation: tuple[str, list[tuple[Perception, Point, float, Polygon]]]
    for generation in generations:
        IO.write(generation[0], generation[1])

if __name__ == "__main__":
    parser: ArgumentParser = ArgumentParser()
    parser.add_argument(
        "--query-fps", nargs=3, type=str, required=True,
        help = (
            "(1) query points GeoJSON, (2) query regions GeoJSON, "
            "and (3) query sample clusters CSV.\n"
            "(1) and (2) must have matching members with the name \"id\", "
            "and (3) must have a matching id column and cluster column."
        )
    )
    parser.add_argument(
        "--site-fps", nargs=3, type=str, required=True,
        help = (
            "(1) site points GeoJSON, (2) site regions GeoJSON, "
            "and (3) site sample clusters CSV.\n"
            "(1) and (2) must have matching members with the name \"id\", "
            "and (3) must have a matching id column and cluster column."
        )
    )
    parser.add_argument(
        "--polygon-fp", type=str, required=True,
        help="Site polygons GeoJSON"
    )
    parser.add_argument(
        "--out", type=str, default="out",
        help="Output directory"
    )
    args: Namespace = parser.parse_args()
    main(args)