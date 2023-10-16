from typing import List, Dict, Tuple
from enum import Enum
import hid
import win32api
import win32file
import win32event
import winerror
from .helpers import get_parent_instance

def enumerate_devices():
    # group infos by parent
    info_dict = {}
    for sub_info in hid.enumerate(0, 0):
        sub_info['path'] = sub_info['path'].decode('utf-8')
        parent_inst = get_parent_instance(sub_info['path'])
        if not parent_inst:
            continue
        info = info_dict.get(parent_inst)
        if info is None:
            info_dict[parent_inst] = sub_info
        else:
            for key in sub_info.keys():
                if key in ['path', 'usage', 'usage_page']:
                    continue
                assert info[key] == sub_info[key]
            info.update({'path': info['path'] + ';' + sub_info['path']})

    return info_dict.values()

class SubDevice:
    def __init__(self):
        self.handle = win32file.INVALID_HANDLE_VALUE
        self.read_ov = win32file.OVERLAPPED()
        self.write_ov = win32file.OVERLAPPED()
        self.read_pending = False
        self.read_buffer = win32file.AllocateReadBuffer(32)

    def __del__(self):
        self.close()

    def open(self, path: str):
        self.handle = win32file.CreateFileW(
            path,
            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
            win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
            None,
            win32file.OPEN_EXISTING,
            win32file.FILE_FLAG_OVERLAPPED,
            None
        )
        if self.handle == win32file.INVALID_HANDLE_VALUE:
            return False
        self.read_ov.hEvent = win32event.CreateEvent(None, False, False, None)
        self.write_ov.hEvent = win32event.CreateEvent(None, False, False, None)
        return True
    
    def close(self):
        win32api.CloseHandle(self.handle)
        win32api.CloseHandle(self.read_ov.hEvent)
        win32api.CloseHandle(self.write_ov.hEvent)
    
    def write(self, data: bytes):
        err, bytes_written = win32file.WriteFile(self.handle, data, self.write_ov)
        if err == winerror.ERROR_IO_PENDING:
            bytes_written = win32file.GetOverlappedResult(self.handle, self.write_ov, True)
        return bytes_written
    
class SubDeviceReadTask:
    def __init__(self, sub_devices: List[SubDevice]=[]):
        self.sub_devices = sub_devices

    def add(self, sub_device: SubDevice):
        self.sub_devices.append(sub_device)

    def finish(self, length: int, timeout: int):
        result_device_idx = -1

        for i, sub_device in enumerate(self.sub_devices):
            if not sub_device.read_pending:
                win32event.ResetEvent(sub_device.read_ov.hEvent)
                sub_device.read_pending = True
                if sub_device.read_buffer.nbytes != length:
                    sub_device.read_buffer = win32file.AllocateReadBuffer(length)
                err, _ = win32file.ReadFile(sub_device.handle, sub_device.read_buffer, sub_device.read_ov)
                if err:
                    if err != winerror.ERROR_IO_PENDING:
                        raise IOError()
                else:
                    sub_device.read_pending = False
                    result_device_idx = i
                    break

        if result_device_idx < 0:
            wait_result = win32event.WaitForMultipleObjects(
                [sub_device.read_ov.hEvent for sub_device in self.sub_devices],
                False,
                timeout if timeout >= 0 else win32event.INFINITE
            )

            if wait_result >= win32event.WAIT_OBJECT_0 and\
                wait_result < win32event.WAIT_OBJECT_0 + len(self.sub_devices):
                result_device_idx = wait_result - win32event.WAIT_OBJECT_0
                sub_device = self.sub_devices[result_device_idx]
                sub_device.read_pending = False
                bytes_read = win32file.GetOverlappedResult(sub_device.handle, sub_device.read_ov, False)
            else:
                return bytes()
            
        return bytes(self.sub_devices[result_device_idx].read_buffer.obj[:bytes_read])
                    
                    
class Device:
    def __init__(self):
        self.sub_devices: Dict[int, SubDevice] = {}

    def __del__(self):
        self.close()

    def open(self, joined_paths: str):
        paths = joined_paths.split(';')
        for path in paths:
            dev = hid.device()
            dev.open_path(path.encode('utf-8'))
            report_id = None
            for (id, length) in zip((0x10, 0x11), (7, 20)):
                try:
                    data = dev.get_input_report(id, 32)
                except IOError:
                    continue
                if len(data) == length:
                    report_id = id
                    break        
            if report_id is not None:
                assert self.sub_devices.get(report_id) is None
                sub_device = SubDevice()
                if not sub_device.open(path):
                    continue
                self.sub_devices[report_id] = sub_device
            dev.close()

        return len(self.sub_devices) > 0
    
    def close(self):
        for sub_device in self.sub_devices.values():
            sub_device.close()
        self.sub_devices = {}

    def read(self, length: int, timeout: int):
        return SubDeviceReadTask(list(self.sub_devices.values())).finish(length, timeout)

    def write(self, data: bytes):
        if len(data) == 0:
            raise ValueError()
        report_id = int.from_bytes(data[0:1], 'big')
        return self.sub_devices[report_id].write(data)

# A device manager to map devices to integers
class DeviceManager:
    __instance = None

    def __init__(self):
        self.devices: Dict[int, Device] = {}
        # start at 1 to pass boolean checks
        self.device_counter = 1

    @classmethod
    def get(cls):
        return cls.__instance
    
    @classmethod
    def init(cls):
        cls.__instance = DeviceManager()

    def open_path(self, path: str):
        device = Device()
        device.open(path)
        handle = self.device_counter
        self.devices[handle] = device
        self.device_counter += 1
        return handle
    
    def close(self, handle: int):
        device = self.devices[handle]
        device.close()
        self.devices.pop(handle)

    def read(self, handle: int, bytes_count, timeout_ms=-1):
        return self.devices[handle].read(bytes_count, timeout_ms)

    def write(self, handle: int, data: bytes):
        return self.devices[handle].write(data)

    def get_info(self, handle: int):
        return self.devices[handle].info

DeviceManager.init()