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
import tifffile
import scipy.optimize as opt
import os
import re

import utils
 
def pixel_sum_batches_single_fluence(scandir, roi_mask):
    """
    image that is zero everywhere except the roi where it is 1
    """
    
    roi_indices = np.where(roi_mask > 0)
    
    dirlist = os.listdir(scandir)
    batchlist = []
    batchnumberlist = []
    for f in dirlist:
        if 'batch' in f and not '.' in f:
            batchlist.append(f)
            batchnumberlist.append(int(f[5:]))
            
    sorted_indices = np.argsort(batchnumberlist)
    batchnumberlist_sorted = [0]*len(sorted_indices)
    batchlist_sorted = ['']*len(sorted_indices)
    for i in range(len(sorted_indices)):
        batchnumberlist_sorted[i] = batchnumberlist[sorted_indices[i]]
        batchlist_sorted[i] = batchlist[sorted_indices[i]]
        
    # Load the delay stage positions and file size from the 1st batch (batch0)
    file_list_0 = os.listdir(f'{scandir}//{batchlist_sorted[0]}')
    im_list_0 = [] # a list storing the file names of just the image files
    dspos_list = [] # a list storing all the delaystage positions in the scan
    
    # go through all the files, select out the images, and store the delay stage positions from the filenames in a list
    for i in range(len(file_list_0)):
        if file_list_0[i].find('.tiff') == -1:
            continue # This means the file here is something other than a tiff in the scan (e.g. the meta data file)
        
        s = file_list_0[i][file_list_0[i].find('pos=')+4:]
        sn = utils.grab_leading_number_from_string(s)
        
        dspos_list.append(float(sn))
        im_list_0.append(file_list_0[i])
        
    sorted_indices = np.argsort(dspos_list)
    dspos_list_sorted = [0]*len(dspos_list)
    im_list_sorted = ['']*len(dspos_list)
    
    for i in range(len(sorted_indices)):
        dspos_list_sorted[i] = dspos_list[sorted_indices[i]]
        im_list_sorted[i] = im_list_0[sorted_indices[i]]
        
    image_0 = tifffile.imread(f'{scandir}//{batchlist_sorted[0]}//{im_list_sorted[0]}')
    h, w = image_0.shape
    pixel_sums = np.zeros([len(batchlist_sorted), len(dspos_list_sorted)]) # Shape is batch, position, roi
        
    # run through the batch lists and collect the pixel sums
    for bi in range(len(batchlist_sorted)):
        print(f'Loading batch {bi}')
        for pi in range(len(dspos_list)):
            im = tifffile.imread(f'{scandir}//{batchlist_sorted[bi]}//{im_list_sorted[pi]}')
            pixel_sums[bi, pi] = np.average(im[roi_indices])
            
    return dspos_list, pixel_sums



def erf_t0_fit_batches(dspos_list, signals, p0s = None, p0tot = None):
    popts = np.empty([signals.shape[0], 4])
    pcovs = np.empty([signals.shape[0], 4, 4])
    for i in range(signals.shape[0]):
        if p0s == None:
            p0 = [np.mean(dspos_list), 0.1*np.std(dspos_list), max(signals[i]) - min(signals[i]), min(signals[i])]
        else:
            p0 = p0s[i]
            
        #erf_fit_func(x, mu, sigma, amp, offset)
        popts[i], pcovs[i] = opt.curve_fit(utils.erf_fit_func, dspos_list, signals[i], p0 = p0)
        
    mean_signal = np.mean(signals, axis = 0)
    if p0tot == None:
        p0 = [np.mean(dspos_list), 0.1*np.std(dspos_list), max(mean_signal) - min(mean_signal), min(mean_signal)]
    else:
        p0 = p0tot
    # Do one final fit on the combined signal of all the batches
    popt_tot, pcov_tot = opt.curve_fit(utils.erf_fit_func, dspos_list, mean_signal, p0 = p0)
    
    return popts, pcovs, popt_tot, pcov_tot


 
if __name__ == "__main__":
    # ~ load_images_smartscan_single_fluence(r'C:\Users\thoma\Documents\GitHub\pythonicbraggtracker\2024_8_8_check_t0_scan_4')
    # ~ a = grab_leading_number_from_string('242.2134afdadf').group()
    # ~ print(a)
    roimask = tifffile.imread(r"C:\Users\thoma\Documents\GitHub\pythonicbraggtracker\roi_mask_test.tif")
    dspos_list, pixel_sums = pixel_sum_batches_single_fluence(r'C:\Users\thoma\Documents\GitHub\pythonicbraggtracker\2024_8_8_check_t0_scan_4', roimask)

    popts, pcovs, popt_tot, pcov_tot = erf_t0_fit_batches(dspos_list, pixel_sums)

    import matplotlib.pyplot as plt
    
    tt = np.linspace(min(dspos_list), max(dspos_list), 1000)
    for bi in range(pixel_sums.shape[0]):
        yy = utils.erf_fit_func(tt, *popts[bi])
        plt.plot(tt, yy)
        plt.scatter(dspos_list, pixel_sums[bi,:], label = f'batch{bi}')
    
    yy = utils.erf_fit_func(tt, *popt_tot)
    plt.plot(tt, yy)
    plt.scatter(dspos_list, np.mean(pixel_sums, axis = 0), label = f'total')
    
    plt.legend()
    plt.show()
    
    fig, ax = plt.subplots()
    ylim_max = max(popts[:,0])
    ylim_min = min(popts[:,0])
    ax.set_ylim([ylim_min,ylim_max])
    
    ax2 = ax.twinx()
    tzpos_mean = popt_tot[0]
    ylim2_max = 6.67*1e3*(tzpos_mean - ylim_max)
    ylim2_min = 6.67*1e3*(tzpos_mean - ylim_min)
    
    ax2.set_ylim([ylim2_min, ylim2_max])
    
    ax.plot(popts[:,0])
    plt.show()
    
