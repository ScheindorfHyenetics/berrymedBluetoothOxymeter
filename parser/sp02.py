#!/usr/bin/python
'''
   ------Header-------
   OBJECT:  [python] (old and quickly-writed but totaly usable) parsing and display script
                     for (nearly undocumented) shangai berry electronics BM1000
                     bluetooth enabled blood oxymeter 
   AUTHOR:  SCHEINDORF HERLJOS ( Leucrocuta@HYENETICS ) 
   CONTACT: herljos@hyenetics.science
   LICENCE: none - public domain
   ---End of Header---

    python scrip to read bluetooth data on virtual serial port 
    sent by chineese oxymeter labelled model "BM1000" from "Shangai Berry Electric Tech"
    (but don't know if this is the right model name, as provided manual never mention anywhere
    existance of a bluetooth capability.)
    
    I picked up datagram of serialized datas from a link on the webpage where I bought this product,
    but don't know if it's still online, neither if they still sell this device.
    Unfortunatly , I don't remember where I saved it and if I even tought to save the file locally.
    This program is the only reference I had to provide these informations, so you have to trust my
    data structure if you have the same device and want to implement yourself code to read oxymeter output.
    (
      pay attention to the fact that bluetooth address of your device will certainly
      be different than mine. I hope that the port remains on the same number.
    )
    
    I don't went deep into python's bluetooth API, my only need was to know how to open a bt serial port
    and bytes read on it.
    Therefore, this script does not handle operations like turning bluetooth on and trusting the device.
    
    immediatly after bluetooth handshake, oxymeter starts sending binary stream.
    I don't remember if this is technically the case, but consider connection as read only, 
    as there are no documented functions initiated by host inputs, and the device never seeks for 
    any data neither.
    
    technical documentation mentioned that the data stream is 7 bytes lenght : 5 bytes of data + 2 null
    but this turned to be an error... 
    There are only 5 data bytes, constantly repeated with new values. 
    
    Datagram is :
    byte0   |byte1   |byte2   |byte3   |byte4
    1BPNSSSS|0LLLLLLL|0PRCGGGG|0ppppppp|0XXXXXXX
    
    8th bit of each bytes is synchronisation byte. Only set to 1 un first byte of current segment.
    After connection establishment, there are no garentee that the first received byte is a fist part 
    of a segment, or any other parts.
    Therefore, waiting for a byte where 8th bit is 1 before starting to proceed values is strongly advised.
    
    B   BEEP EVENT 0,1 
            raised to 1 when a new peak pulsation is counted
    P   PROBE FLAG 0,1
            ... I don't know, I always receive 0 ... 
    N   NO SIGNAL FLAG 0,1
           Exactly like probe flag, always 0 and no idea of the use
    S   SIGNAL 0,...,15
            first tought that it was bluetooth link quality,
            but now I think that it's the strenght of measured sensor raw signal used for 
            oxymetry and pulse rate calculation.
            Set to 15 when no finger or (re)calibration in progress
    L   PLETHYSMOGRAM 0,...,127 (values sent by device in 0...100)
            in this context, windowed hearth pulse strenght value 
            values used on device display to construct the bottom screen time graph
            Set to 100 when calibrating to find usable pulse signal, 
                to 0 when no sensing an inserted finger (or something else, it's up to you)
    Pp  HEART PULSE RATE 0,...,255
            8th bit is bit P from byte2 then remaining bits are p from byte3
            Set to 255 when nothing to sense or no values to display
    R   HEART PULSE DETECTION FLAG 0,1 
            inverted logic value : 0 means calibration still running or nothing inserted under the sensor
    C   FINGER DETECTION FLAG 0,1
            inverted logic value : 0 means sensor is trying measurement            
    G   VISUAL PULSE INTENSITY 0,...,15
            rewindowed pulse strenght value used in device display for the height bar on right of screen 
            like Pleth. value, 0 when no sensing, 15 when no measurements displayed
    X   BLOOD O2 SATURATION 0,...,127 (sent values in 1...100 and 127) 
            bloodstream oxygen saturation calculated by absorbtion rate of
            two lights spot of different frequencies traversing the flesh.
            Set to 127 when no calibration, or nothing between led and photodiode.
    
    *** unstripped content : lot of debug instructions + integral of the old 'quick fix' version + etc, let in comment ***

    *** why a so complex rewrite of a very simple program ? 
    *** => this code is intented to be reused as base structure for a general purpose binary steam unpacker, validity checker, decoder, and data visualization applier. I will probably implement capability to deal with unfixed datagram structure, and use this generic parser to rewrite my old php sms decoder script.
    
'''
 
