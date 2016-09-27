OpenBMC library

Testing
-------

You can create a virtual environment without installing to the Operating System.
Just do the following:

    [hamzy@hamzy-tp-w540 OpenBMC]$ (rm -rf devenv/; tox -e devenv)

Then, you can run the tool as follows:
    [hamzy@hamzy-tp-w540 OpenBMC]$ devenv/bin/openBmcTool --hostname 10.1.2.3 --user root --password passw0rd is_power ?
