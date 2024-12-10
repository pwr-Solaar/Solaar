from __future__ import annotations

import logging
import math

from enum import IntEnum

from logitech_receiver import common
from logitech_receiver.common import NamedInt
from logitech_receiver.common import NamedInts

logger = logging.getLogger(__name__)


def bool_or_toggle(current: bool | str, new: bool | str) -> bool:
    if isinstance(new, bool):
        return new

    try:
        return bool(int(new))
    except (TypeError, ValueError):
        new = str(new).lower()

    if new in ("true", "yes", "on", "t", "y"):
        return True
    if new in ("false", "no", "off", "f", "n"):
        return False
    if new in ("~", "toggle"):
        return not current
    return None


class Kind(IntEnum):
    TOGGLE = 0x01
    CHOICE = 0x02
    RANGE = 0x04
    MAP_CHOICE = 0x0A
    MULTIPLE_TOGGLE = 0x10
    PACKED_RANGE = 0x20
    MULTIPLE_RANGE = 0x40
    HETERO = 0x80


class Validator:
    @classmethod
    def build(cls, setting_class, device, **kwargs) -> Validator:
        return cls(**kwargs)

    @classmethod
    def to_string(cls, value) -> str:
        return str(value)

    def compare(self, args, current):
        if len(args) != 1:
            return False
        return args[0] == current


class BooleanValidator(Validator):
    __slots__ = ("true_value", "false_value", "read_skip_byte_count", "write_prefix_bytes", "mask", "needs_current_value")

    kind = Kind.TOGGLE
    default_true = 0x01
    default_false = 0x00
    # mask specifies all the affected bits in the value
    default_mask = 0xFF

    def __init__(
        self,
        true_value=default_true,
        false_value=default_false,
        mask=default_mask,
        read_skip_byte_count=0,
        write_prefix_bytes=b"",
    ):
        if isinstance(true_value, int):
            assert isinstance(false_value, int)
            if mask is None:
                mask = self.default_mask
            else:
                assert isinstance(mask, int)
            assert true_value & false_value == 0
            assert true_value & mask == true_value
            assert false_value & mask == false_value
            self.needs_current_value = mask != self.default_mask
        elif isinstance(true_value, bytes):
            if false_value is None or false_value == self.default_false:
                false_value = b"\x00" * len(true_value)
            else:
                assert isinstance(false_value, bytes)
            if mask is None or mask == self.default_mask:
                mask = b"\xff" * len(true_value)
            else:
                assert isinstance(mask, bytes)
            assert len(mask) == len(true_value) == len(false_value)
            tv = common.bytes2int(true_value)
            fv = common.bytes2int(false_value)
            mv = common.bytes2int(mask)
            assert tv != fv  # true and false might be something other than bit values
            assert tv & mv == tv
            assert fv & mv == fv
            self.needs_current_value = any(m != 0xFF for m in mask)
        else:
            raise Exception(f"invalid mask '{mask!r}', type {type(mask)}")

        self.true_value = true_value
        self.false_value = false_value
        self.mask = mask
        self.read_skip_byte_count = read_skip_byte_count
        self.write_prefix_bytes = write_prefix_bytes

    def validate_read(self, reply_bytes):
        reply_bytes = reply_bytes[self.read_skip_byte_count :]
        if isinstance(self.mask, int):
            reply_value = ord(reply_bytes[:1]) & self.mask
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("BooleanValidator: validate read %r => %02X", reply_bytes, reply_value)
            if reply_value == self.true_value:
                return True
            if reply_value == self.false_value:
                return False
            logger.warning(
                "BooleanValidator: reply %02X mismatched %02X/%02X/%02X",
                reply_value,
                self.true_value,
                self.false_value,
                self.mask,
            )
            return False

        count = len(self.mask)
        mask = common.bytes2int(self.mask)
        reply_value = common.bytes2int(reply_bytes[:count]) & mask

        true_value = common.bytes2int(self.true_value)
        if reply_value == true_value:
            return True

        false_value = common.bytes2int(self.false_value)
        if reply_value == false_value:
            return False

        logger.warning(
            "BooleanValidator: reply %r mismatched %r/%r/%r", reply_bytes, self.true_value, self.false_value, self.mask
        )
        return False

    def prepare_write(self, new_value, current_value=None):
        if new_value is None:
            new_value = False
        else:
            assert isinstance(new_value, bool), f"New value {new_value} for boolean setting is not a boolean"

        to_write = self.true_value if new_value else self.false_value

        if isinstance(self.mask, int):
            if current_value is not None and self.needs_current_value:
                to_write |= ord(current_value[:1]) & (0xFF ^ self.mask)
            if current_value is not None and to_write == ord(current_value[:1]):
                return None
            to_write = bytes([to_write])
        else:
            to_write = bytearray(to_write)
            count = len(self.mask)
            for i in range(0, count):
                b = ord(to_write[i : i + 1])
                m = ord(self.mask[i : i + 1])
                assert b & m == b
                # b &= m
                if current_value is not None and self.needs_current_value:
                    b |= ord(current_value[i : i + 1]) & (0xFF ^ m)
                to_write[i] = b
            to_write = bytes(to_write)

            if current_value is not None and to_write == current_value[: len(to_write)]:
                return None

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("BooleanValidator: prepare_write(%s, %s) => %r", new_value, current_value, to_write)

        return self.write_prefix_bytes + to_write

    def acceptable(self, args, current):
        if len(args) != 1:
            return None
        val = bool_or_toggle(current, args[0])
        return [val] if val is not None else None


