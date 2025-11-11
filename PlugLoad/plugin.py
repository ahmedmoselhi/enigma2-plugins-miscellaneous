from os import path, system
from Plugins.Plugin import PluginDescriptor
from Components.PluginComponent import plugins
from Components.ServiceEventTracker import ServiceEventTracker, InfoBarBase
from enigma import iPlayableService, eServiceCenter, iServiceInformation
from Components.Label import Label
import ServiceReference
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from traceback import print_exc
from Tools.Import import my_import
from Screens.MessageBox import MessageBox
from threading import Thread
from enigma import *
from Components.Console import Console
import os, sys

doit = True
PlugLoadInstance = None

def woWebIf(session):
    try:
        from Plugins.Extensions.OpenWebif.httpserver import HttpdStart
        HttpdStart(session)
    except:
        print_exc()

class PlugLoadConfig(Screen):

    def __init__(self, session):
        try:
            Screen.__init__(self, session)
            self.session = session
            self['actions'] = ActionMap(['OkCancelActions', 'ColorActions'], {'green': (self.cancel),
               'red': (self.cancel),
               'cancel': (self.cancel),
               'ok': (self.keyOK)}, -1)
            self['text'] = Label(_('Press OK to reload the plugins manually!\nPress EXIT to cancel!'))
            skin = '<screen position="center,center" size="400,75" title="PlugLoad" >\n\t\t\t<widget name="text" position="0,0" zPosition="1" size="400,75" font="Regular;20" valign="center" halign="center" transparent="1" />\n\t\t\t</screen>'
            self.skin = skin
        except:
            print_exc()
            self.close(None)

    def cancel(self):
        self.close()

    def keyOK(self):
        try:
            system('/usr/bin/plugload.sh py')
            plugins.readPluginList('/usr/lib/enigma2/python/Plugins/')
            if os.path.exists('/usr/lib/enigma2/python/Plugins/Extensions/OpenWebif') is True:
                woWebIf(self.session)
            self.session.open(MessageBox, _('The plugins were reloaded successfully!'), MessageBox.TYPE_INFO, timeout=3)
            self.close()
        except:
            print_exc()


class PlugLoad1(Thread):

    def __init__(self, session):
        super().__init__()
        self.session = session

    def run(self):
        try:
            system('/usr/bin/plugload.sh py')
            plugins.readPluginList('/usr/lib/enigma2/python/Plugins/')
            if path.exists('/usr/lib/enigma2/python/Plugins/Extensions/OpenWebif') is True:
                woWebIf(self.session)
        except:
            print_exc()


class PlugLoad:

    def __init__(self, session):
        try:
            self.session = session
            self.service = None
            self.onClose = []
            self.__event_tracker = ServiceEventTracker(screen=self, eventmap={(iPlayableService.evUpdatedInfo): (self.__evUpdatedInfo)})
        except:
            print_exc()

    def __evUpdatedInfo(self):
        global doit
        try:
            if doit is True:
                doit = False
                service = self.session.nav.getCurrentService()
                if service is not None:
                    ret = PlugLoad1(self.session)
                    ret.start()
        except:
            print_exc()


def main(session, **kwargs):
    global PlugLoadInstance
    if PlugLoadInstance is None:
        PlugLoadInstance = PlugLoad(session)


def openconfig(session, **kwargs):
    session.open(PlugLoadConfig)


def Plugins(**kwargs):
    return [PluginDescriptor(where=[PluginDescriptor.WHERE_SESSIONSTART], fnc=main),
     PluginDescriptor(name=_('PlugLoad'), description=_('Load Plugins'), where=[
      PluginDescriptor.WHERE_PLUGINMENU], fnc=openconfig)]