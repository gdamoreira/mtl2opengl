# mtl2opengl

mtl2opengl Version 1.0 (09 March 2017)

Copyright © 2017 Guilherme D'Amoreira

<http://en.damoreira.com.br/>

## ABOUT
mtl2opengl is a python script for converting .obj and .mtl data files into arrays compatible with OpenGL ES on iOS devices.


## INSTRUCTIONS
To run the script with its default settings, type the following into the command line terminal:

python mtl2opengl.py --objfile model.obj --mtlfile model.mtl

where model.obj and model.mtl are the .obj and corresponding .mtl files of your 3D model.

## ABOUT THIS PROJECT
This project is based on [mtl2opengl](https://github.com/ricardo-rendoncepeda/mtl2opengl), a Perl mtl2opengl converter.
**The original project had a bug, when the mtl has a texture file reference (map_Kd), depending on Kd order, the result difers from the original .mtl file**
