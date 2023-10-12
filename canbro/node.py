import can
from cantools.database import Database
from broqer import Value, op, Sink
import logging
import types

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
                setattr(self, "_set_"+signal.name, types.MethodType(lambda self,value: self.__dict__["_signal_"+signal.name].notify(value),self) )
                self.__dict__["_signal_"+signal.name].notify(signal.initial)
                setattr(self, "_get_"+signal.name, types.MethodType(lambda self:  logging.debug("is a sender signal and can not be get!") ,self) )
                self.__dict__["_signal_"+signal.name].subscribe(Sink( logging.debug ))
            else:
                setattr(self, "_get_"+signal.name, types.MethodType(lambda self: self.__dict__["_signal_"+signal.name].get() ,self ) )
                self.__dict__["_signal_"+signal.name].subscribe(Sink(self._update_can_message))
                setattr(self, "_set_"+signal.name, types.MethodType(lambda self,value:  logging.debug("is a resiver signal and can not be set! value={}".format(value)),self ) ) 
            self.__dict__[ signal.name ] = property(fget=self.__dict__["_get_"+signal.name], fset=self.__dict__["_set_"+signal.name],  doc="The signal property." )
            
        if self._metadata.cycle_time:
            self._periodic_publisher = self | op.Throttle(self._metadata.cycle_time / 1000.0)


    def start_periodic(self):
        if self._periodic_publisher:
            self._periodic_publisher.subscribe(self.notify)
            self.running = True
        else:
            print("is not a periodic message")

    def stop_periodic(self):
        if self._periodic_publisher:
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
        logging.debug('Update CAN message callback: %s', self._metadata._name)
        return None
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
    logging.debug('Create signal values for %s', object)
    for message in database._messages:
        if node_name in message.senders:
            logging.debug('Create sender message %s', message._name)
            setattr(object, message._name, Message(message, True) )
        else:
            for signal in message._signals:
                is_in_node_as_reveiver = False
                if node_name in signal.receivers:
                    is_in_node_as_reveiver = True
            if is_in_node_as_reveiver:
                logging.debug('Create receiver message %s', message._name)
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