#STRIP#import serial
import time
import sys
import itertools
import os
import bluetooth
import math
import numbers
import decimal
import json

### helper functions ###
#x is a number (but not a string expressing a number)
#ex: isnumber(80) => True
def isnumber(x):
    return isinstance(x, numbers.Number)

#x is a number or a string representing a number
#ex: isnumber('90.5') => True
def isnumberwstr(x):
    if isinstance(x, numbers.Number):
        return True
    else:
        try:
            x = float(x)
        except ValueError as e:
            return False
        return True
    return False

#return a function checking if a value is item of bounds list
# validstates define states on which constraint is applyed
#ex: contextenumboundaries(validstates=set(('raw',))
def contextenumboundaries(validstates=set(('raw','decoded','alternative'))):
    if not isinstance(validstates,set):
        try:
            validstates = set(validstates)
        except Exception as e:
            return (False,"validstate must be convertible to set object to construct enumboundaries")
    if len(validstates) == 0:
        return (False,"validstate must contain at least one item to construct enumboundaries")    
    staticbounds = []
    def contextincr():
        cheight = len(staticbounds)
        staticbounds.append([None,validstates.copy()])    
        def enumboundaries(key,state,value,currentwork,bounds=None):
            cbounds = staticbounds[cheight][0]
            vstates = staticbounds[cheight][1]
            errtuple = (False,key, state, vstates, cbounds, value)
            if not state in vstates:
                return True
            if state == 'raw':
                if bounds is None:
                    return errtuple+('cannot enforce value if possible list not given',)
            if not bounds is None:
                staticbounds[cheight][0] = bounds
                cbounds = staticbounds[cheight][0]
            if state != 'raw' and cbounds is None:
                return errtuple+('cannot enforce value if possible list not given',)
            for v in cbounds:
                if v == value: 
                    return True
            return errtuple+('value %s not enumerated in possible values' % (value,),)            
        return enumboundaries
    def fixcontextenumboundaries(validstates=set(('raw','decoded','alternative'))):
        if not isinstance(validstates,set):
            try:
                validstates = set(validstates)
            except Exception as e:
                return (False,"validstate must be convertible to set object to construct enumboundaries")
        if len(validstates) == 0:
            return (False,"validstate must contain at least one item to construct enumboundaries")    
        n = froze()
        staticbounds[len(staticbounds)-1][1] = validstates.copy()
        return n
    froze = contextincr
    globals()['contextenumboundaries'] = fixcontextenumboundaries
    return froze()

# check if value is between bounds, apply only on raw state
def intboundaries(key,state,value,currentwork,bounds=None):
    errtuple = (False, key, state, value)
    if state != 'raw':
        return True
    if not isnumber(value):
        if not value.isdigit():
           return errtuple+('cannot enforce numerical boundaries on NaN value',)
        value = int(value)
    if bounds is None: 
        return errtuple+('cannot enforce unknown bounds',)
    if len(filter(lambda v: isnumber(v),bounds)) == 2:
        if value >= bounds[0] and value <= bounds[1]:
            return True
        else:
            return errtuple+('value %s not between boundaries %d-%d' % ((value,)+tuple(bounds)),)
    for rule in bounds:
        if (any(map(lambda t:isinstance(rule, t),(list,tuple))) and
           len(filter(lambda v: isnumber(v),rule)) == 2):
                if not (value >= bounds[0] and value <= bounds[1]):
                   return errtuple+('value %s not between boundaries %d-%d' % ((value,)+tuple(rule)),)
                else:
                   return True
        else: 
            if value == rule:
                return True
    return errtuple+('value %s not enumerated in possible values' % (value,),)

