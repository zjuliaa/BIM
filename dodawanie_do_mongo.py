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
        # print(f"Błąd geometrii {space.Name or space.GlobalId}: {e}")
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
            # print(f"Błąd obrysu {space.Name}: {e}")
            pass

    ax.legend()
    plt.xlabel("X [m]")
    plt.ylabel("Y [m]")
    plt.grid(True)
    plt.show()

# def calculate_volume(shape, scale=1.0):
#     try:
#         verts = np.array(shape.geometry.verts).reshape(-1, 3)
#         faces = shape.geometry.faces

#         face_list = []
#         i = 0
#         while i < len(faces):
#             n = faces[i]
#             indices = faces[i+1:i+1+n]
#             face_list += [[indices[0], indices[j], indices[j+1]] for j in range(1, n-1)]
#             i += n + 1

#         mesh = trimesh.Trimesh(vertices=verts, faces=face_list, process=True)
#         mesh.fix_normals()

#         if not mesh.is_watertight or not mesh.is_winding_consistent:
#             print("Niepoprawna siatka – używam bbox")
#             return mesh.bounding_box_oriented.volume * (scale ** 3)

#         return mesh.volume * (scale ** 3)
#     except Exception as e:
#         print(f"Błąd siatki: {e}")
#         return 0.0

def calculate_volume(shape, scale=1.0):
    try:
        verts = np.array(shape.geometry.verts).reshape(-1, 3)
        faces_raw = shape.geometry.faces

        face_list = []
        i = 0
        while i < len(faces_raw):
            n = faces_raw[i]
            indices = faces_raw[i + 1:i + 1 + n]

            # Zabezpieczenie przed błędną liczbą wierzchołków
            if len(indices) < 3:
                # print(f"Pominięto ścianę z mniej niż 3 wierzchołkami: {indices}")
                i += n + 1
                continue

            # Triangulacja wielokąta (fan triangulation)
            for j in range(1, n - 1):
                try:
                    face_list.append([indices[0], indices[j], indices[j + 1]])
                except IndexError as e:
                    # print(f"Błąd triangulacji przy indeksach {indices}: {e}")
                    pass
            i += n + 1

        mesh = trimesh.Trimesh(vertices=verts, faces=face_list, process=True)

        if not mesh.is_watertight or not mesh.is_volume:
            # print("Niepoprawna siatka – używam bbox")
            return mesh.bounding_box_oriented.volume * (scale ** 3)

        return mesh.volume * (scale ** 3)

    except Exception as e:
        # print(f"❌ Błąd siatki: {e}")
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
            # print(f"  Pomieszczenie: {space.LongName or space.Name or space.GlobalId} - przybliżona powierzchnia: {area:.2f} m²")
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

    # print(f"\n Szacunkowa kubatura budynku: {total_volume:.2f} m³")
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
            # print(f"⚠️ Pomijam nieobsługiwany typ: {etype}")
            pass
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

    # print("🔄 Buforuję geometrię elementów...")
    geometria_elem = buforuj_geometrie(model, settings, element_types)

    for space in model.by_type("IfcSpace"):
        name = space.LongName or space.Name or space.GlobalId
        # print(f"\n📦 Pomieszczenie: {name}")

        elementy = znajdz_elementy_w_pomieszczeniu(space, geometria_elem, settings)

        if not elementy:
            # print("  Brak wykrytych elementów wewnątrz.")
            pass
        else:
            for etype, ename in elementy:
                print(f"  - {etype}: {ename}")


def get_shape_points(ifc_entity, settings):
    try:
        shape = ifcopenshell.geom.create_shape(settings, ifc_entity)
        verts = np.array(shape.geometry.verts).reshape(-1, 3)
        return verts, shape
    except Exception as e:
        # print(f"⚠️ Błąd generowania geometrii: {e}")
        return None, None

