#!/usr/bin/env python3

"""
Convert .SPE file generated by WinViewer to FITS

ref: https://github.com/kaseyrussell/python_misc_modules.git
ref: http://scipy-cookbook.readthedocs.io/items/Reading_SPE_files.html
ref: ftp://ftp.piacton.com/Public/Software/Examples/datatypes/WINHEAD.TXT

NOTE little-endian assumed

"""

import sys
import os
import re
import struct

import numpy as np
from astropy.io import fits
import warnings
#ignore VerifyWarnings
from astropy.io.fits.verify import VerifyWarning
warnings.simplefilter('ignore', category=VerifyWarning)
# If FITS header changed, Major.Minor version will be changed
VERSION = "0.3.0"
AUTHOR = "Iain Rosen <iainrosen@uvic.ca>"

class SPE:
    SPE_CONSTS = {
            'HDRNAMEMAX' : 120 ,   # Max char str length for file name
            'USERINFOMAX': 1000,   # User information space
            'COMMENTMAX' : 80  ,   # User comment string max length (5 comments)
            'LABELMAX'   : 16  ,   # Label string max length
            'FILEVERMAX' : 16  ,   # File version string max length
            'DATEMAX'    : 10  ,   # String length of file creation date string as ddmmmyyyy\0
            'ROIMAX'     : 10  ,   # Max size of roi array of structures
            'TIMEMAX'    : 7   ,   # Max time store as hhmmss\0
            }
    SPE_DATA_OFFSET = 4100 # That is, header's length

    # for key 'datatype'
    SPE_DATATYPE = {
            0: 'f', #'float' 4
            1: 'l', #'long' 4
            2: 'h', #'short' 2
            3: 'H', #'unsigned short' 2
            }
    # struct ctype to numpy dtype
    STRUCT_TO_NUMPY = {
            'f': np.float32,
            'l': np.int32,
            'h': np.short,
            'H': np.ushort,
            }

    #  char
    #  short
    #  float
    #  long
    #  double
    #  BYTE = unsigned char
    #  WORD = unsigned short
    #  DWORD = unsigned long
    SPE_TYPE_FMT = {
            'char': 'c',
            'short': 'h',
            'float': 'f',
            'long': 'l',
            'double': 'd',
            'BYTE': 'B',
            'WORD': 'H',
            'DWORD': 'L',
            }

    # headers which are to be ignored
    SPE_IGNORE = {
            'pixel_position',
            'Spare',
            'Comments',
            'calib',
            'reserved',
            'polynom',
            'Spec',
            'PImax',
            'FlatField',
            }

    # XXX share headerDef between multiple files maybe better ?
    def __init__(self, filename, headerfile = None):
        self._filename = filename

        if headerfile is not None:
            self._headerDef = self.loadHeadersDef(headerfile)
        else:
            self._headerDef = self.loadHeadersDef()

        if not hasattr(filename, "read"):
            self._fileObj = open(filename, "rb")
        else:
            self._fileObj = filename
            self._filename = os.path.realname(filename.name)

        self._fitshdr = self._initFitsHeader()
        self._spe_header = self.loadSpeHeader(self._fileObj, self._headerDef)
        self._extractInfo()

    def __del__(self):
        # XXX not tested yet
        self._fileObj.close()

    @property
    def filename(self):
        return self._filename

    @property
    def speHeader(self):
        return self._spe_header

    @property
    def fitsHeader(self):
        return self._fitshdr

    @property
    def imgCount(self):
        " return number of images "
        return self._img_count

    def imgType(self):
        # XXX xdim and ydim may be confused
        return self._xdim, self._ydim, self._ndtype

    @property
    def imgSize(self):
        if not hasattr(self, '_img_size'):
            self._img_size = self._xdim * self._ydim * struct.calcsize(self._datatype)
        return self._img_size

    def loadSpeImg(self, index):
        """ return a list of images' data
        """
        from collections.abc import Iterable
        if isinstance(index, Iterable):
            index = list(index)
        else:
            try:
                index = [int(index)]
            except: # get all images
                print("Warning: invalid image index", index, ". Fetch all available images")
                index = list(range(self._img_count))

        datas = {}
        fmt = str(self._xdim * self._ydim) + self._datatype
        for i in index:
            self._fileObj.seek(SPE.SPE_DATA_OFFSET + i * self._img_size)
            data = self._fileObj.read(self._img_size)
            datas[i] = np.array(
                    struct.unpack(fmt, data),
                    dtype = self._ndtype
                    ).reshape(self._ydim, self._xdim)
        return datas

    def writeToFits(self, dataArrs, outPrefix = None, clobber = True, output_verify = "exception"):
        """ Save dict of ndarray to fits file
        dataArrs: {index: dataArr} returned by `loadSpeImg`
        """
        if outPrefix is None:
            matched = re.match('(.*)\.spe.*$', self._filename, flags = re.IGNORECASE)
            if matched is not None and matched.groups()[0] != '':
                outPrefix = matched.groups()[0]
            else:
                outPrefix = self._filename

        for index, dataArr in dataArrs.items():
            name = "{}_x{:03}.fits".format(outPrefix, index)
            hdu = fits.PrimaryHDU(data = dataArr,
                    header = self._fitshdr,
                    )
            hdu.writeto(name, output_verify, clobber)

    def spe2fits(self, **kwargs):
        """ Shortcut method for saving all frames in .SPE to FITS
        Each FITS contains only one frame
        """
        for count in range(self._img_count):
            print(count)
            datas = self.loadSpeImg(count)
            self.writeToFits(datas, **kwargs)

    def _initFitsHeader(self):
        fitshdr = fits.header.Header()
        def uglySetHeader(key, val, comment):
            try:
                fitshdr[key] = ( val, comment )
            except:
                fitshdr[key] = ( str(val.encode()), comment )
        # Add additional header
        fitshdr['HEAD']    = ('PVCAM', 'Head model')
