"""
gui.py
Author: Thomas Sutter
Description: 
    GUI for the UED data analysis program
"""


"""
The goal of this script is to provide a user interface for data analysis.

"""

import numpy as np
import scipy as sci
import tifffile
import re
import os

def load_images_smartscan_single_fluence(scandir):
    dirlist = os.listdir(scandir)
    if not 'average' in dirlist:
        raise FileNotFoundError('The "average" directory is missing. scandir must be in smartscan format')
    
    file_list = os.listdir(f'{scandir}//average')
    dspos_list = [] # a list storing all the delaystage positions in the scan
    im_list = [] # a list storing the file names of just the image files
    
    # go through all the files, select out the images, and store the delay stage positions from the filenames in a list
    for i in range(len(file_list)):
        if file_list[i].find('.tiff') == -1:
            continue # This means the file here is something other than a tiff in the scan (e.g. the meta data file)
        
        s = file_list[i][file_list[i].find('pos=')+4:]
        sn = grab_leading_number_from_string(s)
        
        dspos_list.append(float(sn))
        im_list.append(file_list[i])
        
    # Load an example image to get the image shape
    image_0 = tifffile.imread(f'{scandir}//average//{im_list[0]}')
    h, w = image_0.shape
    images = np.empty([len(im_list),h, w])
        
    sorted_indices = np.argsort(dspos_list)
    dspos_list_sorted = [0]*len(dspos_list)
    im_list_sorted = ['']*len(dspos_list)
    
    for i in range(len(sorted_indices)):
        dspos_list_sorted[i] = dspos_list[sorted_indices[i]]
        im_list_sorted[i] = im_list[sorted_indices[i]]
        
        print(f'Loading image: {im_list_sorted[i]}')
        images[i] = tifffile.imread(f'{scandir}//average//{im_list_sorted[i]}')
    
    return np.array(dspos_list_sorted), images
    
def grab_leading_number_from_string(s):
    numeric_part = re.match(r'^\d+(\.\d+)?', s)
    if numeric_part:
        return numeric_part.group()
    else:
        raise SyntaxError('File name following "pos=" argument is non-numeric')

def find_nearest(a,a_arr,returnIndex=True):
    """
    Returns the index for which the element of the array a_arr is closest to the float a
    a_arr should be an array of floats, ints, or something numeric
    """
    index = np.abs(a_arr - a).argmin()
    return index

def nix_outliers(a_arr,sigma_range=3,never_output_empty=False):
    """
    Takes an array of values and throws away statistically unlikely outliers
    A "Dynamic Mean" and a "Dynamic Sigma" are computed
    they are just the mean and standard deviation of the values without the value in question
    The value in question is thrown away if it differs from the dynamic mean by sigmaRange many dynamic sigmas
    Note that the length of the output array is in general smaller than the length of the input array
    If neverOutputEmpty is true and the output array is empty, then nixOutliers will return [0].
    """
    b_arr = []
    for i in range(len(a_arr)):
        a_arr_temp = np.delete(a_arr,i)
        dynamic_mean = np.mean(a_arr_temp)
        dynamic_sigma = np.std(a_arr_temp)
        if abs(a_arr[i] - dynamic_mean) <= sigma_range*dynamic_sigma:
            b_arr.append(a_arr[i])
    output = np.array(b_arr)
    if output.size == 0:
        print("output is empty!")
        if never_output_empty == True:
            print("never output empty = True; thus, I am returning [0]. Beware.")
            return [0]
    return output

def pdf_mean_var(pdf):
    xbar = np.average(np.indices(pdf.shape)[0], weights = pdf)
    xsqrbar = np.average(np.indices(pdf.shape)[0]**2, weights = pdf)
    xvar = xsqrbar - xbar**2
    return xbar, xvar 

