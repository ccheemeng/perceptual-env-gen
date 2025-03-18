from geopandas import GeoDataFrame # type: ignore
from pandas import concat, DataFrame, Series
from shapely import Point, Polygon

from .Sample import Sample
from .Perception import Perception

from typing import Self
from random import Random

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