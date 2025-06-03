from pymongo import MongoClient


mongo_uri = "mongodb+srv://uzytkownik1:scpuXTRs6vB6kByI@budynek.kb5uuax.mongodb.net/"
nazwa_bazy="ifc_db"
kolekcja="rooms"
client = MongoClient(mongo_uri)
db = client[nazwa_bazy]
collection = db[kolekcja]

def get_storeys():
    return sorted(db.rooms.distinct("storeyNumber"))

def get_rooms_by_storey(storey_number: int):
    query = {"storeyNumber": storey_number}
    projection = {
        "_id": 0,
        "roomId": 1,
        "name": 1,
        "storey": 1,
        "dimensions.area": 1,
        "dimensions.volume": 1,
        "dimensions.height": 1,
        "dimensions.width": 1,
        "dimensions.length": 1,
        "geometry2D": 1
    }
    return list(collection.find(query, projection))
