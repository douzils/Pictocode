; installer.iss
[Setup]
AppName=Pictocode
AppVersion=0.1.0
DefaultDirName={pf}\Pictocode
DefaultGroupName=Pictocode
OutputBaseFilename=Pictocode-Setup
Compression=lzma
SolidCompression=yes

[Files]
; On inclut tout le contenu du dossier dist\Pictocode
Source: "dist\Pictocode\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{group}\Pictocode"; Filename: "{app}\Pictocode.exe"
Name: "{group}\Désinstaller Pictocode"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\Pictocode.exe"; Description: "Lancer Pictocode"; Flags: nowait postinstall skipifsilent
