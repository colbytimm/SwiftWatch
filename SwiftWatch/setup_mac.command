pyinstaller --noconfirm --log-level=WARN ^
    --onefile --nowindow ^
    --add-data="about_box.ui" ^
    --add-data="mainwindow.ui" ^
    myscript.spec