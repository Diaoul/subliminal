# -*- coding: utf-8 -*-
import logging
from datetime import datetime
import hashlib
import os
import re
import socket
import struct

import requests
from requests.exceptions import SSLError
from six.moves.xmlrpc_client import ProtocolError

from .exceptions import ServiceUnavailable


logger = logging.getLogger(__name__)


def hash_opensubtitles(video_path):
    """Compute a hash using OpenSubtitles' algorithm.

    :param str video_path: path of the video.
    :return: the hash.
    :rtype: str

    """
    bytesize = struct.calcsize(b'<q')
    with open(video_path, 'rb') as f:
        filesize = os.path.getsize(video_path)
        filehash = filesize
        if filesize < 65536 * 2:
            return
        for _ in range(65536 // bytesize):
            filebuffer = f.read(bytesize)
            (l_value,) = struct.unpack(b'<q', filebuffer)
            filehash += l_value
            filehash &= 0xFFFFFFFFFFFFFFFF  # to remain as 64bit number
        f.seek(max(0, filesize - 65536), 0)
        for _ in range(65536 // bytesize):
            filebuffer = f.read(bytesize)
            (l_value,) = struct.unpack(b'<q', filebuffer)
            filehash += l_value
            filehash &= 0xFFFFFFFFFFFFFFFF
    returnedhash = '%016x' % filehash

    return returnedhash


def hash_thesubdb(video_path):
    """Compute a hash using TheSubDB's algorithm.

    :param str video_path: path of the video.
    :return: the hash.
    :rtype: str

    """
    readsize = 64 * 1024
    if os.path.getsize(video_path) < readsize:
        return
    with open(video_path, 'rb') as f:
        data = f.read(readsize)
        f.seek(-readsize, os.SEEK_END)
        data += f.read(readsize)

    return hashlib.md5(data).hexdigest()


def hash_napiprojekt(video_path):
    """Compute a hash using NapiProjekt's algorithm.

    :param str video_path: path of the video.
    :return: the hash.
    :rtype: str

    """
    readsize = 1024 * 1024 * 10
    with open(video_path, 'rb') as f:
        data = f.read(readsize)
    return hashlib.md5(data).hexdigest()


def hash_shooter(video_path):
    """Compute a hash using Shooter's algorithm

    :param string video_path: path of the video
    :return: the hash
    :rtype: string

    """
    filesize = os.path.getsize(video_path)
    readsize = 4096
    if os.path.getsize(video_path) < readsize * 2:
        return None
    offsets = (readsize, filesize // 3 * 2, filesize // 3, filesize - readsize * 2)
    filehash = []
    with open(video_path, 'rb') as f:
        for offset in offsets:
            f.seek(offset)
            filehash.append(hashlib.md5(f.read(readsize)).hexdigest())
    return ';'.join(filehash)


def sanitize(string, ignore_characters=None):
    """Sanitize a string to strip special characters.

    :param str string: the string to sanitize.
    :param set ignore_characters: characters to ignore.
    :return: the sanitized string.
    :rtype: str

    """
    # only deal with strings
    if string is None:
        return

    ignore_characters = ignore_characters or set()

    # replace some characters with one space
    characters = {'-', ':', '(', ')', '.', ','} - ignore_characters
    if characters:
        string = re.sub(r'[%s]' % re.escape(''.join(characters)), ' ', string)

    # remove some characters
    characters = {'\''} - ignore_characters
    if characters:
        string = re.sub(r'[%s]' % re.escape(''.join(characters)), '', string)

    # replace multiple spaces with one
    string = re.sub(r'\s+', ' ', string)

    # strip and lower case
    return string.strip().lower()


def sanitize_release_group(string):
    """Sanitize a `release_group` string to remove content in square brackets.

    :param str string: the release group to sanitize.
    :return: the sanitized release group.
    :rtype: str

    """
    # only deal with strings
    if string is None:
        return

    # remove content in square brackets
    string = re.sub(r'\[\w+\]', '', string)

    # strip and upper case
    return string.strip().upper()


def timestamp(date):
    """Get the timestamp of the `date`, python2/3 compatible

    :param datetime.datetime date: the utc date.
    :return: the timestamp of the date.
    :rtype: float

    """
    return (date - datetime(1970, 1, 1)).total_seconds()


def matches_title(actual, title, alternative_titles):
    """Whether `actual` matches the `title` or `alternative_titles`

    :param str actual: the actual title to check
    :param str title: the expected title
    :param list alternative_titles: the expected alternative_titles
    :return: whether the actual title matches the title or alternative_titles.
    :rtype: bool

    """
    actual = sanitize(actual)
    title = sanitize(title)
    if actual == title:
        return True

    alternative_titles = set(sanitize(t) for t in alternative_titles)
    if actual in alternative_titles:
        return True

    return actual.startswith(title) and actual[len(title):].strip() in alternative_titles


def handle_exception(e, msg):
    """Handle exception, logging the proper error message followed by `msg`.

    Exception traceback is only logged for specific cases.

    :param exception e: The exception to handle.
    :param str msg: The message to log.
    """
    if isinstance(e, (requests.Timeout, socket.timeout)):
        logger.error('Request timed out. %s', msg)
    elif isinstance(e, (ServiceUnavailable, ProtocolError)):
        # OpenSubtitles raises xmlrpclib.ProtocolError when unavailable
        logger.error('Service unavailable. %s', msg)
    elif isinstance(e, requests.exceptions.HTTPError):
        logger.error('HTTP error %r. %s', e.response.status_code, msg,
                     exc_info=e.response.status_code not in range(500, 600))
    elif isinstance(e, SSLError):
        logger.error('SSL error %r. %s', e.args[0], msg,
                     exc_info=e.args[0] != 'The read operation timed out')
    else:
        logger.exception('Unexpected error. %s', msg)
