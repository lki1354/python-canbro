import can
from cantools.database.can import Database
from broqer import Value


def _create_signal_values(object:)


class Node:
    """ControlUnit (CU)"""
    def __init__(self, name:str, bus:can.BusABC, database:Database) -> None:
        self._name = name
        self._bus = bus
        self._database = database
        for self
    def _on_message(self, message:can.Message) -> None:
        """Callback for received CAN messages"""
        print(message)