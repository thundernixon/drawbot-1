from __future__ import print_function

import py2app
from distutils.core import setup
from distutils.sysconfig import get_python_lib
import os
import sys
import subprocess
import shutil
import datetime
import re
from plistlib import readPlist, writePlist

from fontTools.misc.py23 import PY3

from drawBot.drawBotSettings import __version__, appName

rawTimeStamp = datetime.datetime.today()
timeStamp = rawTimeStamp.strftime("%y%m%d%H%M")


_identifierPat = re.compile("[A-Za-z_][A-Za-z_0-9]*$")
def _isIdentifier(s):
    """Return True if argument `s` is a valid Python identifier."""
    return _identifierPat.match(s) is not None

def _findModules(root, extensions, skip, parent=""):
    """Yield all modules and packages and their submodules and subpackages found at `root`.
    Nested folders that do _not_ contain an __init__.py file are assumed to also be on sys.path.
    `extensions` should be a set of allowed file extensions (without the .). `skip` should be
    a set of file or folder names to skip. The `parent` argument is for internal use only.
    """
    for fileName in os.listdir(root):
        if fileName in skip:
            continue
        path = os.path.join(root, fileName)
        if os.path.isdir(path):
            if _isIdentifier(fileName) and os.path.exists(os.path.join(path, "__init__.py")):
                if parent:
                    packageName = parent + "." + fileName
                else:
                    packageName = fileName
                for module in _findModules(path, extensions, skip, packageName):
                    yield module
            elif not parent:
                for module in _findModules(path, extensions, skip, ""):
                    yield module
        elif "." in fileName:
            moduleName, ext = fileName.split(".", 1)
            if ext in extensions and _isIdentifier(moduleName):
                if parent and moduleName == "__init__":
                    yield parent
                elif parent:
                    yield parent + "." + moduleName
                else:
                    yield moduleName

def getStdLibModules():
    """Return a list of all module names that are part of the Python Standard Library, and
    a flag indicating whether we are running from a pre-installed ("/System") python or not.
    """
    versionDict = dict(major=sys.version_info.major, minor=sys.version_info.minor)
    stdLibPath = get_python_lib(standard_lib=True)
    isSystemPython = stdLibPath.startswith("/System/")
    extensions = {"py"}
    if PY3:
        extensions.add("cpython-%s%sm-darwin.so" % (sys.version_info.major, sys.version_info.minor))
    else:
        extensions.add("so")
    skip = {"site-packages", "test", "turtledemo", "tkinter", "idlelib", "lib2to3"}
    return list(_findModules(stdLibPath, extensions, skip)), isSystemPython


stdLibModules, isSystemPython = getStdLibModules()
if isSystemPython:
    # We use the Python Standard Library from /System, so no need to include anything extra
    stdLibIncludes = []
else:
    # non-/System Python, we should include the entire Python Standard Library
    stdLibIncludes = stdLibModules


def getValueFromSysArgv(key, default=None, isBooleanFlag=False):
    if key in sys.argv:
        try:
            i = sys.argv.index(key)
            if isBooleanFlag:
                value = True
            else:
                value = sys.argv[i + 1]
                del sys.argv[i + 1]
            sys.argv.remove(key)
            return value
        except Exception:
            pass
    return default


codeSignDeveloperName = getValueFromSysArgv("--codesign")

ftpHost = getValueFromSysArgv("--ftphost")
ftpPath = getValueFromSysArgv("--ftppath")
ftpLogin = getValueFromSysArgv("--ftplogin")
ftpPassword = getValueFromSysArgv("--ftppassword")
buildDMG = getValueFromSysArgv("--dmg", isBooleanFlag=True)
runTests = getValueFromSysArgv("--runTests", isBooleanFlag=True)

osxMinVersion = "10.9.0"

iconFile = "DrawBot.icns"