# nowe z geometria
def extract_room_data(space, storey_name, settings, geometria_elem):
    points, shape = get_shape_points(space, settings)
    if points is None or shape is None:
        return None

    area = approximate_floor_area_from_shape(space, settings)
    volume = calculate_volume(shape)
    length, width, height = get_room_dimensions(points)
    elements = znajdz_elementy_w_pomieszczeniu(space, geometria_elem, settings)

    # 2D geometry (Convex Hull)
    floor_z = np.min(points[:, 2])
    floor_points = points[np.abs(points[:, 2] - floor_z) < 0.1]
    outline = []
    if len(floor_points) >= 3:
        try:
            xy_points = floor_points[:, :2]
            hull = ConvexHull(xy_points)
            outline = xy_points[hull.vertices].tolist()
        except Exception as e:
            # print(f"⚠️ Błąd generowania obrysu 2D: {e}")
            pass

    # 3D geometry (vertices + triangle faces)
    geometry3d = {"vertices": [], "faces": []}
    try:
        verts = np.array(shape.geometry.verts).reshape(-1, 3)
        faces_raw = shape.geometry.faces

        face_list = []
        i = 0
        while i < len(faces_raw):
            n = faces_raw[i]
            indices = faces_raw[i + 1:i + 1 + n]

            # Fan triangulation
            for j in range(1, n - 1):
                try:
                    face_list.append([int(indices[0]), int(indices[j]), int(indices[j + 1])])
                except IndexError:
                    continue
            i += n + 1

        geometry3d["vertices"] = verts.round(3).tolist()
        geometry3d["faces"] = face_list

    except Exception as e:
        # print(f"❌ Błąd przetwarzania geometrii 3D: {e}")
        pass

    return {
        "roomId": space.GlobalId,
        "name": space.LongName or space.Name or "Nieznana",
        "storey": storey_name,
        "dimensions": {
            "length": round(float(length), 2),
            "width": round(float(width), 2),
            "height": round(float(height), 2),
            "area": round(area, 2),
            "volume": round(volume, 2)
        },
        "elements": [{"type": etype, "name": ename} for etype, ename in elements],
        "geometry2D": {
            "outline": [[round(float(x), 2), round(float(y), 2)] for x, y in outline]
        },
        "geometry3D": geometry3d
    }


def export_all_rooms(model):
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)

    element_types = ["IfcWall", "IfcWallStandardCase", "IfcDoor", "IfcWindow", "IfcCovering", "IfcFlowTerminal"]
    geometria_elem = buforuj_geometrie(model, settings, element_types)

    all_rooms = []
    storeys = model.by_type("IfcBuildingStorey")
    for i, storey in enumerate(storeys):
        storey_name = storey.Name
        storey_number = i
        spaces = [
            obj for rel in getattr(storey, "IsDecomposedBy", [])
            for obj in getattr(rel, "RelatedObjects", [])
            if obj.is_a("IfcSpace")
        ]
        print("\n📋 Lista wszystkich pomieszczeń przed filtrowaniem:")
        for space in spaces:
            # predefined_type = getattr(space, "PredefinedType", None)
            # name = (space.LongName or space.Name or "").lower()
            # print(f"📦 Pomieszczenie: {name} | Typ: {predefined_type}")
            # # Dodaj warunek debugowania
            # if predefined_type:
            #     print(f"⛔ Pomieszczenie: {name} | Typ: {predefined_type}")

            # # Filtruj znane nieużyteczne typy lub słowa kluczowe
            # nieuzytkowe_typy = ["CIRCULATIONSPACE", "EXTERNAL", "VOID", "NOTDEFINED", "OTHER"]
            # nieuzytkowe_slowa = [ "corridor", "lobby", "shaft", "void", "stairs", "technical", "cirrculation", "instruction"]

            # if (predefined_type and predefined_type.upper() in nieuzytkowe_typy) or any(s in name for s in nieuzytkowe_slowa):
            #     print(f"⚠️ Pomijam: {name} ({predefined_type})")
            #     continue

            room_data = extract_room_data(space, storey_name, settings, geometria_elem)
            if room_data:
                room_data["storeyNumber"] = storey_number
                all_rooms.append(room_data)

    return all_rooms

from pymongo import MongoClient

def save_to_mongodb(data, mongo_uri, db_name="ifc_db", collection_name="rooms"):
    try:
        client = MongoClient(mongo_uri)
        db = client[db_name]
        collection = db[collection_name]
        collection.delete_many({})

        # Wstaw nowe
        collection.insert_many(data)
        print(f"Zapisano {len(data)} pomieszczeń do MongoDB.")
    except Exception as e:
        print(f"Błąd podczas zapisu do MongoDB: {e}")





if __name__ == "__main__":
    # ifc_path = r"C:\sem6\BIM\Dom_jednorodzinny.ifc"
    ifc_path = r"C:\sem6\BIM\Galeria_arch.ifc"
    if not os.path.exists(ifc_path):
        print(f" Brak pliku IFC: {ifc_path}")
    else:
        model = ifcopenshell.open(ifc_path)
        data=export_all_rooms(model)
        # print(data)
        mongo_uri="mongodb+srv://uzytkownik1:scpuXTRs6vB6kByI@budynek.kb5uuax.mongodb.net/"
        save_to_mongodb(data, mongo_uri)