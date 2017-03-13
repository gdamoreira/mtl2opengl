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

        self.names = {}
        self.values = {}

        self.num_verts = 0
        self.num_faces = 0
        self.num_texture = 0
        self.num_normals = 0
        self.num_materials = 0

        self.in_filename_obj = None
        self.in_filename_mtl = None
        self.out_filename_obj = None
        self.out_filename_mtl = None
        self.object_obj = None
        self.object_mtl = None

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

        self.mtl = 0

        self.count = {}

    def init(self):
        self.process_files()

        # derive center coords and scale factor if neither provided nor disabled
        if not (self.scalefac and self.xcen):
            self.calc_size_and_center()

        if self.verbose:
            self.print_input_and_options()

        self.load_data_mtl()
        self.load_data_obj()
        self.normalize_normals()

        if self.verbose:
            self.print_statistics()

        self.write_output_obj()
        self.write_output_mtl()

    @staticmethod
    def fileparse(path):
        (dir_name, file_name) = os.path.split(path)
        (file_base_name, file_extension) = os.path.splitext(file_name)
        return file_base_name, dir_name, file_extension

    def process_files(self):
        if not self.objfile:
            raise ParameterInvalidException()

        if not self.mtlfile:
            raise ParameterInvalidException()

        (file_obj, dir_obj, ext_obj) = self.fileparse(self.objfile)
        self.in_filename_obj = '%s/%s%s' % (dir_obj, file_obj, ext_obj)

        (file_mtl, dir_mtl, ext_mtl) = self.fileparse(self.mtlfile)
        self.in_filename_mtl = '%s/%s%s' % (dir_mtl, file_mtl, ext_mtl)

        (file_obj, dir_obj, ext_obj) = self.fileparse(self.in_filename_obj)
        self.out_filename_obj = '%s/%s%s' % (dir_obj, file_obj, "OBJ.h")

        (file_mtl, dir_mtl, ext_mtl) = self.fileparse(self.in_filename_mtl)
        self.out_filename_mtl = '%s/%s%s' % (dir_mtl, file_mtl, "MTL.h")

        (file_obj, dir_obj, ext_obj) = self.fileparse(self.in_filename_obj)
        self.object_obj = '%s%s' % (file_obj, "OBJ")

        (file_mtl, dir_mtl, ext_mtl) = self.fileparse(self.in_filename_mtl)
        self.object_mtl = '%s%s' % (file_mtl, "MTL")

    # Stores center of object in xcen, ycen, zcen
    # and calculates scaling factor scalefac to limit max
    # side of object to 1.0 units
    def calc_size_and_center(self):
        file_input = open(self.in_filename_obj, 'r')

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
            if re.search(r'v\s+.*', line):
                self.num_verts += 1

                tokens = line.split(' ')
                # remove space
                tokens.pop(1)

                xsum += float(tokens[1])
                ysum += float(tokens[2])
                zsum += float(tokens[3])

                if self.num_verts == 1:
                    xmin = float(tokens[1])
                    xmax = float(tokens[1])
                    ymin = float(tokens[2])
                    ymax = float(tokens[2])
                    zmin = float(tokens[3])
                    zmax = float(tokens[3])
                elif tokens[1] < xmin:
                    xmin = float(tokens[1])
                elif tokens[1] > xmax:
                    xmax = float(tokens[1])

                if tokens[2] < ymin:
                    ymin = float(tokens[2])
                elif tokens[2] > ymax:
                    ymax = float(tokens[2])

                if tokens[3] < zmin:
                    zmin = float(tokens[3])
                elif tokens[3] > zmax:
                    zmax = float(tokens[3])

        file_input.close()

        #  Calculate the center
        if not self.xcen:
            self.xcen = xsum / self.num_verts
            self.ycen = ysum / self.num_verts
            self.zcen = zsum / self.num_verts

        # Calculate the scale factor
        if not self.scalefac:
            xdiff = (xmax - xmin)
            ydiff = (ymax - ymin)
            zdiff = (zmax - zmin)

            if xdiff >= ydiff and xdiff >= zdiff:
                self.scalefac = xdiff
            elif ydiff >= xdiff and ydiff >= zdiff:
                self.scalefac = ydiff
            else:
                self.scalefac = zdiff

            self.scalefac = 1.0 / self.scalefac

    def print_input_and_options(self):
        print "Input files: '%s', '%s'" % (self.in_filename_obj, self.in_filename_mtl)
        print "Output files: '%s', '%s'" % (self.out_filename_obj, self.out_filename_mtl)
        print "Object names: '%s', '%s'" % (self.object_obj, self.object_mtl)
        print "Center: <%s, %s, %s>" % (self.xcen, self.ycen, self.zcen)
        print "Scale by: %s" % self.scalefac

    def print_statistics(self):
        print "----------------"
        print "Vertices: %s" % self.num_verts
        print "Faces: %s" % self.num_faces
        print "Texture Coords: %s" % self.num_texture
        print "Normals: %s" % self.num_normals
        print "Materials: %s" % self.num_materials

    # Reads MTL components for ambient (Ka), diffuse (Kd),
    # specular (Ks), and exponent (Ns) values.
    # Structure:
    # mValues[n][0..2] = Ka
    # mValues[n][3..5] = Kd
    # mValues[n][6..8] = Ks
    # mValues[n][9] = Ns
    def load_data_mtl(self):
        # MTL data
        self.num_materials = -1
        self.values = {}

        file_input = open(self.in_filename_mtl, 'r')

        for line in file_input:
            # materials
            if re.search(r'newmtl\s+.*', line):
                self.num_materials = self.num_materials + 1
                self.values[self.num_materials] = {}

                # initialize material array
                for i in xrange(0, 9):
                    self.values[self.num_materials][i] = 0.0

                self.values[self.num_materials][9] = 1.0

                tokens = line.split(' ')
                self.names[self.num_materials] = tokens[1]

            # ambient
            if re.search(r'\s+Ka\s+.*', line):
                tokens = line.split(' ')
                self.values[self.num_materials][0] = "%.3f" % float(tokens[1])
                self.values[self.num_materials][1] = "%.3f" % float(tokens[2])
                self.values[self.num_materials][2] = "%.3f" % float(tokens[3])

            # diffuse
            if re.search(r'\s+Kd\s+.*', line):
                tokens = line.split(' ')
                self.values[self.num_materials][3] = "%.3f" % float(tokens[1])
                self.values[self.num_materials][4] = "%.3f" % float(tokens[2])
                self.values[self.num_materials][5] = "%.3f" % float(tokens[3])

            # specular
            if re.search(r'\s+Ks\s+.*', line):
                tokens = line.split(' ')
                self.values[self.num_materials][6] = "%.3f" % float(tokens[1])
                self.values[self.num_materials][7] = "%.3f" % float(tokens[2])
                self.values[self.num_materials][8] = "%.3f" % float(tokens[3])

            # exponent
            if re.search(r'\s+Ns\s+.*', line):
                tokens = line.split(' ')
                self.values[self.num_materials][9] = "%.3f" % float(tokens[1])

        file_input.close()
        self.num_materials += 1

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
    def load_data_obj(self):
        # OBJ data
        self.num_verts = 0
        self.num_faces = 0
        self.num_texture = 0
        self.num_normals = 0

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

        file_input = open(self.in_filename_obj, 'r')

        for line in file_input:

            # vertices
            if re.search(r'v\s+.*', line):
                tokens = line.split(' ')
                # remove space
                tokens.pop(1)

                x = (float(tokens[1]) - self.xcen) * self.scalefac
                y = (float(tokens[2]) - self.ycen) * self.scalefac
                z = (float(tokens[3]) - self.zcen) * self.scalefac
                self.xcoords[self.num_verts] = "%.3f" % float(x)
                self.ycoords[self.num_verts] = "%.3f" % float(y)
                self.zcoords[self.num_verts] = "%.3f" % float(z)

                self.num_verts += 1

            # texture coords
            if re.search(r'vt\s+.*', line):
                tokens = line.split(' ')
                x = float(tokens[1])
                y = 1 - float(tokens[2])
                self.tx[self.num_texture] = "%.3f" % float(x)
                self.ty[self.num_texture] = "%.3f" % float(y)

                self.num_texture += 1

            # normals
            if re.search(r'vn\s+.*', line):
                tokens = line.split(' ')
                x = tokens[1]
                y = tokens[2]
                z = tokens[3]
                self.nx[self.num_normals] = "%.3f" % float(x)
                self.ny[self.num_normals] = "%.3f" % float(y)
                self.nz[self.num_normals] = "%.3f" % float(z)

                self.num_normals += 1

            # faces
            regexp = re.compile(r'f\s+([^ ]+)\s+([^ ]+)\s+([^ ]+)(\s+([^ ]+))?')
            result_regexp = regexp.search(line)
            if result_regexp:
                (f1, f2, f3, f4, f5) = result_regexp.groups()
                a = map(float, f1.split('/'))
                b = map(float, f2.split('/'))
                c = map(float, f3.split('/'))

                self.va_idx[self.num_faces] = a[0] - 1
                self.ta_idx[self.num_faces] = a[1] - 1
                self.na_idx[self.num_faces] = a[2] - 1

                self.vb_idx[self.num_faces] = b[0] - 1
                self.tb_idx[self.num_faces] = b[1] - 1
                self.nb_idx[self.num_faces] = b[2] - 1

                self.vc_idx[self.num_faces] = c[0] - 1
                self.tc_idx[self.num_faces] = c[1] - 1
                self.nc_idx[self.num_faces] = c[2] - 1

                self.face_line[self.num_faces] = line
                self.face_mtl[self.num_faces] = self.names[self.mtl]

                self.num_faces += 1

                # rectangle => second triangle
                if f5.rstrip() != "":
                    d = map(float, f5.split('/'))
                    self.va_idx[self.num_faces] = a[0] - 1
                    self.ta_idx[self.num_faces] = a[1] - 1
                    self.na_idx[self.num_faces] = a[2] - 1

                    self.vb_idx[self.num_faces] = d[0] - 1
                    self.tb_idx[self.num_faces] = d[1] - 1
                    self.nb_idx[self.num_faces] = d[2] - 1

                    self.vc_idx[self.num_faces] = c[0] - 1
                    self.tc_idx[self.num_faces] = c[1] - 1
                    self.nc_idx[self.num_faces] = c[2] - 1

                    self.face_line[self.num_faces] = line
                    self.face_mtl[self.num_faces] = self.names[self.mtl]

                    self.num_faces += 1

            # materials
            if re.search(r'usemtl\s+.*', line):
                tokens = line.split(' ')

                i = 0
                for mName in self.names:
                    if tokens[1] == mName:
                        self.mtl = i

                    i += 1

        file_input.close()

    def normalize_normals(self):
        for j in xrange(self.num_normals):
            d = math.sqrt(float(self.nx[j]) * float(self.nx[j]) + float(self.ny[j]) * float(self.ny[j]) + float(self.nz[j]) * float(self.nz[j]))

            if d == 0:
                self.nx[j] = 1
                self.ny[j] = 0
                self.nz[j] = 0
            else:
                self.nx[j] = "%.3f" % (float(self.nx[j]) / d)
                self.ny[j] = "%.3f" % (float(self.ny[j]) / d)
                self.nz[j] = "%.3f" % (float(self.nz[j]) / d)

    def write_output_obj(self):
        self.count = {}

        file_input = open(self.out_filename_obj, 'w')

        file_input.write("// Created with mtl2opengl.py\n\n")

        # some statistics
        file_input.write("/*\n")
        file_input.write("source files: %s, %s\n" % (self.in_filename_obj, self.in_filename_mtl))
        file_input.write("vertices: %s\n" % self.num_verts)
        file_input.write("faces: %s\n" % self.num_faces)
        file_input.write("normals: %s\n" % self.num_normals)
        file_input.write("texture coords: %s\n" % self.num_texture)
        file_input.write("*/\n")
        file_input.write("\n\n")

        # needed constant for glDrawArrays
        file_input.write("unsigned int " + self.object_obj + "NumVerts = " + str(self.num_faces * 3) + ";\n\n")

        # write verts
        file_input.write("float " + self.object_obj + "Verts [] = {\n")

        for i in xrange(self.num_materials):
            self.count[i] = 0

            for j in xrange(self.num_faces):
                if self.face_mtl[j] == self.names[i]:
                    ia = self.va_idx[j]
                    ib = self.vb_idx[j]
                    ic = self.vc_idx[j]
                    file_input.write("%.3f,%.3f,%.3f,\n" % (float(self.xcoords[ia]), float(self.ycoords[ia]), float(self.zcoords[ia])))
                    file_input.write("%.3f,%.3f,%.3f,\n" % (float(self.xcoords[ib]), float(self.ycoords[ib]), float(self.zcoords[ib])))
                    file_input.write("%.3f,%.3f,%.3f,\n" % (float(self.xcoords[ic]), float(self.ycoords[ic]), float(self.zcoords[ic])))

                    self.count[i] += 3

        file_input.write("};\n\n")

        # write normals
        if self.num_normals > 0:
            file_input.write("float " + self.object_obj + "Normals [] = {\n")
            for i in xrange(self.num_materials):
                for j in xrange(self.num_faces):
                    if self.face_mtl[j] == self.names[i]:
                        ia = self.na_idx[j]
                        ib = self.nb_idx[j]
                        ic = self.nc_idx[j]
                        file_input.write("%s,%s,%s,\n" % (self.nx[ia], self.ny[ia], self.nz[ia]))
                        file_input.write("%s,%s,%s,\n" % (self.nx[ib], self.ny[ib], self.nz[ib]))
                        file_input.write("%s,%s,%s,\n" % (self.nx[ic], self.ny[ic], self.nz[ic]))

            file_input.write("};\n\n")

        # write texture coords
        if self.num_texture:
            file_input.write("float " + self.object_obj + "TexCoords [] = {\n")
            for i in xrange(self.num_materials):
                for j in xrange(self.num_faces):
                    if self.face_mtl[j] == self.names[i]:
                        ia = self.ta_idx[j]
                        ib = self.tb_idx[j]
                        ic = self.tc_idx[j]
                        file_input.write("%s,%s,\n" % (self.tx[ia], self.ty[ia]))
                        file_input.write("%s,%s,\n" % (self.tx[ib], self.ty[ib]))
                        file_input.write("%s,%s,\n" % (self.tx[ic], self.ty[ic]))

            file_input.write("};\n\n")

        file_input.close()

    def write_output_mtl(self):
        file_input = open(self.out_filename_mtl, 'w')

        file_input.write("// Created with mtl2opengl.pl\n\n")

        # some statistics
        file_input.write("/*\n")
        file_input.write("source files: %s, %s\n" % (self.in_filename_obj, self.in_filename_mtl))
        file_input.write("materials: %s\n\n" % self.num_materials)
        for i in xrange(self.num_materials):
            kaR = float(self.values[i][0])
            kaG = float(self.values[i][1])
            kaB = float(self.values[i][2])
            kdR = float(self.values[i][3])
            kdG = float(self.values[i][4])
            kdB = float(self.values[i][5])
            ksR = float(self.values[i][6])
            ksG = float(self.values[i][7])
            ksB = float(self.values[i][8])
            nsE = float(self.values[i][9])

            file_input.write("Name: %s" % self.names[i])
            file_input.write("Ka: %.3f, %.3f, %.3f\n" % (kaR, kaG, kaB))
            file_input.write("Kd: %.3f, %.3f, %.3f\n" % (kdR, kdG, kdB))
            file_input.write("Ks: %.3f, %.3f, %.3f\n" % (ksR, ksG, ksB))
            file_input.write("Ns: %.3f\n\n" % nsE)

        file_input.write("*/\n")
        file_input.write("\n\n")

        # needed constant for glDrawArrays
        file_input.write("int " + self.object_mtl + "NumMaterials = " + str(self.num_materials) + ";\n\n")

        # write firsts
        file_input.write("int " + self.object_mtl + "First [" + str(self.num_materials) + "] = {\n")
        for i in xrange(self.num_materials):
            if i == 0:
                first = 0
            else:
                first += self.count[i - 1]

            file_input.write("%s,\n" % first)

        file_input.write("};\n\n")

        # write counts
        file_input.write("int " + self.object_mtl + "Count [" + str(self.num_materials) + "] = {\n")
        for i in xrange(self.num_materials):
            count = self.count[i]
            file_input.write("%s,\n" % count)

        file_input.write("};\n\n")

        # write ambients
        file_input.write("float " + self.object_mtl + "Ambient [" + str(self.num_materials) + "][3] = {\n")
        for i in xrange(self.num_materials):
            kaR = float(self.values[i][0])
            kaG = float(self.values[i][1])
            kaB = float(self.values[i][2])

            file_input.write("%.3f,%.3f,%.3f,\n" % (kaR, kaG, kaB))

        file_input.write("};\n\n")

        # write diffuses
        file_input.write("float " + self.object_mtl + "Diffuse [" + str(self.num_materials) + "][3] = {\n")
        for i in xrange(self.num_materials):
            kdR = float(self.values[i][3])
            kdG = float(self.values[i][4])
            kdB = float(self.values[i][5])

            file_input.write("%.3f,%.3f,%.3f,\n" % (kdR, kdG, kdB))

        file_input.write("};\n\n")

        # write speculars
        file_input.write("float " + self.object_mtl + "Specular [" + str(self.num_materials) + "][3] = {\n")
        for i in xrange(self.num_materials):
            ksR = float(self.values[i][6])
            ksG = float(self.values[i][7])
            ksB = float(self.values[i][8])

            file_input.write("%.3f,%.3f,%.3f,\n" % (ksR, ksG, ksB))

        file_input.write("};\n\n")

        # write exponents
        file_input.write("float " + self.object_mtl + "Exponent [" + str(self.num_materials) + "] = {\n")
        for i in xrange(self.num_materials):
            nsE = float(self.values[i][9])

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
