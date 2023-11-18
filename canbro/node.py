import can
from cantools.database import Database
import logging
from .message import create_message
         

class Node:
    """ControlUnit (CU)"""
    def __init__(self, name:str, bus:can.BusABC, database:Database) -> None:
        self._name = name
        self._bus = bus
        self._database = database
        listener = NodeListener(self)
        self._notifier = can.Notifier(self._bus, [listener])
        self.__create_signal_values(database, name)

    def __create_signal_values(self, database:Database, node_name:str=None) -> None:
        """Create Value instances for all signals in object"""
        logging.debug('Create signal values for %s', self)
        for message in database.messages:
            logging.debug(message.senders)
            if node_name in message.senders:
                logging.debug('Create sender message %s', message._name)
                setattr(self, message._name, create_message(message, True, self._bus ) )
            else:
                for signal in message._signals:
                    is_in_node_as_reveiver = False
                    if node_name in signal.receivers:
                        is_in_node_as_reveiver = True
                if is_in_node_as_reveiver:
                    logging.debug('Create receiver message %s', message._name)
                    setattr(self, message._name, create_message(message, False) )
        
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
            logging.info('Received unknown message with arbitration id {}'.format( msg.arbitration_id ) )
            return
        try:
            self._node.__dict__[database_message._name]._update_data(msg)
        except:
            logging.info('Received message with arbitration id {} and is not a instance of this node. '.format( msg.arbitration_id ) )
