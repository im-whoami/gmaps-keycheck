# gmaps-keycheck

**gmaps-keycheck** is a lightweight Python script that allows you to test the capabilities and access of a **Google Maps API key** across multiple official Google Maps endpoints.

It helps verify which services your key has access to, fetches data like geolocation, elevation, nearby places, and also downloads static and street view images. All responses are shown with HTTP status, summary info, and pretty-printed JSON.

---

## 🚀 Features

- ✅ Tests 15+ Google Maps API endpoints
- 📍 Supports both address and coordinates as input
- 🌐 Returns formatted address, location coordinates, timezone, elevation, place details, and more
- 🖼 Downloads images for Static Map and Street View
- 📦 Saves all output in a local `output/` folder (organized by hashed key)
- 📊 Shows response data inline with a terminal progress bar (`tqdm`)
- 🔁 Uses retry logic for reliable API calls

---

## 📌 Endpoints Tested

- Geocoding
- **Batch Geocoding** (via file upload)
- Static Map
- Street View
- Place Photo
- Place Details
- Text Search
- Distance Matrix
- Elevation
- Time Zone
- Nearby Search
- Autocomplete
- Snap to Roads
- Nearest Roads
- Geolocation (based on IP)

---

## 💻 Requirements

- Python 3.6 or higher
- Python packages:
  ```bash
  pip install requests tqdm
