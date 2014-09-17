#!/usr/bin/env python3
#-*- coding: utf-8 -*-

from execcmd import ExecCmd
import gettext

# i18n: http://docs.python.org/2/library/gettext.html
gettext.install("updatemanager", "/usr/share/locale")
#t = gettext.translation("updatemanager", "/usr/share/locale")
#_ = t.lgettext


class UmApt(object):

    def __init__(self, umglobal):
        self.ec = ExecCmd()
        self.umglobal = umglobal
        self.kernelArchitecture = self.umglobal.getKernelArchitecture()

        self.packagesInfo = []

        self.downgradablePackages = []
        self.upgradablePackages = []
        self.newPackages = []
        self.removedPackages = []
        self.heldbackPackages = []
        self.notavailablePackages = []
        self.orphanedPackages = []

        # Build installed packages info list
        #self.createPackagesInfoList()

    def createPackagesInfoList(self):
        # Reset variables
        self.packagesInfo = []

        # Use env LANG=C to ensure the output of apt-show-versions is always en_US
        cmd = "env LANG=C bash -c 'apt-show-versions'"
        # Get the output of the command in a list
        lst = self.ec.run(cmd=cmd, realTime=False)

        # Loop through each line and fill the package lists
        for line in lst:
            items = line.split(" ")
            if self.umglobal.isStable:
                pck = items[0].split("/")[0]
                ver = items[1]
                avVer = ''
                if "uptodate" in line:
                    ver = items[len(items) - 1]
                    avVer = ver
                elif "upgradeable" in line:
                    ver = items[len(items) - 3]
                    avVer = items[len(items) - 1]
                self.packagesInfo.append([pck, ver, avVer])
            else:
                pck = items[0].split(":")[0]
                if self.kernelArchitecture == "x86_64" and "i386" in items[0]:
                    pck = items[0].split("/")[0]
                ver = items[1]
                avVer = ''
                if "uptodate" in line:
                    avVer = ver
                elif "upgradeable" in line:
                    avVer = items[len(items) - 1]
                self.packagesInfo.append([pck, ver, avVer])

    def createPackageLists(self, customAptGetCommand=""):
        # Reset variables
        self.upgradablePackages = []
        self.newPackages = []
        self.removedPackages = []
        self.heldbackPackages = []

        # Create approriate command
        # Use env LANG=C to ensure the output of dist-upgrade is always en_US
        cmd = "env LANG=C bash -c 'apt-get dist-upgrade --assume-no'"
        if self.umglobal.isStable:
            cmd = "env LANG=C bash -c 'apt-get upgrade --assume-no'"
        if "apt-get" in customAptGetCommand:
            customAptGetCommand = customAptGetCommand.replace("--force-yes", "")
            customAptGetCommand = customAptGetCommand.replace("--assume-yes", "")
            customAptGetCommand = customAptGetCommand.replace("--yes", "")
            customAptGetCommand = customAptGetCommand.replace("-y", "")
            cmd = "env LANG=C bash -c '%s --assume-no'" % customAptGetCommand

        # Get the output of the command in a list
        lst = self.ec.run(cmd=cmd, realTime=False)

        # Loop through each line and fill the package lists
        prevLine = None
        for line in lst:
            if line[0:1].strip() == "":
                if "removed:" in prevLine.lower():
                    self.fillPackageList(self.removedPackages, line.strip())
                elif "new packages" in prevLine.lower():
                    self.fillPackageList(self.newPackages, line.strip(), True)
                elif "kept back:" in prevLine.lower():
                    self.fillPackageList(self.heldbackPackages, line.strip())
                elif "upgraded:" in prevLine.lower():
                    self.fillPackageList(self.upgradablePackages, line.strip())
            else:
                prevLine = line

    def initAptShowVersions(self):
        # Initialize or update package cache only
        cmd = "apt-show-versions -i"
        self.ec.run(cmd=cmd, realTime=False)

    def fillPackageList(self, packageList, line, new=False):
        packages = line.split(" ")
        for package in packages:
            package = package.strip().replace("*", "")
            if new:
                # We're not going to show version info for new packages
                packageList.append([package, "", ""])
            else:
                for info in self.packagesInfo:
                    if package == info[0] or "%s:i386" % package == info[0]:
                        packageList.append(info)
                        break

    def fillNotAvailablePackages(self):
        self.notavailablePackages = []
        # Use env LANG=C to ensure the output of apt-show-versions is always en_US
        cmd = "env LANG=C bash -c 'apt-show-versions' | grep 'available'"
        # Get the output of the command in a list
        lst = self.ec.run(cmd=cmd, realTime=False)

        # Loop through each line and fill the package lists
        for line in lst:
            items = line.split(" ")
            pck = items[0].split(":")[0]
            if pck != "updatemanager":
                if self.kernelArchitecture == "x86_64" and "i386" in items[0]:
                    pck = items[0].split("/")[0]
                ver = items[1]
                avVer = ""
                self.notavailablePackages.append([pck, ver, avVer])

    def fillDowngradablePackages(self):
        self.downgradablePackages = []
        # Use env LANG=C to ensure the output of apt-show-versions is always en_US
        cmd = "env LANG=C bash -c 'apt-show-versions' | grep 'newer'"
        # Get the output of the command in a list
        lst = self.ec.run(cmd=cmd, realTime=False)

        # Loop through each line and fill the package lists
        for line in lst:
            items = line.split(" ")
            pck = items[0].split(":")[0]
            if pck != "updatemanager":
                if self.kernelArchitecture == "x86_64" and "i386" in items[0]:
                    pck = items[0].split("/")[0]
                ver = items[1]
                avVer = self.getDowngradablePackageVersion(pck)
                if ver != avVer:
                    self.downgradablePackages.append([pck, ver, avVer])

    def fillOrphanedPackages(self):
        self.orphanedPackages = []
        # Use env LANG=C to ensure the output of apt-show-versions is always en_US
        cmd = "env LANG=C bash -c 'deborphan'"
        # Get the output of the command in a list
        lst = self.ec.run(cmd=cmd, realTime=False)

        # Loop through each line and fill the package lists
        for line in lst:
            pck = line.split(":")[0]
            if pck != "updatemanager":
                if self.kernelArchitecture == "x86_64" and "i386" in line:
                    pck = line
                ver = ""
                avVer = ""
                for info in self.packagesInfo:
                    if pck == info[0]:
                        ver = info[1]
                        avVer = info[2]
                self.orphanedPackages.append([pck, ver, avVer])

    # Get the package version number
    def getDowngradablePackageVersion(self, package):
        cmd = "env LANG=C bash -c 'apt-cache show %s | grep \"^Version:\" | cut -d\" \" -f 2'" % package
        lst = self.ec.run(cmd, realTime=False)
        if len(lst) > 1:
            return lst[1]
        else:
            return lst[0]

    def getPackageVersion(self, package, candidate=False):
        cmd = "env LANG=C bash -c 'apt-cache policy %s | grep \"Installed:\"'" % package
        if candidate:
            cmd = "env LANG=C bash -c 'apt-cache policy %s | grep \"Candidate:\"'" % package
        lst = self.ec.run(cmd, realTime=False)[0].strip().split(' ')
        return lst[-1]

    def aptHasErrors(self):
        ret = self.ec.run("apt-get --assume-no upgrade", False, False)
        if ret[0:2].upper() == "E:":
            return ret
        return None

    def getAptCacheLockedProgram(self, aptPackages):
        procLst = self.ec.run("ps -U root -u root -o comm=", False)
        for aptProc in aptPackages:
            if aptProc in procLst:
                return aptProc
        return None

    def cleanCache(self, safe=True):
        cmd = "apt-get --yes --force-yes autoclean"
        if not safe:
            cmd = "apt-get --yes --force-yes clean"
        self.ec.run(cmd, realTime=False)
