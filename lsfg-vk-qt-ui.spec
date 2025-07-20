block_cipher = None

a = Analysis(
    ['src/lsfg-vk-qt-ui.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    excludes=[
        'PySide6.QtWebEngineCore', 'PySide6.QtQml', 'PySide6.QtQuick',
        'PySide6.QtQuickWidgets', 'PySide6.QtWebSockets', 'PySide6.QtTest',
        'PySide6.QtNetwork', 'PySide6.QtSerialPort', 'PySide6.QtPositioning',
        'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets', 'PySide6.QtBluetooth',
        'PySide6.Qt3DCore', 'PySide6.Qt3DInput', 'PySide6.Qt3DLogic',
        'PySide6.Qt3DRender', 'PySide6.Qt3DAnimation', 'PySide6.Qt3DExtras',
        'PySide6.QtPrintSupport', 'PySide6.QtSvg', 'PySide6.QtUiTools',
        'PySide6.QtWebChannel',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='lsfg-vk-qt-ui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=True,
    upx=True,
    name='lsfg-vk-qt-ui',
)