class BitFieldValidator(Validator):
    __slots__ = ("byte_count", "options")

    kind = Kind.MULTIPLE_TOGGLE

    def __init__(self, options, byte_count=None):
        assert isinstance(options, list)
        self.options = options
        self.byte_count = (max(x.bit_length() for x in options) + 7) // 8
        if byte_count:
            assert isinstance(byte_count, int) and byte_count >= self.byte_count
            self.byte_count = byte_count

    def to_string(self, value) -> str:
        def element_to_string(key, val):
            k = next((k for k in self.options if int(key) == k), None)
            return str(k) + ":" + str(val) if k is not None else "?"

        return "{" + ", ".join([element_to_string(k, value[k]) for k in value]) + "}"

    def validate_read(self, reply_bytes):
        r = common.bytes2int(reply_bytes[: self.byte_count])
        value = {int(k): False for k in self.options}
        m = 1
        for _ignore in range(8 * self.byte_count):
            if m in self.options:
                value[int(m)] = bool(r & m)
            m <<= 1
        return value

    def prepare_write(self, new_value):
        assert isinstance(new_value, dict)
        w = 0
        for k, v in new_value.items():
            if v:
                w |= int(k)
        return common.int2bytes(w, self.byte_count)

    def get_options(self):
        return self.options

    def acceptable(self, args, current):
        if len(args) != 2:
            return None
        key = next((key for key in self.options if key == args[0]), None)
        if key is None:
            return None
        val = bool_or_toggle(current[int(key)], args[1])
        return None if val is None else [int(key), val]

    def compare(self, args, current):
        if len(args) != 2:
            return False
        key = next((key for key in self.options if key == args[0]), None)
        if key is None:
            return False
        return args[1] == current[int(key)]


