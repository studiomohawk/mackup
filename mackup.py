#!/usr/bin/env python
"""Keep you Mac application settings in sync"""

###########
# Imports #
###########


import argparse
import base64
import os.path
import shutil
import sys
import tempfile


#################
# Configuration #
#################


SUPPORTED_APPS = {
    'Bash': ['.bash_aliases',
             '.bash_logout',
             '.bashrc',
             '.profile'],

    'Git': ['.gitconfig'],

    'Mercurial': ['.hgrc'],

    'S3cmd': ['.s3cfg'],

    'X11': ['.Xresources'],
}


#############
# Constants #
#############


# Current version
VERSION = '0.1'

# Mode used to backup files to Dropbox
BACKUP_MODE = 'backup'

# Mode used to restore files from Dropbox
RESTORE_MODE = 'restore'


###########
# Classes #
###########


class ApplicationProfile(object):
    """Instantiate this class with application specific data"""

    def __init__(self, mackup, files):
        """
        Create an ApplicationProfile instance

        Args:
            mackup (Mackup)
            files (list)
        """
        assert isinstance(mackup, Mackup)
        assert isinstance(files, list)

        self.mackup = mackup
        self.files = files

    def backup(self):
        """
        Backup the application config files

        Algorithm:
            if exists home/file
              if home/file is a real file
                if exists mackup/file
                  are you sure ?
                  if sure
                    rm mackup/file
                    mv home/file mackup/file
                    link mackup/file home/file
                else
                  mv home/file mackup/file
                  link mackup/file home/file
        """

        # For each file used by the application
        for filename in self.files:
            # Get the full path of each file
            filepath = os.path.join(os.environ['HOME'], filename)
            mackup_filepath = os.path.join(self.mackup.mackup_folder, filename)

            # If the file exists and is not already a link pointing to Mackup
            if (os.path.isfile(filepath)
                and not (os.path.islink(filepath)
                         and os.path.isfile(mackup_filepath)
                         and not os.path.islink(mackup_filepath)
                         and os.path.samefile(filepath, mackup_filepath))):

                print "Backing up {}...".format(filename)

                # Check if we already have a backup
                if os.path.isfile(mackup_filepath):
                    # Ask the user if he really want to replace it
                    if confirm("A file named {} already exists in the backup."
                               "\nOr you sure that your want to replace it ?"
                               .format(mackup_filepath)):
                        # Delete the file in Mackup
                        delete(mackup_filepath)
                        # Move the user's file to the backup
                        shutil.copy(filepath, mackup_filepath)
                        # Delete the file in the home
                        delete(filepath)
                        # Link the backuped file to its original place
                        os.symlink(mackup_filepath, filepath)
                else:
                    # Move the user's file to the backup
                    shutil.copy(filepath, mackup_filepath)
                    # Delete the file in the home
                    delete(filepath)
                    # Link the backuped file to its original place
                    os.symlink(mackup_filepath, filepath)

    def restore(self):
        """
        Restore the application config files

        Algorithm:
            if exists mackup/file
              if exists home/file
                are you sure ?
                if sure
                  rm home/file
                  link mackup/file home/file
              else
                link mackup/file home/file
        """

        # For each file used by the application
        for filename in self.files:
            # Get the full path of each file
            mackup_filepath = os.path.join(self.mackup.mackup_folder, filename)
            home_filepath = os.path.join(os.environ['HOME'], filename)

            # If the file exists and is not already pointing to the mackup file
            if (os.path.isfile(mackup_filepath)
                and not (os.path.isfile(home_filepath)
                         and os.path.samefile(mackup_filepath,
                                              home_filepath))):

                print "Restoring {}...".format(filename)

                # Check if there is already a file in the home folder
                if os.path.isfile(home_filepath):
                    if confirm("You already have a file named {} in your home."
                               "\nDo you want to replace it with your backup ?"
                               .format(filename)):
                        delete(home_filepath)
                        os.symlink(mackup_filepath, home_filepath)
                else:
                    os.symlink(mackup_filepath, home_filepath)


