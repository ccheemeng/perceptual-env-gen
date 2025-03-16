from shapely import Polygon

from .Perception import Perception
from .Collection import Collection

class Simulator:
    GENERATION_DISTANCE: float = 50

    def __init__(self, queryCollection: Collection, siteCollection):
        self.queryCollection: Collection = queryCollection
        self.siteCollection: Collection = siteCollection

    def run(self, polygon: Polygon) -> None:
        generatorPerceptions: dict[str, Perception] = self.siteCollection\
            .perceptionsWithin(polygon.buffer(self.GENERATION_DISTANCE))
        print(generatorPerceptions.keys())
        return