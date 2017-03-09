import argparse
import os
import re
import math


class ParameterInvalidException(Exception):
    pass


class Converter():
    def __init__(self, options={}):
        self.options = options

    def init(self):
        # derive center coords and scale factor if neither provided nor disabled
        if not (self.options['scalefac'] and self.options['xcen']):
            self.calcSizeAndCenter()

        if self.options['verbose']:
            self.printInputAndOptions()

        self.loadDataMTL()
        self.loadDataOBJ()
        self.normalizeNormals()

        if self.options['verbose']:
            self.printStatistics()

        self.writeOutputOBJ()
        self.writeOutputMTL()

    # Stores center of object in xcen, ycen, zcen
    # and calculates scaling factor scalefac to limit max
    # side of object to 1.0 units
    def calcSizeAndCenter(self):
        file_input = open(self.options['inFilenameOBJ'], 'r')

        self.options['numVerts'] = 0

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
                self.options['numVerts'] = self.options['numVerts'] + 1
                tokens = line.split(' ')
                # remove space
                tokens.pop(1)

                xsum += float(tokens[1])
                ysum += float(tokens[2])
                zsum += float(tokens[3])

                if (self.options['numVerts'] == 1):
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
        if not self.options['xcen']:
            self.options['xcen'] = xsum / self.options['numVerts']
            self.options['ycen'] = ysum / self.options['numVerts']
            self.options['zcen'] = zsum / self.options['numVerts']

        # Calculate the scale factor
        if not self.options['scalefac']:
            xdiff = (xmax - xmin)
            ydiff = (ymax - ymin)
            zdiff = (zmax - zmin)

            if ((xdiff >= ydiff) and (xdiff >= zdiff)):
                self.options['scalefac'] = xdiff
            elif ( ( ydiff >= xdiff ) and ( ydiff >= zdiff ) ):
                self.options['scalefac'] = ydiff
            else:
                self.options['scalefac'] = zdiff

            self.options['scalefac'] = 1.0 / self.options['scalefac']


    def printInputAndOptions(self):
        print "Input files: '%s', '%s'" % (self.options['inFilenameOBJ'], self.options['inFilenameMTL'])
        print "Output files: '%s', '%s'" % (self.options['outFilenameOBJ'], self.options['outFilenameMTL'])
        print "Object names: '%s', '%s'" % (self.options['objectOBJ'], self.options['objectMTL'])
        print "Center: <%s, %s, %s>" % (self.options['xcen'], self.options['ycen'], self.options['zcen'])
        print "Scale by: %s" % self.options['scalefac']


    def printStatistics(self):
        print "----------------"
        print "Vertices: %s" % self.options['numVerts']
        print "Faces: %s" % self.options['numFaces']
        print "Texture Coords: %s" % self.options['numTexture']
        print "Normals: %s" % self.options['numNormals']
        print "Materials: %s" % self.options['numMaterials']


    # Reads MTL components for ambient (Ka), diffuse (Kd),
    # specular (Ks), and exponent (Ns) values.
    # Structure: 
    # mValues[n][0..2] = Ka
    # mValues[n][3..5] = Kd
    # mValues[n][6..8] = Ks
    # mValues[n][9] = Ns
    def loadDataMTL(self):
        # MTL data
        self.options['numMaterials'] = -1
        self.options['mValues'] = {}

        file_input = open(self.options['inFilenameMTL'], 'r')

        for line in file_input:
            # materials
            if re.search(r'newmtl\s+.*', line):
                self.options['numMaterials'] = self.options['numMaterials'] + 1
                self.options['mValues'][self.options['numMaterials']] = {}

                # initialize material array
                for i in xrange(0, 9):
                    self.options['mValues'][self.options['numMaterials']][i] = 0.0

                self.options['mValues'][self.options['numMaterials']][9] = 1.0

                tokens = line.split(' ')
                self.options['mNames'][self.options['numMaterials']] = tokens[1]

            # ambient
            if re.search(r'\s+Ka\s+.*', line):
                tokens = line.split(' ')
                self.options['mValues'][self.options['numMaterials']][0] = "%.3f" % float(tokens[1])
                self.options['mValues'][self.options['numMaterials']][1] = "%.3f" % float(tokens[2])
                self.options['mValues'][self.options['numMaterials']][2] = "%.3f" % float(tokens[3])

            # diffuse
            if re.search(r'\s+Kd\s+.*', line):
                tokens = line.split(' ')
                self.options['mValues'][self.options['numMaterials']][3] = "%.3f" % float(tokens[1])
                self.options['mValues'][self.options['numMaterials']][4] = "%.3f" % float(tokens[2])
                self.options['mValues'][self.options['numMaterials']][5] = "%.3f" % float(tokens[3])

            # specular
            if re.search(r'\s+Ks\s+.*', line):
                tokens = line.split(' ')
                self.options['mValues'][self.options['numMaterials']][6] = "%.3f" % float(tokens[1])
                self.options['mValues'][self.options['numMaterials']][7] = "%.3f" % float(tokens[2])
                self.options['mValues'][self.options['numMaterials']][8] = "%.3f" % float(tokens[3])

            # exponent
            if re.search(r'\s+Ns\s+.*', line):
                tokens = line.split(' ')
                self.options['mValues'][self.options['numMaterials']][9] = "%.3f" % float(tokens[1])

        file_input.close()
        self.options['numMaterials'] += 1


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
        self.options['numVerts'] = 0
        self.options['numFaces'] = 0
        self.options['numTexture'] = 0
        self.options['numNormals'] = 0

        self.options['xcoords'] = {}
        self.options['ycoords'] = {}
        self.options['zcoords'] = {}
        self.options['tx'] = {}
        self.options['ty'] = {}
        self.options['nx'] = {}
        self.options['ny'] = {}
        self.options['nz'] = {}

        self.options['va_idx'] = {}
        self.options['ta_idx'] = {}
        self.options['na_idx'] = {}

        self.options['vb_idx'] = {}
        self.options['tb_idx'] = {}
        self.options['nb_idx'] = {}

        self.options['vc_idx'] = {}
        self.options['tc_idx'] = {}
        self.options['nc_idx'] = {}

        self.options['face_line'] = {}
        self.options['face_mtl'] = {}

        # MTL data
        self.options['mtl'] = 0

        file_input = open(self.options['inFilenameOBJ'], 'r')

        for line in file_input:

            # vertices
            if (re.search(r'v\s+.*', line)):
                tokens = line.split(' ')
                # remove space
                tokens.pop(1)

                x = (float(tokens[1]) - self.options['xcen']) * self.options['scalefac']
                y = (float(tokens[2]) - self.options['ycen']) * self.options['scalefac']
                z = (float(tokens[3]) - self.options['zcen']) * self.options['scalefac']
                self.options['xcoords'][self.options['numVerts']] = "%.3f" % float(x)
                self.options['ycoords'][self.options['numVerts']] = "%.3f" % float(y)
                self.options['zcoords'][self.options['numVerts']] = "%.3f" % float(z)

                self.options['numVerts'] += 1


            # texture coords
            if (re.search(r'vt\s+.*', line)):
                tokens = line.split(' ')
                x = float(tokens[1])
                y = 1 - float(tokens[2])
                self.options['tx'][self.options['numTexture']] = "%.3f" % float(x)
                self.options['ty'][self.options['numTexture']] = "%.3f" % float(y)

                self.options['numTexture'] += 1

            # normals
            if (re.search(r'vn\s+.*', line)):
                tokens = line.split(' ')
                x = tokens[1]
                y = tokens[2]
                z = tokens[3]
                self.options['nx'][self.options['numNormals']] = "%.3f" % float(x)
                self.options['ny'][self.options['numNormals']] = "%.3f" % float(y)
                self.options['nz'][self.options['numNormals']] = "%.3f" % float(z)

                self.options['numNormals'] += 1

            # faces
            regexp = re.compile(r'f\s+([^ ]+)\s+([^ ]+)\s+([^ ]+)(\s+([^ ]+))?')
            result_regexp = regexp.search(line)
            if (result_regexp):
                (f1, f2, f3, f4, f5) = result_regexp.groups()
                a = map(float, f1.split('/'))
                b = map(float, f2.split('/'))
                c = map(float, f3.split('/'))

                self.options['va_idx'][self.options['numFaces']] = a[0] - 1
                self.options['ta_idx'][self.options['numFaces']] = a[1] - 1
                self.options['na_idx'][self.options['numFaces']] = a[2] - 1

                self.options['vb_idx'][self.options['numFaces']] = b[0] - 1
                self.options['tb_idx'][self.options['numFaces']] = b[1] - 1
                self.options['nb_idx'][self.options['numFaces']] = b[2] - 1

                self.options['vc_idx'][self.options['numFaces']] = c[0] - 1
                self.options['tc_idx'][self.options['numFaces']] = c[1] - 1
                self.options['nc_idx'][self.options['numFaces']] = c[2] - 1

                self.options['face_line'][self.options['numFaces']] = line
                self.options['face_mtl'][self.options['numFaces']] = self.options['mNames'][self.options['mtl']]

                self.options['numFaces'] += 1

                # rectangle => second triangle
                if f5 != "":
                    d = map(float, f5.split('/'))
                    self.options['va_idx'][self.options['numFaces']] = a[0] - 1
                    self.options['ta_idx'][self.options['numFaces']] = a[1] - 1
                    self.options['na_idx'][self.options['numFaces']] = a[2] - 1

                    self.options['vb_idx'][self.options['numFaces']] = d[0] - 1
                    self.options['tb_idx'][self.options['numFaces']] = d[1] - 1
                    self.options['nb_idx'][self.options['numFaces']] = d[2] - 1

                    self.options['vc_idx'][self.options['numFaces']] = c[0] - 1
                    self.options['tc_idx'][self.options['numFaces']] = c[1] - 1
                    self.options['nc_idx'][self.options['numFaces']] = c[2] - 1

                    self.options['face_line'][self.options['numFaces']] = line
                    self.options['face_mtl'][self.options['numFaces']] = self.options['mNames'][self.options['mtl']]

                    self.options['numFaces'] = self.options['numFaces'] + 1

            # materials
            if (re.search(r'usemtl\s+.*', line)):
                tokens = line.split(' ')

                i = 0
                for mName in self.options['mNames']:
                    if tokens[1] == mName:
                        self.options['mtl'] = i

                    i += 1

        file_input.close()


    def normalizeNormals(self):
        for j in xrange(self.options['numNormals']):
            d = math.sqrt(float(self.options['nx'][j]) * float(self.options['nx'][j]) + float(self.options['ny'][j]) * float(self.options['ny'][j]) + float(self.options['nz'][j]) * float(self.options['nz'][j]))

            if d == 0:
                self.options['nx'][j] = 1
                self.options['ny'][j] = 0
                self.options['nz'][j] = 0
            else:
                self.options['nx'][j] = "%.3f" % (float(self.options['nx'][j]) / d)
                self.options['ny'][j] = "%.3f" % (float(self.options['ny'][j]) / d)
                self.options['nz'][j] = "%.3f" % (float(self.options['nz'][j]) / d)


    def writeOutputOBJ(self):
        self.options['mCount'] = {}

        file_input = open(self.options['outFilenameOBJ'], 'w')

        file_input.write("// Created with mtl2opengl.py\n\n")

        # some statistics
        file_input.write("/*\n")
        file_input.write("source files: %s, %s\n" % (self.options['inFilenameOBJ'], self.options['inFilenameMTL']))
        file_input.write("vertices: %s\n" % self.options['numVerts'])
        file_input.write("faces: %s\n" % self.options['numFaces'])
        file_input.write("normals: %s\n" % self.options['numNormals'])
        file_input.write("texture coords: %s\n" % self.options['numTexture'])
        file_input.write("*/\n")
        file_input.write("\n\n")

        # needed constant for glDrawArrays
        file_input.write("unsigned int " + self.options['objectOBJ'] + "NumVerts = " + str(self.options['numFaces'] * 3) + ";\n\n")

        # write verts
        file_input.write("float " + self.options['objectOBJ'] + "Verts [] = {\n")

        for i in xrange(self.options['numMaterials']):
            self.options['mCount'][i] = 0

            for j in xrange(self.options['numFaces']):
                if self.options['face_mtl'][j] == self.options['mNames'][i]:
                    ia = self.options['va_idx'][j]
                    ib = self.options['vb_idx'][j]
                    ic = self.options['vc_idx'][j]
                    file_input.write("%.3f,%.3f,%.3f,\n" % (float(self.options['xcoords'][ia]), float(self.options['ycoords'][ia]), float(self.options['zcoords'][ia])))
                    file_input.write("%.3f,%.3f,%.3f,\n" % (float(self.options['xcoords'][ib]), float(self.options['ycoords'][ib]), float(self.options['zcoords'][ib])))
                    file_input.write("%.3f,%.3f,%.3f,\n" % (float(self.options['xcoords'][ic]), float(self.options['ycoords'][ic]), float(self.options['zcoords'][ic])))

                    self.options['mCount'][i] += 3

        file_input.write("};\n\n")

        # write normals
        if self.options['numNormals'] > 0:
            file_input.write("float " + self.options['objectOBJ'] + "Normals [] = {\n")
            for i in xrange(self.options['numMaterials']):
                for j in xrange(self.options['numFaces']):
                    if self.options['face_mtl'][j] == self.options['mNames'][i]:
                        ia = self.options['na_idx'][j]
                        ib = self.options['nb_idx'][j]
                        ic = self.options['nc_idx'][j]
                        file_input.write("%s,%s,%s,\n" % (self.options['nx'][ia], self.options['ny'][ia], self.options['nz'][ia]))
                        file_input.write("%s,%s,%s,\n" % (self.options['nx'][ib], self.options['ny'][ib], self.options['nz'][ib]))
                        file_input.write("%s,%s,%s,\n" % (self.options['nx'][ic], self.options['ny'][ic], self.options['nz'][ic]))

            file_input.write("};\n\n")

        # write texture coords
        if self.options['numTexture']:
            file_input.write("float " + self.options['objectOBJ'] + "TexCoords [] = {\n")
            for i in xrange(self.options['numMaterials']):
                for j in xrange(self.options['numFaces']):
                    if self.options['face_mtl'][j] == self.options['mNames'][i]:
                        ia = self.options['ta_idx'][j]
                        ib = self.options['tb_idx'][j]
                        ic = self.options['tc_idx'][j]
                        file_input.write("%s,%s,\n" % (self.options['tx'][ia], self.options['ty'][ia]))
                        file_input.write("%s,%s,\n" % (self.options['tx'][ib], self.options['ty'][ib]))
                        file_input.write("%s,%s,\n" % (self.options['tx'][ic], self.options['ty'][ic]))

            file_input.write("};\n\n")

        file_input.close()


    def writeOutputMTL(self):
        file_input = open(self.options['outFilenameMTL'], 'w')

        file_input.write("// Created with mtl2opengl.pl\n\n")

        # some statistics
        file_input.write("/*\n")
        file_input.write("source files: %s, %s\n" % (self.options['inFilenameOBJ'], self.options['inFilenameMTL']))
        file_input.write("materials: %s\n\n" % self.options['numMaterials'])
        for i in xrange(self.options['numMaterials']):
            kaR = float(self.options['mValues'][i][0])
            kaG = float(self.options['mValues'][i][1])
            kaB = float(self.options['mValues'][i][2])
            kdR = float(self.options['mValues'][i][3])
            kdG = float(self.options['mValues'][i][4])
            kdB = float(self.options['mValues'][i][5])
            ksR = float(self.options['mValues'][i][6])
            ksG = float(self.options['mValues'][i][7])
            ksB = float(self.options['mValues'][i][8])
            nsE = float(self.options['mValues'][i][9])

            file_input.write("Name: %s" % self.options['mNames'][i])
            file_input.write("Ka: %.3f, %.3f, %.3f\n" % (kaR, kaG, kaB))
            file_input.write("Kd: %.3f, %.3f, %.3f\n" % (kdR, kdG, kdB))
            file_input.write("Ks: %.3f, %.3f, %.3f\n" % (ksR, ksG, ksB))
            file_input.write("Ns: %.3f\n\n" % nsE)

        file_input.write("*/\n")
        file_input.write("\n\n")

        # needed constant for glDrawArrays
        file_input.write("int " + self.options['objectMTL'] + "NumMaterials = " + str(self.options['numMaterials']) + ";\n\n")

        # write firsts
        file_input.write("int " + self.options['objectMTL'] + "First [" + str(self.options['numMaterials']) + "] = {\n")
        for i in xrange(self.options['numMaterials']):
            if i == 0:
                first = 0
            else:
                first += self.options['mCount'][i - 1]

            file_input.write("%s,\n" % first)

        file_input.write("};\n\n")

        # write counts
        file_input.write("int " + self.options['objectMTL'] + "Count [" + str(self.options['numMaterials']) + "] = {\n")
        for i in xrange(self.options['numMaterials']):
            count = self.options['mCount'][i]
            file_input.write("%s,\n" % count)

        file_input.write("};\n\n")

        # write ambients
        file_input.write("float " + self.options['objectMTL'] + "Ambient [" + str(self.options['numMaterials']) + "][3] = {\n")
        for i in xrange(self.options['numMaterials']):
            kaR = float(self.options['mValues'][i][0])
            kaG = float(self.options['mValues'][i][1])
            kaB = float(self.options['mValues'][i][2])

            file_input.write("%.3f,%.3f,%.3f,\n" % (kaR, kaG, kaB))

        file_input.write("};\n\n")

        # write diffuses
        file_input.write("float " + self.options['objectMTL'] + "Diffuse [" + str(self.options['numMaterials']) + "][3] = {\n")
        for i in xrange(self.options['numMaterials']):
            kdR = float(self.options['mValues'][i][3])
            kdG = float(self.options['mValues'][i][4])
            kdB = float(self.options['mValues'][i][5])

            file_input.write("%.3f,%.3f,%.3f,\n" % (kdR, kdG, kdB))

        file_input.write("};\n\n")

        # write speculars
        file_input.write("float " + self.options['objectMTL'] + "Specular [" + str(self.options['numMaterials']) + "][3] = {\n")
        for i in xrange(self.options['numMaterials']):
            ksR = float(self.options['mValues'][i][6])
            ksG = float(self.options['mValues'][i][7])
            ksB = float(self.options['mValues'][i][8])

            file_input.write("%.3f,%.3f,%.3f,\n" % (ksR, ksG, ksB))

        file_input.write("};\n\n")

        # write exponents
        file_input.write("float " + self.options['objectMTL'] + "Exponent [" + str(self.options['numMaterials']) + "] = {\n")
        for i in xrange(self.options['numMaterials']):
            nsE = float(self.options['mValues'][i][9])

            file_input.write("%.3f,\n" % nsE)

        file_input.write("};\n\n")

        file_input.close()