class Mackup(object):
    """Main Mackup class"""

    def __init__(self):
        """Mackup Constructor"""
        try:
            self.dropbox_folder = get_dropbox_folder_location()
        except IOError:
            error(("Unable to find the Dropbox folder."
                   " If Dropbox is not installed and running, go for it on"
                   " <http://www.dropbox.com/>"))

        self.mackup_folder = self.dropbox_folder + '/Mackup'
        self.temp_folder = tempfile.mkdtemp(prefix="mackup_tmp_")

    def _check_for_usable_environment(self):
        """Check if the current env is usable and has everything's required"""

        # Do we have a home folder ?
        if not os.path.isdir(self.dropbox_folder):
            error(("Unable to find the Dropbox folder."
                   " If Dropbox is not installed and running, go for it on"
                   " <http://www.dropbox.com/>"))

    def check_for_usable_backup_env(self):
        """Check if the current env can be used to back up files"""
        self._check_for_usable_environment()
        self.create_mackup_home()

    def check_for_usable_restore_env(self):
        """Check if the current env can be used to restore files"""
        self._check_for_usable_environment()

        if not os.path.isdir(self.mackup_folder):
            error("Unable to find the Mackup folder: {}\n"
                  "You might want to backup some files or get your Dropbox"
                  " folder synced first."
                  .format(self.mackup_folder))

    def clean_temp_folder(self):
        """Delete the temp folder and files created while running"""
        shutil.rmtree(self.temp_folder)

    def create_mackup_home(self):
        """If the Mackup home folder does not exist, create it"""
        if not os.path.isdir(self.mackup_folder):
            if confirm("Mackup needs a folder to store your configuration "
                       " files\nDo you want to create it now ? <{}>"
                       .format(self.mackup_folder)):
                os.mkdir(self.mackup_folder)
            else:
                error("Mackup can't do anything without a home =(")


####################
# Useful functions #
####################


def confirm(question):
    """
    Ask the user if he really want something to happen

    Args:
        question(str): What can happen

    Returns:
        (boolean): Confirmed or not
    """
    while True:
        answer = raw_input(question + ' <Yes|No>')
        if answer == 'Yes':
            confirmed = True
            break
        if answer == 'No':
            confirmed = False
            break

    return confirmed


def delete(filepath):
    """
    Delete the given file. Should support undelete later on.

    Args:
        filepath (str): Absolute full path to a file. e.g. /path/to/file
    """
    os.remove(filepath)


def error(message):
    """
    Throw an error with the given message and immediatly quit.

    Args:
        message(str): The message to display.
    """
    sys.exit("Error: {}".format(message))


def parse_cmdline_args():
    """
    Setup the engine that's gonna parse the command line arguments

    Returns:
        (argparse.Namespace)
    """

    # Format some epilog text
    epilog = "Supported applications:\n"
    for app in sorted(SUPPORTED_APPS.iterkeys()):
        epilog = epilog + "  - {}\n".format(app)
    epilog += "\nMackup requires a fully synced Dropbox folder."

    # Setup the global parser
    parser = argparse.ArgumentParser(
        description=("Mackup {}\n"
                     "Keep you application settings in sync."
                     .format(VERSION)),
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    # Add the required arg
    parser.add_argument("mode",
                        choices=[BACKUP_MODE, RESTORE_MODE],
                        help=("Backup your conf files to Dropbox or restore"
                              " your files locally from Dropbox"))

    # Parse the command line and return the parsed options
    return parser.parse_args()


def get_dropbox_folder_location():
    """
    Try to locate the Dropbox folder

    Returns:
        (str) Full path to the current Dropbox folder
    """
    host_db_path = os.environ['HOME'] + '/.dropbox/host.db'
    with open(host_db_path, 'r') as f:
        data = f.read().split()
    dropbox_home = base64.b64decode(data[1])

    return dropbox_home


################
# Main Program #
################


def main():
    """Main function"""

    # Get the command line arg
    args = parse_cmdline_args()

    mackup = Mackup()

    if args.mode == BACKUP_MODE:
        # Check the env where the command is being run
        mackup.check_for_usable_backup_env()

        for app_name in SUPPORTED_APPS:
            app = ApplicationProfile(mackup, SUPPORTED_APPS[app_name])
            app.backup()

    elif args.mode == RESTORE_MODE:
        # Check the env where the command is being run
        mackup.check_for_usable_restore_env()

        for app_name in SUPPORTED_APPS:
            app = ApplicationProfile(mackup, SUPPORTED_APPS[app_name])
            app.restore()

    else:
        raise ValueError("Unsupported mode: {}".format(args.mode))

    # Delete the tmp folder
    mackup.clean_temp_folder()

if __name__ == "__main__":
    main()