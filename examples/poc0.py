from can.interface import Bus
from cantools.database import load_file
from broqer import Sink
from canbro import Node
import os
from time import sleep
import logging
logging.basicConfig(level=logging.DEBUG)

# load dbc file
db = load_file('poc/device_CAN.dbc')

# create ECU node with virtual bus test
bus_e= Bus('test', interface='virtual')
ecu = Node(name="ECU",bus=bus_e,database=db )

# create VCU node with virtual bus test, and connect to ECU via same name of bus -> test
bus_v= Bus('test', interface='virtual')
vcu= Node(name='CONTROL',bus=bus_v,database=db )

def show_singal(sig):
    print( '{} = {} {}'.format(sig._metadata.name,sig._state,sig._metadata.unit))

vcu.DEM.start_periodic()


sleep(1)

i = 0

while(1):
    sleep(1.5)
    os.system('clear')
    show_singal(ecu.DEM._signal_operation_mode)
    print('press ctrl+c to exit')
    i=i+1
    vcu.DEM._signal_operation_mode.notify(i)
    sleep(1)
    i=i%6