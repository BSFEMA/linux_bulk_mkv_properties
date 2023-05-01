# Linux Bulk MKV Properties
A bulk MKV properties utility for Linux using Python and GTK+

## Purpose:
I couldn't find a good tool for bulk changing the default flag on audio and subtitle tracks in mkv files on **Linux**, so I decided to make my own.  While I made the [Linux Bulk MKV Edit](https://github.com/BSFEMA/linux_bulk_mkv_properties) to remove audio & subtitle tracks, I have run into situations where I just want to set the default audio & subtitle tracks without making any 'real' changes.  I created Linux Bulk MKV Properties to do just that.  This will not perform the conversion directly, but will spit out the command lines necessary to do the conversions.  Simply copy the command lines into a terminal and away it goes.

## Functionality:
* Point it at a folder and it will display for every .mkv file in that folder the following:
  * The file name
  * The MKV's Title
  * Audio track information:
    * Track ID/Number
    * Track Language
    * Track Name
    * Track Type/Codec
  * Subtitle track information:
    * Track ID/Number
    * Track Language
    * Track Name
    * Track Type/Codec
* Next, choose which tracks to **make default** based on the user selected criteria.  Please note that this application will set every audio/subtitle track to Default=False, then set Default=True for any track that matches the selection criteria below:
  * Audio/Subtitle Languages
    * Default:  A list each unique audio/subtitle languages that the combined MKV files have.
    * If you remove a track (Example:  Change "en, ja" to "ja"), then the resulting MKV files will only set the default track flag for the remaining audio/subtitle languages ("ja" in the case of the example).
  * Audio/Subtitle Name
    * If you populate this, then the resulting MKV files will only set the default track flag for the audio/subtitle tracks that have a track name that contains the characters (case insensative) you entered.
    * Note:  This is a single string field, it does not currently support multiple values.
  * Audio/Subtitle Type/Codec
    * If you populate this, then the resulting MKV files will only set the default track flag for the audio/subtitle tracks that have a track 'type'/'codec' that contains the characters you entered.
    * Note:  This is a single string field, it does not currently support multiple values.
  * Note:  If you don't modify the default selections, the resulting files will have all tracks set as default.
* Next, optionally choose which track IDs you want to set as default.
* Next, optionally choose if you want ot keep the MKV title or not.
* Next, click the Process Files button to get the command line output to perform the conversion.
* Paste the output into a terminal and the files will be converted.
* Note:  This will always set the MKV title to blank, which is my preference as I prefer my video player to just display the filename.
* HINT:  I recommend my own [Linux File Rename Utility](https://github.com/BSFEMA/linux_file_rename_utility) for bulk renaming of files in Linux! 

## Author:
BSFEMA

## Started:
2023-03-30

## Screenshot:
![screenshot](https://github.com/BSFEMA/linux_bulk_mkv_properties/raw/master/screenshot.png)

## Prerequisites:
You need to have MKVToolNix installed:  https://mkvtoolnix.download/downloads.html  Try running "mkvmerge --version" in terminal.  If that works, then you are good to go, otherwise install MKVToolNix

## Command Line Parameters:
There is just 1.  It is the folder path that will be used to start looking at the *.mkv files from.  If this value isn't provided, then the starting path will be where this application file is located.  The intention is that you can call this application from a context menu from a file browser (e.g. Nemo) and it would automatically load up that folder.

## Nemo Action:

You can create a nemo action file so that you can right-click in a folder and launch the linux_bulk_mkv_properties.py application from there.

Example (filename = "linux_bulk_mkv_properties.nemo_action") 

    [Nemo Action]
    Name=Linux Bulk MKV Properties
    Quote=double
    Exec=python3 "[PATH_TO]/linux_bulk_mkv_properties.py" %F
    Selection=any
    Extensions=any
    Icon-Name=python3

Save the "linux_bulk_mkv_properties.nemo_action" file to "~/.local/share/nemo/actions".

Context menus might be possible for other file managers, but that will be up to you to figure out ;)

## Resources:
https://mkvtoolnix.download/doc/mkvextract.html