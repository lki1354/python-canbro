import can
from cantools.database import Database
from broqer import Value


class Signal(Value):
    def __init__(self, metadata,init=...):
        super().__init__(init)
        self._metadata = metadata


class Message(Value):
    def __init__(self, metadata, sender, init=...):
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


def _create_signal_values(object:object, database:Database, node_name:str=None) -> None:
    """Create Value instances for all signals in object"""
    if node_name is None:
        node_name = object.__class__.__name__
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