def gaussian_2d(x, y, x0, y0, xalpha, yalpha, A, offset, rotAngle):
    #Translate x,y by x0,y0 for easier coordinate system x_trans,y_trans
    x_trans = x-x0
    y_trans = y-y0
    x_trans_rot = x_trans*np.cos(rotAngle)+y_trans*np.sin(rotAngle)
    y_trans_rot = y_trans*np.cos(rotAngle)-x_trans*np.sin(rotAngle) # Rotates the coordinate system to handle general beam profiles
    return A * np.exp( -0.5*(((x_trans_rot)/xalpha)**2 + ((y_trans_rot)/yalpha)**2 ) ) + offset

def erf_fit_func(x, mu, sigma, amp, offset):
    return 0.5*amp*(sci.special.erf((x-mu)/sigma) + 1) + offset
    
def sgolay_2d_filter(image, window_length =  9, polyorder = 5):
    filtered_image_1 = np.empty(image.shape)
    filtered_image_2 = np.empty(image.shape)
    for i in range(image.shape[0]):
        xdata = image[i,:]
        ydata = image[:,i]
        filtered_image_1[i, :] = sci.signal.savgol_filter(xdata, window_length = window_length, polyorder = polyorder)
        filtered_image_2[:, i] = sci.signal.savgol_filter(ydata, window_length = window_length, polyorder = polyorder)
    return 0.5*(filtered_image_1 + filtered_image_2)
    

# ~ if __name__ == "__main__":

# -*- coding: utf-8 -*-

"""
Two-dimensional Savitzky-Golay filter

"""

import collections
import typing as t

import numpy as np
import numpy.linalg as la

import scipy.ndimage as ndim


Param2 = collections.namedtuple('Param2', ('row', 'column'))
Polynom2 = collections.namedtuple('Polynom2', ('row_pows', 'column_pows', 'num_coeffs'))

_Param2Type = t.Union[Param2, t.Tuple[int, int]]
_ParamType = t.Union[int, _Param2Type]

_DIM = 2


class SGolayKernel2:
    """Computes two-dimensional kernel (weights) for Savitzky-Golay filter
    """

    def __init__(self, window_size: _Param2Type, poly_order: _Param2Type):
        self._window_size = Param2(*window_size)
        self._poly_order = Param2(*poly_order)

        self._kernel = None  # type: np.ndarray
        self.computed = False

    def __call__(self):
        self.compute()

    def compute(self):
        if self.computed:
            return

        polynom = self._make_polynom(self._poly_order)
        basis_matrix = self._make_basis_matrix(self._window_size, polynom)

        self._kernel = self._compute_kernel(self._window_size, basis_matrix)

        self.computed = True

    @property
    def kernel(self) -> np.ndarray:
        """Returns 2D Savitzky-Golay kernel
        """
        self.compute()
        return self._kernel

    @staticmethod
    def _make_polynom(poly_order: Param2) -> Polynom2:
        """
        Creates 2-D polynom model (for example poly33):
            p = a00 + a10x + a01y + a20x^2 + a11xy + a02y^2 + a30x^3 + a21x^2y \
                + a12xy^2 + a03y^3
        """
        row_pows = []
        column_pows = []
        num_coeffs = 0

        for row in range(poly_order.row + 1):
            for column in range(poly_order.column + 1):
                if (row + column) > max(*poly_order):
                    continue

                row_pows.append(row)
                column_pows.append(column)

                num_coeffs += 1

        return Polynom2(row_pows, column_pows, num_coeffs)

    @staticmethod
    def _make_basis_matrix(window_size: Param2, poly: Polynom2) -> np.ndarray:
        """Creates basis polynomial matrix
        """
        basis_rows = window_size.row * window_size.column
        basis_columns = poly.num_coeffs

        basis_matrix = np.zeros((basis_rows, basis_columns))

        radius_row = (window_size.row - 1) // 2
        radius_column = (window_size.column - 1) // 2

        row_pows = np.array(poly.row_pows)
        column_pows = np.array(poly.column_pows)

        k = 0

        for row in range(-radius_row, radius_row + 1):
            for column in range(-radius_column, radius_column + 1):
                basis_matrix[k, :] = column ** column_pows * row ** row_pows
                k += 1

        return basis_matrix

    @staticmethod
    def _compute_kernel(window_size: Param2,
                        basis_matrix: np.ndarray) -> np.ndarray:
        """Computes filter 2D kernel via solving least squares problem
        """
        q, _ = la.qr(basis_matrix)

        iq = (window_size.row * window_size.column - 1) // 2
        kernel = q @ np.array(q[iq, :], ndmin=2).T
        kernel = np.fliplr(kernel.reshape(*window_size, order='F'))

        return kernel


