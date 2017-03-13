#! /usr/bin/python
# =head1 NAME
# 
#  mtl2opengl - converts obj and mtl files to arrays for use with OpenGL ES
#  
# =head1 SYNOPSIS
# 
#  mtl2opengl [options]
# 
#  use -help or -man for further information
# 
# =head1 DESCRIPTION
# 
# This script expects:
# An OBJ file consisting of vertices (v), texture coords (vt) and normals (vn). The 
# corresponding MTL file consisting of ambient (Ka), diffuse (Kd), specular (Ks), and 
# exponent (Ns) components.
# 
# The resulting .H files offer three float arrays for the OBJ geometry data and
# four float arrays for the MTL material data to be rendered.
# 
# =head1 AUTHOR
# 
# Guilherme D'Amoreira <http://en.damoreira.com.br/>
# 
# =head1 VERSION
# 
# 13 March 2017 (1.1)
# 
# =head1 VERSION HISTORY
#  
# Version 1.1
# -----------
# - Adjusted code to use class attributes
# - Added docs on arguments parser
# 
# Version 1.0
# -----------
# First mtl2opengl.py transcode
# 
# =head1 COPYRIGHT
# 
# MIT License
# 
# Copyright (c) 2017 Guilherme D'Amoreira
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# 
# =head1 ACKNOWLEDGEMENTS
# 
# This script is based on the work of:
# 
# Ricardo Rendon Cepeda <https://github.com/ricardo-rendoncepeda/mtl2opengl>
# 
# Heiko Behrens <http://heikobehrens.net/2009/08/27/obj2opengl/>
# 
# Margaret Geroch <http://people.sc.fsu.edu/~jburkardt/pl_src/obj2opengl/obj2opengl.html>
# 
# =head1 REQUIRED ARGUMENTS
# 
# The argument --objfile (1) must be an OBJ file. 
# The argument --mtlfile (2) must be the corresponding MTL file.
# 
# =head1 OPTIONS
# 
# =over
# 
# =item B<-noScale>    
# 
# Prevents automatic scaling. Otherwise the object will be scaled
# such the the longest dimension is 1 unit.
# 
# =item B<-scale <float>>
# 
# Sets the scale factor explicitly. Please be aware that negative numbers
# are not handled correctly regarding the orientation of the normals.
# 
# =item B<-noMove>
# 
# Prevents automatic scaling. Otherwise the object will be moved to the center of
# its vertices.
# 
# =item B<-center>
# 
# Sets center point of the object to centralize.
# 
# =item B<-verbose>
# 
# Runs this script logging some information.
#    
# =cut
import argparse
import os
import re
import math


class ParameterInvalidException(Exception):
    pass


