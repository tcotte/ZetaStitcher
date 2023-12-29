# Use ZetaStitcher to stitch only in 2D

### Issue with solver

File `ZetaStitcher\zetastitcher\fuse\absolute_positions.py`:
Error `qpsolvers.exceptions.SolverNotFound: solver 'cvxpy' is not in the list ['clarabel', 'daqp', 'ecos', 'osqp', 'scs'] of available solvers`
Replace
```
stitcher = GaussianStitcher(
    n_dims=N_DIMS,
    solver='cvxpy'
)
```

by
```
stitcher = GaussianStitcher(
    n_dims=N_DIMS,
    solver='clarabel'
)
```

### Jpg file reading

Add file `zetastitcher\io\jpgwrapper.py`:
This file enables to use *.jpg* files to stitch them. Before the creation of the class lying into this file, the library
was able to stitch only *.tiff* files.

### Avoid utilization of temporary yaml

File `zetastitcher\align\__main__.py` was previously returning nothing but create a yaml file gathering all FileMatrix 
information resulted from complete alignment pipeline (*align.Runner* class).
We added to it a boolean which enables (if its value is True) to retrieve the FileMatrix object from the *run()* 
function.

### Creation of input yaml

The *align.Runner* class takes as entry an *input_folder* parameter which can be the path of an input folder (where
tiles are lying) or the path of a yaml file which indicates the absolute path of all tiles and their expected 
coordinates in the warped picture. Because, previously we renamed each file to use *zetastitcher*, create a function 
which enables to automatically write information of all tiles in yaml file was very interesting (and use it to stitch 
instead of using the folder path of tiles).
Therefore, we tried to develop an automatic process allowing us to write this yaml file. The code is in 
*create_yaml_2_stitch.py* file. This code seems to be nice but was not concretely tested because we did not have the 
grid data to test it.
When this code will be tested, it should be implemented in the whole function which enables to do the stitching in an 
automate way. When the stitching will be done within this function, the input yaml file has to be delete.
