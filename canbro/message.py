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


class Signal(Value):
    def __init__(self, metadata):
        super().__init__()
        self._metadata = metadata
    def init_value(self):
        if self._metadata.initial != None:
            self._state = self._metadata.initial
            logging.debug("set initial value of signal {} to {} with type {}".format(self._metadata.name,self._state,type(self._state)))
        else:
            logging.error("signal {} has no initial value".format(self._metadata.name,))



class Message(Value):
    def __init__(self, metadata:database.Message, data_ids:list=None):
        super().__init__()
        self._metadata = metadata
        if data_ids is not None:
            self.e2e = E2E()
            logging.info("set data ids, but just autosar profile 2 is supported!")
            self.e2e.data_ids = data_ids
        else:
            self.e2e = None
        logging.debug("create message {}".format(metadata._name))
    def add_data_ids(self, data_ids:list, crc_signal:str, snc_signal:str): #todo check if this function should moved to another class
        if self.e2e is None:
            self.e2e = E2E()
            logging.info("set data ids, but just autosar profile 2 is supported!")
        self.e2e.data_ids = data_ids
        self.e2e.crc_signal_name = crc_signal
        self.e2e.snc_signal_name = snc_signal
         

class MessageTx(Message):
    def __init__(self, metadata:database.Message, can_bus:can.BusABC=None):
        super().__init__(metadata)
        self._can_bus = can_bus
        self._send_msg = False
        for signal in metadata._signals:
            setattr(self, "_signal_"+signal.name, Signal(signal) )
            setattr(self, "_set_"+signal.name, types.MethodType(lambda self,value: self.__dict__["_signal_"+signal.name].notify(value),self) )
            #if signal.initial == None:
            #    logging.error("signal {} has no initial value".format(signal.name))
            #if signal.initial != None: #todo init value
            #    self.__dict__["_signal_"+signal.name]._state = signal.initial
            setattr(self, "_get_"+signal.name, types.MethodType(lambda self: self.__dict__["_signal_"+signal.name].get() ,self )  )
            self.__dict__["_signal_"+signal.name].subscribe(Sink( self._update_can_message))   
    
    def _get_signals(self) -> dict: 
        data = dict()
        for signal in self._metadata._signals:
            data[signal.name] = self.__dict__["_signal_"+signal.name].get()
        return data
    
    def send_after_update(self, value:bool = True) -> None:
        self._send_msg = value
    
    def send(self) -> None:
        self._can_bus.send(self._can_message)
    def _update_message(self) -> None:
        logging.debug('Update CAN message: %s', self._metadata._name)
        arbitration_id = self._metadata.frame_id
        extended_id = self._metadata.is_extended_frame
        data = self._get_signals()
        logging.debug('Update CAN Data: {}'.format(data) )
        pruned_data = self._metadata.gather_signals(data)
        data = self._metadata.encode(pruned_data)
        self._can_message = can.Message(arbitration_id=arbitration_id, is_extended_id=extended_id, data=data)
        self.notify(self._can_message)

    def _update_can_message(self,value) -> None:
        self._update_message()
        if self._send_msg:
            self._can_bus.send(self._can_message)


class MessageTxCycle(MessageTx):
    def __init__(self, metadata:database.Message, can_bus:can.BusABC=None):
        super().__init__(metadata, can_bus)
        self._periodic_task = None
        self._send_msg = False
    
    def send_after_update(self, value):
        logging.ERROR("is a periodic message and can not be send after update")
    
    def _update_can_message(self,value) -> None:
        self._update_message()    
        if self._periodic_task is not None:
            self._periodic_task.modify_data(self._can_message)

    def start_periodic(self):
        if self._metadata.cycle_time:
            for signal in self._metadata._signals:
                self.__dict__["_signal_"+signal.name].init_value()
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


