# Copyright 2017 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import time
from queue import Queue
from threading import Thread

from ovos_bus_client import Message
from ovos_utils.log import LOG
from ovos_utils.signal import check_for_signal


class EnclosureReader(Thread):
    """
    Reads data from Serial port.

    Listens to all commands sent by Arduino that must be be performed on
    Mycroft Core.

    E.g. Mycroft Stop Feature
        # . Arduino sends a Stop command after a button press on a Mycroft unit
        # . ``EnclosureReader`` captures the Stop command
        # . Notify all Mycroft Core processes (e.g. skills) to be stopped

    Note: A command is identified by a line break
    """

    def __init__(self, serial, bus):
        super(EnclosureReader, self).__init__(target=self.read)
        self.alive = True
        self.daemon = True
        self.serial = serial
        self.bus = bus
        self.start()

        # Notifications from mycroft-core
        self.bus.on("mycroft.stop.handled", self.on_stop_handled)

    def read(self):
        while self.alive:
            try:
                data = self.serial.readline()[:-2]
                if data:
                    try:
                        data_str = data.decode()
                    except UnicodeError as e:
                        data_str = data.decode('utf-8', errors='replace')
                        LOG.warning('Invalid characters in response from '
                                    ' enclosure: {}'.format(repr(e)))
                    self.process(data_str)
            except Exception as e:
                LOG.error("Reading error: {0}".format(e))

    def on_stop_handled(self, event):
        # A skill performed a stop
        check_for_signal('buttonPress')

    def process(self, data):
        # TODO: Look into removing this emit altogether.
        # We need to check if any other serial bus messages
        # are handled by other parts of the code
        if "mycroft.stop" not in data:
            self.bus.emit(Message(data))

        if "Command: system.version" in data:
            # This happens in response to the "system.version" message
            # sent during the construction of Enclosure()
            self.bus.emit(Message("enclosure.started"))

        if "mycroft.stop" in data:
            self.bus.emit(Message("mycroft.stop"))

        if "volume.up" in data:
            self.bus.emit(Message("mycroft.volume.increase",
                                  {'play_sound': True}))

        if "volume.down" in data:
            self.bus.emit(Message("mycroft.volume.decrease",
                                  {'play_sound': True}))

        if "unit.shutdown" in data:
            # Eyes to soft gray on shutdown
            self.bus.emit(Message("enclosure.eyes.color",
                                  {'r': 70, 'g': 65, 'b': 69}))
            self.bus.emit(
                Message("enclosure.eyes.timedspin",
                        {'length': 12000}))
            self.bus.emit(Message("enclosure.mouth.reset"))
            time.sleep(0.5)  # give the system time to pass the message
            self.bus.emit(Message("system.shutdown"))

        if "unit.reboot" in data:
            # Eyes to soft gray on reboot
            self.bus.emit(Message("enclosure.eyes.color",
                                  {'r': 70, 'g': 65, 'b': 69}))
            self.bus.emit(Message("enclosure.eyes.spin"))
            self.bus.emit(Message("enclosure.mouth.reset"))
            time.sleep(0.5)  # give the system time to pass the message
            self.bus.emit(Message("system.reboot"))

        if "unit.setwifi" in data:
            self.bus.emit(Message("system.wifi.setup"))
        if "unit.factory-reset" in data:
            self.bus.emit(Message("system.factory.reset"))  # not in mycroft-core!
        if "unit.enable-ssh" in data:
            # This is handled by the wifi client
            self.bus.emit(Message("system.ssh.enable"))
        if "unit.disable-ssh" in data:
            # This is handled by the wifi client
            self.bus.emit(Message("system.ssh.disable"))

    def stop(self):
        self.alive = False


class EnclosureWriter(Thread):
    """
    Writes data to Serial port.
        # . Enqueues all commands received from Mycroft enclosures
           implementation
        # . Process them on the received order by writing on the Serial port

    E.g. Displaying a text on Mycroft's Mouth
        # . ``EnclosureMouth`` sends a text command
        # . ``EnclosureWriter`` captures and enqueue the command
        # . ``EnclosureWriter`` removes the next command from the queue
        # . ``EnclosureWriter`` writes the command to Serial port

    Note: A command has to end with a line break
    """

    def __init__(self, serial, bus, size=16):
        super(EnclosureWriter, self).__init__(target=self.flush)
        self.alive = True
        self.daemon = True
        self.serial = serial
        self.bus = bus
        self.commands = Queue(size)
        self.start()

    def flush(self):
        while self.alive:
            try:
                cmd = self.commands.get() + '\n'
                self.serial.write(cmd.encode())
                self.commands.task_done()
            except Exception as e:
                LOG.error("Writing error: {0}".format(e))

    def write(self, command):
        self.commands.put(str(command))

    def stop(self):
        self.alive = False
