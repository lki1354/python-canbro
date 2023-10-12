from canbro import Node
from can.interface import Bus
from cantools.database import load_file

ecu = Node(name="VCU",bus=Bus("virtul"),database=load_file('J1939.dbc') )


