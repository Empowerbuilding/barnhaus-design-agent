import requests, json, sys

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

# Level 1 doors
place_door("d_mbed",   5948410, 20, 24, 0,  "Door-Interior-Single-1_Panel-Wood", '36" x 96"')
place_door("d_mbath",  5948411,  6, 18, 0,  "Door-Interior-Single-1_Panel-Wood", '32" x 96"')
place_door("d_his",    5948413,  4,  8, 0,  "Door-Interior-Single-1_Panel-Wood", '30" x 96"')
place_door("d_hers",   5948415,  6,  4, 0,  "Door-Interior-Single-1_Panel-Wood", '30" x 96"')
place_door("d_half",   5948418, 46, 10, 0,  "Door-Interior-Single-1_Panel-Wood", '28"')
place_door("d_pantry", 5948416, 42, 25, 0,  "Door-Interior-Single-1_Panel-Wood", '30" x 96"')
place_door("d_mud",    5948416, 42, 15, 0,  "Door-Interior-Single-1_Panel-Wood", '30" x 96"')
place_door("d_gar2mud",5948402, 52, 12, 0,  "Door-Exterior-Single-Entry-Half Flat Glass-Wood_Clad", '36" x 96"')

# Level 2 doors (z=11 = Level 2 elevation)
place_door("d_b2",     5948422, 10, 10, 11, "Door-Interior-Single-1_Panel-Wood", '30" x 96"')
place_door("d_b3",     5948422, 28, 10, 11, "Door-Interior-Single-1_Panel-Wood", '30" x 96"')
place_door("d_bath2",  5948422, 44, 10, 11, "Door-Interior-Single-1_Panel-Wood", '28"')
place_door("d_b4",     5948423, 14, 18, 11, "Door-Interior-Single-1_Panel-Wood", '30" x 96"')
place_door("d_b5",     5948423, 34, 18, 11, "Door-Interior-Single-1_Panel-Wood", '30" x 96"')
