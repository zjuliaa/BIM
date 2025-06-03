import ifcopenshell
import ifcopenshell.geom
import numpy as np
import os
import matplotlib.pyplot as plt
from scipy.spatial import ConvexHull
import trimesh

def get_room_geometry(space):
    try:
        settings = ifcopenshell.geom.settings()
        shape = ifcopenshell.geom.create_shape(settings, space)
        verts = shape.geometry.verts
        points = np.array(verts).reshape(-1, 3)

        name = space.LongName or space.Name or "Nieznana nazwa"
        # print(f"Geometria pomieszczenia: {name}")
        # for i, point in enumerate(points):
        #     print(f"  Punkt {i+1}: x={point[0]:.2f}, y={point[1]:.2f}, z={point[2]:.2f}")
        # print()

    except Exception as e:
        print(f"Błąd podczas pobierania geometrii dla {space.LongName or space.Name}: {e}")


def get_room_dimensions(space):
    
    try:
        settings = ifcopenshell.geom.settings()
        shape = ifcopenshell.geom.create_shape(settings, space)
        verts = shape.geometry.verts
        points = np.array(verts).reshape(-1, 3)

        min_x, max_x = np.min(points[:, 0]), np.max(points[:, 0])
        min_y, max_y = np.min(points[:, 1]), np.max(points[:, 1])
        min_z, max_z = np.min(points[:, 2]), np.max(points[:, 2])

        length = max_x - min_x
        width = max_y - min_y
        height = max_z - min_z

        name = space.LongName or space.Name or "Nieznana nazwa"
        print(f"Pomieszczenie: {name}")
        print(f"  - Długość: {length:.2f} m")
        print(f"  - Szerokość: {width:.2f} m")
        print(f"  - Wysokość: {height:.2f} m\n")

    except Exception as e:
        print(f"Błąd w pomieszczeniu {space.LongName or space.Name}: {e}")

def wypisz_kondygnacje_i_pomieszczenia_z_wymiarami(model):
    kondygnacje = model.by_type("IfcBuildingStorey")

    for kond in kondygnacje:
        print(f"Kondygnacja: {kond.Name}")
        znalezione = []

        if hasattr(kond, "IsDecomposedBy"):
            for rel in kond.IsDecomposedBy:
                for elem in rel.RelatedObjects:
                    if elem.is_a("IfcSpace"):
                        znalezione.append(elem)

        if znalezione:
            print("  Pomieszczenia:")
            for pom in znalezione:
                nazwa = pom.LongName or pom.Name
                print(f"    - {nazwa}")
                get_room_dimensions(pom)
                get_room_geometry(pom)
        else:
            print("  Brak pomieszczeń na tej kondygnacji.\n")



def rysuj_obrys_pomieszczen_na_kondygnacjach(model):
    kondygnacje = model.by_type("IfcBuildingStorey")

    for kond in kondygnacje:
        fig, ax = plt.subplots()
        ax.set_title(f"Obrysy pomieszczeń – {kond.Name}")
        ax.set_aspect("equal")

        znalezione = []

        if hasattr(kond, "IsDecomposedBy"):
            for rel in kond.IsDecomposedBy:
                for elem in rel.RelatedObjects:
                    if elem.is_a("IfcSpace"):
                        znalezione.append(elem)
        if not znalezione:
            print(f"Brak pomieszczeń na kondygnacji {kond.Name}")
            continue
        for space in znalezione:
            try:
                settings = ifcopenshell.geom.settings()
                shape = ifcopenshell.geom.create_shape(settings, space)
                verts = shape.geometry.verts
                points = np.array(verts).reshape(-1, 3)

                # Rzut na XY
                xy_points = points[:, :2]

                # Obrys wypukły (Convex Hull)
                hull = ConvexHull(xy_points)
                polygon = xy_points[hull.vertices]

                name = space.LongName or space.Name or "?"
                ax.fill(*zip(*polygon), alpha=0.5, label=name)

            except Exception as e:
                print(f"Błąd geometrii w pomieszczeniu {space.Name}: {e}")

        ax.legend()
        plt.xlabel("X [m]")
        plt.ylabel("Y [m]")
        plt.grid(True)
        plt.show()



def calculate_volume_from_shape(shape, scale=1.0):
    try:
        verts = np.array(shape.geometry.verts).reshape(-1, 3)
        faces = shape.geometry.faces

        i = 0
        face_list = []

        while i < len(faces):
            n = faces[i]
            i += 1
            indices = faces[i:i+n]
            i += n

            if len(indices) >= 3:
                for j in range(1, len(indices) - 1):
                    face_list.append([indices[0], indices[j], indices[j + 1]])

        mesh = trimesh.Trimesh(vertices=verts, faces=face_list, process=True)

        mesh.fix_normals()

        if not mesh.is_watertight or not mesh.is_winding_consistent:
            print("⚠️ Niepoprawna siatka – używam bbox")
            return mesh.bounding_box_oriented.volume * (scale ** 3)

        return abs(mesh.volume) * (scale ** 3)
    except Exception as e:
        print(f"❗ Błąd siatki: {e}")
        return 0.0



def calculate_building_volume(ifc_path):
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    ifc_file = ifcopenshell.open(ifc_path)

    spaces = ifc_file.by_type("IfcSpace")
    total_volume = 0.0
    processed = 0

    for space in spaces:
        try:
            shape = ifcopenshell.geom.create_shape(settings, space)
            vol = calculate_volume_from_shape(shape)
            print(f"🧱 {space.LongName or space.Name or space.GlobalId} — objętość: {vol:.2f} m³")
            total_volume += vol
            processed += 1
        except Exception as e:
            print(f"❗ Błąd geometrii {space.LongName or space.GlobalId}: {e}")

    print(f"\n✅ Obliczono objętość dla {processed} pomieszczeń.")
    print(f"📦 Szacunkowa kubatura budynku: {total_volume:.2f} m³")
    return total_volume


if __name__ == "__main__":
    ifc_file_path = r"C:\sem6\BIM\Dom_jednorodzinny.ifc"
    # ifc_file_path = r"C:\sem6\BIM\Galeria_arch.ifc"
    if not os.path.exists(ifc_file_path):
        print(f"Plik IFC nie istnieje: {ifc_file_path}")
    else:
        model = ifcopenshell.open(ifc_file_path)
        wypisz_kondygnacje_i_pomieszczenia_z_wymiarami(model)
        rysuj_obrys_pomieszczen_na_kondygnacjach(model)
        total_volume = calculate_building_volume(ifc_file_path)
        print(f"📦 Szacunkowa kubatura budynku: {total_volume:.2f} m³")