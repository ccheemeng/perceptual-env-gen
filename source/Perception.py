from shapely import Polygon

from .Sample import Sample

from collections.abc import Collection

class Perception:
    def __init__(self, sample: Sample, radius: float,
                 samples: Collection[Sample]) -> None:
        self.id: str = sample.getId()
        self.sample: Sample = sample
        self.radius: float = radius
        self.samples: list[Sample] = list(samples)
        self.sampleMap: dict[int, tuple[Sample, ...]] =\
            Perception.mapSamples(samples)

    def __repr__(self) -> str:
        return (
            f"{self.sample.__repr__()}: "
            f"r={self.radius}, {len(self.samples)} samples"
        )
    
    @staticmethod
    def mapSamples(samples: Collection[Sample]) ->\
        dict[int, tuple[Sample, ...]]:
        sampleMap: dict[int, list[Sample]] = dict()
        sample: Sample
        for sample in samples:
            if not sample.getCluster() in sampleMap:
                sampleMap[sample.getCluster()] = []
            sampleMap[sample.getCluster()].append(sample)
        sampleImMap: dict[int, tuple[Sample, ...]] = dict()
        cluster: int
        for cluster in sampleMap:
            sampleImMap[cluster] = tuple(sampleMap[cluster])
        return sampleImMap
    
    def getSamples(self) -> list[Sample]:
        return self.samples
    
    def within(self, polygon: Polygon) -> bool:
        return self.sample.within(polygon)