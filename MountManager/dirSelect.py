# -*- coding: utf-8 -*-

from . import _
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Pixmap import Pixmap
from Components.Label import Label
from Components.Button import Button
from Components.FileList import FileList


class dirSelectDlg(Screen):
    # No change needed in the skin definition
    skin = """
            <screen name="dirSelectDlg" position="center,center" size="560,360">
                  <widget name="filelist" position="10,10" size="540,210" scrollbarMode="showOnDemand" />
                  <widget name="ButtonGreentext" position="70,270" size="460,25" halign="left" zPosition="10" font="Regular;21" transparent="1" />
                  <widget name="ButtonGreen" pixmap="skin_default/buttons/button_green.png" position="30,270" zPosition="10" size="35,25" transparent="1" alphatest="on" />
                  <widget name="ButtonRedtext" position="70,300" size="460,25" halign="left" zPosition="10" font="Regular;21" transparent="1" />
                  <widget name="ButtonRed" pixmap="skin_default/buttons/button_red.png" position="30,300" zPosition="10" size="35,25" transparent="1" alphatest="on" />
                  <widget name="ButtonOKtext" position="70,330" size="460,25" halign="left" zPosition="10" font="Regular;21" transparent="1" />
                  <widget name="ButtonOK" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/MountManager/icons/ok.png" position="30,330" zPosition="10" size="35,25" transparent="1" alphatest="on" />
            </screen>"""

    def __init__(self, session, currDir, showFilesBoolean):
        self.skin = dirSelectDlg.skin
        Screen.__init__(self, session)
        self.session = session
        self.showFilesBoolean = showFilesBoolean

        self["ButtonGreen"] = Pixmap()
        self["ButtonGreentext"] = Button()
        self["ButtonRed"] = Pixmap()
        self["ButtonRedtext"] = Label(_("Close"))
        self["ButtonOK"] = Pixmap()
        self["ButtonOKtext"] = Label(_("Enter directory"))
        # showMountpoints=True is kept as it's part of the original logic
        self["filelist"] = FileList(
            currDir,
            showDirectories=True,
            showFiles=showFilesBoolean,
            showMountpoints=True,
            useServiceRef=False)

        self["actions"] = ActionMap(["WizardActions",
                                     "DirectionActions",
                                     "ColorActions"],
                                    {"ok": self.ok,
                                     "back": self.cancel,
                                     "left": self.left,
                                     "right": self.right,
                                     "up": self.up,
                                     "down": self.down,
                                     "green": self.green,
                                     "red": self.red},
                                    -1)

        self.onLayoutFinish.append(self.setStartDir)
        # Initialize epath to prevent potential UnboundLocalError if green is
        # pressed too early
        self.epath = ""

    def setStartDir(self):
        # Attempt to descend into the initial directory if possible (e.g., if
        # currDir is a mountpoint)
        if self["filelist"].canDescent():
            self["filelist"].descent()

        self.CurrentDirectory = self["filelist"].getCurrentDirectory()
        self.instance.setTitle(self.CurrentDirectory)
        self.setPathName()

    def updatePathName(self):
        filename = self["filelist"].getFilename()

        # The original try-except block to handle TypeError when getFilename() returns None is simplified.
        # Check if a filename is actually selected (it can be None when no item
        # is selected or on '..' entry)
        if filename is None:
            # If no file/directory is selected, we can't show a 'select'
            # option.
            self["ButtonGreentext"].hide()
            self["ButtonGreen"].hide()
            # Keep CurrentDirectory title updated
            self.CurrentDirectory = self["filelist"].getCurrentDirectory()
            self.instance.setTitle(self.CurrentDirectory)
            return  # Exit the function if nothing is selected

        # Logic check: If the selected item's full path is longer than the current directory, it means
        # we are highlighting an actual file/directory *within* the current directory.
        # This is the original logic's intent.
        if len(filename) > len(self.CurrentDirectory):
            self.setPathName()
        # If showFilesBoolean is True, we always want to show the path name for the selected item,
        # regardless of length (e.g., for selecting a file at the current
        # level).
        elif self.showFilesBoolean:
            self.setPathName()
        # If showFilesBoolean is False (directory selection only) AND we are not highlighting a
        # sub-item (meaning we are on '..' or a mountpoint entry that has the same length as CurrentDirectory
        # when `getFilename()` is called), then we hide the select button.
        else:
            self["ButtonGreentext"].hide()
            self["ButtonGreen"].hide()

        self.CurrentDirectory = self["filelist"].getCurrentDirectory()
        self.instance.setTitle(self.CurrentDirectory)

    def setPathName(self):
        filename = self["filelist"].getFilename()
        if filename is None:
            # Should not happen if called correctly from
            # updatePathName/setStartDir, but as a safeguard:
            self.epath = self.CurrentDirectory
        elif self.showFilesBoolean and not self["filelist"].canDescent() and not filename.startswith('..'):
            # Original logic: if showing files AND the current item is not a directory we can descend into (i.e., a file or '.' entry)
            # then use the full path composed of the directory and the filename.
            # Added check for '..' to avoid path issues when selecting the
            # parent directory entry as a "file" path.
            self.epath = self.CurrentDirectory + filename
        else:
            # Otherwise, use the full path returned by getFilename() (which is
            # the path to the directory/file)
            self.epath = filename

        # Remove trailing slash if it's not the root directory '/'
        if len(self.epath) > 1 and self.epath.endswith('/'):
            self.epath = self.epath[:-1]

        # This print is kept for debugging purposes as is common in this type of code.
        # print(self.epath)

        self["ButtonGreentext"].setText(_("select:") + " " + self.epath)
        self["ButtonGreentext"].show()
        self["ButtonGreen"].show()

    def ok(self):
        if self["filelist"].canDescent():
            self["filelist"].descent()

            filename = self["filelist"].getFilename()

            # Simplified and corrected logic for showing the path name after
            # descending into a directory:
            if filename is not None:
                # If we descended and there is a selected item (i.e. not an empty directory),
                # call setPathName to update the 'select' path.
                # The original logic comparing lengths was flawed when descending, as getFilename()
                # should return a relative path or None right after descent, and the new directory
                # should be shown in the title.
                self.setPathName()
            else:
                # Handle the case where the new directory is empty or no item
                # is selected (like on '..')
                self["ButtonGreentext"].hide()
                self["ButtonGreen"].hide()

            # Update current directory and title regardless of the item
            # selected inside the new folder
            self.CurrentDirectory = self["filelist"].getCurrentDirectory()
            self.instance.setTitle(self.CurrentDirectory)

    def up(self):
        self["filelist"].up()
        self.updatePathName()

    def down(self):
        self["filelist"].down()
        self.updatePathName()

    def left(self):
        self["filelist"].pageUp()
        self.updatePathName()

    def right(self):
        self["filelist"].pageDown()
        self.updatePathName()

    # Redundant 'red' method removed and simply mapped to 'cancel'
    def cancel(self):
        self.close(False)

    def red(self):
        self.close(False)

    def green(self):
        # Ensure self.epath is set before trying to close
        if hasattr(self, 'epath') and self.epath:
            self.close(self.epath)
        else:
            # Fallback, perhaps select the current directory if nothing else is
            # selected
            self.close(self.CurrentDirectory)
