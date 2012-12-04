#@+leo-ver=5-thin
#@+node:tbrown.20090119215428.2: * @file todo.py
#@+<< docstring >>
#@+node:tbrown.20090119215428.3: ** << docstring >> (todo.py)
''' Provides to-do list and simple task management.

This plugin adds time required, progress and priority settings for nodes. With
the @project tag a branch can display progress and time required with dynamic
hierarchical updates.

The Task Tab
============

The plugin creates a "Task" Tab in the log pane.  It looks like this:
    
    .. image:: ../Icons/cleo/LeoTaskTab.png
    
Along the top are icons that you can associate with nodes.
Just click on the icon: it will appear on the presently selected node.

Next are a set of fields that allow you to associate **due dates** and
**completion times** with nodes. The @setting @data todo_due_date_offsets lists
date offsets, +n -n days from now, or <n >n to subtract / add n days to existing
date.

Clicking on the Button named "Menu" reveals submenus.

For full details, see http://leo.zwiki.org/Tododoc

Icons
=====

The plugin uses icons in the leo/Icons/cleo folder. These icons are generated
from the file cleo_icons.svg in the same directory. You may replace the PNG
images with any others you wish.

'''


#@-<< docstring >>

#@@language python
#@@tabwidth -4

#@+<< imports >>
#@+node:tbrown.20090119215428.4: ** << imports >>
import leo.core.leoGlobals as g

import os
import re
import datetime

if g.app.gui.guiName() == "qt":

    from PyQt4 import QtCore, QtGui, uic
    Qt = QtCore.Qt
#@-<< imports >>
__version__ = "0.30"
#@+<< version history >>
#@+node:tbrown.20090119215428.5: ** << version history >>
#@@killcolor

#@+at Use and distribute under the same terms as leo itself.
# 
# 0.30 TNB
#   - fork from cleo.py to todo.py
#   - Qt interface in a tab
#@-<< version history >>

#@+others
#@+node:tbrown.20090119215428.6: ** init
def init():

    name = g.app.gui.guiName()
    if name != "qt":
        if name != 'nullGui':
            print('todo.py plugin not loading because gui is not Qt')
        return False

    g.registerHandler('after-create-leo-frame',onCreate)
    # can't use before-create-leo-frame because Qt dock's not ready
    g.plugin_signon(__name__)
    g.tree_popup_handlers.append(popup_entry)
    return True

#@+node:tbrown.20090119215428.7: ** onCreate
def onCreate (tag,key):

    c = key.get('c')

    todoController(c)
#@+node:tbrown.20090630144958.5318: ** popup_entry
def popup_entry(c,p,menu):
    c.cleo.addPopupMenu(c,p,menu)
