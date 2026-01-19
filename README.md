BrickEdit-Interface is a tool to help users exploit BrickEdit's capabilities without any code knowledge, by providing a set of tools in a graphical interface.

Before using BrickEdit-Interface, you need to have the following dependencies installed:

`PySide6`: Python binding for the Qt framework (used for GUI);
`asteval`: A Python library for evaluating arbitrary expressions safely

BrickEdit-Interface uses Qt Resource Files (.qrc) to bundle resources such as icons and images.

When adding assets, remember to save the file and run the following command to compile the .qrc file into a .py file: `pyside6-rcc resources.qrc -o resources_rc.py`.
This will generate a resources_rc.py file that you can import in your Python code.

Remember: this program is compiled using Nuitka. `eval()`, `exec()` and similar, unsafe functions are strictly forbidden. Use asteval to evaluate expressions safely.

## Compilation:

FOR TESTING:
```ps1
python -m nuitka `
    --onefile `
    --windows-console-mode=disable `
    --output-dir=compiled_build `
    --windows-icon-from-ico="assets/icons/brickeditinterface.ico" `
    --enable-plugin=pyside6 `
    main.py
```

FOR RELEASE (OPTIMIZED, LONGER TO COMPILE):
```ps1
python -m nuitka `
    --onefile `
    --windows-console-mode=disable `
    --output-dir=release_build `
    --windows-icon-from-ico="assets/icons/brickeditinterface.ico" `
    --enable-plugin=pyside6 `
    --lto=yes `
    --clang `
    --remove-output `
    main.py
```