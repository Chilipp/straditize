@echo off
REM Explicitly move noarch packages into `Lib/site-packages` as a workaround to
REM [this issue][i86] with lack of `constructor` support for `noarch` packages.
REM
REM [i86]: https://github.com/conda/constructor/issues/86#issuecomment-330863531
IF EXIST site-packages (
REM Move directory modules.
for /D %%i in (site-packages/*) do IF NOT EXIST Lib\site-packages\%%i (
    echo Move noarch package: %%i
    move site-packages\%%i Lib\site-packages
)
REM Move file modules.
for %%i in (site-packages/*.py) do IF "%%~xi" == ".py" (IF NOT EXIST Lib\site-packages\%%i (
    echo Move noarch package: %%i
    move site-packages\%%i Lib\site-packages
))
rmdir /S/Q site-packages
)
