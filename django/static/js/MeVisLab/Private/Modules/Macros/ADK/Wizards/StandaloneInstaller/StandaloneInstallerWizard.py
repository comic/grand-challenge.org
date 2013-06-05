# -----------------------------------------------------------------------
# 
# Copyright (c) 2001-2013, MeVis Medical Solutions AG, Bremen, Germany
# ALL RIGHTS RESERVED
# 
# THIS FILE CONTAINS CONFIDENTIAL AND PROPRIETARY INFORMATION OF MEVIS 
# MEDICAL SOLUTIONS AG. ANY DUPLICATION, MODIFICATION, DISTRIBUTION, OR 
# DISCLOSURE IN ANY FORM, IN WHOLE, OR IN PART, IS STRICTLY PROHIBITED 
# WITHOUT THE PRIOR EXPRESS WRITTEN PERMISSION OF MEVIS MEDICAL SOLUTIONS 
# AG.
# 
#----------------------------------------------------------------------------------
#! Standalone Installer Wizard
#!
# \file    StandaloneInstallerWizard.py
# \author  Florian Link
# \date    02/2005
#
#----------------------------------------------------------------------------------

from mevis import *

_step = 0

_titles = [
    "Welcome",
    "General Settings",
    "Manual File Lists",
    "Application Options",
    "Installer Options"]

_infos = [
    "Start from an existing macro module",
    "General settings for your standalone application",
    "Specify additional files that will not be detected by the module dependency analyzer",
    "Additional settings for your application",
    "Additional installer settings which are not required"]

# --- Initialization

# Initialize module
def InitModule():
  InitFields()
  UpdateCreateEnable()

# Initialize field values
def InitFields():
  info = MLAB.priv().licenseInformation()
  if info["valid"]:
    ctx.field("licensePath").setStringValue(info["filename"])
  ctx.field("availableMacros").value = ",".join(MLAB.allMacroModules())

def InitWindow():
  global _step

  _step = 0
  UpdateTab()

def ExitWindow():
  pass


# --- Field updates

# Update createEnable flag
def UpdateCreateEnable():
  moduleName = ctx.field("moduleName").stringValue()
  targetPackage = ctx.field("ModuleWizardPackageSelector.valid").value
  ctx.field("createEnable").setBoolValue(bool(moduleName) and targetPackage)

# Update nextEnable flag
def UpdateNextEnable():
  flag = True
  if _step == 0:
    moduleName  = ctx.field("moduleName").stringValue()
    targetPackage   = ctx.field("ModuleWizardPackageSelector.valid").value
    flag = moduleName and targetPackage
  if _step >= len(_titles)-1:
    flag = False
  ctx.field("nextEnable").value = flag

# Perform "Next"
def NextStep():
  global _step
  _step += 1
  UpdateTab()

# Perform "Prev"
def PrevStep():
  global _step
  _step -= 1
  UpdateTab()

# Update tab view item
def UpdateTab():
  ctx.controlDebug("tab").selectTabAtIndex(_step)
  ctx.field("stepTitle").value = _titles[_step]
  ctx.field("stepInfo").value = _infos[_step]
  UpdateNextEnable()

def fv(field):
  return ctx.field(field).value

def ConvertImage(src, target, type):
  if MLABFileManager.exists(src):
    ok = MLABGraphic.convertImage(src, target)
    if not ok:
      MLAB.showWarning("Could not convert " + type + " file: " + src)
  else:
    MLAB.showWarning("The " + type + " file does not exist: " + src)
    
# --- Code creation

