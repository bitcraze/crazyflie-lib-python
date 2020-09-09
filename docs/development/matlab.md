---
title: Using Matlab with the Crazyflie API
page_id: matlab 
---


Using Matlab with the Crazyflie API is easy -- you just need to install
the python 'matlab engine' and then can access all matlab commands
directly from python.

Prerequisites
-------------

1.  MATLAB 2014b or later
2.  64 bit python 2.7, 3.3 or 3.4
3.  The Crazyflie API

Installing the Matlab python engine
-----------------------------------

1.  Find the path to the MATLAB folder. To do this, start MATLAB and
    type matlabroot in the command window. Copy the path returned by
    matlabroot
2.  To install the engine open a command window and on Windows type cd
    \"matlabroot\\extern\\engines\\python\". On Mac or Linux systems
    type cd \"matlabroot/extern/engines/python\".
3.  Finally type python setup.py install

Step 3 sometimes fails if you do not have write permission to the
default build directory. If this happens:

3a. Create a new directory to store the build directory where you have
write permission.\
3b. Then set up the python engine with:
`python setup.py build --build-base builddir install --user `{.bash}

Here builddir is the path of the directory created in step 3b. Note the
double dashes (no space) before 'build-base' and 'user'.

### More information (from Mathworks MATLAB documentation)

System requirements:
<http://www.mathworks.com/help/matlab/matlab_external/system-requirements-for-matlab-engine-for-python.html>

Installation:
<http://www.mathworks.com/help/matlab/matlab_external/install-the-matlab-engine-for-python.html>

Installation in non-default locations
<http://www.mathworks.com/help/matlab/matlab_external/install-matlab-engine-api-for-python-in-nondefault-locations.html>

Using the Matlab Python engine
------------------------------

Once you have installed the matlab engine, you can use any matlab
commands (or your own matlab scripts) from within the Crazyflie API. To
do this:

1.  Import the matlab engine with: `import matlab.engine`{.python}
2.  Create a matlab engine object (which starts matlab -- the initial
    startup will be slow) with
    (eg)`self.eng = matlab.engine.start_matlab()`{.python}
3.  ***Optional*** You might want to add a directory with your matlab
    scripts to the matlab
    path:`self.eng.addpath("directory name",nargout=0)`{.python}
4.  ***Optional*** MATLAB errors and console output will usually appear
    in the console window of IDEs such as pycharm or Eclipse. To divert
    them to a file you can create StringIO objects. To do this you must
    first import StringIO, then create the StringIO objects,
    eg`self.matlabout = StringIO.StringIO()
    self.matlaberr = StringIO.StringIO()`{.python}
5.  You can then run a matlab script or function
    with:`output = self.eng.function_name([argument list],[stdout=self.matlabout],[stderr=self.matlaberr],[nargout=n])`{.python}
    Here 'output' is the output from the matlab function (if multiple
    arguments are returned by the function then output is an array - see
    the matlab python engine documentation for more information),
    \[argument list\] is the input arguments to the matlab function,
    self.matlabout and self.matlaberr are StringIO objects to capture
    Matlab errors and console output (optional) and n is the number of
    output arguments from the MATLAB script (the default is 1).

### More information

Matlab engine API documentation from Mathworks:
<http://www.mathworks.com/help/matlab/matlab-engine-for-python.html>

Call MATLAB functions from python
<http://www.mathworks.com/help/matlab/matlab_external/call-matlab-functions-from-python.html>

Limitations
-----------

Not all data structures in matlab and python have direct equivalents.
You can pass most primitive data types between them, as well as arrays.
You can also usually pass matlab data types from one matlab function to
another (eg you can save an output variable from a matlab function such
as a file handle or plot handle in a python variable, and then pass it
to another matlab function).

For speed it is best to minimize communications between python and
matlab - i.e. try to do all matlab computations through a single script,
instead of calling many matlab functions from inside python.

More information
----------------

Pass data to matlab from python
<http://www.mathworks.com/help/matlab/matlab_external/pass-data-to-matlab-from-python.html>
