from can_broqer import Node
from can.interface import Bus
from cantools import database

ecu = Node(name="VCU",bus=Bus("virtul"),database=database.load_file('J1939.dbc') )