class MessageTxCycleE2E(MessageTxCycle):
    running = False
    def __init__(self, metadata:database.Message, can_bus:can.BusABC):   #add_data_ids(self, data_ids:list, crc_signal:str, snc_signal:str)
        super().__init__(metadata, can_bus)
        
        for signal in metadata.signals:
            sigType = 'GenSigFuncType'
            if sigType in signal.dbc.attributes:
                if signal.dbc.attributes[sigType].value == 2:
                    crc_signal = signal.name
                if signal.dbc.attributes[sigType].value == 1:
                    snc_signal = signal.name
        data_ids = metadata.dbc.attributes['DataIds'].value
        try:
            data_ids = ast.literal_eval(data_ids)
        except :
            logging.error("can not convert data ids to list")
        self.add_data_ids(data_ids, crc_signal, snc_signal)

    def _update_e2e(self, msg: can.Message) -> None:
        seq_counter = self.__dict__["_signal_"+self.e2e.snc_signal_name].get()
        data_id = self.e2e.data_ids[seq_counter]
        crc = compute_profile2_crc(self._can_message.data, data_id )
        self.__dict__["_signal_"+self.e2e.crc_signal_name]._state = crc
        self._can_message.data[0] = crc
    
    def _update_can_message(self, value) -> None:
        self._update_message()    
        self._update_e2e(self._can_message)
        if self.running:
            logging.debug("update periodic e2e send message {}".format(self._metadata._name))
        else:
            logging.debug("periodic e2e send message {} is not started".format(self._metadata._name))

    async def __cycle(self, value):
        self.timestamp = datetime.datetime.now().timestamp()
        self.send()
        await asyncio.sleep(self._metadata.cycle_time / 1000.0)
        snc = self.__dict__["_signal_"+self.e2e.snc_signal_name].get()
        return snc
    def _increase_counter(self, snc:int):
        self.__dict__["_signal_"+self.e2e.snc_signal_name].notify( (snc + 1) % len(self.e2e.data_ids) )
        self.notify(self._can_message)
    def start_periodic(self):
        if self._metadata.cycle_time:
            for signal in self._metadata._signals:
                self.__dict__["_signal_"+signal.name].init_value()
            self._periodic_publisher = (self | op.MapAsync(self.__cycle, mode=op.AsyncMode.CONCURRENT))
            self._periodic_feedback = self._periodic_publisher.subscribe(Sink(self._increase_counter))
            logging.debug("set periodic publisher for message {}".format(self._metadata._name))
            self.running = True
            self._update_can_message(None)
        else:
            print("is not a periodic message")
    def stop_periodic(self):
        if self._periodic_feedback is not None:
            #self._periodic_publisher.dispose()
            self._periodic_feedback.dispose()
            self.running = False
        else:
            print("is not a periodic message")


class MessageRx(Message):
    def __init__(self, metadata:database.Message):
        super().__init__(metadata)
        self.timestamp = 0
        for signal in metadata._signals:
            setattr(self, "_signal_"+signal.name, Signal(signal) )
            setattr(self, "_get_"+signal.name, types.MethodType(lambda self: self.__dict__["_signal_"+signal.name].get() ,self ) )
            self.__dict__["_signal_"+signal.name].subscribe(Sink(logging.debug, "Signal {} changed to value = %".format(signal.name)))
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
        try:
            data_decoded = self._metadata.decode(msg.data)
        except ValueError:
            logging.ERROR('Received unknown message with arbitration id {}'.format( msg.arbitration_id ) )
        logging.debug('Update signals: %s', self._metadata._name)
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
        if metadata.cycle_time and 'DataIds' in metadata.dbc.attributes:
            msg_obj= MessageTxCycleE2E(metadata, _can_bus)
        elif metadata.cycle_time:
            msg_obj= MessageTxCycle(metadata, _can_bus)
        else:
            msg_obj= MessageTx(metadata, _can_bus)
    else:
        msg_obj= MessageRx(metadata)
    return msg_obj



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