# Create code from template list
def CreateCode ():
  cmdline = []

  if not ctx.field("productName").value:
    ctx.field("productName").value = ctx.field("moduleName").value
  
  iconFileWin32  = fv("iconFileWin32")
  iconFileMac    = fv("iconFileMac")
  headerImageWin32 = fv("headerImageWin32")
  dsstoreFileMac = fv("dsstoreFileMac")
  headerImageMac = fv("headerImageMac")
  splashFile  = fv("splashScreenImage")
  productName = fv("productName")
  moduleName  = fv("moduleName")
  
  package1 = MLABPackageManager.packageByIdentifier(fv("packageIdentifier"))
  if not package1:
    MLAB.logError("package " + fv("packageIdentifier") + " not found!")
    return
  targetDir = package1.path() + "/Configuration/Installers/" + productName
  ctx.field("targetDir").value = targetDir
  
  modes = {}
  modes["MAXIMIZED"] = "-showmaximized"
  modes["FULLSCREEN"] = "-showfullscreen"
  modes["NORMAL"] = ""
  cmdline.append(modes[fv("windowMode")])

  splashTarget = ""
  ctx.field("copiedSplashScreenImage").value = ""
  splashTarget = targetDir+"/"+productName+"Splash.png"
  if splashFile:
    ctx.field("copiedSplashScreenImage").value = productName+"Splash.png"

  if ctx.field("diagnosisFlag").value:
    cmdline.append("-diagnosis")
  
  iconTarget = ""
  if iconFileWin32 or iconFileMac:
    iconTarget = targetDir+"/"+productName
    ctx.field("copiedIconFile").value = productName
  else:
    ctx.field("copiedIconFile").value = ""
  headerTargetWin32 = ""
  if headerImageWin32:
    headerTargetWin32 = targetDir+"/"+productName+".bmp"
    ctx.field("copiedHeaderImageWin32").value = productName+".bmp"
  else:
    ctx.field("copiedHeaderImageWin32").value = ""

  dsstoreTargetMac = ""
  if dsstoreFileMac:
    dsstoreTargetMac = targetDir+"/"+productName+".DSStore"
    ctx.field("copiedDSStoreFileMac").value = productName+".DSStore"
  else:
    ctx.field("copiedDSStoreFileMac").value = ""
  
  headerTargetMac = ""
  if headerImageMac:
    headerTargetMac = targetDir+"/"+productName+".png"
    ctx.field("copiedHeaderImageMac").value = productName+".png"
  else:
    ctx.field("copiedHeaderImageMac").value = ""

  ctx.field("cmdLineArgs").value = " ".join(cmdline)
  
  userFileSection1  = ""
  if ctx.field("assembleInstallerScript").value:
    userFileSection1 += "\n# additional files/commands\n"
    userFileSection1 += ctx.field("assembleInstallerScript").value + "\n"
  ctx.field("userFileSection").value = userFileSection1

  templateListPath = ctx.field("templateListPath").stringValue()
  CreateCodeFromTemplateList(templateListPath)

  # Clean up temporary field
  ctx.field("userFileSection").value = ""


  if iconTarget:
    if iconFileWin32:
      if iconFileWin32.endswith(".ico"):
        MLABFileManager.copy(iconFileWin32, iconTarget + ".ico")
      else:
        ConvertImage(iconFileWin32, iconTarget + ".ico", "windows icon")
    if iconFileMac:
      if iconFileMac.endswith(".icns"):
        MLABFileManager.copy(iconFileMac, iconTarget + ".icns")
      else:
        ConvertImage(iconFileMac, iconTarget + ".icns", "mac icon")

  if headerTargetWin32:
    ConvertImage(headerImageWin32, headerTargetWin32, "windows header image")
  if dsstoreTargetMac:
    MLABFileManager.copy(dsstoreFileMac, dsstoreTargetMac)
  if headerTargetMac:
    ConvertImage(headerImageMac, headerTargetMac, "mac header image")
  if splashFile:
    ConvertImage(splashFile, splashTarget, "splash image")
  
  txt = "All configuration files for your installer have been generated at<p>"
  txt += "<a href=\"mlab_open:"+ctx.field("targetDir").value + "\">"+ctx.field("targetDir").value+"<a><p>"
  
  if not MLAB.isMacOS():
    txt += "Starting the generated batch file <i>"+ctx.field("productName").value+".bat</i> will create an installer file named <i>" + ctx.field("productName").value + ".exe</i>.<p>"
    txt += "You can now click the <b>Create Installer</b> button to run the batch file. "
    txt += "Alternatively, you can run the created batch file at a later time or inside of your build system."
  
  ctx.field("createCodeDialogText").value = txt
  ctx.showWindow("CreateCodeDialog")

def CheckModuleName():
  mod = ctx.field("moduleName").value
  moduleInfo = MLAB.moduleInfo(mod)
  if "type" in moduleInfo:
    if moduleInfo["type"] != "MacroModule":
      MLAB.showWarning("The module <b>"+mod+"</b> is not a MacroModule!")
  else:
    MLAB.showWarning("The module <b>"+mod+"</b> does not exist!")

def createInstaller():
  proc = MLAB.newProcess()
  proc.addArgument(MLABFileManager.getExecutable("ToolRunner"))
  proc.addArgument(ctx.field("targetDir").value + "/" + ctx.field("productName").value + ".mlinstall")
  proc.run()

def checkExternalTools():
  proc = MLAB.newProcess()
  proc.addArgument(MLABFileManager.getExecutable("ToolRunner"))
  proc.addArgument("-toolcheck")
  proc.run()

def browseOutputDirectory():
  MLAB.openFile(ctx.field("targetDir").value)

def createApplicationLicense():
  proc = MLAB.newProcess()
  proc.addArgument(MLABFileManager.getExecutable("ApplicationLicenseManager"))
  proc.addArgument(ctx.field("targetDir").value + "/" + ctx.field("productName").value + ".mlinstall")
  proc.run()

def packageIdentifierChanged(field):
  ident = ctx.field("packageIdentifier").value
  if not MLABPackageManager.packageByIdentifier(ident):
    return
  try:
    group, name = ident.split("/", 1)
  except:
    group = ""
    name = ""
  if group.startswith("FME"):
    ctx.field("licenseFileNeeded").value = False
    ctx.field("defaultStandaloneSetupInclude").value = "$(MLAB_FMEwork_General)/Configuration/Installers/Shared/Standalone/defaultFraunhoferMEVISStandaloneSetup.mli"
  else:
    ctx.field("licenseFileNeeded").value = True
    ctx.field("defaultStandaloneSetupInclude").value = "$(MLAB_MeVisLab_IDE)/Configuration/Installers/Shared/Standalone/defaultStandaloneSetup.mli"

def setMeVisStandaloneLicenseDefault():
  lic = MLAB.variable("MLAB_MeVis_Foundation")+"/Configuration/Installers/Shared/Core/Resources/MeVisStandaloneApplicationLicense.dat"
  ctx.field("licensePath").value = lic
#//# MeVis signature v1
#//# key: MFowDQYJKoZIhvcNAQEBBQADSQAwRgJBANEfsmYse2e1dRhkQ9AQbreCq9uxwzWLoGom13MNYmyfwoJqQOEXljLFAgw2eEjaT12G4CdqKWhRxh9ANP6n7GMCARE=:VI/mB8bT4u+mRtf/ru8yUQi8BzpaS3UeL2x62YxsUYnVqCWuLrVNLiukIIjnJMKQXlc8ezmgOIcVAV7pgvgKpQ==
#//# owner: MeVis
#//# date: 2013-04-10T22:33:03
#//# hash: RqfeNFYoJy5aAgj+ZegDU2rU3Qwb3pKc2JfPEQNKz8A7Myor+vzZ0ZRnkhN1phSEXhW/DLv3tcwONdVpp1rhgg==
#//# MeVis end