class BitFieldWithOffsetAndMaskValidator(Validator):
    __slots__ = ("byte_count", "options", "_option_from_key", "_mask_from_offset", "_option_from_offset_mask")

    kind = Kind.MULTIPLE_TOGGLE
    sep = 0x01

    def __init__(self, options, om_method=None, byte_count=None):
        assert isinstance(options, list)
        # each element of options is an instance of a class
        # that has an id (which is used as an index in other dictionaries)
        # and where om_method is a method that returns a byte offset and byte mask
        # that says how to access and modify the bit toggle for the option
        self.options = options
        self.om_method = om_method
        # to retrieve the options efficiently:
        self._option_from_key = {}
        self._mask_from_offset = {}
        self._option_from_offset_mask = {}
        for opt in options:
            offset, mask = om_method(opt)
            self._option_from_key[int(opt)] = opt
            try:
                self._mask_from_offset[offset] |= mask
            except KeyError:
                self._mask_from_offset[offset] = mask
            try:
                mask_to_opt = self._option_from_offset_mask[offset]
            except KeyError:
                mask_to_opt = {}
                self._option_from_offset_mask[offset] = mask_to_opt
            mask_to_opt[mask] = opt
        self.byte_count = (max(om_method(x)[1].bit_length() for x in options) + 7) // 8  # is this correct??
        if byte_count:
            assert isinstance(byte_count, int) and byte_count >= self.byte_count
            self.byte_count = byte_count

    def prepare_read(self):
        r = []
        for offset, mask in self._mask_from_offset.items():
            b = offset << (8 * (self.byte_count + 1))
            b |= (self.sep << (8 * self.byte_count)) | mask
            r.append(common.int2bytes(b, self.byte_count + 2))
        return r

    def prepare_read_key(self, key):
        option = self._option_from_key.get(key, None)
        if option is None:
            return None
        offset, mask = option.om_method(option)
        b = offset << (8 * (self.byte_count + 1))
        b |= (self.sep << (8 * self.byte_count)) | mask
        return common.int2bytes(b, self.byte_count + 2)

    def validate_read(self, reply_bytes_dict):
        values = {int(k): False for k in self.options}
        for query, b in reply_bytes_dict.items():
            offset = common.bytes2int(query[0:1])
            b += (self.byte_count - len(b)) * b"\x00"
            value = common.bytes2int(b[: self.byte_count])
            mask_to_opt = self._option_from_offset_mask.get(offset, {})
            m = 1
            for _ignore in range(8 * self.byte_count):
                if m in mask_to_opt:
                    values[int(mask_to_opt[m])] = bool(value & m)
                m <<= 1
        return values

    def prepare_write(self, new_value):
        assert isinstance(new_value, dict)
        w = {}
        for k, v in new_value.items():
            option = self._option_from_key[int(k)]
            offset, mask = self.om_method(option)
            if offset not in w:
                w[offset] = 0
            if v:
                w[offset] |= mask
        return [
            common.int2bytes(
                (offset << (8 * (2 * self.byte_count + 1)))
                | (self.sep << (16 * self.byte_count))
                | (self._mask_from_offset[offset] << (8 * self.byte_count))
                | value,
                2 * self.byte_count + 2,
            )
            for offset, value in w.items()
        ]

    def get_options(self):
        return [int(opt) if isinstance(opt, int) else opt.as_int() for opt in self.options]

    def acceptable(self, args, current):
        if len(args) != 2:
            return None
        key = next((option.id for option in self.options if option.as_int() == args[0]), None)
        if key is None:
            return None
        val = bool_or_toggle(current[int(key)], args[1])
        return None if val is None else [int(key), val]

    def compare(self, args, current):
        if len(args) != 2:
            return False
        key = next((option.id for option in self.options if option.as_int() == args[0]), None)
        if key is None:
            return False
        return args[1] == current[int(key)]


