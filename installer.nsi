; ==============================================================================
; tchMaterial-parser-for-Windows7 — NSIS 3.09 安装脚本
; 打包对象：PyInstaller onedir（文件夹模式）产物 dist/tchMaterial-parser-for-Windows7/
; 编译命令：makensis /V2 /DAPP_VERSION=1.0.0 installer.nsi
; 产物：    dist/tchMaterial-parser-for-Windows7-Setup-<version>.exe
; 依赖：    NSIS 3.09（Unicode），需 nsExec 插件（官方自带）
; ==============================================================================

!ifndef APP_VERSION
  !define APP_VERSION "1.0.0"
!endif

!define APP_NAME      "国家中小学智慧教育平台 资源下载工具"
!define APP_PUBLISHER "肥宅水水呀 / Minecraftgoose"
!define APP_DIR_NAME  "tchMaterial-parser-for-Windows7"
!define APP_EXE       "tchMaterial-parser-for-Windows7.exe"
!define APP_URL       "https://github.com/Minecraftgoose/tchMaterial-parser-for-Windows7"
!define UNINST_KEY    "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_DIR_NAME}"
!define OUT_NAME      "tchMaterial-parser-for-Windows7-Setup-${APP_VERSION}.exe"

Unicode True
!include "MUI2.nsh"
!include "LogicLib.nsh"

Name "${APP_NAME} ${APP_VERSION} (Windows 7)"
OutFile "dist\${OUT_NAME}"
BrandingText "${APP_NAME} ${APP_VERSION}"

InstallDir "$PROGRAMFILES64\${APP_DIR_NAME}"
InstallDirRegKey HKLM "${UNINST_KEY}" "InstallLocation"
RequestExecutionLevel admin
SetCompressor /SOLID lzma
ShowInstDetails show
ShowUninstDetails show

!define MUI_ICON   "assets\icon.ico"
!define MUI_UNICON "assets\icon.ico"
!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "运行 ${APP_NAME}"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "SimpChinese"

; ------------------------------------------------------------------------------
; 安装：整目录递归铺开（含 _internal/），写卸载信息，建快捷方式
; ------------------------------------------------------------------------------
Section "主程序 (必须)" SEC_MAIN
  SetOutPath "$INSTDIR"

  ; 覆盖安装前若存在旧版，先静默卸载，避免残留文件版本混杂
  ${If} ${FileExists} "$INSTDIR\uninstall.exe"
    DetailPrint "检测到旧版本，正在静默卸载…"
    ExecWait '"$INSTDIR\uninstall.exe" /S _?=$INSTDIR'
    Delete "$INSTDIR\uninstall.exe"
  ${EndIf}

  ; onedir 产物：exe 与 _internal/ 一并递归打包
  File /r "dist\${APP_DIR_NAME}\*.*"

  WriteUninstaller "$INSTDIR\uninstall.exe"

  ; 控制面板「程序和功能」条目
  WriteRegStr   HKLM "${UNINST_KEY}" "DisplayName"     "${APP_NAME} (Windows 7)"
  WriteRegStr   HKLM "${UNINST_KEY}" "DisplayVersion"  "${APP_VERSION}"
  WriteRegStr   HKLM "${UNINST_KEY}" "Publisher"       "${APP_PUBLISHER}"
  WriteRegStr   HKLM "${UNINST_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr   HKLM "${UNINST_KEY}" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegStr   HKLM "${UNINST_KEY}" "QuietUninstallString" '"$INSTDIR\uninstall.exe" /S'
  WriteRegStr   HKLM "${UNINST_KEY}" "DisplayIcon"     "$INSTDIR\${APP_EXE}"
  WriteRegStr   HKLM "${UNINST_KEY}" "URLInfoAbout"    "${APP_URL}"
  WriteRegDWORD HKLM "${UNINST_KEY}" "NoModify" 1
  WriteRegDWORD HKLM "${UNINST_KEY}" "NoRepair" 1

  ; 开始菜单 + 桌面快捷方式
  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  CreateShortCut  "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
  CreateShortCut  "$SMPROGRAMS\${APP_NAME}\卸载 ${APP_NAME}.lnk" "$INSTDIR\uninstall.exe"
  CreateShortCut  "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0

  DetailPrint "安装完成：$INSTDIR"
SectionEnd

; ------------------------------------------------------------------------------
; 卸载：结束进程 → 清目录 → 清快捷方式与注册表
; ------------------------------------------------------------------------------
Section "Uninstall"
  ; 主程序无窗运行时也会驻留进程，先尝试结束，避免文件占用导致删不干净
  nsExec::Exec 'taskkill /F /IM ${APP_EXE}'
  Pop $0

  RMDir /r "$INSTDIR"
  Delete "$DESKTOP\${APP_NAME}.lnk"
  RMDir /r "$SMPROGRAMS\${APP_NAME}"
  DeleteRegKey HKLM "${UNINST_KEY}"
SectionEnd
