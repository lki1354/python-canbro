from cantools.autosar import compute_profile2_crc
import can

class E2E():
    data_ids = None
    crc_signal_name = None
    snc_signal_name = None
    def __init__(self) -> None:
        pass


def update_e2e_autosar_profile2(msg: can.Message) -> None:
    """
    Updates the E2E protection of the message.

    Args:
    - msg (can.Message): The CAN message to be updated.
    """
    data_ids = [0x42, 0x52, 0x55, 0x53, 0x41, 0x20, 0x48, 0x59, 0x50, 0x4F, 0x57, 0x45, 0x52, 0x20, 0x41, 0x47]
    seq_counter = msg.data[1] & 0x0F
    seq_counter += 1
    seq_counter %= 16
    data_id = data_ids[seq_counter]
    crc = compute_profile2_crc(msg.data, data_id )
    msg.data[0] = crc
    msg.data[1] = (msg.data[1] & 0xF0) | seq_counter
    