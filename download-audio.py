#!/usr/bin/python
from __future__ import unicode_literals
import youtube_dl
import os
import sys
import subprocess
import json
import re
import string

# selenium
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time

class bcolours:
    HEADER = '\033[95m'
    SUCCESS = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def printMessage(status, message):
  if (status == 'HEADER'):
   print bcolours.HEADER + message + bcolours.ENDC
  elif (status == 'SUCCESS'):
   print bcolours.SUCCESS + message + bcolours.ENDC
  elif (status == 'WARNING'):
   print bcolours.WARNING + message + bcolours.ENDC
  elif ((status == 'FAIL') or (status == 'ERROR')):
   print bcolours.FAIL + message + bcolours.ENDC
  else:
    print bcolours.ENDC + message + bcolours.ENDC
  


def getShareUrl(url):
  print bcolours.HEADER + "Looking up URL" + bcolours.ENDC
  driver = webdriver.PhantomJS() # headless
  #driver = webdriver.Firefox() # visible
  driver.get(url)

  try:
    elem = driver.find_element_by_xpath(".//*[@id='watch8-secondary-actions']/button") # current style
    #style-scope ytd-button-renderer style-default # new-style
  except Exception as e:
    printMessage("WARNING", "Failed to find share button")
    filename = generateFilename("screen", "png")
    driver.get_screenshot_as_file('/screenshot/' + filename)
    driver.close()
    return -1
  else:
    time.sleep(2)
    elem.click()
  finally:
    pass

  try:
    time.sleep(1)
    share_url = driver.find_element_by_xpath(".//*[@id='watch-actions-share-panel']/div/div[3]/div[2]/span[1]/input")
    url = share_url.get_attribute("value")
  except Exception as e:
    printMessage("WARNING", "Failed to get URL")
    driver.close()
    return -1
  #else:
  #  print url
  finally:
    pass

  if (url == 1 or url == '1'):
    return -1

  message = "Fetched URL successfully: " + url
  printMessage("SUCCESS", message)
  driver.close()
  return url

def tryToGetStartTime(url):
  start_time = 0
  if ((len(url.split("?")) > 1) or (len(url.split("?")) > 1)):
    try:
      num_splits = len(url.split("&"))
      if (num_splits > 1):
        time = url.split("&")[1]
        #print time
        match = re.findall(r't=(.*?)s',time)
        if match:
          start_time = int(match[0])
    except:
      printMessage("WARNING", "Failed to get start time")
      start_time = 0
  return start_time

def prepareUrl(url):
  url = url.replace("https", "http") # remove secure
  start_time = tryToGetStartTime(url)
  url = url.split("&")[0] # ignore &t timestamps.
  return url, start_time

def generateFilename(name, extension):
  filename = name
  count = 1
  while os.path.isfile(filename + '.' + extension):
    filename = name + str(count)
    count += 1
  return filename + '.' + extension

def get_sec(time_str):
  h, m, s = time_str.split(':')
  return int(h) * 3600 + int(m) * 60 + int(s)

def getVideoDetails():
  ydl_opts = {}
  with youtube_dl.YoutubeDL(ydl_opts) as ydl:
    info_dict = ydl.extract_info(url, download=False)
    video_id = info_dict.get("id", None)
    video_title = info_dict.get('title', None)

    command = "youtube-dl -j " + video_id

    try:
      response = subprocess.check_output(command, shell=True)
    except Exception as e:
      printMessage("ERROR", "Unable to get video details from URL, quitting")
      exit(-1)

    json_dict = json.loads(response)
    end_time = json_dict["duration"]

    return video_id, video_title, end_time

def downloadM4a():
  printMessage("HEADER", "Downloading m4a")

  if (os.path.isfile(filename) == False):
    command = 'youtube-dl -f 140 --embed-thumbnail --add-metadata --output ' + filename + ' ' + url
    try:
      subprocess.call(command, shell=True)
    except Exception as e:
      printMessage("ERROR", "Unable to download m4a from URL, quitting")
      exit(-1)

def format_filename(s): #https://gist.github.com/seanh/93666
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    my_filename = ''.join(c for c in s if c in valid_chars)
    my_filename = my_filename.replace(' ','_') # I don't like spaces in filenames.
    return my_filename

def convertToMp3():
  printMessage("HEADER", "Converting m4a to mp3")

  modified_video_title = format_filename(video_title)
  audio_title = "output.nosync/" + '"' + modified_video_title + '"' + '.mp3' 
  options = ' -map_metadata 0 -acodec libmp3lame -ab 128k '
  start_stop_times = ' -ss ' + str(start_time) + ' -t ' + str(duration)

  ffmpeg = 'ffmpeg -i ' + filename + start_stop_times + options + audio_title

  delete_prev_mp3 = 'rm ' + audio_title
  try:
    subprocess.call(delete_prev_mp3, shell=True)
  except:
    printMessage("ERROR", "Unable to delete previous mp3, quitting")
    exit(-1)

  printMessage("HEADER", ffmpeg)
  try:
    subprocess.call(ffmpeg, shell=True)
  except Exception as e:
    printMessage("ERROR", "Unable to convert m4a to mp3, quitting")
    exit(-1)

  return modified_video_title

def deleteM4a():
  delete_m4a = 'rm ' + filename
  try:
    subprocess.call(delete_m4a, shell=True)
  except Exception as e:
    printMessage("ERROR", "Unable to delete m4a, quitting")
    exit(-1)

#######################################################


if (len(sys.argv) < 2):
  printMessage("FAIL", 'Need to pass URL to download audio from')
  sys.exit(-1)

initialUrl = sys.argv[1]

start_time = 0
url = getShareUrl(sys.argv[1])
if (url == -1):
  url, start_time = prepareUrl(initialUrl)

video_id, video_title, end_time = getVideoDetails()
filename = "temp.nosync/" + video_id + ".m4a"

if (len(sys.argv) > 2):
  start_time = get_sec(sys.argv[2])

if (len(sys.argv) > 3):
  end_time = get_sec(sys.argv[3])

if ((len(sys.argv) > 2) or (start_time != 0)):
  video_title = video_title + '_cropped'

print "\nStart time = {}s".format(start_time)
print "End time = {}s".format(end_time)
duration = end_time - start_time
print "\n{}".format(video_title)
print "Duration = {}s\n".format(duration)

if (duration < 0):
  printMessage("FAIL", "End time must be after start time")
  sys.exit(-1)

# Download initial .m4a
downloadM4a()

# Convert .m4a into .mp3
modified_video_title = convertToMp3()

# Delete initial .m4a
deleteM4a()

printMessage("SUCCESS", "Successfully downloaded: " + modified_video_title + ".mp3")
exit(0)