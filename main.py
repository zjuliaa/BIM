import ifcopenshell
import ifcopenshell.geom
import math
from scipy.spatial import ConvexHull
import numpy as np

def calculate_area_from_shape(shape):
    verts = shape.geometry.verts
    faces = shape.geometry.faces
    area = 0.0
    i = 0
    while i < len(faces):
        n = faces[i]  
        i += 1
        if n == 3:
            idx0, idx1, idx2 = faces[i], faces[i+1], faces[i+2]
            i += 3
            x0, y0 = verts[3*idx0], verts[3*idx0+1]
            x1, y1 = verts[3*idx1], verts[3*idx1+1]
            x2, y2 = verts[3*idx2], verts[3*idx2+1]
            a = (x1 - x0)*(y2 - y0) - (x2 - x0)*(y1 - y0)
            area += abs(a) / 2.0
        else:
            i += n

    return area

def get_area_from_property_sets(space):
    if not hasattr(space, "IsDefinedBy") or not space.IsDefinedBy:
        return None
    for rel in space.IsDefinedBy:
        if rel.is_a("IfcRelDefinesByProperties"):
            prop_set = rel.RelatingPropertyDefinition
            if prop_set.is_a("IfcPropertySet"):
                for prop in prop_set.HasProperties:
                    if prop.Name in ("GrossFloorArea", "NetFloorArea", "Area"):
                        try:
                            return float(prop.NominalValue.wrappedValue)
                        except:
                            pass
    return None

def extract_building_properties(ifc_path):
    settings = ifcopenshell.geom.settings()
    ifc_file = ifcopenshell.open(ifc_path)
    buildings = ifc_file.by_type("IfcBuilding")
    print(f"Znaleziono {len(buildings)} budynków")
    spaces = ifc_file.by_type("IfcSpace")
    print(f"Znaleziono {len(spaces)} przestrzeni (pomieszczeń)")
    if buildings:
        building = buildings[0]
        name = building.Name if building.Name else "Brak nazwy budynku"
    else:
        name = "Brak danych"
    total_area = 0.0
    for space in spaces:
        area = get_area_from_property_sets(space)
        if area:
            print(f"{space.LongName} - powierzchnia z Pset: {area} m²")
            total_area += area
    return settings, spaces, name, total_area

def approximate_floor_area_from_shape(shape):
    verts = shape.geometry.verts
    points = np.array(verts).reshape(-1,3)
    floor_z = np.min(points[:,2])
    floor_points = points[np.abs(points[:,2] - floor_z) < 0.1]
    if len(floor_points) < 3:
        return 0.0
    xy_points = floor_points[:, :2]
    hull = ConvexHull(xy_points)
    return hull.volume  

if __name__ == "__main__":
    ifc_file_path = "modele/dom_jednorodzinny.ifc"
    settings, spaces, name,  area = extract_building_properties(ifc_file_path)
    print(f"Budynek: {name}")

    total_geom_area = 0.0
    for space in spaces:
        try:
            shape = ifcopenshell.geom.create_shape(settings, space)
            area = approximate_floor_area_from_shape(shape)
            print(f"Pomieszczenie {space.LongName} - przybliżona powierzchnia: {area:.2f} m²")
            total_geom_area += area
        except Exception as e:
            print(f"Błąd dla {space.LongName}: {e}")

    print(f"Całkowita przybliżona powierzchnia (z geometrii): {total_geom_area:.2f} m²")
