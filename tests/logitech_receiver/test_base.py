import struct
import sys

from typing import Union
from unittest import mock

import pytest

from logitech_receiver import base
from logitech_receiver import exceptions
from logitech_receiver.base import CENTURION_ADDRESSED_REPORT_ID
from logitech_receiver.base import CENTURION_REPORT_ID
from logitech_receiver.base import HIDPP_SHORT_MESSAGE_ID
from logitech_receiver.base import CenturionHandleState
from logitech_receiver.common import LOGITECH_VENDOR_ID
from logitech_receiver.common import BusID
from logitech_receiver.hidpp10_constants import ErrorCode as Hidpp10Error
from logitech_receiver.hidpp20_constants import ErrorCode as Hidpp20Error


@pytest.mark.parametrize(
    "usb_id, expected_name, expected_receiver_kind",
    [
        (0xC548, "Bolt Receiver", "bolt"),
        (0xC52B, "Unifying Receiver", "unifying"),
        (0xC531, "Nano Receiver", "nano"),
        (0xC53F, "Lightspeed Receiver", None),
        (0xC517, "EX100 Receiver 27 Mhz", "27Mhz"),
    ],
)
def test_product_information(usb_id, expected_name, expected_receiver_kind):
    res = base.product_information(usb_id)

    assert res["name"] == expected_name
    assert isinstance(res["vendor_id"], int)
    assert isinstance(res["product_id"], int)

    if expected_receiver_kind:
        assert res["receiver_kind"] == expected_receiver_kind


def test_filter_receivers_known():
    bus_id = 2
    product_id = 0xC548

    receiver_info = base.get_known_receiver_info(bus_id, LOGITECH_VENDOR_ID, product_id)

    assert receiver_info["name"] == "Bolt Receiver"
    assert receiver_info["receiver_kind"] == "bolt"


def test_filter_receivers_unknown():
    bus_id = 1
    product_id = 0xC500

    receiver_info = base.get_known_receiver_info(bus_id, LOGITECH_VENDOR_ID, product_id)

    assert receiver_info["bus_id"] == bus_id
    assert receiver_info["product_id"] == product_id


@pytest.mark.parametrize(
    "product_id, bus, hidpp_short, hidpp_long, expected",
    [
        (0xC548, BusID.USB, True, False, {"name": "Bolt Receiver", "usb_interface": 2}),
        (0xC07D, BusID.USB, True, False, {"usb_interface": 1}),
        (0xC07E, BusID.USB, False, True, {"usb_interface": 1}),
        (0xC07E, BusID.BLUETOOTH, False, True, {"bus_id": 5}),
        (0xA07E, BusID.USB, False, True, {"product_id": 0xA07E}),
        (0xA07C, BusID.USB, False, False, None),
        (0xC07F, BusID.USB, None, None, {"usb_interface": 2}),
        (0xC07F, BusID.BLUETOOTH, None, None, None),
        (0xB013, BusID.BLUETOOTH, None, None, {"product_id": 0xB013}),
    ],
)
def test_filter_products_of_interest(product_id, bus, hidpp_short, hidpp_long, expected):
    receiver_info = base.filter_products_of_interest(
        bus,
        LOGITECH_VENDOR_ID,
        product_id,
        hidpp_short=hidpp_short,
        hidpp_long=hidpp_long,
    )

    if expected is None:
        assert receiver_info == expected
    else:
        assert all([receiver_info[key] == expected_value for key, expected_value in expected.items()])
        assert receiver_info["vendor_id"] == LOGITECH_VENDOR_ID
        assert receiver_info["product_id"]


def test_match():
    record = {"vendor_id": LOGITECH_VENDOR_ID}

    res = base._match_device(record, 0, LOGITECH_VENDOR_ID, 0)

    assert res is True


@pytest.mark.parametrize(
    "report_id, sub_id, address, valid_notification",
    [
        (0x1, 0x72, 0x57, True),
        (0x1, 0x40, 0x63, True),
        (0x1, 0x40, 0x71, True),
        (0x1, 0x80, 0x71, False),
        (0x1, 0x00, 0x70, False),
        (0x20, 0x09, 0x71, False),
        (0x1, 0x37, 0x71, False),
    ],
)
def test_make_notification(report_id, sub_id, address, valid_notification):
    devnumber = 123
    data = bytes([sub_id, address, 0x02, 0x03, 0x04])

    result = base.make_notification(report_id, devnumber, data)

    if valid_notification:
        assert isinstance(result, base.HIDPPNotification)
        assert result.report_id == report_id
        assert result.devnumber == devnumber
        assert result.sub_id == sub_id
        assert result.address == address
        assert result.data == bytes([0x02, 0x03, 0x04])
    else:
        assert result is None


