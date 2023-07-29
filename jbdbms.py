#!/usr/bin/python3

from bluepy.btle import Peripheral, DefaultDelegate, BTLEException
import struct
import argparse
import sys
import time
import binascii

parser = argparse.ArgumentParser(description='Pull data from JBDBMS (also known as eg. LLT BMS) via bluetooth')
parser.add_argument("-a", "--address", help="Device BLE Address", required=True)
parser.add_argument("-i", "--interval", type=int, help="Data fetch interval", required=True)
args = parser.parse_args()


def bmsinfo(data):
    offset = 4  # skip header
    volts, amps, remain, capacity, cycles, mdate, balance1, balance2, protect, version, percent, fet, cells, sensors, temp1, temp2, temp3, temp4 = struct.unpack_from('>HhHHHHHHHBBBBBHHHH', data, offset)

    print("Voltage (V) " + str(volts/100))
    print("Amps (A) " + str(amps/100))
    print("Capacity (Ah): " + str(capacity/100))
    print("Remaining Capacity (Ah): " + str(remain/100))
    print("Cycles: " + str(cycles))
    print("Manufacture Date: " + str(mdate))
    print("Temp 1: " + str((temp1-2731)/10) + " C")
    print("Temp 2: " + str((temp2-2731)/10) + " C")
    print("Temp 3: " + str((temp3-2731)/10) + " C")
    print("Temp 4: " + str((temp4-2731)/10) + " C")
    print("Protect trigger: " + str(protect))
    print("Version number: " + str(version))
    print("Percent: " + str(percent))
    print("Fet: " + str(fet)) 	# fet 0011 = 3 both on ; 0010 = 2 disch on ; 0001 = 1 chrg on ; 0000 = 0 both off
    print("Cells: " + str(cells))
    print("Sensors: " + str(sensors))

    prt = (format(protect, "b").zfill(16))		# protect trigger (0,1)(off,on)
    ovp = int(prt[0:1])			# overvoltage
    uvp = int(prt[1:2])			# undervoltage
    bov = int(prt[2:3])			# pack overvoltage
    buv = int(prt[3:4])			# pack undervoltage
    cot = int(prt[4:5])			# current over temp
    cut = int(prt[5:6])			# current under temp
    dot = int(prt[6:7])			# discharge over temp
    dut = int(prt[7:8])			# discharge under temp
    coc = int(prt[8:9])			# charge over current
    duc = int(prt[9:10])		# discharge under current
    sc = int(prt[10:11])		# short circuit
    ic = int(prt[11:12])        # ic failure
    cnf = int(prt[12:13])		# fet config problem


    #balance1 contains info for cell 1-16
    #balance2 contains info for cell 17-32

    #bal1 = (format(balance1, "b").zfill(16))
    #c16 = int(bal1[0:1])
    #c15 = int(bal1[1:2])							# using balance1 bits for 16 cells
    #c14 = int(bal1[2:3])							# balance2 is for next 17-32 cells - not using
    #c13 = int(bal1[3:4])
    #c12 = int(bal1[4:5])							# bit shows (0,1) charging on-off
    #c11 = int(bal1[5:6])
    #c10 = int(bal1[6:7])
    #c09 = int(bal1[7:8])
    #c08 = int(bal1[8:9])
    #c07 = int(bal1[9:10])
    #c06 = int(bal1[10:11])
    #c05 = int(bal1[11:12])
    #c04 = int(bal1[12:13])
    #c03 = int(bal1[13:14])
    #c02 = int(bal1[14:15])
    #c01 = int(bal1[15:16])

def cellvoltages(celldata):
    offset = 4 # skip header
    cell1, cell2, cell3, cell4, cell5, cell6, cell7, cell8, cell9, cell10 = struct.unpack_from('>HHHHHHHHHH', celldata, offset)
    cells = [cell1, cell2, cell3, cell4, cell5, cell6, cell7, cell8, cell9, cell10]
    i = 1
    for cell in cells:
        print("Cell " + str(i) + " " + str(cell/1000) + " V")
        i+=1

class MyDelegate(DefaultDelegate):
    buffer = b''
    def __init__(self):
        DefaultDelegate.__init__(self)
    def handleNotification(self, cHandle, data):
        #print("GOT NOTIFICATION")
        hex_data = binascii.hexlify(data)
        #print(str(hex_data))

        if hex_data.startswith(b'dd04') or hex_data.startswith(b'dd03'):
            self.buffer += hex_data
        elif hex_data.endswith(b'77'):	 # end of message
            self.buffer += hex_data
            #print("COMPLETE MESSAGE: " + str(self.buffer))
            if self.buffer.startswith(b'dd04'):
                cellvoltages(binascii.unhexlify(self.buffer))
                self.buffer = b''
            elif self.buffer.startswith(b'dd03'):
                bmsinfo(binascii.unhexlify(self.buffer))
                self.buffer = b''

try:
    print('attempting to connect')
    bms = Peripheral(args.address,addrType="public")
except BTLEException as ex:
    print('could not connect')
    exit()
else:
    print('connected to ',args.address)


bms.setDelegate(MyDelegate())

while True:
    # Request Cell Voltages
    result = bms.writeCharacteristic(0x15,b'\xdd\xa5\x04\x00\xff\xfc\x77',False)
    bms.waitForNotifications(5)

    # Request BMS information
    result = bms.writeCharacteristic(0x15,b'\xdd\xa5\x03\x00\xff\xfd\x77',False)
    bms.waitForNotifications(5)

    #TODO: swap order of the requests above so cell voltages can use no. of cell
    # info from the second message to allow variable amount of cells..
    time.sleep(args.interval)

