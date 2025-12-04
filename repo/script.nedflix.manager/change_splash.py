import os
import xbmcaddon
import xbmcgui
import xbmcvfs

addon = xbmcaddon.Addon()
addon_path = addon.getAddonInfo('path')
icon_path = os.path.join(addon_path, 'icon.png')  # or 'icon.svg' if you use SVG


def apply_splash(screen_name_png):
    addon = xbmcaddon.Addon()
    addon_path = addon.getAddonInfo('path')

    # Kodi splash source (png)
    source_splash = os.path.join(addon_path, 'media', 'kodi_splash_screens', screen_name_png)
    dest_splash = xbmcvfs.translatePath('special://home/media/splash.png')

    # Bingie splash source (jpg)
    base_name = os.path.splitext(screen_name_png)[0]
    bingie_file = base_name + '.jpg'
    source_bingie = os.path.join(addon_path, 'media', 'bingie_settings_splash_screens', bingie_file)
    dest_bingie = xbmcvfs.translatePath('special://home/addons/skin.nedflix/extras/media/backgrounds/settings_bingie.jpg')

    # NEW: copy PNG to bingie_splash.png
    dest_bingie_png = xbmcvfs.translatePath('special://home/addons/skin.nedflix/extras/media/bingie_splash.png')

    if not xbmcvfs.exists(source_splash):
        xbmcgui.Dialog().notification('Splash Screen', 'Selected splash image for Kodi not found!', xbmcgui.NOTIFICATION_ERROR)
        return

    if not xbmcvfs.exists(source_bingie):
        xbmcgui.Dialog().notification('Splash Screen', 'Corresponding Bingie splash image not found!', xbmcgui.NOTIFICATION_ERROR)
        return

    try:
        # Copy Kodi splash png
        if xbmcvfs.exists(dest_splash):
            xbmcvfs.delete(dest_splash)
        xbmcvfs.copy(source_splash, dest_splash)

        # Copy Bingie splash jpg (renamed)
        if xbmcvfs.exists(dest_bingie):
            xbmcvfs.delete(dest_bingie)
        xbmcvfs.copy(source_bingie, dest_bingie)

        # NEW: Copy PNG to bingie_splash.png
        if xbmcvfs.exists(dest_bingie_png):
            xbmcvfs.delete(dest_bingie_png)
        xbmcvfs.copy(source_splash, dest_bingie_png)

        xbmcgui.Dialog().notification('Woohoo!', 'Splash screen changed!', icon=icon_path)
    except Exception as e:
        xbmcgui.Dialog().notification('Error', str(e), xbmcgui.NOTIFICATION_ERROR)


def choose_splash_screen():
    addon = xbmcaddon.Addon()
    addon_path = addon.getAddonInfo('path')
    splash_folder = os.path.join(addon_path, 'media', 'kodi_splash_screens')
    files = [f for f in xbmcvfs.listdir(splash_folder)[1] if f.endswith('.png')]

    if not files:
        xbmcgui.Dialog().notification('Splash Screen', 'No splash images found.', xbmcgui.NOTIFICATION_ERROR)
        return

    choice = xbmcgui.Dialog().select('Choose Splash Screen', files)
    if choice >= 0:
        apply_splash(files[choice])
