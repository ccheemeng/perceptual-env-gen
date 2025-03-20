from geojson import Feature, FeatureCollection, Point, Polygon, geometry # type: ignore[import-untyped]
from shapely import Point as ShapelyPoint, Polygon as ShapelyPolygon

from collections.abc import Collection
from json import dump as jsonDump
from os.path import join as osPathJoin
from pathlib import Path

class Writer:
    def __init__(self, dir: str) -> None:
        geometry.DEFAULT_PRECISION = 16
        self.dir = osPathJoin("runs", dir)

    def write(self, output: list[tuple[ShapelyPolygon, list[tuple[ShapelyPoint, ShapelyPoint, float, ShapelyPolygon]]]]) -> None:
        Path(self.dir).mkdir(parents=True, exist_ok=True)
        plots = {}
        i: int = 0
        plot: tuple[ShapelyPolygon, list[tuple[ShapelyPoint, ShapelyPoint, float, ShapelyPolygon]]]
        for plot in output:
            siteShapelyPolygon: ShapelyPolygon = plot[0]
            siteCoords: list[tuple[float, float]] = list(siteShapelyPolygon.exterior.coords)
            siteCoords.extend(siteShapelyPolygon.interiors)
            sitePolygon: Polygon = Polygon(siteCoords)
            plots[i] = sitePolygon
            simulations = []
            for simulation in plot[1]:
                originPoint: Point = Point((simulation[0].x, simulation[0].y))
                destinationPoint: Point = Point((simulation[1].x, simulation[1].y))
                rotation: float = float(simulation[2])
                clippingShapelyPolygon = simulation[3]
                clippingCoords: list[tuple[float, float]] = list(clippingShapelyPolygon.exterior.coords)
                clippingCoords.extend(clippingShapelyPolygon.interiors)
                clippingPolygon: Polygon = Polygon(clippingCoords)
                simulationFeatureCollection: FeatureCollection = FeatureCollection([
                    Feature(geometry=originPoint, properties={"type": "origin", "rotation": rotation}),
                    Feature(geometry=destinationPoint, properties={"type": "destination"}),
                    Feature(geometry=clippingShapelyPolygon, properties={"type": "mask"})
                ])
                simulations.append(simulationFeatureCollection)
            with open(osPathJoin(self.dir, f"sim{i}.json"), 'w') as fp:
                jsonDump(simulations, fp, indent=4)
            i += 1
        with open(osPathJoin(self.dir, f"plots.json"), 'w') as fp:
            jsonDump(plots, fp, indent=4)