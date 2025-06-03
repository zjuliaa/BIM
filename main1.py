import tkinter as tk
from tkinter import ttk
from db1 import get_storeys, get_rooms_by_storey

root = tk.Tk()
root.title("Przeglądarka budynku")

# Dropdown pięter
storey_var = tk.StringVar()
storey_menu = ttk.Combobox(root, textvariable=storey_var)
storeys = get_storeys()
storey_menu["values"] = storeys
storey_menu.pack()
loaded_rooms = []
# Lista pokojów
room_list = tk.Listbox(root)
room_list.pack()

# Canvas (na przyszłość - do rysowania)
canvas = tk.Canvas(root, width=600, height=400, bg="white")
canvas.pack()

room_polygons = {}  # globalny słownik: roomId -> canvas polygon id

def draw_floor():
    canvas.delete("all")
    room_polygons.clear()
    for i, room in enumerate(loaded_rooms):
        outline = room.get("geometry2D", {}).get("outline", [])
        if outline:
            scale = 5
            offset_x = 200
            offset_y = 200
            scaled_points = [(x * scale + offset_x, -y * scale + offset_y) for x, y in outline]
            poly_id = canvas.create_polygon(scaled_points, fill="lightgray", outline="black")
            room_polygons[poly_id] = i  # zapamiętaj indeks pokoju pod id rysunku


def load_rooms(event):
    global loaded_rooms
    try:
        storey = int(storey_var.get())
    except ValueError:
        return

    loaded_rooms = get_rooms_by_storey(storey)
    room_list.delete(0, tk.END)
    for room in loaded_rooms:
        room_list.insert(tk.END, room.get("name", "Brak nazwy"))

    draw_floor()

    
def draw_room(event):
    selection = room_list.curselection()
    if not selection:
        return
    index = selection[0]
    if index >= len(loaded_rooms):
        return

    room = loaded_rooms[index]

    draw_floor()  # rysuj wszystkie pokoje

    # Podświetl wybrany
    outline = room.get("geometry2D", {}).get("outline", [])
    if outline:
        scale = 5
        offset_x = 200
        offset_y = 200
        scaled_points = [(x * scale + offset_x, -y * scale + offset_y) for x, y in outline]
        canvas.create_polygon(scaled_points, fill="lightblue", outline="darkblue", width=2)

    dims = room.get("dimensions", {})
    info = f"Nazwa: {room.get('name', 'Brak')}\nPowierzchnia: {dims.get('area', 'Brak')} m²\nObjętość: {dims.get('volume', 'Brak')} m³"

    canvas.create_text(10, 10, anchor="nw", text=info, fill="black", font=("Arial", 12))

def on_canvas_click(event):
    clicked = canvas.find_withtag("current") 

    if clicked:
        poly_id = clicked[0]
        if poly_id in room_polygons:
            index = room_polygons[poly_id]
            # Zaznacz pokój w liście:
            room_list.selection_clear(0, tk.END)
            room_list.selection_set(index)
            room_list.see(index)  # przewiń do pokoju
            draw_room(None)  # odśwież podświetlenie i info

canvas.bind("<Button-1>", on_canvas_click)
back_button = tk.Button(root, text="Wróć do widoku piętra", command=lambda: draw_floor())
back_button.pack(pady=5)

storey_menu.bind("<<ComboboxSelected>>", load_rooms)
room_list.bind("<<ListboxSelect>>", draw_room)
root.mainloop()
