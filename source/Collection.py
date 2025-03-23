from geopandas import GeoDataFrame # type: ignore[import-untyped]
from pandas import concat, DataFrame, Series
from shapely import Point, Polygon, STRTree

from .Sample import Sample
from .Perception import Perception

import time
from typing import Hashable, Self, Union

class Collection:
    RADIUS: float = 100

    def __init__(self, samples: dict[str, Sample],
                 perceptions: dict[str, Perception]) -> None:
        self.samples: dict[str, Sample] = samples
        self.perceptions: dict[str, Perception] = perceptions

    @classmethod
    def fromPointsRegionsClusters(
        cls, pointsGdf: GeoDataFrame,
        regionsGdf: GeoDataFrame, clusters: dict[str, int]
    ) -> Self:
        samples: dict[str, Sample] = Collection.initSamples(pointsGdf, clusters)
        perceptions: dict[str, Perception] =\
            Collection.initPerceptions(samples, pointsGdf, regionsGdf)
        return cls(samples, perceptions)

    @staticmethod
    def initSamples(pointsGdf: GeoDataFrame, clusters: dict[str, int])\
    -> dict[str, Sample]:
        samples: dict[str, Sample] = dict()
        index: str
        row: Series
        for index, row in pointsGdf.iterrows():
            point: Point = row["geometry"]
            cluster: int = clusters[index]
            samples[index] = Sample(index, point, cluster)
        return samples

    @staticmethod
    def initPerceptions(
        samples: dict[str, Sample],
        pointsGdf: GeoDataFrame,
        regionsGdf: GeoDataFrame
    ) -> dict[str, Perception]:
        perceptions: dict[str, Perception] = dict()
        pointsGdf.sindex
        id: str
        sample: Sample
        for id, sample in samples.items():
            region: Polygon = regionsGdf.iloc[id]
            sampleList: list[Sample] = [
                samples[i] for i in pointsGdf.iloc[
                    pointsGdf.sindex.query(region, predicate="intersects")
                ].index
            ]
            perceptions[id] = Perception(sample, region, sampleList)
        return perceptions
    
    # can be optimised, now it recreates all samples and perceptions regardless of if they are modified
    def update(self, generated: list[tuple[Perception, Perception, float, Polygon]], queryCollection: Self) -> Self:
        newSamples: dict[str, Sample] = self.samples.copy()
        newRegions: dict[str, Polygon] = {id: polygon for id, polygon in self.perceptions.items()}
        generation: tuple[Perception, Perception, float, Polygon]
        for generation in generated:
            origin: Point = generation[0].getPoint()
            destination: Point = generation[1].getPoint()
            translation: tuple[float, float] = (destination.x - origin.x, destination.y - origin.y)
            rotation: float = generation[2]
            rotTransSamples: list[Sample] = [sample
                                            .translate(translation)
                                            .rotate((destination.x, destination.y), rotation)\
                                        for sample in generation[0].getSamples()]
            rotTransSamplePoints: list[Point] = [sample.getPoint for sample in rotTransSamples]
            strTree: STRTree = STRTree(rotTransSamplePoints)
            query: list[int] = list(strTree.query(generation[3], predicate="intersects"))
            filteredSamples: list[Sample] = list()
            i: int
            for i in query:
                filteredSamples.append(rotTransSamples[i])
            filteredRegions: list[Polygon] = list()
            for sample in filteredSamples:
                region: Polygon = queryCollection.getPerception(sample.getId()).getRegion()
                region = Collection.translate(region).rotate(region)
                filteredRegions.append(region)
            for sample in filteredSamples:
    
    def getPerceptions(self) -> dict[str, Perception]:
        return self.perceptions

    def perceptionsWithin(self, polygon: Polygon) -> dict[str, Perception]:
        id: str
        perception: Perception
        return {id: perception for id, perception in self.perceptions.items()
                if perception.within(polygon)}
    
    def getPerception(self, perceptionId: str) -> Perception:
        return self.perceptions[perceptionId]
    
    def findSimilar(self, query: Perception, limit: int = 1) -> Union[tuple[Perception, float], list[tuple[Perception, float]]]:
        start = time.time()
        perceptionDistances: dict[str, tuple[float, float]] =\
            {id: Collection.calculateDistance(perception, query) for id, perception in self.perceptions.items()}
        end = time.time()
        print(f"{query} query took {end - start} seconds")
        # perceptionDistances: dict[str, tuple[float, float]] =\
        #     {id: (0, 0) for id, perception in self.perceptions.items()} # ARBITRARY RETURN FOR FAST TESTING
        perceptionDf: DataFrame = DataFrame.from_dict(perceptionDistances, orient="index", columns=["distance", "rotation"]).sort_values("distance", axis=0).head(limit)
        similar: list[tuple[Perception, float]] = list()
        i: int = 0
        index: Hashable
        row: Series
        for index, row in perceptionDf.iterrows():
            assert(isinstance(index, str))
            if i >= limit:
                break
            similar.append((self.perceptions[index], row["rotation"]))
        if limit == 1:
            return similar[0]
        return similar
    
    @staticmethod
    def calculateDistance(p1: Perception, p2: Perception) -> tuple[float, float]:
        rotation: float = Perception.rotation(p1, p2)
        distance: float = Perception.distance(p1, p2, rotation)
        return (distance, rotation)