def test_get_next_sw_id():
    res1 = base._get_next_sw_id()
    res2 = base._get_next_sw_id()

    assert res1 == 2
    assert res2 == 3


@pytest.mark.parametrize(
    "prefix, error_code, return_error, raise_exception",
    [
        (b"\x8f", Hidpp10Error.INVALID_SUB_ID_COMMAND, False, False),
        (b"\x8f", Hidpp10Error.INVALID_SUB_ID_COMMAND, True, False),
        (b"\xff", Hidpp20Error.UNKNOWN, False, True),
    ],
)
def test_request_errors(
    prefix: bytes, error_code: Union[Hidpp10Error, Hidpp20Error], return_error: bool, raise_exception: bool
):
    handle = 0
    device_number = 66

    next_sw_id = 0x02
    reply_data_sw_id = struct.pack("!H", 0x0000 | next_sw_id)

    with mock.patch(
        "logitech_receiver.base._read",
        return_value=(HIDPP_SHORT_MESSAGE_ID, device_number, prefix + reply_data_sw_id + struct.pack("B", error_code)),
    ), mock.patch("logitech_receiver.base._read_input_buffer"), mock.patch(
        "logitech_receiver.base.write", return_value=None
    ), mock.patch("logitech_receiver.base._get_next_sw_id", return_value=next_sw_id):
        if raise_exception:
            with pytest.raises(exceptions.FeatureCallError) as context:
                base.request(handle, device_number, next_sw_id, return_error=return_error)
            assert context.value.number == device_number
            assert context.value.request == next_sw_id
            assert context.value.error == error_code
            assert context.value.params == b""

        else:
            result = base.request(handle, device_number, next_sw_id, return_error=return_error)
            assert result == (error_code if return_error else None)


@pytest.mark.skipif(sys.platform == "darwin", reason="Test only runs on Linux")
@pytest.mark.parametrize(
    "simulated_error, expected_result",
    [
        (Hidpp10Error.INVALID_SUB_ID_COMMAND, 1.0),
        (Hidpp10Error.RESOURCE_ERROR, None),
        (Hidpp10Error.CONNECTION_REQUEST_FAILED, None),
        (Hidpp10Error.UNKNOWN_DEVICE, exceptions.NoSuchDevice),
    ],
)
def test_ping_errors(simulated_error: Hidpp10Error, expected_result):
    handle = 1
    device_number = 1

    next_sw_id = 0x05
    reply_data_sw_id = struct.pack("!H", 0x0010 | next_sw_id)

    with mock.patch(
        "logitech_receiver.base._read",
        return_value=(HIDPP_SHORT_MESSAGE_ID, device_number, b"\x8f" + reply_data_sw_id + bytes([simulated_error])),
    ), mock.patch("logitech_receiver.base._read_input_buffer"), mock.patch(
        "logitech_receiver.base.write", return_value=None
    ), mock.patch("logitech_receiver.base._get_next_sw_id", return_value=next_sw_id):
        if isinstance(expected_result, type) and issubclass(expected_result, Exception):
            with pytest.raises(expected_result) as context:
                base.ping(handle=handle, devnumber=device_number)
            assert context.value.number == device_number
            assert context.value.request == struct.unpack("!H", reply_data_sw_id)[0]

        else:
            result = base.ping(handle=handle, devnumber=device_number)
            assert result == expected_result


# --- Centurion transport tests ---


class TestCenturionFrameHeader:
    """Test _centurion_frame_header builds correct headers for both variants."""

    def test_0x51_header(self):
        state = CenturionHandleState(report_id=CENTURION_REPORT_ID)
        header = base._centurion_frame_header(state, cpl_length=5, flags=0x00)
        assert header == bytes([0x51, 5, 0x00])

    def test_0x51_header_with_flags(self):
        state = CenturionHandleState(report_id=CENTURION_REPORT_ID)
        header = base._centurion_frame_header(state, cpl_length=10, flags=0x03)
        assert header == bytes([0x51, 10, 0x03])

    def test_0x50_header_unknown_addr(self):
        state = CenturionHandleState(report_id=CENTURION_ADDRESSED_REPORT_ID, device_addr=None)
        header = base._centurion_frame_header(state, cpl_length=5, flags=0x00)
        # device_addr defaults to 0x00 when unknown
        assert header == bytes([0x50, 0x00, 5, 0x00])

    def test_0x50_header_known_addr(self):
        state = CenturionHandleState(report_id=CENTURION_ADDRESSED_REPORT_ID, device_addr=0x23)
        header = base._centurion_frame_header(state, cpl_length=5, flags=0x00)
        assert header == bytes([0x50, 0x23, 5, 0x00])

    def test_0x50_header_with_flags(self):
        state = CenturionHandleState(report_id=CENTURION_ADDRESSED_REPORT_ID, device_addr=0x23)
        header = base._centurion_frame_header(state, cpl_length=10, flags=0x07)
        assert header == bytes([0x50, 0x23, 10, 0x07])