#@+node:tbrown.20090119215428.8: ** class todoQtUI
if g.app.gui.guiName() == "qt":
    class cleoQtUI(QtGui.QWidget):
        #@+others
        #@+node:ekr.20111118104929.10204: *3* ctor
        def __init__(self, owner, logTab=True):

            self.owner = owner

            QtGui.QWidget.__init__(self)
            uiPath = g.os_path_join(g.app.leoDir, 'plugins', 'ToDo.ui')
            form_class, base_class = uic.loadUiType(uiPath)
            if logTab:
                self.owner.c.frame.log.createTab('Task', widget = self) 
            self.UI = form_class()
            self.UI.setupUi(self)

            u = self.UI
            o = self.owner

            self.menu = QtGui.QMenu()
            self.populateMenu(self.menu, o)

            u.butMenu.setMenu(self.menu)

            self.connect(u.butHelp, QtCore.SIGNAL("clicked()"), o.showHelp)

            self.connect(u.butClrProg, QtCore.SIGNAL("clicked()"),
                o.progress_clear)
            self.connect(u.butClrTime, QtCore.SIGNAL("clicked()"),
                o.clear_time_req)
            self.connect(u.butPriClr, QtCore.SIGNAL("clicked()"),
                o.priority_clear)

            # if live update is too slow change valueChanged(*) to editingFinished()
            self.connect(u.spinTime, QtCore.SIGNAL("valueChanged(double)"),
                lambda v: o.set_time_req(val=u.spinTime.value()))
            self.connect(u.spinProg, QtCore.SIGNAL("valueChanged(int)"),
                lambda v: o.set_progress(val=u.spinProg.value()))

            # can't work out SIGNAL() names
            u.dueDateEdit.dateChanged.connect(
                lambda v: o.set_due_date(val=u.dueDateEdit.date()))
            u.dueTimeEdit.timeChanged.connect(
                lambda v: o.set_due_time(val=u.dueTimeEdit.time()))

            u.dueDateToggle.stateChanged.connect(
                lambda v: o.set_due_date(val=u.dueDateEdit.date(), mode='check'))
            u.dueTimeToggle.stateChanged.connect(
                lambda v: o.set_due_time(val=u.dueTimeEdit.time(), mode='check'))
                
            # FIXME - move to ui design
            u.dueDateEdit.setEnabled(True)
            u.dueTimeEdit.setEnabled(True)

            for but in ["butPri1", "butPri6", "butPriChk", "butPri2",
                "butPri4", "butPri5", "butPri8", "butPri9", "butPri0",
                "butPriToDo", "butPriXgry", "butPriBang", "butPriX",
                "butPriQuery", "butPriBullet", "butPri7", 
                "butPri3"]:

                w = getattr(u, but)

                # w.property() seems to give QVariant in python 2.x and int in 3.x!?
                try:
                    pri = int(w.property('priority'))
                except (TypeError, ValueError):
                    try:
                        pri, ok = w.property('priority').toInt()
                    except (TypeError, ValueError):
                        pri = -1

                def setter(pri=pri): o.setPri(pri)
                self.connect(w, QtCore.SIGNAL("clicked()"), setter)

            offsets = self.owner.c.config.getData('todo_due_date_offsets')
            if not offsets:
                offsets = '+7 +0 +1 +2 +3 +4 +5 +6 +10 +14 +21 +28 +42 +60 +90 +120 +150 ' \
                          '>7 <7 <14 >14 <28 >28'.split()
            self.date_offset_default = int(offsets[0].strip('>').replace('<', '-'))
            offsets = sorted(set(offsets), key=lambda x: (x[0],int(x[1:].strip('>').replace('<', '-'))))
            u.dueDateOffset.addItems(offsets)
            u.dueDateOffset.setCurrentIndex(self.date_offset_default)
            self.connect(self.UI.dueDateOffset, QtCore.SIGNAL("activated(int)"),
                lambda v: o.set_due_date_offset())

            self.setDueDate = self.make_func(self.UI.dueDateEdit,
                self.UI.dueDateToggle, 'setDate',
                datetime.date.today() + datetime.timedelta(self.date_offset_default))
                 
            self.setDueTime = self.make_func(self.UI.dueTimeEdit,
                self.UI.dueTimeToggle, 'setTime',
                datetime.datetime.now().time())
        #@+node:ekr.20111118104929.10203: *3* make_func
        def make_func(self, edit, toggle, method, default):

            def func(value, edit=edit, toggle=toggle, 
                     method=method, default=default, self=self):
                         
                edit.blockSignals(True)
                toggle.blockSignals(True)
                
                if value:
                    getattr(edit, method)(value)
                    # edit.setEnabled(True)
                    toggle.setChecked(Qt.Checked)
                else:
                    getattr(edit, method)(default)
                    # edit.setEnabled(False)
                    toggle.setChecked(Qt.Unchecked)
                    
                edit.blockSignals(False)
                toggle.blockSignals(False)
                
            return func
                    
        #@+node:ekr.20111118104929.10205: *3* populateMenu
        @staticmethod
        def populateMenu(menu,o): 
            menu.addAction('Find next ToDo', o.find_todo)
            m = menu.addMenu("Priority")
            m.addAction('Priority Sort', o.priSort)
            m.addAction('Due Date Sort', o.dueSort)
            m.addAction('Mark children todo', o.childrenTodo)
            m.addAction('Show distribution', o.showDist)
            m.addAction('Redistribute', o.reclassify)
            m = menu.addMenu("Time")
            m.addAction('Show times', lambda:o.show_times(show=True))
            m.addAction('Hide times', lambda:o.show_times(show=False))
            m.addAction('Re-calc. derived times', o.local_recalc)
            m.addAction('Clear derived times', o.local_clear)
            m = menu.addMenu("Misc.")
            m.addAction('Hide all Todo icons', lambda:o.loadAllIcons(clear=True))
            m.addAction('Show all Todo icons', o.loadAllIcons)
            m.addAction('Delete Todo from node', o.clear_all)
            m.addAction('Delete Todo from subtree', lambda:o.clear_all(recurse=True))
            m.addAction('Delete Todo from all', lambda:o.clear_all(all=True))
        #@+node:ekr.20111118104929.10209: *3* setDueDate
        #X def setDueDate(self, date_):
        #X     self.UI.dueDateEdit.blockSignals(True)
        #X     self.UI.dueDateToggle.blockSignals(True)
        #X     if date_:
        #X         self.UI.dueDateEdit.setDate(date_)
        #X         self.UI.dueDateEdit.setEnabled(True)
        #X         self.UI.dueDateToggle.setChecked(Qt.Checked)
        #X     else:
        #X         self.UI.dueDateEdit.setDate(datetime.date.today() + 
        #X             datetime.timedelta(7))
        #X         self.UI.dueDateEdit.setEnabled(False)
        #X         self.UI.dueDateToggle.setChecked(Qt.Unchecked)
        #X     self.UI.dueDateEdit.blockSignals(False)
        #X     self.UI.dueDateToggle.blockSignals(False)

        #X    def setDueTime(self, time_):
        #X     self.UI.dueTimeEdit.blockSignals(True)
        #X     self.UI.dueTimeToggle.blockSignals(True)
        #X     if time_:
        #X         self.UI.dueTimeEdit.setTime(time_)
        #X         self.UI.dueTimeToggle.setChecked(Qt.Checked)
        #X     else:
        #X         self.UI.dueTimeEdit.setTime(datetime.datetime.now().time())
        #X         self.UI.dueTimeToggle.setChecked(Qt.Unchecked)
        #X     self.UI.dueTimeEdit.blockSignals(False)
        #X     self.UI.dueTimeToggle.blockSignals(False)
        #@+node:ekr.20111118104929.10207: *3* setProgress
        def setProgress(self, prgr):
            self.UI.spinProg.blockSignals(True)
            self.UI.spinProg.setValue(prgr)
            self.UI.spinProg.blockSignals(False)
        #@+node:ekr.20111118104929.10208: *3* setTime
        def setTime(self, timeReq):
            self.UI.spinTime.blockSignals(True)
            self.UI.spinTime.setValue(timeReq)
            self.UI.spinTime.blockSignals(False)
        #@-others