# if cond function applyed to segment is True, then replace segments items in replace
# using values from by
# ex: replacebyif(segment,[['pulse'],['spO2'],['_alternate','pulse'],['_alternate','spO2']],[0,0,'N/A','N/A'],lambda seg: seg['nofinger'] == True)
def replacebyif(segment,replace,by,cond):
    if cond(segment):
        for ind,subkey in enumerate(replace):
            try:
                subkey = directref(segment,subkey)
                subkey('set',by[ind])        
            except Exception as e:
                pass

def directref(segment, path):
    def directrefaccessor(mode='get',newvalue=None):
        if not mode in ('get','set'):
            raise ValueError('mode %s not valid operation (set|get)' % mode)
        if mode == 'get':
            return cur[curindex]
        elif mode == 'set':
            cur[curindex] = newvalue
    cur = segment
    _debugpath = ''
    for descend in path[0:len(path)-1]:
        _debugpath = "%s/%s" % (_debugpath, descend)
        if cur.__contains__(descend):
            cur = cur.__getitem__(descend)
        else: 
            raise KeyError('key %s in segment[%s] not existent at this level (keys in cur = %s)' % (descend, _debugpath, cur.keys()))
    curindex = path[len(path)-1]
    if not cur.__contains__(curindex):
        raise KeyError('key %s in segment[%s] not existent at this level (keys in cur = %s)' % (curindex, _debugpath, cur.keys()))
    return directrefaccessor

def bargraph(value,vmax,window,chars='[#| ]',direction=True):
    windowed = int(math.ceil(float(value)/float(vmax)*float(window)))
    if direction == False:
        chars = chars[0] + chars[3] + chars[2] + chars[1] + chars[4]
    string = chars[0] + chars[1]*(windowed-1) + chars[2] + chars[3]*(window-windowed) + chars[4]
    return string