class TestUnwrapCenturionFrame:
    """Test _unwrap_centurion_frame for both 0x51 and 0x50 variants."""

    HANDLE = 99

    def setup_method(self):
        """Ensure no leftover centurion state between tests."""
        base._centurion_handles.pop(self.HANDLE, None)

    def teardown_method(self):
        base._centurion_handles.pop(self.HANDLE, None)

    def test_unwrap_0x51_frame(self):
        """0x51 frame with feat_idx=0x02, func_sw=0x1A, 2 data bytes."""
        # cpl_length = 1(flags) + 1(feat_idx) + 1(func_sw) + 2(data) = 5
        raw = bytes([0x51, 5, 0x00, 0x02, 0x1A, 0xAA, 0xBB]) + b"\x00" * 57
        result = base._unwrap_centurion_frame(raw, self.HANDLE, self.HANDLE)
        # Should reconstruct as [0x11, 0xFF, feat_idx, func_sw, data..., pad to 20]
        assert result[0] == 0x11
        assert result[1] == 0xFF
        assert result[2] == 0x02  # feat_idx
        assert result[3] == 0x1A  # func_sw
        assert result[4] == 0xAA
        assert result[5] == 0xBB
        assert len(result) == 20  # padded to standard long

    def test_unwrap_0x50_frame(self):
        """0x50 frame with device_addr=0x23, same payload as above."""
        # Frame: [0x50, device_addr, cpl_length, flags, feat_idx, func_sw, data...]
        raw = bytes([0x50, 0x23, 5, 0x00, 0x02, 0x1A, 0xAA, 0xBB]) + b"\x00" * 56
        base._centurion_handles[self.HANDLE] = CenturionHandleState(report_id=CENTURION_ADDRESSED_REPORT_ID)
        result = base._unwrap_centurion_frame(raw, self.HANDLE, self.HANDLE)
        assert result[0] == 0x11
        assert result[1] == 0xFF
        assert result[2] == 0x02  # feat_idx
        assert result[3] == 0x1A  # func_sw
        assert result[4] == 0xAA
        assert result[5] == 0xBB
        assert len(result) == 20

    def test_0x50_learns_device_addr(self):
        """First RX on a 0x50 handle should learn the device address."""
        base._centurion_handles[self.HANDLE] = CenturionHandleState(report_id=CENTURION_ADDRESSED_REPORT_ID)
        assert base._centurion_handles[self.HANDLE].device_addr is None

        raw = bytes([0x50, 0x23, 3, 0x00, 0x02, 0x1A]) + b"\x00" * 58
        base._unwrap_centurion_frame(raw, self.HANDLE, self.HANDLE)

        assert base._centurion_handles[self.HANDLE].device_addr == 0x23

    def test_0x50_does_not_overwrite_addr(self):
        """Once learned, device address should not be overwritten."""
        base._centurion_handles[self.HANDLE] = CenturionHandleState(report_id=CENTURION_ADDRESSED_REPORT_ID, device_addr=0x23)
        raw = bytes([0x50, 0xFF, 3, 0x00, 0x02, 0x1A]) + b"\x00" * 58
        base._unwrap_centurion_frame(raw, self.HANDLE, self.HANDLE)

        # Should keep the original address, not overwrite with 0xFF
        assert base._centurion_handles[self.HANDLE].device_addr == 0x23

    def test_non_centurion_frame_passthrough(self):
        """Non-centurion report IDs should be returned unchanged."""
        raw = bytes([0x11, 0x01, 0x02, 0x1A]) + b"\x00" * 16
        result = base._unwrap_centurion_frame(raw, self.HANDLE, self.HANDLE)
        assert result == raw

    def test_unwrap_0x51_large_payload(self):
        """0x51 frame with payload large enough to need 63-byte padding."""
        # cpl_length covers all 61 payload bytes + flags = 62
        payload = bytes(range(61))
        raw = bytes([0x51, 62, 0x00]) + payload
        result = base._unwrap_centurion_frame(raw, self.HANDLE, self.HANDLE)
        assert len(result) == 63  # padded to centurion extended
        assert result[0] == 0x11
        assert result[1] == 0xFF
        assert result[2:63] == payload


