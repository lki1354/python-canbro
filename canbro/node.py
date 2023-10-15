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
    def __init__(self, metadata:Database, sender:bool, _can_bus:can.BusABC=None, transmitter=None ):
        super().__init__()
        self._metadata = metadata
        self.is_sender = sender
        self._can_bus = _can_bus
        self._periodic_task = None
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
            
            self.__dict__[ signal.name ] = property(fget=self.__dict__["_get_"+signal.name], fset=self.__dict__["_set_"+signal.name],  doc="The signal property." )

        if sender:
            if transmitter:
                self._transmitter = transmitter
            else:
                logging.ERROR("no transmitter function given for a sender message")    

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
    def _update_signals(self,signals:dict) -> None:
        logging.debug('Update signals: %s', self._metadata._name)
        for signal_name, signal_value in signals.items():
            self.__dict__["_signal_"+signal_name].notify(signal_value)

                
    def _send_msg(self,value) -> None:
        logging.debug('Send CAN message: %s', self._metadata._name)
        self._transmitter(self._can_message)


def _create_signal_values(object:object, database:Database, node_name:str=None) -> None:
    """Create Value instances for all signals in object"""
    logging.debug('Create signal values for %s', object)
    for message in database._messages:
        if node_name in message.senders:
            logging.debug('Create sender message %s', message._name)
            setattr(object, message._name, Message(message, True, object._bus ,object._send_message) )
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
        self._database = database
        listener = NodeListener(self)
        self._notifier = can.Notifier(self._bus, [listener])
        _create_signal_values(self, database, name)
        
    def _on_message(self, message:can.Message) -> None:
        """Callback for received CAN messages"""
        print(message)
    def _send_message(self, message:can.Message) -> None:
        """Callback for received CAN messages"""
        logging.debug('Send CAN message from Node %s: %s', self._name,message)
        self._bus.send(message)


class NodeListener(can.Listener):
    def __init__(self, node: Node) -> None:
        self._node = node

    def on_message_received(self, msg: can.Message):
        if msg.is_error_frame or msg.is_remote_frame: # or msg.is_fd: #todo what is 
            # rtr is currently not supported
            return

        try:
            database_message = self._node._database.get_message_by_frame_id(
                msg.arbitration_id)
        except KeyError:
            logging.ERROR('Received unknown message with arbitration id {}'.format( msg.arbitration_id ) )
            return
        try:
            data_decoded = database_message.decode(msg.data)
        except ValueError:
            logging.ERROR('Received unknown message with arbitration id {}'.format( msg.arbitration_id ) )
        self._node.__dict__[database_message._name]._update_signals(data_decoded)