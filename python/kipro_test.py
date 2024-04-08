import urllib.parse, urllib.request

# https://gitlab.aja.com/pub/rest_api/-/blob/52578781dbf8207689ea71df3753b9801334d695/KiPro-GO/04_Ki-Pro-GO_Commands.md
host = "192.168.1.51"

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

f = urllib.request.urlopen("http://" + host + "/clips", timeout=1)
s = f.read().decode("ascii")

print(s)