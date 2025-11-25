@REM 超快速编译 - 仅用于快速测试
@REM conda activate mytoolsbuild

@echo 开始超快速编译（测试版 - 最小优化）...
python -m nuitka ^
    --standalone ^
    --windows-console-mode=attach ^
    --assume-yes-for-downloads ^
    --include-data-dir=bin=bin ^
    --include-data-dir=src/assets=src/assets ^
    --nofollow-import-to=tkinter ^
    --nofollow-import-to=unittest ^
    --nofollow-import-to=test ^
    --nofollow-import-to=pytest ^
    --nofollow-import-to=setuptools ^
    --nofollow-import-to=distutils ^
    --nofollow-import-to=wheel ^
    --nofollow-import-to=pip ^
    --nofollow-import-to=IPython ^
    --nofollow-import-to=matplotlib ^
    --output-dir=dist ^
    --output-filename=mytools_test.exe ^
    --jobs=8 ^
    --low-memory ^
    --disable-ccache=no ^
    --remove-output ^
    src/main.py

@echo.
@echo 编译完成！测试目录: dist\mytools_test.dist\
@echo 可执行文件: dist\mytools_test.dist\mytools_test.exe