class SGolayFilter2:
    """Two-dimensional Savitzky-Golay filter
    """

    def __init__(self, window_size: _ParamType, poly_order: _ParamType):
        self._window_size = self._canonize_param(
            'window_size', window_size, self._validate_window_size)
        self._poly_order = self._canonize_param(
            'poly_order', poly_order, self._validate_poly_order)

        self._kernel = SGolayKernel2(self._window_size, self._poly_order)

    def __call__(self, data: np.ndarray,
                 mode: str = 'reflect', cval: float = 0.0):
        return self._filtrate(data, mode=mode, cval=cval)

    @property
    def window_size(self) -> Param2:
        return self._window_size

    @property
    def poly_order(self) -> Param2:
        return self._poly_order

    @property
    def kernel(self) -> SGolayKernel2:
        """Returns filter 2D kernel
        """
        return self._kernel

    @staticmethod
    def _canonize_param(name, value: _ParamType, validator) -> Param2:
        err = TypeError(
            'The parameter "{}" must be int scalar or Tuple[int, int]'.format(
                name))

        if isinstance(value, int):
            value = (value, value)

        if not isinstance(value, (list, tuple)):
            raise err
        if len(value) != _DIM:
            raise err
        if not all(isinstance(v, int) for v in value):
            raise err

        validator(value)

        return Param2(*value)

    @staticmethod
    def _validate_window_size(value):
        if not all(v >= 3 and bool(v % 2) for v in value):
            raise ValueError(
                'Window size values must be odd and >= 3 (Given: {})'.format(
                    value))

    @staticmethod
    def _validate_poly_order(value):
        if not all(v >= 1 for v in value):
            raise ValueError(
                'Polynom order values must be >= 1 (Given: {})'.format(value))

    def _filtrate(self, data: np.ndarray, *args, **kwargs):
        self._kernel.compute()
        return ndim.correlate(data, self._kernel.kernel, *args, **kwargs)



import matplotlib.pyplot as plt
image = np.zeros([250,250])
X, Y = np.indices(image.shape)
mux, muy = 100, 150
sx, sy = 50, 50
image += np.exp(-0.5*(((X-mux)/sx)**2 + ((Y-muy)/sy)**2))
image += np.exp(-0.5*(((X-mux)/2)**2 + ((Y-muy)/3)**2))
image += np.random.normal(loc = 0, scale = 0.1, size = image.shape)

filtered_image = sgolay_2d_filter(image)

zs = SGolayFilter2(window_size=9, poly_order=5)(image)


print('np.sum(zs-image)',np.sum(zs-image))
print('np.sum(filtered_image-image',np.sum(filtered_image-image))

# ~ plt.plot(image[100,:], c = 'black')
# ~ plt.plot(xfiltered, c = 'green', alpha = 1)
fig, axs = plt.subplots(2,3)
axs[0,0].imshow(image)
axs[0,1].imshow(filtered_image)
axs[0,2].imshow(zs)

axs[1,0].imshow(image-image)
axs[1,1].imshow(filtered_image-image, vmin = -0.1, vmax = 0.1)
axs[1,2].imshow(zs-image, vmin = -0.1, vmax = 0.1)
plt.show()
