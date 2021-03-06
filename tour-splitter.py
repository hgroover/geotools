#!/usr/bin/python
# Tour splitter - take a Google Maps tour in kml format and split into
# multiple pieces so long tours can be rendered using Google Earth Pro
# MovieMaker (which tends to crash during really long tours).
# A path is converted into a tour by highlighting the path object
# then using the "Play tour" icon at the bottom of my places. Save
# on the tour playback bar prompts for a name and saves the path as
# a tour. The Options / Touring / When creating a tour from a line / Speed
# in effect at the time of saving the path as a tour is what determines
# the speed of the tour. There is no way to change the speed of the tour
# later. Speed is in units under Options / 3D view / Units (either mph or kph).

import xml.etree.ElementTree as ET
import math
import sys
import os
from math import radians, cos, sin, asin, sqrt

# Return haversine distance in miles
def haversine(lat1, lon1, lat2, lon2):

      R = 3959.87433 # this is in miles.  For Earth radius in kilometers use 6372.8 km

      dLat = radians(lat2 - lat1)
      dLon = radians(lon2 - lon1)
      lat1 = radians(lat1)
      lat2 = radians(lat2)

      a = sin(dLat/2)**2 + cos(lat1)*cos(lat2)*sin(dLon/2)**2
      c = 2*asin(sqrt(a))

      return R * c

version = '1.02'
# 10 minutes; at 240mph, about 24m
maxtime = 600
# 25 miles; at 250mph, about 10m
maxdist = 25
splitByTime = 0
splitByDistance = 1
if len(sys.argv) < 2:
   print 'Syntax: tour-splitter.py tourfile [maxtime]'
   print 'maxtime is in seconds, default is 900 (15m)'
   sys.exit(1)
basename = sys.argv[1]
(base_base, base_ext) = os.path.splitext(basename)
if base_ext != '':
   basename = base_base
   print 'Using basename', basename
if not os.path.isfile(basename + '.kml'):
   print 'Cannot read', basename + '.kml'
   sys.exit(1)
if len(sys.argv) > 2:
   maxtime = float(sys.argv[2])

if splitByTime > 0:
   print 'tour-splitter {} - parsing {}.kml, maximum time per segment = {}s'.format(version, basename, maxtime)
else:
   print 'tour-splitter {} - parsing {}.kml, maximum distance per segment = {}m'.format(version, basename, maxdist)

tree = ET.parse(basename + '.kml')
root = tree.getroot()

#print 'Parsed tree:'
#print tree.tag
#print tree.attrib
#print root.tag
#print root.name
#print root.description
#print root.attrib
preamble = '<?xml version="1.0" encoding="UTF-8"?>' + "\r\n"
preamble = preamble + '<ns0:kml xmlns:ns0="http://www.opengis.net/kml/2.2" xmlns:ns1="http://www.google.com/kml/ext/2.2">' + "\r\n"
preamble = preamble + "<ns1:Tour>\r\n"
#print 'Children:'
for child in root:
  #print child.tag, child.attrib
  firstborn = child
#print 'Grandchildren:'
# Tour has a name and description (not attributes but tags)
name = ''
description = ''
for child2 in firstborn:
  if child2.tag == '{http://www.opengis.net/kml/2.2}name':
     print 'Name:', child2.text
     name = child2.text
  elif child2.tag == '{http://www.opengis.net/kml/2.2}description':
     print 'Description:', child2.text
     description = child2.text
  elif child2.tag == '{http://www.google.com/kml/ext/2.2}Playlist':
     playlist = child2
  else: 
     preamble = preamble + ET.tostring(child2)
     print child2.tag, child2.attrib, child2.text
