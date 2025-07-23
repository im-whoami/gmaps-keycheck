#!/usr/bin/env python3
"""
gmaps-keycheck v1.2

Lightweight tool to test a Google Maps API key against core Google Maps endpoints,
including Batch Geocoding, and display each successful call’s data and its JSON
response inline, with a progress bar.

Endpoints tested:
  • Geocoding
  • Batch Geocoding
  • Static Map
  • Street View
  • Place Photo
  • Place Details
  • Text Search
  • Distance Matrix
  • Elevation
  • Time Zone
  • Nearby Search
  • Autocomplete
  • Snap to Roads
  • Nearest Roads
  • Geolocate

Usage:
  python gmaps-keycheck.py
"""

import sys, csv, json, time, hashlib, pathlib, subprocess, requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

GREEN, RED, RESET = "\033[92m", "\033[91m", "\033[0m"
SERVICES = [
    "geocode", "batchgeocode", "staticmap", "streetview", "photoreference",
    "placedetails", "textsearch", "distancematrix", "elevation", "timezone",
    "nearbysearch", "autocomplete", "snaptoroads", "nearestroads", "geolocate"
]

def make_session(retries=2, backoff=0.5, timeout=10):
    s = requests.Session()
    retry = Retry(total=retries, backoff_factor=backoff,
                  status_forcelist=[429,500,502,503,504],
                  allowed_methods=["GET","POST"])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    orig = s.request
    def timed_request(m, u, **kw): return orig(m, u, timeout=timeout, **kw)
    s.request = timed_request
    return s

def mask_key(key):
    h = hashlib.sha1(key.encode()).hexdigest()[:8]
    return f"{key[:4]}…{key[-4:]} ({h})"

def fetch_json(session, method, url, **kw):
    try:
        r = getattr(session, method)(url, **kw)
        return r.status_code, r.json()
    except:
        return None, {}

def fetch_image(session, url, params, dest):
    try:
        r = session.get(url, params=params)
        if r.status_code == 200:
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f: f.write(r.content)
            return True, r.status_code, r.headers
        return False, r.status_code, r.headers
    except:
        return False, None, {}

