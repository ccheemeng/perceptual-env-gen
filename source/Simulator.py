from shapely import Geometry, MultiPoint, MultiPolygon, Point, Polygon, difference, intersection, union_all, voronoi_polygons

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

    def run(self, site: Polygon, siteCollection: Collection) -> list[tuple[Perception, Point, float, tuple[Polygon, ...]]]:
        polygonQueue: Queue[Polygon] = Queue()
        polygonQueue.put(site)
        # list[tuple[queryPerception, destination, rotation, generatedPolygon]]
        generation: list[tuple[Perception, Point, float, tuple[Polygon, ...]]] = list()
        while not polygonQueue.empty():
            polygon: Polygon = polygonQueue.get()
            print(f"Generating for {polygon.__repr__()}")
            print(f"{polygonQueue.qsize()} left in queue")
            generated: list[tuple[Perception, Point, float, tuple[Polygon, ...]]]
            remainingPolygons: list[Polygon]
            newCollection: Collection
            generated, remainingPolygons, newCollection = self.generate(polygon, siteCollection)
            generation.extend(generated)
            remainingPolygon: Polygon
            for remainingPolygon in remainingPolygons:
                if not remainingPolygon.is_empty:
                    polygonQueue.put(remainingPolygon)
                    print(f"{remainingPolygon.__repr__()} put in queue")
            siteCollection = newCollection
            print("=========================")
        return generation
    
    def generate(self, polygon: Polygon, siteCollection: Collection) -> tuple[list[tuple[Perception, Point, float, tuple[Polygon, ...]]], list[Polygon], Collection]:
        generators: list[tuple[Perception, Polygon]] = self.findGenerators(polygon, siteCollection)
        querySamplesAdded: set[Sample] = set()
        newIds: list[str] = list()
        newPoints: list[Point] = list()
        newRegions: list[Polygon] = list()
        newSamples: list[Sample] = list()
        generated: list[tuple[Perception, Point, float, tuple[Polygon, ...]]] = list()
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
            transformedQueryPolygon: Polygon = Geometric.rotate(Geometric.translate(queryPerception.getRegion(), origin, destination), destination, rotation) # type: ignore[assignment]
            generatedPolygon: Geometry = intersection(transformedQueryPolygon, generatingPolygon)
            generatedPolygons: list[Polygon] = Geometric.geometryToPolygons(generatedPolygon)
            generatedPolygons = list(filter(lambda p: not p.is_empty, generatedPolygons))
            if len(generatedPolygons) <= 0:
                leftoverPolygons.append(generatingPolygon)
                continue
            remainingPolygons: list[Polygon] = Geometric.geometryToPolygons(difference(generatingPolygon, MultiPolygon(generatedPolygons)))
            remainingPolygons = list(filter(lambda p: not p.is_empty, remainingPolygons))
            clippingPolygon: list[Polygon] = [Geometric.translate(Geometric.rotate(polygon, destination, -rotation), destination, origin) for polygon in generatedPolygons] # type: ignore[misc]
            sampleSetInClip: set[Sample] = set()
            for polygon in clippingPolygon:
                samples: list[Sample] = self.queryCollection.samplesInPolygon(polygon)
                sampleSetInClip.update(samples)
            samplesInClip: list[Sample] = list(filter(lambda s: not s in querySamplesAdded, sampleSetInClip))
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
            generated.append((queryPerception, destination, rotation, tuple(generatedPolygons)))
            leftoverPolygons.extend(remainingPolygons)
        leftoverPolygons = Geometric.geometryToPolygons(union_all(leftoverPolygons))
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