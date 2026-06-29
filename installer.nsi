!define APPNAME "ClubMessenger"
!define COMPANY "C. SALVAT"
!define VERSION "1.3.3"

Name "${APPNAME}"
BrandingText "${COMPANY}"

OutFile "Setup_${APPNAME}_v${VERSION}.exe"
InstallDir "$PROGRAMFILES\${APPNAME}"

VIProductVersion "${VERSION}.0"
VIFileVersion "${VERSION}.0"
VIAddVersionKey "FileVersion" "${VERSION}.0"
VIAddVersionKey "ProductName" "${APPNAME}"
VIAddVersionKey "CompanyName" "${COMPANY}"
VIAddVersionKey "FileDescription" "Installateur de ${APPNAME}"
VIAddVersionKey "LegalCopyright" "© 2026 ${COMPANY}"

!include "MUI2.nsh"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_LANGUAGE "French"

; --- Application principale
Section "Application principale" SEC_MAIN
    SectionIn RO
    SetOutPath "$INSTDIR"
    File "dist\ClubMessenger.exe"
    WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

; --- Raccourcis
Section "Raccourcis" SEC_SHORTCUTS
    CreateDirectory "$SMPROGRAMS\${APPNAME}"
    CreateShortCut "$SMPROGRAMS\${APPNAME}\${APPNAME}.lnk" "$INSTDIR\ClubMessenger.exe"
    CreateShortCut "$DESKTOP\${APPNAME}.lnk" "$INSTDIR\ClubMessenger.exe"
SectionEnd


; --- Désinstallation
Section "Uninstall"
    Delete "$INSTDIR\ClubMessenger.exe"
    Delete "$INSTDIR\Uninstall.exe"
    RMDir "$INSTDIR"

    Delete "$DESKTOP\${APPNAME}.lnk"
    RMDir /r "$SMPROGRAMS\${APPNAME}"

    ; On SUPPRIME la base utilisateur
	Delete "$PROFILE\.clubmessenger\clubmessenger.db"
    RMDir "$PROFILE\.clubmessenger"

    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}"
SectionEnd

Function .onInstSuccess
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayName" "${APPNAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "Publisher" "${COMPANY}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayVersion" "${VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "UninstallString" "$INSTDIR\Uninstall.exe"
FunctionEnd

