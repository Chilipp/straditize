Constructor information for straditize-conda
============================================

The files in this directory are intended to construct a conda installer which
to be ready to use with the straditize installation.

The created environment contain the following packages, downloaded from the
conda-forge channel:

- python
- scipy
- matplotlib
- dask
- xarray
- netcdf4
- cartopy
- seaborn
- bottleneck
- statsmodels
- psyplot

This constructor informations are automatically used to create executables when
a new release is published and the executables are then uploaded to github.