def test_key_place(session, key, place, out_root):
    results, geo, pid = {}, None, None

    for svc in tqdm(SERVICES, desc=f"Checking {place}", leave=False):
        if svc == "geocode":
            code, js = fetch_json(session, "get",
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={"address": place, "key": key})
            if js.get("status") == "OK":
                addr = js["results"][0]["formatted_address"]
                results["geocode"] = {"http": code, "info": addr, "raw": js}
                loc = js["results"][0]["geometry"]["location"]
                geo = f"{loc['lat']},{loc['lng']}"
                pid = js["results"][0]["place_id"]

        elif svc == "batchgeocode":
            batch_csv = out_root / "batch.csv"
            batch_csv.parent.mkdir(parents=True, exist_ok=True)
            with open(batch_csv, "w", newline="") as f:
                csv.writer(f).writerows([["address"], [place]])
            code, js = fetch_json(session, "post",
                "https://maps.googleapis.com/maps/api/geocode/batch/json",
                files={"file": open(batch_csv, "rb")},
                params={"key": key})
            info = "" if code == 200 else js.get("status", "")
            results["batchgeocode"] = {"http": code, "info": info, "raw": js}

        elif svc == "staticmap" and geo:
            ok, c, h = fetch_image(session,
                "https://maps.googleapis.com/maps/api/staticmap",
                {"center": geo, "zoom": 7, "size": "400x400", "key": key},
                out_root/"staticmap.png")
            if ok:
                sz = int(h.get("Content-Length", 0)) // 1024
                info = f"{h.get('Content-Type','')}, {sz}KB"
                results["staticmap"] = {"http": c, "info": info, "raw": dict(h)}

        elif svc == "streetview" and geo:
            ok, c, h = fetch_image(session,
                "https://maps.googleapis.com/maps/api/streetview",
                {"location": geo, "size": "400x400", "key": key},
                out_root/"streetview.jpg")
            if ok:
                sz = int(h.get("Content-Length", 0)) // 1024
                info = f"{h.get('Content-Type','')}, {sz}KB"
                results["streetview"] = {"http": c, "info": info, "raw": dict(h)}

        elif svc == "photoreference" and pid:
            code, js = fetch_json(session, "get",
                "https://maps.googleapis.com/maps/api/place/findplacefromtext/json",
                params={"input": place, "inputtype": "textquery", "fields": "photos", "key": key})
            cands = js.get("candidates", [])
            if cands and "photos" in cands[0]:
                ref = cands[0]["photos"][0].get("photo_reference", "")
                results["photoreference"] = {"http": code, "info": ref, "raw": js}

        elif svc == "placedetails" and pid:
            code, js = fetch_json(session, "get",
                "https://maps.googleapis.com/maps/api/place/details/json",
                params={"place_id": pid, "key": key})
            if js.get("status") == "OK":
                nm = js["result"].get("name", "")
                results["placedetails"] = {"http": code, "info": nm, "raw": js}

        elif svc == "textsearch":
            code, js = fetch_json(session, "get",
                "https://maps.googleapis.com/maps/api/place/textsearch/json",
                params={"query": place, "key": key})
            if js.get("results"):
                nm = js["results"][0].get("name", "")
                results["textsearch"] = {"http": code, "info": nm, "raw": js}

        elif svc == "distancematrix" and geo:
            code, js = fetch_json(session, "get",
                "https://maps.googleapis.com/maps/api/distancematrix/json",
                params={"origins": geo, "destinations": geo, "key": key})
            rows = js.get("rows", [])
            if rows and rows[0].get("elements", []):
                el = rows[0]["elements"][0]
                if "distance" in el:
                    d = el["distance"]["text"]; t = el["duration"]["text"]
                    results["distancematrix"] = {"http": code, "info": f"{d}, {t}", "raw": js}

        elif svc == "elevation" and geo:
            code, js = fetch_json(session, "get",
                "https://maps.googleapis.com/maps/api/elevation/json",
                params={"locations": geo, "key": key})
            rs = js.get("results", [])
            if rs:
                e = rs[0].get("elevation", "")
                results["elevation"] = {"http": code, "info": f"{e}m", "raw": js}

        elif svc == "timezone" and geo:
            ts = int(time.time())
            code, js = fetch_json(session, "get",
                "https://maps.googleapis.com/maps/api/timezone/json",
                params={"location": geo, "timestamp": ts, "key": key})
            tz = js.get("timeZoneId", "")
            if tz:
                results["timezone"] = {"http": code, "info": tz, "raw": js}

        elif svc == "nearbysearch" and geo:
            code, js = fetch_json(session, "get",
                "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
                params={"location": geo, "radius": 1000, "type": "restaurant", "key": key})
            if js.get("results"):
                nm = js["results"][0].get("name", "")
                results["nearbysearch"] = {"http": code, "info": nm, "raw": js}

        elif svc == "autocomplete":
            prefix = place.split()[0]
            code, js = fetch_json(session, "get",
                "https://maps.googleapis.com/maps/api/place/autocomplete/json",
                params={"input": prefix, "types": "geocode", "key": key})
            preds = js.get("predictions", [])
            if preds:
                desc = preds[0].get("description", "")
                results["autocomplete"] = {"http": code, "info": desc, "raw": js}

        elif svc == "snaptoroads" and geo:
            code, js = fetch_json(session, "get",
                "https://roads.googleapis.com/v1/snapToRoads",
                params={"path": f"{geo}|{geo}", "interpolate": True, "key": key})
            pts = len(js.get("snappedPoints", []))
            if pts:
                results["snaptoroads"] = {"http": code, "info": f"{pts} points", "raw": js}

        elif svc == "nearestroads" and geo:
            code, js = fetch_json(session, "get",
                "https://roads.googleapis.com/v1/nearestRoads",
                params={"points": geo, "key": key})
            pts = len(js.get("snappedPoints", []))
            if pts:
                results["nearestroads"] = {"http": code, "info": f"{pts} points", "raw": js}

        elif svc == "geolocate":
            code, js = fetch_json(session, "post",
                "https://www.googleapis.com/geolocation/v1/geolocate",
                params={"key": key}, json={"considerIp": True})
            loc = js.get("location", {})
            if loc.get("lat") is not None:
                info = f"{loc['lat']},{loc['lng']}"
            else:
                info = js.get("error", js.get("status", "UNKNOWN"))
            results["geolocate"] = {"http": code, "info": info, "raw": js}

    return results

def print_table(key, place, results):
    print(f"\nKey {mask_key(key)}  Place \"{place}\"")
    print("-" * 60)
    print(f"{'API':15}{'HTTP':6}  Info")
    print("-" * 60)
    for svc, r in results.items():
        http = str(r["http"] or "").ljust(6)
        info = r["info"]
        print(f"{svc[:15].ljust(15)}{http}  {info}")
        raw = r.get("raw")
        if raw is not None:
            raw_str = json.dumps(raw, indent=2)
            for line in raw_str.splitlines():
                print(" " * 23 + line)
    print("-" * 60)

def main():
    key   = input("Enter your Google Maps API key: ").strip()
    place = input("Enter place (address or lat,lng): ").strip()
    if not key or not place:
        print("API key and place are required."); sys.exit(1)

    session  = make_session()
    out_root = pathlib.Path("output") / hashlib.sha1(key.encode()).hexdigest()[:8]
    results  = test_key_place(session, key, place, out_root)

    print_table(key, place, results)

if __name__ == "__main__":
    main()
