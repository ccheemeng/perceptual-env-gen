from geopandas import GeoDataFrame, GeoSeries, read_file
from pandas import DataFrame, read_csv
from shapely import MultiPolygon, Point

from source import Geometric, IO

from argparse import ArgumentParser, Namespace
from csv import reader, writer
from os.path import join

def main(args: Namespace) -> None:
    runs: list[str] = IO.collectRuns(args.gen_dir)
    run: str
    for run in runs:
        transformationDf: DataFrame
        with open(join(args.gen_dir, f"{run}.csv"), 'r') as fp:
            transformationDf = read_csv(fp, header=0, index_col=0).rename(index=(lambda i: str(i)))
        multiPolygonGdf: GeoDataFrame
        with open(join(args.gen_dir, f"{run}.geojson"), 'r') as fp:
            multiPolygonGdf = read_file(fp)
            multiPolygonGdf = multiPolygonGdf.set_index("id", drop=True).rename(index=(lambda i: str(i)))
        index: str
        multiPolygon: GeoSeries
        for index, multiPolygon in multiPolygonGdf.iterrows():
            perceptionId: str = transformationDf.loc[index]["perceptionId"]
            translation: tuple[float, float] = tuple(transformationDf.loc[index][["translationX", "translationY"]])
            destination: tuple[float, float] = tuple(transformationDf.loc[index][["destinationX", "destinationY"]])
            rotation: float = transformationDf.loc[index]["rotationCCW"]
            multiPolygon: MultiPolygon = multiPolygon["geometry"]
            points: list[Point] = list()
            labels: list[Point] = list()
            with open(join(args.pc_dir, f"{perceptionId}_sampled.csv"), 'r') as fp:
                csvreader = reader(fp)
                for row in csvreader:
                    pointxy = Geometric.rotateTuple(Geometric.translateTuple((float(row[0]), float(row[1])), translation), destination, rotation)
                    points.append(Point(pointxy[0], pointxy[1], row[2]))
                    labels.append(int(row[3]))
            pointsGdf: GeoDataFrame = GeoDataFrame(data={"label": labels}, geometry=points).clip(multiPolygon, keep_geom_type=True)
            print(len(pointsGdf), multiPolygon.__repr__())
            rows: list[tuple[float, float, float, int]] = list()
            pointLabel: GeoSeries
            for _, pointLabel in pointsGdf.iterrows():
                point: Point = pointLabel["geometry"]
                label: int = pointLabel["label"]
                rows.append((point.x, point.y, point.z, label))
            with open(join(args.gen_dir, f"{run}_points.csv"), 'a') as fp:
                csvwriter = writer(fp)
                csvwriter.writerows(rows)

if __name__ == "__main__":
    parser: ArgumentParser = ArgumentParser()
    parser.add_argument(
        "--gen-dir", type=str, required=True,
        help = (
            "Directory containing pairs of\n"
            "(1) query point cloud transformation CSV and "
            "(2) query application MultiPolygon GeoJSON.\n"
            "(1) must have an id column with a corresponding MultiPolygon in "
            "(2) via its member \"id\".\n"
            "(2) must have the same file name as (1) excluding file type extension."
        )
    )
    parser.add_argument(
        "--pc-dir", type=str, required=True,
        help = (
            "Directory containing query point cloud CSVs with no header and 4 columns:\n"
            "    x: float\n"
            "    y: float\n"
            "    z: float\n"
            "label: int\n"
            "CSVs must have filenames corresponding to values in "
            "perceptionId column in query point cloud transformation CSV."
        )
    )
    args: Namespace = parser.parse_args()
    main(args)