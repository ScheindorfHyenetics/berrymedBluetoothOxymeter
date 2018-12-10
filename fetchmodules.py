#!/bin/bash

PIPEXE="pip2"
PYTHONEXE="/usr/bin/python2.7"
DEVICEID="8C:DE:52:65:12:4F"

ARGLIST=" ./fetchmodules.py '<PIP2 Path>' '<python2 path>' '<your bluetooth device id>"
ARGNUM=3

IDPATCH="/tmp/id.patch"

if [[ -e $(pwd)/parser ]] && [[ -e $(pwd)/gui ]]
then


if [[ -n "$1" ]]
then if [[ "$1" = "-h" ]] || [[ "$1" = "--help" ]]
    then echo "this script ensure to install all required modules using pip for python 2"
         echo "it can also patch the original code to adapt to your device and preferences"
         echo "==="
         echo "Usage: " $ARGLIST " ;"
         echo "You can run the script with all defaults params by running without arguments"
         echo "Or you can run it customized and then you need to supply ALL the arguyments"
         exit 1
   fi
   if [[ $# -lt $ARGNUM ]]
   then echo "You need to provide ALL the arguments : " $ARGLIST
        exit 2
   fi
   PIPEXE="$1"
   PYTHONEXE="$2"
   DEVICEID="$3"
fi

echo "Using $PIPEXE to install modules"
echo "Using python exec at $PYTHONEXE"
echo "Patch parser with device id : $DEVICEID"

sleep 1

echo "= require bluetooth module ="

sleep 1

echo $PIPEXE "install pybluez"
$PIPEXE install pybluez

echo " . "
sleep 1
echo "= require ptGTK ="
$PIPEXE install pygtk

sleep 1
echo "= Patching device ID ="
sleep 1
echo " . "

echo "--- parser/sp02.py      2017-04-18 09:01:28.542629549 +0200" > "$IDPATCH"
echo "+++ /tmp/spo.pt 2018-12-10 21:47:41.217490514 +0100" >> "$IDPATCH"
echo "@@ -563,7 +563,7 @@" >> "$IDPATCH"
echo "                        dsrdtr=False," >> "$IDPATCH"
echo "                        interCharTimeout=None)" >> "$IDPATCH"
echo "     rf.open() \"\"\"" >> "$IDPATCH"
echo "-    bd_addr = \"8C:DE:52:65:12:4F\"" >> "$IDPATCH"
echo "+    bd_addr = \"$DEVICEID\"" >> "$IDPATCH"
echo "     port = 6" >> "$IDPATCH"
echo "     sock=bluetooth.BluetoothSocket( bluetooth.RFCOMM )" >> "$IDPATCH"
echo "     sock.connect((bd_addr, port))" >> "$IDPATCH"
cp -v parser/sp02.py parser/sp02.origine.py
if [[ -e parser/sp02.origine.py ]]
then "copied original file as parser/sp02.origine.py , now apply patch $IDPATCH on parser/sp02.py"
     sleep 1
     patch  parser/sp02.py "$IDPATCH" && echo "Backuped then patched sp02.py" || { echo "patching failed, critical error" ; exit 4 ; }
else echo "can't make a copy of sp02.py, I wont patch it, halting"
     exit 5
fi
echo " === "
echo " Everything should be working now, if nothing failed. "
echo " Kenore tawa "
echo " ____________________________________________________ "
exit 0
else echo "please run this script from the project root path"
     exit 3
fi
