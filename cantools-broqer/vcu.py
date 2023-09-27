from control_unit import ControlUnit

class VehicleControlUnit(ControlUnit):
    def __init__(self, name, vehicle_type):
        super().__init__(name)
        self.vehicle_type = vehicle_type
        # additional initialization code here