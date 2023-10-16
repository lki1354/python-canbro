import can
from cantools.database import Database
from broqer import Value, op, Sink
import logging
import types
import asyncio



class Signal(Value):
    def __init__(self, metadata):
        super().__init__()
        self._metadata = metadata


class Message(Value):
    def __init__(self, metadata:Database):
        super().__init__()
        self._metadata = metadata
         



class MessageTx(Message):
    def __init__(self, metadata:Database, can_bus:can.BusABC=None):
        super().__init__(metadata)
        self._can_bus = can_bus
        self._periodic_task = None
        for signal in metadata._signals:
            setattr(self, "_signal_"+signal.name, Signal(signal) )
            setattr(self, "_set_"+signal.name, types.MethodType(lambda self,value: self.__dict__["_signal_"+signal.name].notify(value),self) )
            if signal.initial == None:
                logging.error("signal {} has no initial value".format(signal.name))
            signal.initial = 10
            if signal.initial != None:
                self.__dict__["_signal_"+signal.name].notify(signal.initial)
            logging.debug("set initial value of signal {} to {} with type {}".format(signal.name,signal.initial,type(signal.initial)))
            setattr(self, "_get_"+signal.name, types.MethodType(lambda self: self.__dict__["_signal_"+signal.name].get() ,self )  )
            self.__dict__["_signal_"+signal.name].subscribe(Sink( self._update_can_message))   
    
    def _get_signals(self) -> dict: 
        data = dict()
        for signal in self._metadata._signals:
            data[signal.name] = self.__dict__["_signal_"+signal.name].get()
        return data

    def _update_can_message(self,value) -> None:
        logging.debug('Update CAN message: %s', self._metadata._name)
        #return None
        arbitration_id = self._metadata.frame_id
        extended_id = self._metadata.is_extended_frame
        data = self._get_signals()
        logging.debug('Update CAN Data: {}'.format(data) )
        pruned_data = self._metadata.gather_signals(data)
        data = self._metadata.encode(pruned_data)
        self._can_message = can.Message(arbitration_id=arbitration_id,
                                        is_extended_id=extended_id,
                                        data=data)
        self.notify(self._can_message)
        if self._periodic_task is not None:
            self._periodic_task.modify_data(self._can_message)
        else:
            self._can_bus.send(self._can_message)

    def _update_can_message(self,value) -> None:
        logging.debug('Update CAN message: %s', self._metadata._name)
        #return None
        arbitration_id = self._metadata.frame_id
        extended_id = self._metadata.is_extended_frame
        data = self._get_signals()
        logging.debug('Update CAN Data: {}'.format(data) )
        pruned_data = self._metadata.gather_signals(data)
        data = self._metadata.encode(pruned_data)
        self._can_message = can.Message(arbitration_id=arbitration_id,
                                        is_extended_id=extended_id,
                                        data=data)
        self.notify(self._can_message)
        if self._periodic_task is not None:
            self._periodic_task.modify_data(self._can_message)
        else:
            self._can_bus.send(self._can_message)
    
    def start_periodic(self):
        if self._metadata.cycle_time:
            #self._periodic_publisher = self | op.Throttle(self._metadata.cycle_time / 1000.0)
            self._update_can_message(None)
            self._periodic_task = self._can_bus.send_periodic( self._can_message, self._metadata.cycle_time / 1000.0)
            logging.debug("set periodic publisher for message {}".format(self._metadata._name))
            #self._periodic_publisher.subscribe(self._send_msg)
            #self._periodic_publisher.subscribe(self.notify)
            self.running = True
        else:
            print("is not a periodic message")

    def stop_periodic(self):
        if self._periodic_task is not None:
            self._periodic_task.stop()
            self._periodic_task = None
        #if self._metadata.cycle_time:
            #self._periodic_publisher.unsubscribe(self._send_msg)
            #self._periodic_publisher.unsubscribe(self.notify)
            self.running = False
        else:
            print("is not a periodic message")


class MessageRx(Message):
    def __init__(self, metadata:Database):
        super().__init__(metadata)
        for signal in metadata._signals:
            setattr(self, "_signal_"+signal.name, Signal(signal) )
            setattr(self, "_get_"+signal.name, types.MethodType(lambda self: self.__dict__["_signal_"+signal.name].get() ,self ) )
            self.__dict__["_signal_"+signal.name].subscribe(Sink(logging.debug, "Signal {} changed to value = %".format(signal.name)))
            setattr(self, "_set_"+signal.name, types.MethodType(lambda self,value:  logging.error("is a resiver signal and can not be set! value={}".format(value)),self ) ) 
    def _update_signals(self,signals:dict) -> None:
        logging.debug('Update signals: %s', self._metadata._name)
        for signal_name, signal_value in signals.items():
            self.__dict__["_signal_"+signal_name].notify(signal_value)


test = """ def create_device(name:str, sender:bool ,bus:can.BusABC, database:Database) -> Node:
    "Create a device (Node)"
# creating class dynamically 


    if sender:
        pass
    else:
        Device = type(name, (MessageRx, ), { 
            # constructor 
            "__init__": super().__init__(), 
            
            # data members 
            "string_attribute": "Geeks 4 geeks !", 
            "int_attribute": 1706256, 
            
            # member functions 
            "func_arg": displayMethod, 
        }) 


    return Device(name, bus, database)

self.__dict__[ signal.name ] = property(fget=self.__dict__["_get_"+signal.name], fset=self.__dict__["_set_"+signal.name],  doc="The signal property." )



        for signal in metadata._signals:
            setattr(self, "_signal_"+signal.name, Signal(signal) )
            if sender:
                setattr(self, "_set_"+signal.name, types.MethodType(lambda self,value: self.__dict__["_signal_"+signal.name].notify(value),self) )
                signal.initial = 10
                if signal.initial != None:
                    self.__dict__["_signal_"+signal.name].notify(signal.initial)
                logging.debug("set initial value of signal {} to {} with type {}".format(signal.name,signal.initial,type(signal.initial)))
                setattr(self, "_get_"+signal.name, types.MethodType(lambda self: self.__dict__["_signal_"+signal.name].get() ,self )  )
                self.__dict__["_signal_"+signal.name].subscribe(Sink( self._update_can_message))
            else:
                setattr(self, "_get_"+signal.name, types.MethodType(lambda self: self.__dict__["_signal_"+signal.name].get() ,self ) )
                self.__dict__["_signal_"+signal.name].subscribe(Sink(logging.debug))
                setattr(self, "_set_"+signal.name, types.MethodType(lambda self,value:  logging.debug("is a resiver signal and can not be set! value={}".format(value)),self ) ) 
"""

def create_message(metadata:Database, sender:bool, _can_bus:can.BusABC=None ) -> Message:
    """Create a message (Value)"""

    if sender:
        msg_obj= MessageTx(metadata, _can_bus)
    else:
        msg_obj= MessageRx(metadata)
    return msg_obj


