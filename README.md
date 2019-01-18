# BluePlayer
A python library created to use a linux machine as a "bluetooth speaker" with AVRCP support


## EXAMPLE OF USAGE:

```
GObject.threads_init()
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

player = None

# Handlers definition
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

# Player initializaion
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
```