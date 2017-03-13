# mtl2opengl

mtl2opengl Version 1.0 (13 March 2017)

Copyright © 2017 Guilherme D'Amoreira

<http://en.damoreira.com.br/>

## ABOUT
mtl2opengl is a python script for converting .obj and .mtl data files into arrays compatible with OpenGL ES on iOS devices.


## INSTRUCTIONS
To run the script with its default settings, type the following into the command line terminal:

```
python mtl2opengl.py --objfile model.obj --mtlfile model.mtl
```

where model.obj and model.mtl are the .obj and corresponding .mtl files of your 3D model.

## USAGE
```
usage: mtl2opengl.py [-h] [--center N/N/N] [--noMove 1/0] [--noScale 1/0]
                     [--scale 0..1] [--verbose 1/0] --mtlfile <mtlfile path>
                     --objfile <objfile path>

An OBJ file consisting of vertices (v), texture coords (vt) and normals (vn).
The corresponding MTL file consisting of ambient (Ka), diffuse (Kd), specular
(Ks), and exponent (Ns) components. The resulting .H files offer three float
arrays for the OBJ geometry data and four float arrays for the MTL material
data to be rendered.

optional arguments:
  -h, --help            show this help message and exit
  --center N/N/N        Sets center point of the object to centralize. The
                        format is "N" as a number: N/N/N.
  --noMove 1/0          Prevents automatic scaling. Otherwise the object will
                        be moved to the center of its vertices.
  --noScale 1/0         Prevents automatic scaling. Otherwise the object will
                        be scaled such the the longest dimension is 1 unit.
  --scale 0..1          Sets the scale factor explicitly. Please be aware that
                        negative numbers are not handled correctly regarding
                        the orientation of the normals.
  --verbose 1/0         Runs this script logging some information.
  --mtlfile <mtlfile path>
                        Sets the .mtl file path.
  --objfile <objfile path>
                        Sets the .obj file path.
```

## ABOUT THIS PROJECT
This project is based on [mtl2opengl](https://github.com/ricardo-rendoncepeda/mtl2opengl), a Perl mtl2opengl converter.
**The original project had a bug, when the mtl has a texture file reference (map_Kd), depending on Kd order, the result difers from the original .mtl file**
