import re, sys
import xbmc, xbmcvfs, xbmcgui

def change_theme():    

    dialog = xbmcgui.Dialog()

    # Define your available theme options as tuples: (Display Label, Logo Image Path, Diffuse Hex Code)
    logo_options = [
        ("Red (Default)",                   "home/bingie_logo.png",                     "e50914"),
        ("Yellow",                          "home/bingie_logo_yellow.png",              "e5c709"),
        ("Yellow (Smiler)",                 "home/bingie_logo_yellow2.png",             "ffec00"),
        ("Blue (Prime Video)",              "home/bingie_logo_blue.png",                "0679fd"),
        ("Pink (iPlayer)",                  "home/bingie_logo_pink.png",                "ff4c98"),
        ("Turquoise",                       "home/bingie_logo_turquoise.png",           "45b8ac"),
        ("Sunlight",                        "home/bingie_logo_sunlight.png",            "edd59e"),
        ("Orange",                          "home/bingie_logo_orange.png",              "ffa00a"),
        ("Orange (Rec Room)",               "home/bingie_logo_orange2.png",             "ff6727"),
        ("Green",                           "home/bingie_logo_green.png",               "1dd72f"),
        ("Light Green (Channel 4)",         "home/bingie_logo_light_green.png",         "aaff89"),
        ("Aqua (Kodi)",                     "home/bingie_logo_aqua.png",                "2ba7d7"),
        ("Aqua 2",                          "home/bingie_logo_aqua2.png",               "01ffff"),
        ("Peach Fuzz",                      "home/bingie_logo_peach_fuzz.png",          "ffbe98"),
        ("Purple",                          "home/bingie_logo_purple.png",              "a515ff"),
        ("Purple (GOG)",                    "home/bingie_logo_purple2.png",             "6900d1"),
        ("Dedflix",                         "home/bingie_logo_dedflix.png",             "c20c0c"),
        ("Dedflix (Orange)",                "home/bingie_logo_dedflix2.png",            "fb7e07"),
        ("Sledflix",                        "home/bingie_logo_sledflix.png",            "e8372d"),        
        ("Nedflix",                         "home/bingie_logo_nedflix.png",             "1ed760")
    ]
    
    # Build a list of display labels for the selection dialog.
    display_labels = [option[0] for option in logo_options]
    
    # Translate the file path for the IncludesHomeBingie.xml file.
    file_path = xbmcvfs.translatePath("special://home/addons/skin.nedflix/1080i/IncludesHomeBingie.xml")
    if not xbmcvfs.exists(file_path):
        dialog.ok("Error", "File not found:\n" + file_path)
        return
    
    # Translate the file path for the Theme Variable.theme file.
    theme_file_path = xbmcvfs.translatePath("special://home/addons/skin.nedflix/extras/skinthemes/Update Theme.theme")
    
    # Translate the file path for the Custom_1159_MPAATopBar.xml file.
    custom_file_path = xbmcvfs.translatePath("special://home/addons/skin.nedflix/1080i/Custom_1159_MPAATopBar.xml")
    
    # Define the list of theme data keys that should get updated in the theme file.
    # Add or remove keys as needed.
    keys_to_update = [
        "WatchedIndicator.Watched.Color.base",
        "BingieProgressBarColor.base",
        "WatchedIndicator.Episodes.Color",
        "SpinnerTextureColor.base"
        "LineUnderMenuIconsColor.base",
        "lineundermenuiconscolor",
        "BingieOSDProgressBarColor.base",
        "BingieProgressBarColor",
        "WatchedIndicator.Episodes.Color.base",
        "WatchedIndicator.Watched.Color",
        "OSDVolumeButtonColor.base",
        "BingieNewEpisodesTagColor.base",
        "WatchedIndicator.Progress.Color.base",
        "bingienewepisodestagcolor",
        "ActiveSpinControlColor",
        "SpinnerTextureColor",
        "WatchedIndicator.Progress.Color",
        "ActiveSpinControlColor.base",
        "OSDBufferingSpinnerColor.base",
        "bingieosdprogressbarcolor",
        "OSDVolumeButtonColor",
        "osdbufferingspinnercolor",
        
        # You can add additional keys here if needed.
    ]
    
    # Loop continuously so the theme-selection dialog remains available until cancelled.
    while True:
        choice = dialog.select("Choose Theme", display_labels)
        if choice == -1:
            break  # Exit the function if the user cancels.
            
        # Map the selection to the chosen values.
        new_logo_path = logo_options[choice][1]
        new_diffuse_hex = logo_options[choice][2]
        
        try:
            # -----------------------------------
            # Update IncludesHomeBingie.xml
            # -----------------------------------
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            if len(lines) < 835:
                dialog.ok("Error", "The file does not have at least 835 lines.")
                continue
            
            # Update the Bingie Logo line (assumed line 820; index 819)
            lines[819] = re.sub(r'(<texture>).*?(</texture>)', r'\1' + new_logo_path + r'\2', lines[819])
            # Update the Bingie Logo line (assumed line 832; index 831)
            lines[831] = re.sub(r'(<texture>).*?(</texture>)', r'\1' + new_logo_path + r'\2', lines[831])
            # Update the diffuse color line (assumed line 847; index 846)
            lines[846] = re.sub(r'(colordiffuse=")[0-9A-Fa-f]{8}(")', r'\1' + "ff" + new_diffuse_hex + r'\2', lines[846])
            
            # Write the updated contents back to IncludesHomeBingie.xml.
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            
            # -----------------------------------
            # Update Custom_1159_MPAATopBar.xml (line 36)
            # -----------------------------------
            if xbmcvfs.exists(custom_file_path):
                with open(custom_file_path, "r", encoding="utf-8") as f:
                    custom_lines = f.readlines()
                
                if len(custom_lines) < 36:
                    dialog.ok("Error", "Custom_1159_MPAATopBar.xml does not have at least 36 lines.")
                else:
                    # Using index 35 (line 36) modify the colordiffuse tag.
                    # The expected tag is: <colordiffuse>FFE50914</colordiffuse>
                    # We update the inner value to "FF" + new_diffuse_hex (in uppercase).
                    custom_lines[35] = re.sub(r"(<colordiffuse>)[^<]*(</colordiffuse>)",
                                              r"\1" + "FF" + new_diffuse_hex.upper() + r"\2",
                                              custom_lines[35])
                    
                    # Write back the updated lines.
                    with open(custom_file_path, "w", encoding="utf-8") as f:
                        f.writelines(custom_lines)
            
            # -----------------------------------
            # Update the Theme Variable.theme file if it exists.
            # -----------------------------------
            if xbmcvfs.exists(theme_file_path):
                with open(theme_file_path, "r", encoding="utf-8") as f:
                    theme_content = f.read()
                
                # For each key, update its value within the tuple.
                for key in keys_to_update:
                    # Construct a regex from the key.
                    # Pattern matches tuple of the form: ('string', 'KEY', 'XXXXXXXX')
                    pattern = r"(\('string',\s*'" + re.escape(key) + r"'\s*,\s*')[0-9A-Fa-f]{8}('.*\))"
                    replacement = r"\1" + "ff" + new_diffuse_hex + r"\2"
                    theme_content = re.sub(pattern, replacement, theme_content)
                
                with open(theme_file_path, "w", encoding="utf-8") as f:
                    f.write(theme_content)
            
            # Refresh the skin automatically.
            xbmc.executebuiltin("ReloadSkin()")
            xbmc.executebuiltin("RunScript(script.skin.helper.skinbackup,action=colorthemes)")
            sys.exit()
        
        except Exception as e:
            xbmc.log("Error updating Bingie theme: " + str(e), xbmc.LOGERROR)
            dialog.ok("Error", "Failed to update Bingie theme.")