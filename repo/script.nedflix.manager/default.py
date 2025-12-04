import os
import re
import time
import sys
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import json

import home_widgets_ordering
import rename_delete_widgets
from change_widget_size import change_widget_size
from change_splash import choose_splash_screen
from change_theme import change_theme 

# Friendly mappings for hubs (used for display)
HUB_FRIENDLY_MAPPING = {
    "moviesaddon": "Films",
    "tvshowsaddon": "TV",
    "myhub": "Animation",
    "newaddon": "New & Popular",
    "music": "Wrestling"
}

def get_kodi_userdata_path():
    kodi_base_path = xbmcvfs.translatePath("special://userdata")
    return os.path.join(kodi_base_path, "addon_data", "skin.nedflix", "settings.xml")

def extract_hub_names(xml_file):
    """
    Extract unique hub IDs from the settings.xml file.
    Returns both the raw hub IDs and a friendly display list.
    """
    try:
        with open(xml_file, 'r', encoding='utf-8') as f:
            content = f.read()
        pattern = re.compile(r'<setting id="(bingiehub-[^-]+)-\d+\.label" type="string">')
        hubs = pattern.findall(content)
        hubs = sorted(list(set(hubs)))
        hubs = [hub for hub in hubs if not hub.endswith("local") and hub not in ["bingiehub-customhub", "bingiehub-somethingaddon"]]
        display_list = []
        for hub in hubs:
            hub_key = hub.replace("bingiehub-", "")
            display_name = HUB_FRIENDLY_MAPPING.get(hub_key, hub_key)
            display_list.append(display_name)
        return hubs, display_list
    except Exception:
        return [], []

def extract_widget_names(xml_file, hub):
    """
    Extract widget names for a given hub from the settings.xml file.
    Assumes a maximum of 10 widget slots.
    """
    try:
        with open(xml_file, 'r', encoding='utf-8') as f:
            content = f.read()
        widget_names = []
        for i in range(10):
            widget_id = 510 + i * 10 if i < 9 else 5100
            label_pattern = rf'<setting id="{hub}-{widget_id}\.label" type="string">(.*?)</setting>'
            match = re.search(label_pattern, content)
            if match and match.group(1).strip():
                widget_names.append(match.group(1).strip())
            else:
                widget_names.append(f"Slot {i+1} (No widget assigned)")
        return widget_names
    except Exception:
        return []

