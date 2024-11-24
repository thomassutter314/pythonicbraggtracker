"""
translationcorr.py
Author: Thomas Sutter
Description: 
    scripts for tracking a beam with a 2D gaussian fit
"""

import numpy as np
import matplotlib.pyplot as plt
import scipy.optimize as opt
import scipy as sci
import tifffile

import utils

def determine_guess_params(z_roi,x_roi,y_roi,preliminaryScanNumber,verbose=False):
    numberOf_rows_columns = np.shape(z_roi)
    ##Scans start
    #X axis Scans:
    Z_scannedX = np.zeros([preliminaryScanNumber[0],numberOf_rows_columns[1]])
    Y_scanned = np.zeros(preliminaryScanNumber[0])
    x_maximizing = np.zeros(preliminaryScanNumber[0])
    x_weights_RiemannSums = np.zeros(preliminaryScanNumber[0])
    for i in range(preliminaryScanNumber[0]):
        row = int(numberOf_rows_columns[0]/preliminaryScanNumber[0])*i
        Z_scannedX[i,:] = z_roi[row,:]
        Y_scanned[i] = y_roi[row]
        x_maximizing[i] = x_roi[np.argmax(Z_scannedX[i,:])]
        x_weights_RiemannSums[i] = sum(Z_scannedX[i,:])

    guessVal_x = np.mean(x_maximizing)
    x_weights_RiemannSums = x_weights_RiemannSums - min(x_weights_RiemannSums) #Subtracts off the noise ideally
    if sum(x_weights_RiemannSums) > 0:
        fancy_guessVal_x = np.average(x_maximizing,weights = x_weights_RiemannSums)
    else:
        fancy_guessVal_x = 0

    if verbose == True:
        plotStack(X_ROI,Y_scanned,Z_scannedX)
        plt.plot(x_maximizing,Y_scanned,np.zeros(len(x_maximizing)),'-g',linewidth=4)
        plt.plot(np.ones(len(x_maximizing))*guessVal_x,Y_scanned,np.zeros(len(x_maximizing)),'--k')
        plt.title("X scan")
        plt.xlabel("X")
        plt.ylabel("Y")
        plt.show(block=False)

    #Y axis Scans:
    Z_scannedY = np.zeros([preliminaryScanNumber[1],numberOf_rows_columns[0]])
    X_scanned = np.zeros(preliminaryScanNumber[1])
    y_maximizing = np.zeros(preliminaryScanNumber[1])
    y_weights_RiemannSums = np.zeros(preliminaryScanNumber[1])
    for i in range(preliminaryScanNumber[1]):
        row = int(numberOf_rows_columns[1]/preliminaryScanNumber[1])*i
        Z_scannedY[i,:] = z_roi[:,row]
        X_scanned[i] = x_roi[row]
        y_maximizing[i] = y_roi[np.argmax(Z_scannedY[i,:])]
        y_weights_RiemannSums[i] = sum(Z_scannedY[i,:])

    guessVal_y = np.mean(y_maximizing)
    y_weights_RiemannSums = y_weights_RiemannSums - min(y_weights_RiemannSums) #Subtracts off the noise ideally
    if sum(y_weights_RiemannSums) > 0:
        fancy_guessVal_y = np.average(y_maximizing,weights = y_weights_RiemannSums)
    else:
        fancy_guessVal_y = 0

    if verbose == True:
        plotStack(Y_ROI,X_scanned,Z_scannedY,swapXY = True)
        plt.plot(X_scanned,y_maximizing,np.zeros(len(y_maximizing)),'-g',linewidth=4)
        plt.plot(X_scanned,np.ones(len(y_maximizing))*guessVal_y,np.zeros(len(y_maximizing)),'--k')
        plt.title("Y scan")
        plt.xlabel("X")
        plt.ylabel("Y")
        plt.show(block=False)

    ##Scans end

    ##Scan analysis starts
    #Determine guess for sigma_x
    Y_indexClosest = utils.find_nearest(guessVal_y, y_roi) #Finds the index of the curve closest to 2D guassian peak
    NtenPercent = int(len(z_roi[Y_indexClosest,:])*0.1)+1 # 10% of the number of values in this cross-section. +1 for safety
    bottomVals = np.partition(z_roi[Y_indexClosest,:],NtenPercent)[:NtenPercent] # The smallest 10% of the cross-section plot
    topVals = np.partition(z_roi[Y_indexClosest,:],-NtenPercent)[-NtenPercent:] # The largest 10% of the cross-section plot
    bottomVals_culled = utils.nix_outliers(bottomVals,never_output_empty=True) # Throws away statistical outliers. Returns [0] if input was empty
    topVals_culled = utils.nix_outliers(topVals,never_output_empty=True) # Throws away statistical outliers
    guessVal_offset_xscan = np.mean(bottomVals_culled) # Gives the guess for the offset based on the X scans
    guessVal_amplitude_xscan = np.mean(topVals_culled) - guessVal_offset_xscan # Guess for amplitude based on the X scans
    #print("guessVal_amplitude_xscan",guessVal_amplitude_xscan)
    #print("guessVal_offset_xscan",guessVal_offset_xscan)
    F_x = z_roi[Y_indexClosest,:] - guessVal_offset_xscan # Subtracts away offset from the cross-section
    mean_F_x, var_F_x = utils.pdf_mean_var(F_x)
    guessVal_sigma_x = np.sqrt(var_F_x) # Gets the guess for sigma from a numerical integral

    if verbose == True:
        plt.figure()
        plt.plot(x_roi,z_roi[Y_indexClosest,:],'g--',zorder=2)
        plt.axvline(x=guessVal_x,c='blue',zorder=2,label='guessVal')
        plt.axvline(x=mean_F_x+x_roi[0],c='red',zorder=2,label='mean_F_x+X_ROI[0]')
        plt.axvline(x=fancy_guessVal_x,c='green',zorder=2,label='fancy guess')
        for i in range(len(z_roi[:,0])):
            plt.plot(x_roi,z_roi[i,:],'k-',alpha=0.3,zorder=1)
        plt.xlabel("X axis")
        plt.ylabel("Z axis")
        plt.title('X vs Z')
        plt.legend()
        plt.show(block=False)

    #Determine guess for sigma_y
    X_indexClosest = utils.find_nearest(guessVal_x,x_roi) # Finds the index of the curve closest to 2D guassian peak
    NtenPercent = int(len(z_roi[X_indexClosest,:])*0.1)+1 # 10% of the number of values in this cross-section. +1 for safety
    bottomVals = np.partition(z_roi[X_indexClosest,:],NtenPercent)[:NtenPercent] # The smallest 10% of the cross-section plot
    topVals = np.partition(z_roi[X_indexClosest,:],-NtenPercent)[-NtenPercent:] # The largest 10% of the cross-section plot
    #print(topVals,"topVals")
    bottomVals_culled = utils.nix_outliers(bottomVals,never_output_empty=True) # Throws away statistical outliers. Returns [0] if input was empty
    topVals_culled = utils.nix_outliers(topVals,never_output_empty=True) # Throws away statistical outliers
    #print(topVals_culled,"topVals_culled")
    guessVal_offset_yscan = np.mean(bottomVals_culled) # Gives the guess for the offset based on the Y scans
    guessVal_amplitude_yscan = np.mean(topVals_culled) - guessVal_offset_yscan #guess for amplitude based on the Y scans
    #print(guessVal_offset_yscan,"guessVal_offset_yscan")
    #print(guessVal_amplitude_yscan,"guessVal_amplitude_yscan")
    #print("guessVal_amplitude_yscan",guessVal_amplitude_yscan)
    #print("guessVal_offset_yscan",guessVal_offset_yscan)
    F_y = z_roi[X_indexClosest,:] - guessVal_offset_yscan # Subtracts away offset from the cross-section
    mean_F_y, var_F_y = utils.pdf_mean_var(F_y)
    guessVal_sigma_y = np.sqrt(var_F_y) # Gets the guess for sigma from a numerical integral

    #print("guessVal_sigma_x",guessVal_sigma_x)
    #print("guessVal_sigma_y",guessVal_sigma_y)

    if verbose == True:
        plt.figure()
        plt.plot(y_roi,z_roi[:,X_indexClosest],'g--',zorder=2)
        plt.axvline(x=guessVal_y,c='blue',zorder=2,label='guessVal')
        plt.axvline(x=mean_F_y+y_roi[0],c='red',zorder=2,label='mean_F_x+X_ROI[0]')
        plt.axvline(x=fancy_guessVal_y,c='green',zorder=2,label='fancy guess')
        for i in range(len(z_roi[0,:])):
            plt.plot(y_roi,z_roi[:,i],'k-',alpha=0.3,zorder=1)
        plt.xlabel("Y axis")
        plt.ylabel("Z axis")
        plt.title('Y vs Z')
        plt.legend()
        plt.show(block=False)


    #Takes the average value from the two scans to determine the guess for offset and amplitude
    guessVal_offset = 0.5*(guessVal_offset_xscan + guessVal_offset_yscan)
    guessVal_amplitude = 0.5*(guessVal_amplitude_xscan + guessVal_amplitude_yscan)
    ##Scan analysis ends

    # There are three options for the guess vals here. This one seems like it might be the best
    # ~ guessVal_x = mean_F_x + X_ROI[0]
    # ~ guessVal_y = mean_F_y + Y_ROI[0]
    # in this application, i'm going with the fancy guess val
    guessVal_x = fancy_guessVal_x
    guessVal_y = fancy_guessVal_y

    

    # The zero at the end of the return is the guess angle, it is always zero for this method
    return guessVal_x, guessVal_y, guessVal_sigma_x, guessVal_sigma_y, guessVal_amplitude, guessVal_offset, 0

