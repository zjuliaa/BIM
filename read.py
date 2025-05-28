
import ifcopenshell
import ifcopenshell.geom
import numpy as np
from scipy.spatial import ConvexHull
from pymongo import MongoClient

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

def main():
    # Połącz z MongoDB Atlas (podmień na swój connection string)
    client = MongoClient("mongodb+srv://uzytkownik1:scpuXTRs6vB6kByI@budynek.kb5uuax.mongodb.net/")
    db = client["ifc_db"]
    collection = db["spaces"]

    ifc_file_path = "modele/dom_jednorodzinny.ifc"
    settings = ifcopenshell.geom.settings()
    ifc_file = ifcopenshell.open(ifc_file_path)
    spaces = ifc_file.by_type("IfcSpace")

    # Usuń stare dane (opcjonalnie)
    collection.delete_many({})

    for space in spaces:
        # Zbierz podstawowe info
        space_doc = {
            "global_id": space.GlobalId,
            "name": space.Name,
            "long_name": getattr(space, "LongName", None),
            "description": space.Description,
            "properties": {},
            "area_from_pset": None,
            "area_from_geom": None
        }

        space_doc["area_from_pset"] = get_area_from_property_sets(space)

        try:
            shape = ifcopenshell.geom.create_shape(settings, space)
            area_geom = approximate_floor_area_from_shape(shape)
            space_doc["area_from_geom"] = area_geom
        except Exception as e:
            space_doc["geom_error"] = str(e)

        if hasattr(space, "IsDefinedBy"):
            for rel in space.IsDefinedBy:
                if rel.is_a("IfcRelDefinesByProperties"):
                    prop_set = rel.RelatingPropertyDefinition
                    if prop_set.is_a("IfcPropertySet"):
                        pset_name = prop_set.Name
                        space_doc["properties"][pset_name] = {}
                        for prop in prop_set.HasProperties:
                            val = getattr(prop, "NominalValue", None)
                            if val:
                                space_doc["properties"][pset_name][prop.Name] = val.wrappedValue

        collection.insert_one(space_doc)
        print(f"Wstawiono dane pomieszczenia: {space_doc['name']}")

    print("Import zakończony!")

if __name__ == "__main__":
    main()
