import can
from cantools.database import Database
from broqer import Value, op


class Signal(Value):
    def __init__(self, metadata,init=...):
        super().__init__(init)
        self._metadata = metadata


class Message(Value):
    def __init__(self, metadata:Database, sender:bool, init=...):
        super().__init__(init)
        self._metadata = metadata
        self.is_sender = sender
        for signal in metadata._signals:
            setattr(self, "_signal_"+signal.name, Signal(signal) )
            if sender:
                setattr(self, "set_"+signal.name, lambda self,value: self.__dict__["_signal_"+signal.name].notify(value) )
                setattr(self, "get_"+signal.name, lambda self:  print("is a sender signal and can not be get!") ) 
            else:
                setattr(self, "get_"+signal.name, lambda self: self.__dict__["_signal_"+signal.name].get() )
                setattr(self, "set_"+signal.name, lambda self,value:  print("is a resiver signal and can not be set!") ) 
            setattr(self, signal.name ,property(fget=self._get_signal, fset=self._set_signal) )
            self.__dict__["_signal_"+signal.name].notify(signal.initial)
            self.__dict__["_signal_"+signal.name].subscribe(self._update_can_message)
        if self._metadata.cycle_time:
            self._periodic_publisher = self | op.Throttle(self._metadata.cycle_time / 1000.0)


    def start_periodic(self):
        if self._metadata.cycle_time:
            self._periodic_publisher.subscribe(self.notify)
            self.running = True
        else:
            print("is not a periodic message")

    def stop_periodic(self):
        if self._metadata.cycle_time:
            self._periodic_publisher.unsubscribe(self.notify)
            self.running = False
        else:
            print("is not a periodic message")

    def _get_signals(self) -> dict: 
        data = dict()
        for signal in self._metadata._signals:
            data[signal] = self.__dict__["_signal_"+signal.name].get()

        return data

    def _update_can_message(self,value) -> None:
        arbitration_id = self._metadata.frame_id
        extended_id = self._metadata.is_extended_frame
        data = self._get_signals()
        pruned_data = self._metadata.gather_signals(data)
        data = self._metadata.encode(pruned_data,
                                    self._metadata.scaling,
                                    self._metadata.padding)
        self._can_message = can.Message(arbitration_id=arbitration_id,
                                        is_extended_id=extended_id,
                                        data=data)        
    def send_periodic_start(self):
        if not self.enabled:
            return
        
        self._periodic_task = self._can_bus.send_periodic(
            self._can_message,
            self._metadata.cycle_time / 1000.0)


def _create_signal_values(object:object, database:Database, node_name:str=None) -> None:
    """Create Value instances for all signals in object"""
    for message in database._messages:
        if node_name in message.senders:
            setattr(object, message._name, Message(message, True) )
        else:
            for signal in message._signals:
                is_in_node_as_reveiver = False
                if node_name in signal.receivers:
                    is_in_node_as_reveiver = True
            if is_in_node_as_reveiver:
                setattr(object, message._name, Message(message, False) )
                

class Node:
    """ControlUnit (CU)"""
    def __init__(self, name:str, bus:can.BusABC, database:Database) -> None:
        self._name = name
        self._bus = bus
        _create_signal_values(self, database, name)
        
    def _on_message(self, message:can.Message) -> None:
        """Callback for received CAN messages"""
        print(message)