import serial
import time
import json

class ThrottleController():
    def __init__(self, port_string: str, config_file: str):
        self.port = port_string
        self.config_file = config_file
        self.initialize()

    def initialize(self):
        with open(self.config_file) as fp:
            params = json.load(fp)
        self.full_position = params["full_position"]
        self.over_torque = params["over_torque"]
    
    def calculate_checksum1(self, mesg_list: list[int], seed: int = 0):
        """Calculate the checksum of an one byte integer array of values

        Args:
            msg (list[int]): list of bytes to send
            seed (int): One byte seed value. Defaults to 0
        """
        checksum = seed
        for i in mesg_list:
            checksum = (checksum + i) & 0xFF
        return checksum


    def calculate_checksum2(self, mesg_list: list[int], seed: int = 0):
        """Calculate the checksum2 of an one byte integer array of values

        Args:
            msg (list[int]): list of bytes to send
            seed (int): One byte seed value. Defaults to 0
        """
        checksum = seed
        for i in mesg_list:
            checksum = checksum ^ i
        return checksum


    def set_servo_number_efis_to_servo(self, serial_port: serial.Serial, servo_number: int):
        """Set the servo number using a serial port connected with usb to rs232 cable

        Args:
            serial_port (serial.Serial): Serial port to send message to
            servo_number (int): Servo number to set
        """

        start_mesgs = [0xD5, 0x82]
        set_message_length = [6]
        set_servo_mesgs = [0x00, 0x00, 0xAA, 0x55]
        set_servo_number = 1
        set_servo_mesgs.append(set_servo_number & 0xFF)  # Set servo to number
        set_servo_mesgs.append((set_servo_number ^ 0xFF) & 0xFF)  # Set servo message length
        # calculate xor of all bytes in set_servo_mesgs
        chks1 = [self.calculate_checksum1(set_servo_mesgs, seed=0xAA)]
        chks2 = [self.calculate_checksum2(set_servo_mesgs, seed=0x55)]
        whole_message = start_mesgs + set_message_length + set_servo_mesgs + chks1 + chks2
        print("Send Message: ")
        print([hex(i) for i in whole_message])
        serial_port.write(bytes(whole_message))


    def send_servo_position_message_from_efis_to_servo(
        self, serial_port: serial.Serial, position: int
    ):
        """send the servo position message from the EFIS to the servo

        Args:
            serial_port (serial.Serial): the serial port to send the message to
            position (int): the position to send to the servo. if -1 then just poll the position
        """
        start_mesgs = [0xD5, 0x82]
        set_message_length = [15]
        set_message_header = [0x01, 0x00]
        set_frespond = [0x01]
        if position == -1:
            set_options_1 = [0x00]
            tgt_position = 0x00.to_bytes(2, byteorder="little")
        else:
            set_options_1 = [
                0x01
            ]  # Here we will not reset torque measurement and not set torque
            tgt_position = (position).to_bytes(2, byteorder="little")
        
        tgt_position_send = [tgt_position[0], tgt_position[1]]

        fill_bytes = (0).to_bytes(9, byteorder="little")
        fill_bytes_send = [
            fill_bytes[0],
            fill_bytes[1],
            fill_bytes[2],
            fill_bytes[3],
            fill_bytes[4],
            fill_bytes[5],
            fill_bytes[6],
            fill_bytes[7],
            fill_bytes[8],
        ]
        set_servo_mesg = (
            set_message_header
            + set_frespond
            + set_options_1
            + tgt_position_send
            + fill_bytes_send
        )
        print([hex(i) for i in set_servo_mesg])
        chks1 = [self.calculate_checksum1(set_servo_mesg, seed=0xAA)]
        chks2 = [self.calculate_checksum2(set_servo_mesg, seed=0x55)]
        whole_message = start_mesgs + set_message_length + set_servo_mesg + chks1 + chks2
        print("Send Message: ")
        print([hex(i) for i in whole_message])
        serial_port.write(bytes(whole_message))
        
    def read_servo_ack_from_servo_to_efis(self, serial_port: serial.Serial):
        """Read the servo ack message from the servo to the EFIS

        Args:
            serial_port (serial.Serial): the serial port to read from
        """
        message_dict = {}
        ack = serial_port.read(8)
        ack_bytes = list(ack)
        message_dict["torque"] = ack_bytes[9]
        message_dict["voltage"] = ack_bytes[8]
        message_dict["Position"] = ack_bytes[7]*256 + ack_bytes[6]
        message_dict["enganged"] = ack_bytes[5] & 0x01
        message_dict["slipping"] = ack_bytes[5] & 0x02
        message_dict["voltage_alarm"] = ack_bytes[5] & 0x03
        message_dict["ack_length"] = len(ack_bytes)
        print("Ack: ")
        print([hex(i) for i in ack])
        
        return message_dict


    