[app]

# (str) Title of your application
title = HyperNova

# (str) Package name
package.name = hypernova

# (str) Package domain (needed for android/ios packaging)
package.domain = com.hypernova.trading

# (str) Source code where the main.py lives
source.dir = ../HyperNova

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,html,css,js,json,db

# (str) Application versioning (method 1)
version = 1.0.0

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,flask,requests,urllib3,numpy,pandas,pandas_ta,flask_socketio,flask_cors,setuptools

# (str) Presplash of the application
#presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon of the application
#icon.filename = %(source.dir)s/data/icon.png

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (list) Permissions
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WAKE_LOCK,FOREGROUND_SERVICE,RECEIVE_BOOT_COMPLETED

# (int) Target Android API, should be as high as possible.
android.api = 34

# (int) Minimum API your APK / AAB will support.
android.minapi = 24

# (str) Android NDK version to use
android.ndk = 25b

# (bool) If True, then skip trying to update the Android sdk
android.skip_update = False

# (bool) If True, then automatically accept SDK license
android.accept_sdk_license = True

# (list) Android service to run in background (7/24 Persistent Engine)
android.services = HyperNovaService:run_live.py:foreground

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
