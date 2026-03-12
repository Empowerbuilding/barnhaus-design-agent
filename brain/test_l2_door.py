import requests

BASE = "http://localhost:3000/execute"

def call(req_id, tool, payload):
    r = requests.post(BASE, json={"request_id": req_id, "tool": tool, "payload": payload})
    return r.json()

# Delete L2 hallway south wall
d = call("del_l2", "revit.delete_element", {"element_id": 5948422})
print("Delete:", d["Status"])

# Recreate it
d = call("mk_l2", "revit.create_wall", {
    "start_point": {"x": 0, "y": 10, "z": 10},
    "end_point":   {"x": 52, "y": 10, "z": 10},
    "height": 10, "level": "Level 2.0", "wall_type": 'Wall 4.5 Interior"'
})
wid = d["Result"]["wall_id"]
print("New wall:", wid)

# Immediately place door
d = call("d_test", "revit.place_door", {
    "wall_id": wid,
    "location": {"x": 10, "y": 10, "z": 11},
    "family_name": "Door-Interior-Single-1_Panel-Wood",
    "type_name": '30" x 96"'
})
print("Door:", d["Status"], d.get("Result") or d.get("Message"))
