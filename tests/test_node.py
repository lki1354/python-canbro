import unittest
import can
from canbro.node import Node

class TestNode(unittest.TestCase):
    def setUp(self):
        self.bus = can.interface.Bus(bustype='virtual')
        self.db = can.Database()
        self.db.add_message(can.Message(arbitration_id=0x100, data=[0, 1, 2, 3]))
        self.node = Node(name='test_node', bus=self.bus, database=self.db)

    def tearDown(self):
        self.bus.shutdown()

    def test_create_signal_values(self):
        self.assertEqual(len(self.node.__dict__), 1)
        self.assertTrue(hasattr(self.node, '0x100'))

    def test_on_message(self):
        msg = can.Message(arbitration_id=0x100, data=[4, 5, 6, 7])
        self.node._on_message(msg)
        # TODO: assert that the message was printed

    def test_send_message(self):
        msg = can.Message(arbitration_id=0x100, data=[4, 5, 6, 7])
        self.node._send_message(msg)
        # TODO: assert that the message was sent on the bus