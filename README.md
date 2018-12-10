# berrymedBluetoothOxymeter
Data acquisition and GUI for BerryMed Oxymeter


DISCLAIMER
This program was wrote for my specific device, I don't know bluetooth well and I don't know if the device id of my
oxymeter is the same as every other produced devices, or if each one has unique id.
If your device is a berrymed oxymeter and your run is telling that there are no host, then :
run bluetoothctl
enter : power on
then : scan on
make sure you had turn on your oxymeter at this point
then enter : devices
and select the hexadecimal part of the line "Device 8C:DE:52:65:12:4F BerryMed"
With this key, open parser/sp02.py and at line 566 replace the hexa id here by yours : bd_addr = "8C:DE:52:65:12:4F"

Please read DEPENDS.txt for informations about required things.

making it short: 
bluetooth is read and converted to structured JSON by the parser. Find it in parser directory.
Then you can pipe this JSON to a file, or better, to the stdin of the GUI interface. It's in gui dir.
There are multiple files cuz I tested with blocking IO and non blocking IO.

You can also replay JSON from a saved file by cating it piped in gui.
 But this can lead to a bug because of the speed the datas are received this way.
So you can use ratelimit.py in parser directory.


=== Read and View ===
python2.7 berrymedBluetoothOxymeter/parser/sp02.py | python2.7 berrymedBluetoothOxymeter/gui/jsonread.nonblock.py

=== Read, Record ===
python2.7 berrymedBluetoothOxymeter/parser/sp02.py > /path/to/file.json 

=== Read, Record, View ===
python2.7 berrymedBluetoothOxymeter/parser/sp02.py | tee  /path/to/file.json |  python2.7 berrymedBluetoothOxymeter/gui/jsonread.nonblock.py

=== Replay a file ===
cat /path/to/json | python2.7 berrymedBluetoothOxymeter/parser/ratelimit.py |  python2.7 berrymedBluetoothOxymeter/gui/jsonread.nonblock.py


===Experimental stuff in gui===
add "--experiments" option :  python2.7 berrymedBluetoothOxymeter/gui/jsonread.nonblock.py --experiments


!!!
!!!

I included a file called fetchmodule.py in this project, its purpos is to install required modules (ie bluetooth)  and make changes to the code (ie device uuid)
run it from the same directory as the script, please.