#meanings for final unpacked items:
#          d short description (provide only one time for each same items) (default: "")
#            shorcut access metadata(unpacked segment)('help',itemname)
#          b known boundaries, tupple with boundaries values to express numeric interval,
#                               or tupple enumerating possible raw values
#            value accessible by shorcut ('bounds',itemname) 
#            in function returned by metadata(unpacked segment)
#            (default: None)
#          u decoding function used for each completely read items (i.e. character string unpacking)
#            provided arguments are current item to transform designator and value,
#                               and actual state of unpacked segment.
#            raw value still accessible by shorcut ('raw',itemname) ... 
#            (default: None)
#          c constraint checking function if one is required. checked after a full item record is got.
#            and after eventual decoding and transmogrifying.
#            arguments are designator, 'raw'/'decoded'/'alternative' and the corresponding value
#                       + current state of unpacking
#                       + for raw value, known boundaries is provided altogether if defined
#            if (False,...) is returned when checking an item,exception is raised with tuple in payload. 
#            (default: None)
#          t corresponding typing assigned to object containing final item value,
#            after optional transformation/decode (default: long)
#          e transformation function to apply on decoded value if desired or needed
#            (i.e. graphical display of windowed value with no trivial numeric reading)
#            transmogryfied value doesn't replace decoded item, but is accessible via : 
#            metadata(unpacked segment)('altered') 
#            arguments are decoded value to format and designator and current state of unpacking
#            (default: None)
#          f final function called on each items avec full reception on a valid segment
#            arguments are designator, item raw value, decoded value, alternative value,
#            and fully unpacked segment
#            return value unrelevant, function is advised to directly modify segment dictionary
datagram = {'bitmap':((('sync',4),'beep','noprobe','nosignal')+('signal',)*4,
                      (('sync',3),)+('pleth',)*7,
                      (('sync',2),('pulse',7),'nopulse','nofinger')+('pulsebar',)*4,
                      (('sync',1),)+tuple(map(lambda i: ('pulse',6-i), range(0,7))),
                      (('sync',0),)+('satO2',)*7
                     ),
            'content': 
                      {
                       'sync': { 'd':'synchronization bit',
                                 'b':(16,),
                                 'u':None,
                                 'c':contextenumboundaries(validstates=set(('raw',))),
                                 't':long,
                                 'e':lambda k,v,s: None,
                                 'f':lambda k,raw,decoded,formated,s: None
                               },
                       'signal':
                                {'d':'measured signal strength',
                                 'b':(0,15),
                                 'u':None,
                                 'c':intboundaries,
                                 't':long,
                                 'e':lambda k,v,s: "%s%s" % (k,bargraph(v,15,10)),
                                 'f':lambda k,raw,decoded,formated,s: None
                                },
                       'nosignal': {
                                    'd':'???',
                                    'b':(0,1),
                                    'u':lambda k,v,s: v != 0,
                                    'c':contextenumboundaries(validstates=set(('raw',))),
                                    't':bool,
                                    'e':lambda k,v,s: (v and '[x]%s' or '[ ]%s') % k,
                                    'f':lambda k,raw,decoded,formated,s: None
                                   },
                       'noprobe': {
                                    'd':'???',
                                    'b':(0,1),
                                    'u':lambda k,v,s: v != 0,
                                    'c':contextenumboundaries(validstates=set(('raw',))),
                                    't':bool,
                                    'e':lambda k,v,s: (v and '[x]%s' or '[ ]%s') % k,
                                    'f':lambda k,raw,decoded,formated,s: None,
                                   },
                       'beep': {
                                    'd':'new pulse counted at this point',
                                    'b':(0,1),
                                    'u':lambda k,v,s: v != 0,
                                    'c':contextenumboundaries(validstates=set(('raw',))),
                                    't':bool,
                                    'e':lambda k,v,s: (v and '<%s>'%k or '< >'),
                                    'f':lambda k,raw,decoded,formated,s: None
                               },
                       'pleth':
                                {'d':'hearth pulse measured strengh',
                                 'b':(0,100),
                                 'u':None,
                                 'c':intboundaries,
                                 't':long,
                                 'e':lambda k,v,s: "%s%s" % (k,bargraph(v,100,20)),
                                 'f':lambda k,raw,decoded,formated,s: None
                                }, 
                        'pulse':
                                {
                                 'd':'hearth BPM frequency',
                                 'b':(0,255),
                                 'u':None,
                                 'c':intboundaries,
                                 't':long,
                                 'e':lambda k,v,s: "%s BPM < %s >" % (v,(
                                                                           (v < 30 and "[!] severe bradychardia") or
                                                                           (v < 50 and "[*] bradychardia") or 
                                                                           (v < 90 and "[ ] -") or
                                                                           (v < 125 and "[*] tachychardia") or
                                                                           ('[!] serious tachycardia')
                                                                        )
                                                                     ),
                                 'f':lambda k,raw,decoded,formated,s: None
                                },
                        'nopulse': {
                                        'd':'pulse calibration in progress',
                                        'b':(0,1),
                                        'u':lambda k,v,s: v != 0,
                                        'c':contextenumboundaries(validstates=set(('raw',))),
                                        't':bool,
                                        'e':lambda k,v,s: (v and '[x]%s' or '[ ]%s') % k,
                                        'f':lambda k,raw,decoded,formated,s: None
                                    },                                
                        'nofinger': {
                                        'd':'no detection of an inserted finger',
                                        'b':(0,1),
                                        'u':lambda k,v,s: v != 0,
                                        'c':contextenumboundaries(validstates=set(('raw',))),
                                        't':bool,
                                        'e':lambda k,v,s: (v and '[x]%s' or '[ ]%s') % k,
                                        'f':lambda k,raw,decoded,formated,s: None
                                    },
                        'pulsebar':
                                    {'d':'pulse strength bargraph',
                                     'b':(0,15),
                                     'u':None,
                                     'c':intboundaries,
                                     't':long,
                                     'e':lambda k,v,s: "%s%s" % (k,bargraph(v,15,15)),
                                     'f':lambda k,raw,decoded,formated,s: None
                                    },
                        'satO2':
                                {'d':'blood oxygen saturation',
                                 'b':(0,127),
                                 'u':None,
                                 'c':intboundaries,
                                 't':long,
                                 'e':lambda k,v,s: "%s %%" % (v),
                                 'f':lambda k,raw,decoded,formated,s: None
                                }
                      }
        }

