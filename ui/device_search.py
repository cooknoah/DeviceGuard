"""Client-side text filtering for the connected-devices table.

Pure (Qt-free) so it's easy to unit-test; the Devices view calls
``filter_devices`` on the loaded snapshot as the user types.
"""

# Device fields searched by a query, in the order a user is likely to think of.
_SEARCH_FIELDS = ("name", "manufacturer", "pnp_class", "device_id")


def device_matches(device: dict, query: str) -> bool:
    """True if the (already-lowercased) query is a substring of any searched
    field. An empty query matches everything."""
    if not query:
        return True
    return any(
        query in (device.get(field) or "").lower()
        for field in _SEARCH_FIELDS
    )


def filter_devices(devices: list[dict], query: str) -> list[dict]:
    """Return the devices matching ``query`` (case-insensitive substring over
    name / manufacturer / class / device id). Blank query returns all."""
    q = (query or "").strip().lower()
    if not q:
        return list(devices)
    return [d for d in devices if device_matches(d, q)]
