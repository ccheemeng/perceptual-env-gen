from shapely import Geometry, GeometryCollection, LineString, LinearRing,\
    MultiLineString, MultiPoint, MultiPolygon, Point, Polygon

from collections.abc import Sequence
from math import cos, sin

class Geometric:
    @staticmethod
    def geometryToPolygons(geometry: Geometry) -> list[Polygon]:
        if isinstance(geometry, Polygon):
            return [geometry]
        if isinstance(geometry, MultiPolygon):
            return list(geometry.geoms)
        if isinstance(geometry, GeometryCollection):
            newPolygons: list[Polygon] = list()
            for geom in geometry.geoms:
                newPolygons.extend(Geometric.geometryToPolygons(geom))
            return newPolygons
        return list()
    
    @staticmethod
    def translate(geometry: object, originOrVector: object, destination: object = None) -> object:
        if destination == None:
            return Geometric.translateVector(geometry, originOrVector)
        return Geometric.translateOD(geometry, originOrVector, destination)
    
    @staticmethod
    def translateVector(geometry: object, vector: object) -> object:
        if isinstance(vector, Point):
            return Geometric.translateVectorTuple(geometry, (vector.x, vector.y))
        if isinstance(vector, Sequence):
            Geometric.checkSequence2Float(vector)
            return Geometric.translateVectorTuple(geometry, (vector[0], vector[1]))
        raise ValueError(f"Vector {vector} must be Point or tuple[float, float]!")
        
    @staticmethod
    def translateOD(geometry: object, origin: object, destination: object) -> object:
        if isinstance(origin, Point) and isinstance(destination, Point):
            return Geometric.translateVectorTuple(geometry, (destination.x - origin.x, destination.y - origin.y))
        if isinstance(origin, Point) and isinstance(destination, Sequence):
            Geometric.checkSequence2Float(destination)
            return Geometric.translateVectorTuple(geometry, (destination[0] - origin.x, destination[1] - origin.y))
        if isinstance(origin, Sequence) and isinstance(destination, Point):
            Geometric.checkSequence2Float(origin)
            return Geometric.translateVectorTuple(geometry, (destination.x - origin[0], destination.y - origin[1]))
        if isinstance(origin, Sequence) and isinstance(destination, Sequence):
            Geometric.checkSequence2Float(origin)
            Geometric.checkSequence2Float(destination)
            return Geometric.translateVectorTuple(geometry, (destination[0] - origin[0], destination[1] - origin[1]))
        raise ValueError(f"Origin {origin} and destination {destination} must be Point or tuple[float, float]!")
    
    @staticmethod
    def translateVectorTuple(geometry: object, vector: tuple[float, float]) -> object:
        if isinstance(geometry, Point):
            return Geometric.translatePoint(geometry, vector)
        if isinstance(geometry, LineString):
            raise NotImplementedError("LineString not implemented!")
        if isinstance(geometry, LinearRing):
            raise NotImplementedError("LinearRing not implemented!")
        if isinstance(geometry, Polygon):
            return Geometric.translatePolygon(geometry, vector)
        if isinstance(geometry, MultiPoint):
            raise NotImplementedError("MultiPoint not implemented!")
        if isinstance(geometry, MultiLineString):
            raise NotImplementedError("MultiLineString not implemented!")
        if isinstance(geometry, MultiPolygon):
            raise NotImplementedError("MultiPolygon not implemented!")
        if isinstance(geometry, GeometryCollection):
            raise NotImplementedError("GeometryCollection not implemented!")
        if isinstance(geometry, Sequence):
            Geometric.checkSequence2Float(geometry)
            return Geometric.translateTuple((geometry[0], geometry[1]), vector)
        raise ValueError(f"Geometry {geometry} not supported!")
        
    @staticmethod
    def translatePoint(geometry: Point, vector: tuple[float, float]) -> Point:
        return Point(Geometric.translateTuple((geometry.x, geometry.y), vector))
    
    @staticmethod
    def translatePolygon(geometry: Polygon, vector: tuple[float, float]) -> Polygon:
        exterior: list[Point] = [Geometric.translatePoint(Point(point), vector) for point in geometry.exterior.coords]
        interiors: list[list[Point]] = [[Geometric.translatePoint(Point(point), vector) for point in interior.coords] for interior in geometry.interiors]
        return Polygon(shell=exterior, holes=interiors)
    
    @staticmethod
    def translateTuple(geometry: tuple[float, float], vector: tuple[float, float]) -> tuple[float, float]:
        return (geometry[0] + vector[0], geometry[1] + vector[1])

    @staticmethod
    def rotate(geometry: object, origin: object, rotation: float) -> object:
        if isinstance(origin, Point):
            return Geometric.rotateAboutShapely(geometry, origin, rotation)
        if isinstance(origin, Sequence):
            Geometric.checkSequence2Float(origin)
            originTuple: tuple[float, float] = (origin[0], origin[1])
            return Geometric.rotateAboutTuple(geometry, originTuple, rotation)
        raise ValueError(f"Invalid origin {origin}!")
    
    @staticmethod
    def rotateAboutShapely(geometry: object, origin: Point, rotation: float) -> object:
        originTuple: tuple[float, float] = (origin.x, origin.y)
        return Geometric.rotateAboutTuple(geometry, originTuple, rotation)
    
    @staticmethod
    def rotateAboutTuple(geometry: object, origin: tuple[float, float], rotation: float) -> object:
        if isinstance(geometry, Point):
            return Geometric.rotatePoint(geometry, origin, rotation)
        if isinstance(geometry, LineString):
            raise NotImplementedError("LineString not implemented!")
        if isinstance(geometry, LinearRing):
            raise NotImplementedError("LinearRing not implemented!")
        if isinstance(geometry, Polygon):
            return Geometric.rotatePolygon(geometry, origin, rotation)
        if isinstance(geometry, MultiPoint):
            raise NotImplementedError("MultiPoint not implemented!")
        if isinstance(geometry, MultiLineString):
            raise NotImplementedError("MultiLineString not implemented!")
        if isinstance(geometry, MultiPolygon):
            raise NotImplementedError("MultiPolygon not implemented!")
        if isinstance(geometry, GeometryCollection):
            raise NotImplementedError("GeometryCollection not implemented!")
        if isinstance(geometry, Sequence):
            Geometric.checkSequence2Float(geometry)
            return Geometric.rotateTuple((geometry[0], geometry[1]), origin, rotation)
        raise ValueError(f"Geometry {geometry} not supported!")
    
    @staticmethod
    def rotatePoint(geometry: Point, origin: tuple[float, float], rotation: float) -> Point:
        return Point(Geometric.rotateTuple((geometry.x, geometry.y), origin, rotation))
    
    @staticmethod
    def rotatePolygon(geometry: Polygon, origin: tuple[float, float], rotation: float) -> Polygon:
        exterior: list[Point] = [Geometric.rotatePoint(Point(point), origin, rotation) for point in geometry.exterior.coords]
        interiors: list[list[Point]] = [[Geometric.rotatePoint(Point(point), origin, rotation) for point in interior.coords] for interior in geometry.interiors]
        return Polygon(shell=exterior, holes=interiors)
    
    @staticmethod
    def rotateTuple(geometry: tuple[float, float], origin: tuple[float, float], rotation: float) -> tuple[float, float]:
        x0: float = geometry[0] - origin[0]
        y0: float = geometry[1] - origin[1]
        xRot: float = x0 * cos(rotation) - y0 * sin(rotation)
        yRot: float = x0 * sin(rotation) + y0 * cos(rotation)
        xNew: float = xRot + origin[0]
        yNew: float = yRot + origin[1]
        return (xNew, yNew)
    
    @staticmethod
    def checkSequence2Float(sequence: Sequence[object]) -> None:
        x: object
        for x in sequence:
            try:
                float(x) # type: ignore[arg-type]
            except:
                raise ValueError(f"{x} in {sequence} must be float or castable to float!")
        if len(sequence) < 2:
            raise ValueError(f"{sequence} must have 2 values!")