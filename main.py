import zipfile, configparser
from io import BytesIO
from os.path import isfile, join, isdir
from os import listdir
import shutil
import tempfile
import SiteHandler
import packages.requests as requests
import argparse

import warnings
warnings.filterwarnings("ignore")

def confirmExit():
    input('\nPress the Enter key to exit')
    exit(0)

class AddonUpdater:
    def __init__(self):
        print('')

        # Read config file
        if not isfile('config.ini'):
            print('Failed to read configuration file. Are you sure there is a file called "config.ini"?\n')
            confirmExit()

        config = configparser.ConfigParser()
        config.read('config.ini')

        try:
            self.WOW_ADDON_LOCATION = config['WOW ADDON UPDATER']['WoW Addon Location']
            self.INSTALLED_VERS_FILE = config['WOW ADDON UPDATER']['Installed Versions File']
        except Exception:
            print('Failed to parse configuration file.')

        if not isfile(self.INSTALLED_VERS_FILE):
            open(self.INSTALLED_VERS_FILE, 'w').close() # Create installed versions file since it doesn't exist

        return

    def install(self, addon_list):
        for addon_url in addon_list:
            addon_url = addon_url.rstrip('\n')

            if not addon_url:
                continue
            if '|' in addon_url: # Expected input format: "mydomain.com/myzip.zip" or "mydomain.com/myzip.zip|subfolder"
                subfolder = addon_url.split('|')[1]
                addon_url = addon_url.split('|')[0]
            else:
                subfolder = ''

            addonName = SiteHandler.getAddonName(addon_url)
            currentVersion = SiteHandler.getCurrentVersion(addon_url)
            if currentVersion is None:
                currentVersion = 'Not Available'
            installedVersion = self.getInstalledVersion(addon_url)
            if not currentVersion == installedVersion:
                print(addonName + '\t' + currentVersion + '\tInstalled/Updated')
                ziploc = SiteHandler.findZiploc(addon_url)
                install_success = False
                install_success = self.getAddon(ziploc, subfolder) # install_success[1] is list of subfolders
                if install_success[0] is True and currentVersion is not '':
                    self.setInstalledVersion(addonName, addon_url, currentVersion, install_success[1])
            else:
                print(addonName + '\t' + currentVersion + '\tUp-to-date')

    def getAddon(self, ziploc, subfolder):
        if ziploc == '':
            return False
        try:
            r = requests.get(ziploc, stream=True)
            z = zipfile.ZipFile(BytesIO(r.content))
            self.extract(z, ziploc, subfolder)
            return (True, self.getFolderNames(z))
        except Exception:
            print('Failed to download or extract zip file for addon. Skipping...\n')
            return (False, [])
    
    def getFolderNames(self, zip):
        parent_folders = []
        for i in zip.namelist():
            i = i.split('/')[0]
            if i not in parent_folders:
                parent_folders.append(i)
        return parent_folders

    def extract(self, zip, url, subfolder):
        if subfolder == '':
            zip.extractall(self.WOW_ADDON_LOCATION)
        else: # Pull subfolder out to main level, remove original extracted folder
            try:
                with tempfile.TemporaryDirectory() as tempDirPath:
                    zip.extractall(tempDirPath)
                    extractedFolderPath = join(tempDirPath, listdir(tempDirPath)[0])
                    subfolderPath = join(extractedFolderPath, subfolder)
                    shutil.copytree(subfolderPath, join(self.WOW_ADDON_LOCATION, subfolder))
            except Exception as ex:
                print('Failed to get subfolder ' + subfolder)

    def getInstalledVersion(self, addonpage):
        installedVers = configparser.ConfigParser()
        installedVers.read(self.INSTALLED_VERS_FILE)
        try:
            return installedVers[addonpage]['version']
        except Exception:
            return 'version not found'

    def setInstalledVersion(self, addonname, addonpage, currentVersion, folders):
        config = configparser.ConfigParser()
        config.read(self.INSTALLED_VERS_FILE)
        try:
            config.get(addonpage, 'name')       # addon name
            config.get(addonpage, 'version')    # addon version
            config.get(addonpage, 'folders')    # addon subfolders
        except:
            config.add_section(addonpage)                   # Otherwise create a new section
        config.set(addonpage, 'name', addonname)            # Set addon name
        config.set(addonpage, 'version', currentVersion)    # Set addon version
        config.set(addonpage, 'folders', str(folders)[1 : -1].replace("'","").replace(" ",""))  # List all subfolders
        with open(self.INSTALLED_VERS_FILE, 'w') as installedVersFile:
            config.write(installedVersFile)

    def uninstall(self, addon_list):
        config = configparser.ConfigParser()                        # Read INSTALLED_VERS_FILE
        config.read(self.INSTALLED_VERS_FILE)
        for to_del in addon_list:
            print("Uninstall {} ...".format(to_del))
            for folder in config.get(to_del, 'folders').split(','): # Proceed to delete all addon folders by reading
                if (isdir(join(self.WOW_ADDON_LOCATION, folder))):  # the INSTALLED_VERS_FILE
                    #print("\t{}".format(folder))
                    shutil.rmtree(join(self.WOW_ADDON_LOCATION, folder))
                else:
                    print("\tCannot find {}".format(join(self.WOW_ADDON_LOCATION, folder)))
            config.remove_section(to_del)                           # Remove the addon entry from INSTALLED_VERS_FILE
            with open(self.INSTALLED_VERS_FILE, 'w') as installedVersFile:
                config.write(installedVersFile)
'''
def main():
    addonupdater = AddonUpdater()
    addonupdater.install()
    addonupdater.uninstallAddon()
    return
'''
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='World of Addons - An open source World of Warcraft addon manager')

    # python arg.py -l url1 url2 url3
    parser.add_argument('-l','--list', nargs='+', required=True, help='<Required> Specifies list of addon URLs.')
    
    # python arg.py -l url1 url2 url3 -i
    parser.add_argument('-i', '--install', action='store_true', help='<Flag> If set script will update or install all addons specified by -l.')

    # python arg.py -l url1 url2 url3 --uninstall
    parser.add_argument('--uninstall', action='store_true', help='<Flag> If set script will uninstall all addons specified by -l.')

    # python arg.py -l url1 url2 url3 -c
    parser.add_argument('-c', '--check', action='store_true', help='<Flag> If set script will check if update is available for specified addon.')

    args = parser.parse_args()

    addonupdater = AddonUpdater()

    if (args.check == True):
        print("Checking the following addons for updates:\n\t{}".format(args.list))

    if (args.install == True and args.uninstall == False):
        addonupdater.install(args.list)

    if (args.install == False and args.uninstall == True):
        addonupdater.uninstall(args.list)