class TestProbeCenturionDeviceAddr:
    """Test probe_centurion_device_addr: brute-force write for all 256 addrs, then read."""

    HANDLE = 101

    def setup_method(self):
        base._centurion_handles.pop(self.HANDLE, None)

    def teardown_method(self):
        base._centurion_handles.pop(self.HANDLE, None)

    def test_learns_addr_on_first_hit(self):
        """Probe finds addr=0x23 on candidate #36 (0-indexed 0x23=35) and stops."""
        state = CenturionHandleState(report_id=CENTURION_ADDRESSED_REPORT_ID)
        reply = bytes([0x50, 0x23, 0x03, 0x00]) + b"\x00" * 60

        def read_side_effect(_handle, _size, _timeout):
            # Return a response only after the write with addr=0x23
            if mock_write.call_count == 0x24:  # 0x23 is the 36th write (1-indexed)
                return reply
            return None

        with (
            mock.patch.object(base.hidapi, "write") as mock_write,
            mock.patch.object(base.hidapi, "read", side_effect=read_side_effect),
        ):
            result = base.probe_centurion_device_addr(self.HANDLE, state)
        assert result is True
        assert state.device_addr == 0x23
        # Short-circuit: stopped at candidate 0x23 (36 writes), not all 256
        assert mock_write.call_count == 0x24

    def test_skips_non_matching_read_until_match(self):
        """Non-0x50 frames in the read are ignored; next candidate's read succeeds."""
        state = CenturionHandleState(report_id=CENTURION_ADDRESSED_REPORT_ID)
        noise = b"\x11\xff" + b"\x00" * 62
        match = bytes([0x50, 0x42, 0x03, 0x00]) + b"\x00" * 60
        # Reads cycle: noise, noise, match — so addr is found on 3rd candidate
        with (
            mock.patch.object(base.hidapi, "write"),
            mock.patch.object(base.hidapi, "read", side_effect=[noise, noise, match]),
        ):
            result = base.probe_centurion_device_addr(self.HANDLE, state)
        assert result is True
        assert state.device_addr == 0x42

    def test_returns_false_when_no_response(self):
        state = CenturionHandleState(report_id=CENTURION_ADDRESSED_REPORT_ID)
        with (
            mock.patch.object(base.hidapi, "write"),
            mock.patch.object(base.hidapi, "read", return_value=None),
        ):
            result = base.probe_centurion_device_addr(self.HANDLE, state)
        assert result is False
        assert state.device_addr is None

    def test_noop_for_0x51_variant(self):
        state = CenturionHandleState(report_id=CENTURION_REPORT_ID)
        with (
            mock.patch.object(base.hidapi, "write") as mock_write,
            mock.patch.object(base.hidapi, "read") as mock_read,
        ):
            result = base.probe_centurion_device_addr(self.HANDLE, state)
        assert result is False
        assert state.device_addr is None
        mock_write.assert_not_called()
        mock_read.assert_not_called()

    def test_noop_when_addr_already_known(self):
        state = CenturionHandleState(report_id=CENTURION_ADDRESSED_REPORT_ID, device_addr=0x23)
        with (
            mock.patch.object(base.hidapi, "write") as mock_write,
            mock.patch.object(base.hidapi, "read") as mock_read,
        ):
            result = base.probe_centurion_device_addr(self.HANDLE, state)
        assert result is False
        assert state.device_addr == 0x23
        mock_write.assert_not_called()
        mock_read.assert_not_called()

    def test_aborts_on_repeated_write_failure(self):
        state = CenturionHandleState(report_id=CENTURION_ADDRESSED_REPORT_ID)
        with (
            mock.patch.object(base.hidapi, "write", side_effect=OSError("no device")),
            mock.patch.object(base.hidapi, "read") as mock_read,
        ):
            result = base.probe_centurion_device_addr(self.HANDLE, state)
        assert result is False
        assert state.device_addr is None
        mock_read.assert_not_called()

    def test_write_frames_have_sequential_addrs(self):
        """Verify each write uses a different device_addr from 0x00 to 0xFF."""
        state = CenturionHandleState(report_id=CENTURION_ADDRESSED_REPORT_ID)
        with (
            mock.patch.object(base.hidapi, "write") as mock_write,
            mock.patch.object(base.hidapi, "read", return_value=None),  # no response → scans all 256
        ):
            base.probe_centurion_device_addr(self.HANDLE, state)
        assert mock_write.call_count == 256
        addrs_sent = [mock_write.call_args_list[i][0][1][1] for i in range(256)]
        assert addrs_sent == list(range(256))
