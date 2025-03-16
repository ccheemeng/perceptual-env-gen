from shapely import Polygon

from .Perception import Perception
from .Collection import Collection

class Simulator:
    GENERATION_DISTANCE: float = 50

    def __init__(self, collection: Collection):
        self.collection = collection

    def run(self, polygon: Polygon) -> None:
        generatorPerceptions: dict[str, Perception] = self.collection\
            .perceptionsWithin(polygon.buffer(self.GENERATION_DISTANCE))
        print(generatorPerceptions.keys())
        return