class Converter():
    def __init__(self, scalefac=0, verbose=None, xcen=None, ycen=None, zcen=None, objfile=None, mtlfile=None):
        self.xcen = xcen
        self.ycen = ycen
        self.zcen = zcen
        self.scalefac = scalefac
        self.verbose = verbose
        self.objfile = objfile
        self.mtlfile = mtlfile

        self.mNames = {}
        self.mValues = {}

        self.numVerts = 0
        self.numFaces = 0
        self.numTexture = 0
        self.numNormals = 0
        self.numMaterials = 0

    def init(self):
        self.process_files()

        # derive center coords and scale factor if neither provided nor disabled
        if not (self.scalefac and self.xcen):
            self.calcSizeAndCenter()

        if self.verbose:
            self.printInputAndOptions()

        self.loadDataMTL()
        self.loadDataOBJ()
        self.normalizeNormals()

        if self.verbose:
            self.printStatistics()

        self.writeOutputOBJ()
        self.writeOutputMTL()

    def fileparse(self, path):
        (dir_name, file_name) = os.path.split(path)
        (file_base_name, file_extension) = os.path.splitext(file_name)
        return (file_base_name, dir_name, file_extension)

    def process_files(self):
        if not self.objfile:
            raise ParameterInvalidException()

        if not self.mtlfile:
            raise ParameterInvalidException()

        (fileOBJ, dirOBJ, extOBJ) = self.fileparse(self.objfile)
        self.inFilenameOBJ = '%s/%s%s' % (dirOBJ, fileOBJ, extOBJ)

        (fileMTL, dirMTL, extMTL) = self.fileparse(self.mtlfile)
        self.inFilenameMTL = '%s/%s%s' % (dirMTL, fileMTL, extMTL)

        (fileOBJ, dirOBJ, extOBJ) = self.fileparse(self.inFilenameOBJ)
        self.outFilenameOBJ = '%s/%s%s' % (dirOBJ, fileOBJ, "OBJ.h")

        (fileMTL, dirMTL, extMTL) = self.fileparse(self.inFilenameMTL)
        self.outFilenameMTL = '%s/%s%s' % (dirMTL, fileMTL, "MTL.h")

        (fileOBJ, dirOBJ, extOBJ) = self.fileparse(self.inFilenameOBJ)
        self.objectOBJ = '%s%s' % (fileOBJ, "OBJ")

        (fileMTL, dirMTL, extMTL) = self.fileparse(self.inFilenameMTL)
        self.objectMTL = '%s%s' % (fileMTL, "MTL")

    # Stores center of object in xcen, ycen, zcen
    # and calculates scaling factor scalefac to limit max
    # side of object to 1.0 units
    def calcSizeAndCenter(self):
        file_input = open(self.inFilenameOBJ, 'r')

        xsum = 0
        ysum = 0
        zsum = 0
        xmin = 0
        ymin = 0
        zmin = 0
        xmax = 0
        ymax = 0
        zmax = 0

        for line in file_input:
            if (re.search(r'v\s+.*', line)):
                self.numVerts += 1

                tokens = line.split(' ')
                # remove space
                tokens.pop(1)

                xsum += float(tokens[1])
                ysum += float(tokens[2])
                zsum += float(tokens[3])

                if self.numVerts == 1:
                    xmin = float(tokens[1])
                    xmax = float(tokens[1])
                    ymin = float(tokens[2])
                    ymax = float(tokens[2])
                    zmin = float(tokens[3])
                    zmax = float(tokens[3])
                else:
                    if (tokens[1] < xmin):
                        xmin = float(tokens[1])
                    elif (tokens[1] > xmax):
                        xmax = float(tokens[1])

                    if (tokens[2] < ymin):
                        ymin = float(tokens[2])
                    elif (tokens[2] > ymax):
                        ymax = float(tokens[2])

                    if (tokens[3] < zmin):
                        zmin = float(tokens[3])
                    elif (tokens[3] > zmax):
                        zmax = float(tokens[3])

        file_input.close()

        #  Calculate the center
        if not self.xcen:
            self.xcen = xsum / self.numVerts
            self.ycen = ysum / self.numVerts
            self.zcen = zsum / self.numVerts

        # Calculate the scale factor
        if not self.scalefac:
            xdiff = (xmax - xmin)
            ydiff = (ymax - ymin)
            zdiff = (zmax - zmin)

            if ((xdiff >= ydiff) and (xdiff >= zdiff)):
                self.scalefac = xdiff
            elif ((ydiff >= xdiff) and (ydiff >= zdiff)):
                self.scalefac = ydiff
            else:
                self.scalefac = zdiff

            self.scalefac = 1.0 / self.scalefac

    def printInputAndOptions(self):
        print "Input files: '%s', '%s'" % (self.inFilenameOBJ, self.inFilenameMTL)
        print "Output files: '%s', '%s'" % (self.outFilenameOBJ, self.outFilenameMTL)
        print "Object names: '%s', '%s'" % (self.objectOBJ, self.objectMTL)
        print "Center: <%s, %s, %s>" % (self.xcen, self.ycen, self.zcen)
        print "Scale by: %s" % self.scalefac

    def printStatistics(self):
        print "----------------"
        print "Vertices: %s" % self.numVerts
        print "Faces: %s" % self.numFaces
        print "Texture Coords: %s" % self.numTexture
        print "Normals: %s" % self.numNormals
        print "Materials: %s" % self.numMaterials

    # Reads MTL components for ambient (Ka), diffuse (Kd),
    # specular (Ks), and exponent (Ns) values.
    # Structure: 
    # mValues[n][0..2] = Ka
    # mValues[n][3..5] = Kd
    # mValues[n][6..8] = Ks
    # mValues[n][9] = Ns
    def loadDataMTL(self):
        # MTL data
        self.numMaterials = -1
        self.mValues = {}

        file_input = open(self.inFilenameMTL, 'r')

        for line in file_input:
            # materials
            if re.search(r'newmtl\s+.*', line):
                self.numMaterials = self.numMaterials + 1
                self.mValues[self.numMaterials] = {}

                # initialize material array
                for i in xrange(0, 9):
                    self.mValues[self.numMaterials][i] = 0.0

                self.mValues[self.numMaterials][9] = 1.0

                tokens = line.split(' ')
                self.mNames[self.numMaterials] = tokens[1]

            # ambient
            if re.search(r'\s+Ka\s+.*', line):
                tokens = line.split(' ')
                self.mValues[self.numMaterials][0] = "%.3f" % float(tokens[1])
                self.mValues[self.numMaterials][1] = "%.3f" % float(tokens[2])
                self.mValues[self.numMaterials][2] = "%.3f" % float(tokens[3])

            # diffuse
            if re.search(r'\s+Kd\s+.*', line):
                tokens = line.split(' ')
                self.mValues[self.numMaterials][3] = "%.3f" % float(tokens[1])
                self.mValues[self.numMaterials][4] = "%.3f" % float(tokens[2])
                self.mValues[self.numMaterials][5] = "%.3f" % float(tokens[3])

            # specular
            if re.search(r'\s+Ks\s+.*', line):
                tokens = line.split(' ')
                self.mValues[self.numMaterials][6] = "%.3f" % float(tokens[1])
                self.mValues[self.numMaterials][7] = "%.3f" % float(tokens[2])
                self.mValues[self.numMaterials][8] = "%.3f" % float(tokens[3])

            # exponent
            if re.search(r'\s+Ns\s+.*', line):
                tokens = line.split(' ')
                self.mValues[self.numMaterials][9] = "%.3f" % float(tokens[1])

        file_input.close()
        self.numMaterials += 1

    # reads vertices into $xcoords[], $ycoords[], $zcoords[]
    #   where coordinates are moved and scaled according to
    #   $xcen, $ycen, $zcen and $scalefac
    # reads texture coords into $tx[], $ty[] 
    #   where y coordinate is mirrowed
    # reads normals into $nx[], $ny[], $nz[]
    #   but does not normalize, see normalizeNormals()
    # reads faces and establishes lookup data where
    #   va_idx[], vb_idx[], vc_idx[] for vertices
    #   ta_idx[], tb_idx[], tc_idx[] for texture coords
    #   na_idx[], nb_idx[], nc_idx[] for normals
    #   store indizes for the former arrays respectively
    #   also, $face_line[] store actual face string
    def loadDataOBJ(self):
        # OBJ data
        self.numVerts = 0
        self.numFaces = 0
        self.numTexture = 0
        self.numNormals = 0

        self.xcoords = {}
        self.ycoords = {}
        self.zcoords = {}
        self.tx = {}
        self.ty = {}
        self.nx = {}
        self.ny = {}
        self.nz = {}

        self.va_idx = {}
        self.ta_idx = {}
        self.na_idx = {}

        self.vb_idx = {}
        self.tb_idx = {}
        self.nb_idx = {}

        self.vc_idx = {}
        self.tc_idx = {}
        self.nc_idx = {}

        self.face_line = {}
        self.face_mtl = {}

        # MTL data
        self.mtl = 0

        file_input = open(self.inFilenameOBJ, 'r')

        for line in file_input:

            # vertices
            if (re.search(r'v\s+.*', line)):
                tokens = line.split(' ')
                # remove space
                tokens.pop(1)

                x = (float(tokens[1]) - self.xcen) * self.scalefac
                y = (float(tokens[2]) - self.ycen) * self.scalefac
                z = (float(tokens[3]) - self.zcen) * self.scalefac
                self.xcoords[self.numVerts] = "%.3f" % float(x)
                self.ycoords[self.numVerts] = "%.3f" % float(y)
                self.zcoords[self.numVerts] = "%.3f" % float(z)

                self.numVerts += 1

            # texture coords
            if (re.search(r'vt\s+.*', line)):
                tokens = line.split(' ')
                x = float(tokens[1])
                y = 1 - float(tokens[2])
                self.tx[self.numTexture] = "%.3f" % float(x)
                self.ty[self.numTexture] = "%.3f" % float(y)

                self.numTexture += 1

            # normals
            if (re.search(r'vn\s+.*', line)):
                tokens = line.split(' ')
                x = tokens[1]
                y = tokens[2]
                z = tokens[3]
                self.nx[self.numNormals] = "%.3f" % float(x)
                self.ny[self.numNormals] = "%.3f" % float(y)
                self.nz[self.numNormals] = "%.3f" % float(z)

                self.numNormals += 1

            # faces
            regexp = re.compile(r'f\s+([^ ]+)\s+([^ ]+)\s+([^ ]+)(\s+([^ ]+))?')
            result_regexp = regexp.search(line)
            if (result_regexp):
                (f1, f2, f3, f4, f5) = result_regexp.groups()
                a = map(float, f1.split('/'))
                b = map(float, f2.split('/'))
                c = map(float, f3.split('/'))

                self.va_idx[self.numFaces] = a[0] - 1
                self.ta_idx[self.numFaces] = a[1] - 1
                self.na_idx[self.numFaces] = a[2] - 1

                self.vb_idx[self.numFaces] = b[0] - 1
                self.tb_idx[self.numFaces] = b[1] - 1
                self.nb_idx[self.numFaces] = b[2] - 1

                self.vc_idx[self.numFaces] = c[0] - 1
                self.tc_idx[self.numFaces] = c[1] - 1
                self.nc_idx[self.numFaces] = c[2] - 1

                self.face_line[self.numFaces] = line
                self.face_mtl[self.numFaces] = self.mNames[self.mtl]

                self.numFaces += 1

                # rectangle => second triangle
                if f5 != "":
                    d = map(float, f5.split('/'))
                    self.va_idx[self.numFaces] = a[0] - 1
                    self.ta_idx[self.numFaces] = a[1] - 1
                    self.na_idx[self.numFaces] = a[2] - 1

                    self.vb_idx[self.numFaces] = d[0] - 1
                    self.tb_idx[self.numFaces] = d[1] - 1
                    self.nb_idx[self.numFaces] = d[2] - 1

                    self.vc_idx[self.numFaces] = c[0] - 1
                    self.tc_idx[self.numFaces] = c[1] - 1
                    self.nc_idx[self.numFaces] = c[2] - 1

                    self.face_line[self.numFaces] = line
                    self.face_mtl[self.numFaces] = self.mNames[self.mtl]

                    self.numFaces = self.numFaces + 1

            # materials
            if (re.search(r'usemtl\s+.*', line)):
                tokens = line.split(' ')

                i = 0
                for mName in self.mNames:
                    if tokens[1] == mName:
                        self.mtl = i

                    i += 1

        file_input.close()

    def normalizeNormals(self):
        for j in xrange(self.numNormals):
            d = math.sqrt(float(self.nx[j]) * float(self.nx[j]) + float(self.ny[j]) * float(self.ny[j]) + float(self.nz[j]) * float(self.nz[j]))

            if d == 0:
                self.nx[j] = 1
                self.ny[j] = 0
                self.nz[j] = 0
            else:
                self.nx[j] = "%.3f" % (float(self.nx[j]) / d)
                self.ny[j] = "%.3f" % (float(self.ny[j]) / d)
                self.nz[j] = "%.3f" % (float(self.nz[j]) / d)

    def writeOutputOBJ(self):
        self.mCount = {}

        file_input = open(self.outFilenameOBJ, 'w')

        file_input.write("// Created with mtl2opengl.py\n\n")

        # some statistics
        file_input.write("/*\n")
        file_input.write("source files: %s, %s\n" % (self.inFilenameOBJ, self.inFilenameMTL))
        file_input.write("vertices: %s\n" % self.numVerts)
        file_input.write("faces: %s\n" % self.numFaces)
        file_input.write("normals: %s\n" % self.numNormals)
        file_input.write("texture coords: %s\n" % self.numTexture)
        file_input.write("*/\n")
        file_input.write("\n\n")

        # needed constant for glDrawArrays
        file_input.write("unsigned int " + self.objectOBJ + "NumVerts = " + str(self.numFaces * 3) + ";\n\n")

        # write verts
        file_input.write("float " + self.objectOBJ + "Verts [] = {\n")

        for i in xrange(self.numMaterials):
            self.mCount[i] = 0

            for j in xrange(self.numFaces):
                if self.face_mtl[j] == self.mNames[i]:
                    ia = self.va_idx[j]
                    ib = self.vb_idx[j]
                    ic = self.vc_idx[j]
                    file_input.write("%.3f,%.3f,%.3f,\n" % (float(self.xcoords[ia]), float(self.ycoords[ia]), float(self.zcoords[ia])))
                    file_input.write("%.3f,%.3f,%.3f,\n" % (float(self.xcoords[ib]), float(self.ycoords[ib]), float(self.zcoords[ib])))
                    file_input.write("%.3f,%.3f,%.3f,\n" % (float(self.xcoords[ic]), float(self.ycoords[ic]), float(self.zcoords[ic])))

                    self.mCount[i] += 3

        file_input.write("};\n\n")

        # write normals
        if self.numNormals > 0:
            file_input.write("float " + self.objectOBJ + "Normals [] = {\n")
            for i in xrange(self.numMaterials):
                for j in xrange(self.numFaces):
                    if self.face_mtl[j] == self.mNames[i]:
                        ia = self.na_idx[j]
                        ib = self.nb_idx[j]
                        ic = self.nc_idx[j]
                        file_input.write("%s,%s,%s,\n" % (self.nx[ia], self.ny[ia], self.nz[ia]))
                        file_input.write("%s,%s,%s,\n" % (self.nx[ib], self.ny[ib], self.nz[ib]))
                        file_input.write("%s,%s,%s,\n" % (self.nx[ic], self.ny[ic], self.nz[ic]))

            file_input.write("};\n\n")

        # write texture coords
        if self.numTexture:
            file_input.write("float " + self.objectOBJ + "TexCoords [] = {\n")
            for i in xrange(self.numMaterials):
                for j in xrange(self.numFaces):
                    if self.face_mtl[j] == self.mNames[i]:
                        ia = self.ta_idx[j]
                        ib = self.tb_idx[j]
                        ic = self.tc_idx[j]
                        file_input.write("%s,%s,\n" % (self.tx[ia], self.ty[ia]))
                        file_input.write("%s,%s,\n" % (self.tx[ib], self.ty[ib]))
                        file_input.write("%s,%s,\n" % (self.tx[ic], self.ty[ic]))

            file_input.write("};\n\n")

        file_input.close()

    def writeOutputMTL(self):
        file_input = open(self.outFilenameMTL, 'w')

        file_input.write("// Created with mtl2opengl.pl\n\n")

        # some statistics
        file_input.write("/*\n")
        file_input.write("source files: %s, %s\n" % (self.inFilenameOBJ, self.inFilenameMTL))
        file_input.write("materials: %s\n\n" % self.numMaterials)
        for i in xrange(self.numMaterials):
            kaR = float(self.mValues[i][0])
            kaG = float(self.mValues[i][1])
            kaB = float(self.mValues[i][2])
            kdR = float(self.mValues[i][3])
            kdG = float(self.mValues[i][4])
            kdB = float(self.mValues[i][5])
            ksR = float(self.mValues[i][6])
            ksG = float(self.mValues[i][7])
            ksB = float(self.mValues[i][8])
            nsE = float(self.mValues[i][9])

            file_input.write("Name: %s" % self.mNames[i])
            file_input.write("Ka: %.3f, %.3f, %.3f\n" % (kaR, kaG, kaB))
            file_input.write("Kd: %.3f, %.3f, %.3f\n" % (kdR, kdG, kdB))
            file_input.write("Ks: %.3f, %.3f, %.3f\n" % (ksR, ksG, ksB))
            file_input.write("Ns: %.3f\n\n" % nsE)

        file_input.write("*/\n")
        file_input.write("\n\n")

        # needed constant for glDrawArrays
        file_input.write("int " + self.objectMTL + "NumMaterials = " + str(self.numMaterials) + ";\n\n")

        # write firsts
        file_input.write("int " + self.objectMTL + "First [" + str(self.numMaterials) + "] = {\n")
        for i in xrange(self.numMaterials):
            if i == 0:
                first = 0
            else:
                first += self.mCount[i - 1]

            file_input.write("%s,\n" % first)

        file_input.write("};\n\n")

        # write counts
        file_input.write("int " + self.objectMTL + "Count [" + str(self.numMaterials) + "] = {\n")
        for i in xrange(self.numMaterials):
            count = self.mCount[i]
            file_input.write("%s,\n" % count)

        file_input.write("};\n\n")

        # write ambients
        file_input.write("float " + self.objectMTL + "Ambient [" + str(self.numMaterials) + "][3] = {\n")
        for i in xrange(self.numMaterials):
            kaR = float(self.mValues[i][0])
            kaG = float(self.mValues[i][1])
            kaB = float(self.mValues[i][2])

            file_input.write("%.3f,%.3f,%.3f,\n" % (kaR, kaG, kaB))

        file_input.write("};\n\n")

        # write diffuses
        file_input.write("float " + self.objectMTL + "Diffuse [" + str(self.numMaterials) + "][3] = {\n")
        for i in xrange(self.numMaterials):
            kdR = float(self.mValues[i][3])
            kdG = float(self.mValues[i][4])
            kdB = float(self.mValues[i][5])

            file_input.write("%.3f,%.3f,%.3f,\n" % (kdR, kdG, kdB))

        file_input.write("};\n\n")

        # write speculars
        file_input.write("float " + self.objectMTL + "Specular [" + str(self.numMaterials) + "][3] = {\n")
        for i in xrange(self.numMaterials):
            ksR = float(self.mValues[i][6])
            ksG = float(self.mValues[i][7])
            ksB = float(self.mValues[i][8])

            file_input.write("%.3f,%.3f,%.3f,\n" % (ksR, ksG, ksB))

        file_input.write("};\n\n")

        # write exponents
        file_input.write("float " + self.objectMTL + "Exponent [" + str(self.numMaterials) + "] = {\n")
        for i in xrange(self.numMaterials):
            nsE = float(self.mValues[i][9])

            file_input.write("%.3f,\n" % nsE)

        file_input.write("};\n\n")

        file_input.close()


