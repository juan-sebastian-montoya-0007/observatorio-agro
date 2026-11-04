"""Refresh the checked-in DANE MGN 2025 snapshot; never runs in the API process."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = (
    "https://geoportal.dane.gov.co/mparcgis/rest/services/"
    "MGN2025/Serv_CapasMGN_2025/FeatureServer"
)
OUTPUT = Path(__file__).resolve().parents[1] / "app" / "data" / "cartography"


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "publisher": "DANE",
        "name": "Marco Geoestadístico Nacional 2025",
        "source_url": BASE_URL,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "crs": "EPSG:4326",
        "note": "Geometrías oficiales generalizadas para visualización estadística.",
        "layers": {},
    }
    for level, layer, code_field, name_field, offset in (
        ("department", 319, "DPTO_CCDGO", "DPTO_CNMBRE", 0.008),
        ("municipality", 317, "MPIO_CDPMP", "MPIO_CNMBRE", 0.002),
    ):
        params = {
            "where": "1=1",
            "outFields": f"{code_field},{name_field},DPTO_CCDGO",
            "outSR": "4326",
            "f": "geojson",
            "returnGeometry": "true",
            "maxAllowableOffset": str(offset),
            "geometryPrecision": "5",
        }
        query_url = f"{BASE_URL}/{layer}/query?{urlencode(params)}"
        request = Request(query_url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(request, timeout=120) as response:
            raw = response.read()
        collection = json.loads(raw)
        if collection.get("type") != "FeatureCollection" or not collection.get("features"):
            raise ValueError(f"Unexpected DANE response: {str(collection)[:500]}")
        if collection.get("exceededTransferLimit"):
            raise ValueError("DANE truncated the snapshot")
        for feature in collection["features"]:
            properties = {key.upper(): value for key, value in feature["properties"].items()}
            feature["properties"] = {
                "code": str(properties[code_field]).zfill(2 if level == "department" else 5),
                "name": properties[name_field],
                "department_code": str(properties["DPTO_CCDGO"]).zfill(2),
            }
            feature.pop("id", None)
        collection["features"].sort(key=lambda feature: feature["properties"]["code"])
        codes = [feature["properties"]["code"] for feature in collection["features"]]
        if len(set(codes)) != len(codes):
            raise ValueError("Duplicate DIVIPOLA codes in DANE snapshot")
        encoded = json.dumps(collection, ensure_ascii=False, separators=(",", ":")).encode()
        file_name = f"{level}s.geojson"
        (OUTPUT / file_name).write_bytes(encoded)
        manifest["layers"][level] = {
            "layer": layer,
            "file": file_name,
            "feature_count": len(codes),
            "sha256": hashlib.sha256(encoded).hexdigest(),
            "download_sha256": hashlib.sha256(raw).hexdigest(),
            "max_allowable_offset_degrees": offset,
            "query_url": query_url,
        }
        print(f"{level}: {len(codes)} features, {len(encoded):,} bytes")
    (OUTPUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