#@+node:tbrown.20090119215428.9: ** class todoController
class todoController:

    '''A per-commander class that manages tasks.'''

    #@+others
    #@+node:tbrown.20090119215428.10: *3* priority table
    priorities = {
      1: {'long': 'Urgent',    'short': '1', 'icon': 'pri1.png'},
      2: {'long': 'Very High', 'short': '2', 'icon': 'pri2.png'},
      3: {'long': 'High',      'short': '3', 'icon': 'pri3.png'},
      4: {'long': 'Medium',    'short': '4', 'icon': 'pri4.png'},
      5: {'long': 'Low',       'short': '5', 'icon': 'pri5.png'},
      6: {'long': 'Very Low',  'short': '6', 'icon': 'pri6.png'},
      7: {'long': 'Sometime',  'short': '7', 'icon': 'pri7.png'},
      8: {'long': 'Level 8',   'short': '8', 'icon': 'pri8.png'},
      9: {'long': 'Level 9',   'short': '9', 'icon': 'pri9.png'},
     10: {'long': 'Level 0',   'short': '0', 'icon': 'pri0.png'},
     19: {'long': 'To do',     'short': 'o', 'icon': 'chkboxblk.png'},
     20: {'long': 'Bang',      'short': '!', 'icon': 'bngblk.png'},
     21: {'long': 'Cross',     'short': 'X', 'icon': 'xblk.png'},
     22: {'long': '(cross)',   'short': 'x', 'icon': 'xgry.png'},
     23: {'long': 'Query',     'short': '?', 'icon': 'qryblk.png'},
     24: {'long': 'Bullet',    'short': '-', 'icon': 'bullet.png'},
    100: {'long': 'Done',      'short': 'D', 'icon': 'chkblk.png'},
    }

    todo_priorities = 1,2,3,4,5,6,7,8,9,10,19
    #@+node:tbrown.20090119215428.11: *3* __init__
    def __init__ (self,c):

        self.c = c
        c.cleo = self
        self.donePriority = 100
        self.menuicons = {}  # menu icon cache
        self.recentIcons = []
        #X self.smiley = None
        self.redrawLevels = 0

        #@+<< set / read default values >>
        #@+node:tbrown.20090119215428.12: *4* << set / read default values >>
        self.time_name = 'days'
        if c.config.getString('todo_time_name'):
            self.time_name = c.config.getString('todo_time_name')

        self.icon_location = 'beforeHeadline'
        if c.config.getString('todo_icon_location'):
            self.icon_location = c.config.getString('todo_icon_location')

        self.prog_location = 'beforeHeadline'
        if c.config.getString('todo_prog_location'):
            self.prog_location = c.config.getString('todo_prog_location')

        self.icon_order = 'pri-first'
        if c.config.getString('todo_icon_order'):
            self.icon_order = c.config.getString('todo_icon_order')
        #@-<< set / read default values >>

        self.handlers = [
           ("close-frame",self.close),
           ('select3', self.updateUI),
           ('save2', self.loadAllIcons),
        ]

        # chdir so the Icons can be located
        owd = os.getcwd()
        os.chdir(os.path.split(__file__)[0])
        self.ui = cleoQtUI(self)
        os.chdir(owd)

        for i in self.handlers:
            g.registerHandler(i[0], i[1])

        self.loadAllIcons()
    #@+node:tbrown.20090522142657.7894: *3* __del__
    def __del__(self):
        for i in self.handlers:
            g.unregisterHandler(i[0], i[1])
    #@+node:tbrown.20090630144958.5319: *3* addPopupMenu
    def addPopupMenu(self,c,p,menu):

        def rnd(x): return re.sub('.0$', '', '%.1f' % x)

        taskmenu = menu.addMenu("Task")

        submenu = taskmenu.addMenu("Status")

        iconlist = [(menu, i) for i in self.recentIcons]
        iconlist.extend([(submenu, i) for i in self.priorities])

        for m,i in iconlist:
            icon = self.menuicon(i)
            a = m.addAction(icon, self.priorities[i]["long"])
            a.setIconVisibleInMenu(True)
            def func(pri=i):
                self.setPri(pri)
            a.connect(a, QtCore.SIGNAL("triggered()"), func)

        submenu = taskmenu.addMenu("Progress")
        for i in range(11):
            icon = self.menuicon(10*i, progress=True)
            a = submenu.addAction(icon, "%d%%" % (i*10))
            a.setIconVisibleInMenu(True)
            def func(prog=i):
                self.set_progress(val=10*prog)
            a.connect(a, QtCore.SIGNAL("triggered()"), func)

        prog = self.getat(p.v, 'progress')
        if isinstance(prog,int):
            a = taskmenu.addAction("(%d%% complete)"%prog)
            a.setIconVisibleInMenu(True)
            a.enabled = False

        time_ = self.getat(p.v, 'time_req')
        if isinstance(time_,float):
            if isinstance(prog,int):
                f = prog/100.
                a = taskmenu.addAction("(%s+%s=%s %s)"%(rnd(f*time_),
                    rnd((1.-f)*time_),rnd(time_), self.time_name))
            else:
                a = taskmenu.addAction("(%s %s)"%(rnd(time_), self.time_name))
            a.enabled = False


        cleoQtUI.populateMenu(taskmenu, self)
    #@+node:tbrown.20090630144958.5320: *3* menuicon
    def menuicon(self, pri, progress=False):
        """return icon from cache, placing it there if needed"""

        if progress:
            prog = pri
            pri = 'prog-%d'%pri

        if pri not in self.menuicons:

            if progress:
                fn = 'prg%03d.png' % prog
            else:
                fn = self.priorities[pri]["icon"]

            iconDir = g.os_path_abspath(
              g.os_path_normpath(
                g.os_path_join(g.app.loadDir,"..","Icons")))

            fn = g.os_path_join(iconDir,'cleo',fn)

            self.menuicons[pri] = QtGui.QIcon(fn)

        return self.menuicons[pri]
    #@+node:tbrown.20090119215428.13: *3* redrawer
    def redrawer(fn):
        """decorator for methods which create the need for a redraw"""
        def new(self, *args, **kargs):
            self.redrawLevels += 1
            try:
                ans = fn(self,*args, **kargs)
            finally:
                self.redrawLevels -= 1

                if self.redrawLevels == 0:
                    self.redraw()

            return ans
        return new
    #@+node:tbrown.20090119215428.14: *3* projectChanger
    def projectChanger(fn):
        """decorator for methods which change projects"""
        def new(self, *args, **kargs):
            ans = fn(self,*args, **kargs)
            self.update_project()
            return ans
        return new
    #@+node:tbrown.20090119215428.15: *3* loadAllIcons
    @redrawer
    def loadAllIcons(self, tag=None, k=None, clear=None):
        """Load icons to represent cleo state"""

        for p in self.c.all_positions():
            self.loadIcons(p, clear=clear)
    #@+node:tbrown.20090119215428.16: *3* loadIcons
    @redrawer
    def loadIcons(self, p, clear=False):

        com = self.c.editCommands
        allIcons = com.getIconList(p)
        icons = [i for i in allIcons if 'cleoIcon' not in i]

        if clear:
            iterations = []
        else:
            iterations = [True, False]

        for which in iterations:

            if which == (self.icon_order == 'pri-first'):
                pri = self.getat(p.v, 'priority')
                if pri: pri = int(pri)
                if pri in self.priorities:
                    iconDir = g.os_path_abspath(
                      g.os_path_normpath(
                        g.os_path_join(g.app.loadDir,"..","Icons")))
                    com.appendImageDictToList(icons, iconDir,
                        g.os_path_join('cleo',self.priorities[pri]['icon']),
                        2, on='vnode', cleoIcon='1', where=self.icon_location)
                        # Icon location defaults to 'beforeIcon' unless cleo_icon_location global defined.
                        # Example: @strings[beforeIcon,beforeHeadline] cleo_icon_location = beforeHeadline
                    com.setIconList(p, icons)
            else:

                prog = self.getat(p.v, 'progress')
                if prog is not '':
                    prog = int(prog)
                    use = prog//10*10
                    use = 'prg%03d.png' % use

                    iconDir = g.os_path_abspath(
                      g.os_path_normpath(
                        g.os_path_join(g.app.loadDir,"..","Icons")))

                    com.appendImageDictToList(icons, iconDir,
                        g.os_path_join('cleo',use),
                        2, on='vnode', cleoIcon='1', where=self.prog_location)
                    com.setIconList(p, icons)

        if len(allIcons) != len(icons):  # something to add / remove
            com.setIconList(p, icons)

    #@+node:tbrown.20090119215428.17: *3* close
    def close(self, tag, key):
        "unregister handlers on closing commander"

        if self.c != key['c']: return  # not our problem

        for i in self.handlers:
            g.unregisterHandler(i[0], i[1])
    #@+node:tbrown.20090119215428.18: *3* showHelp
    def showHelp(self):
        g.es('Check the Plugins menu Todo entry')
    #@+node:tbrown.20090119215428.19: *3* attributes...
    #@+at
    # annotate was the previous name of this plugin, which is why the default values
    # for several keyword args is 'annotate'.
    #@+node:tbrown.20090119215428.20: *4* delUD
    def delUD (self,node,udict="annotate"):

        ''' Remove our dict from the node'''

        if (hasattr(node,"unknownAttributes" )
            and udict in node.unknownAttributes):

            del node.unknownAttributes[udict]
    #@+node:tbrown.20090119215428.21: *4* hasUD
    def hasUD (self,node,udict="annotate"):

        ''' Return True if the node has an UD.'''

        return (
            hasattr(node,"unknownAttributes") and
            udict in node.unknownAttributes and
            type(node.unknownAttributes.get(udict)) == type({}) # EKR
        )
    #@+node:tbrown.20090119215428.22: *4* getat
    def getat(self, node, attrib):
        "new attrbiute getter"

        if (not hasattr(node,'unknownAttributes') or
            "annotate" not in node.unknownAttributes or
            not type(node.unknownAttributes["annotate"]) == type({}) or
            attrib not in node.unknownAttributes["annotate"]):

            if attrib == "priority":
                return 9999
            else:
                return ""

        x = node.unknownAttributes["annotate"][attrib]
        return x
    #@+node:tbrown.20090119215428.23: *4* testDefault
    def testDefault(self, attrib, val):
        "return true if val is default val for attrib"

        return attrib == "priority" and val == 9999 or val == ""
    #@+node:tbrown.20090119215428.24: *4* setat
    def setat(self, node, attrib, val):
        "new attrbiute setter"

        if 'annotate' in node.u and 'src_unl' in node.u['annotate']:
            if not hasattr(node, '_cached_src_vnode'):
                src_unl = node.u['annotate']['src_unl']
                c1 = self.c
                p1 = c1.vnode2position(node)
                c2, p2 = self.unl_to_pos(src_unl, p1)
                node._cached_src_c = c2
                node._cached_src_vnode = p2.v
            node._cached_src_c.cleo.setat(node._cached_src_vnode, attrib, val)
            node._cached_src_c.cleo.updateUI(k={'c': node._cached_src_c})
            node._cached_src_c.setChanged(True)

        isDefault = self.testDefault(attrib, val)

        if (not hasattr(node,'unknownAttributes') or
            "annotate" not in node.unknownAttributes or
            type(node.unknownAttributes["annotate"]) != type({})):
            # dictionary doesn't exist

            if isDefault:
                return  # don't create dict. for default value

            if not hasattr(node,'unknownAttributes'):  # node has no unknownAttributes
                node.unknownAttributes = {}
                node.unknownAttributes["annotate"] = {}
            else:  # our private dictionary isn't present
                if ("annotate" not in node.unknownAttributes or
                    type(node.unknownAttributes["annotate"]) != type({})):
                    node.unknownAttributes["annotate"] = {}
                    
            node.unknownAttributes["annotate"]['created'] = datetime.datetime.now()

            node.unknownAttributes["annotate"][attrib] = val

            return

        # dictionary exists


        if (attrib not in node.unknownAttributes["annotate"] or
            node.unknownAttributes["annotate"][attrib] != val):
            self.c.setChanged(True)

        node.unknownAttributes["annotate"][attrib] = val

        if isDefault:  # check if all default, if so drop dict.
            self.dropEmpty(node, dictOk = True)
    #@+node:tbrown.20090119215428.25: *4* dropEmpty
    def dropEmpty(self, node, dictOk = False):

        if (dictOk or
            hasattr(node,'unknownAttributes') and
            "annotate" in node.unknownAttributes and
            type(node.unknownAttributes["annotate"]) == type({})):

            isDefault = True
            for ky, vl in node.unknownAttributes["annotate"].items():

                if not self.testDefault(ky, vl):
                    isDefault = False
                    break

            if isDefault:  # no non-defaults seen, drop the whole cleo dictionary
                del node.unknownAttributes["annotate"]
                self.c.setChanged(True)
                return True

        return False
    #@+node:tbrown.20090119215428.26: *4* safe_del
    def safe_del(self, d, k):
        "delete a key from a dict. if present"
        if k in d: del d[k]
    #@+node:tbrown.20090119215428.27: *3* drawing...
    #@+node:tbrown.20090119215428.28: *4* redraw
    def redraw(self):

        self.updateUI()
        self.c.redraw_now()
    #@+node:tbrown.20090119215428.29: *4* clear_all
    @redrawer
    def clear_all(self, recurse=False, all=False):

        if all:
            what = self.c.all_positions()
        elif recurse:
            what = self.c.currentPosition().self_and_subtree()
        else:
            what = iter([self.c.currentPosition()])

        for p in what:
            self.delUD(p.v)
            self.loadIcons(p)
            self.show_times(p)

    #@+node:tbrown.20090119215428.30: *3* Progress/time/project...
    #@+node:tbrown.20090119215428.31: *4* progress_clear
    @redrawer
    @projectChanger
    def progress_clear(self,v=None):

        self.setat(self.c.currentPosition().v, 'progress', '')
    #@+node:tbrown.20090119215428.32: *4* set_progress
    @redrawer
    @projectChanger
    def set_progress(self,p=None, val=None):
        if p is None:
            p = self.c.currentPosition()
        v = p.v

        if val == None: return

        self.setat(v, 'progress', val)
    #@+node:tbrown.20090119215428.33: *4* set_time_req
    @redrawer
    @projectChanger
    def set_time_req(self,p=None, val=None):
        if p is None:
            p = self.c.currentPosition()
        v = p.v

        if val == None: return

        self.setat(v, 'time_req', val)

        if self.getat(v, 'progress') == '':
            self.setat(v, 'progress', 0)
    #@+node:tbrown.20090119215428.34: *4* show_times
    @redrawer
    def show_times(self, p=None, show=False):

        def rnd(x): return re.sub('.0$', '', '%.1f' % x)

        if p is None:
            p = self.c.currentPosition()

        for nd in p.self_and_subtree():
            self.c.setHeadString(nd, re.sub(' <[^>]*>$', '', nd.headString()))

            tr = self.getat(nd.v, 'time_req')
            pr = self.getat(nd.v, 'progress')
            try: pr = float(pr)
            except: pr = ''
            if tr != '' or pr != '':
                ans = ' <'
                if tr != '':
                    if pr == '' or pr == 0 or pr == 100:
                        ans += rnd(tr) + ' ' + self.time_name
                    else:
                        ans += '%s+%s=%s %s' % (rnd(pr/100.*tr), rnd((1-pr/100.)*tr), rnd(tr), self.time_name)
                    if pr != '': ans += ', '
                if pr != '':
                    ans += rnd(pr) + '%'  # pr may be non-integer if set by recalc_time
                ans += '>'

                if show:
                    self.c.setHeadString(nd, nd.headString()+ans)
                self.loadIcons(nd)  # update progress icon

    #@+node:tbrown.20090119215428.35: *4* recalc_time
    def recalc_time(self, p=None, clear=False):

        if p is None:
            p = self.c.currentPosition()

        v = p.v
        time_totl = None
        time_done = None

        # get values from children, if any
        for cn in p.children():
            ans = self.recalc_time(cn.copy(), clear)
            if time_totl == None:
                time_totl = ans[0]
            else:
                if ans[0] != None: time_totl += ans[0]

            if time_done == None:
                time_done = ans[1]
            else:
                if ans[1] != None: time_done += ans[1]

        if time_totl != None:  # some value returned

            if clear:  # then we should just clear our values
                self.setat(v, 'progress', '')
                self.setat(v, 'time_req', '')
                return (time_totl, time_done)

            if time_done != None:  # some work done
                # can't round derived progress without getting bad results form show_times
                if time_totl == 0:
                    pr = 0.
                else:
                    pr = float(time_done) / float(time_totl) * 100.
                self.setat(v, 'progress', pr)
            else:
                self.setat(v, 'progress', 0)
            self.setat(v, 'time_req', time_totl)
        else:  # no values from children, use own
            tr = self.getat(v, 'time_req')
            pr = self.getat(v, 'progress')
            if tr != '':
                time_totl = tr
                if pr != '':
                    time_done = float(pr) / 100. * tr
                else:
                    self.setat(v, 'progress', 0)

        return (time_totl, time_done)
    #@+node:tbrown.20090119215428.36: *4* clear_time_req
    @redrawer
    @projectChanger
    def clear_time_req(self, p=None):

        if p is None:
            p = self.c.currentPosition()
        v = p.v
        self.setat(v, 'time_req', '')
    #@+node:tbrown.20090119215428.37: *4* update_project
    @redrawer
    def update_project(self, p=None):
        """Find highest parent with '@project' in headline and run recalc_time
        and maybe show_times (if headline has '@project time')"""

        if p is None:
            p = self.c.currentPosition()
        project = None

        for nd in p.self_and_parents():
            if nd.headString().find('@project') > -1:
                project = nd.copy()

        if project:
            self.recalc_time(project)
            if project.headString().find('@project time') > -1:
                self.show_times(project, show=True)
            else:
                self.show_times(p, show=True)
        else:
            self.show_times(p, show=False)
    #@+node:tbrown.20090119215428.38: *4* local_recalc
    @redrawer
    def local_recalc(self, p=None):
        self.recalc_time(p)
    #@+node:tbrown.20090119215428.39: *4* local_clear
    @redrawer
    def local_clear(self, p=None):
        self.recalc_time(p, clear=True)
    #@+node:tbrown.20110213091328.16233: *4* set_due_date
    def set_due_date(self,p=None, val=None, mode='adjust'):
        "mode: `adjust` for change in time, `check` for checkbox toggle"
        if p is None:
            p = self.c.currentPosition()
        v = p.v
        
        if mode == 'check':
            if self.ui.UI.dueDateToggle.checkState() == Qt.Unchecked:
                self.setat(v, 'duedate', "")
            else:
                self.setat(v, 'duedate', val.toPyDate())
        else:
            self.ui.UI.dueDateToggle.setCheckState(Qt.Checked)
            self.setat(v, 'duedate', val.toPyDate())

        self.updateUI()  # if change was made to date with offset selector
    #@+node:tbrown.20110213091328.16235: *4* set_due_time
    def set_due_time(self,p=None, val=None, mode='adjust'):
        "mode: `adjust` for change in time, `check` for checkbox toggle"
        if p is None:
            p = self.c.currentPosition()
        v = p.v

        if mode == 'check':
            if self.ui.UI.dueTimeToggle.checkState() == Qt.Unchecked:
                self.setat(v, 'duetime', "")
            else:
                self.setat(v, 'duetime', val.toPyTime())
        else:
            self.ui.UI.dueTimeToggle.setCheckState(Qt.Checked)
            self.setat(v, 'duetime', val.toPyTime())
    #@+node:tbrown.20121204084515.60965: *4* set_due_date_offset
    def set_due_date_offset(self):
        """set_due_date_offset - update date by selected offset

        offset sytax::
            
            +5 five days after today
            -5 five days before today
            >5 move current date 5 days later
            <5 move current date 5 days earlier

        """

        offset = str(self.ui.UI.dueDateOffset.currentText())
        
        mult = 1  # to handle '<' as a negative relative offset

        date = QtCore.QDate.currentDate()

        if '<' in offset or '>' in offset:
            date = self.ui.UI.dueDateEdit.date()
        
        if offset.startswith('<'):
            mult = -1
        
        self.set_due_date(val=date.addDays(mult*int(offset.strip('<>'))))
    #@+node:tbrown.20090119215428.40: *3* ToDo icon related...
    #@+node:tbrown.20090119215428.41: *4* childrenTodo
    @redrawer
    def childrenTodo(self, p=None):
        if p is None:
            p = self.c.currentPosition()
        for p in p.children():
            if self.getat(p.v, 'priority') != 9999: continue
            self.setat(p.v, 'priority', 19)
            self.loadIcons(p)
    #@+node:tbrown.20090119215428.42: *4* find_todo
    @redrawer
    def find_todo(self, p=None, stage = 0):
        """Recursively find the next todo"""

        # search is like XPath 'following' axis, all nodes after p in document order.
        # returning True should always propogate all the way back up to the top
        # stages: 0 - user selected start node, 1 - searching siblings, parents siblings, 2 - searching children

        if p is None:
            p = self.c.currentPosition()

        # see if this node is a todo
        if stage != 0 and self.getat(p.v, 'priority') in self.todo_priorities:
            if p.getParent(): 
                self.c.selectPosition(p.getParent())
                self.c.expandNode()
            self.c.selectPosition(p)
            return True

        for nd in p.children():
            if self.find_todo(nd, stage = 2): return True

        if stage < 2 and p.getNext():
            if self.find_todo(p.getNext(), stage = 1): return True

        if stage < 2 and p.getParent() and p.getParent().getNext():
            if self.find_todo(p.getParent().getNext(), stage = 1): return True

        if stage == 0: g.es("None found")

        return False
    #@+node:tbrown.20090119215428.43: *4* prikey
    def prikey(self, v):
        """key function for sorting by priority"""
        # getat returns 9999 for nodes without priority, so you'll only get -1
        # if a[1] is not a node.  Or even an object.

        try:
            pa = int(self.getat(v, 'priority'))
        except ValueError:
            pa = -1

        return pa
    #@+node:tbrown.20110213153425.16373: *4* duekey
    def duekey(self, v):
        """key function for sorting by due date/time"""

        date_ = self.getat(v, 'duedate') or datetime.date(3000,1,1)
        time_ = self.getat(v, 'duetime') or datetime.time(23, 59, 59)
            
        return date_, time_
    #@+node:tbrown.20110213153425.16377: *4* dueSort
    @redrawer
    def dueSort(self, p=None):
        if p is None:
            p = self.c.currentPosition()
        self.c.selectPosition(p)
        self.c.sortSiblings(key=self.duekey)
    #@+node:tbrown.20090119215428.44: *4* priority_clear
    @redrawer
    def priority_clear(self,v=None):

        if v is None:
            v = self.c.currentPosition().v
        self.setat(v, 'priority', 9999)
        self.loadIcons(self.c.currentPosition())
    #@+node:tbrown.20090119215428.45: *4* priSort
    @redrawer
    def priSort(self, p=None):
        if p is None:
            p = self.c.currentPosition()
        self.c.selectPosition(p)
        self.c.sortSiblings(key=self.prikey)
    #@+node:tbrown.20090119215428.46: *4* reclassify
    @redrawer
    def reclassify(self, p=None):
        """change priority codes"""

        if p is None:
            p = self.c.currentPosition()
        g.es('\n Current distribution:')
        self.showDist()
        dat = {}
        for end in 'from', 'to':
            if Qt:
                x0,ok = QtGui.QInputDialog.getText(None, 'Reclassify priority' ,'%s priorities (1-9,19)'%end)
                if not ok:
                    x0 = None
                else:
                    x0 = str(x0)
            else:
                x0 = g.app.gui.runAskOkCancelStringDialog(
                    self.c,'Reclassify priority' ,'%s priorities (1-7,19)' % end.upper())
            try:
                while re.search(r'\d+-\d+', x0):
                    what = re.search(r'\d+-\d+', x0).group(0)
                    rng = [int(n) for n in what.split('-')]
                    repl = []
                    if rng[0] > rng[1]:
                        for n in range(rng[0], rng[1]-1, -1):
                            repl.append(str(n))
                    else:
                        for n in range(rng[0], rng[1]+1):
                            repl.append(str(n))
                    x0 = x0.replace(what, ','.join(repl))

                x0 = [int(i) for i in x0.replace(',',' ').split()]
                      # if int(i) in self.todo_priorities]
            except:
                g.es('Not understood, no action')
                return
            if not x0:
                g.es('No action')
                return
            dat[end] = x0

        if len(dat['from']) != len(dat['to']):
            g.es('Unequal list lengths, no action')
            return

        cnt = 0
        for p in p.subtree():
            pri = int(self.getat(p.v, 'priority'))
            if pri in dat['from']:
                self.setat(p.v, 'priority', dat['to'][dat['from'].index(pri)])
                self.loadIcons(p)
                cnt += 1
        g.es('\n%d priorities reclassified, new distribution:' % cnt)
        self.showDist()
    #@+node:tbrown.20090119215428.47: *4* setPri
    @redrawer
    def setPri(self,pri):

        if pri in self.recentIcons:
            self.recentIcons.remove(pri)
        self.recentIcons.insert(0, pri)
        self.recentIcons = self.recentIcons[:3]

        p = self.c.currentPosition()
        self.setat(p.v, 'priority', pri)
        self.loadIcons(p)
    #@+node:tbrown.20090119215428.48: *4* showDist
    def showDist(self, p=None):
        """show distribution of priority levels in subtree"""
        if p is None:
            p = self.c.currentPosition()
        pris = {}
        for p in p.subtree():
            pri = int(self.getat(p.v, 'priority'))
            if pri not in pris:
                pris[pri] = 1
            else:
                pris[pri] += 1
        pris = sorted([(k,v) for k,v in pris.items()]) 
        for pri in pris:
            if pri[0] in self.priorities:
                g.es('%s\t%d\t%s\t(%s)' % (self.priorities[pri[0]]['short'], pri[1],
                    self.priorities[pri[0]]['long'],pri[0]))
    #@+node:tbrown.20090119215428.49: *3* updateUI
    def updateUI(self,tag=None,k=None):

        if k and k['c'] != self.c:
            return  # wrong number

        v = self.c.currentPosition().v
        self.ui.setProgress(int(self.getat(v, 'progress') or 0 ))
        self.ui.setTime(float(self.getat(v, 'time_req') or 0 ))
        
        self.ui.setDueDate(self.getat(v, 'duedate'))
        # default is "", which is understood by setDueDate()
        self.ui.setDueTime(self.getat(v, 'duetime'))
        # ditto

        created = self.getat(v, 'created')
        if created:
            self.ui.UI.createdTxt.setText(created.strftime("%d %b %y"))
            self.ui.UI.createdTxt.setToolTip(created.strftime("Created %H:%M %d %b %Y"))
        else:
            try:
                gdate = self.c.p.v.gnx.split('.')[1][:12]
                created = datetime.datetime.strptime(gdate, '%Y%m%d%H%M')
            except Exception:
                created = None
            if created:
                self.ui.UI.createdTxt.setText(created.strftime("%d %b %y?"))
                self.ui.UI.createdTxt.setToolTip(created.strftime("gnx created %H:%M %d %b %Y"))
            else:
                self.ui.UI.createdTxt.setText("")

            
    #@+node:tbrown.20121129095833.39490: *3* unl_to_pos
    def unl_to_pos(self, unl, for_p):
        """"unl may be an outline (like c) or an UNL (string)
        
        return c, p where c is an outline and p is a node to copy data to
        in that outline
        
        for_p is the p to be copied - needed to check for invalid recursive
        copy / move
        """

        # COPIED FROM quickMove.py

        # unl is an UNL indicating where to insert
        full_path = unl
        path, unl = full_path.split('#')
        c2 = g.openWithFileName(path, old_c=self.c)
        self.c.bringToFront(c2=self.c)
        found, maxdepth, maxp = g.recursiveUNLFind(unl.split('-->'), c2)
        
        if found:
            
            if (for_p == maxp or for_p.isAncestorOf(maxp)):
                g.es("Invalid move")
                return None, None
            
            nd = maxp
        else:
            g.es("Could not find '%s'"%full_path)
            self.c.bringToFront(c2=self.c)
            return None, None

        return c2, nd
    #@-others
#@+node:tbrown.20100701093750.13800: ** command inc/dec priority
@g.command('todo-dec-pri')
def todo_dec_pri(event, direction=1):

    c = event['c']
    p = c.p
    pri = int(c.cleo.getat(p.v, 'priority'))

    if pri not in c.cleo.priorities:
        pri = 1
    else:
        ordered = sorted(c.cleo.priorities.keys())
        pri = ordered[(ordered.index(pri) + direction) % len(ordered)]

    pri = c.cleo.setPri(pri)

    c.redraw()

    # c.executeMinibufferCommand("todo-inc-pri")

@g.command('todo-inc-pri')
def todo_inc_pri(event):
    todo_dec_pri(event, direction=-1)
#@-others
#@-leo