# main function call
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='An OBJ file consisting of vertices (v), texture coords (vt) and normals (vn). \
        The corresponding MTL file consisting of ambient (Ka), diffuse (Kd), specular (Ks), and exponent (Ns) components. \
        The resulting .H files offer three float arrays for the OBJ geometry data and \
        four float arrays for the MTL material data to be rendered.')
    parser.add_argument('--center', metavar='N/N/N', help='Sets center point of the object to centralize. The format is "N" as a number: N/N/N.')
    parser.add_argument('--noMove', metavar='1/0', help='Prevents automatic scaling. Otherwise the object will be moved to the center of its vertices.')
    parser.add_argument('--noScale', metavar='1/0', help='Prevents automatic scaling. Otherwise the object will be scaled such the the longest dimension is 1 unit.')
    parser.add_argument('--scale', metavar='0..1',
                        help='Sets the scale factor explicitly. Please be aware that negative numbers are not handled correctly regarding the orientation of the normals.')
    parser.add_argument('--verbose', metavar='1/0', help='Runs this script logging some information.')
    parser.add_argument('--mtlfile', metavar='<mtlfile path>', help='Sets the .mtl file path.', required=True)
    parser.add_argument('--objfile', metavar='<objfile path>', help='Sets the .obj file path.', required=True)

    args = parser.parse_args()
    objfile = args.objfile
    mtlfile = args.mtlfile
    scalefac = args.scale
    verbose = args.verbose
    no_scale = args.noScale
    no_move = args.noMove
    center = args.center
    xcen = None
    ycen = None
    zcen = None

    if no_scale:
        scalefac = 1
    elif scalefac < 0:
        raise ParameterInvalidException()

    if no_move:
        center = '0/0/0'

    if center:
        center = center.split('/')
        xcen = center[0]
        ycen = center[1]
        zcen = center[2]

    # start converter
    converter = Converter(scalefac=scalefac, verbose=verbose, xcen=xcen, ycen=ycen, zcen=zcen, objfile=objfile, mtlfile=mtlfile)
    converter.init()
