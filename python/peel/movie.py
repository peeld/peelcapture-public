# Copyright (c) 2022 Peel Software Development Inc
# All Rights Reserved.
#
# THIS SOFTWARE AND DOCUMENTATION ARE PROVIDED "AS IS" AND WITH ALL FAULTS AND DEFECTS WITHOUT WARRANTY OF ANY KIND. TO
# THE MAXIMUM EXTENT PERMITTED UNDER APPLICABLE LAW, PEEL SOFTWARE DEVELOPMENT, ON ITS OWN BEHALF AND ON BEHALF OF ITS
# AFFILIATES AND ITS AND THEIR RESPECTIVE LICENSORS AND SERVICE PROVIDERS, EXPRESSLY DISCLAIMS ALL WARRANTIES, WHETHER
# EXPRESS, IMPLIED, STATUTORY, OR OTHERWISE, WITH RESPECT TO THE SOFTWARE AND DOCUMENTATION, INCLUDING ALL IMPLIED
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, TITLE, AND NON-INFRINGEMENT, AND WARRANTIES THAT MAY
# ARISE OUT OF COURSE OF DEALING, COURSE OF PERFORMANCE, USAGE, OR TRADE PRACTICE. WITHOUT LIMITATION TO THE FOREGOING,
# PEEL SOFTWARE DEVELOPMENT PROVIDES NO WARRANTY OR UNDERTAKING, AND MAKES NO REPRESENTATION OF ANY KIND THAT THE
# LICENSED SOFTWARE WILL MEET REQUIREMENTS, ACHIEVE ANY INTENDED RESULTS, BE COMPATIBLE, OR WORK WITH ANY OTHER
# SOFTWARE, APPLICATIONS, SYSTEMS, OR SERVICES, OPERATE WITHOUT INTERRUPTION, MEET ANY PERFORMANCE OR RELIABILITY
# STANDARDS OR BE ERROR FREE, OR THAT ANY ERRORS OR DEFECTS CAN OR WILL BE CORRECTED.
#
# IN NO EVENT WILL PEEL SOFTWARE DEVELOPMENT OR ITS AFFILIATES, OR ANY OF ITS OR THEIR RESPECTIVE LICENSORS OR SERVICE
# PROVIDERS, BE LIABLE TO ANY THIRD PARTY FOR ANY USE, INTERRUPTION, DELAY, OR INABILITY TO USE THE SOFTWARE; LOST
# REVENUES OR PROFITS; DELAYS, INTERRUPTION, OR LOSS OF SERVICES, BUSINESS, OR GOODWILL; LOSS OR CORRUPTION OF DATA;
# LOSS RESULTING FROM SYSTEM OR SYSTEM SERVICE FAILURE, MALFUNCTION, OR SHUTDOWN; FAILURE TO ACCURATELY TRANSFER, READ,
# OR TRANSMIT INFORMATION; FAILURE TO UPDATE OR PROVIDE CORRECT INFORMATION; SYSTEM INCOMPATIBILITY OR PROVISION OF
# INCORRECT COMPATIBILITY INFORMATION; OR BREACHES IN SYSTEM SECURITY; OR FOR ANY CONSEQUENTIAL, INCIDENTAL, INDIRECT,
# EXEMPLARY, SPECIAL, OR PUNITIVE DAMAGES, WHETHER ARISING OUT OF OR IN CONNECTION WITH THIS AGREEMENT, BREACH OF
# CONTRACT, TORT (INCLUDING NEGLIGENCE), OR OTHERWISE, REGARDLESS OF WHETHER SUCH DAMAGES WERE FORESEEABLE AND WHETHER
# OR NOT THE LICENSOR WAS ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.


import subprocess
import os
import os.path
import json
import timecode
import tempfile
from PySide6 import QtCore


def ffmpeg():
    ffmpeg_exe = os.path.join(QtCore.QCoreApplication.applicationDirPath(), "ffmpeg.exe")
    if not os.path.isfile(ffmpeg_exe):
        raise RuntimeError("Error: Could not find ffmpeg here: " + ffmpeg_exe)
    return ffmpeg_exe


def ffprobe():
    ffprobe_exe = os.path.join(QtCore.QCoreApplication.applicationDirPath(), "ffmpeg.exe")
    if not os.path.isfile(ffprobe_exe):
        raise RuntimeError("Error: Could not find ffprobe here: " + ffprobe_exe)
    return ffprobe_exe


def runthis(cmd):
    print("CMD: " + str(cmd))
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    print(out.decode())
    print(err.decode())


def make_h264(source, dest):
    runthis([ffmpeg(), "-i", source, "-vcodec", "libx264", dest])


def make_thumb(mov):
    basedir, filename = os.path.split(mov)
    thumb_dir = os.path.join(basedir, ".thumb")
    if not os.path.isdir(thumb_dir):
        os.mkdir(thumb_dir)

    print(filename)
    print(os.path.splitext(filename))
    basename, ext = os.path.splitext(filename)
    thumb_name = basename + ext.replace(".", "_") + ".png"

    thumb_path = os.path.join(thumb_dir, thumb_name)
    if os.path.isfile(thumb_path):
        return thumb_path

    runthis([ffmpeg(), "-i",  mov, "-ss", "00:00:01.000", "-vframes", "1", thumb_path])
    return thumb_path


def mov_start(mov_file):

    cmd = [ffprobe(), "-print_format", "json", "-show_streams", mov_file]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    data = json.loads(out)
    tc = None
    rate = None
    if 'streams' not in data:
        print("Invalid file: " + str(mov_file))
        return None, None

    for i in data['streams']:
        if 'r_frame_rate' in i and i['r_frame_rate'] != "0/0": rate = i['r_frame_rate']
        if 'tags' not in i: continue
        if 'timecode' not in i['tags']: continue
        tc = i['tags']['timecode']
        print(tc)

    if tc is None:
        raise RuntimeError("No timecode")

    return tc, rate


def add_timecode(in_file, out_file):
    start, rate = mov_start(in_file)

    if start is None:
        return

    if rate != "30/1":
        print("Not 30fps: " + str(rate))

    start_tc = timecode.Timecode('30', start) - timecode.Timecode('30', frames=1)

    f1 = "timecode='%s\:%s\:%s\:%s':" % start_tc.frames_to_tc(start_tc.frames)
    f2 = "fontfile=tf.ttf: r=30: x=1700: y=5: timecode_rate=30:"
    f3 = "fontcolor=0xccFFFF@1: fontsize=32: box=1: boxcolor=0x000000@0.7"

    cmd = [ffmpeg(), "-i", in_file, "-c:a", "aac", "-vf",
           "drawtext=" + f1 + f2 + f3,
           "-c:v", "libx264", "-preset", "fast", "-f", "mp4", "-y", out_file + ".mp4"]

    runthis(cmd)




