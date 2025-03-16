from geopandas import GeoDataFrame # type: ignore
from pandas import concat, DataFrame, Series
from shapely import Point, Polygon

from .Sample import Sample
from .Perception import Perception

from typing import Self

class Collection:
    RADIUS: float = 100

    def __init__(
        self,
        samples: dict[str, Sample], sampleAttributes,
        perceptions: dict[str, Perception], perceptionAttributes: DataFrame
    ) -> None:
        self.samples: dict[str, Sample] = samples
        self.sampleAttributes: DataFrame = sampleAttributes
        self.perceptions: dict[str, Perception] = perceptions
        self.perceptionAttributes: DataFrame = perceptionAttributes

    @classmethod
    def fromGeoDataFrame(cls, gdf: GeoDataFrame, radius: float = RADIUS) -> Self:
        samples: dict[str, Sample] = Collection.initSamples(gdf, radius)
        sampleAttributes: DataFrame = gdf.drop("geometry", axis=1)
        perceptions: dict[str, Perception] =\
            Collection.initPerceptions(gdf, samples, radius)
        perceptionAttributes: DataFrame =\
            Collection.initPerceptionAttributes(sampleAttributes, perceptions)
        return cls(samples, sampleAttributes, perceptions, perceptionAttributes)

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
        gdf: GeoDataFrame, samples: dict[str, Sample], radius: float
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
            perceptions[id] = Perception(sample, radius, sampleList)
        return perceptions

    @staticmethod
    def initPerceptionAttributes(
        sampleAttributes: DataFrame,
        perceptions: dict[str, Perception]
    ) -> DataFrame:
        return concat((
            sampleAttributes.apply(
                lambda row: sampleAttributes.loc[
                    sampleAttributes.index.isin([
                        sample.getId() for sample in perceptions[row.name]\
                            .getSamples()
                    ])
                ].drop("cluster", axis=1).sum(axis=0), axis=1
            ),
            sampleAttributes["cluster"]
        ), axis=1)
    
    def perceptionsWithin(self, polygon: Polygon) -> dict[str, Perception]:
        id: str
        perception: Perception
        return {id: perception for id, perception in self.perceptions.items() if perception.within(polygon)}