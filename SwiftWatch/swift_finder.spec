# -*- mode: python -*-

block_cipher = None


a = Analysis(['swift_finder.py'],
             pathex=["/Users/colbytimm/Documents/Colby's Folder/Learning/Programming/Automating-the-Collection-of-Bird-Data-from-Video-Footage/gui"],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='swift_finder',
          debug=False,
          strip=False,
          upx=True,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='swift_finder')
app = BUNDLE(coll,
             name='swift_finder.app',
             icon=None,
             bundle_identifier=None)
