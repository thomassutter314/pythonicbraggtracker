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
    file_list = os.listdir(scandir)
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
    image_0 = tifffile.imread(f'{scandir}//{im_list[0]}')
    h, w = image_0.shape
    images = np.empty([len(im_list),h, w])
        
    sorted_indices = np.argsort(dspos_list)
    dspos_list_sorted = [0]*len(dspos_list)
    im_list_sorted = ['']*len(dspos_list)
    
    for i in range(len(sorted_indices)):
        dspos_list_sorted[i] = dspos_list[sorted_indices[i]]
        im_list_sorted[i] = im_list[sorted_indices[i]]
        
        print(f'Loading image: {im_list_sorted[i]}')
        images[i] = tifffile.imread(f'{scandir}//{im_list_sorted[i]}')
    
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

