import httpx
from typing import Optional, Tuple
from app.utils.logger import get_logger


class GeocodingService:
    """Lightweight geocoding: static centroid map for Seoul gu/dong with optional Nominatim fallback."""

    def __init__(self):
        self.logger = get_logger("geocoding_service")
        # Minimal seed; can be expanded or loaded from a JSON file
        self.seoul_gu_centroids = {
            "강남구": (37.5172, 127.0473),
            "서초구": (37.4836, 127.0327),
            "송파구": (37.5146, 127.1065),
            "강동구": (37.5301, 127.1238),
            "강서구": (37.5610, 126.8226),
            "강북구": (37.6396, 127.0257),
            "강동구": (37.5301, 127.1238),
            "관악구": (37.4784, 126.9516),
            "광진구": (37.5385, 127.0823),
            "구로구": (37.4955, 126.8877),
            "금천구": (37.4569, 126.8955),
            "노원구": (37.6543, 127.0565),
            "도봉구": (37.6688, 127.0471),
            "동대문구": (37.5744, 127.0400),
            "동작구": (37.5124, 126.9393),
            "마포구": (37.5638, 126.9084),
            "서대문구": (37.5791, 126.9368),
            "성동구": (37.5633, 127.0364),
            "성북구": (37.5894, 127.0167),
            "양천구": (37.5169, 126.8665),
            "영등포구": (37.5264, 126.8963),
            "용산구": (37.5311, 126.9819),
            "은평구": (37.6176, 126.9227),
            "종로구": (37.5735, 126.9793),
            "중구": (37.5636, 126.9976),
            "중랑구": (37.6066, 127.0927),
        }

    async def geocode_text(self, text: str) -> Optional[Tuple[float, float]]:
        # Try Seoul gu centroid
        for gu, (lat, lon) in self.seoul_gu_centroids.items():
            if gu in text:
                return lat, lon
        # Optional: Nominatim fallback (best-effort)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": text, "format": "json", "limit": 1},
                    headers={"User-Agent": "stubichat-geocoder"}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data:
                        lat = float(data[0]["lat"])  # type: ignore
                        lon = float(data[0]["lon"])  # type: ignore
                        return lat, lon
        except Exception as e:
            self.logger.warning(f"Nominatim fallback failed: {e}")
        return None

