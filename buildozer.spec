[app]

# (str) Title of your application
title = HyperNova

# (str) Package name
package.name = hypernova

# (str) Package domain (needed for android/ios packaging)
package.domain = com.hypernova.trading

# (str) Source code where the main.py lives
source.dir = HyperNova

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,html,css,js,json,db

# (str) Application versioning (method 1)
version = 1.0.0

# (list) Pure-Python Requirements (Ultra fast build, zero C++ compile crashes)
requirements = python3,flask,requests,urllib3,flask_socketio,flask_cors,setuptools

# (str) Supported orientation
orientation = portrait

# (list) Permissions
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WAKE_LOCK,FOREGROUND_SERVICE,RECEIVE_BOOT_COMPLETED

# (str) Bootstrap for web applications
p4a.bootstrap = webview
p4a.port = 5000

# (int) Target Android API
android.api = 34
android.minapi = 24
android.ndk = 25b
android.skip_update = False
android.accept_sdk_license = True

# (list) Android service to run in background (7/24 Persistent Engine)
android.services = HyperNovaService:run_live.py:foreground

[buildozer]
log_level = 2
warn_on_root = 0

