import ifcopenshell
import ifcopenshell.geom
import numpy as np
import os

def get_shape_points(ifc_entity, settings):
    try:
        shape = ifcopenshell.geom.create_shape(settings, ifc_entity)
        verts = np.array(shape.geometry.verts).reshape(-1, 3)
        return verts, shape
    except Exception as e:
        print(f"⚠️ Błąd generowania geometrii: {e}")
        return None, None

def wypisz_wlasnosci_pset(space):
    if not hasattr(space, "IsDefinedBy"):
        return
    for rel in space.IsDefinedBy:
        pset_candidate = getattr(rel, "RelatingDefinition", None) or getattr(rel, "RelatingPropertyDefinition", None)
        if pset_candidate and pset_candidate.is_a("IfcPropertySet"):
            pset = pset_candidate
            print(f"  PSet: {pset.Name}")
            for prop in pset.HasProperties:
                val = getattr(prop, "NominalValue", None)
                if val is None:
                    val = getattr(prop, "InnerValue", None)
                print(f"    - {prop.Name}: {val}")

def wypisz_materialy_i_wykonczenia(space):
    # Sprawdza relacje HasCoverings (np. podłogi, tynki)
    if not hasattr(space, "HasCoverings"):
        return
    if not space.HasCoverings:
        print("  Brak powiązanych materiałów / wykończeń")
        return
    print("  Materiały / wykończenia powiązane:")
    for covering in space.HasCoverings:
        elem = covering.RelatedCoverings if hasattr(covering, "RelatedCoverings") else None
        # Zazwyczaj to pojedynczy element IfcCovering
        if covering.is_a("IfcRelCoversSpaces"):
            for cover in covering.RelatedCoverings:
                print(f"    - {cover.is_a()}: {cover.Name or cover.GlobalId}")
        else:
            # Fallback
            print(f"    - {covering.is_a()}: {covering.Name or covering.GlobalId}")

def analizuj_pomieszczenie(space):
    print("\n📦 Pomieszczenie:")
    print(f"  GlobalId: {space.GlobalId}")
    print(f"  Name: {space.Name or 'brak nazwy'}")
    print(f"  LongName: {space.LongName or 'brak'}")
    print(f"  Description: {space.Description or 'brak'}")

    if hasattr(space, "IsDefinedBy"):
        for rel in space.IsDefinedBy:
            relating = getattr(rel, "RelatingDefinition", None)
            if relating and relating.is_a("IfcElementQuantity"):
                print("  Quantities:")
                for q in relating.Quantities:
                    val = None
                    if hasattr(q, "AreaValue"):
                        val = q.AreaValue
                    elif hasattr(q, "VolumeValue"):
                        val = q.VolumeValue
                    elif hasattr(q, "LengthValue"):
                        val = q.LengthValue
                    print(f"    - {q.Name}: {val}")

    # Policz drzwi i okna w pomieszczeniu (jeśli są)
    drzwi = 0
    okna = 0
    if hasattr(space, "ContainsElements"):
        for rel in space.ContainsElements:
            for elem in rel.RelatedElements:
                etype = elem.is_a()
                if etype == "IfcDoor":
                    drzwi += 1
                elif etype == "IfcWindow":
                    okna += 1
    print(f"  Liczba drzwi: {drzwi}")
    print(f"  Liczba okien: {okna}")

    # Materiały i wykończenia (np. pokrycia podłóg, ścian)
    wypisz_materialy_i_wykonczenia(space)

    # Własności z PropertySetów
    wypisz_wlasnosci_pset(space)


if __name__ == "__main__":
    ifc_path = r"C:\sem6\BIM\Dom_jednorodzinny.ifc"
    if not os.path.exists(ifc_path):
        print(f"❌ Brak pliku IFC: {ifc_path}")
    else:
        model = ifcopenshell.open(ifc_path)
        for space in model.by_type("IfcSpace"):
            analizuj_pomieszczenie(space)