plist = dict(

    CFBundleDocumentTypes=[
        dict(
            CFBundleTypeExtensions=["py"],
            CFBundleTypeName="Python Source File",
            CFBundleTypeRole="Editor",
            CFBundleTypeIconFile="pythonIcon.icns",
            NSDocumentClass="DrawBotDocument",
        ),
        dict(
            CFBundleTypeExtensions=["drawbot"],
            CFBundleTypeName="DrawBot Package",
            CFBundleTypeRole="Viewer",
            CFBundleTypeIconFile="drawbotPackageIcon.icns",
            NSDocumentClass="DrawBotDocument",
            LSTypeIsPackage=True,
        ),
    ],
    CFBundleIdentifier="com.drawbot",
    LSMinimumSystemVersion=osxMinVersion,
    LSApplicationCategoryType="public.app-category.graphics-design",
    LSMinimumSystemVersionByArchitecture=dict(i386=osxMinVersion, x86_64=osxMinVersion),
    LSArchitecturePriority=["x86_64", "i386"],
    CFBundleShortVersionString=__version__,
    CFBundleVersion=__version__,
    CFBundleIconFile=iconFile,
    NSHumanReadableCopyright="Copyright by Just van Rossum and Frederik Berlaen.",
    CFBundleURLTypes=[
        dict(
            CFBundleURLName="com.drawbot",
            CFBundleURLSchemes=[appName.lower()])
    ],
)


dataFiles = [
    "Resources/English.lproj",
    # os.path.dirname(vanilla.__file__),
]

# add all images
for fileName in os.listdir("Resources/Images"):
    baseName, extension = os.path.splitext(fileName)
    if extension.lower() in [".png", ".icns"]:
        fullPath = os.path.join("Resources/Images", fileName)
        dataFiles.append(fullPath)

# add all external tools
for fileName in os.listdir("Resources/externalTools"):
    fullPath = os.path.join("Resources/externalTools", fileName)
    dataFiles.append(fullPath)

# build
setup(
    name=appName,
    data_files=dataFiles,
    app=[dict(script="DrawBot.py", plist=plist)],
    options=dict(
        py2app=dict(
            packages=[
                'vanilla',
                'defcon',
                'defconAppKit',
                'fontParts',
                'mutatorMath',
                'woffTools',
                'compositor',
                'feaTools2',
                'ufo2svg',
                'fontPens',
                'booleanOperations',
                # 'pyclipper',
                'pygments',
                'jedi',
                'fontTools',
                # 'xml'
                'pkg_resources',
            ],
            includes=[
                # 'csv',
                # 'this'
            ] + stdLibIncludes,
            excludes=[
                "numpy",
                "scipy",
                "matplotlib",
                "PIL",
                "pygame",
                "wx",
                "sphinx",
                "jinja2",
            ]
        )
    )
)

# fix the icon
path = os.path.join(os.path.dirname(__file__), "dist", "%s.app" % appName, "Contents", "Info.plist")
appPlist = readPlist(path)
appPlist["CFBundleIconFile"] = iconFile
writePlist(appPlist, path)


# get relevant paths
drawBotRoot = os.path.dirname(os.path.abspath(__file__))
distLocation = os.path.join(drawBotRoot, "dist")
appLocation = os.path.join(distLocation, "%s.app" % appName)
imgLocation = os.path.join(distLocation, "img_%s" % appName)
existingDmgLocation = os.path.join(distLocation, "%s.dmg" % appName)
dmgLocation = os.path.join(distLocation, appName)


if "-A" not in sys.argv:
    # make sure the external tools have the correct permissions
    externalTools = ("ffmpeg", "gifsicle", "mkbitmap", "potrace")
    for externalTool in externalTools:
        externalToolPath = os.path.join(appLocation, "contents", "Resources", externalTool)
        os.chmod(externalToolPath, 0o775)