class datagramparser:
    def __init__(self, datagram):
        self.datagram = datagram
        self.segbytes = len(datagram['bitmap'])
    
    def newsegment(self):
        fields = self.datagram['content'].keys()
        segment = {}
        for key in fields:
            segment[key] = 0
        segment['_alternate'] = {}
        segment['_raw'] = {}
        return segment
    
    def parsebyte(self, data, bytenum):
        model = self.datagram['bitmap'][bytenum]
        cbit = 128
        unpacked = {}
        counter = {}
        #print(bin(data))
        for i in model:
            if not isinstance(i,tuple):
                if not i in unpacked:
                    unpacked[i] = 0
                    counter[i] = len(filter(lambda x: x == i,model))
                counter[i] -= 1
                i = (i,counter[i])
            else:
                if not i[0] in unpacked:
                    unpacked[i[0]] = 0
                    counter[i[0]] = 0
            #print("%s : %s * %s | %s" % (i[0],bool(data & cbit),2**i[1],unpacked[i[0]]))
            unpacked[i[0]] = (bool(data & cbit)*(2**i[1])) | unpacked[i[0]]
            cbit = cbit / 2
        return unpacked
    
    def mergebytes(self,datas,bytedata):
        mergekeys = set(datas.keys()).union(set(bytedata.keys()))
        merged = {}
        for k in mergekeys:
            if k in datas:
                l = datas[k]
            else:
                l = 0
            if k in bytedata:
                r = bytedata[k]
            else:
                r = 0
            merged[k] = l | r
        return merged
        
    def readrawsegment(self,datas):
        segment = self.newsegment()
        unpack = {}
        if len(datas) < self.segbytes:
            raise ValueError('segment lenght %s , expected %s' % (len(datas),self.segbytes))
        for i,byte in enumerate(datas):
            unpack = self.mergebytes(unpack,self.parsebyte(byte,i))
        segment.update(unpack)
        return segment
    
    def applyrules(self,segment):
        for item in self.datagram['content']:
            model = self.datagram['content'][item]
            cur = segment[item]
            segment['_raw'][item] = cur
            #intboundaries(key,state,value,currentwork,bounds=None)
            if 'c' in model:
                constraint = model['c']
                if 'b' in model: 
                    bounds = model['b']
                else:
                    bounds = None
            else:
                constraint = None
            if not constraint is None:
                r = constraint(item,'raw',cur,segment,bounds)
                if isinstance(r,tuple):
                    raise ValueError('constraint failure on %s value %s : %s' % (item,cur,r))
            #print(bin(cur))
            if 'u' in model:
                if not model['u'] is None:
                    unpackitm = model['u']
                    cur = unpackitm(item,cur,segment)
                    segment[item] = cur
                    if not constraint is None:
                        r = constraint(item,'decoded',cur,segment,bounds)
                        if isinstance(r,tuple):
                            raise ValueError('constraint failure on %s value %s : %s' % (item,cur,r))
            #print(segment[item])
            segment[item] = model['t'](segment[item])
            #print(segment[item])
            if 'e' in model:
                if not model['e'] is None:
                    altern = model['e']
                    alt = altern(item,segment[item],segment)
                    if not constraint is None:
                        r = constraint(item,'alternative',cur,segment,bounds)
                        if isinstance(r,tuple):
                            raise ValueError('constraint failure on %s value %s : %s' % (item,cur,r))
                    segment['_alternate'][item] = alt
            #print(segment[item])
        for item in self.datagram['content']:
            model = self.datagram['content'][item]
            if 'f' in model:
                #k,raw,decoded,formated,s
                fin = model['f']
                if item in segment['_alternate']:
                    alt = segment['_alternate'][item]
                else:
                    alt = segment[item]
                fin(item,segment['_raw'][item],segment[item],alt,segment)
        return segment
    
    def metadata(self,segment):
        def reader(req, key):
            if (key == '_alternate' or key == '_raw'):
                raise IndexError('%s should not be used in metadata call !' % key)
            structure = self.datagram
            validreqs = {'help': lambda datas,key: structure['content'][key]['d'],
                         'length': lambda datas,key: sum(
                                                         map(lambda cbyte: len(filter(lambda v: v==key or ((isinstance(v,tuple) or isinstance(v,list)) and v[0]==key), structure['bitmap'][cbyte])),range(0,len(structure['bitmap'])))
                                                         ),
                         'bounds': lambda datas,key: structure['content'][key]['b'],
                         'alter': lambda datas,key: (key in datas['_alternate']) and datas['_alternate'][key] or datas[key],
                         'raw': lambda datas,key: datas['_raw'][key]
                         }
            return validreqs[req](segment,key)
        return reader        

