from can.interface import Bus
from cantools.database import load_file
from broqer import Sink
from canbro import Node

# load dbc file
db = load_file('poc/device_CAN.dbc')

# create ECU node with virtual bus test
bus_e= Bus('test', interface='virtual')
ecu = Node(name="ECU",bus=bus_e,database=db )

# create VCU node with virtual bus test, and connect to ECU via same name of bus -> test
bus_v= Bus('test', interface='virtual')
vcu= Node(name='CONTROL',bus=bus_v,database=db )

def show_vcu_value(value):
    print( 'value={}'.format(value) , end='')

show_print = ecu.DEM._signal_operation_mode.subscribe(Sink(show_vcu_value))

vcu.DEM.start_periodic()

vcu.DEM._signal_operation_mode.notify(2)

input("Wait for a key to stop the example...")