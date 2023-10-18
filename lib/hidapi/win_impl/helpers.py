import ctypes
from ctypes import windll, create_unicode_buffer, c_ulong, c_ushort, c_byte, c_ubyte, POINTER, byref
from ctypes.wintypes import LPCWSTR, ULONG, PULONG, PBYTE, DWORD

class GUID(ctypes.Structure):
    _fields_ = [
        ('Data1', c_ulong),
        ('Data2', c_ushort),
        ('Data3', c_ushort),
        ('Data4', c_ubyte * 8)
    ]

class DEVPROPKEY(ctypes.Structure):
    _fields_ = [
        ('fmtid', GUID),
        ('pid', ULONG)
    ]

    def __init__(self, l, w1, w2, b1, b2, b3, b4, b5, b6, b7, b8, _pid):
        super().__init__(
            fmtid=GUID(
                Data1=l,
                Data2=w1,
                Data3=w2,
                Data4=(c_ubyte * 8)(b1, b2, b3, b4, b5, b6, b7, b8)
            ),
            pid=_pid
        )

CR_SUCCESS = 0x00000000
CR_BUFFER_SMALL = 0x0000001A
DEVPROP_TYPE_STRING = 0x00000012
CM_LOCATE_DEVNODE_NORMAL = 0x00000000
DEVPKEY_Device_InstanceId = DEVPROPKEY(0x78c34fc8, 0x104a, 0x4aca, 0x9e, 0xa4, 0x52, 0x4d, 0x52, 0x99, 0x6e, 0x57, 256)

CM_Get_Device_Interface_PropertyW = windll.cfgmgr32.CM_Get_Device_Interface_PropertyW
CM_Locate_DevNodeW = windll.cfgmgr32.CM_Locate_DevNodeW
CM_Get_Parent = windll.cfgmgr32.CM_Get_Parent

def get_parent_instance(path: str) -> int|None:
    prop_type = c_ulong()
    length = c_ulong(0)

    path_unicode = create_unicode_buffer(path)
    
    cr = CM_Get_Device_Interface_PropertyW(
        path_unicode,
        byref(DEVPKEY_Device_InstanceId),
        byref(prop_type),
        None,
        byref(length),
        c_ulong(0)
    )

    if (cr != CR_SUCCESS and cr != CR_BUFFER_SMALL) or prop_type.value != DEVPROP_TYPE_STRING:
        return None
    
    instance_id = (c_byte * length.value)()
    
    cr = CM_Get_Device_Interface_PropertyW(
        path_unicode,
        byref(DEVPKEY_Device_InstanceId),
        byref(prop_type),
        instance_id,
        byref(length),
        c_ulong(0)
    )

    if cr != CR_SUCCESS:
        return None
    
    dev_inst = DWORD()
    cr = CM_Locate_DevNodeW(byref(dev_inst), instance_id, CM_LOCATE_DEVNODE_NORMAL)

    if cr != CR_SUCCESS:
        return None
    
    dev_inst_parent = DWORD()
    cr = CM_Get_Parent(byref(dev_inst_parent), dev_inst, 0)

    if cr != CR_SUCCESS:
        return None
    
    return dev_inst_parent.value
    

    