# main function call
if __name__ == '__main__':
    def fileparse(path):
        (dirName, fileName) = os.path.split(path)
        (fileBaseName, fileExtension) = os.path.splitext(fileName)
        return (fileBaseName, dirName, fileExtension)


    parser = argparse.ArgumentParser(description='Process converter.')
    parser.add_argument('--man', metavar='', help='')
    parser.add_argument('--noScale', metavar='', help='')
    parser.add_argument('--scale', metavar='', help='')
    parser.add_argument('--noMove', metavar='', help='')
    parser.add_argument('--center', metavar='', help='')
    parser.add_argument('--verbose', metavar='', help='')
    parser.add_argument('--objfile', metavar='', help='')
    parser.add_argument('--mtlfile', metavar='', help='')

    args = parser.parse_args()
    options = {
        'man': args.man,
        'noScale': args.noScale,
        'scale': args.scale,
        'noMove': args.noMove,
        'center': args.center,
        'verbose': args.verbose,
        'scalefac': 0,
        'xcen': None,
        'ycen': None,
        'zcen': None,
        'mNames': {},
        'mValues': {}
    }

    if options['noScale']:
        options['scalefac'] = 1
    elif options['scalefac'] < 0:
        raise ParameterInvalidException()

    if options['noMove']:
        options['center'] = '0/0/0'

    if options['center']:
        center = options['center'].split('/')
        options['xcen'] = center[0]
        options['ycen'] = center[1]
        options['zcen'] = center[2]

    objfile = args.objfile
    if not objfile:
        raise ParameterInvalidException()

    mtlfile = args.mtlfile
    if not mtlfile:
        raise ParameterInvalidException()

    (fileOBJ, dirOBJ, extOBJ) = fileparse(objfile)
    options['inFilenameOBJ'] = '%s/%s%s' % (dirOBJ, fileOBJ, extOBJ)

    (fileMTL, dirMTL, extMTL) = fileparse(mtlfile)
    options['inFilenameMTL'] = '%s/%s%s' % (dirMTL, fileMTL, extMTL)

    (fileOBJ, dirOBJ, extOBJ) = fileparse(options['inFilenameOBJ'])
    options['outFilenameOBJ'] = '%s/%s%s' % (dirOBJ, fileOBJ, "OBJ.h")

    (fileMTL, dirMTL, extMTL) = fileparse(options['inFilenameMTL'])
    options['outFilenameMTL'] = '%s/%s%s' % (dirMTL, fileMTL, "MTL.h")

    (fileOBJ, dirOBJ, extOBJ) = fileparse(options['inFilenameOBJ'])
    options['objectOBJ'] = '%s%s' % (fileOBJ, "OBJ")

    (fileMTL, dirMTL, extMTL) = fileparse(options['inFilenameMTL'])
    options['objectMTL'] = '%s%s' % (fileMTL, "MTL")

    if not os.path.exists(options['inFilenameOBJ']) or not os.path.exists(options['inFilenameMTL']):
        raise ParameterInvalidException()

    # start converter
    converter = Converter(options)
    converter.init()