#wanted to test the compile() function - uncomment is not advised
#_DO_INTERACTIVE = False
#if _DO_INTERACTIVE :
    #import copy
    #_state_ = copy.copy(vars())
    #import traceback
    #import dis
    #x = ''
    #code = None
    #while _DO_INTERACTIVE :
        #x += raw_input('(RST buffer/END session) EVAL>')
        #if x[-3:] == "RST":
            #x = ''
            #continue
        #if x[-3:] == "END":
            #for i in vars().keys():
                #if i == '_state_' or i == 'i':
                    #continue
                #if not i in _state_:
                    #print('removing %s' % i)
                    #del vars()[i]
                    #continue
                #if vars()[i] != _state_[i]:
                    #print('restoring %s to %s' % (i,_state_[i]))
                    #vars()[i] = _state_[i]
            #del _state_
            #del i
            #_DO_INTERACTIVE = False
            #break
        #try:
            #x = reduce(lambda txt,rep: txt.replace(rep,''),[x,"x=","x =","import","read(","write(","truncate(","open(","io.","os."])
            #code = compile(x,'<interactive>','single')
            #print('compilation done, eval : %s' % x)
            #eval(code)
        #except Exception as e:
            #traceback.print_exc()


try:
    """ os.system("bash -c 'rfcomm connect 22 8C:DE:52:65:12:4F 6 &'")
    time.sleep(10)
    rf = serial.Serial(port="/dev/rfcomm22", 
                       baudrate=115200,
                       bytesize=8,
                       parity=serial.PARITY_NONE,
                       stopbits=serial.STOPBITS_ONE,
                       timeout=1,
                       xonxoff=False,
                       rtscts=False,
                       writeTimeout=None,
                       dsrdtr=False,
                       interCharTimeout=None)
    rf.open() """
    bd_addr = "8C:DE:52:65:12:4F"
    port = 6
    sock=bluetooth.BluetoothSocket( bluetooth.RFCOMM )
    sock.connect((bd_addr, port))
    ''' synced = False
        nbyte = None
        pulsemax = 0
        pulsemin = 9999
        satmax = 0
        satmin = 9999
        signal = 0
        flagns = True
        flprob = True
        flbeep = False
        pleth  = 0
        sat    = 0
        bargr  = 0
        flsens = False
        pulser = False
        pulse = 0
        byte6 = 0
        byte7 = 0
        prevbg = 0
        while True:
            a = ord(sock.recv(1))
            if not synced:
                b = a & 0b10000000
                if b != 0:
                    synced = 1
                    nbyte = 0
            if nbyte is not None:
                if nbyte > 0:
                    if (a & 0b10000000) != 0:
                        raise BaseException('sync error byte {} {}'.format(str(nbyte),str(bin(a))))
                if nbyte == 0:
                    if (a & 0b10000000) == 0:
                        raise BaseException('sync error byte 0 {}'.format(str(bin(a))))
                    signal = a & 0b00001111
                    flagns = (a & 0b00010000) >> 4
                    flprob = (a & 0b00100000) >> 5
                    flbeep = (a & 0b01000000) >> 6
                elif nbyte == 1:
                    pleth =  a & 0b01111111
                elif nbyte == 2:
                    bargr =  a & 0b00001111
                    flsens = (a & 0b00010000) >> 4
                    pulser = (a & 0b00100000) >> 5
                    pulse =  (a & 0b01000000) >> 6
                elif nbyte == 3:
                    pulse =  (pulse << 7) | (a & 0b01111111)
                elif nbyte == 4:
                    sat =    a & 0b01111111 
                    if pulsemax < pulse and pulser == 0:
                        pulsemax = pulse
                    if pulsemin > pulse and pulser == 0:
                        pulsemin = pulse
                    if satmax < sat and pulser == 0:
                        satmax = sat
                    if satmin > sat and pulser == 0:
                        satmin = sat
                    
                    plethX = int(math.ceil(pleth/10))
                    plethX = '[' + ('-' * plethX) + '#' + (' ' * (11 - plethX)) + ']'
                    
                    bargrX = int(bargr)
                    bargrX = '[' + ('-' * bargrX) + '#' + (' ' * (14 - bargrX)) + ']'
                    
                    bgprim = bargr - prevbg
                    prevbg = bargr
                    
                    if bgprim < 0:
                        prevbgX = '\\'
                    elif bgprim == 0:
                        prevbgX = '-'
                    else:
                        prevbgX = '/'
                    
                    print('{} {} {} {} {} {} {} {} {} pulse {} (min {} max {}) sat {} (min {} max {})'.format(signal,
                                                                 flagns,
                                                                 flprob,
                                                                 flbeep,
                                                                 plethX,
                                                                 bargrX,
                                                                 prevbgX,
                                                                 flsens,
                                                                 pulser,
                                                                 pulse,
                                                                 pulsemin,
                                                                 pulsemax,
                                                                 sat,
                                                                 satmin,
                                                                 satmax))
                                                             #byte6,
                                                             #byte7))
    #            elif nbyte == 5:
    #                byte6 = a
    #            elif nbyte == 6:
    #                byte7 = a
                nbyte = (nbyte + 1) % 5 '''
    
    parser = datagramparser(datagram)
    a = ord(sock.recv(1))
    while a & 128 == 0:
        a = ord(sock.recv(1))
    bytemap = [a]
    while True:
        while len(bytemap) < 5:
            bytemap.append(ord(sock.recv(1)))
        segment = parser.applyrules(parser.readrawsegment(bytemap))
        replacebyif(segment,[['pulse'],['satO2'],['_alternate','pulse'],['_alternate','satO2']],[None,None,'N/A','N/A'],lambda seg: seg['nofinger'] == True or seg['nopulse'] == True)
        segment['timestamp'] = time.time()
        bytemap = []
        strsegment = []
        #for i in segment:
        #    if i in ['_raw','_alternate','sync']:
        #        continue
        #    strsegment.append(parser.metadata(segment)('alter',i))
            #strsegment.append(str(parser.metadata(segment)('raw',i)))
            #strsegment.append(str(segment[i]))
        #print(' , '.join(strsegment))
        print(json.dumps(segment))
        print('')
except Exception as e:
    print(json.dumps(e.message))
    #print(sys.exc_info()[2].tb_lineno)
finally:
    sock.close()
    exit()
    
