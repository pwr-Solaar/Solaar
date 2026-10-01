import pytest

from logitech_receiver import easy_switch
from logitech_receiver import exceptions
from logitech_receiver import settings_templates
from logitech_receiver.base import HIDPPNotification
from logitech_receiver.hidpp20_constants import SupportedFeature

from . import fake_hidpp

NAMES = {0: (True, "WORK-LAPTOP-1"), 1: (True, "Alex’s MacBook Pro"), 2: (True, "omarchy-desktop")}


def keyboard(names=NAMES, link_cookie=0xB7):
    device = fake_hidpp.Device(name="MX Mechanical Mini", feature=SupportedFeature.CHANGE_HOST, version=2)
    device.hosts = easy_switch.Hosts(names, link_cookie=link_cookie)
    return device


def mouse(current_host=2, cookies="B7B7B7", names=NAMES, fresh_cookies=None, name="MX Anywhere 3S"):
    responses = [
        fake_hidpp.Response(f"03{current_host:02X}00", 0x0400),
        fake_hidpp.Response((fresh_cookies or cookies) + "00" * 13, 0x0420),
    ]
    device = fake_hidpp.Device(name=name, responses=responses, feature=SupportedFeature.CHANGE_HOST, version=1)
    device.features[SupportedFeature.CHANGE_HOST]  # look up the feature before requests are counted
    device.hosts = easy_switch.Hosts(names, cookies=bytes.fromhex(cookies))
    return device


def switches(spy_request):
    return [call.args[1] for call in spy_request.call_args_list if call.args[0] == 0x0410]


def test_follow(mocker):
    """The linked mouse gets the same requests as from Logi Options+, and nothing is sent to the keyboard"""
    lead, follower = keyboard(), mouse()
    spy_keyboard = mocker.spy(lead, "request")
    spy_mouse = mocker.spy(follower, "request")

    easy_switch.follow(lead, lead.hosts, 1, [lead, follower])

    assert [call.args for call in spy_mouse.call_args_list] == [(0x0400,), (0x0420,), (0x0410, 1)]
    assert spy_mouse.call_args.kwargs == {"no_reply": True}
    spy_keyboard.assert_not_called()


@pytest.mark.parametrize("current, new", [(current, new) for current in range(3) for new in range(3) if current != new])
def test_follow_by_name(current, new, mocker):
    """The mouse switches to its host with the name of the new host of the keyboard, whatever its index"""
    mouse_host = {"A": 1, "B": 2, "C": 0}
    lead = keyboard({0: (True, "A"), 1: (True, "B"), 2: (True, "C")})
    follower = mouse(mouse_host["ABC"[current]], names={0: (True, "C"), 1: (True, "A"), 2: (True, "B")})
    spy_request = mocker.spy(follower, "request")

    easy_switch.follow(lead, lead.hosts, new, [follower])

    assert switches(spy_request) == [mouse_host["ABC"[new]]]


@pytest.mark.parametrize(
    "keyboard_names, link_cookie, mouse_names",
    [
        ({0: (True, "A"), 1: (True, "B"), 2: (True, "C")}, 0xB7, {0: (True, "A"), 1: (True, "X"), 2: (True, "C")}),
        ({0: (True, "A"), 1: (True, "B"), 2: (True, "C")}, 0xB7, {0: (True, "A"), 1: (False, "B"), 2: (True, "C")}),
        ({0: (True, "A"), 1: (False, "B"), 2: (True, "C")}, 0xB7, {0: (True, "A"), 1: (True, "B"), 2: (True, "C")}),
        ({0: (True, "A"), 1: (True, ""), 2: (True, "C")}, 0xB7, {0: (True, "A"), 1: (True, ""), 2: (True, "C")}),
        ({0: (True, "A"), 2: (True, "C")}, 0xB7, {0: (True, "A"), 1: (True, "B"), 2: (True, "C")}),
        ({0: (True, "A"), 1: (True, "B"), 2: (True, "C")}, None, {0: (True, "A"), 1: (True, "B"), 2: (True, "C")}),
    ],
)
def test_follow_no_matching_host(keyboard_names, link_cookie, mouse_names, mocker):
    """Without a paired host with the same name, the mouse does not switch, not even to the same index"""
    lead = keyboard(keyboard_names, link_cookie)
    follower = mouse(names=mouse_names)
    spy_request = mocker.spy(follower, "request")

    easy_switch.follow(lead, lead.hosts, 1, [follower])

    assert switches(spy_request) == []


def test_follow_without_hosts(mocker):
    lead, follower = keyboard(), mouse()
    lead.hosts = None
    spy_request = mocker.spy(follower, "request")

    easy_switch.follow(lead, lead.hosts, 1, [follower])

    spy_request.assert_not_called()


