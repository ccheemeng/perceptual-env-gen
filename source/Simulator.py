from shapely import MultiPoint, Point, Polygon, difference, intersection, voronoi_polygons

from .Collection import Collection
from .Geometric import Geometric
from .Perception import Perception
from .Sample import Sample

from queue import Queue

class Simulator:
    MAX_GEN_DIST: float = 40

    def __init__(self, queryCollection: Collection, max_gen_dist: float = MAX_GEN_DIST):
        self.queryCollection: Collection = queryCollection
        self.max_gen_dist: float = max_gen_dist

    def run(self, site: Polygon, siteCollection: Collection) -> list[tuple[Perception, Point, float, Polygon]]:
        polygonQueue: Queue[Polygon] = Queue()
        polygonQueue.put(site)
        # list[tuple[queryPerception, destination, rotation, generatedPolygon]]
        generation: list[tuple[Perception, Point, float, Polygon]] = list()
        while not polygonQueue.empty():
            print(f"Generating for {polygon}")
            polygon: Polygon = polygonQueue.get()
            generated: list[tuple[Perception, Point, float, Polygon]]
            remainingPolygons: list[Polygon]
            newCollection: Collection
            generated, remainingPolygons, newCollection = self.generate(polygon, siteCollection)
            generation.extend(generated)
            remainingPolygon: Polygon
            for remainingPolygon in remainingPolygons:
                if not remainingPolygon.is_empty:
                    polygonQueue.put(remainingPolygon)
            siteCollection = newCollection
            print("=========================")
        return generation
    
    def generate(self, polygon: Polygon, siteCollection: Collection) -> tuple[list[tuple[Perception, Point, float, Polygon]], list[Polygon], Collection]:
        generators: list[tuple[Perception, Polygon]] = self.findGenerators(polygon, siteCollection)
        querySamplesAdded: set[Sample] = set()
        newIds: list[str] = list()
        newPoints: list[Point] = list()
        newRegions: list[Polygon] = list()
        newSamples: list[Sample] = list()
        generated: list[tuple[Perception, Point, float, Polygon]] = list()
        leftoverPolygons: list[Polygon] = list()
        generator: tuple[Perception, Polygon]
        for generator in generators:
            sitePerception: Perception = generator[0]
            generatingPolygon: Polygon = generator[1]
            distance: float
            queryPerception: Perception
            rotation: float
            distance, queryPerception, rotation = self.queryCollection.findSimilar(sitePerception)
            origin: Point = queryPerception.getPoint()
            destination: Point = sitePerception.getPoint()
            generatedPolygon: Polygon = Geometric.rotate(Geometric.translate(queryPerception.getRegion(), origin, destination), destination, rotation) # type: ignore[assignment]
            generatedPolygon = intersection(generatedPolygon, generatingPolygon) # type: ignore[assignment]
            assert(isinstance(generatedPolygon, Polygon))
            if generatedPolygon.is_empty:
                leftoverPolygons.append(generatingPolygon)
                continue
            remainingPolygons: list[Polygon] = Geometric.geometryToPolygons(difference(generatingPolygon, generatedPolygon))
            remainingPolygons = list(filter(lambda p: not p.is_empty, remainingPolygons))
            clippingPolygon: Polygon = Geometric.translate(Geometric.rotate(generatedPolygon, destination, -rotation), destination, origin) # type: ignore[assignment]
            samplesInClip: list[Sample] = self.queryCollection.samplesInPolygon(clippingPolygon)
            samplesInClip = list(filter(lambda s: not s in querySamplesAdded, samplesInClip))
            querySamplesAdded.update(samplesInClip)
            sampleInClip: Sample
            for sampleInClip in samplesInClip:
                associatedPerception: Perception = self.queryCollection.perceptionFromSample(sampleInClip)
                newSample = sampleInClip.translate(origin, destination).rotate(destination, rotation)
                newId: str = associatedPerception.getId()
                newPoint: Point = newSample.getPoint()
                newRegion: Polygon = associatedPerception.getRegion()
                newRegion = Geometric.rotate(Geometric.translate(newRegion, origin, destination), destination, rotation) # type: ignore[assignment]
                newIds.append(newId)
                newPoints.append(newPoint)
                newRegions.append(newRegion)
                newSamples.append(newSample)
            generated.append((queryPerception, destination, rotation, generatedPolygon))
            leftoverPolygons.extend(remainingPolygons)
        newSiteCollection = siteCollection.update(newIds, newPoints, newRegions, newSamples)
        return (generated, leftoverPolygons, newSiteCollection)
    
    def findGenerators(self, polygon: Polygon, siteCollection: Collection) -> list[tuple[Perception, Polygon]]:
        generators: list[tuple[Perception, Polygon]] = list()
        sitePerceptions: list[Perception] = siteCollection.getPerceptions()
        perceptionPoints: list[tuple[Perception, Point]] = list()
        sitePerception: Perception
        for sitePerception in sitePerceptions:
            perceptionPoint: Point = sitePerception.getPoint()
            distanceToPolygon: float = perceptionPoint.distance(polygon)
            if distanceToPolygon <= self.max_gen_dist:
                perceptionPoints.append((sitePerception, perceptionPoint))
        voronoiPolygons: list[Polygon] = Geometric.geometryToPolygons(voronoi_polygons(MultiPoint([dpp[1] for dpp in perceptionPoints]), extend_to=polygon))
        assert len(voronoiPolygons) == len(perceptionPoints), "No 1:1 mapping between site points and site voronoi polygons!"
        i: int
        for i in range(len(perceptionPoints)):
            perception: Perception = perceptionPoints[i][0]
            voronoiPolygon: Polygon = voronoiPolygons[i]
            sitePolygons: list[Polygon] = Geometric.geometryToPolygons(intersection(voronoiPolygon, polygon))
            sitePolygon: Polygon
            for sitePolygon in sitePolygons:
                if sitePolygon.is_empty:
                    continue
                generators.append((perception, sitePolygon))
        return generators