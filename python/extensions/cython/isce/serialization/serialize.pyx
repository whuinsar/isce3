#cython: language_level=3
#
# Author: Joshua Cohen
# Copyright 2017
#

from libcpp.string cimport string
from Serialization cimport *
import h5py
from IH5 cimport hid_t, IGroup

def deserialize(h5Group, pyOrbit isceobj, **kwargs):
    """
    High-level interface for deserializing generic ISCE objects from an HDF5
    Level-1 product.

    Args:
        h5Group (h5py Group):                   h5py group
        isceobj:                                Any supported ISCE extension class.
        
    Return:
        None 
    """
    group = pyStringToBytes('IH5:::ID={0}'.format(h5Group.id.id))

    if isinstance(isceobj, pyPoly2d):
        loadPoly2d(group, isceobj, **kwargs)
    elif isinstance(isceobj, pyMetadata):
        loadMetadata(group, isceobj, **kwargs)

    else:
        raise NotImplementedError('No suitable deserialization method found.')
    
# --------------------------------------------------------------------------------
# Serialization functions for isce3::core objects
# --------------------------------------------------------------------------------

def loadPoly2d(pyIGroup group, pyPoly2d poly, poly_name='skew_dcpolynomial'):
    """
    Load Poly2d parameters from HDF5 file.

    Args:
        group (pyIGroup):                       IH5File for product.
        poly (pyPoly2d):                        pyPoly2d instance.
        poly_name (str):                        H5 dataset name for polynomial.

    Return:
        None
    """
    loadFromH5(group.c_igroup, deref(poly.c_poly2d), <string> pyStringToBytes(poly_name))

# --------------------------------------------------------------------------------
# Serialization functions for isce3::product objects
# --------------------------------------------------------------------------------

def loadMetadata(pyIGroup group, pyMetadata meta):
    """
    Load Metadata parameters from HDF5 file.

    Args:
        group (pyIGroup):                       IH5File for product.
        meta (pyMetadata):                      pyMetadata instance.

    Return:
        None
    """
    loadFromH5(group.c_igroup, deref(meta.c_metadata))
