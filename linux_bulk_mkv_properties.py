#!/usr/bin/python3
"""
Application:  linux_bulk_mkv_properties.py
Author:  BSFEMA
Started:  2023-03-30
Prerequisites:  You need to have MKVToolNix installed:  https://mkvtoolnix.download/downloads.html
                Try running "mkvmerge --version" in terminal
                If that works, then you are good to go, otherwise install MKVToolNix
Command Line Parameters:  There is just 1:
                          It is the folder path that will be used to start looking at the *.mkv files from.
                          If this value isn't provided, then the starting path will be where this application file is located.
                          The intention is that you can call this application from a context menu from a file browser (e.g. Nemo) and it would automatically load up that folder.
Purpose:  I couldn't find a good tool for bulk changing the default flag on audio and subtitle tracks in mkv files on **Linux**, so I decided to make my own.
          While I made the Linux Bulk MKV Edit (https://github.com/BSFEMA/linux_bulk_mkv_properties) to remove audio & subtitle tracks,
          I have run into situations where I just want to set the default audio & subtitle tracks without making any 'real' changes.
          I created Linux Bulk MKV Properties to do just that.
          This will not perform the conversion directly, but will spit out the command lines necessary to do the conversions.
          Simply copy the command lines into a terminal and away it goes.
Resources:  https://mkvtoolnix.download/doc/mkvpropedit.html
            https://docs.gtk.org/Pango/pango_markup.html
"""


import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
import sys
import os
import re
import datetime
from operator import itemgetter
import subprocess
import json


default_folder_path = ""  # The path for the filechooser and data grid to work against.  This is the base folder to work against.
files_Full = []  # Holds all of the file information
files = []  # Holds only the file information for displaying in the data grid
konami_code = []  # Easter Egg to see if the Konami code has been entered in the About dialog.
languages_audio = []  # Holds the unique audio languages
types_audio = []  # Holds the unique audio types (codex)
ids_audio = []  # Holds the unique audio IDs
languages_subtitle = []  # Holds the unique subtitle languages
types_subtitle = []  # Holds the unique subtitle types (codex)
ids_subtitle = []  # Holds the unique subtitle ids
command_lines = {}  # The full list of command lines, or the output of this application
output = ""  # The output of the command lines
multi_lines = False


