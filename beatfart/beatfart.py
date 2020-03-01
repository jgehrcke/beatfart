#!/usr/bin/env python
#
# MIT License

# Copyright (c) 2014-2020 Dr. Jan-Philip Gehrcke

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
This program is intended to repair MP3 files published by Beatport with invalid
metadata (specifically, the text encoding).

Attempts to fix broken text in Beatport MP3 ID3 tags.

See https://gehrcke.de/2014/07/mojibake-beatports-id3-text-encoding-is-broken/
"""

import os
import logging
import sys
import argparse

import mutagen.id3


__version__ = "0.0.1"


TAGS = [
    "TPE1",
    "TIT1",
    "TIT2",
    "TIT3",
    "TALB",
    "TOPE",
    "TOAL",
    "TPE2",
    "TPE3",
    "TPE4",
    "TCOM",
]


log = logging.getLogger()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d %(levelname)s: %(message)s",
    datefmt="%y%m%d-%H:%M:%S",
)


def processpath(path):
    if os.path.isfile(path):
        processfile(path)
    elif os.path.isdir(path):
        processdir(path)
    else:
        raise Exception(f"Invalid path: {path}")


def processdir(dpath):
    for root, dirnames, filenames in os.walk(dpath):
        for fname in filenames:
            processfile(os.path.join(root, fname))
        for _ in dirnames:
            # ignore directories
            continue


def processfile(fpath):

    _, ext = os.path.splitext(fpath)
    if ext.lower() not in [".mp3"]:
        return None

    try:
        data = mutagen.id3.ID3(fpath)
    except mutagen.id3.ID3NoHeaderError:
        log.debug("skip file (ID3NoHeaderError): %s", fpath)
        return None

    for tag in TAGS:

        if tag not in data:
            log.debug("skip tag %s in file %s", tag, fpath)
            continue

        # print(mutagen.id3.Encoding.UTF8)
        # print(data[tag].encoding)
        if data[tag].encoding != mutagen.id3.Encoding.UTF8:
            log.debug(
                "skip file (non-utf-8), tag %s supposedly %s-encoded. %s",
                tag,
                data[tag].encoding,
                fpath,
            )
            return None

        text_processed = processbytes(bytes(data[tag]))
        if text_processed is not None:
            text_asinfile = str(data[tag])
            if text_asinfile != text_processed:
                print(
                    "candidate.,\n"
                    "    from file: %s\n"
                    "    corrected: %s" % (repr(text_asinfile), repr(text_processed))
                )
                print("fix me")


def processbytes(rawdata):
    """
    # Scenario good data:
    >>> s = "jürgen" gooddata = s.encode('utf-8') gooddata b'j\xc3\xbcrgen'

    >>> rawdata = gooddata

    >>> step1 = rawdata.decode("utf-8") step1 'jürgen'

    >>> step2 = step1.encode("raw_unicode_escape") step2 b'j\xfcrgen'  # code
    >>> point U+00FC is the Ü, that is why. But is this byte sequence
    >>> meaningful?

    >>> doubledecoded = step2.decode("utf-8") Traceback (most recent call
    last): File "<stdin>", line 1, in <module> UnicodeDecodeError: 'utf-8'
    codec can't decode byte 0xfc in position 1: invalid start byte

    # Not in this case! A UnicodeDecodeError in this step is an indicator for
    # the fact that the original data was actually _good_. Is this always the
    # case? That is, are there situations of _good_ data where the
    # "raw_unicode_escape" yields a byte sequence that is valid in UTF-8?
    # I don't know, let's address this question later. Worst case: false
    # positive, that we attempt to fix a file that does not need fixing.

    woops, just saw this match in my music collection which I think
    from file: 'Fazıl Say'
    corrected: 'Faz\\u0131l Say'

    """

    def _method1(rawdata):

        step1 = rawdata.decode("utf-8")
        step2 = step1.encode("raw_unicode_escape")

        try:
            doubledecoded = step2.decode("utf-8")
        except UnicodeDecodeError:
            # Assume that the original data was actually good, see docstring
            # above.
            return None
        return doubledecoded

    def _method2(rawdata):

        step1 = rawdata.decode("utf-8")
        step2 = step1.encode("raw_unicode_escape")

        doubledecoded = step2.decode("utf-8", errors="surrogateescape")

        # if this got longer than there's an escape seq left in text, shit
        # happened, if it got shorter then we're good.

        if len(step1) > len(doubledecoded):
            return doubledecoded
        return None

    return _method2(rawdata)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    opts = parser.parse_args()

    for p in opts.paths:
        processpath(p)
