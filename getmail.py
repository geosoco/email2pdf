#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import imaplib
from email.mime.text import MIMEText
from email.parser import Parser
from email.utils import parsedate_tz, mktime_tz
import mimetypes
import email
from ezconf import ConfigFile
import pdfkit
import re
import os
import datetime
import time


#
#
# main
#
#

cfg = ConfigFile("config.json")

mail = imaplib.IMAP4_SSL(cfg.getValue('mailserver.address'))
mail.login(
    cfg.getValue("mailserver.username"),
    cfg.getValue("mailserver.password")
    )

result, newcount = mail.select('INBOX')

print result, newcount


result, ids = mail.search(None, "ALL")

print result, ids



result, data = mail.fetch(1, '(UID RFC822)')

print result, len(data)
for i, d in enumerate(data[0]):
    if len(d) < 40:
        print i, ":", d
    else:
        print i, ":", "too long"


match = re.match(r"\s*\d+\s*\(UID\s*(\d+)\s*RFC822 {\d+}", data[0][0])
uid = match.group(1)

msg = email.message_from_string(data[0][1])
print msg.keys()


datestr = msg['Date']
msgdate = datetime.datetime.fromtimestamp(mktime_tz(parsedate_tz(datestr)))

print "Date:", msgdate
print "Content-Type:", msg['Content-Type']
print "Message-ID:", msg['Message-ID']

print "is multipart", msg.is_multipart()

part_dict = {}

counter = 1
for part in msg.walk():
    contenttype = part.get_content_type()
    print contenttype

    if contenttype.startswith('multipart'):
        continue

    part_dict[contenttype] = part

    filename = part.get_filename()
    if not filename:

        if contenttype == "text/plain":
            ext = ".txt"
        else:
            ext = mimetypes.guess_extension(contenttype)
            if not ext:
                ext = '.bin'

        filename = 'part-%03d%s' % (counter, ext)
    print "filename:", filename

    counter += 1


out_base_path = cfg.getValue("output.path")
if not os.path.exists(out_base_path):
    os.makedirs(out_base_path)

#
# write text data
#

print uid, msgdate.strftime("%Y%m%d_%H%M%S")
text_fn_base = "{}_{}.html".format(uid, msgdate.strftime("%Y%m%d_%H%M%S"))
text_path = os.path.join(out_base_path, text_fn_base)
if 'text/html' in part_dict:
    part = part_dict['text/html']    
elif 'text/plain' in part_dict:
    part = part_dict['text/plain']

with open(text_path, "wb") as f:
    f.write(part.get_payload(decode=True))

#
# find any files and write those
#

whitelist = ["image/png", "image/jpeg"]

count = 1
for ct, part in part_dict.iteritems():
    if ct in whitelist:
        out_fn = part.get_filename()
        if not out_fn:
            ext = mimetypes.guess_extension(ct)
            out_fn = 'part-%03d%s' % (counter, ext)
    count += 1

    file_path = os.path.join(out_base_path, out_fn)
    with open(file_path, 'wb') as f:
        f.write(part.get_payload(decode=True))


