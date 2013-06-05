##
## NOTE: '##' represents a Mako comment and will not be in the final output!
##
#---------------------------------------------------------------------------------------------------
# ${vars.productName} Installer Setup
#---------------------------------------------------------------------------------------------------

# Name of the product
$PRODUCT ${vars.productName}

# Version of the product
$VERSION ${vars.version}

# Macro that is used as standalone application
$STANDALONE_MACRONAME ${vars.moduleName}

# Include release DLL's and executables
$RELEASE ${vars.releaseFlag}
# Include debug DLL's and executables
$DEBUG   ${vars.debugFlag}

# by default the ModuleDependencyAnalyzer detects the dependencies of the application macro
$STANDALONE_AUTO_DETECT_MODULE_DEPENDENCIES 1

# arguments that are passed to the MeVisLab Macro
# $STANDALONE_APPLICATION_ARGS arg1 arg2

%if vars.enableFinishPage:
# enable the installer finish page on Windows, which allows to start the application after it was installed
# and/or to show additional information.
$STANDALONE_FINISHPAGE 1

# Overwrite the title of the finish page
#$INSTALLER_FINISHPAGE_TITLE Your Title

# Overwrite the text of the finish page
#$INSTALLER_FINISHPAGE_TEXT Alternative text...

# Show a link on the finish page
#$INSTALLER_FINISHPAGE_LINK Your Link Text
#$INSTALLER_FINISHPAGE_LINK_LOCATION http://www.whatever.com 

# Overwrite the run application text  
#$INSTALLER_FINISHPAGE_RUN_TEXT

# Uncheck the run check box by default
#$INSTALLER_FINISHPAGE_RUN_NOTCHECKED 1

# Show a checkbox for readme/documentation
#$INSTALLER_FINISHPAGE_SHOWREADME Packages/YourPackageGroup/YourPackage/.../SomeFile.[html/PDF/txt]

# Text that is shown on the readme checkbox
#$INSTALLER_FINISHPAGE_SHOWREADME_TEXT Open documentation

# Uncheck the show readme check box by default
$INSTALLER_FINISHPAGE_SHOWREADME_NOTCHECKED 1

%endif
##
##
# additional prefs file options (up to 10)
#$PREFSFILE_OPTION1 MLCacheSizeInMB = 1024
#$PREFSFILE_OPTION2 OtherOption = OtherValue

%if vars.precompilePythonFiles:
# precompile all python files
$INSTALLER_COMPILE_ALL_PYTHON_FILES 1
%if vars.excludeOriginalPythonFiles:
# remove all *.py files
$INSTALLER_EXCLUDE_UNCOMPILED_PYTHON_FILES 1
%endif

%endif
##
##
%if vars.createPackagesZip:
# file I/O optimization: all *.(py|pyc|script|def|mlab|js|txt|png) files are included
# in Packages.zip next to the Packages directory. This will speed up loading those files.
$STANDALONE_CREATE_PACKAGES_ZIP 1

%endif
##
##
# arguments that are passed to the MeVisLab Starter
$STANDALONE_STARTER_ARGS ${vars.cmdLineArgs}

%if vars.copiedSplashScreenImage:
# the splash image that is used instead of the MeVisLab Splash Image
$STANDALONE_SPLASHIMAGE $(LOCAL)/${vars.copiedSplashScreenImage}

%endif
##
##
%if vars.copiedHeaderImageWin32:
# set the bitmap that is used in the installer header
$INSTALLER_HEADERBMP $(LOCAL)/${vars.copiedHeaderImageWin32}

%endif
##
##
%if vars.copiedDSStoreFileMac:
# set the store of custom attributes of the disk image (DMG)'s root folder
$INSTALLER_MACX_DSSTORE $(LOCAL)/${vars.copiedDSStoreFileMac}

%endif
##
##
%if vars.copiedHeaderImageMac:
# set the png that is used as background image in the mac installer
# requires INSTALLER_MACX_DSSTORE to be set as well
$INSTALLER_MACX_IMAGE $(LOCAL)/${vars.copiedHeaderImageMac}

%endif
##
##
%if vars.copiedIconFile:
# set the icon file for the application
$STANDALONE_ICON $(LOCAL)/${vars.copiedIconFile}

%endif
##
##
%if vars.licenseFileNeeded:
# License used for signing the files:
$SIGN_LICENSE_FILE ${vars.licensePath}

%endif
##
##
# license file to be embedded into application
#$STANDALONE_LICENSEKEY $(LOCAL)/license.dat

# use native, Aqua-style GUI for Mac OS X applications
#$MACX_INFO_APPSTYLE_NATIVE  1

#---------------------------------------------------------------------------------------------------

INCLUDE ${vars.defaultStandaloneSetupInclude}

#---------------------------------------------------------------------------------------------------

${vars.userFileSection}
##
##
%if vars.createPackagesZip:

# This can be uncommented to add more files to Packages.zip or to exclude
# files from Packages.zip that should stay in the filesystem.
# Note: the paths in the collect statements must be relative to the Packages directory!
#       (e.g. - MeVisLab/Standard/Modules/Examples)
#ZIP_COLLECT_BEGIN $(STANDALONE_PACKAGES_ZIP_FILE)
#+ relative/path/to/add
#- relative/path/to/remove
#ZIP_COLLECT_END

%endif
