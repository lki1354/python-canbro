from cantools import tester, database
import can

class ControlUnit:
    """ControlUnit (CU)"""
    def __init__(self, controller_node:str, dut_node:str, database_path:str) -> None:
        self._can_bus = can.interface.Bus() 
        self._database = database.load_file(database_path)
        self._tester = tester.Tester(dut_node,self._database,self._can_bus, on_message=self._on_message)
    def _on_message(self, message:can.Message) -> None:
        """Callback for received CAN messages"""
        print(message)