import geopandas # type: ignore[import-untyped]
import pandas as pd
import shapely
from sklearn import cluster # type: ignore[import-untyped]

from .Attributes import Attributes
from .Buildings import Buildings
from .Collection import Collection
from .Geometric import Geometric
from .Perception import Perception
from .Sample import Sample

import functools
import queue

class Simulator:
    MAX_GEN_DIST: float = 40
    MIN_POLYGON_AREA: float = 15
    EPS: float = 10

    def __init__(self,
        queryCollection: Collection,
        queryBuildings: Buildings
    ):
        self.queryCollection: Collection = queryCollection
        self.queryBuildings: Buildings = queryBuildings

    def run(self,
        site: shapely.Polygon,
        target: Attributes,
        siteCollection: Collection
    ) -> list[tuple[
        Perception,
        shapely.Point,
        float,
        tuple[shapely.Polygon, ...],
        Attributes,
        Buildings
    ]]:
        polygonQueue: queue.Queue[shapely.Polygon] = queue.Queue()
        polygonQueue.put(site)
        # list[tuple[queryPerception, destination, rotation, generatedPolygon]]
        generation: list[tuple[
            Perception,
            shapely.Point,
            float,
            tuple[shapely.Polygon, ...],
            Attributes,
            Buildings
        ]] = list()
        while not polygonQueue.empty():
            print("=========================")
            polygon: shapely.Polygon = polygonQueue.get()
            print(
                f"Generating for {polygon.__repr__()}\n"
                f"{polygonQueue.qsize()} left in queue\n"
                f"Site: {siteCollection}\n"
                f"Target: {target}")
            if polygon.area < self.MIN_POLYGON_AREA:
                print(
                    f"Skipping {polygon.__repr__()}: "
                    "smaller than {self.MIN_POLYGON_AREA} m2")
                continue
            generated: list[tuple[
                Perception,
                shapely.Point,
                float,
                tuple[shapely.Polygon, ...],
                Attributes,
                Buildings
            ]]
            remainingPolygons: list[shapely.Polygon]
            newCollection: Collection
            (
                generated,
                remainingPolygons,
                newCollection,
                newTarget
            ) = self.generate(polygon, siteCollection, target)
            generation.extend(generated)
            remainingPolygon: shapely.Polygon
            for remainingPolygon in remainingPolygons:
                if not (
                    remainingPolygon.is_empty
                    or remainingPolygon.equals(polygon)
                ):
                    polygonQueue.put(remainingPolygon)
                    print(f"{remainingPolygon.__repr__()} put in queue")
            siteCollection = newCollection
            target = newTarget
            achieved: Attributes = functools.reduce(
                (lambda a1, a2: a1.accumulate(a2)),
                [g[4] for g in generated],
                Attributes.of()
            )
            print(f"Achieved: {achieved}")
        return generation
    
    def generate(self,
        polygon: shapely.Polygon,
        siteCollection: Collection,
        target: Attributes
    ) -> tuple[
        list[tuple[
            Perception,
            shapely.Point,
            float,
            tuple[shapely.Polygon, ...],
            Attributes,
            Buildings
        ]],
        list[shapely.Polygon],
        Collection,
        Attributes
    ]:
        generators: list[tuple[
            Perception,
            shapely.Polygon,
            Attributes
        ]] = self.findGenerators(polygon, siteCollection, target)
        print(f"{len(generators)} generators")
        querySamplesAdded: set[Sample] = set()
        newIds: list[str] = list()
        newPoints: list[shapely.Point] = list()
        newRegions: list[shapely.Polygon] = list()
        newSamples: list[Sample] = list()
        generated: list[tuple[
            Perception,
            shapely.Point,
            float,
            tuple[shapely.Polygon, ...],
            Attributes,
            Buildings
        ]] = list()
        leftoverPolygons: list[shapely.Polygon] = list()
        achieved: Attributes = Attributes.of()
        generator: tuple[Perception, shapely.Polygon, Attributes]
        for generator in generators:
            sitePerception: Perception = generator[0]
            generatingPolygon: shapely.Polygon = generator[1]
            siteTarget: Attributes = generator[2]
            queryPerception: Perception
            rotation: float
            generatedPolygons: list[shapely.Polygon]
            queryAchieved: Attributes
            buildings: Buildings
            (
                queryPerception,
                rotation,
                generatedPolygons,
                queryAchieved,
                buildings
            ) = self.queryCollection.query(
                sitePerception,
                generatingPolygon,
                self.queryBuildings,
                siteTarget
            )
            if len(generatedPolygons) <= 0:
                leftoverPolygons.append(generatingPolygon)
                continue
            origin: shapely.Point = queryPerception.getPoint()
            destination: shapely.Point = sitePerception.getPoint()
            remainingPolygons: list[
                shapely.Polygon
            ] = Geometric.geometryToPolygons(
                shapely.difference(
                    generatingPolygon, shapely.MultiPolygon(generatedPolygons)))
            remainingPolygons = list(
                filter(lambda p: not p.is_empty, remainingPolygons))
            clippingPolygons: list[shapely.Polygon] = [
                Geometric.translateOD( # type: ignore[misc]
                    Geometric.rotateAboutShapely(
                        polygon,
                        destination,
                        -rotation
                    ),
                    destination,
                    origin
                )
                for polygon in generatedPolygons]
            sampleSetInClip: set[Sample] = set()
            for polygon in clippingPolygons:
                samples: list[Sample] = self.queryCollection.samplesInPolygon(
                    polygon)
                sampleSetInClip.update(samples)
            samplesInClip: list[Sample] = list(
                filter(lambda s: not s in querySamplesAdded, sampleSetInClip))
            querySamplesAdded.update(samplesInClip)
            sampleInClip: Sample
            for sampleInClip in samplesInClip:
                associatedPerception: Perception = (
                    self.queryCollection.perceptionFromSample(sampleInClip))
                newSample = sampleInClip.translate(
                    origin, destination).rotate(destination, rotation)
                newId: str = associatedPerception.getId()
                newPoint: shapely.Point = newSample.getPoint()
                newRegion: shapely.Polygon = associatedPerception.getRegion()
                newRegion = Geometric.rotateAboutShapely( # type: ignore[assignment]
                    Geometric.translateOD(newRegion, origin, destination),
                    destination,
                    rotation
                )
                newIds.append(newId)
                newPoints.append(newPoint)
                newRegions.append(newRegion)
                newSamples.append(newSample)
            generated.append((
                queryPerception,
                destination,
                rotation,
                tuple(generatedPolygons),
                queryAchieved,
                buildings
            ))
            leftoverPolygons.extend(remainingPolygons)
            achieved = achieved.accumulate(queryAchieved)
        leftoverPolygons = Geometric.geometryToPolygons(
            shapely.union_all(leftoverPolygons))
        newSiteCollection = siteCollection.update(
            newIds,
            newPoints,
            newRegions,
            newSamples
        )
        newTarget = target.subtract(achieved)
        return (generated, leftoverPolygons, newSiteCollection, newTarget)
    
    def findGenerators(self,
        polygon: shapely.Polygon,
        siteCollection: Collection,
        target: Attributes
    ) -> list[tuple[Perception, shapely.Polygon, Attributes]]:
        generators: list[tuple[
            Perception,
            shapely.Polygon,
            Attributes
        ]] = list()
        sitePerceptions: list[Perception] = siteCollection.getPerceptions()
        perceptionsGdf: geopandas.GeoDataFrame = geopandas.GeoDataFrame(
            data={"perception": sitePerceptions},
            geometry=[perception.getPoint() for perception in sitePerceptions]
        )
        perceptionsGdf["distToPolygon"] = perceptionsGdf["geometry"].distance(
            polygon)
        perceptionsGdf = perceptionsGdf.drop(
            perceptionsGdf.loc[
                perceptionsGdf["distToPolygon"] > self.MAX_GEN_DIST].index)
        perceptionsGdf = perceptionsGdf.drop_duplicates(subset="geometry")
        perceptionsGdf["cluster"] = perceptionsGdf["perception"].apply(
            lambda p: p.getCluster())
        cluster_group = perceptionsGdf.groupby("cluster")
        def filterCorePoints(group: pd.DataFrame) -> pd.DataFrame:
            X: list[tuple[float, float]] = [
                (point.x, point.y)
                for point in group["geometry"]]
            dbscan: cluster.DBSCAN = cluster.DBSCAN(eps=self.EPS, min_samples=1)
            dbscan.fit(X)
            group["label"] = dbscan.labels_
            core = group.groupby("label")
            def getCore(group: pd.DataFrame) -> pd.DataFrame:
                points: pd.Series = group["geometry"]
                xs: list[float] = [point.x for point in points]
                ys: list[float] = [point.y for point in points]
                centroid: shapely.Point = shapely.Point(
                    sum(xs) / len(xs),
                    sum(ys) / len(ys)
                )
                group["distance"] = group["geometry"].distance(centroid)
                group = group.sort_values("distance", axis=0)
                group = group.drop(columns="distance")
                return group.head(1)
            return core.apply(
                getCore, include_groups=False).reset_index(level=0)
        perceptionsGdf = cluster_group.apply(
            filterCorePoints, include_groups=False).reset_index(level=0)
        perceptionPoints: list[tuple[Perception, shapely.Point]] = list()
        for index, row in perceptionsGdf.iterrows():
            perceptionPoints.append((row["perception"], row["geometry"]))
        if len(perceptionPoints) <= 1:
            return [
                (perceptionPoint[0], polygon, target)
                for perceptionPoint in perceptionPoints]
        voronoiPolygons: list[shapely.Polygon] = Geometric.voronoiPolygons(
            [perceptionPoint[1] for perceptionPoint in perceptionPoints],
            extendTo=polygon
        )
        totalArea: float = polygon.area
        i: int
        for i in range(len(perceptionPoints)):
            perception: Perception = perceptionPoints[i][0]
            voronoiPolygon: shapely.Polygon = voronoiPolygons[i]
            sitePolygons: list[shapely.Polygon] = Geometric.geometryToPolygons(
                shapely.intersection(voronoiPolygon, polygon))
            sitePolygon: shapely.Polygon
            for sitePolygon in sitePolygons:
                if sitePolygon.is_empty:
                    continue
                ratio: float = sitePolygon.area / totalArea
                siteTarget: Attributes = target.ratio(ratio)
                generators.append((perception, sitePolygon, siteTarget))
        return generators