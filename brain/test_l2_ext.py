import requests

BASE = "http://localhost:3000/execute"

def call(req_id, tool, payload):
    r = requests.post(BASE, json={"request_id": req_id, "tool": tool, "payload": payload})
    return r.json()

# Try door on L2 exterior south wall (5948406)
d = call("d_l2ext", "revit.place_door", {
    "wall_id": 5948406,
    "location": {"x": 26, "y": 0, "z": 11},
    "family_name": "Door-Interior-Single-1_Panel-Wood",
    "type_name": '30" x 96"'
})
print("Door on L2 EXT:", d["Status"], d.get("Result") or d.get("Message"))

# Try window on L2 interior wall (5948450)
d = call("w_l2int", "revit.place_window", {
    "wall_id": 5948450,
    "location": {"x": 26, "y": 10, "z": 14},
    "family_name": "Fixed",
    "type_name": "0915 x 1220mm"
})
print("Window on L2 INT:", d["Status"], d.get("Result") or d.get("Message"))