class Main():
    def __init__(self):
        global multi_lines
        # Setup Glade Gtk
        self.builder = gtk.Builder()
        self.builder.add_from_file(os.path.join(sys.path[0], "linux_bulk_mkv_properties.glade"))  # Looking where the python script is located
        self.builder.connect_signals(self)
        # Get UI components
        window = self.builder.get_object("main_Window")
        window.connect("delete-event", gtk.main_quit)
        window.set_title('Linux Bulk MKV Properties')
        window.set_default_icon_from_file(os.path.join(sys.path[0], "linux_bulk_mkv_properties.svg"))  # Setting the "default" icon makes it usable in the about dialog. (This will take .ico, .png, and .svg images.)
        # Set the default size of the window
        # window.resize(982, 580)
        # Set the default data grid height (400)
        self.set_scrollwindow_Data_Grid_height(400)
        window.show()
        # This allows the use css styling
        provider = gtk.CssProvider()
        provider.load_from_path(os.path.join(sys.path[0], "linux_bulk_mkv_properties.css"))  # Looking where the python script is located
        gtk.StyleContext().add_provider_for_screen(gdk.Screen.get_default(), provider, gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        # Set initial_load to True so that the data grid doesn't refresh multiple times when various settings are being initialized
        self.initial_load = True
        # Set filechooser_Folder_Selecter and entry_Folder_path values to the default_folder_path
        filechooser_Folder_Selecter = self.builder.get_object("filechooser_Folder_Selecter")
        filechooser_Folder_Selecter.set_current_folder(default_folder_path)
        entry_Folder_path = self.builder.get_object("entry_Folder_path")
        entry_Folder_path.set_text(default_folder_path)
        # Set various objects to their defaults:
        button_Multi = self.builder.get_object("button_Multi")
        button_Multi.set_active(1)
        multi_lines = button_Multi.get_active()
        # Set the alignment of the Audio and Subtite data grid colums
        cellrenderer_Subtitles = self.builder.get_object("cellrenderer_Subtitles")
        cellrenderer_Audio = self.builder.get_object("cellrenderer_Audio")
        # alignment: (X/Horizontal, Y/Vertical)  [values 0.0-1.0]
        # (0,0) = Left, Top
        # (0,1) = Left, Bottom
        # (1,0) = Right, Top
        # (1,1) = Right, Botton
        cellrenderer_Subtitles.set_alignment(0, 0)
        cellrenderer_Audio.set_alignment(0, 0)
        # Set the button_Process image
        button_Process = self.builder.get_object("button_Process")
        button_Process.set_always_show_image(True)
        self.button_Process_image = gtk.Image()
        self.button_Process_image.set_from_file(os.path.join(sys.path[0], "linux_bulk_mkv_properties.svg"))
        self.button_Process_image.get_style_context().add_class('spinner')
        button_Process.set_image(self.button_Process_image)
        button_Process.set_image_position(gtk.PositionType.TOP)
        # Set combo_Title_Keep to default value (2nd entry because I like that option)
        combo_Title_Keep = self.builder.get_object("combo_Title_Keep")
        combo_Title_Keep.set_entry_text_column(0)
        combo_Title_Keep.set_active(1)
        # Set initial_load to False as the application settings should now be setup correctly
        self.initial_load = False
        self.repaint_GUI()  # Make sure GUI is up to date
        watch_cursor = gdk.Cursor(gdk.CursorType.WATCH)
        window.get_window().set_cursor(watch_cursor)  # Set curror to 'Waiting'
        self.repaint_GUI()  # Make sure GUI is up to date
        # Setup the data grid
        self.clear_Data_Grid()
        populate_files_Full()
        self.update_lables()
        self.load_Data_Grid()
        self.resize_column_widths()
        self.repaint_GUI()  # Make sure GUI is up to date
        window.get_window().set_cursor(None)  # Set curror back to 'None'
        self.repaint_GUI()  # Make sure GUI is up to date

    """ ************************************************************************************************************ """
    #  These are the various widget's signal handler functions:  UI elements other than buttons & dialogs
    """ ************************************************************************************************************ """

    def repaint_GUI(self):
        # Defect #2 - Implement a waiting cursor to give an indication when the data grid is taking a long time to load.
        # Unfortunately, I haven't found an easier/better way to implement this...
        while gtk.events_pending():
            gtk.main_iteration_do(False)

    def filechooser_Folder_Selecter_fileset(self, widget):
        entry_Folder_path = self.builder.get_object("entry_Folder_path")
        entry_Folder_path.set_text(widget.get_filename())

    def entry_Folder_Path_changed(self, widget):
        if not self.initial_load:
            self.repaint_GUI()  # Make sure GUI is up to date
            window = self.builder.get_object("main_Window")
            watch_cursor = gdk.Cursor(gdk.CursorType.WATCH)
            window.get_window().set_cursor(watch_cursor)  # Set curror to 'Waiting'
            self.repaint_GUI()  # Make sure GUI is up to date
            current_path = widget.get_text()
            if os.path.isdir(current_path):
                widget.get_style_context().remove_class('red-foreground')
                # widget.get_style_context().add_class('black-foreground')
                # Reload the data grid now that a new (real) folder is selected
                global default_folder_path
                if current_path[-1:] == "/":  # remove the final "/" from a path
                    current_path = current_path[:-1]
                default_folder_path = current_path  # Now that the edited text is a folder, set the default_folder_path to use that
                self.clear_Data_Grid()
                populate_files_Full()
                self.load_Data_Grid()
                self.resize_column_widths()
                self.update_lables()
            else:
                # widget.get_style_context().remove_class('black-foreground')
                widget.get_style_context().add_class('red-foreground')
            self.repaint_GUI()  # Make sure GUI is up to date
            window.get_window().set_cursor(None)  # Set curror back to 'None'
            self.repaint_GUI()  # Make sure GUI is up to date

    def set_scrollwindow_Data_Grid_height(self, new_height):  # Set the height of the data grid
        scrollwindow_Data_Grid = self.builder.get_object("scrollwindow_Data_Grid")
        if int(new_height) >= 0:
            scrollwindow_Data_Grid.set_size_request(scrollwindow_Data_Grid.get_allocated_width(), int(new_height))
        else:
            scrollwindow_Data_Grid.set_size_request(scrollwindow_Data_Grid.get_allocated_width(), 200)  # Default is 400

    def update_lables(self):
        global languages_audio
        global languages_subtitle
        global types_audio
        global types_subtitle
        global ids_audio
        global ids_subtitle
        l_a = ""
        t_a = ""
        l_s = ""
        t_s = ""
        i_a = ""
        i_s = ""
        for element in languages_audio:
            if len(l_a) == 0:
                l_a = element
            else:
                l_a = l_a + ", " + element
        for element in types_audio:
            if len(t_a) == 0:
                t_a = element
            else:
                t_a = t_a + ", " + element
        for element in languages_subtitle:
            if len(l_s) == 0:
                l_s = element
            else:
                l_s = l_s + ", " + element
        for element in types_subtitle:
            if len(t_s) == 0:
                t_s = element
            else:
                t_s = t_s + ", " + element
        for element in ids_audio:
            if len(i_a) == 0:
                i_a = element
            else:
                i_a = i_a + ", " + element
        for element in ids_subtitle:
            if len(i_s) == 0:
                i_s = element
            else:
                i_s = i_s + ", " + element
        # Update the GUI with the languages and types
        label_Audio_Languages = self.builder.get_object("label_Audio_Languages")
        label_Audio_Types = self.builder.get_object("label_Audio_Types")
        label_Subtitles_Languages = self.builder.get_object("label_Subtitles_Languages")
        label_Subtitles_Types = self.builder.get_object("label_Subtitles_Types")
        label_IDs_Audio = self.builder.get_object("label_IDs_Audio")
        label_IDs_Subtitles = self.builder.get_object("label_IDs_Subtitles")
        label_Audio_Languages.set_text("  Languages (" + str(l_a) + "):")
        label_Audio_Types.set_text("  Types (" + str(t_a) + "):")
        label_Subtitles_Languages.set_text("  Languages (" + str(l_s) + "):")
        label_Subtitles_Types.set_text("  Types (" + str(t_s) + "):")
        label_IDs_Audio.set_text("3. Set Detault Audio Track IDs (" + str(i_a) + "):")
        label_IDs_Subtitles.set_text("4. Set Detault Subtitle Track IDs (" + str(i_s) + "):")
        entry_Audio_Languages = self.builder.get_object("entry_Audio_Languages")
        entry_Subtitles_Languages = self.builder.get_object("entry_Subtitles_Languages")
        entry_Audio_Languages.set_text(str(l_a))
        entry_Subtitles_Languages.set_text(str(l_s))

    """ ************************************************************************************************************ """
    #  These are the various widget's signal handler functions:  UI elements that are buttons & dialogs
    """ ************************************************************************************************************ """

    def button_Multi_toggled(self, widget):
        global multi_lines
        button_Multi = self.builder.get_object("button_Multi")
        multi_lines = button_Multi.get_active()
        populate_files_Full()
        self.button_Refresh_clicked(self)

    def button_Process_clicked(self, widget):
        global default_folder_path
        global files_Full
        global command_lines
        combo_Title_Keep = self.builder.get_object("combo_Title_Keep")
        entry_Audio_Languages = self.builder.get_object("entry_Audio_Languages")
        entry_Audio_Name = self.builder.get_object("entry_Audio_Name")
        entry_Audio_Types = self.builder.get_object("entry_Audio_Types")
        entry_Subtitles_Languages = self.builder.get_object("entry_Subtitles_Languages")
        entry_Subtitles_Name = self.builder.get_object("entry_Subtitles_Name")
        entry_Subtitles_Types = self.builder.get_object("entry_Subtitles_Types")
        entry_IDs_Audio = self.builder.get_object("entry_IDs_Audio")
        entry_IDs_Subtitles = self.builder.get_object("entry_IDs_Subtitles")
        command_lines.clear()
        command_lines = {}
        ################################################################################
        # Clear up input
        # Title
        mkv_title = combo_Title_Keep.get_active()
        # Audio Languages
        al = ""
        if len(entry_Audio_Languages.get_text()) != 0:
            if ',' in entry_Audio_Languages.get_text():
                al = entry_Audio_Languages.get_text().split(',')
                count = 0
                for lang in al:
                    lang = lang.strip()
                    if len(lang) == 0:
                        al.pop(count)
                    count = count + 1
            else:
                al = entry_Audio_Languages.get_text()
        # Audio Name
        an = ""
        if len(entry_Audio_Name.get_text()) != 0:
            an = entry_Audio_Name.get_text().strip()
        # Audio Types
        at = ""
        if len(entry_Audio_Types.get_text()) != 0:
            at = entry_Audio_Types.get_text().strip()
        # Audio IDs
        ai = ""
        if len(entry_IDs_Audio.get_text()) != 0:
            if ',' in entry_IDs_Audio.get_text():
                ai = entry_IDs_Audio.get_text().split(',')
                ai_temp = []
                for id in ai:
                    id = id.strip()
                    if len(id) > 0:
                        ai_temp.append(id)
                ai = ai_temp
            else:
                ai = entry_IDs_Audio.get_text()
        # Subtitle Languages
        sl = ""
        if len(entry_Subtitles_Languages.get_text()) != 0:
            if ',' in entry_Subtitles_Languages.get_text():
                sl = entry_Subtitles_Languages.get_text().split(',')
                count = 0
                for lang in sl:
                    lang = lang.strip()
                    if len(lang) == 0:
                        sl.pop(count)
                    count = count + 1
            else:
                sl = entry_Subtitles_Languages.get_text().strip()
        # Subtitle Name
        sn = ""
        if len(entry_Subtitles_Name.get_text()) != 0:
            sn = entry_Subtitles_Name.get_text().strip()
        # Subtitle Types
        st = ""
        if len(entry_Subtitles_Types.get_text()) != 0:
            st = entry_Subtitles_Types.get_text().strip()
        # Subtitle IDs
        si = ""
        if len(entry_IDs_Subtitles.get_text()) != 0:
            if ',' in entry_IDs_Subtitles.get_text():
                si = entry_IDs_Subtitles.get_text().split(',')
                si_temp = []
                for id in si:
                    id = id.strip()
                    if len(id) > 0:
                        si_temp.append(id)
                si = si_temp
            else:
                si = entry_IDs_Subtitles.get_text()
        ################################################################################
        # files_Full[0] = Current_Name
        # files_Full[1] = New_Name
        # files_Full[2] = File_Size
        # files_Full[3] = File_Date
        # files_Full[4] = Audio
        # files_Full[5] = Subtitles
        # files_Full[6] = Status
        # files_Full[7] = (json data) {}
        # files_Full[8] = (video tracks) {}
        # files_Full[9] = (audio tracks) {}
        # files_Full[10] = (subtitle tracks) {}
        # Build list of Track IDs to keep
        for i in range(len(files_Full)):
            # Make list of all Audio and Subtitle tracks
            audio_and_subtitles = []
            for track in files_Full[i][9]:
                audio_and_subtitles.append(track)
            for track in files_Full[i][10]:
                audio_and_subtitles.append(track)
            # Make a temp copy of the file, then start removing the various tracks
            keep_audio = []
            keep_subtitle = []
            # Audio Languages
            temp_audio = []
            for track in files_Full[i][9]:
                if files_Full[i][9][track]["track_lang"] in str(al):
                    temp_audio.append(track)
            keep_audio = keep_audio + temp_audio
            # Audio Name
            if len(an) > 0:
                temp_audio = []
                for track in files_Full[i][9]:
                    if str(an).upper() in files_Full[i][9][track]["track_name"].upper():
                        temp_audio.append(track)
                keep_audio = keep_audio + temp_audio
            # Audio Type
            if len(at) > 0:
                temp_audio = []
                for track in files_Full[i][9]:
                    if str(at).upper() in files_Full[i][9][track]["track_type"].upper():
                        temp_audio.append(track)
                keep_audio = temp_audio
            # Audio IDs
            if len(ai) > 0:
                temp_audio = []
                for track in ai:
                    if str(track) in ids_audio:
                        temp_audio.append(track)
                keep_audio = keep_audio + temp_audio
            # Subtitle Languages
            temp_subtitle = []
            for track in files_Full[i][10]:
                if files_Full[i][10][track]["track_lang"] in str(sl):
                    temp_subtitle.append(track)
            keep_subtitle = keep_subtitle + temp_subtitle
            # Subtitle Name
            if len(sn) > 0:
                temp_subtitle = []
                for track in files_Full[i][10]:
                    if str(sn).upper() in files_Full[i][10][track]["track_name"].upper():
                        temp_subtitle.append(track)
                keep_subtitle = keep_subtitle + temp_subtitle
            # Subtitle Type
            if len(st) > 0:
                temp_subtitle = []
                for track in files_Full[i][10]:
                    if str(st).upper() in files_Full[i][10][track]["track_type"].upper():
                        temp_subtitle.append(track)
                keep_subtitle = keep_subtitle + temp_subtitle
            # Subtitle IDs
            if len(si) > 0:
                temp_subtitle = []
                for track in si:
                    if str(track) in ids_subtitle:
                        temp_subtitle.append(track)
                keep_subtitle = keep_subtitle + temp_subtitle
            ################################################################################
            # Build the track options based on the remaining tracks
            """
            mkvpropedit [options] {source-filename} {actions}

            mkvpropedit movie.mkv
            --edit info
            --set "title=The movie"
            --edit track:1 --set language=fre
            --edit track:2 --set language=ita
            --edit track:1 --set flag-default=0
            --edit track:2 --set flag-default=1
            Note: Since tracks are zero based, need to use (track_ID + 1)
            """
            command = "/usr/bin/mkvpropedit '" + str(files_Full[i][0]) + "' --edit info "
            if mkv_title == 1:
                command = command + "--set \"title=\" "
            # Set all to NOT default
            for track in audio_and_subtitles:
                command = command + "--edit track:" + str(int(track) + 1) + " --set flag-default=0 "
            # Set Default Audio Tracks
            for track in keep_audio:
                command = command + "--edit track:" + str(int(track) + 1) + " --set flag-default=1 "
            # Set Default Subtitle Tracks
            for track in keep_subtitle:
                command = command + "--edit track:" + str(int(track) + 1) + " --set flag-default=1 "
            command_lines[files_Full[i][0]] = command
        # print(str(command_lines))
        self.dialog_Results(self)

    def dialog_Results(self, widget):  # Creates the "Results" dialog that displays the command line
        global command_lines
        global output
        # Make output
        output = ""
        for command in command_lines:
            output = output + "# " + str(command) + "\n"
            output = output + str(command_lines[command]) + "\n"
        # Create Dialog
        dialog = gtk.Dialog(title="Command Lines", parent=None)
        dialog.set_modal(True)
        dialog.set_default_size(1200, 600)
        area = dialog.get_content_area()
        dialog.add_buttons(gtk.STOCK_OK, gtk.ResponseType.OK)
        # Add a 'copy to clipboard' button
        button_copy_to_clipboard = gtk.Button(label="Copy output to Clipboard")
        button_copy_to_clipboard.connect("clicked", self.copy_output_to_clipboard)
        # Create textview
        dialog.textview = gtk.TextView()
        textbuffer = dialog.textview.get_buffer()
        dialog.textview.set_wrap_mode(gtk.WrapMode.WORD)
        textbuffer.set_text(str(output))
        # Create a scrolledwindow, so the text view fills the dialog and is resizable
        scrolledwindow = gtk.ScrolledWindow()
        scrolledwindow.set_hexpand(True)
        scrolledwindow.set_vexpand(True)
        scrolledwindow.add(dialog.textview)
        area.add(scrolledwindow)
        area.add(button_copy_to_clipboard)
        # Display the dialog
        dialog.show_all()
        dialog.run()
        dialog.destroy()

    def copy_output_to_clipboard(self, widget):
        global output
        self.clipboard = gtk.Clipboard.get(gdk.SELECTION_CLIPBOARD)
        self.clipboard.set_text(output, -1)

    def button_Refresh_clicked(self, widget):
        self.repaint_GUI()  # Make sure GUI is up to date
        window = self.builder.get_object("main_Window")
        watch_cursor = gdk.Cursor(gdk.CursorType.WATCH)
        window.get_window().set_cursor(watch_cursor)  # Set curror to 'Waiting'
        self.repaint_GUI()  # Make sure GUI is up to date
        self.clear_Data_Grid()
        populate_files_Full()
        self.load_Data_Grid()
        self.resize_column_widths()
        self.update_lables()
        self.repaint_GUI()  # Make sure GUI is up to date
        window.get_window().set_cursor(None)  # Set curror back to 'None'
        self.repaint_GUI()  # Make sure GUI is up to date

    def button_Reset_clicked(self, widget):
        entry_Audio_Languages = self.builder.get_object("entry_Audio_Languages")
        entry_Audio_Name = self.builder.get_object("entry_Audio_Name")
        entry_Audio_Types = self.builder.get_object("entry_Audio_Types")
        entry_Subtitles_Languages = self.builder.get_object("entry_Subtitles_Languages")
        entry_Subtitles_Name = self.builder.get_object("entry_Subtitles_Name")
        entry_Subtitles_Types = self.builder.get_object("entry_Subtitles_Types")
        entry_Audio_Languages.set_text("")
        entry_Audio_Name.set_text("")
        entry_Audio_Types.set_text("")
        entry_Subtitles_Languages.set_text("")
        entry_Subtitles_Name.set_text("")
        entry_Subtitles_Types.set_text("")
        combo_Title_Keep = self.builder.get_object("combo_Title_Keep")
        combo_Title_Keep.set_entry_text_column(0)
        combo_Title_Keep.set_active(1)
        parse_json_data()
        self.update_lables()

    def button_About_clicked(self, widget):  # Creates the About Dialog
        about = gtk.AboutDialog()
        about.connect("key-press-event", self.about_dialog_key_press)  # Easter Egg:  Check to see if Konami code has been entered
        about.set_program_name("Linux Bulk MKV Properties")
        about.set_version("Version 1.4")
        about.set_copyright("Copyright (c) BSFEMA")
        about.set_comments("Python application using Gtk and Glade for bulk editing MKV default properties in Linux")
        about.set_license_type(gtk.License(7))  # License = MIT_X11
        about.set_website("https://github.com/BSFEMA/linux_bulk_mkv_properties")
        about.set_website_label("https://github.com/BSFEMA/linux_bulk_mkv_properties")
        about.set_authors(["BSFEMA"])
        about.set_artists(["BSFEMA"])
        about.set_documenters(["BSFEMA"])
        about.run()
        about.destroy()

    def about_dialog_key_press(self, widget, event):  # Easter Egg:  Check to see if Konami code has been entered
        global konami_code
        keyname = gdk.keyval_name(event.keyval)
        if len(konami_code) == 10:
            konami_code.pop(0)
            konami_code.append(keyname)
        else:
            konami_code.append(keyname)
        if (konami_code == ['Up', 'Up', 'Down', 'Down', 'Left', 'Right', 'Left', 'Right', 'b', 'a']) or (konami_code == ['Up', 'Up', 'Down', 'Down', 'Left', 'Right', 'Left', 'Right', 'B', 'A']):
            self.dialog_BSFEMA(self)
            # print("Konami code entered:  " + str(konami_code))
            konami_code.clear()

    def dialog_BSFEMA(self, widget):  # Creates the "BSFEMA" dialog that just spins my logo
        dialog = gtk.Dialog(title="BSFEMA", parent=None)
        dialog.add_buttons(gtk.STOCK_OK, gtk.ResponseType.OK)
        dialog.set_modal(True)
        # dialog.set_default_size(200, 200)
        area = dialog.get_content_area()
        dialog.image = gtk.Image()
        dialog.image.set_from_file(os.path.join(sys.path[0], "linux_bulk_mkv_properties.svg"))
        dialog.image.get_style_context().add_class('spinner')
        area.add(dialog.image)
        dialog.show_all()
        dialog.run()
        dialog.destroy()

    """ ************************************************************************************************************ """
    # These are the various class functions
    """ ************************************************************************************************************ """

    def entry_Add_File_Name_changed(self, widget):
        self.load_Data_Grid()
        self.resize_column_widths()

    def rename_files(self):  # This is the function that actually does the file renaming action
        global default_folder_path

    def resize_column_widths(self):  # have the data grid columns automatically resize
        treeviewcolumn_Current_Name = self.builder.get_object("treeviewcolumn_Current_Name")
        treeviewcolumn_Current_Name.queue_resize()
        treeviewcolumn_Title = self.builder.get_object("treeviewcolumn_Title")
        treeviewcolumn_Title.queue_resize()
        treeviewcolumn_Full_Audio = self.builder.get_object("treeviewcolumn_Audio")
        treeviewcolumn_Full_Audio.queue_resize()
        treeviewcolumn_Full_Subtitles = self.builder.get_object("treeviewcolumn_Subtitles")
        treeviewcolumn_Full_Subtitles.queue_resize()
        treeviewcolumn_Defaults = self.builder.get_object("treeviewcolumn_Defaults")
        treeviewcolumn_Defaults.queue_resize()

    def clear_Data_Grid(self):  # Clears out the data grid and global files lists
        # treeview_Data_Grid = Select None
        treeview_Data_Grid = self.builder.get_object("treeview_Data_Grid")
        selection = treeview_Data_Grid.get_selection()
        selection.unselect_all()
        # Do the rest of the original clear_Data_Grid bits
        liststore_Data_Grid = self.builder.get_object("liststore_Data_Grid")
        liststore_Data_Grid.clear()
        global files
        global files_Full
        files.clear()
        files_Full.clear()

    def load_Data_Grid(self):  # Loads data grid with files list
        # files_Full[0] = Current_Name
        # files_Full[1] = New_Name
        # files_Full[2] = File_Size
        # files_Full[3] = File_Date
        # files_Full[4] = Audio
        # files_Full[5] = Subtitles
        # files_Full[6] = Status
        # files_Full[7] = (json data) {}
        # files_Full[8] = (video tracks) {}
        # files_Full[9] = (audio tracks) {}
        # files_Full[10] = (subtitle tracks) {}
        global files
        files.clear()
        liststore_Data_Grid = self.builder.get_object("liststore_Data_Grid")
        liststore_Data_Grid.clear()
        # Build files from files_Full
        # Get prefix and suffix for new file names
        for file in files_Full:
            files.append([file[0], file[1], file[2], file[3], file[4]])
        # Build data grid from files
        for file in files:
            liststore_Data_Grid.append(file)


""" **************************************************************************************************************** """
# "class Main()" ends here...
# Beyond here lay functions...
""" **************************************************************************************************************** """


def get_list_of_mkv_files():  # Gets the list of all files and folder from the default_folder_path
    global default_folder_path
    file_list = []  # Temp list to be sorted
    file_list.clear()
    for filename in os.listdir(default_folder_path):
        if str(filename[-4:]).lower() == ".mkv":
            if os.path.isfile(default_folder_path + "/" + str(filename)):
                file_list.append(str(filename))
    file_list.sort()  # Get a sorted list of the files
    return file_list


def populate_files_Full():
    # This populates the files_Full list with all file/folder information, which is the basis of the data grid
    global files_Full
    # files_Full[0] = Current_Name
    # files_Full[1] = Title
    # files_Full[2] = Audio
    # files_Full[3] = Subtitles
    # files_Full[4] = Defaults
    # files_Full[5] = ""
    # files_Full[6] = ""
    # files_Full[7] = (json data) {}
    # files_Full[8] = (video tracks) {}
    # files_Full[9] = (audio tracks) {}
    # files_Full[10] = (subtitle tracks) {}
    files_Full.clear()
    files_temp = []
    files_temp = get_list_of_mkv_files()
    files_temp.sort()
    for file in files_temp:
        part0 = file
        part1 = ""
        part2 = ""
        part3 = ""
        part4 = ""
        part5 = ""
        part6 = ""
        # Get information from mkv file in json format:
        cmd = ["mkvmerge --identify --identification-format json \"" + default_folder_path + "/" + file + "\""]
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        json_data, err = proc.communicate()
        json_data = json_data.decode("utf-8")
        part7 = json.loads(json_data)  # json information of all objects in the mkv file
        part8 = {}
        part9 = {}
        part10 = {}
        part11 = []
        part12 = []
        files_Full.append([part0, part1, part2, part3, part4, part5, part6, part7, part8, part9, part10, part11])
    # Get the track information
    parse_json_data()


def parse_json_data():
    global files_Full
    global languages_audio
    global languages_subtitle
    global types_audio
    global types_subtitle
    global ids_audio
    global ids_subtitle
    global multi_lines
    # Clear the lists
    languages_audio.clear()
    languages_subtitle.clear()
    types_audio.clear()
    types_subtitle.clear()
    ids_audio.clear()
    ids_subtitle.clear()
    # Parse the json data to get the individual tracks for the various types
    for i in range(len(files_Full)):
        if "title" in files_Full[i][7]["container"]["properties"]:
            files_Full[i][1] = files_Full[i][7]["container"]["properties"]["title"]
        if not (files_Full[i][7].get("tracks") is None):
            command = ""
            for track in files_Full[i][7]["tracks"]:
                # track_type = track["properties"]["codec_id"]
                track_type = track["codec"]
                track_id = track["id"]
                if track["properties"].get("default_track") == True:
                    if str(track["type"]).upper() != "video".upper():
                        files_Full[i][11].append(str(track_id))
                        if len(files_Full[i][4]) == 0:
                            files_Full[i][4] = "<b>" + str(track_id) + "</b>-" + str(track["type"])
                        else:
                            files_Full[i][4] = files_Full[i][4] + "\n<b>" + str(track_id) + "</b>-" + str(track["type"])
                if track["type"] == "audio":  # Populate the track IDs for the audio tracks
                    if str(track_id) not in ids_audio:
                        ids_audio.append(str(track_id))
                if track["type"] == "subtitles":  # Populate the track IDs for the subtitle tracks
                    if str(track_id) not in ids_subtitle:
                        ids_subtitle.append(str(track_id))
                if "language_ietf" in track["properties"]:  # "language_ietf" isn't always a property...
                    track_lang = track["properties"]["language_ietf"]
                elif "language" in track["properties"]:
                    track_lang = track["properties"]["language"]
                else:
                    track_lang = ""
                if not (track["properties"].get("track_name") is None):
                    track_name = track["properties"]["track_name"]
                else:
                    track_name = ""
                if track["type"] == "video":
                    if "display_dimensions" in track["properties"]:
                        track_disdim = track["properties"]["display_dimensions"]
                    else:
                        track_disdim = ""
                    files_Full[i][8][track_id] = {"track_type": track_type, "track_lang": track_lang, "track_name": track_name, "track_disdim": track_disdim}
                elif track["type"] == "audio":
                    if track_lang not in languages_audio:
                        languages_audio.append(track_lang)
                    if track_type not in types_audio:
                        types_audio.append(track_type)
                    files_Full[i][9][track_id] = {"track_type": track_type, "track_lang": track_lang, "track_name": track_name}
                elif track["type"] == "subtitles":
                    if "encoding" in track["properties"]:
                        track_encode = track["properties"]["encoding"]
                    else:
                        track_encode = ""
                    if track_lang not in languages_subtitle:
                        languages_subtitle.append(track_lang)
                    if track_type not in types_subtitle:
                        types_subtitle.append(track_type)
                    files_Full[i][10][track_id] = {"track_type": track_type, "track_lang": track_lang, "track_name": track_name, "track_encode": track_encode}
                else:
                    print("Unknown track type = " + str(file))
    # Sort the lists
    languages_audio.sort()
    languages_subtitle.sort()
    types_audio.sort()
    types_subtitle.sort()
    ids_audio.sort()
    ids_subtitle.sort()
    # Parse the individual tracks to get the easy list of audio and subtitles
    # files_Full[0] = Current_Name
    # files_Full[1] = Title
    # files_Full[2] = Audio
    # files_Full[3] = Subtitles
    # files_Full[4] = Defaults
    if multi_lines == True:
        multi_lines_string = "\n"
    else:
        multi_lines_string = ",  "
    for i in range(len(files_Full)):
        audio = ""
        for track in files_Full[i][9]:
            name = str(files_Full[i][9][track]["track_name"])
            name = name.replace("&", "&amp;")
            if name == "":
                if len(audio) > 0:
                    if str(track) in files_Full[i][11]:
                        audio = audio + str(multi_lines_string) + "<b>" + str(track) + "-" + str(files_Full[i][9][track]["track_lang"]) + " (" + str(files_Full[i][9][track]["track_type"]) + ")</b>"
                    else:
                        audio = audio + str(multi_lines_string) + str(track) + "-" + str(files_Full[i][9][track]["track_lang"]) + " (" + str(files_Full[i][9][track]["track_type"]) + ")"
                else:
                    if str(track) in files_Full[i][11]:
                        audio = audio + "<b>" + str(track) + "-" + str(files_Full[i][9][track]["track_lang"]) + " (" + str(files_Full[i][9][track]["track_type"]) + ")</b>"
                    else:
                        audio = audio + str(track) + "-" + str(files_Full[i][9][track]["track_lang"]) + " (" + str(files_Full[i][9][track]["track_type"]) + ")"
            else:
                if len(audio) > 0:
                    if str(track) in files_Full[i][11]:
                        audio = audio + str(multi_lines_string) + "<b>" + str(track) + "-" + str(files_Full[i][9][track]["track_lang"]) + " ('" + str(name) + "' " + str(files_Full[i][9][track]["track_type"]) + ")</b>"
                    else:
                        audio = audio + str(multi_lines_string) + str(track) + "-" + str(files_Full[i][9][track]["track_lang"]) + " ('" + str(name) + "' " + str(files_Full[i][9][track]["track_type"]) + ")"
                else:
                    if str(track) in files_Full[i][11]:
                        audio = audio + "<b>" + str(track) + "-" + str(files_Full[i][9][track]["track_lang"]) + " ('" + str(name) + "' " + str(files_Full[i][9][track]["track_type"]) + ")</b>"
                    else:
                        audio = audio + str(track) + "-" + str(files_Full[i][9][track]["track_lang"]) + " ('" + str(name) + "' " + str(files_Full[i][9][track]["track_type"]) + ")"
        files_Full[i][2] = audio
        subtitles = ""
        for track in files_Full[i][10]:
            name = str(files_Full[i][10][track]["track_name"])
            name = name.replace("&", "&amp;")
            if name == "":
                if len(subtitles) > 0:
                    if str(track) in files_Full[i][11]:
                        subtitles = subtitles + str(multi_lines_string) + "<b>" + str(track) + "-" + str(files_Full[i][10][track]["track_lang"]) + " (" + str(files_Full[i][10][track]["track_type"]) + ")</b>"
                    else:
                        subtitles = subtitles + str(multi_lines_string) + str(track) + "-" + str(files_Full[i][10][track]["track_lang"]) + " (" + str(files_Full[i][10][track]["track_type"]) + ")"
                else:
                    if str(track) in files_Full[i][11]:
                        subtitles = subtitles + "<b>" + str(track) + "-" + str(files_Full[i][10][track]["track_lang"]) + " (" + str(files_Full[i][10][track]["track_type"]) + ")</b>"
                    else:
                        subtitles = subtitles + str(track) + "-" + str(files_Full[i][10][track]["track_lang"]) + " (" + str(files_Full[i][10][track]["track_type"]) + ")"
            else:
                if len(subtitles) > 0:
                    if str(track) in files_Full[i][11]:
                        subtitles = subtitles + str(multi_lines_string) + "<b>" + str(track) + "-" + str(files_Full[i][10][track]["track_lang"]) + " ('" + str(name) + "' " + str(files_Full[i][10][track]["track_type"]) + ")</b>"
                    else:
                        subtitles = subtitles + str(multi_lines_string) + str(track) + "-" + str(files_Full[i][10][track]["track_lang"]) + " ('" + str(name) + "' " + str(files_Full[i][10][track]["track_type"]) + ")"
                else:
                    if str(track) in files_Full[i][11]:
                        subtitles = subtitles + "<b>" + str(track) + "-" + str(files_Full[i][10][track]["track_lang"]) + " ('" + str(name) + "' " + str(files_Full[i][10][track]["track_type"]) + ")</b>"
                    else:
                        subtitles = subtitles + str(track) + "-" + str(files_Full[i][10][track]["track_lang"]) + " ('" + str(name) + "' " + str(files_Full[i][10][track]["track_type"]) + ")"
        files_Full[i][3] = subtitles


def update_parameter_files_at_start(command_line_parameters):  # Fix and Validate the command lind parameter files list and add to parameter_files
    global parameter_files
    for param in command_line_parameters:
        # Remove the 'file://' part to get a valid 'path'
        temp_file_address = param.replace("file://", "")
        # Replace all percent-encoding with actual characters
        temp_file_address = temp_file_address.replace("%20", " ")
        temp_file_address = temp_file_address.replace("%21", "!")
        temp_file_address = temp_file_address.replace("%22", "\"")
        temp_file_address = temp_file_address.replace("%23", "#")
        temp_file_address = temp_file_address.replace("%24", "$")
        temp_file_address = temp_file_address.replace("%25", "%")
        temp_file_address = temp_file_address.replace("%26", "&")
        temp_file_address = temp_file_address.replace("%27", "\'")
        temp_file_address = temp_file_address.replace("%28", "(")
        temp_file_address = temp_file_address.replace("%29", ")")
        temp_file_address = temp_file_address.replace("%2A", "*")
        temp_file_address = temp_file_address.replace("%2B", "+")
        temp_file_address = temp_file_address.replace("%2C", ",")
        temp_file_address = temp_file_address.replace("%2D", "-")
        temp_file_address = temp_file_address.replace("%2E", ".")
        temp_file_address = temp_file_address.replace("%2F", "/")
        temp_file_address = temp_file_address.replace("%3A", ":")
        temp_file_address = temp_file_address.replace("%3B", ";")
        temp_file_address = temp_file_address.replace("%3C", "<")
        temp_file_address = temp_file_address.replace("%3D", "=")
        temp_file_address = temp_file_address.replace("%3E", ">")
        temp_file_address = temp_file_address.replace("%3F", "?")
        temp_file_address = temp_file_address.replace("%40", "@")
        temp_file_address = temp_file_address.replace("%5B", "[")
        temp_file_address = temp_file_address.replace("%5C", "\\")
        temp_file_address = temp_file_address.replace("%5D", "]")
        temp_file_address = temp_file_address.replace("%5E", "^")
        temp_file_address = temp_file_address.replace("%5F", "_")
        temp_file_address = temp_file_address.replace("%60", "`")
        temp_file_address = temp_file_address.replace("%7B", "{")
        temp_file_address = temp_file_address.replace("%7C", "|")
        temp_file_address = temp_file_address.replace("%7D", "}")
        temp_file_address = temp_file_address.replace("%7E", "~")
        if os.path.exists(temp_file_address):
            parameter_files.append(temp_file_address)
        else:
            print("There was a problem adding the following path from the command line parameters:  " + str(temp_file_address))


if __name__ == '__main__':
    # Check for command line arguments, and set the default_folder_path appropriately
    if len(sys.argv) > 1:  # If there is a command line argument, check if it is a folder
        if os.path.isdir(sys.argv[1]):  # Valid folder:  so set the default_folder_path to it
            default_folder_path = sys.argv[1]
        elif os.path.isdir(os.path.dirname(os.path.abspath(sys.argv[1]))):  # If valid file path was sent:  use folder path from it.
            default_folder_path = os.path.dirname(os.path.abspath(sys.argv[1]))
        elif "file://" in sys.argv[1]:  # In case using 'Bulk Rename' option in Nemo, get file path from first parameter and auto-select the files.
            update_parameter_files_at_start(sys.argv[1:])  # Convert URL encoded files to paths
            if os.path.isdir(os.path.dirname(os.path.abspath(parameter_files[0]))):  # If the first file is a valid path:  use folder path from it.
                default_folder_path = os.path.dirname(os.path.abspath(parameter_files[0]))
            else:  # Invalid first file path:  so set the default_folder_path to where the python file is
                default_folder_path = sys.path[0]
        else:  # Invalid file/folder paths:  so set the default_folder_path to where the python file is
            default_folder_path = sys.path[0]
    else:  # No command line argument:  so set the default_folder_path to where the python file is
        default_folder_path = sys.path[0]
    main = Main()
    gtk.main()