def clear_hub_properties_json(properties_file, slot_index):
    """
    Clears all property values for a home widget slot in the properties JSON file.
    Deletes the text within the fourth element of each relevant entry.
    """
    try:
        with open(properties_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        suffix = "" if slot_index == 1 else f".{slot_index - 1}"
        keys_to_clear = ["widget", "widgetName", "widgetType", "widgetTarget", "widgetPath"]

        for entry in data:
            if isinstance(entry, list) and len(entry) == 4:  # Ensure the entry is correctly formatted
                if entry[0] == "mainmenu" and entry[1] == "10000":  # Target home widgets
                    for key in keys_to_clear:
                        if entry[2] == f"{key}{suffix}":  
                            entry[3] = ""  # Clear only the fourth value in the list

        # Save the updated JSON file
        with open(properties_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    except Exception as e:
        xbmc.log("Error clearing home widget properties: " + str(e), xbmc.LOGERROR)
        xbmcgui.Dialog().ok("Error", "Failed to clear home widget properties.")

def update_hub_properties_json(properties_file, slot_index, new_value, is_home_widget=False):
    """
    Updates the widgetName in the properties JSON file.
    Ensures that home widget updates do not affect hub widgets by scoping updates.
    """
    try:
        with open(properties_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        suffix = "" if slot_index == 1 else f".{slot_index - 1}"
        target_key = "widgetName" + suffix
        updated = False

        for entry in data:
            if isinstance(entry, list) and len(entry) >= 4:
                if entry[0] == "mainmenu" and entry[1] == "10000":
                    if is_home_widget:
                        # Restrict updates ONLY to home widgets (should not affect hubs)
                        if not entry[2].startswith("hub-"):
                            if entry[2] == target_key:
                                entry[3] = new_value
                                updated = True
                    else:
                        # Restrict updates ONLY to hub widgets
                        if entry[2].startswith("hub-"):
                            if entry[2] == target_key:
                                entry[3] = new_value
                                updated = True

        if not updated:
            xbmcgui.Dialog().ok("Warning", "No matching JSON widgetName entry was found.")

        with open(properties_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        xbmc.log("Error updating hub JSON properties: " + str(e), xbmc.LOGERROR)
        xbmcgui.Dialog().ok("Error", "Failed to update hub JSON properties.")
    """
    Directly updates the widgetName value for a hub widget slot in the JSON properties file.
    For slot 1, the key is "widgetName"; for slot i (i>=2) it is "widgetName.{i-1}".
    """
    try:
        with open(properties_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        suffix = "" if slot_index == 1 else f".{slot_index - 1}"
        target_key = "widgetName" + suffix
        updated = False
        for entry in data:
            if isinstance(entry, list) and len(entry) >= 4:
                if entry[0] == "mainmenu" and entry[1] == "10000" and entry[2] == target_key:
                    entry[3] = new_value
                    updated = True
        if not updated:
            xbmcgui.Dialog().ok("Warning", "No matching JSON widgetName entry was found.")
        with open(properties_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        xbmc.log("Error updating hub JSON properties: " + str(e), xbmc.LOGERROR)
        xbmcgui.Dialog().ok("Error", "Failed to update hub JSON properties.")

def remove_widget_includes(skin_xml_file, widget_id):
    """
    Removes <include> blocks from the skin XML file that contain a 
    <param name="widgetid" value="widget_id" /> element.
    """
    try:
        with open(skin_xml_file, "r", encoding="utf-8") as f:
            xml_content = f.read()
        pattern = rf"<include\b(?:(?!<\/include>).)*?<param\s+name=\"widgetid\"\s+value=\"{re.escape(widget_id)}\".*?<\/include>"
        new_xml, count = re.subn(pattern, "", xml_content, flags=re.DOTALL | re.IGNORECASE)
        if count == 0:
            xbmcgui.Dialog().ok("Warning", f"No matching include blocks found for widgetid {widget_id}.")
        with open(skin_xml_file, "w", encoding="utf-8") as f:
            f.write(new_xml)
    except Exception as e:
        xbmc.log("Error removing widget includes: " + str(e), xbmc.LOGERROR)
        xbmcgui.Dialog().ok("Error", "Failed to remove widget includes.")

def reorder_hub_widgets(selected_hub, settings_file):
    """
    Reorders widgets for a given hub by swapping widget settings in the XML file.
    """
    while True:
        widgets = extract_widget_names(settings_file, selected_hub)
        if not widgets:
            xbmcgui.Dialog().ok("Error", "No widgets found for the selected hub.")
            return
        dlg = xbmcgui.Dialog()
        while True:
            src = dlg.select("Select widget to move", widgets)
            if src == -1:
                return
            tgt = dlg.select("Select target slot", widgets, preselect=src)
            if tgt == -1 or src == tgt:
                break
            reorder_widget(settings_file, selected_hub, src, tgt)
            # Refresh the widget order after swap.
            widgets = extract_widget_names(settings_file, selected_hub)

def reorder_widget(xml_file, hub, source_index, target_index):
    """
    Swaps the settings for two widget slots within the specified hub.
    """
    try:
        with open(xml_file, 'r', encoding='utf-8') as f:
            content = f.read()
        widget_id_source = 510 + source_index * 10 if source_index < 9 else 5100
        widget_id_target = 510 + target_index * 10 if target_index < 9 else 5100
        keys = ["path", "label", "sortorder", "sortby", "LocalizedSortOrder", "LocalizedSortBy", "target"]
        for key in keys:
            pattern_src = re.compile(rf'(<setting id="{hub}-{widget_id_source}\.{key}" type="string">)(.*?)(</setting>)')
            pattern_tgt = re.compile(rf'(<setting id="{hub}-{widget_id_target}\.{key}" type="string">)(.*?)(</setting>)')
            src_match = pattern_src.search(content)
            tgt_match = pattern_tgt.search(content)
            if src_match and tgt_match:
                src_val = src_match.group(2)
                tgt_val = tgt_match.group(2)
                content = content.replace(src_match.group(0),
                                          f'{src_match.group(1)}{tgt_val}{src_match.group(3)}')
                content = content.replace(tgt_match.group(0),
                                          f'{tgt_match.group(1)}{src_val}{tgt_match.group(3)}')
        with open(xml_file, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception as e:
        xbmc.log(f"[Reorder Hub Widgets] Failed to swap widget values: {e}", xbmc.LOGERROR)

def reorder_widgets_menu(settings_file):
    """
    Displays a menu for moving widgets between Home and Hub.
    For Home, calls the home widget ordering module.
    For Hubs, uses the settings.xml file.
    """
    while True:
        groups = ["Home"]
        hubs, hubs_display = extract_hub_names(settings_file)
        if hubs:
            for hub, disp in zip(hubs, hubs_display):
                groups.append(disp)
        sel_group = xbmcgui.Dialog().select("Select hub for moving widgets", groups)
        if sel_group == -1:
            break
        if sel_group == 0:
            # Launch the home widget ordering module.
            home_widgets_ordering.run()
        else:
            selected_hub = hubs[sel_group - 1]
            reorder_hub_widgets(selected_hub, settings_file)
    
def refresh_skin():
    xbmc.executebuiltin("ReloadSkin()")

def save_and_close_kodi():
    xbmc.executebuiltin("RunAddon(plugin.close.kodi)")            

def widgets_main_menu():
    SETTINGS_FILE = get_kodi_userdata_path()  # Hub settings XML file
    HOME_WIDGETS_FILE = xbmcvfs.translatePath("special://home/addons/skin.nedflix/1080i/script-skinshortcuts-includes.xml")

    while True:
        options = [
            "Move Widgets",       
            "Rename Widgets",
            "Delete Widgets"
        ]
        choice = xbmcgui.Dialog().select("Manage Widgets", options)

        if choice == -1:
            break
        elif choice == 0:
            reorder_widgets_menu(SETTINGS_FILE)
        elif choice == 1:
            rename_delete_widgets.rename_widget(SETTINGS_FILE, HOME_WIDGETS_FILE)
        elif choice == 2:
            rename_delete_widgets.delete_widget(SETTINGS_FILE, HOME_WIDGETS_FILE) 

def main_menu():
    options = [
        "Change Theme",
        "Change Splash Screens",
        "Manage Widgets",        
        "Change Wrestling Widgets Size",  
        "Save and Refresh (Home Widgets)",
        "Save and Force Quit Kodi (All Widgets)"                
    ]
    return xbmcgui.Dialog().select("Nedflix Manager", options)

if __name__ == '__main__':
    SETTINGS_FILE = get_kodi_userdata_path()  # Hub settings XML file
    # Define the home widgets XML file manually
    HOME_WIDGETS_FILE = xbmcvfs.translatePath("special://home/addons/skin.nedflix/1080i/script-skinshortcuts-includes.xml")
    
    while True:
        choice = main_menu()
        if choice == -1:
            sys.exit()
        elif choice == 0:
            change_theme()
        elif choice == 1:
            choose_splash_screen()
        elif choice == 2:
            widgets_main_menu()        
        elif choice == 3:
            change_widget_size()
        elif choice == 4:
            refresh_skin()
            sys.exit()
        elif choice == 5:
            save_and_close_kodi()        
            