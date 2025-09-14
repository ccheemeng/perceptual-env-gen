import shapely

import math
from typing import Optional, Sequence

class Geometric:
    @staticmethod
    def geometryToPolygons(geometry: shapely.Geometry) -> list[shapely.Polygon]:
        if isinstance(geometry, shapely.Polygon):
            return [geometry]
        if isinstance(geometry, shapely.MultiPolygon):
            return list(geometry.geoms)
        if isinstance(geometry, shapely.GeometryCollection):
            newPolygons: list[shapely.Polygon] = list()
            for geom in geometry.geoms:
                newPolygons.extend(Geometric.geometryToPolygons(geom))
            return newPolygons
        return list()
    
    @staticmethod
    def voronoiPolygons(points: list[shapely.Point],
        extendTo: Optional[shapely.Geometry] = None) -> list[shapely.Polygon]:
        polygons: list[shapely.Polygon] = Geometric.geometryToPolygons(
            shapely.voronoi_polygons(
                shapely.MultiPoint(points), extend_to=extendTo))
        sortedPolygons: list[shapely.Polygon] = list()
        point: shapely.Point
        for point in points:
            polygon: shapely.Polygon
            for polygon in polygons:
                if point.within(polygon):
                    polygons.remove(polygon)
                    sortedPolygons.append(polygon)
                    break
        assert (
            len(sortedPolygons) == len(points)
        ), f"Could not find voronoi for {points.__repr__()}!"
        return sortedPolygons

    @staticmethod
    def translate(geometry: object, originOrVector: object,
        destination: object = None) -> object:
        if destination == None:
            return Geometric.translateVector(geometry, originOrVector)
        return Geometric.translateOD(geometry, originOrVector, destination)
    
    @staticmethod
    def translateVector(geometry: object, vector: object) -> object:
        if isinstance(vector, shapely.Point):
            return Geometric.translateVectorTuple(geometry, (vector.x, vector.y))
        if isinstance(vector, Sequence):
            Geometric.checkSequence2Float(vector)
            return Geometric.translateVectorTuple(
                geometry, (vector[0], vector[1]))
        raise ValueError(
            f"Vector {vector} must be "
            "shapely.Point or tuple[float, float]!")
        
    @staticmethod
    def translateOD(
        geometry: object,
        origin: object,
        destination: object
    ) -> object:
        if (
            isinstance(origin, shapely.Point)
            and isinstance(destination, shapely.Point)
        ):
            return Geometric.translateVectorTuple(
                geometry, (destination.x - origin.x, destination.y - origin.y))
        if (
            isinstance(origin, shapely.Point)
            and isinstance(destination, Sequence)
        ):
            Geometric.checkSequence2Float(destination)
            return Geometric.translateVectorTuple(geometry,
                (destination[0] - origin.x, destination[1] - origin.y))
        if (
            isinstance(origin, Sequence)
            and isinstance(destination, shapely.Point)
        ):
            Geometric.checkSequence2Float(origin)
            return Geometric.translateVectorTuple(geometry,
                (destination.x - origin[0], destination.y - origin[1]))
        if isinstance(origin, Sequence) and isinstance(destination, Sequence):
            Geometric.checkSequence2Float(origin)
            Geometric.checkSequence2Float(destination)
            return Geometric.translateVectorTuple(geometry,
                (destination[0] - origin[0], destination[1] - origin[1]))
        raise ValueError(
            f"Origin {origin} and destination {destination} "
            "must be shapely.Point or tuple[float, float]!")
    
    @staticmethod
    def translateVectorTuple(
        geometry: object,
        vector: tuple[float, float]
    ) -> object:
        if isinstance(geometry, shapely.Point):
            return Geometric.translatePoint(geometry, vector)
        if isinstance(geometry, shapely.LineString):
            raise NotImplementedError("LineString not implemented!")
        if isinstance(geometry, shapely.LinearRing):
            raise NotImplementedError("LinearRing not implemented!")
        if isinstance(geometry, shapely.Polygon):
            return Geometric.translatePolygon(geometry, vector)
        if isinstance(geometry, shapely.MultiPoint):
            raise NotImplementedError("MultiPoint not implemented!")
        if isinstance(geometry, shapely.MultiLineString):
            raise NotImplementedError("MultiLineString not implemented!")
        if isinstance(geometry, shapely.MultiPolygon):
            return shapely.MultiPolygon([
                Geometric.translatePolygon(polygon, vector)
                for polygon in geometry.geoms])
        if isinstance(geometry, shapely.GeometryCollection):
            raise NotImplementedError("GeometryCollection not implemented!")
        if isinstance(geometry, Sequence):
            Geometric.checkSequence2Float(geometry)
            return Geometric.translateTuple((geometry[0], geometry[1]), vector)
        raise ValueError(f"Geometry {geometry} not supported!")
        
    @staticmethod
    def translatePoint(
        geometry: shapely.Point,
        vector: tuple[float, float]
    ) -> shapely.Point:
        return shapely.Point(
            Geometric.translateTuple((geometry.x, geometry.y), vector))
    
    @staticmethod
    def translatePolygon(
        geometry: shapely.Polygon,
        vector: tuple[float, float]
    ) -> shapely.Polygon:
        exterior: list[shapely.Point] = [
            Geometric.translatePoint(shapely.Point(point), vector)
            for point in geometry.exterior.coords]
        interiors: list[list[shapely.Point]] = [
            [
                Geometric.translatePoint(shapely.Point(point), vector)
                for point in interior.coords]
            for interior in geometry.interiors]
        return shapely.Polygon(shell=exterior, holes=interiors)
    
    @staticmethod
    def translateTuple(
        geometry: tuple[float, float],
        vector: tuple[float, float]
    ) -> tuple[float, float]:
        return (geometry[0] + vector[0], geometry[1] + vector[1])

    @staticmethod
    def rotate(geometry: object, origin: object, rotation: float) -> object:
        if isinstance(origin, shapely.Point):
            return Geometric.rotateAboutShapely(geometry, origin, rotation)
        if isinstance(origin, Sequence):
            Geometric.checkSequence2Float(origin)
            originTuple: tuple[float, float] = (origin[0], origin[1])
            return Geometric.rotateAboutTuple(geometry, originTuple, rotation)
        raise ValueError(f"Invalid origin {origin}!")
    
    @staticmethod
    def rotateAboutShapely(
        geometry: object,
        origin: shapely.Point,
        rotation: float
    ) -> object:
        originTuple: tuple[float, float] = (origin.x, origin.y)
        return Geometric.rotateAboutTuple(geometry, originTuple, rotation)
    
    @staticmethod
    def rotateAboutTuple(
        geometry: object,
        origin: tuple[float, float],
        rotation: float
    ) -> object:
        if isinstance(geometry, shapely.Point):
            return Geometric.rotatePoint(geometry, origin, rotation)
        if isinstance(geometry, shapely.LineString):
            raise NotImplementedError("LineString not implemented!")
        if isinstance(geometry, shapely.LinearRing):
            raise NotImplementedError("LinearRing not implemented!")
        if isinstance(geometry, shapely.Polygon):
            return Geometric.rotatePolygon(geometry, origin, rotation)
        if isinstance(geometry, shapely.MultiPoint):
            raise NotImplementedError("MultiPoint not implemented!")
        if isinstance(geometry, shapely.MultiLineString):
            raise NotImplementedError("MultiLineString not implemented!")
        if isinstance(geometry, shapely.MultiPolygon):
            return shapely.MultiPolygon([
                Geometric.rotatePolygon(polygon, origin, rotation)
                for polygon in geometry.geoms])
        if isinstance(geometry, shapely.GeometryCollection):
            raise NotImplementedError("GeometryCollection not implemented!")
        if isinstance(geometry, Sequence):
            Geometric.checkSequence2Float(geometry)
            return Geometric.rotateTuple(
                (geometry[0], geometry[1]), origin, rotation)
        raise ValueError(f"Geometry {geometry} not supported!")
    
    @staticmethod
    def rotatePoint(
        geometry: shapely.Point,
        origin: tuple[float, float],
        rotation: float
    ) -> shapely.Point:
        return shapely.Point(
            Geometric.rotateTuple((geometry.x, geometry.y), origin, rotation))
    
    @staticmethod
    def rotatePolygon(
        geometry: shapely.Polygon,
        origin: tuple[float, float],
        rotation: float
    ) -> shapely.Polygon:
        exterior: list[shapely.Point] = [
            Geometric.rotatePoint(shapely.Point(point), origin, rotation)
            for point in geometry.exterior.coords]
        interiors: list[list[shapely.Point]] = [
            [
                Geometric.rotatePoint(shapely.Point(point), origin, rotation)
                for point in interior.coords]
            for interior in geometry.interiors]
        return shapely.Polygon(shell=exterior, holes=interiors)
    
    @staticmethod
    def rotateTuple(
        geometry: tuple[float, float],
        origin: tuple[float, float],
        rotation: float
    ) -> tuple[float, float]:
        x0: float = geometry[0] - origin[0]
        y0: float = geometry[1] - origin[1]
        xRot: float = x0 * math.cos(rotation) - y0 * math.sin(rotation)
        yRot: float = x0 * math.sin(rotation) + y0 * math.cos(rotation)
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
                raise ValueError(
                    f"{x} in {sequence} must be float or castable to float!")
        if len(sequence) < 2:
            raise ValueError(f"{sequence} must have 2 values!")