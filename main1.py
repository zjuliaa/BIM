import tkinter as tk
from tkinter import ttk
from db1 import get_storeys, get_rooms_by_storey
import random

root = tk.Tk()
root.title("Przeglądarka budynku")
root.geometry("1000x600")
root.minsize(1200, 500)
root.columnconfigure(0, weight=1)
root.columnconfigure(1, weight=3)
root.rowconfigure(1, weight=1)
top_frame = ttk.Frame(root, padding=(10,10))
top_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
top_frame.columnconfigure(0, weight=1)
storey_var = tk.StringVar()
storey_menu = ttk.Combobox(top_frame, textvariable=storey_var, state="readonly", font=("Segoe UI", 11))
storeys = get_storeys()
storey_menu["values"] = storeys
storey_menu.grid(row=0, column=0, sticky="ew")
back_button = ttk.Button(top_frame, text="Wróć do widoku piętra", command=lambda: reset_selection_and_draw())
back_button.grid(row=0, column=1, padx=10)
list_frame = ttk.Frame(root, padding=(10,10))
list_frame.grid(row=1, column=0, sticky="nsew")
list_frame.rowconfigure(0, weight=1)
list_frame.columnconfigure(0, weight=1)
room_list = tk.Listbox(list_frame, font=("Segoe UI", 10), activestyle='dotbox', selectbackground="#0078D7", selectforeground="white")
room_list.grid(row=0, column=0, sticky="nsew")
scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=room_list.yview)
scrollbar.grid(row=0, column=1, sticky="ns")
room_list.config(yscrollcommand=scrollbar.set)
canvas = tk.Canvas(root, bg="white", highlightthickness=1, highlightbackground="gray")
canvas.grid(row=1, column=1, sticky="nsew", padx=(0,10), pady=10)

loaded_rooms = []
room_polygons = {}
room_polygons = {}  
room_colors = {}  
selected_room_index = None

def random_color():
    base = 150
    r = random.randint(base, 255)
    g = random.randint(base, 255)
    b = random.randint(base, 255)
    return f'#{r:02x}{g:02x}{b:02x}'

def reset_selection_and_draw():
    global selected_room_index
    selected_room_index = None
    draw_floor()


def draw_floor():
    global room_colors
    canvas.delete("all")
    room_polygons.clear()

    scale = 6
    offset_x = 300
    offset_y = 300
    if not room_colors or len(room_colors) != len(loaded_rooms):
        room_colors = {i: random_color() for i in range(len(loaded_rooms))}
    circulation_rooms = []
    secondary_rooms = []
    normal_rooms = []
    for room in loaded_rooms:
        name = room.get("name", "").lower()
        if "cirrculation" in name:
            circulation_rooms.append(room)
        elif any(x in name for x in ["service", "instruction", "administration"]):
            secondary_rooms.append(room)
        else:
            normal_rooms.append(room)

    def draw_room_poly(room, fill_color):
        idx = loaded_rooms.index(room)
        outline = room.get("geometry2D", {}).get("outline", [])
        if outline:
            scaled = [(x * scale + offset_x, -y * scale + offset_y) for x, y in outline]
            poly_id = canvas.create_polygon(scaled, fill=fill_color, outline="")
            room_polygons[poly_id] = idx

    for room in circulation_rooms:
        idx = loaded_rooms.index(room)
        fill_color = room_colors.get(idx, "#dddddd")
        draw_room_poly(room, fill_color)
    for room in secondary_rooms:
        idx = loaded_rooms.index(room)
        fill_color = room_colors.get(idx, "#e0e0e0")
        draw_room_poly(room, fill_color)
    for room in normal_rooms:
        idx = loaded_rooms.index(room)
        fill_color = room_colors.get(idx, "lightgray")
        draw_room_poly(room, fill_color)
    if selected_room_index is not None and 0 <= selected_room_index < len(loaded_rooms):
        room = loaded_rooms[selected_room_index]
        outline = room.get("geometry2D", {}).get("outline", [])
        if outline:
            scaled = [(x * scale + offset_x, -y * scale + offset_y) for x, y in outline]
            fill_color = room_colors.get(selected_room_index, "lightblue")
            canvas.create_polygon(scaled, fill=fill_color, outline="darkblue", width=3)

def load_rooms(event):
    global loaded_rooms, selected_room_index
    selected_room_index = None  

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
    global selected_room_index
    selection = room_list.curselection()
    if not selection:
        return
    index = selection[0]
    if index >= len(loaded_rooms):
        return
    selected_room_index = index
    draw_floor()
    room = loaded_rooms[index]
    dims = room.get("dimensions", {})
    info = (
        f"Nazwa: {room.get('name', 'Brak')}\n"
        f"Powierzchnia: {dims.get('area', 'Brak')} m²\n"
        f"Objętość: {dims.get('volume', 'Brak')} m³\n"
        f"Długość: {dims.get('length', 'Brak')} m\n"
        f"Szerokość: {dims.get('width', 'Brak')} m\n"
        f"Wysokość: {dims.get('height', 'Brak')} m"
    )
    canvas.create_text(10, 10, anchor="nw", text=info, fill="black", font=("Helvetica", 12))


def on_canvas_click(event):
    global selected_room_index
    clicked = canvas.find_withtag("current")
    if clicked:
        poly_id = clicked[0]
        if poly_id in room_polygons:
            selected_room_index = room_polygons[poly_id]
            room_list.selection_clear(0, tk.END)
            room_list.selection_set(selected_room_index)
            room_list.see(selected_room_index)
            draw_floor()
            draw_room(None)

canvas.bind("<Button-1>", on_canvas_click)
storey_menu.bind("<<ComboboxSelected>>", load_rooms)
room_list.bind("<<ListboxSelect>>", draw_room)

if storeys:
    storey_var.set(storeys[0])
    load_rooms(None)

root.mainloop()