if runTests:
    appExecutable = os.path.join(appLocation, "Contents", "MacOS", appName)
    runAllTestsPath = os.path.join(drawBotRoot, "tests", "runAllTests.py")
    commands = [appExecutable, "--testScript=%s" % runAllTestsPath]
    print("Running DrawBot tests...")
    process = subprocess.Popen(commands, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    stdout, stderr = process.communicate()
    lines = stdout.splitlines()
    for startTestOutputIndex, line in enumerate(lines):
        if line.endswith(" starting test script"):
            break
    if startTestOutputIndex != 0:
        print("*** UNEXPECTED OUTPUT BEFORE TEST OUTPUT ***")
        for line in lines[:startTestOutputIndex]:
            print(line)
        print("*** UNEXPECTED OUTPUT BEFORE TEST OUTPUT ***")
        sys.exit(1)
    okLine1 = lines[-3].strip()  # in case of expected failures or unexpected successes
    okLine2 = lines[-2].strip()
    if okLine1.split()[-1] != "OK" and okLine2.split()[-1] != "OK":
        print("*** TESTS FAILED ***")
        print("Run following command to see details:")
        print(" ".join(commands))
        sys.exit(1)
    else:
        print("Tests ok.")


if buildDMG or ftpHost is not None:
    assert "-A" not in sys.argv, "can't build .dmg when using py2app -A"

    if codeSignDeveloperName:
        # ================
        # = code singing =
        # ================
        print("---------------------")
        print("-   code signing    -")
        cmds = ["codesign", "--force", "--deep", "--sign", "Developer ID Application: %s" % codeSignDeveloperName, appLocation]
        popen = subprocess.Popen(cmds)
        popen.wait()
        print("- done code singing -")
        print("---------------------")

        print("------------------------------")
        print("- verifying with codesign... -")
        cmds = ["codesign", "--verify", "--verbose=4", appLocation]
        popen = subprocess.Popen(cmds)
        popen.wait()
        print("------------------------------")

        print("---------------------------")
        print("- verifying with spctl... -")
        cmds = ["spctl", "--verbose=4", "--raw", "--assess", "--type", "execute", appLocation]
        popen = subprocess.Popen(cmds)
        popen.wait()
        print("---------------------------")

    # ================
    # = creating dmg =
    # ================
    print("------------------------")
    print("-    building dmg...   -")
    if os.path.exists(existingDmgLocation):
        os.remove(existingDmgLocation)

    os.mkdir(imgLocation)
    os.rename(os.path.join(distLocation, "%s.app" % appName), os.path.join(imgLocation, "%s.app" % appName))
    tempDmgName = "%s.tmp.dmg" % appName

    os.system("hdiutil create -size 200m -srcfolder \"%s\" -volname %s -format UDZO \"%s\"" % (imgLocation, appName, os.path.join(distLocation, tempDmgName)))

    os.system("hdiutil convert -format UDZO -imagekey zlib-level=9 -o \"%s\" \"%s\"" % (dmgLocation, os.path.join(distLocation, tempDmgName)))

    os.remove(os.path.join(distLocation, tempDmgName))

    os.rename(os.path.join(imgLocation, "%s.app" % appName), os.path.join(distLocation, "%s.app" % appName))

    shutil.rmtree(imgLocation)

    print("- done building dmg... -")
    print("------------------------")

    if ftpHost and ftpPath and ftpLogin and ftpPassword:
        import ftplib
        print("-------------------------")
        print("-    uploading to ftp   -")
        session = ftplib.FTP(ftpHost, ftpLogin, ftpPassword)
        session.cwd(ftpPath)

        dmgFile = open(existingDmgLocation, 'rb')
        fileName = os.path.basename(existingDmgLocation)
        session.storbinary('STOR %s' % fileName, dmgFile)
        dmgFile.close()

        # store a version
        session.cwd("versionHistory")
        dmgFile = open(existingDmgLocation, 'rb')
        fileName, ext = os.path.splitext(fileName)
        fileName = fileName + "_" + timeStamp + ext
        session.storbinary('STOR %s' % fileName, dmgFile)
        dmgFile.close()

        print("- done uploading to ftp -")
        print("-------------------------")
        session.quit()
