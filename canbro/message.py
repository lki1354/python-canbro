import can
from cantools import database  
from cantools.autosar import compute_profile2_crc
from .e2e import E2E
from broqer import Value, op, Sink
import logging
import types
import asyncio
import datetime
import ast

from typing import (
    Any,
    Callable,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
    cast,
)


class Signal(Value):
    """
    A class representing a signal in a message.

    Attributes:
    - metadata: An object containing metadata about the signal.
    """
    def __init__(self, metadata):
        super().__init__()
        self._metadata = metadata
    def init_value(self):
        if self._metadata.initial != None:
            self._state = self._metadata.initial
            logging.debug("set initial value of signal {} to {} with type {}".format(self._metadata.name,self._state,type(self._state)))
        else:
            self._state = self._metadata.minimum + 1
            logging.error("signal {} has no initial value set to min +1".format(self._metadata.name,))



class Message(Value):
    """
    Represents a CAN message.

    Attributes:
        _metadata (database.Message): The metadata of the message.
        e2e (E2E): The end-to-end data object.
    """

    def __init__(self, metadata:database.Message):
        """
        Initializes a new instance of the Message class.

        Args:
            metadata (database.Message): The metadata of the message.
            data_ids (list, optional): The list of data IDs. Defaults to None.
        """
        super().__init__()
        self._metadata = metadata
        logging.debug("create message {}".format(metadata._name))
        self.e2e = None
        logging.info("E2E check is not implemented yet for received messages")

         

class MessageTx(Message):
    """
    A class representing a CAN message that can be transmitted on a CAN bus.

    Args:
        metadata (database.Message): The metadata associated with the message.
        can_bus (can.BusABC, optional): The CAN bus to transmit the message on. Defaults to None.

    Attributes:
        _can_bus (can.BusABC): The CAN bus to transmit the message on.
        _send_msg (bool): A flag indicating whether the message should be sent after it is updated.
    """

    def __init__(self, metadata:database.Message, can_bus:can.BusABC=None, update_msg:bool = True):
        super().__init__(metadata)
        self._can_bus = can_bus
        self._send_msg = update_msg
        for signal in metadata._signals:
            setattr(self, "_signal_"+signal.name, Signal(signal) )
            setattr(self, "_set_"+signal.name, types.MethodType(lambda self,value: self.__dict__["_signal_"+signal.name].notify(value),self) )
            #if signal.initial == None:
            #    logging.error("signal {} has no initial value".format(signal.name))
            #if signal.initial != None: #todo init value
            #    self.__dict__["_signal_"+signal.name]._state = signal.initial
            setattr(self, "_get_"+signal.name, types.MethodType(lambda self: self.__dict__["_signal_"+signal.name].get() ,self )  )
            if self._send_msg :
                self.__dict__["_signal_"+signal.name].subscribe(Sink( self._update_can_message))   
    
    def _get_signals(self) -> dict: 
        """
        Returns a dictionary containing the current values of all signals in the message.

        Returns:
            dict: A dictionary containing the current values of all signals in the message.
        """
        data = dict()
        for signal in self._metadata._signals:
            data[signal.name] = self.__dict__["_signal_"+signal.name].get()
        return data
    
    def send_after_update(self, value:bool) -> None:
        """
        Sets the flag indicating whether the message should be sent after it is updated.

        Args:
            value (bool, optional): The value to set the flag to. Defaults to True.
        """
        self._send_msg = value
    
    def send(self) -> None:
        """
        Sends the message on the associated CAN bus.
        """
        self._can_bus.send(self._state)
    
    def _update_message(self) -> None:
        """
        Updates the message with the current values of all signals.
        """
        logging.debug('Update CAN TX message: %s', self._metadata._name)
        arbitration_id = self._metadata.frame_id
        extended_id = self._metadata.is_extended_frame
        data = self._get_signals()
        logging.debug('Update CAN TX Data: {}'.format(data) )
        pruned_data = self._metadata.gather_signals(data)
        data = self._metadata.encode(pruned_data)
        _can_message = can.Message(arbitration_id=arbitration_id, is_extended_id=extended_id, data=data)
        self.notify(_can_message)

    def _update_can_message(self,value) -> None:
        """
        Updates the message and sends it on the associated CAN bus if the send flag is set.

        Args:
            value: The new value of a signal in the message.
        """
        self._update_message()
        if self._send_msg:
            self._can_bus.send(self._state)


