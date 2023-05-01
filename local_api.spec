# -*- mode: python ; coding: utf-8 -*-

import shutil, os, sys, subprocess

block_cipher = None

subprocess.run(['bumpversion', 'build'])

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[('ext_lib\\ThermoFisher.CommonCore.RawFileReader.dll', '.'), ('ext_lib\\ThermoFisher.CommonCore.Data.dll', '.')],
    datas=[('config.toml', '.')],
    hiddenimports=['sqlite3'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='local_api',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version="file_version_info.txt"
)


shutil.copyfile('config.toml', '{0}/config.toml.example'.format(DISTPATH))
# timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
# tsver = "timestamp_version.txt"
# with open('{0}/'.format(DISTPATH) + tsver, 'w') as file:
#    file.write(timestamp)
# shutil.copyfile(tsver, '{0}/'.format(DISTPATH) + tsver)
verfile = "uploader_version.txt"
shutil.copyfile(verfile, '{0}/'.format(DISTPATH) + verfile)
#shortcut = "update_uploader.lnk"
#batch = "update_uploader.bat"
## tmp = tempfile.TemporaryFile()
#with open('{0}/'.format(DISTPATH) + batch, 'w') as bat:
#    command = "local_api.exe --update"
#    bat.write(command)
