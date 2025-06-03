import ifcopenshell
import ifcopenshell.geom
import math
from scipy.spatial import ConvexHull
import numpy as np
import matplotlib.pyplot as plt


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

def extract_building_overview(ifc_path):
    ifc_file = ifcopenshell.open(ifc_path)

    # Działka (IfcSite)
    sites = ifc_file.by_type("IfcSite")
    if sites:
        site = sites[0]
        site_name = site.Name or "Brak nazwy"
        site_latitude = getattr(site.RefLatitude, 'wrappedValue', site.RefLatitude if hasattr(site, "RefLatitude") else None)
        site_longitude = getattr(site.RefLongitude, 'wrappedValue', site.RefLongitude if hasattr(site, "RefLongitude") else None)
        print("📍 Informacje o działce:")
        print(f"  - Nazwa: {site_name}")
        print(f"  - Szerokość geograficzna: {site_latitude}")
        print(f"  - Długość geograficzna: {site_longitude}")
    else:
        print("❗ Brak danych o działce (IfcSite)")

    # Budynek
    buildings = ifc_file.by_type("IfcBuilding")
    if buildings:
        building = buildings[0]
        building_name = building.Name or "Brak nazwy budynku"
        print(f"\n🏢 Budynek: {building_name}")
    else:
        print("❗ Brak danych o budynku")
        return

    # Kondygnacje
    storeys = ifc_file.by_type("IfcBuildingStorey")
    print(f"  - Liczba kondygnacji: {len(storeys)}")

    # Pomieszczenia
    spaces = ifc_file.by_type("IfcSpace")
    print(f"  - Liczba pomieszczeń: {len(spaces)}")

    # Drzwi
    doors = ifc_file.by_type("IfcDoor")
    print(f"  - Liczba drzwi: {len(doors)}")

    # Okna
    windows = ifc_file.by_type("IfcWindow")
    print(f"  - Liczba okien: {len(windows)}")

def get_room_dimensions(space, settings):
    try:
        shape = ifcopenshell.geom.create_shape(settings, space)
        verts = shape.geometry.verts
        points = np.array(verts).reshape(-1, 3)

        # Zakresy w osiach X, Y, Z
        min_x, max_x = np.min(points[:, 0]), np.max(points[:, 0])
        min_y, max_y = np.min(points[:, 1]), np.max(points[:, 1])
        min_z, max_z = np.min(points[:, 2]), np.max(points[:, 2])

        length = max_x - min_x
        width = max_y - min_y
        height = max_z - min_z

        name = space.LongName or space.Name or "Nieznana nazwa"
        print(f"📏 Pomieszczenie: {name}")
        print(f"  - Długość: {length:.2f} m")
        print(f"  - Szerokość: {width:.2f} m")
        print(f"  - Wysokość: {height:.2f} m\n")

    except Exception as e:
        print(f"❗ Błąd w pomieszczeniu {space.LongName}: {e}")

if __name__ == "__main__":
    ifc_file_path = "C:\sem6\BIM\Dom_jednorodzinny.ifc"
    extract_building_overview(ifc_file_path)
    settings, spaces, name,  area = extract_building_properties(ifc_file_path)
    print(f"Budynek: {name}")

    total_geom_area = 0.0
    for space in spaces:
        try:
            get_room_dimensions(space, settings)
            shape = ifcopenshell.geom.create_shape(settings, space)
            area = approximate_floor_area_from_shape(shape)
            print(f"Pomieszczenie {space.LongName} - przybliżona powierzchnia: {area:.2f} m²")
            total_geom_area += area
        except Exception as e:
            print(f"Błąd dla {space.LongName}: {e}")

    print(f"Całkowita przybliżona powierzchnia (z geometrii): {total_geom_area:.2f} m²")
