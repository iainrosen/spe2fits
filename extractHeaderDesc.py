#!/usr/bin/env python3

import sys
import re
import requests

# Try to match: "^# (type)  (key)  (offset) (description)$"
pattern = re.compile(r"^#?\s+(?P<type>\w+)\s+(?P<key>[\w\[\]]+)\s+(?P<offset>\d+)(?P<comment>.*)$")

def convertMatchedDict(matched:dict) -> dict:
    return {
        "type":   matched['type'],
        "key":    matched['key'],
        "offset": int(matched['offset']),
        "comment": matched['comment'].strip(),
        }

def saveHeader2csv(meta):
    print("offset,type,key,comment")
    list(map(lambda m:
            print("{offset},{type},{key},{comment}"
                .format(**m)),
            meta)
        )

def getHeaders(filename) -> list:
    fhandler = open(filename)
    fdata = fhandler.readlines()
    metadata = []
    for d in fdata:
#    sys.stdout.write(d)
        match = re.match(pattern, d)
        if match is not None:
#        print(match.groupdict())
            metadata.append(
                    convertMatchedDict(
                        match.groupdict()
                        )
                    )
    return metadata
def downloadHeaders():
    url = 'https://gist.github.com/iainrosen/6d767384027a3bcf4edc20a2abc7fb73/raw/a2445dc08b73092c4ad66e587c673b1015923fc5/WINHEAD.txt'
    r = requests.get(url, allow_redirects=True)
    open('WINHEAD.txt', 'wb').write(r.content)
if __name__ == '__main__':
    filename = 'WINHEAD.TXT' if len(sys.argv) < 2 else sys.argv[1]
    metadata = getHeaders(filename)
    saveHeader2csv(metadata)
#print("\n".join(map(str,metadata)))

