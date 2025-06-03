import ifcopenshell
import ifcopenshell.geom
import numpy as np
import os
import matplotlib.pyplot as plt
from scipy.spatial import ConvexHull
import trimesh



def approximate_floor_area_from_shape(space, settings):
    """Oblicza przybliżoną powierzchni powierzchni danego IfcSpace."""
    shape = ifcopenshell.geom.create_shape(settings, space)
    verts = shape.geometry.verts
    points = np.array(verts).reshape(-1,3)
    floor_z = np.min(points[:,2])
    floor_points = points[np.abs(points[:,2] - floor_z) < 0.1]
    if len(floor_points) < 3:
        return 0.0
    xy_points = floor_points[:, :2]
    hull = ConvexHull(xy_points)
    return hull.volume  

def get_shape_points(space, settings=None):
    """Zwraca punkty geometrii danego IfcSpace."""
    try:
        if settings is None:
            settings = ifcopenshell.geom.settings()
            settings.set(settings.USE_WORLD_COORDS, True)
        shape = ifcopenshell.geom.create_shape(settings, space)
        verts = np.array(shape.geometry.verts).reshape(-1, 3)
        return verts, shape
    except Exception as e:
        print(f"Błąd geometrii {space.Name or space.GlobalId}: {e}")
        return None, None

def get_room_dimensions(points):
    """Zwraca długość, szerokość i wysokość z punktów geometrii."""
    min_vals = points.min(axis=0)
    max_vals = points.max(axis=0)
    return tuple(max_vals - min_vals)

def print_room_info(space, points):
    """Drukuje nazwę pomieszczenia i jego wymiary."""
    name = space.LongName or space.Name or "Nieznana nazwa"
    length, width, height = get_room_dimensions(points)
    print(f"Pomieszczenie: {name}")
    print(f"  - Długość: {length:.2f} m\n  - Szerokość: {width:.2f} m\n  - Wysokość: {height:.2f} m\n")

def rysuj_obrys_pomieszczen(kondygnacja, spaces, settings):
    fig, ax = plt.subplots()
    ax.set_title(f"Obrysy pomieszczeń – {kondygnacja.Name}")
    ax.set_aspect("equal")

    for space in spaces:
        points, _ = get_shape_points(space, settings)
        if points is None: continue

        xy = points[:, :2]
        try:
            hull = ConvexHull(xy)
            polygon = xy[hull.vertices]
            ax.fill(*zip(*polygon), alpha=0.5, label=space.LongName or space.Name or "?")
        except Exception as e:
            print(f"Błąd obrysu {space.Name}: {e}")

    ax.legend()
    plt.xlabel("X [m]")
    plt.ylabel("Y [m]")
    plt.grid(True)
    plt.show()

def calculate_volume(shape, scale=1.0):
    try:
        verts = np.array(shape.geometry.verts).reshape(-1, 3)
        faces = shape.geometry.faces

        face_list = []
        i = 0
        while i < len(faces):
            n = faces[i]
            indices = faces[i+1:i+1+n]
            face_list += [[indices[0], indices[j], indices[j+1]] for j in range(1, n-1)]
            i += n + 1

        mesh = trimesh.Trimesh(vertices=verts, faces=face_list, process=True)
        mesh.fix_normals()

        if not mesh.is_watertight or not mesh.is_winding_consistent:
            print("Niepoprawna siatka – używam bbox")
            return mesh.bounding_box_oriented.volume * (scale ** 3)

        return mesh.volume * (scale ** 3)
    except Exception as e:
        print(f"Błąd siatki: {e}")
        return 0.0

def process_storeys(model):
    settings = ifcopenshell.geom.settings()
    # settings.set(settings.USE_WORLD_COORDS, True)

    for storey in model.by_type("IfcBuildingStorey"):
        print(f"Kondygnacja: {storey.Name}")
        spaces = [
            obj for rel in getattr(storey, "IsDecomposedBy", [])
            for obj in getattr(rel, "RelatedObjects", [])
            if obj.is_a("IfcSpace")
        ]

        if not spaces:
            print("  Brak pomieszczeń.")
            continue

        for space in spaces:
            points, _ = get_shape_points(space, settings)
            area=approximate_floor_area_from_shape(space, settings)
            print(f"  Pomieszczenie: {space.LongName or space.Name or space.GlobalId} - przybliżona powierzchnia: {area:.2f} m²")
            if points is not None:
                print_room_info(space, points)

        rysuj_obrys_pomieszczen(storey, spaces, settings)

def calculate_total_volume(model):
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)

    total_volume = 0.0
    for space in model.by_type("IfcSpace"):
        _, shape = get_shape_points(space, settings)
        if shape is not None:
            vol = calculate_volume(shape)
            print(f" {space.LongName or space.Name or space.GlobalId} — objętość: {vol:.2f} m³")
            total_volume += vol

    print(f"\n Szacunkowa kubatura budynku: {total_volume:.2f} m³")
    return total_volume



def buforuj_geometrie(model, settings, element_types):
    geometria = {}
    for etype in element_types:
        try:
            for elem in model.by_type(etype):
                try:
                    verts, _ = get_shape_points(elem, settings)
                    if verts is not None:
                        geometria[elem.GlobalId] = (etype, elem.Name or elem.GlobalId, verts)
                except Exception as e:
                    print(f"Błąd geometrii {etype}: {e}")
        except RuntimeError:
            print(f"⚠️ Pomijam nieobsługiwany typ: {etype}")
    return geometria


def znajdz_elementy_w_pomieszczeniu(space, geometria_elem, settings):
    verts, _ = get_shape_points(space, settings)
    if verts is None:
        return []

    bbox_min = verts.min(axis=0)
    bbox_max = verts.max(axis=0)
    bbox = np.array([bbox_min, bbox_max])

    znalezione = []
    for gid, (etype, ename, elem_verts) in geometria_elem.items():
        centroid = elem_verts.mean(axis=0)
        if np.all(centroid >= bbox[0]) and np.all(centroid <= bbox[1]):
            znalezione.append((etype, ename))
    return znalezione


def wypisz_elementy_pomieszczen(model):
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)

    element_types = ["IfcWall", "IfcWallStandardCase", "IfcDoor", "IfcWindow", "IfcCovering", "IfcFlowTerminal"]

    print("🔄 Buforuję geometrię elementów...")
    geometria_elem = buforuj_geometrie(model, settings, element_types)

    for space in model.by_type("IfcSpace"):
        name = space.LongName or space.Name or space.GlobalId
        print(f"\n📦 Pomieszczenie: {name}")

        elementy = znajdz_elementy_w_pomieszczeniu(space, geometria_elem, settings)

        if not elementy:
            print("  Brak wykrytych elementów wewnątrz.")
        else:
            for etype, ename in elementy:
                print(f"  - {etype}: {ename}")


def get_shape_points(ifc_entity, settings):
    try:
        shape = ifcopenshell.geom.create_shape(settings, ifc_entity)
        verts = np.array(shape.geometry.verts).reshape(-1, 3)
        return verts, shape
    except Exception as e:
        print(f"⚠️ Błąd generowania geometrii: {e}")
        return None, None


if __name__ == "__main__":
    ifc_path = r"C:\sem6\BIM\Dom_jednorodzinny.ifc"
    if not os.path.exists(ifc_path):
        print(f" Brak pliku IFC: {ifc_path}")
    else:
        model = ifcopenshell.open(ifc_path)


        process_storeys(model)
        # calculate_total_volume(model)
        # wypisz_elementy_pomieszczen(model)