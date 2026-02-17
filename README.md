BrickEdit-Interface is a tool to help users exploit BrickEdit's capabilities without any code knowledge, by providing a set of tools in a graphical interface.


# About Windows Defender

Windows Defenders believes the file is a virus because I did not pay hundreds of euros a month to get a certificate so it stop complaining. I cannot do anything about that. If you trust this software, ignore its warnings and whitelist it if it gets quarantined. If you do not trust this software, do not download it.


# How to compile yourself for newbies:

1. Download Python 3.13 at https://www.python.org/ftp/python/3.13.11/python-3.13.11-amd64.exe
2. Run the downloaded executable and install Python. Use default settings.
3. Download the source code on GitHub (in the releases page, download Source code (ZIP) for the latest version).
4. Extract the archive
5. Right click in a blank spot in the directory where `main.py` is. Then click "Open in Terminal" or "Open in Powershell"
6. Ensure the right version of python is installed by running `python --version`. If it does not work, try replacing `python` with `py` or `python3`. You will also have to do this for later commands including `python`
7. Create a virtual environment by running `python -m venv .venv`
8. Install requirements by running `python -m pip install -r requirements.txt`. You can see what this command will install by opening `requirements.txt`
9. (Optional) Make sure you trust the source code you will compile. If you do not trust the `resources_rc.py` file:
    1. Delete `resources_rc.py`
    2. See the `resources.qrc` file. You will see all pathes lead to either a license or assets such as images.
    3. Run the following command: `pyside6-rcc resources.qrc -o resources_rc.py`
10. Do not close the terminal window. You should now be able to run `python main.py` by double clicking (and selecting Python 3.13 if necessary)
11. Compile the program by running `python -m nuitka --onefile --windows-console-mode=disable --windows-icon-from-ico="assets/icons/brickeditinterface.ico" --output-dir=compiled_build --enable-plugin=pyside6 main.py`. This will take a few minutes
12. You are done. The compiled build is available in `compiled_build/main.exe`. Run it by double click the executable.


# For developers:

Before using BrickEdit-Interface, you need to have the following dependencies installed:

```ps1
pip install -r requirements.txt
```

BrickEdit-Interface uses Qt Resource Files (.qrc) to bundle resources such as icons and images.

When adding assets, remember to save the file and run the following command to compile the .qrc file into a .py file: `pyside6-rcc resources.qrc -o resources_rc.py`.
This will generate a resources_rc.py file that you can import in your Python code.

Remember: this program is compiled using Nuitka. `eval()`, `exec()` and similar, unsafe functions are strictly forbidden. Use asteval to evaluate expressions safely.

## Compilation:

FOR TESTING:
```ps1
python -m nuitka `
    --standalone `
    --windows-console-mode=disable `
    --output-dir=compiled_build `
    --windows-icon-from-ico="assets/icons/brickeditinterface.ico" `
    --enable-plugin=pyside6 `
    main.py
```

FOR RELEASE (OPTIMIZED, LONGER TO COMPILE):
```ps1
python -m nuitka `
    --standalone `
    --windows-console-mode=disable `
    --output-dir=compiled_build `
    --windows-icon-from-ico="assets/icons/brickeditinterface.ico" `
    --enable-plugin=pyside6 `
    --enable-plugin=numpy `
    --remove-output `
    --output-filename="BrickEdit-Interface.exe" `
    main.py
```