class ChoicesValidator(Validator):
    """Translates between NamedInts and a byte sequence.
    :param choices: a list of NamedInts
    :param byte_count: the size of the derived byte sequence. If None, it
    will be calculated from the choices."""

    kind = Kind.CHOICE

    def __init__(self, choices=None, byte_count=None, read_skip_byte_count=0, write_prefix_bytes=b""):
        assert choices is not None
        assert isinstance(choices, NamedInts)
        assert len(choices) > 1
        self.choices = choices
        self.needs_current_value = False

        max_bits = max(x.bit_length() for x in choices)
        self._byte_count = (max_bits // 8) + (1 if max_bits % 8 else 0)
        if byte_count:
            assert self._byte_count <= byte_count
            self._byte_count = byte_count
        assert self._byte_count < 8
        self._read_skip_byte_count = read_skip_byte_count
        self._write_prefix_bytes = write_prefix_bytes if write_prefix_bytes else b""
        assert self._byte_count + self._read_skip_byte_count <= 14
        assert self._byte_count + len(self._write_prefix_bytes) <= 14

    def to_string(self, value) -> str:
        return str(self.choices[value]) if isinstance(value, int) else str(value)

    def validate_read(self, reply_bytes):
        reply_value = common.bytes2int(reply_bytes[self._read_skip_byte_count : self._read_skip_byte_count + self._byte_count])
        valid_value = self.choices[reply_value]
        assert valid_value is not None, f"{self.__class__.__name__}: failed to validate read value {reply_value:02X}"
        return valid_value

    def prepare_write(self, new_value, current_value=None):
        if new_value is None:
            value = self.choices[:][0]
        else:
            value = self.choice(new_value)
        if value is None:
            raise ValueError(f"invalid choice {new_value!r}")
        assert isinstance(value, NamedInt)
        return self._write_prefix_bytes + value.bytes(self._byte_count)

    def choice(self, value):
        if isinstance(value, int):
            return self.choices[value]
        try:
            int(value)
            if int(value) in self.choices:
                return self.choices[int(value)]
        except Exception:
            pass
        if value in self.choices:
            return self.choices[value]
        else:
            return None

    def acceptable(self, args, current):
        choice = self.choice(args[0]) if len(args) == 1 else None
        return None if choice is None else [choice]


class ChoicesMapValidator(ChoicesValidator):
    kind = Kind.MAP_CHOICE

    def __init__(
        self,
        choices_map,
        key_byte_count=0,
        key_postfix_bytes=b"",
        byte_count=0,
        read_skip_byte_count=0,
        write_prefix_bytes=b"",
        extra_default=None,
        mask=-1,
        activate=0,
    ):
        assert choices_map is not None
        assert isinstance(choices_map, dict)
        max_key_bits = 0
        max_value_bits = 0
        for key, choices in choices_map.items():
            assert isinstance(key, NamedInt)
            assert isinstance(choices, NamedInts)
            max_key_bits = max(max_key_bits, key.bit_length())
            for key_value in choices:
                assert isinstance(key_value, NamedInt)
                max_value_bits = max(max_value_bits, key_value.bit_length())
        self._key_byte_count = (max_key_bits + 7) // 8
        if key_byte_count:
            assert self._key_byte_count <= key_byte_count
            self._key_byte_count = key_byte_count
        self._byte_count = (max_value_bits + 7) // 8
        if byte_count:
            assert self._byte_count <= byte_count
            self._byte_count = byte_count

        self.choices = choices_map
        self.needs_current_value = False
        self.extra_default = extra_default
        self._key_postfix_bytes = key_postfix_bytes
        self._read_skip_byte_count = read_skip_byte_count if read_skip_byte_count else 0
        self._write_prefix_bytes = write_prefix_bytes if write_prefix_bytes else b""
        self.activate = activate
        self.mask = mask
        assert self._byte_count + self._read_skip_byte_count + self._key_byte_count <= 14
        assert self._byte_count + len(self._write_prefix_bytes) + self._key_byte_count <= 14

    def to_string(self, value) -> str:
        def element_to_string(key, val):
            k, c = next(((k, c) for k, c in self.choices.items() if int(key) == k), (None, None))
            return str(k) + ":" + str(c[val]) if k is not None else "?"

        return "{" + ", ".join([element_to_string(k, value[k]) for k in sorted(value)]) + "}"

    def validate_read(self, reply_bytes, key):
        start = self._key_byte_count + self._read_skip_byte_count
        end = start + self._byte_count
        reply_value = common.bytes2int(reply_bytes[start:end]) & self.mask
        # reprogrammable keys starts out as 0, which is not a choice, so don't use assert here
        if self.extra_default is not None and self.extra_default == reply_value:
            return int(self.choices[key][0])
        if reply_value not in self.choices[key]:
            assert reply_value in self.choices[key], "%s: failed to validate read value %02X" % (
                self.__class__.__name__,
                reply_value,
            )
        return reply_value

    def prepare_key(self, key):
        return key.to_bytes(self._key_byte_count, "big") + self._key_postfix_bytes

    def prepare_write(self, key, new_value):
        choices = self.choices.get(key)
        if choices is None or (new_value not in choices and new_value != self.extra_default):
            logger.error("invalid choice %r for %s", new_value, key)
            return None
        new_value = new_value | self.activate
        return self._write_prefix_bytes + new_value.to_bytes(self._byte_count, "big")

    def acceptable(self, args, current):
        if len(args) != 2:
            return None
        key, choices = next(((key, item) for key, item in self.choices.items() if key == args[0]), (None, None))
        if choices is None or args[1] not in choices:
            return None
        choice = next((item for item in choices if item == args[1]), None)
        return [int(key), int(choice)] if choice is not None else None

    def compare(self, args, current):
        if len(args) != 2:
            return False
        key = next((key for key in self.choices if key == int(args[0])), None)
        if key is None:
            return False
        return args[1] == current[int(key)]


class RangeValidator(Validator):
    kind = Kind.RANGE
    """Translates between integers and a byte sequence.
    :param min_value: minimum accepted value (inclusive)
    :param max_value: maximum accepted value (inclusive)
    :param byte_count: the size of the derived byte sequence. If None, it
    will be calculated from the range."""
    min_value = 0
    max_value = 255

    @classmethod
    def build(cls, setting_class, device, **kwargs):
        kwargs["min_value"] = setting_class.min_value
        kwargs["max_value"] = setting_class.max_value
        return cls(**kwargs)

    def __init__(self, min_value=0, max_value=255, byte_count=1):
        assert max_value > min_value
        self.min_value = min_value
        self.max_value = max_value
        self.needs_current_value = True  # read and check before write (needed for ADC power and probably a good idea anyway)

        self._byte_count = math.ceil(math.log(max_value + 1, 256))
        if byte_count:
            assert self._byte_count <= byte_count
            self._byte_count = byte_count
        assert self._byte_count < 8

    def validate_read(self, reply_bytes):
        reply_value = common.bytes2int(reply_bytes[: self._byte_count])
        assert reply_value >= self.min_value, f"{self.__class__.__name__}: failed to validate read value {reply_value:02X}"
        assert reply_value <= self.max_value, f"{self.__class__.__name__}: failed to validate read value {reply_value:02X}"
        return reply_value

    def prepare_write(self, new_value, current_value=None):
        if new_value < self.min_value or new_value > self.max_value:
            raise ValueError(f"invalid choice {new_value!r}")
        current_value = self.validate_read(current_value) if current_value is not None else None
        to_write = common.int2bytes(new_value, self._byte_count)
        # current value is known and same as value to be written return None to signal not to write it
        return None if current_value is not None and current_value == new_value else to_write

    def acceptable(self, args, current):
        arg = args[0]
        #  None if len(args) != 1 or type(arg) != int or arg < self.min_value or arg > self.max_value else args)
        return None if len(args) != 1 or isinstance(arg, int) or arg < self.min_value or arg > self.max_value else args

    def compare(self, args, current):
        if len(args) == 1:
            return args[0] == current
        elif len(args) == 2:
            return args[0] <= current <= args[1]
        else:
            return False


class HeteroValidator(Validator):
    kind = Kind.HETERO

    @classmethod
    def build(cls, setting_class, device, **kwargs):
        return cls(**kwargs)

    def __init__(self, data_class=None, options=None, readable=True):
        assert data_class is not None and options is not None
        self.data_class = data_class
        self.options = options
        self.readable = readable
        self.needs_current_value = False

    def validate_read(self, reply_bytes):
        if self.readable:
            reply_value = self.data_class.from_bytes(reply_bytes, options=self.options)
            return reply_value

    def prepare_write(self, new_value, current_value=None):
        to_write = new_value.to_bytes(options=self.options)
        return to_write

    def acceptable(self, args, current):  # should this actually do some checking?
        return True


class PackedRangeValidator(Validator):
    kind = Kind.PACKED_RANGE
    """Several range values, all the same size, all the same min and max"""
    min_value = 0
    max_value = 255
    count = 1
    rsbc = 0
    write_prefix_bytes = b""

    def __init__(
        self, keys, min_value=0, max_value=255, count=1, byte_count=1, read_skip_byte_count=0, write_prefix_bytes=b""
    ):
        assert max_value > min_value
        self.needs_current_value = True
        self.keys = keys
        self.min_value = min_value
        self.max_value = max_value
        self.count = count
        self.bc = math.ceil(math.log(max_value + 1 - min(0, min_value), 256))
        if byte_count:
            assert self.bc <= byte_count
            self.bc = byte_count
        assert self.bc * self.count
        self.rsbc = read_skip_byte_count
        self.write_prefix_bytes = write_prefix_bytes

    def validate_read(self, reply_bytes):
        rvs = {
            n: common.bytes2int(reply_bytes[self.rsbc + n * self.bc : self.rsbc + (n + 1) * self.bc], signed=True)
            for n in range(self.count)
        }
        for n in range(self.count):
            assert rvs[n] >= self.min_value, f"{self.__class__.__name__}: failed to validate read value {rvs[n]:02X}"
            assert rvs[n] <= self.max_value, f"{self.__class__.__name__}: failed to validate read value {rvs[n]:02X}"
        return rvs

    def prepare_write(self, new_values):
        if len(new_values) != self.count:
            raise ValueError(f"wrong number of values {new_values!r}")
        for new_value in new_values.values():
            if new_value < self.min_value or new_value > self.max_value:
                raise ValueError(f"invalid value {new_value!r}")
        bytes = self.write_prefix_bytes + b"".join(
            common.int2bytes(new_values[n], self.bc, signed=True) for n in range(self.count)
        )
        return bytes

    def acceptable(self, args, current):
        if len(args) != 2 or int(args[0]) < 0 or int(args[0]) >= self.count:
            return None
        return None if not isinstance(args[1], int) or args[1] < self.min_value or args[1] > self.max_value else args

    def compare(self, args, current):
        logger.warning("compare not implemented for packed range settings")
        return False


class MultipleRangeValidator(Validator):
    kind = Kind.MULTIPLE_RANGE

    def __init__(self, items, sub_items):
        assert isinstance(items, list)  # each element must have .index and its __int__ must return its id (not its index)
        assert isinstance(sub_items, dict)
        # sub_items: items -> class with .minimum, .maximum, .length (in bytes), .id (a string) and .widget (e.g. 'Scale')
        self.items = items
        self.keys = NamedInts(**{str(item): int(item) for item in items})
        self._item_from_id = {int(k): k for k in items}
        self.sub_items = sub_items

    def prepare_read_item(self, item):
        return common.int2bytes((self._item_from_id[int(item)].index << 1) | 0xFF, 2)

    def validate_read_item(self, reply_bytes, item):
        item = self._item_from_id[int(item)]
        start = 0
        value = {}
        for sub_item in self.sub_items[item]:
            r = reply_bytes[start : start + sub_item.length]
            if len(r) < sub_item.length:
                r += b"\x00" * (sub_item.length - len(value))
            v = common.bytes2int(r)
            if not (sub_item.minimum < v < sub_item.maximum):
                logger.warning(
                    f"{self.__class__.__name__}: failed to validate read value for {item}.{sub_item}: "
                    + f"{v} not in [{sub_item.minimum}..{sub_item.maximum}]"
                )
            value[str(sub_item)] = v
            start += sub_item.length
        return value

    def prepare_write(self, value):
        seq = []
        w = b""
        for item in value.keys():
            _item = self._item_from_id[int(item)]
            b = common.int2bytes(_item.index, 1)
            for sub_item in self.sub_items[_item]:
                try:
                    v = value[int(item)][str(sub_item)]
                except KeyError:
                    return None
                if not (sub_item.minimum <= v <= sub_item.maximum):
                    raise ValueError(
                        f"invalid choice for {item}.{sub_item}: {v} not in [{sub_item.minimum}..{sub_item.maximum}]"
                    )
                b += common.int2bytes(v, sub_item.length)
            if len(w) + len(b) > 15:
                seq.append(b + b"\xff")
                w = b""
            w += b
        seq.append(w + b"\xff")
        return seq

    def prepare_write_item(self, item, value):
        _item = self._item_from_id[int(item)]
        w = common.int2bytes(_item.index, 1)
        for sub_item in self.sub_items[_item]:
            try:
                v = value[str(sub_item)]
            except KeyError:
                return None
            if not (sub_item.minimum <= v <= sub_item.maximum):
                raise ValueError(f"invalid choice for {item}.{sub_item}: {v} not in [{sub_item.minimum}..{sub_item.maximum}]")
            w += common.int2bytes(v, sub_item.length)
        return w + b"\xff"

    def acceptable(self, args, current):
        # just one item, with at least one sub-item
        if not isinstance(args, list) or len(args) != 2 or not isinstance(args[1], dict):
            return None
        item = next((p for p in self.items if p.id == args[0] or str(p) == args[0]), None)
        if not item:
            return None
        for sub_key, value in args[1].items():
            sub_item = next((it for it in self.sub_items[item] if it.id == sub_key), None)
            if not sub_item:
                return None
            if not isinstance(value, int) or not (sub_item.minimum <= value <= sub_item.maximum):
                return None
        return [int(item), {**args[1]}]

    def compare(self, args, current):
        logger.warning("compare not implemented for multiple range settings")
        return False
