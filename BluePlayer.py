#!/usr/bin/env python3

#python3-dbus
#python3-gi

import time
# import signal
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GObject

SERVICE_NAME = "org.bluez"
AGENT_IFACE = SERVICE_NAME + '.Agent1'
ADAPTER_IFACE = SERVICE_NAME + ".Adapter1"
DEVICE_IFACE = SERVICE_NAME + ".Device1"
PLAYER_IFACE = SERVICE_NAME + '.MediaPlayer1'
TRANSPORT_IFACE = SERVICE_NAME + '.MediaTransport1'

# Utility functions from bluezutils.py
def getManagedObjects():
    bus = dbus.SystemBus()
    manager = dbus.Interface(bus.get_object(SERVICE_NAME, "/"), "org.freedesktop.DBus.ObjectManager")
    return manager.GetManagedObjects()

def findAdapter():
    objects = getManagedObjects();
    bus = dbus.SystemBus()
    for path, ifaces in objects.items():
        adapter = ifaces.get(ADAPTER_IFACE)
        if adapter is None:
            continue
        obj = bus.get_object(SERVICE_NAME, path)
        return dbus.Interface(obj, ADAPTER_IFACE)
    raise Exception("Bluetooth adapter not found")

class BluePlayer(dbus.service.Object):
    AGENT_PATH = "/blueplayer/agent"
    CAPABILITY = "DisplayOnly"

    bus = None
    adapter = None
    device = None
    deviceAlias = None
    player = None
    transport = None
    connected = None
    state = None
    status = None
    discoverable = None
    track = None
    position = None
    utcLastPosChange = None
    adapter = None

    # Callbacks
    newDeviceCallback = None
    playPauseCallback = None
    songChangeCallback = None
    positionChangeCallback = None

    # Notifiers
    def notifyNewDevice(self, devName):
        if self.newDeviceCallback != None:
            self.newDeviceCallback(devName)

    def notifyPlayPause(self, status):
        if self.playPauseCallback != None:
            self.playPauseCallback(status)

    def notifySongChange(self, newSong):
        if self.songChangeCallback != None:
            self.songChangeCallback(newSong)

    def notifyPositionChange(self, newPos):
        if self.positionChangeCallback != None:
            self.positionChangeCallback(newPos)

    # Private functions
    def __init__(self):
        # init bus and add signals receivers then check if there is a connected device
        self.bus = dbus.SystemBus()

        dbus.service.Object.__init__(self, dbus.SystemBus(), BluePlayer.AGENT_PATH)

        self.bus.add_signal_receiver(self.playerHandler,
                bus_name=SERVICE_NAME,
                dbus_interface="org.freedesktop.DBus.Properties",
                signal_name="PropertiesChanged",
                path_keyword="path")

        self.registerAgent()

        self.adapter = findAdapter()

    def findPlayer(self):
        # Find all the current media players
        manager = dbus.Interface(self.bus.get_object(SERVICE_NAME, "/"), "org.freedesktop.DBus.ObjectManager")
        objects = manager.GetManagedObjects()

        player_path = None
        transport_path = None
        for path, interfaces in objects.items():
            if PLAYER_IFACE in interfaces:
                player_path = path
            if TRANSPORT_IFACE in interfaces:
                transport_path = path

        if player_path:
            self.connected = True
            self.getPlayer(player_path)
            player_properties = self.player.GetAll(PLAYER_IFACE, dbus_interface="org.freedesktop.DBus.Properties")
            self.notifyNewDevice(self.getDeviceInfo())
            if "Status" in player_properties:
                self.status = player_properties["Status"]
                self.notifyPlayPause(self.status)
            if "Track" in player_properties:
                self.track = player_properties["Track"]
                self.notifySongChange(self.track)
            if "Position" in player_properties:
                self.position = player_properties["Position"]
                self.utcLastPosChange = int(round(time.time() * 1000)) # save the utc of when the last position was registered
                self.notifyPositionChange(self.position)
            self.setDiscoverable(False)
        else:
            print("No device connected")

        if transport_path:
            self.transport = self.bus.get_object(SERVICE_NAME, transport_path)
            transport_properties = self.transport.GetAll(TRANSPORT_IFACE, dbus_interface="org.freedesktop.DBus.Properties")
            if "State" in transport_properties:
                self.state = transport_properties["State"]

    def getPlayer(self, path):
        # get a media player from dbus and the relative device
        self.player = self.bus.get_object(SERVICE_NAME, path)
        device_path = self.player.Get("org.bluez.MediaPlayer1", "Device", dbus_interface="org.freedesktop.DBus.Properties")
        self.getDevice(device_path)

    def getDevice(self, path):
        self.device = self.bus.get_object(SERVICE_NAME, path)
        self.deviceAlias = self.device.Get(DEVICE_IFACE, "Alias", dbus_interface="org.freedesktop.DBus.Properties")
        self.deviceAddress = self.device.Get(DEVICE_IFACE, "Address", dbus_interface="org.freedesktop.DBus.Properties")
        print("Current device => " + self.deviceAlias)

    def disconnectDevice(self, path):
        busDevice = self.bus.get_object(SERVICE_NAME, path);
        device = dbus.Interface(busDevice, DEVICE_IFACE)

        props = dbus.Interface(
            self.bus.get_object(SERVICE_NAME, device.object_path),
            "org.freedesktop.DBus.Properties")

        if props.Get("org.bluez.Device1", "Connected"):
            device.Disconnect()

    def playerHandler(self, interface, changed, invalidated, path):
        # handler for signals
        iface = interface[interface.rfind(".") + 1:]

        if iface == "Device1":
            if "Connected" in changed: # connection state changed, self.connected is 1 if connected, 0 if not
                if self.connected and changed["Connected"]:
                    print("Another device already connected, removing the new one")
                    self.disconnectDevice(path)
        if iface == "MediaControl1":
            if "Connected" in changed: # connection state changed for media control, self.connected is 1 if connected, 0 if not
                if self.connected:
                    if changed["Connected"]:
                        print("Another device already connected, removing the new one")
                    else:
                        print("Lost connection with => " + self.deviceAlias)
                        self.connected = False
                        self.setDiscoverable(True)
                else:
                    if changed["Connected"]:
                        self.findPlayer()
        elif iface == "MediaTransport1":
            if "State" in changed: # pending, active or idle, don't think this is useful
                self.state = (changed["State"])
            # if "Connected" in changed: # connection state changed, self.connect is 1 if connected, 0 if not
            #     #connection status changed
        elif iface == "MediaPlayer1":
            if "Track" in changed: # track changed so this will be executed on start and on every song change
                self.track = changed["Track"] # track contains Artist, Title, Album, TrackNumber, NumberOfTracks, Duration
                #self.position = 0
                #self.utcLastPosChange = int(round(time.time() * 1000)) # save the utc of when the last position was registered
                self.notifySongChange(self.track)
                #self.notifyPositionChange(self.position)
            if "Status" in changed: # status is paused or playing
                self.status = (changed["Status"])
                self.notifyPlayPause(self.status)
            if "Position" in changed:
                self.position = changed["Position"]
                self.utcLastPosChange = int(round(time.time() * 1000)) # save the utc of when the last position was registered
                self.notifyPositionChange(self.position)

    @dbus.service.method(AGENT_IFACE, in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey):
        self.trustDevice(device)
        return

    @dbus.service.method(AGENT_IFACE, in_signature="os", out_signature="")
    def AuthorizeService(self, device, uuid):
        return

    @dbus.service.method(AGENT_IFACE, in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        return "0000"

    @dbus.service.method(AGENT_IFACE, in_signature="os", out_signature="")
    def Authorize(self, device, uuid):
        return

    @dbus.service.method("org.bluez.Agent", in_signature="ou", out_signature="")
    def DisplayPasskey(self, device, passkey):
        print("Passkey ({}, {:06d})".format(device, passkey))

    @dbus.service.method("org.bluez.Agent", in_signature="os", out_signature="")
    def DisplayPinCode(self, device, pincode):
        print("PinCode ({}, {})".format(device, pincode))

    def trustDevice(self, path):
        device_properties = dbus.Interface(self.bus.get_object(SERVICE_NAME, path), "org.freedesktop.DBus.Properties")
        device_properties.Set(DEVICE_IFACE, "Trusted", True)

    def registerAgent(self):
        manager = dbus.Interface(self.bus.get_object(SERVICE_NAME, "/org/bluez"), "org.bluez.AgentManager1")
        manager.RegisterAgent(BluePlayer.AGENT_PATH, BluePlayer.CAPABILITY)
        manager.RequestDefaultAgent(BluePlayer.AGENT_PATH)

    # Private functions

    # Public functions
    def setCallbacks(self, newDevHandler, PPHandler, songChHandler, posChHandler):
        self.newDeviceCallback = newDevHandler
        self.playPauseCallback = PPHandler
        self.songChangeCallback = songChHandler
        self.positionChangeCallback = posChHandler

    def start(self):
        self.findPlayer()

        if not self.connected:
            self.setDiscoverable(True)

        print("BluePlayer started!")

    def getTrackInfo(self):
        if self.track != None:
            return self.track # track contains Artist, Title, Album, TrackNumber, NumberOfTracks, Duration
        else:
            return None

    def getDeviceInfo(self):
        if self.connected:
            return {
                "Alias": self.deviceAlias,
                "Address": self.deviceAddress
            }
        else:
            return None

    def getStatus(self):
        return self.status

    def getCurSongPosition(self):
        if not self.connected:
            return 0

        if self.status == "paused":
            return self.position
        else:
            return self.position + (int(round(time.time() * 1000)) - self.utcLastPosChange)

    def next(self):
        self.player.Next(dbus_interface=PLAYER_IFACE)

    def previous(self):
        self.player.Previous(dbus_interface=PLAYER_IFACE)

    def play(self):
        self.player.Play(dbus_interface=PLAYER_IFACE)

    def pause(self):
        self.player.Pause(dbus_interface=PLAYER_IFACE)

    # def volumeUp(self):
        # self.player.VolumeUp(dbus_interface=PLAYER_IFACE)
        # self.control.VolumeUp(dbus_interface=CONTROL_IFACE)
        # self.transport.VolumeUp(dbus_interface=TRANSPORT_IFACE)

    # def volumeDown(self):
        # self.player.VolumeDown(dbus_interface=PLAYER_IFACE)
        # self.control.VolumeDown(dbus_interface=CONTROL_IFACE)
        # self.transport.VolumeDown(dbus_interface=TRANSPORT_IFACE)

    def setDiscoverable(self, status):
        adapter_path = findAdapter().object_path
        adapter = dbus.Interface(self.bus.get_object(SERVICE_NAME, adapter_path), "org.freedesktop.DBus.Properties")
        adapter.Set(ADAPTER_IFACE, "Discoverable", status)
        if status:
            print("Bluetooth is now discoverable")
            print("Use pin 0000 if asked")

    def startNewPairingProcess(self):
        if self.connected:
            self.disconnectDevice(self.device.object_path)

    def tryToReconnectToLastDevice(self): # works but probably needs a revision cause from tests after this reconnects the device the music doesn't play
        if not self.device == None:
            print("Trying to reconnect to last device")

            try:
                busDevice = self.bus.get_object(SERVICE_NAME, self.device.object_path);
                tmpDevice = dbus.Interface(busDevice, DEVICE_IFACE)
            except dbus.exceptions.DBusException as error:
                return False

            try:
                props = dbus.Interface(
                    self.bus.get_object(SERVICE_NAME, tmpDevice.object_path),
                    "org.freedesktop.DBus.Properties")

                if not props.Get("org.bluez.Device1", "Connected"):
                    tmpDevice.Connect()
            except dbus.exceptions.DBusException as error:
                return False

    def shutdown(self):
        if self.connected:
            self.disconnectDevice(self.device.object_path)
        self.setDiscoverable(False)


# EXAMPLE OF USAGE:

"""

GObject.threads_init()
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

player = None

def newDeviceHandler(dev):
    print(dev["Alias"] + "(" + dev["Address"] + ") is now connected!")
    player.play()

def playPauseHandler(newStatus): # will be paused or playing
    print(" => " + newStatus + " <= ")

def songChangeHandler(newSong):
    print("Artist:          " + newSong["Artist"])
    print("Title:           " + newSong["Title"])
    print("Album:           " + newSong["Album"])
    print("TrackNumber:     " + str(newSong["TrackNumber"]))
    print("NumberOfTracks:  " + str(newSong["NumberOfTracks"]))
    print("Duration:        " + str(newSong["Duration"]))

def songPosChangeHandler(newPos):
    trackInfo = player.getTrackInfo()
    if trackInfo != None and "Duration" in trackInfo:
        duration = trackInfo["Duration"]
    else:
        duration = -1
    print("Song is at " + str(newPos) + "ms of " + str(duration) + "ms")

try:
    player = BluePlayer()
    player.setCallbacks(newDeviceHandler, playPauseHandler, songChangeHandler, songPosChangeHandler)
    player.start()

    mainloop = GObject.MainLoop()
    mainloop.run()
except KeyboardInterrupt as ex:
    print("BluePlayer canceled by user")
except Exception as ex:
    print("How embarrassing. The following error occurred {}".format(ex))
finally:
    if player:
        player.shutdown()

"""
