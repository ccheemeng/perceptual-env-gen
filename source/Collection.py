from geopandas import GeoDataFrame # type: ignore[import-untyped]
from pandas import concat, DataFrame, Series
from shapely import Point, Polygon

from .Sample import Sample
from .Perception import Perception

from random import Random
import time
from typing import Hashable, Self, Union

class Collection:
    RADIUS: float = 100

    def __init__(
        self, samples: dict[str, Sample],
        perceptions: dict[str, Perception], perceptionAttributes: DataFrame
    ) -> None:
        self.samples: dict[str, Sample] = samples
        self.perceptions: dict[str, Perception] = perceptions
        self.perceptionAttributes: DataFrame = perceptionAttributes

    @classmethod
    def fromGeoDataFrame(cls, gdf: GeoDataFrame,
        radius: float = RADIUS, random: Random = Random(0)) -> Self:
        samples: dict[str, Sample] = Collection.initSamples(gdf, radius)
        perceptions: dict[str, Perception] =\
            Collection.initPerceptions(gdf, samples, radius, random)
        perceptionAttributes: DataFrame = gdf.drop("geometry", axis=1)
        return cls(samples, perceptions, perceptionAttributes)

    @staticmethod
    def initSamples(gdf: GeoDataFrame, radius: float) -> dict[str, Sample]:
        samples: dict[str, Sample] = dict()
        index: str
        row: Series
        for index, row in gdf.iterrows():
            point: Point = row["geometry"]
            cluster: int = row["cluster"]
            samples[index] = Sample(index, Point(point.x, point.y),
                radius, cluster)
        return samples

    @staticmethod
    def initPerceptions(
        gdf: GeoDataFrame, samples: dict[str, Sample], radius: float, random: Random
    ) -> dict[str, Perception]:
        perceptions: dict[str, Perception] = dict()
        gdf.sindex
        id: str
        sample: Sample
        for id, sample in samples.items():
            sampleList: list[Sample] = [
                samples[i] for i in gdf.iloc[gdf.sindex.query(
                    gdf.loc[id, "geometry"].buffer(radius), predicate="contains"
                )].index
            ]
            perceptions[id] = Perception(sample, radius, sampleList, random)
        return perceptions
    
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
        # start = time.time()
        # perceptionDistances: dict[str, tuple[float, float]] =\
        #     {id: Collection.calculateDistance(perception, query) for id, perception in self.perceptions.items()}
        # end = time.time()
        # print(f"{query} query took {end - start} seconds")
        perceptionDistances: dict[str, tuple[float, float]] =\
            {id: (0, 0) for id, perception in self.perceptions.items()} # ARBITRARY RETURN FOR FAST TESTING
        perceptionDf: DataFrame = DataFrame.from_dict(perceptionDistances, orient="index", columns=["distance", "rotation"]).sort_values("distance", axis=0).head(limit)
        similar: list[tuple[Perception, float]] = list()
        i: int = 0
        index: Hashable
        row: Series
        for index, row in perceptionDf.iterrows():
            if i >= limit:
                break
            similar.append((self.perceptions[index], row["rotation"]))
        if limit == 1:
            return similar[0]
        return similar
    
    @staticmethod
    def calculateDistance(p1: Perception, p2: Perception) -> tuple[float, float]:
        start = time.time()
        rotation: float = Perception.rotation(p1, p2)
        distance: float = Perception.distance(p1, p2, rotation)
        end = time.time()
        print(f"distance from {p1} to {p2} took {end - start} seconds")
        return (distance, rotation)