# Get total duration and distance
totalTime = 0.0
totalDistance = 0.0
prevlat = 0
prevlon = 0
for child in playlist:
  if child.tag == '{http://www.google.com/kml/ext/2.2}FlyTo':
     duration = child.find('{http://www.google.com/kml/ext/2.2}duration')
     #print 'Fly to:', duration.text
     totalTime = totalTime + float(duration.text)
     #print ET.tostring(child)
     # Find latitude and longitude within LookAt
     lookat = child.find('{http://www.opengis.net/kml/2.2}LookAt')
     lat = float(lookat.find('{http://www.opengis.net/kml/2.2}latitude').text)
     lon = float(lookat.find('{http://www.opengis.net/kml/2.2}longitude').text)
     if prevlat != 0:
        distance = haversine( prevlat, prevlon, lat, lon )
        totalDistance = totalDistance + distance
     prevlat = lat
     prevlon = lon
  else:
     print child.tag, child.text
print 'Total duration (s):', totalTime
print 'Total distance (m):', totalDistance
if totalTime > maxtime:
  chunkFloat = totalTime / maxtime
  chunkRounded = math.floor(chunkFloat + 0.9999999)
  chunkMaxTime = totalTime / chunkRounded
  chunkRounded = int(chunkRounded)
  # FIXME normalize chunk time to an even multiple but ensure the last chunk is not too short
  print 'Splitting, total time', totalTime, 'splitting into', chunkRounded, 'pieces, time per piece', chunkMaxTime
else:
  print 'Not splitting - total time', totalTime

# Dump preamble + '<ns0:name>name</ns0:name>' + '<ns0:description>desc</ns0:description>' + '<ns1:Playlist>'
postamble = "</ns1:Playlist>\r\n</ns1:Tour>\r\n</ns0:kml>\r\n"

startTime = 0.0
startDist = 0.0
lastFlyTo = ''
prevlat = 0
prevlon = 0
for x in range(1,chunkRounded+1):
  filename = "{2}-{0}of{1}.kml".format(x, chunkRounded, basename)
  print 'Writing', filename, 'starting from', startTime
  with open(filename, 'wb') as f:
     f.write(preamble)
     f.write("<ns0:name>{0} ({1} of {2})</ns0:name>\r\n".format(name, x, chunkRounded))
     f.write("<ns0:description>{0} starting {1}m {2}s miles {3}</ns0:description>\r\n".format(description, int(startTime / 60), startTime - 60 * int(startTime / 60), startDist))
     f.write("<ns1:Playlist>\r\n")
     # Skip leading elements
     chunkStartTime = 0.0
     chunkElapsed = 0.0
     chunkIndex = 0
     for child in playlist:
        if child.tag == '{http://www.google.com/kml/ext/2.2}FlyTo':
           duration = float(child.find('{http://www.google.com/kml/ext/2.2}duration').text)
           #if x == 1:
           #   print 'Fly to:', duration, child.find('{http://www.google.com/kml/ext/2.2}duration').text
           lookat = child.find('{http://www.opengis.net/kml/2.2}LookAt')
           lat = float(lookat.find('{http://www.opengis.net/kml/2.2}latitude').text)
           lon = float(lookat.find('{http://www.opengis.net/kml/2.2}longitude').text)
           distance = 0
           if prevlat != 0:
              distance = haversine( prevlat, prevlon, lat, lon )
           prevlat = lat
           prevlon = lon
        else:
           print 'Warning: discarding ' + ET.tostring(child)
           continue
        if chunkStartTime < startTime:
           if x == 1:
              print 'Skipping start, chunkStartTime', chunkStartTime
           chunkStartTime = chunkStartTime + duration
           continue
        if chunkIndex == 0:
           print 'Writing chunk {0} starting at {1}s duration {2} mile {3}'.format(x, startTime, duration, startDist)
           # Replicate the last record of the previous chunk with ns0:FlyToMode removed
           if x > 1:
              f.write(lastFlyTo.replace('<ns0:flyToMode>smooth</ns0:flyToMode>', ''))
        lastFlyTo = ET.tostring(child)
        f.write(lastFlyTo)
        startTime = startTime + duration
        startDist = startDist + distance
        chunkStartTime = chunkStartTime + duration
        chunkElapsed = chunkElapsed + duration
        chunkIndex = chunkIndex + 1
        # Check for end
        if chunkElapsed >= chunkMaxTime:
           break
     # Close
     f.write("</ns1:Playlist>\r\n</ns1:Tour>\r\n</ns0:kml>\r\n")
     f.close()
