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
import scipy.optimize as opt
import scipy.special as spec
import matplotlib.pyplot as plt
import tifffile
import os


# Fit functions
def G1(t, t0, w1, a):
    return 1-a*0.5*(1+spec.erf((t-t0)/(np.sqrt(2)*w1)))

def G2(t, t0, w1, A1, A2, tau):
	return 1-0.5*(1+spec.erf((t-t0)/(np.sqrt(2)*w1)))*(A1 + A2*np.exp(-(t-t0)/tau))

# Read in all the batches and fit specific sets
def fit_batches(data_loc, bin_size = 1, fit_func = G1, p0 = [0, 0.2, 0.4], plot_guess = False):
    # Give this function an array where the 1st column is the delay stage steps,
    # and the other columns are the intensities of the variuos batches.
    # The function will fit each batch with a given fit_func and produce a plot of time-zero vs. batch number.
    data_raw = np.loadtxt(data_loc, skiprows = 1, delimiter = ',')
    signals_raw = data_raw[:, 1:]
    dsPos = data_raw[:, 0]
    
    signals = np.zeros([signals_raw.shape[0], int(np.ceil(signals_raw.shape[1]/bin_size))])
    print(signals.shape)
    print(signals_raw.shape)
    for i in range(signals_raw.shape[1]):
        signals[:, i//bin_size] += signals_raw[:, i]
    
    t0pos = 57.7
    times = 6.67*(t0pos - dsPos)
    signal = np.mean(signals, axis = 1)/np.mean(signals[-5:])
    if not plot_guess:
        popt, pcov = opt.curve_fit(fit_func, times, signal, p0 = p0)
    else:
        popt, pcov = p0, np.zeros([len(p0), len(p0)])
    print(f'popt of average: {popt}')
    tt = np.linspace(min(times), max(times), 1000)
    yy = fit_func(tt, *popt)
    plt.plot(tt, yy, 'k-', label = f'avg, t0_pos = {round(t0pos - popt[0]/6.67, 4)} mm \nw1 = {round(popt[1], 2)} ps')
    plt.scatter(times, signal, c = 'black', marker = 's')
    
    t0 = popt[0]
    batch_nums = []
    t0vals = []
    t0vals_err = []
    w1vals = []
    w1vals_err = []
    
    cmap = plt.cm.jet
    for i in range(signals.shape[1]):
        signal = signals[:, i]/np.mean(signals[-5:, i])
        if not plot_guess:
            popt, pcov = opt.curve_fit(fit_func, times, signal, p0 = p0)
        else:
            popt, pcov = p0, np.zeros([len(p0), len(p0)])
        batch_nums.append(i)
        t0vals.append(popt[0])
        t0vals_err.append(np.sqrt(pcov[0,0]))
        w1vals.append(popt[1])
        w1vals_err.append(np.sqrt(pcov[1,1]))
        tt = np.linspace(min(times), max(times), 1000)
        yy = fit_func(tt, *popt)
        
        if bin_size == 1:
            plotLabel = f'batch{i}'
        else:
            if signals_raw.shape[1] > (i+1)*bin_size - 1:
                plotLabel = f'batch: {i*bin_size}-{(i+1)*bin_size - 1}'
            else:
                plotLabel = f'batch: {i*bin_size}-{signals_raw.shape[1] - 1}'
        
        plt.plot(tt, yy, linestyle = '--', label = plotLabel, c = cmap(i/(signals.shape[1] - 1)))
        plt.scatter(times, signal, color = cmap(i/(signals.shape[1] - 1)))
    
    plt.legend()
    plt.show()
    
    t0vals = np.array(t0vals) - t0
    
    fig, axs = plt.subplots(1, 2)
    plt.suptitle(f'bin_size = {bin_size}')
    axs[0].errorbar(batch_nums, t0vals, yerr = t0vals_err, fmt="o")
    axs[0].set_ylabel(r'$t_0$ (ps)')
    axs[0].set_xlabel(r'batch index')
    axs[1].errorbar(batch_nums, w1vals, yerr = w1vals_err, fmt="o")
    axs[1].set_ylabel(r'$w_1$ (ps)')
    axs[1].set_xlabel(r'batch index')
    plt.show()

# Read in specific batches and plot average
def fit_batch_set(data_loc, t0pos, batches, fit_func = G1, p0 = [0, 0.2, 0.4],
                  plot_guess = False, plot_individual_batches = False, plot = True, save = True):
    data_raw = np.loadtxt(data_loc, skiprows = 1, delimiter = ',')
    signals_raw = data_raw[:, 1:]
    dsPos = data_raw[:, 0]
    times = 6.67*(t0pos - dsPos)
    # ~ times = dsPos
    
    signal = np.zeros(signals_raw.shape[0])
    normed_curves = np.zeros([len(batches), signals_raw.shape[0]])
    for i in range(len(batches)):
        signal += signals_raw[:, batches[i]]/len(batches)
        temp_sig = signals_raw[:, batches[i]]/len(batches)
        temp_sig = temp_sig/np.mean(temp_sig[-5:])
        normed_curves[i] = temp_sig
        if plot_individual_batches:
            plt.scatter(times, temp_sig, marker = 's', label = batches[i])
    
    # Compute std from normed_curves
    err = np.std(normed_curves, axis = 0)/np.sqrt(len(batches))
    
    # Normalize signal
    signal = signal/np.mean(signal[-5:])
        
    if not plot_guess:
        popt, pcov = opt.curve_fit(fit_func, times, signal, p0 = p0)
    else:
        popt, pcov = p0, np.zeros([len(p0), len(p0)])
    print(f'popt of average: {popt}')
    tt = np.linspace(min(times), max(times), 1000)
    yy = fit_func(tt, *popt)
    
    if save:
        np.savetxt('batch_set_data.csv', np.array([times, signal]).transpose(), header = 'times, signal', delimiter = ',')
    
    if plot:
        plt.plot(tt, yy, 'k-', label = f'avg, t0_pos = {round(t0pos - popt[0]/6.67, 4)} mm \nw1 = {round(popt[1], 2)} ps')
        plt.errorbar(times, signal, err, c = 'black', fmt = 'none', capsize = 5)
        plt.scatter(times, signal, c = 'black', marker = 's')
        plt.legend()
        plt.show()
        
    return times, signal, tt, yy

def readBatchMetaDataWeight(fileDir, pi):
    with open(fileDir, 'r') as f:
        metaData = f.readlines()

    idString_start = f'pi = '
    idString_finish = f', dsPos'
    weightString = f'weight = '
    for l in range(len(metaData)):
        if idString_start in metaData[l]:
            index_start = metaData[l].find(idString_start) + len(idString_start)
            index_finish = metaData[l].find(idString_finish)
            if pi == int(metaData[l][index_start:index_finish]):
                indexWeight = metaData[l].find(weightString) + len(weightString)
                weight = int(metaData[l][indexWeight:])
                return weight

def average_batches(scan_dir, save_dir, batch_list = [0, 1], image_dtype = np.float32):
    # Give this function a scan directory along with a list of batches
    # The function will load each batch and make a new directory of images
    # which contains batch averaged images. Useful if you want to just average specific batches.
    
    # Create the array that will store the averaged images
    file_arr = os.listdir(scan_dir + r'//batch' + str(batch_list[0]))
    image_path_arr = [x for x in file_arr if x[:4] == 'pos=' and x[-5:] == '.tiff']
    dsPosString_arr = [x[4:-5] for x in image_path_arr]
    example_image = tifffile.imread(scan_dir + r'//batch' + str(batch_list[0]) + r'//' + image_path_arr[0])
    images_avg = np.zeros([len(image_path_arr), example_image.shape[0], example_image.shape[1]], dtype = image_dtype) # The batch averaged images go in this array
    wAvg = np.zeros(len(image_path_arr)) # keep track of the weights corresponding to each image
    
    for bi in range(len(batch_list)):
        print(f'Working on batch {batch_list[bi]}')
        file_arr = os.listdir(scan_dir + r'//batch' + str(batch_list[bi]))
        image_path_arr = [x for x in file_arr if x[:4] == 'pos=' and x[-5:] == '.tiff']
        for pi in range(len(image_path_arr)):
            imNew = tifffile.imread(scan_dir + r'//batch' + str(batch_list[bi]) + f'//pos={dsPosString_arr[pi]}.tiff') # Load the image corresponding to this position and the latest batch
            wNew = readBatchMetaDataWeight(fileDir = scan_dir + r'//batch' + str(batch_list[bi]) + '//batchMetaData.txt', pi = pi)
            images_avg[pi] = (wNew*imNew + wAvg[pi]*images_avg[pi])/(wNew + wAvg[pi])
            wAvg[pi] += wNew
            
            
    for pi in range(len(image_path_arr)):
        print(f'Saving image: {dsPosString_arr[pi]}')
        tifffile.imwrite(f'{save_dir}//pos={dsPosString_arr[pi]}.tiff', images_avg[pi])
            
            

if __name__ == '__main__':
    # ~ fit_batches(data_loc = r'F:\2024_12_6_KrampusWeekendScans_VTe2_fluenceSet\analysis\2Ko_2nd_batches.csv', 
                # ~ bin_size = 5, fit_func = G1)
                # ~ bin_size = 4, fit_func = G2, p0 = [0.3,  0.2, 0.2, 0.1, 1], plot_guess = False)

    fit_batch_set(data_loc = r'F:\2024_12_6_KrampusWeekendScans_VTe2_fluenceSet\analysis\2Ko_new_batches.csv',
                plot = True, t0pos = 57.7 + 0.114/6.67, batches = [6,7,9,10,11,12,13,14], fit_func = G2, p0 = [0.3,  0.2, 0.2, 0.1, 1], plot_guess = False)        
    
    # To compare two scans
    if False:
        times, signal_1, tt, yy_1 = fit_batch_set(data_loc = r'C:\Users\Kogar\Documents\electron_beam_photos\scans\2024_12_6_KrampusWeekendScans_VTe2_fluenceSet\analysis\2Ko_new_batches.csv',
                        plot = False, t0pos = 57.7 + 0.114/6.67, batches = [7,8,9,10,11,12,13], fit_func = G2, p0 = [0.3,  0.2, 0.2, 0.1, 1], plot_guess = False)
        
        plt.plot(tt, yy_1, 'r-', label = f'')
        plt.scatter(times, signal_1, c = 'red', marker = 's')
        
        times, signal_2, tt, yy_2 = fit_batch_set(data_loc = r'C:\Users\Kogar\Documents\electron_beam_photos\scans\2024_12_6_KrampusWeekendScans_VTe2_fluenceSet\analysis\2Ko_2nd_batches.csv',
                        plot = False, t0pos = 57.7 + 0.451/6.67, batches = [0,1,2,3,4,5,6,7], fit_func = G2, p0 = [0.3,  0.2, 0.2, 0.1, 1], plot_guess = False)
        
        # ~ signal = (signal_1 + signal_2)/2
        # ~ yy = (yy_1 + yy_2)/2
        plt.plot(tt, yy_2, 'k-', label = f'')
        plt.scatter(times, signal_2, c = 'black', marker = 's')
        
        plt.show()
    
    # ~ average_batches(scan_dir = r'C:\Users\Kogar\Documents\electron_beam_photos\scans\2024_12_5_VTe2_4Ko',
                    # ~ save_dir = r'C:\Users\Kogar\Documents\electron_beam_photos\scans\2024_12_5_VTe2_4Ko\analysis\batch0-4avg',
                    # ~ batch_list = [0,1,2,3,4])

