[app]
title = System Pop Art
package.name = wifimessenger.v47
package.domain = org.campus.sync
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,v47
version = 4.7

# Visual Assets (Upload your own icon.png and splash.png later)
icon.filename = icon.png
presplash.filename = splash.png

requirements = python3,kivy,pyjnius
orientation = portrait
android.archs = arm64-v8a, armeabi-v7a
android.api = 34
android.minapi = 21

# Permissions for Offline Mesh & File Sharing
android.permissions = INTERNET, ACCESS_WIFI_STATE, CHANGE_WIFI_MULTICAST_STATE, WAKE_LOCK, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE
android.wakelock = True
