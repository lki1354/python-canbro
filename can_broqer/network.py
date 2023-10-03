import can
from cantools import database
from configparser import ConfigParser
import logging
from .node import Node

log = logging.getLogger(__name__)



class Network:
    def __init__(self,bus_path:str=None, bus:can.BusABC = None, database_path:str = None) -> None:
        self._bus = can.interface.Bus()
        listener = NodeListener(self)
        config = ConfigParser().read('can.ini')
        self._loop = None
        self._notifier = can.Notifier(self._bus, (listener,), 1, self._loop)
        self._database = database.load_file(database_path or config.get('database','path'))
        for node_name in self._database.nodes:
            self._create_node(node_name.name)

    def _create_node(self, name:str) -> None:
        """Create a node"""
        self.__dict__.update({name: Node(name, self._bus, self._database)})
        return self.__dict__[name]
    
    @property
    def nodes(self) -> list[Node]:
        """Get all nodes"""
        nodes=[]
        for node in self._database.nodes:
            nodes.append(self.__dict__[node.name])
        return nodes



class NodeListener(can.Listener):
    def __init__(self, network: BusNetwork):
        self._network = network

    def on_message_received(self, msg: can.Message):
        if msg.is_error_frame or msg.is_remote_frame or msg.is_fd:
            # rtr is currently not supported
            return

        with self._network.lock:
            callback = self._network.subscriptions.get(msg.arbitration_id, None)

        if not callback:
            return

        try:
            callback(msg.arbitration_id, msg.data)
        except Exception as e:
            log.exception(f"{e!r} while processing {msg!r}")


class Listener(can.Listener):

    def __init__(self, database, messages, input_queue, on_message):
        self._database = database
        self._messages = messages
        self._input_queue = input_queue
        self._on_message = on_message

    def on_message_received(self, msg):
        if msg.is_error_frame or msg.is_remote_frame:
            return

        try:
            database_message = self._database.get_message_by_frame_id(
                msg.arbitration_id)
        except KeyError:
            return

        if database_message.name not in self._messages:
            return

        message = self._messages[database_message.name]

        if not message.enabled:
            return

        decoded =    database_message.decode(msg.data,
                                                         message.decode_choices,
                                                         message.scaling)

        if self._on_message:
            self._on_message(decoded)

        self._input_queue.put(decoded)
