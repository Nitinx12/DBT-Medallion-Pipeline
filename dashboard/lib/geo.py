"""Static store coordinates for the Geo page (synthetic demo geography).

Store cities are generated placeholders, so real geocoding is impossible.
Each store sits on a representative point of its province (US state
capital) with a small deterministic jitter where a province has two
stores, so bubbles never stack exactly. Do not treat these as addresses.
"""

from __future__ import annotations

import pandas as pd

# store_id -> (latitude, longitude). Sources: state capital coordinates;
# same province pairs (IL, MD, SC) offset by +/-0.25 degrees.
STORE_GEO: dict[int, tuple[float, float]] = {
    1: (40.03, -89.65),
    2: (40.76, -111.89),
    3: (41.82, -71.41),
    4: (40.22, -74.76),
    5: (30.45, -91.15),
    6: (39.23, -76.49),
    7: (34.25, -81.03),
    8: (43.62, -116.20),
    9: (33.75, -84.39),
    10: (35.47, -97.52),
    11: (39.05, -95.68),
    12: (44.31, -69.78),
    13: (33.75, -81.03),
    14: (44.94, -123.04),
    15: (21.31, -157.86),
    16: (37.54, -77.44),
    17: (47.04, -122.90),
    18: (42.73, -84.56),
    19: (46.59, -112.04),
    20: (38.35, -81.63),
    21: (38.73, -76.49),
    22: (44.95, -93.09),
    23: (46.81, -100.78),
    24: (39.53, -89.65),
    25: (38.20, -84.87),
}


def store_coordinates() -> pd.DataFrame:
    """Return store_id + latitude + longitude for every mapped store."""
    return pd.DataFrame(
        [(sid, lat, lng) for sid, (lat, lng) in sorted(STORE_GEO.items())],
        columns=["store_id", "latitude", "longitude"],
    )
