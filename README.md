# spe2fits
Convert .SPE files generated by PI(Princeton Instruments) WinViewer to FITS. This is a stripped down version of jerryjiahaha/spe2fits and has been updated to work with newer versions of Python.

## Install Instructions
### Running from release
The easiest method is to use a release compiled for your operating system. This release contains all of the needed dependencies and is much easier to setup and use. You can find the latest release for your operating system [here](https://github.com/iainrosen/spe2fits/releases).

After downloading (you may need to rename the downloaded file), place the script in the directory with your SPE files, open up a terminal or command prompt, and type `./spe2fits filename.SPE` where `filename` is the name of your SPE file you would like to convert. You can also use the `--all` tag instead of a filename to convert every SPE file in the current working directory. **Be careful with using `--all`, because it will overwrite existing files.**

### Running from source
It is recommended you use Python 3.11 to run this script from source. You'll need the following dependencies before you start:
#### Dependencies
- AstroPy
- MatPlotLib
- Warnings
- NumPy
- Collections

After these are installed using pip: `python3 -m pip install packagename`, you can run the script just as above, but with the .py extension. Ex: `./spe2fits.py filename.SPE`.

