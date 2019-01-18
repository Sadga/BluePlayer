#!/bin/bash

if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

echo "Installing needed software..."
apt-get -qq update && apt-get -qq --yes install alsa-utils bluez bluez-tools pulseaudio-module-bluetooth python-gobject python-gobject-2 python3-gi python3-dbus 1>/dev/null 2>/dev/null
if [ $? -eq 0 ]; then
    echo "Software installed correctly"
else
    echo "Software installation fail"
    exit
fi

if grep -q "##a2dp_setup##" "/etc/pulse/daemon.conf"; then
    echo "/etc/pulse/daemon.conf => Already OK"
else
    RESAMPLE_METHOD="ffmpeg"

    echo
    echo "Please choose bluetooth resample-method"
    echo "0  => src-sinc-best-quality"
    echo "1  => src-sinc-medium-quality"
    echo "2  => src-sinc-fastest"
    echo "3  => src-zero-order-hold"
    echo "4  => src-linear"
    echo "5  => trivial"
    echo "6  => speex-float-N"
    echo "7  => speex-fixed-N"
    echo "8  => ffmpeg (Default)"
    echo "9  => soxr-mq"
    echo "10 => soxr-hq"
    echo "11 => soxr-vhq"
    echo -n "Choice: "

    read choice

    case $choice in
        '0') RESAMPLE_METHOD="src-sinc-best-quality";;
        '1') RESAMPLE_METHOD="src-sinc-medium-quality";;
        '2') RESAMPLE_METHOD="src-sinc-fastest";;
        '3') RESAMPLE_METHOD="src-zero-order-hold";;
        '4') RESAMPLE_METHOD="src-linear";;
        '5') RESAMPLE_METHOD="trivial";;
        '6') RESAMPLE_METHOD="speex-float-N";;
        '7') RESAMPLE_METHOD="speex-fixed-N";;
        '8') RESAMPLE_METHOD="ffmpeg";;
        '9') RESAMPLE_METHOD="soxr-mq";;
        '10') RESAMPLE_METHOD="soxr-hq";;
        '11') RESAMPLE_METHOD="soxr-vhq";;

        *)   echo "Wrong option, using ffmpeg";;
    esac

    echo
    echo "\"$RESAMPLE_METHOD\" selected, to change it edit the file /etc/pulse/daemon.conf"
    echo

    echo                                    >> /etc/pulse/daemon.conf
    echo                                    >> /etc/pulse/daemon.conf
    echo                                    >> /etc/pulse/daemon.conf
    echo "##a2dp_setup##"                   >> /etc/pulse/daemon.conf
    echo "## Bluetooth audio conf ##"       >> /etc/pulse/daemon.conf
    echo "resample-method=$RESAMPLE_METHOD" >> /etc/pulse/daemon.conf
    echo "enable-remixing = no"             >> /etc/pulse/daemon.conf
    echo "enable-lfe-remixing = no"         >> /etc/pulse/daemon.conf
    echo "default-sample-format = s32le"    >> /etc/pulse/daemon.conf
    echo "default-sample-rate = 192000"     >> /etc/pulse/daemon.conf
    echo "alternate-sample-rate = 176000"   >> /etc/pulse/daemon.conf
    echo "default-sample-channels = 2"      >> /etc/pulse/daemon.conf
    echo "exit-idle-time = -1"              >> /etc/pulse/daemon.conf
    echo "## Bluetooth audio conf ##"       >> /etc/pulse/daemon.conf
    echo "/etc/pulse/daemon.conf => OK"

    echo "" >> "/tmp/a2dpSR"
fi

if [ -f "/tmp/a2dpSR" ]; then
    echo ""
    echo "Please reboot the system"
fi

# bluetooth class of device: 0x200414

exit