@pytest.mark.parametrize("fresh_cookies", ["000000", "A6A6A6", "B7B700"])
def test_follow_not_linked_now(fresh_cookies, mocker):
    """The host cookie of the current host of the mouse has to be the link cookie of the keyboard"""
    lead, follower = keyboard(), mouse(fresh_cookies=fresh_cookies)
    spy_request = mocker.spy(follower, "request")

    easy_switch.follow(lead, lead.hosts, 1, [follower])

    assert switches(spy_request) == []


@pytest.mark.parametrize("cookies", ["000000", "A6A6A6"])
def test_follow_not_linked(cookies, mocker):
    """Devices that were not linked to the keyboard when they connected are not asked anything"""
    lead, follower = keyboard(), mouse(cookies=cookies)
    spy_request = mocker.spy(follower, "request")

    easy_switch.follow(lead, lead.hosts, 1, [follower])

    spy_request.assert_not_called()


def test_follow_offline(mocker):
    lead, follower = keyboard(), mouse()
    follower.online = False
    spy_request = mocker.spy(follower, "request")

    easy_switch.follow(lead, lead.hosts, 1, [follower])

    spy_request.assert_not_called()


def test_follow_no_reply(mocker):
    lead, follower = keyboard(), mouse()
    follower.responses = [r for r in follower.responses if r.id != 0x0420]  # no reply with host cookies
    spy_request = mocker.spy(follower, "request")

    easy_switch.follow(lead, lead.hosts, 1, [follower])

    assert switches(spy_request) == []


@pytest.mark.parametrize("asked", [False, True])
def test_follow_too_late(asked, mocker):
    """A device is not switched, and not even asked, when the deadline has passed"""
    lead, follower = keyboard(), mouse()
    late = 100.0 + easy_switch.DEADLINE + 0.1
    mocker.patch("time.monotonic", side_effect=[100.0, 100.0, late] if asked else [100.0, late])
    spy_request = mocker.spy(follower, "request")

    easy_switch.follow(lead, lead.hosts, 1, [follower])

    assert switches(spy_request) == []
    assert spy_request.called == asked


def test_follow_same_names(mocker):
    """The current host of the mouse, which the keyboard leaves, is not a candidate even if it has the same name"""
    names = {0: (True, "fedora"), 1: (True, "MacBook-Pro"), 2: (True, "fedora")}
    lead, follower = keyboard(names), mouse(0, names=names)
    spy_request = mocker.spy(follower, "request")

    easy_switch.follow(lead, lead.hosts, 0, [follower])

    assert switches(spy_request) == [2]


def test_follow_error(mocker):
    """An error with one device does not keep other devices from following"""
    lead, broken, follower = keyboard(), mouse(name="broken"), mouse()
    mocker.patch.object(broken, "request", side_effect=OSError("device gone"))
    spy_request = mocker.spy(follower, "request")

    easy_switch.follow(lead, lead.hosts, 1, [broken, follower])

    assert switches(spy_request) == [1]


@pytest.mark.parametrize(
    "names, preferred, expected_host",
    [
        ({0: (True, "A"), 1: (True, "B"), 2: (True, "C")}, 0, 1),
        ({0: (True, "B"), 1: (True, "B"), 2: (True, "C")}, 1, 1),
        ({0: (True, "B"), 1: (True, "B"), 2: (True, "C")}, 2, 0),
        ({0: (False, "B"), 1: (True, "A"), 2: (True, "B")}, 0, 2),
        ({0: (True, "A"), 1: (True, "BB"), 2: (True, "C")}, 1, None),
    ],
)
def test_choose_host(names, preferred, expected_host):
    assert easy_switch.choose_host("mouse", names, "B", preferred) == expected_host


@pytest.mark.parametrize(
    "sub_id, address, data, follows",
    [
        (0x04, 0x00, "0201", True),
        (0x04, 0x00, "0202", False),  # same host
        (0x04, 0x10, "0201", False),  # another event
        (0x05, 0x00, "0201", False),  # another feature
        (0x41, 0x00, "0201", False),  # not a feature notification
    ],
)
def test_handler(sub_id, address, data, follows, mocker):
    lead = keyboard()
    hosts = lead.hosts
    lead.features[SupportedFeature.CHANGE_HOST]
    follow = mocker.patch.object(easy_switch, "follow")
    notification = HIDPPNotification(0x11, 1, sub_id, address, bytes.fromhex(data))

    result = easy_switch.handler(lead, notification)

    assert result is None
    assert follow.called == follows
    if follows:  # what is known about the hosts of the leaving keyboard is not used or updated any more
        assert follow.call_args.args[:3] == (lead, hosts, 1)
        assert lead.hosts is None
    else:
        assert lead.hosts is hosts


def test_handler_error(mocker):
    lead = keyboard()
    mocker.patch.object(lead.features, "get_feature", side_effect=IndexError("bad index"))
    notification = HIDPPNotification(0x11, 1, 0x04, 0x00, b"\x02\x01")

    assert easy_switch.handler(lead, notification) is None


