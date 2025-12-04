import serial
import time

class ElliptecController:
    """Class to connect to and control Thorlabs Elliptec ELL14 rotation stages"""
    # Class variables for serial communication
    port = "COM5"
    baudrate = 9600
    pulses_per_turn = 143360 # We tested that this is the correct number of steps for a single
    # turn, but we have have NO IDEA why this is. The ELL manual specifies 262144 (2^18) pulses per turn,
    # but this is wrong and we don't know why.

    def __init__(self, port='COM5', baudrate=9600, address='0', verbose=False):
        # Connection details to establish serial connection
        self.address = address  # hex address (0‑F)
        self.verbose = verbose

        if not hasattr(self, "ser"):  # only initialize connection if it doesn't already exist 
            ElliptecController.port = port
            ElliptecController.baudrate = baudrate
            ElliptecController.ser = serial.Serial(port=ElliptecController.port,
                                    baudrate=ElliptecController.baudrate,
                                    bytesize=serial.EIGHTBITS,
                                    stopbits=serial.STOPBITS_ONE,
                                    parity=serial.PARITY_NONE,
                                    timeout=2)  # according to manual, timeout 2 s
            
        time.sleep(0.1)
        self._purge()  # Reset everything for clean start
        self.position = 0.0  # initialize position, always home to get correct initial value!

    def _purge(self):
        """Reset serial buffers for clean start of conneciton."""
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        time.sleep(0.05)

    def _send_cmd(self, cmd: str):
        """Send command (without CRLF), add CR (0x0D) and LF (0x0A) terminator according to manual"""
        full = f"{self.address}{cmd}"
        # send as ASCII bytes
        self.ser.write(full.encode('ascii'))
        self.ser.write(b'\r\n')
        # wait for response
        resp = self.ser.readline().decode('ascii', errors='ignore').strip()
        return resp
    
    def _deg_to_pulses(self, degrees: float):
        """Convert degrees to pulses (integer)."""
        return int(degrees * self.pulses_per_turn / 360)

    def _pulses_to_deg(self, pulses: int):
        """Convert pulses to degrees (float)."""
        # Handle signed 32-bit values
        if pulses >= 0x80000000:
            pulses -= 0x100000000
        return pulses * 360.0 / self.pulses_per_turn
    
    def _update_position(self, resp: str):
        """Update position whenever response is received from device. The class automatically calls
        this function after every move, so there is usually no need to update the position manually."""
        try:
            pos_hex = resp[-8:]
            self.position = round(self._pulses_to_deg(int(pos_hex, 16)), 2)
        except ValueError:
            print(f"⚠ Respuesta inválida del actuador: '{resp}' (pos_hex='{pos_hex}')")
            # No actualizamos la posición
        return

    def get_info(self):
        """Command IN: get module information"""
        resp = self._send_cmd("in")
        return resp

    def get_status(self):
        """Command GS: get status/error"""
        resp = self._send_cmd("gs")
        return resp

    def get_position_deg(self):
        """Output current position in degrees."""
        return self.position

    def home(self, direction=0):
        """Command HO: homing. direction=0 for CW / forward (rotary) or ignored if linear"""
        cmd = f"ho{direction}"
        resp = self._send_cmd(cmd)
        self._update_position(resp)
        if self.verbose:
            print(f"Homed device {self.address}. Position: {self.position:.2f}°")
        return resp   

    def move_absolute(self, pulses: int):
        """Command MA: move to absolute position in pulse counts"""
        # pulses must be encoded as 32-bit (4 bytes) big endian hexadecimal
        hexval = format(pulses & 0xFFFFFFFF, '08X')
        cmd = f"ma{hexval}"
        resp = self._send_cmd(cmd)
        self._update_position(resp)
        # if self.verbose:
            # print(f"Moved device {self.address} to position {self.position:.2f}°")
        return resp

    def move_relative(self, pulses: int):
        """Command MR: move relative by pulse counts"""
        hexval = format(pulses & 0xFFFFFFFF, '08X')
        cmd = f"mr{hexval}"
        resp = self._send_cmd(cmd)
        self._update_position(resp)
        # if self.verbose:
            # print(f"Moved device {self.address} to position {self.position:.2f}°")
        return resp
    
    def move_absolute_deg(self, degrees: float):
        """Command MA: move to absolute position in pulse counts"""
        # pulses must be encoded as 32-bit (4 bytes) big endian hexadecimal
        pulses = self._deg_to_pulses(degrees)
        hexval = format(pulses & 0xFFFFFFFF, '08X')
        cmd = f"ma{hexval}"
        resp = self._send_cmd(cmd)
        self._update_position(resp)
        # if self.verbose:
            # print(f"Moved device {self.address} to position {self.position:.2f}°")
        return resp

    def move_relative_deg(self, degrees: float):
        """Command MR: move relative by pulse counts"""
        pulses = self._deg_to_pulses(degrees)
        hexval = format(pulses & 0xFFFFFFFF, '08X')
        cmd = f"mr{hexval}"
        resp = self._send_cmd(cmd)
        self._update_position(resp)
        # if self.verbose:
            # print(f"Moved device {self.address} to position {self.position:.2f}°")
        return resp

    def stop(self):
        """Command ST: stop motion"""
        resp = self._send_cmd("st")
        self._update_position(resp)
        # if self.verbose:
            # print(f"Stopped device {self.address} at position {self.position:.2f}°")
        return resp

    def close(self):
        self.ser.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

if __name__ == "__main__":
    # Initialize both devices
    ell_0 = ElliptecController(port="COM5", address='0', verbose=True)
    ell_2 = ElliptecController(port="COM5", address='2', verbose=True)

    # ===== Information =====
    print("=== Device 0 Info ===", ell_0.get_info())
    print("=== Device 0 Status ===", ell_0.get_status())
    print("=== Device 2 Info ===", ell_2.get_info())
    print("=== Device 2 Status ===", ell_2.get_status())

    # ===== Homing =====
    ell_0.home(direction=0) # Homing device 0
    ell_2.home(direction=0) # Homing device 2
    time.sleep(5)

    # ===== Move Absolute (degrees) =====
    ell_0.move_absolute_deg(-9.99) # Rotate device 0 to an absolute position
    ell_2.move_absolute_deg(359.99) # Rotate device 2 to an absolute position
    time.sleep(3)

    # ===== Move Relative (degrees) =====
    ell_0.move_relative_deg(-360) # Rotate device 0 clockwise relatively to the last position
    ell_2.move_relative_deg(-360) # Rotate device 2 clockwise relatively to the last position
    time.sleep(3)
    ell_0.move_relative_deg(-361) # Rotate device 0 anticlockwise relatively to the last position
    ell_2.move_relative_deg(-361) # Rotate device 2 anticlockwise relatively to the last position


    # ===== Stop =====
    # print("Stop Device 0 …", ell_0.stop())
    # print("Stop Device 2 …", ell_2.stop())

    # Close COM port
    ell_0.close()
