pyinstaller --noconfirm --log-level=WARN ^
    --onefile --nowindow ^
    --add-data="README;." ^
    --add-data="image1.png;img" ^
    --add-binary="libfoo.so;lib" ^
    --hidden-import=secret1 ^
    --hidden-import=secret2 ^
    --icon=..\MLNMFLCN.ICO ^
    myscript.spec