class MessageTxCycle(MessageTx):
    """
    A class representing a periodic message that is sent cyclically on the CAN bus.

    Attributes:
    metadata (database.Message): The metadata of the message.
    can_bus (can.BusABC): The CAN bus to send the message on.
    _periodic_task: The periodic task that sends the message.
    _send_msg (bool): A flag indicating whether the message should be sent.
    """

    def __init__(self, metadata:database.Message, can_bus:can.BusABC=None, msg_callback: Optional[Callable[[can.Message], None]] = None ):
        super().__init__(metadata, can_bus, update_msg=False)
        self._periodic_task = None
        self._msg_callback = msg_callback
    
    def send_after_update(self, value):
        """
        Raises an error as a periodic message cannot be sent after an update.
        """
        logging.ERROR("is a periodic message and can not be send after update")
    
    def _update_calc_E2E(self,msg: can.Message) -> None:
        """
        update message data and calculates the end-to-end (E2E) protection for the message.
        """
        self._update_message()
        
        if self._msg_callback is not None:
            msg = self._state
            self._msg_callback(msg)
        else:
            self._periodic_task.modify_data(self._state)
        

    def _update_can_message(self,value) -> None:
        logging.ERROR("is a periodic message will be update before sending")
 #       """
 #       Updates the CAN message with the current signal values.
 #       """
 #       self._update_message()    
 #       if self._periodic_task is not None:
 #           self._periodic_task.modify_data(self._state)

    def start_periodic(self, msg_callback: Optional[Callable[[can.Message], None]] = None):
        """
        Starts sending the message periodically on the CAN bus.
        """
        if msg_callback is not None:
            self._msg_callback = msg_callback
        if self._metadata.cycle_time:
            for signal in self._metadata._signals:
                self.__dict__["_signal_"+signal.name].init_value()
            #self._periodic_publisher = self | op.Throttle(self._metadata.cycle_time / 1000.0)
            #self._update_can_message(None)
            self._update_message()
            self._periodic_task = self._can_bus.send_periodic( self._state, self._metadata.cycle_time / 1000.0, modifier_callback=self._update_calc_E2E)
            logging.debug("set periodic publisher for message {}".format(self._metadata._name))
            #self._periodic_publisher.subscribe(self._send_msg)
            #self._periodic_publisher.subscribe(self.notify)
            self.running = True
        else:
            print("is not a periodic message")

    def stop_periodic(self):
        """
        Stops sending the message periodically on the CAN bus.
        """
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
    """
    A class representing a received CAN message.

    Inherits from the Message class and adds functionality for decoding and updating signals.

    Attributes:
    - metadata (database.Message): The metadata for the message.
    - timestamp (float): The timestamp for the message.
    - _signal_* (Signal): The signals for the message.
    - _get_* (method): Methods for getting the value of each signal.
    - _set_* (method): Methods for setting the value of each signal (not available for receiver signals).
    - e2e (EndToEnd): The end-to-end configuration for the message (if applicable).

    Methods:
    - __init__(self, metadata:database.Message): Initializes the MessageRx object.
    - _update_data(self, msg: can.Message) -> None: Updates the signals for the message based on the received CAN message.
    """
    def __init__(self, metadata:database.Message):
        super().__init__(metadata)
        self.timestamp = 0
        for signal in metadata._signals:
            setattr(self, "_signal_"+signal.name, Signal(signal) )
            setattr(self, "_get_"+signal.name, types.MethodType(lambda self: self.__dict__["_signal_"+signal.name].get() ,self ) )
            self.__dict__["_signal_"+signal.name].subscribe(Sink( lambda value, name= signal.name: logging.debug("Signal "+name+" changed to value = {}".format(value) ) ))
            setattr(self, "_set_"+signal.name, types.MethodType(lambda self,value:  logging.error("is a resiver signal and can not be set! value={}".format(value)),self ) )
            sigType = 'GenSigFuncType'
            if sigType in signal.dbc.attributes:
                if signal.dbc.attributes[sigType].value == 2:
                    crc_signal = signal.name
                if signal.dbc.attributes[sigType].value == 1:
                    snc_signal = signal.name
        if "DataIds" in metadata.dbc.attributes:
            data_ids = metadata.dbc.attributes['DataIds'].value
            try:
                data_ids = ast.literal_eval(data_ids)
                self.add_data_ids(data_ids, crc_signal, snc_signal)
            except :
                logging.debug("MSG rx is not with E2E, can not convert data ids to list")

    
    def _update_data(self, msg: can.Message) -> None:
        """
        Updates the signals for the message based on the received CAN message.

        Args:
        - msg (can.Message): The received CAN message.
        """
        try:
            data_decoded = self._metadata.decode(msg.data)
        except ValueError:
            logging.error('Received unknown message with arbitration id {}'.format( msg.arbitration_id ) )
        logging.debug('Update RX signals: %s', self._metadata._name)
        if self.e2e is not None:
            seq_counter = data_decoded[self.e2e.snc_signal_name]
            data_id = self.e2e.data_ids[seq_counter]
            crc = compute_profile2_crc(msg.data, data_id )
            if crc != msg.data[0]:
                logging.error('CRC check failed for message %s', self._metadata._name)
                return
        self.timestamp = msg.timestamp
        for signal_name, signal_value in data_decoded.items():
            self.__dict__["_signal_"+signal_name].notify(signal_value)


def create_message(metadata:database.Message, sender:bool, _can_bus:can.BusABC=None ) -> Message:
    """Create a message (Value)"""

    if sender:
        #if metadata.cycle_time and metadata.signals[0].dbc.attributes['GenSigFuncType'].value == 2:
        if metadata.cycle_time:
            msg_obj= MessageTxCycle(metadata, _can_bus)
        else:
            msg_obj= MessageTx(metadata, _can_bus)
    else:
        msg_obj= MessageRx(metadata)
    return msg_obj


def create_message_class(name: str, is_tx: bool, signals: list[str], messages: list[str]) -> type[Message]:
    """
    Creates a dynamic class definition for messages RX and TX with messages and signals as setter and getter property.

    todo: this is not used yet and not tested

    Args:
    - name (str): The name of the class.
    - is_tx (bool): True if the class represents a TX message, False if it represents an RX message.
    - signals (List[str]): The list of signal names for the message.
    - messages (List[str]): The list of message names for the message.

    Returns:
    - Type[Message]: The dynamically generated class definition.
    """
    # Define the base class
    base_class = MessageTx if is_tx else MessageRx

    # Define the class dictionary
    class_dict = {
        # Constructor
        "__init__": lambda self, metadata: base_class.__init__(self, metadata),

        # Signals
        **{f"_{signal}": property(lambda self: self._get_signal(signal), lambda self, value: self._set_signal(signal, value)) for signal in signals},

        # Messages
        **{f"_{message}": property(lambda self: self._get_message(message), lambda self, value: self._set_message(message, value)) for message in messages}
    }

    # Create the class
    message_class = type(name, (base_class,), class_dict)

    return message_class