def _gaussian(m_arr, *args):
    x, y = m_arr
    arr = np.zeros(x.shape)
    arr += utils.gaussian_2d(x, y, *args)
    return arr

def fit_image_to_gaussian(pixel_data, preliminary_scan_number = [20,20], return_guess_params = False,
                          verbose = False, prevfit = [], return_figs = False, cmap = 'plasma'):

    # For best functionality, the preliminary scan number along an axis should be less than or equal to
    # the width in pixels along that axis in the reference image.

    h, w = np.shape(pixel_data) # Determine the height and width of the image to be fit
    x_roi = np.arange(0,w,1)
    y_roi = np.arange(0,h,1)

    if verbose == True:
        print("w = " + str(w),"h = " + str(h))

    #preliminaryScanNumber: array in form [x axis value, y axis value] that specifies the number of
    #scans on each axis that will be performed.
    #These scans serve the purpose of finding good guess values for the 2D Gaussian fit

    if (len(prevfit) == 0) or (return_guess_params == True):
        guess_prms = determine_guess_params(pixel_data,x_roi,y_roi,preliminary_scan_number,verbose=verbose)
    else:
        guess_prms = prevFit

    # Initial guesses to the fit parameters.
    #guess_prms = (guessVal_x, guessVal_y, guessVal_sigma_x, guessVal_sigma_y, guessVal_amplitude, guessVal_offset, guessVal_rotAngle)
    #guess_prms = (guessVal_x, guessVal_y, guessVal_sigma_x, guessVal_sigma_y, guessVal_amplitude, guessVal_offset, guessVal_rotAngle)
    # Hard physical and mathematical boundaries on the fit parameters
    
    if pixel_data.dtype == np.uint8:
        bounds_prms = ([0,0,0,0,0,0,-np.pi/2],[w,h,sci.inf,sci.inf,2**8,2**8,np.pi/2])
    if pixel_data.dtype == np.uint16:
        bounds_prms = ([0,0,0,0,0,0,-np.pi/2],[w,h,sci.inf,sci.inf,2**16,2**16,np.pi/2])
    if pixel_data.dtype == np.float32:
        bounds_prms = ([0,0,0,0,-2**32,-2**32,-np.pi/2],[w,h,sci.inf,sci.inf,2**32,2**32,np.pi/2])
    if pixel_data.dtype == np.float64:
        bounds_prms = ([0,0,0,0,-2**64,-2**64,-np.pi/2],[w,h,sci.inf,sci.inf,2**64,2**64,np.pi/2])
    

    # The two-dimensional domain of the fit.
    x_mesh, y_mesh = np.meshgrid(x_roi, y_roi)

    # Plot the 3D figure of the fitted function and the residuals.
    if verbose == True:
        fig = plt.figure()
        ax = plt.axes(projection='3d')
        ax.plot_surface(x_mesh, y_mesh, pixel_data, cmap=cmap)
        ax.set_zlim(0,np.max(pixel_data)+2)


    if return_guess_params == True:
        return *guess_prms, np.inf

    if verbose == True:
        print("guess (x0,y0,sigma_x,sigma_y,amplitude,offset):")
        print(guess_prms)
        print("bounds")
        print(bounds_prms)

    # We need to ravel the meshgrids of X, Y points to a pair of 1-D arrays.
    xdata = np.vstack((x_mesh.ravel(), y_mesh.ravel()))
    # Do the fit, using our custom _gaussian function which understands our
    # flattened (ravelled) ordering of the data points.

    # Computes the best fit parameters, but the values are in terms of the rotated coordinate system
    popt, pcov = opt.curve_fit(_gaussian, xdata, pixel_data.ravel(), guess_prms,  bounds = bounds_prms)

    fit = np.zeros(pixel_data.shape)
    fit += utils.gaussian_2d(x_mesh, y_mesh, *popt)
    rms = np.sqrt(np.mean((pixel_data - fit)**2))

    if verbose == True:
        print("popt")
        print(popt)
        print('RMS residual =', rms)
        # Plot the 3D figure of the fitted function and the residuals.
        fig = plt.figure()
        ax = plt.axes(projection='3d')
        #ax.plot_surface(X, Y, Z, cmap='plasma')
        ax.plot_surface(X, Y, fit, cmap='plasma')
        ax.set_zlim(0,np.max(Z)+2)
        cset = ax.contourf(X, Y, fit, zdir='z', offset=-4, cmap='plasma')
        #ax.set_zlim(-4,np.max(fit))
        plt.show()
        # Plot the test data as a 2D image and the fit as overlaid contours.
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.imshow(Z, origin='lower', cmap='plasma',
                  extent=(x_roi.min(), x_roi.max(), y_roi.min(), y_roi.max()),zorder=1)
        #levels = [np.exp(-0.5)*popt[4],np.exp(-2)*popt[4],np.exp(-9/2)*popt[4]]
        #print(popt[4])
        ax.contour(X, Y, fit, colors='w',levels = [popt[5]+np.exp(-4.5)*popt[4],popt[5]+np.exp(-2)*popt[4],popt[5]+np.exp(-1/2)*popt[4]],zorder=2)
        #Draw annotation lines that indicate contour lengths. 1, 2, & 3 sigma contours are shown for the gaussian
        startX = popt[0]
        startY = popt[1]
        sigmaEffective = np.sqrt((popt[2]**2+popt[3]**2)/2)
        for j in range(3):
            angle = j*np.radians(120)-np.radians(90)
            diffX = np.cos(angle)*sigmaEffective*(j+1)
            diffY = np.sin(angle)*sigmaEffective*(j+1)
            ax.annotate("", xy=(startX+0.5*diffX, startY+0.5*diffY), xytext=(startX+diffX, startY+diffY),arrowprops=dict(arrowstyle="-"),zorder=3)
            ax.annotate(str(j+1) + r"$\sigma_{rms}$", xy=(startX, startY), \
                        xytext=(startX+0.4*diffX, startY+0.4*diffY),arrowprops=dict(arrowstyle='-'), \
                        zorder=3,horizontalalignment="center")
        ax.scatter(startX,startY,marker='+',s=100,c='green',zorder=4)
        #print(popt)
        #plt.xlim([-3*sigmaEffective+startX,3*sigmaEffective+startX])
        #plt.ylim([-3*sigmaEffective+startY,3*sigmaEffective+startY])
        plt.show()

    if return_figs == True:
        # Plot the test data as a 2D image and the fit as overlaid contours.
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.imshow(pixel_data, origin='lower', cmap='plasma',
                  extent=(x_roi.min(), y_roi.max(), y_roi.min(), y_roi.max()),zorder=1)
        #levels = [np.exp(-0.5)*popt[4],np.exp(-2)*popt[4],np.exp(-9/2)*popt[4]]
        #print(popt[4])
        ax.contour(x_mesh, y_mesh, fit, colors='w',levels = [popt[5]+np.exp(-4.5)*popt[4],popt[5]+np.exp(-2)*popt[4],popt[5]+np.exp(-1/2)*popt[4]],zorder=2)
        #Draw annotation lines that indicate contour lengths. 1, 2, & 3 sigma contours are shown for the gaussian
        startX = popt[0]
        startY = popt[1]
        sigmaEffective = np.sqrt((popt[2]**2+popt[3]**2)/2)
        for j in range(3):
            angle = j*np.radians(120)-np.radians(90)
            diffX = np.cos(angle)*sigmaEffective*(j+1)
            diffY = np.sin(angle)*sigmaEffective*(j+1)
            ax.annotate("", xy=(startX+0.5*diffX, startY+0.5*diffY), xytext=(startX+diffX, startY+diffY),arrowprops=dict(arrowstyle="-"),zorder=3)
            ax.annotate(str(j+1) + r"$\sigma_{rms}$", xy=(startX, startY), \
                        xytext=(startX+0.4*diffX, startY+0.4*diffY),arrowprops=dict(arrowstyle='-'), \
                        zorder=3,horizontalalignment="center")
        ax.scatter(startX,startY,marker='+',s=100,c='green',zorder=4)
        
        return fig, ax, popt, rms, guess_prms
    else:
        # Returns the fit parameters and the badness of fit
        return popt, rms, guess_prms
   
def plotStack(x, y, Z,swapXY=False):
    #x should be single array of values along x axis, plotting axis
    #y should be single array of values along y axis, jumping axis (len(y) must equal number of curves)
    #Z should be a collection of arrays for the different lines
	plt.figure()
	ax = plt.subplot(projection='3d')
	numberOfCurves = np.shape(Z)[0]
	if swapXY == False:
		for i in range(numberOfCurves):
			yy = np.ones(x.size)*y[i]
			ax.plot(x,yy,Z[i])
	else:
		for i in range(numberOfCurves):
			yy = np.ones(x.size)*y[i]
			ax.plot(yy,x,Z[i])


if __name__ == '__main__':
    image = tifffile.imread(r"C:\Users\thoma\OneDrive - UCLA IT Services\Documents\GitHub\smartScan\initialRoi_0.tiff")
    fit_image_to_gaussian(image,verbose=True)
