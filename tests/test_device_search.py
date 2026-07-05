"""Client-side device search/filter."""

from ui.device_search import device_matches, filter_devices


DEVICES = [
    {"name": "Pulsar eS HE 70", "manufacturer": "Pulsar", "pnp_class": "HIDClass",
     "device_id": "HID\\VID_3710&PID_2405"},
    {"name": "ROG Gaming Display", "manufacturer": "WinUsb Device", "pnp_class": "USBDevice",
     "device_id": "USB\\VID_0B05&PID_1BA4"},
    {"name": "HyperX Quadcast", "manufacturer": "Generic USB Audio", "pnp_class": "MEDIA",
     "device_id": "USB\\VID_0951&PID_16A4"},
]


def test_blank_query_returns_all():
    assert filter_devices(DEVICES, "") == DEVICES
    assert filter_devices(DEVICES, "   ") == DEVICES


def test_match_by_name_case_insensitive():
    out = filter_devices(DEVICES, "pulsar")
    assert len(out) == 1 and out[0]["name"] == "Pulsar eS HE 70"


def test_match_by_manufacturer():
    out = filter_devices(DEVICES, "winusb")
    assert [d["name"] for d in out] == ["ROG Gaming Display"]


def test_match_by_device_id_fragment():
    out = filter_devices(DEVICES, "vid_0951")
    assert [d["name"] for d in out] == ["HyperX Quadcast"]


def test_match_by_class():
    out = filter_devices(DEVICES, "hidclass")
    assert [d["name"] for d in out] == ["Pulsar eS HE 70"]


def test_no_match_returns_empty():
    assert filter_devices(DEVICES, "zzz-nothing") == []


def test_query_spanning_no_single_field_does_not_match():
    # "pulsar es" is in the name, but "pulsar winusb" spans two devices/fields.
    assert filter_devices(DEVICES, "pulsar winusb") == []


def test_returns_a_new_list_not_the_input():
    out = filter_devices(DEVICES, "")
    assert out == DEVICES and out is not DEVICES


def test_device_matches_handles_missing_fields():
    assert device_matches({}, "anything") is False
    assert device_matches({}, "") is True
