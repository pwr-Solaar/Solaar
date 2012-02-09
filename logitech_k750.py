#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import sys
import time
import usb.core, usb.util

"""
    Logitech Wireless Solar Keyboard K750 lux and power readings on Linux
    Requires pyusb >= 1.0.0-a1

    Copyright (©) <2011> <Noah K. Tilton noahktilton@gmail.com>

    Permission is hereby granted, free of charge, to any person
    obtaining a copy of this software and associated documentation files
    (the "Software"), to deal in the Software without restriction,
    including without limitation the rights to use, copy, modify, merge,
    publish, distribute, sublicense, and/or sell copies of the Software,
    and to permit persons to whom the Software is furnished to do so,
    subject to the following conditions:

    The above copyright notice and this permission notice shall be
    included in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
    OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
    HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
    WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
    OTHER DEALINGS IN THE SOFTWARE.
"""

class USB(object):

    def __init__(self, vendor_id, product_id):
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.device = usb.core.find(idVendor=self.vendor_id, idProduct=self.product_id)

        if self.device is None: sys.exit('No device found: %s, %s' % \
                (self.vendor_id, self.product_id))
        self.interface = None
        for config in self.device:
            for interface in config:
                # bInterfaceProtocol 1 is keyboard, per USB spec
                #                    2 is mouse, per USB spec
                #                    0 is logitech's special sauce (?)
                if interface.bInterfaceProtocol == 0:
                    self.interface = interface
        if self.interface is None:
            sys.exit("Couldn't find special sauce interface.")

    def detach(self, n):
        #print "detaching.... ",
        try:
            self.device.detach_kernel_driver(interface=n)
            #print "Detached %s." % n
        except usb.core.USBError as e:
            print "couldn't detach, %s" % e

    def attach(self, n):
        #print "attaching....",
        try:
            self.device.attach_kernel_driver(interface=n)
            #print "Attached %s." % n
        except usb.core.USBError as e:
            print "couldn't attach, %s" % e

    def claim(self, i):
        usb.util.claim_interface(self.device, i)

    def release(self, i):
        usb.util.release_interface(self.device, i)

    def open(self, device_index=0, interface_indices=(0,0,), endpoint_index=0):
        self.configuration      = self.device[device_index]
        if self.configuration   is None: sys.exit("Bad configuration.")
        #self.interface          = self.configuration[interface_indices]
        #if self.interface       is None: sys.exit("Bad interface.")
        self.endpoint           = self.interface[endpoint_index]
        if self.endpoint        is None: sys.exit("Bad endpoint.")

if __name__ == '__main__':

    # find
    kb = USB( vendor_id=0x046d, product_id=0xc52b)
    #kb.open( device_index=0, interface_indices=(2,0,), endpoint_index=0 )
    kb.open( device_index=0,
            interface_indices=(kb.interface.bInterfaceNumber,0,),
            endpoint_index=0 )

    kb.detach(kb.interface.bInterfaceNumber)
    kb.claim(kb.interface.bInterfaceNumber)

    # fuzz (ymmv here -- I used wireshark, and there is a lot of
    # other noise traffic that I am not including because I don't
    # think it's required to make this work)
    #kb.device.ctrl_transfer(0x21, 0x09, 0x0210, 2,"\x10\xff\x81\x00\x00\x00\x00"),
    #kb.device.ctrl_transfer(0x21, 0x09, 0x0210, 2,"\x10\xff\x83\xb5\x31\x00\x00"),
    kb.device.ctrl_transfer(0x21, 0x09, 0x0210, kb.interface.bInterfaceNumber, "\x10\x02\x09\x03\x78\x01\x00"),
    #kb.device.ctrl_transfer(0x21, 0x09, 0x0210, 2,"\x10\x02\x02\x02\x00\x00\x00"),

    # profit
    data = list( kb.device.read(
                kb.endpoint.bEndpointAddress,
                kb.endpoint.wMaxPacketSize,
                kb.interface.bInterfaceNumber,
                6000))


    charge  = data[4]
    lux     = int(round(((255*data[5])+data[6])/538.0, 2)*100)
    print "%s,%s" % (charge, lux)
    # "Charge: %s Lux: %s (%s | %s)" % \
    # (data[4],
    # data[5],
    # data[6])

    kb.release(kb.interface.bInterfaceNumber)
    kb.attach(kb.interface.bInterfaceNumber)
    #time.sleep(1)

# Python™ ftw!
