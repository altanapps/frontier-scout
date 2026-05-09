"""Geographic coordinates for each lab, keyed by DB lab name.

City → (lat, lon, country_code). Pixel jitter is used to spread multiple
labs in the same city so they don't overlap on the map.
"""

CITY_COORDS = {
    "London":     (51.50, -0.13, "GB"),
    "Oxford":     (51.76, -1.26, "GB"),
    "Cambridge":  (52.20,  0.12, "GB"),
    "Hinxton":    (52.09,  0.20, "GB"),
    "Edinburgh":  (55.95, -3.19, "GB"),
    "Zurich":     (47.38,  8.55, "CH"),
    "Lausanne":   (46.52,  6.57, "CH"),
    "Munich":     (48.14, 11.58, "DE"),
    "Tübingen":   (48.52,  9.05, "DE"),
    "Heidelberg": (49.40,  8.67, "DE"),
    "Bonn":       (50.74,  7.10, "DE"),
    "Freiburg":   (47.99,  7.84, "DE"),
    "Bremen":     (53.07,  8.80, "DE"),
    "Jülich":     (50.92,  6.36, "DE"),
    "Aachen":     (50.78,  6.08, "DE"),
    "Stuttgart":  (48.78,  9.18, "DE"),
    "Paris":      (48.85,  2.35, "FR"),
    "Grenoble":   (45.19,  5.72, "FR"),
    "Lille":      (50.63,  3.06, "FR"),
    "Rennes":     (48.11, -1.68, "FR"),
    "Bordeaux":   (44.84, -0.58, "FR"),
    "Delft":      (52.00,  4.36, "NL"),
    "Enschede":   (52.22,  6.89, "NL"),
    "Eindhoven":  (51.45,  5.48, "NL"),
    "Leuven":     (50.88,  4.70, "BE"),
    "Milan":      (45.46,  9.19, "IT"),
    "Rome":       (41.90, 12.50, "IT"),
    "Pisa":       (43.72, 10.40, "IT"),
    "Naples":     (40.85, 14.27, "IT"),
    "Genoa":      (44.41,  8.93, "IT"),
    "Madrid":     (40.42, -3.70, "ES"),
    "Stockholm":  (59.33, 18.07, "SE"),
    "Lund":       (55.71, 13.20, "SE"),
    "Helsinki":   (60.17, 24.94, "FI"),
    "Tampere":    (61.50, 23.78, "FI"),
    "Tartu":      (58.38, 26.73, "EE"),
    "Prague":     (50.08, 14.43, "CZ"),
    "Istanbul":   (41.08, 28.99, "TR"),
    "Ankara":     (39.93, 32.86, "TR"),
    "Trondheim":  (63.43, 10.40, "NO"),
}


def _city_for(lab_name: str) -> str:
    """Best-effort match lab name → city by keyword."""
    n = lab_name.lower()
    if "imperial" in n or "ucl" in n or "king's" in n: return "London"
    if "oxford" in n: return "Oxford"
    if "cambridge" in n: return "Cambridge"
    if "sanger" in n: return "Hinxton"
    if "edinburgh" in n: return "Edinburgh"
    if "eth zurich" in n or "eth ai" in n: return "Zurich"
    if "epfl" in n: return "Lausanne"
    if "tum " in n or "munich" in n: return "Munich"
    if "tübingen" in n or "tubingen" in n or "ellis" in n: return "Tübingen"
    if "heidelberg" in n or "embl" in n: return "Heidelberg"
    if "bonn" in n: return "Bonn"
    if "freiburg" in n: return "Freiburg"
    if "dfki" in n or "bremen" in n: return "Bremen"
    if "jülich" in n or "julich" in n: return "Jülich"
    if "inria paris" in n or "willow" in n or "sierra" in n: return "Paris"
    if "inria grenoble" in n or "chroma" in n or "thoth" in n: return "Grenoble"
    if "inria lille" in n or "defrost" in n: return "Lille"
    if "inria rennes" in n or "rainbow" in n: return "Rennes"
    if "inria bordeaux" in n or "auctus" in n: return "Bordeaux"
    if "tu delft" in n or "qutech" in n or "delft" in n: return "Delft"
    if "twente" in n: return "Enschede"
    if "ku leuven" in n or "leuven" in n: return "Leuven"
    if "polimi" in n or "politecnico di milano" in n or "milan" in n: return "Milan"
    if "sapienza" in n or "rome" in n: return "Rome"
    if "pisa" in n or "piaggio" in n: return "Pisa"
    if "naples" in n or "prisma" in n: return "Naples"
    if "carlos iii" in n or "madrid" in n: return "Madrid"
    if "kth" in n or "stockholm" in n: return "Stockholm"
    if "lund" in n: return "Lund"
    if "aalto" in n or "helsinki" in n or "hiit" in n: return "Helsinki"
    if "tampere" in n: return "Tampere"
    if "tartu" in n: return "Tartu"
    if "ctu prague" in n or "prague" in n or "ciirc" in n: return "Prague"
    if "iit genoa" in n or "humanoid sensing" in n or "hsp " in n: return "Genoa"
    if "rwth" in n or "aachen" in n: return "Aachen"
    if "stuttgart" in n: return "Stuttgart"
    if "tu eindhoven" in n or "eindhoven" in n: return "Eindhoven"
    if "bogazici" in n or "boun" in n or "colors" in n: return "Istanbul"
    if "metu" in n or "kovan" in n or "ankara" in n: return "Ankara"
    if "sintef" in n or "ntnu" in n: return "Trondheim"
    return "London"  # fallback


def coords_for(lab_name: str) -> tuple[str, str, float, float]:
    """Return (city, country_code, lat, lon) for a lab name."""
    city = _city_for(lab_name)
    lat, lon, cc = CITY_COORDS[city]
    return city, cc, lat, lon
