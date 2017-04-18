#!/usr/bin/python
# -*- coding: utf8 -*-

# turn on bluetooth then your berrymed device, 
# then : python sp02.py | python jsonreadtest.py

import sys
import json
import os
import sys
import pygtk
pygtk.require("2.0")
import gtk
import gtk.glade
import gobject
import traceback
import random
import itertools
import math
import time
import threading as th
import fcntl

__cpath__ = os.path.dirname(sys.argv[0]) + os.sep     

_experiments_ = False
if "--experiments" in sys.argv: _experiments_ = True

def dumpattr(obj,deep=1,offset=''):
    print("%s %s" % (offset,obj))
    if deep > 0:
        for attr in dir(obj):
            try:
                dumpattr(getattr(obj,attr),deep=(deep-1),offset=(offset+'-%s-'%(attr,)))
            except AttributeError as e:
                print('%s AttributeError %s' % (offset,attr))

def timestring(seconds):
    ltime = time.localtime(float(seconds))
    strtime = "d%s m%s y%s %s:%s:%s" % (ltime.tm_mday,ltime.tm_mon,ltime.tm_year,ltime.tm_hour,ltime.tm_min,ltime.tm_sec)
    return strtime
    
def rewindow(value,flwb,fupb,tlwb,tupb):
    value = (float(value)-float(flwb))/(float(fupb)-float(flwb))
    value = value*(float(tupb)-float(tlwb))+float(tlwb)
    return value

