import requests

BASE = "http://localhost:3000/execute"

def place_door(req_id, wall_id, x, y, z, family, type_name):
    r = requests.post(BASE, json={
        "request_id": req_id,
        "tool": "revit.place_door",
        "payload": {
            "wall_id": wall_id,
            "location": {"x": x, "y": y, "z": z},
            "family_name": family,
            "type_name": type_name
        }
    })
    d = r.json()
    status = d.get("Status","?")
    result = d.get("Result") or {}
    msg = d.get("Message","")
    print(f"{req_id}: {status} {result.get('door_id','') if status=='ok' else msg}")

# Try z=0 for L2 doors (Revit may interpret location relative to level)
place_door("d_b2_z0",    5948422, 10, 10, 0,  "Door-Interior-Single-1_Panel-Wood", '30" x 96"')
