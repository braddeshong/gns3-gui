# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 GNS3 Technologies Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Base class for port objects.
"""

import os
import sys
import subprocess
import shlex

from ..qt import QtCore
from ..nios.nio_udp import NIOUDP
from ..settings import PACKET_CAPTURE_SETTINGS, PACKET_CAPTURE_SETTING_TYPES


class Port(object):
    """
    Base port.

    :param name: port name (string)
    :param default_nio: NIO object to use by default
    :param stub: indicates a stub port
    """

    _instance_count = 1
    _settings = {}

    # port statuses
    stopped = 0
    started = 1
    suspended = 2

    def __init__(self, name, default_nio=None, stub=False):

        # create an unique ID
        self._id = Port._instance_count
        Port._instance_count += 1

        self._name = name
        self._port_number = None
        self._slot_number = None
        self._stub = stub
        self._link_id = None
        self._port_label = None
        self._status = Port.stopped
        self._data = {}
        self._destination_node = None
        self._destination_port = None

        self._capture_supported = False
        self._capture_file_path = ""
        self._capturing = False
        self._tail_process = None
        self._capture_reader_process = None

        if default_nio is None:
            self._default_nio = NIOUDP
        else:
            self._default_nio = default_nio
        self._nio = None

    def id(self):
        """
        Returns an unique identifier for this port.

        :returns: port identifier (integer)
        """

        return self._id

    def setId(self, new_id):
        """
        Sets an identifier for this port.

        :param new_id: node identifier (integer)
        """

        self._id = new_id

        # update the instance count to avoid conflicts
        if new_id >= Port._instance_count:
            Port._instance_count = new_id + 1

    @classmethod
    def reset(cls):
        """
        Reset the instance count.
        """

        cls._instance_count = 1

    def name(self):
        """
        Returns the name of this port.

        :returns: current port name (string)
        """

        return self._name

    def setName(self, new_name):
        """
        Sets a new name for this port.

        :param new_name: new port name (string)
        """

        self._name = new_name

    def status(self):
        """
        Returns the status of this port.
        0 = stopped, 1 = started, 2 = suspended.

        :returns: port status (integer)
        """

        return self._status

    def setStatus(self, status):
        """
        Sets a status for this port.
        0 = stopped, 1 = started, 2 = suspended.

        :param status: port status (integer)
        """

        self._status = status

    def slotNumber(self):
        """
        Returns the slot number for this port.

        :returns: current slot number (integer)
        """

        return self._slot_number

    def setSlotNumber(self, slot_number):
        """
        Sets the slot number for this port.

        :param slot_number: new slot number (integer)
        """

        self._slot_number = slot_number

    def portNumber(self):
        """
        Returns the port number for this port.

        :returns: current port number (integer)
        """

        return self._port_number

    def setPortNumber(self, port_number):
        """
        Sets the port number for this port.

        :param port: new port number (integer)
        """

        self._port_number = port_number

    def destinationNode(self):
        """
        Returns the destination node

        :returns: destination Node instance
        """

        return self._destination_node

    def setDestinationNode(self, node):
        """
        Sets a new destination Node instance for this port.

        :param node: new destination Node instance
        """

        self._destination_node = node

    def destinationPort(self):
        """
        Returns the destination Port instance

        :returns: destination Port instance
        """

        return self._destination_port

    def setDestinationPort(self, port):
        """
        Sets a new destination Port instance for this port.

        :param port: new destination Port instance
        """

        self._destination_port = port

    def defaultNio(self):
        """
        Returns the default NIO for this port.

        :returns: NIO object
        """

        return self._default_nio

    def nio(self):
        """
        Returns the NIO attached to this port.

        :returns: NIO instance
        """

        return self._nio

    def setNio(self, nio):
        """
        Attach a NIO to this port.

        :param nio: NIO instance
        """

        self._nio = nio

    def linkId(self):
        """
        Returns the link id connected to this port.

        :returns: link id (integer)
        """

        return self._link_id

    def setLinkId(self, link_id):
        """
        Adds the link id connected to this port.

        :param link_id: link id (integer)
        """

        self._link_id = link_id

    def description(self):
        """
        Returns the text description of this port.

        :returns: description
        """

        if self._destination_node and self._destination_port:
            return "connected to {name} on port {port}".format(name=self._destination_node.name(),
                                                               port=self._destination_port.name())
        return ""

    def setFree(self):
        """
        Frees this port.
        """

        self._nio = None
        self._link_id = None
        self._destination_node = None
        self._destination_port = None
        self._port_label = None
        self.stopPacketCapture()

    def isFree(self):
        """
        Checks if this port is free to use (no NIO attached).

        :returns: boolean
        """

        if self._nio:
            return False
        return True

    def isStub(self):
        """
        Checks if this is a stub port.

        :returns: boolean
        """

        return self._stub

    @staticmethod
    def linkType():
        """
        Default link type to be used.

        :returns: string
        """

        return "Ethernet"

    @staticmethod
    def dataLinkTypes():
        """
        Returns the supported PCAP DLTs.

        :return: dictionary
        """

        return {"Ethernet": "DLT_EN10MB"}

    def data(self):
        """
        Returns the data associated with this port.

        :returns: current port data (dictionary)
        """

        return self._data

    def setData(self, new_data):
        """
        Sets data to be associated with this port.

        :param new_data: new port data (dictionary)
        """

        self._data = new_data

    def label(self):
        """
        Returns the port label.

        :return: NoteItem instance.
        """

        return self._port_label

    def setLabel(self, label):
        """
        Sets a port label.

        :param label: NoteItem instance.
        """

        self._port_label = label

    @classmethod
    def loadPacketCaptureSettings(cls):
        """
        Loads the packet capture settings from the persistent settings file.
        """

        settings = QtCore.QSettings()
        settings.beginGroup("PacketCapture")
        for name, value in PACKET_CAPTURE_SETTINGS.items():
            cls._settings[name] = settings.value(name, value, type=PACKET_CAPTURE_SETTING_TYPES[name])
        settings.endGroup()

    @classmethod
    def setPacketCaptureSettings(cls, new_settings):
        """
        Sets new packet capture settings.

        :param new_settings: settings dictionary
        """

        cls._settings.update(new_settings)
        settings = QtCore.QSettings()
        settings.beginGroup("PacketCapture")
        for name, value in cls._settings.items():
            settings.setValue(name, value)
        settings.endGroup()

    @classmethod
    def packetCaptureSettings(cls):
        """
        Returns the packet capture settings.

        :returns: settings dictionary
        """

        return cls._settings

    def setPacketCaptureSupported(self, value):
        """
        Sets either packet capture is support or not on this port

        :param value: boolean
        """

        self._capture_supported = value

    def packetCaptureSupported(self):
        """
        Returns either packet capture is support or not on this port

        :return: boolean
        """

        return self._capture_supported

    def capturing(self):
        """
        Returns either packet capture is active

        :return: boolean
        """

        return self._capturing

    def startPacketCapture(self, capture_file_path):
        """
        Starts a packet capture.

        :param capture_file_path: PCAP capture output file
        """

        self._capturing = True
        self._capture_file_path = capture_file_path
        if os.path.isfile(capture_file_path) and self._settings["command_auto_start"]:
            self.startPacketCaptureReader()

    def stopPacketCapture(self):
        """
        Stops a packet capture.
        """

        self._capturing = False
        self._capture_file_path = ""
        if self._tail_process and self._tail_process.poll() is None:
            self._tail_process.kill()
            self._tail_process = None
        self._capture_reader_process = None

    def startPacketCaptureReader(self):
        """
        Starts the packet capture reader.
        """

        if not os.path.isfile(self._capture_file_path):
            raise FileNotFoundError("the {} capture file does not exist on this host".format(self._capture_file_path))

        if self._tail_process and self._tail_process.poll() is None:
            self._tail_process.kill()
            self._tail_process = None
        if self._capture_reader_process and self._capture_reader_process.poll() is None:
            self._capture_reader_process.kill()
            self._capture_reader_process = None

        command = self._settings["packet_capture_reader_command"]
        command = command.replace("%c", '"' + self._capture_file_path + '"')

        if "|" in command:
            # live traffic capture (using tail)
            env = None
            command1, command2 = command.split("|", 1)
            info = None
            if sys.platform.startswith("win"):
                # hide tail window on Windows
                info = subprocess.STARTUPINFO()
                info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                info.wShowWindow = subprocess.SW_HIDE
                if hasattr(sys, "frozen"):
                    env = {"PATH": os.path.dirname(os.path.abspath(sys.executable))}  # for Popen to find tail.exe
                command1 = command1.strip()
                command2 = command2.strip()
            else:
                command1 = shlex.split(command1)
                command2 = shlex.split(command2)

            self._tail_process = subprocess.Popen(command1, startupinfo=info, stdout=subprocess.PIPE, env=env)
            self._capture_reader_process = subprocess.Popen(command2, stdin=self._tail_process.stdout, stdout=subprocess.PIPE)
            self._tail_process.stdout.close()
        else:
            # normal traffic capture
            if not sys.platform.startswith("win"):
                command = shlex.split(command)
            self._capture_reader_process = subprocess.Popen(command)

    def captureFileName(self, source_node_name):
        """
        Returns a capture file name.

        :param source_node_name: source node name

        :return: capture file name
        """

        capture_file_name = "{}_{}_to_{}_{}.pcap".format(source_node_name,
                                                         self.name().replace('/', '-'),
                                                         self.destinationNode().name(),
                                                         self.destinationPort().name().replace('/', '-'))
        return capture_file_name

    def dump(self):
        """
        Returns a representation of this port.

        :returns: dictionary
        """

        port = {"name": self._name,
                "id": self._id}

        if self._nio:
            port["nio"] = str(self._nio)
        if self._port_number is not None:
            port["port_number"] = self._port_number
        if self._slot_number is not None:
            port["slot_number"] = self._slot_number
        if self._stub:
            port["stub"] = self._stub
        if self.description():
            port["description"] = self.description()
        if self._link_id is not None:
            port["link_id"] = self._link_id

        return port

    def __str__(self):

        return self._name