def test_read_hosts_keyboard(mocker):
    device = fake_hidpp.Device(feature=SupportedFeature.CHANGE_HOST, version=2, kind="keyboard", unitId="61965D0E")
    spy_request = mocker.spy(device, "request")

    hosts = easy_switch.read_hosts(device, NAMES)

    assert hosts == easy_switch.Hosts(NAMES, b"", 0xB7)
    assert all(call.args[0] >> 8 != 0x04 for call in spy_request.call_args_list)


def test_read_hosts_mouse():
    responses = [fake_hidpp.Response("030200", 0x0400), fake_hidpp.Response("B7B7B7" + "00" * 13, 0x0420)]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.CHANGE_HOST, version=1, kind="mouse")

    hosts = easy_switch.read_hosts(device, NAMES)

    assert hosts == easy_switch.Hosts(NAMES, b"\xb7\xb7\xb7", None)


@pytest.mark.parametrize(
    "kind, version, hosts_info, unit_id, present",
    [
        ("keyboard", 2, True, "61965D0E", True),
        ("keyboard", 1, True, "61965D0E", False),
        ("mouse", 2, True, "61965D0E", False),
        ("keyboard", 2, False, "61965D0E", False),
        ("keyboard", 2, True, "D5F4B3B2", False),  # link cookie 0
        ("keyboard", 2, True, None, False),
    ],
)
def test_setting_present(kind, version, hosts_info, unit_id, present):
    responses = [fake_hidpp.Response("050003", 0x0000, "1815")] if hosts_info else []
    device = fake_hidpp.Device(
        responses=responses, feature=SupportedFeature.CHANGE_HOST, version=version, kind=kind, unitId=unit_id
    )

    setting = settings_templates.check_feature(device, settings_templates.EnhancedEasySwitch)

    assert bool(setting) == present


def test_setting(mocker):
    """The setting is on by default and adds its notification handler once"""
    responses = [fake_hidpp.Response("050003", 0x0000, "1815")]
    device = fake_hidpp.Device(
        responses=responses, feature=SupportedFeature.CHANGE_HOST, version=2, kind="keyboard", unitId="61965D0E"
    )
    device.add_notification_handler = mocker.Mock()
    follow = mocker.patch.object(easy_switch, "follow")
    notification = HIDPPNotification(0x11, 1, 0x04, 0x00, b"\x02\x01")
    setting = settings_templates.check_feature(device, settings_templates.EnhancedEasySwitch)

    assert setting.read() is True
    assert not setting.live_readable  # only Solaar knows the value
    setting.apply()
    setting.write(False)
    setting.write(True)

    device.add_notification_handler.assert_called_once()
    name, handler = device.add_notification_handler.call_args.args
    assert name == "enhanced-easy-switch"
    assert handler(device, notification) is None
    assert follow.call_count == 1
    setting.write(False)
    assert handler(device, notification) is None
    assert follow.call_count == 1


def test_change_host_apply(mocker):
    """When a device becomes active, what is needed about its hosts is read"""
    mocker.patch("socket.gethostname", return_value="omarchy-desktop.lan")
    responses = [
        fake_hidpp.Response("050003", 0x0000, "1815"),  # HOSTS_INFO at 0x05
        fake_hidpp.Response("030200", 0x0400),
        fake_hidpp.Response("B7B7B7" + "00" * 13, 0x0420),
        fake_hidpp.Response("13080302", 0x0500),
        fake_hidpp.Response("000105010D18", 0x0510, "00"),
        fake_hidpp.Response("0000574F524B2D4C4150544F502D31", 0x0530, "0000"),
        fake_hidpp.Response("010104011418", 0x0510, "01"),
        fake_hidpp.Response("0100416C6578E2809973204D6163426F", 0x0530, "0100"),
        fake_hidpp.Response("010E6F6B2050726F", 0x0530, "010E"),
        fake_hidpp.Response("020105010F18", 0x0510, "02"),
        fake_hidpp.Response("02006F6D61726368792D6465736B746F", 0x0530, "0200"),
        fake_hidpp.Response("020E70", 0x0530, "020E"),
    ]
    device = fake_hidpp.Device(responses=responses, feature=SupportedFeature.CHANGE_HOST, version=1, kind="mouse")
    setting = settings_templates.check_feature(device, settings_templates.ChangeHost)

    setting.apply()

    assert device.hosts == easy_switch.Hosts(NAMES, b"\xb7\xb7\xb7", None)


def test_change_host_apply_error(mocker):
    """If the hosts of a device can't be read when it becomes active, nothing from an earlier connection is kept"""
    device = fake_hidpp.Device(
        responses=[fake_hidpp.Response("050003", 0x0000, "1815"), fake_hidpp.Response("030200", 0x0400)],
        feature=SupportedFeature.CHANGE_HOST,
        version=1,
        kind="mouse",
    )
    setting = settings_templates.check_feature(device, settings_templates.ChangeHost)
    device.hosts = easy_switch.Hosts(NAMES, b"\xb7\xb7\xb7")
    mocker.patch.object(settings_templates._hidpp20, "get_host_names", side_effect=exceptions.FeatureCallError())

    setting.apply()

    assert device.hosts is None
