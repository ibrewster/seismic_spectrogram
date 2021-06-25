#!/usr/bin/env python3
import subprocess
import sys

import gen_config
import gen_station_config

if __name__ == "__main__":
    assume_yes = False
    if len(sys.argv) > 1 and sys.argv[1] == '-y':
        assume_yes = True
    print("Welcome to the spectrogram web setup script!")
    print("This script will walk you through the steps needed to get up and running.")
    cont = 'y' if assume_yes else 'invalid'
    while cont.lower() not in ['', 'y', 'n']:
        cont = input("Continue? [Y/n]: ")

    if cont.lower() == 'n':
        exit()

    print("Installing base requirements")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade",
                           "-r", "requirements.txt"])

    gen_base_conf = 'y' if assume_yes else 'invalid'
    while gen_base_conf.lower() not in ('', 'y', 'n'):
        gen_base_conf = input("Generate new config.ini file? [Y/n]: ")

    if gen_base_conf.lower() != 'n':
        gen_config.main()
        print("specgen/config.ini has been generated.")
        print("Please verify the contents of this file and edit")
        print("To suit your enviroment before continuing.")
        if not assume_yes:
            input("Hit return when ready to continue.")

    gen_station = 'y' if assume_yes else 'invalid'
    while gen_station.lower() not in ('', 'n', 'y'):
        gen_station = input("Generate new station config file? [Y/n]: ")

    if gen_station.lower() != 'n':
        print("Please verify that the settings and VOLCS list at the top of the")
        print("gen_station_config.py file are as desired")
        if not assume_yes:
            input("Hit return when ready to continue")

        print("Generating station config. This may take a few minutes...")
        gen_station_config.generate_stations()
        print("Station config generated")

    print()
    print("Hooks are user-supplied scripts that operate on the retrieved and processed")
    print("data to provide additional functionality. Some hooks may require additional")
    print("modules to be installed in order to function.")
    print()
    print("This step is optional, if a module required for a hook is not installed")
    print("that hook will simply not be run.")
    install_hooks = 'y' if assume_yes else 'invalid'
    while install_hooks.lower() not in ('', 'n', 'y'):
        install_hooks = input("Install required modules for hooks? [Y/n]: ")

    if install_hooks.lower() != 'n':
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade",
                               "-r", "specgen/hooks/requirements.txt"])

    print()
    print("Your install is set up and ready to go. To generate spectrograms and")
    print('run hooks (if installed), run the "run_generate" script. You will')
    print('typically want to run this as a cron job every 10 minutes.')
    print()
    print("The web interface can be launched in development mode by running run_web.py")
    print("For production use, it is recommended that you instead use a production-")
    print("quality WSGI server behind a web server such as Nginx or Apache")
    print("See https://flask.palletsprojects.com/en/2.0.x/deploying/ for more information")
