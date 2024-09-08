import serial

from ovos_utils.log import LOG
# from ovos_config import Configuration

class MK1Serial():
    def __init__(self, config=None):
        config = config or {"port": "/dev/ttyAMA0",
                            "rate": 9600,
                            "timeout": 5.0})
        self.port = config.get("port")
        self.rate = config.get("rate")
        self.timeout = config.get("timeout")

        try:
            self.ser = serial.serial_for_url(url=self.port, baudrate=self.rate, timeout=self.timeout, do_not_open=True)
            LOG.info(f"Serial connection created with port: {self.port}, baudrate: {self.rate}, timeout: {self.timeout}")
        except Exception as e:
            LOG.exception(f"could not connect to serial: {self.port}")

    @property
    def is_open(self):
        if self.ser:
            return self.ser.is_open()
        return False

    def open_ser(self):
        if not self.is_open():
            try:
                self.ser.open()
            except Exception as e:
                LOG.error(f"could not open serial port {self.port}: {e}")
        else:
            LOG.debug(f"serial port {self.port} is already open")

    def close_ser(self):
        if self.is_open():
            try:
                self.ser.flush()
                self.ser.close()
            except Exception as e:
                LOG.error(f"could not close serial port {self.port}: {e}")
        else:
            LOG.debug(f"serial port {self.port} is already closed")

    def reset_ser(self):
        if self.is_open():
            try:
                self.close_ser()
                self.open_ser()
                LOG.debug(f"serial connection {self.port} has been reset")
            except Exception as e:
                LOG.error(f"could not reset serial port {self.port}: {e}")