#        fitshdr['SPEFNAME'] = (self._filename, "original SPE filename")
        uglySetHeader('SPEFNAME', *(self._filename, "original SPE filename"))
        fitshdr['TOOLNAME'] = ('spe2fits ' + VERSION, "Tools to convert WinViewer .SPE to FITS")
        fitshdr['AUTHOR'] = (AUTHOR, "Tools' author")
        return fitshdr

    @property
    def datatype(self):
        if not hasattr(self, '_datatype'):
            self._datatype = None # just init this var
        return self._datatype

    @datatype.setter
    def datatype(self, datatype):
        " bind ndtype and datatype "
        self._datatype = datatype
        self._ndtype = SPE.STRUCT_TO_NUMPY[datatype]

    def _extractInfo(self):
        """ Extract information and construct FITS header from .SPE header
        """
        self._stripIgnore()

        self._img_count = self._spe_header['NumFrames'][0]
        self._xdim = self._spe_header['xdim'][0]
        self._ydim = self._spe_header['ydim'][0]
        self.datatype = SPE.SPE_DATATYPE.get(self._spe_header['datatype'][0], 'f')
        self._img_size = self._xdim * self._ydim * struct.calcsize(self.datatype)

        for k, v in self._spe_header.items():
            self._fitshdr[k.upper()] = v # why astropy does not auto upper or ignore case..

        self.renameHeaderKey('exp_sec', 'EXPOSURE')
        self.renameHeaderKey('ReadoutTime', 'READTIME', 'Experiment readout time in ms')
        self.renameHeaderKey('DetTemperature', 'TEMP')

    def _stripIgnore(self):
        """ Remove some headers in .SPE file
        """
        keys = list(self._spe_header.keys())
        for key in keys:
            for toIgnore in SPE.SPE_IGNORE:
                if toIgnore in key and self._spe_header[key][0] in ('', 0, 0.0):
                    self._spe_header.pop(key)

    def renameHeaderKey(self, oldname, newname, newcomment = None):
        """ Change FITS header's key name
        """
        fitshdr = self._fitshdr
        try:
            comment = newcomment if newcomment is not None else fitshdr.comments[oldname]
            fitshdr.insert(3, (newname, fitshdr[oldname], comment), after = True)
            fitshdr.remove(oldname)
        except Exception as e:
            print("Warning:", e)

    # Some header to be added:  ROIinfo, type,
    # TODO save header defination to python
    @staticmethod
    def loadHeadersDef(headerfile = "WINHEAD.TXT"):
        """ load/parse header defination file
        """
        import extractHeaderDesc as H
        if not os.path.exists(headerfile):
            print("Downloading header file required for conversion")
            H.downloadHeaders()
        print("Using header: "+headerfile)
        headers = H.getHeaders(headerfile)
        return headers

    @staticmethod
    def loadSpeHeader(fileObj, headerDef):
        """ load and save .SPE file header
        fileObj:  file handler(opened file, can be read())
        headerDef: [{}], keys: 'offset', 'type', 'key', 'comment'
        """
        headerDict = {}
        fileObj.seek(0)
        headerData = fileObj.read(SPE.SPE_DATA_OFFSET)
        for header in headerDef:
            #print(header)
            key = header['key']
            offset = header['offset']
            type_ = header['type']
            comment = header['comment']
            fmt, counts, size, key = SPE.parseFormat(type_, key)
            SPE.addToHeader(headerDict, headerData, key,
                    offset = offset,
                    fmt = fmt,
                    counts = counts,
                    length = size,
                    comment = comment,
                    )
        return headerDict

    @staticmethod
    def parseFormat(type_, key):
        """ parse format with type and key
        convert a[b] to b'fmt'
        convert a[b][c] to b * cs if type is char
        return: ('fmt',   'counts',  'length', 'key')
        #0 char a[b][c] -> ('<c>s',  <b>,   <c>, 'a')
        #1 char a[b]    -> ('<b>s',  1,     0,   'a')
        #2 type a[b]    -> ('<b><t>',1,     0,   'a')
                 ( unpack will get tuple length > 1 )
        #3 type a       -> ('<t>',   1,     0,   'a')
                default is #3
        """
        counts = 1
        length = 0 # only not zero for a[b][c] (length will be c)
        got = key.partition('[') # a[b]:('a','[','b]')  a[b][c]:('a','[','b][c]')
        realKey, rest = got[0], got[2]
        fmt = SPE.SPE_TYPE_FMT.get(type_, 'c')
        if rest != '' and fmt == 'c': # #0 or #1
            fmt = 's'
            newgot = rest.partition(']') # ('b',']','') or ('b',']','[c]')
            length = SPE.fetchLength(newgot[0]) # 'b'
            if newgot[2] != '': # '[c]' #0
                counts = length # 'counts' is 'b'
                c_length = SPE.fetchLength(newgot[2][1:-1]) # '[c]' -> c
                fmt = str(c_length) + fmt # <c>s
                length = c_length # 'length' is 'c'
            else: # '' #1
                fmt = str(length) + fmt # <b>s
                length = 0
        elif rest != '': # #2
            fmt = rest.partition(']')[0] + fmt # 'b''fmt'
        return fmt, counts, length, realKey

    @staticmethod
    def fetchLength(lenStr):
        """ parse/convert lenStr to length
        """
        try:
            length = int(SPE.SPE_CONSTS.get(lenStr, lenStr))
        except:
            length = 1
        return length

    @staticmethod
    def addToHeader(headerDict, headerData, key,
            offset = 0, fmt = 'c', counts = 1, length = 0, comment = ''):
        """ add new extracted data to header
        headerDict: dict with header info which is to be updated
        headerData: data of header
        key: key name to be parsed and added
        offset: read offset
        counts: key will be parsed to (counts) sub key
        length: for counts > 1, length gives each count's size
        comment: comment/description of the key
        """
        if counts == 1:
            val = struct.unpack_from(fmt, headerData, offset=offset)
            if len(val) > 1:
                for i in range(len(val)):
                    newkey = "{key}_{index}".format(
                            key = key,
                            index = i,
                            )
                    headerDict[newkey] = (SPE.checkVal(val[i], fmt), comment)
            else:
                headerDict[key] = (SPE.checkVal(val[0], fmt), comment)
        else:
            for i in range(counts):
                val = struct.unpack_from(fmt, headerData, offset = i * length + offset)
                newkey = "{key}_{index}".format(
                        key = key,
                        index = i,
                        )
                headerDict[newkey] = (SPE.checkVal(val[0], fmt), comment)

    @staticmethod
    def checkVal(val, fmt):
        """ modify val with fmt's info
        we will strip null character
        """
        if 's' in fmt:
            return val.decode().partition('\x00')[0]
        if 'c' in fmt and ord(val) == 0:
            return ''
        return val

if __name__ == '__main__':
    filename = sys.argv[1]
    if filename=="--all":
        for i in os.listdir("."):
            if i.endswith(".SPE"):
                print("Now converting: "+i)
                speHandler = SPE(i)
                speHandler.spe2fits()
    else:
        speHandler = SPE(filename)
        speHandler.spe2fits()