class thisapp:
    def __init__(self):
        interface = gtk.Builder()
        interface.add_from_file('%s/sp02.glade' % (__cpath__,))
        interface.connect_signals(self)
        self.interface = interface
        self.assignmap(['hbox1','hbox3','hbox5','satl','ratel','fnopulse','fnofinger','signaltxt','lsttimetxt','lastbeeptobeep','beeper','beep2beepavgl','beatduration','beatrms','beatrmsovertime','beatrmsdeoffset'],['hbox1','hbox3','hbox5','sat','rate','nopulse','nofinger','signal','timestamp','lastbeeptobeep','beeper','beep2beepavgl','beatduration','beatrms','beatrmsovertime','beatrmsdeoffset'])
        self.createprogressbars('pleth',self.hbox1,250)
        self.createprogressbars('satp',self.hbox3,200)
        self.createprogressbars('ratep',self.hbox5,200)
        #if _experiments_:
            #self.createprogressbars('d_dt_pleth',self.hbox8,250)
            #self.cd_dt_pleth = self.cpleth
            #self.lastcd_dt_pleth = self.lastcpleth
        map(lambda k:
                     map(lambda sfx: 
                                    setattr(self,'%s%sl' % (k,sfx), interface.get_object("%s%s" % (k,sfx))) or setattr(self,'%s%sv' % (k,sfx),None),
                         ['max','min']),
            ['rate','sat','beep2beep'])
        self.clipboard = gtk.Clipboard()
        self.crateplwb = 0
        self.cratepupb = 255
        self.crateplocmin = 255
        self.crateplocmax = 0
        self.rdline = ''
        gobject.threads_init()
        self.tjsonuplink = []
        self.exitevent = th.Event()
        if not _experiments_:
            interface.get_object("experiments").set_property('visible',False)
        else :
            self.lastbeep = 0
            self.beep2beep = [0]*10
            self.beep2beeppt = 0
            self.beep2beepavgv = 0
            self.lasttime = 0
            self.dfplwb = -255
            self.dfpupb = 255
            self.localdfmin = 255
            self.localdfmax = -255
            self.pwrstmark = [False,False,0,0]
        self.tjson = th.Thread(target=self.parsejson,kwargs={'uplink':self.tjsonuplink,'onexit':self.exitevent})
        self.tjson.start()
        gobject.timeout_add(10, self.checkjson)
    
    def checkjson(self):
        if not self.tjson.isAlive():
            print('contact lost with json parser thread. termination')
            gtk.main_quit()
            exit()
        instlen = min(len(self.tjsonuplink),5)
        while instlen > 0:
            obj = self.tjsonuplink.pop(0)
            try:
                self.windisplay(obj)
            except Exception as e:
                traceback.print_exc()
            instlen -= 1
        return True
    
    def assignmap(self,attrnames,gtkbuildobjs):
        for kn,key in enumerate(attrnames):
            setattr(self,key,self.interface.get_object(gtkbuildobjs[kn]))
    
    def createprogressbars(self,gid,container,howmany,requestwidth=5,orientation='bottom-to-top'):
        progressbargroup = []
        for i in range(0,howmany):
            progressbargroup.append(gtk.ProgressBar(None))
            progressbargroup[i].set_property('width_request',requestwidth)
            progressbargroup[i].set_property('orientation','bottom-to-top')
            progressbargroup[i].set_visible(True)
            #container.add(progressbargroup[i])
            container.pack_start(progressbargroup[i],False,True)
            progressbargroup[i].show()
            progressbargroup[i].set_property('fraction',0.5)
        setattr(self,gid,progressbargroup)
        setattr(self,'c%s' % gid,itertools.cycle(xrange(0,howmany)))
        setattr(self,'lastc%s' % gid,0)
    
    def parsejson(self,uplink=None,onexit=None):
        ending = False
        if uplink is None or onexit is None: 
            return False
        while not ending:
            try:
                if onexit.isSet():
                    print('thread exit requested')
                    ending = True
                    return False
                #char = sys.stdin.read(1)
                #if char == '':
                #    raise StopIteration()
                line = sys.stdin.next()
                #print(line,self.rdline)
                obj = None
                #while line != '':
                #self.rdline += char
                #line = line[1:]
                #if self.rdline[-2:] == "\n\n":
                try:
                    try:
                        #obj = json.loads(self.rdline)
                        #print(line)
                        obj = json.loads(line)
                    except Exception as e:
                        pass
                    if not obj is None:
                        uplink.append(obj)
                        #self.windisplay(obj)
                        #self.rdline = line
                        #return True
                except Exception as e:
                    traceback.print_exc()
                finally:
                    self.rdline = ''
                    #time.sleep(0.001)
                    #return True
            except StopIteration:
                print 'EOF!'
                ending = True
                #return False
            #except IOError as e:
            #    if str(e) == "[Errno 11] Resource temporarily unavailable":
            #        pass
            #    else:
            #        raise e
        return False
    
    def changecolor(self,widget,state,strcolor):
        map = widget.get_colormap() 
        color = map.alloc_color(strcolor)
        style = widget.get_style().copy()
        style.bg[state] = color
        widget.set_style(style)
    
    def setmaxmin(self,basename,mesure,unit,timestamp):
        label = map(lambda sfx: getattr(self,'%s%sl' % (basename,sfx)), ['max','min'])
        value = map(lambda sfx: '%s%sv' % (basename,sfx), ['max','min'])
        for ind,cond in enumerate([lambda a,b: a > b,lambda a,b: a < b]):
            if getattr(self,value[ind]) is None or cond(mesure,getattr(self,value[ind])):
                setattr(self,value[ind],mesure)
                label[ind].set_text('<small>%s %s : %s %s at %s</small>' % (basename.capitalize(),
                                                             ['Max','Min'][ind],
                                                             getattr(self,value[ind]),
                                                             unit,
                                                             timestring(timestamp)))
                label[ind].set_property('use_markup',True)
    
    def windisplay(self,obj):
        #print(obj)
        #self.temptxt.set_text('%s %s %s' % (self.cpleth,obj['pleth'],float(obj['pleth'])/100))
        self.lsttimetxt.set_text('%s' % timestring(obj['timestamp']))
        if _experiments_:
            if self.lasttime == 0: self.lasttime = float(obj['timestamp'])
        if obj['nopulse']:
            self.fnopulse.set_property('active',True)
            self.signaltxt.set_text('?')
        else:
            self.fnopulse.set_property('active',False)
            self.signaltxt.set_text('%s' % obj['signal'])
        if obj['nofinger']:
            self.fnofinger.set_property('active',True)
        else:
            self.fnofinger.set_property('active',False)
        #self.beeper.set_text('')
        #self.changecolor(self.beeper,gtk.STATE_PRELIGHT,'grey')
        if obj['beep']:
            if _experiments_:
                if self.lastbeep == 0: self.lastbeep = float(obj['timestamp'])
                #self.beeper.set_text('beep')
                #self.changecolor(self.beeper,gtk.STATE_PRELIGHT,'white')
                nxtcase = (self.beep2beeppt + 1) % len(self.beep2beep)
                self.beep2beep[nxtcase] = float(obj['timestamp']) - self.lastbeep
                self.lastbeep = float(obj['timestamp'])
                self.lastbeeptobeep.set_text('%s ms' % self.beep2beep[nxtcase])
                self.beeper.set_text(str(round((1.0/self.beep2beep[nxtcase])*60,2))+'bpm')
                self.setmaxmin('beep2beep',self.beep2beep[nxtcase],'ms',obj['timestamp'])
                if nxtcase == 0:
                    self.beep2beepavgl.set_text(str(sum(self.beep2beep)/len(self.beep2beep))+'ms')
                self.beep2beeppt = nxtcase
        cpleth = self.cpleth.next()
        self.pleth[cpleth].set_property('fraction',float(obj['pleth'])/100)
        for i in range(0,4):
                self.changecolor(self.pleth[(cpleth+i)%len(self.pleth)],gtk.STATE_PRELIGHT,'yellow')
        if obj['beep']:
            self.changecolor(self.pleth[cpleth],gtk.STATE_PRELIGHT,'black')
            self.changecolor(self.pleth[cpleth],gtk.STATE_NORMAL,'white')
        else:
            self.changecolor(self.pleth[cpleth],gtk.STATE_NORMAL,'grey')
            pn = float(self.pleth[(cpleth-1)%len(self.pleth)].get_property('fraction'))
            df = float(obj['pleth'])/100-pn
            #if _experiments_:
                #if cpleth == 0:
                    #self.dfplwb = max(-255,self.localdfmin)
                    #self.dfpupb = min(255,self.localdfmax) 
                    #self.localdfmax = -255
                    #self.localdfmin = 255                
                #dftime = float(obj['timestamp'])-self.lasttime
                #dxdt = df/(dftime+1)
                #self.uppingtime.set_text('<small>%s %s %s</small>' % (self.dfplwb,self.dfpupb,dxdt))
                #if dxdt > self.localdfmax : self.localdfmax = dxdt
                #if dxdt < self.localdfmin : self.localdfmin = dxdt
                #self.uppingtime.set_property('use_markup',True)
                #self.d_dt_pleth[cpleth].set_property('fraction',rewindow(dxdt,min(self.dfplwb,dxdt,-0.5),max(self.dfpupb,dxdt,+0.6),0,1))
            if df > 0:
                self.changecolor(self.pleth[cpleth],gtk.STATE_PRELIGHT,'green')
            elif df < 0:
                self.changecolor(self.pleth[cpleth],gtk.STATE_PRELIGHT,'red')
            else:
                self.changecolor(self.pleth[cpleth],gtk.STATE_PRELIGHT,'blue')
            if _experiments_:
                if self.pwrstmark[0:2] == [False,False] and df > 0:
                    self.pwrstmark = [True,False,cpleth,float(obj['timestamp'])]
                    self.changecolor(self.pleth[cpleth],gtk.STATE_NORMAL,'orange')
                elif self.pwrstmark[0:2] == [True,False] and df < 0:
                    self.pwrstmark[1] = True
                elif self.pwrstmark[0:2] == [True,True] and df > 0:
                    self.changecolor(self.pleth[cpleth],gtk.STATE_NORMAL,'brown')
                    i = self.pwrstmark[2]
                    vs = []
                    lwb = 2.0
                    upb = -1.0
                    while i != cpleth:
                        vl = float(self.pleth[i].get_property('fraction'))
                        if vl > upb: upb = vl
                        if vl < lwb: lwb = vl
                        vs.append(float(self.pleth[i].get_property('fraction')))
                        i = (i+1) % len(self.pleth)                       
                    #vsf = (sum(map(lambda x: rewindow(x,lwb,upb,0,1)**2,vs))/len(vs))**0.5
                    vs0 = (sum(map(lambda x: (x-lwb)**2,vs))/len(vs))**0.5
                    vs = (sum(map(lambda x: x**2,vs))/len(vs))**0.5
                    timing = float(obj['timestamp'])-self.pwrstmark[3]
                    self.beatduration.set_text(str(timing)+"s")
                    self.beatrms.set_text(str(vs)+" rms")
                    self.beatrmsdeoffset.set_text(str(vs0)+ " rms0")
                    self.beatrmsovertime.set_text(str(vs0/timing)+" rms0/s")
                    self.pwrstmark = [False,False,cpleth,float(obj['timestamp'])]
        self.lastcpleth = cpleth
        csatp = self.lastcsatp
        if obj['satO2'] is None: 
            self.changecolor(self.satp[csatp],gtk.STATE_PRELIGHT,'red')
            self.satp[csatp].set_property('fraction',random.random())
            self.satl.set_text('saturation: N/A')
        else:
            csatp = self.csatp.next()
            self.setmaxmin('sat',obj['satO2'],'%',obj['timestamp'])
            self.changecolor(self.satp[csatp],gtk.STATE_PRELIGHT,'green')
            self.satp[csatp].set_property('fraction',(float(obj['satO2'])/100)**2)
            self.satl.set_text('saturation: %s %%' % obj['satO2'])
            self.lastcsatp = csatp
        cratep = self.lastcratep
        if obj['pulse'] is None:
            self.changecolor(self.ratep[cratep],gtk.STATE_PRELIGHT,'red')
            self.ratep[cratep].set_property('fraction',random.random())
            self.ratel.set_text('Pulse Rate: N/A')
        else:
            cratep = self.cratep.next()
            if obj['pulse'] > self.crateplocmax: self.crateplocmax = obj['pulse']
            if obj['pulse'] < self.crateplocmin: self.crateplocmin = obj['pulse']
            if cratep == 0:
                self.crateplwb = max(0,self.crateplocmin-15)
                self.cratepupb = min(255,self.crateplocmax+15) 
                self.crateplocmax = 0
                self.crateplocmin = 255
            self.setmaxmin('rate',obj['pulse'],'BPM',obj['timestamp'])
            if obj['beep']:
                self.changecolor(self.ratep[cratep],gtk.STATE_NORMAL,'white')
            else:
                self.changecolor(self.ratep[cratep],gtk.STATE_NORMAL,'grey')
            if obj['pulse'] > 100:
                self.changecolor(self.ratep[cratep],gtk.STATE_PRELIGHT,'red')
                self.ratel.set_text('Pulse Rate: %s BPM (!)' % obj['pulse'])
            elif obj['pulse'] < 50:
                self.changecolor(self.ratep[cratep],gtk.STATE_PRELIGHT,'red')
                self.ratel.set_text('Pulse Rate: %s BPM (!)' % obj['pulse'])
            else:
                self.changecolor(self.ratep[cratep],gtk.STATE_PRELIGHT,'green')
                self.ratel.set_text('Pulse Rate: %s BPM' % obj['pulse'])
            
            #print("%s %s" % (self.crateplwb,self.cratepupb))
            nx = rewindow(float(obj['pulse']),self.crateplwb,self.cratepupb,0,1)
            #fraction = 1.442695040451*math.log(nx+1)
            #fraction = 1.581976127237-1.58197593758*math.exp(-nx)
            fraction = 1.899014097714*math.log(math.log(nx+1)+1)
            #fraction = 1/(1+math.exp(-8.497409863662*(nx-0.5)))
            self.ratep[cratep].set_property('fraction',fraction)
            self.lastcratep = cratep
            if _experiments_:
                self.lasttime = float(obj['timestamp'])
    
    def on_mainframe_destroy(self, source=None, event=None):
        print('mainframe destruction asked')
        self.exitevent.set()
        gtk.main_quit()

if __name__ == "__main__":
    #http://stackoverflow.com/questions/30172428/python-non-block-read-file
    #flag = fcntl.fcntl(sys.stdin.fileno(), fcntl.F_GETFL)
    #fcntl.fcntl(sys.stdin.fileno(), fcntl.F_SETFL, flag | os.O_NONBLOCK)
    app = thisapp()
    gtk.main()



