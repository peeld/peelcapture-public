import urllib.parse
import urllib.request
import re
# https://gitlab.aja.com/pub/rest_api/-/blob/52578781dbf8207689ea71df3753b9801334d695/KiPro-GO/04_Ki-Pro-GO_Commands.md
host = "192.168.1.193"

def call(**params):

    try:

        url = "http://" + host + "/config?" + urllib.parse.urlencode(params)
        print(url)
        f = urllib.request.urlopen(url, timeout=1)
        return f.read()

    except Exception as e:
        print("KI PRO ERROR: " + str(e))
        return None

#ret = call(paramid='eParamID_MediaState', value=1, action="set")
#print(ret)

def clips(host):
    f = urllib.request.urlopen("http://" + host + "/clips", timeout=1)
    s = f.read().decode("ascii")

    for clip in re.findall(r"\{[^\)]+?\}", s):

        ret = re.match("{(.*)}", clip)
        if not ret:
            continue

        clip = ret.group(1).strip()

        d = {}

        for i in re.findall(r'.*?: "[^"]*",\s+', clip + ","):
            p = i.find(':')
            k = i[:p].strip()
            v = i[p + 1:].strip()[1:-2]
            if k and v:
                d[k] = v

        yield d



print(clips(host))