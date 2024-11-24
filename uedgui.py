"""
gui.py
Author: Thomas Sutter
Description: 
    GUI for the UED data analysis program
"""


"""
The goal of this script is to provide a user interface for data analysis.

"""

import tkinter as tk
from tkinter import filedialog as fd
from tkinter import ttk
# ~ import random as rand
import matplotlib
matplotlib.use('TkAgg')
# ~ from matplotlib.ticker import FormatStrFormatter
from matplotlib.backends.backend_tkagg import FigureCanvasTk, NavigationToolbar2Tk
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.gridspec as gridspec
import matplotlib.widgets
from matplotlib import cm
# ~ import matplotlib.animation as animation
# ~ from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg,
    NavigationToolbar2Tk)
    
# Use a matplotlib backend that doesn't have an associated gui
# ~ plt.switch_backend('agg')

import numpy as np
import scipy
import time
import datetime
import threading
import tifffile
import json
import os
import csv

import translationcorr
import calibratebravais
import utils


def make_separate_plot_window(fig, rootTitle, data = None, dataHeader = ''):
    print(data)
    # The data arguments are just in case you want to provide a way for the user to save the data
    # Some general formatting vars
    padyControls = 1
    padySep = 1
    entryWidth = 10
    largeEntryWidth = 20
    sepWidth = 230
    sepHeight = 1
    buttonWidth = 18
    cntrlBg = '#2F8D35'
    
    separate_root = tk.Tk()
    separate_root.title(rootTitle)
    separate_canvas = FigureCanvasTkAgg(fig, master=separate_root)
    separate_canvas.draw()
    separate_canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
    
    # Make a Tkinter frame for the controls
    controls = tk.Frame(master=separate_root, width=50, height=100, padx=5, pady=5)
    controls.pack(side=tk.LEFT)
    
    def saveDataButtonFunc():
        file_path = fd.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        
        if type(data) == type(np.array([])):
            np.savetxt(file_path,data,delimiter = ',',header = dataHeader)
            
        if type(data) == type([]):
            # Transpose the list of lists using zip
            transposed_data = zip(*data)
            with open(file_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(dataHeader)  # Write the header
                writer.writerows(transposed_data)
        
                
    saveDataButton = tk.Button(
        master=controls,
        text="Save Plot Data",
        width=buttonWidth,
        height=1,
        fg='black', bg='white',
        command=saveDataButtonFunc)
        
    saveDataButton.pack()
    
    
    # Add the Matplotlib toolbar to the separate window
    toolbar = NavigationToolbar2Tk(separate_canvas, separate_root)
    toolbar.update()
    separate_canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
    
def make_profile_plot3d(time, data, xdata, tlabel, xlabel, rootTitle, title):
    fig, ax = plt.subplots()
    
    # Create a list of colors corresponding to each plot
    colors = plt.cm.viridis(np.linspace(0, 1, len(time)))
    
    for ti in range(len(time)):
        ax.plot(xdata,data[ti],color=colors[ti],alpha=0.8)
        
    ax.set_xlabel(xlabel)
    ax.set_title(title)
        
    # Create a ScalarMappable object for the colorbar
    sm = cm.ScalarMappable(cmap=plt.cm.viridis)
    sm.set_array(time)
    
    # Add a colorbar
    cbar = plt.colorbar(sm, ax=ax, label='Time')
    
    # Set title for the colorbar
    cbar.set_label(tlabel, rotation=90, labelpad=10)
    
    dataToSave = [xdata]
    header = ['xdata']
    for i in range(len(data[:,0])):
        dataToSave.append(data[i,:])
        header.append(f'pos {i}')

    make_separate_plot_window(fig, rootTitle, data = dataToSave, dataHeader = header)

class RoiRectangle():
    def __init__(self,cx,cy,w,h,ax):
        self.cx = cx
        self.cy = cy
        self.w = w
        self.h = h
        tl_x = self.cx - w/2
        tl_y = self.cy - h/2
        self.patch = patches.Rectangle((tl_x, tl_y), self.w, self.h, linewidth=1, edgecolor='r', facecolor='none', alpha=0.8)
        self.live = False
        self.onColor = 'white'
        self.offColor = 'red'
        
        self.cRadius = 1
        # ~ self.cpatch = patches.Circle((self.cx,self.cy),self.cRadius, edgecolor=(1, 0, 0, 0.5), facecolor=(1, 0, 0, 1),fill=False)
        
        ax.add_patch(self.patch) # Add the patch to the axis
        self.title_y_offset = 1
        self.roiTitle = ax.text(tl_x, tl_y-self.title_y_offset, f'{int(self.cx)}, {int(self.cy)}', fontsize=6, color='red')
        # ~ ax.add_patch(self.cpatch) # Add the center patch to the axis
    
    def updateShape(self, w, h):
        self.w = w
        self.h = h
        tl_x = self.cx - self.w/2
        tl_y = self.cy - self.h/2
        self.patch.set_xy((tl_x,tl_y)) # Update patch top left corner
        self.patch.set_width(self.w) # Update the patch with new width
        self.patch.set_height(self.h) # Update the patch with new height
        self.roiTitle.set_position((tl_x, tl_y-self.title_y_offset))
        
    def updatePosition(self, x, y):
        self.cx = x
        self.cy = y
        tl_x = self.cx - self.w/2
        tl_y = self.cy - self.h/2
        self.patch.set_xy((tl_x,tl_y)) # Update patch top left corner
        self.roiTitle.set_position((tl_x, tl_y-self.title_y_offset))
        self.roiTitle.set_text(f'{int(self.cx)}, {int(self.cy)}')
    
    def goDead(self):
        self.patch.set_edgecolor(self.offColor)
        self.roiTitle.set_color(self.offColor)
        self.live = False
        
    def goLive(self):
        if self.w < 1:
            self.w = 1 # Minimum width is a single pixel
        if self.h < 1:
            self.h = 1 # Minimum height is a single pixel
        tl_x = self.cx - self.w/2
        tl_y = self.cy - self.h/2
        self.patch.set_xy((tl_x,tl_y)) # Update patch top left corner
        self.patch.set_width(self.w) # Update the patch with new width
        self.patch.set_height(self.h) # Update the patch with new height
        self.patch.set_edgecolor(self.onColor)
        self.roiTitle.set_color(self.onColor)
        self.live = True
        
    def updateAxis(self, ax):
        del self.patch
        tl_x = self.cx - self.w/2
        tl_y = self.cy - self.h/2
        self.patch = patches.Rectangle((tl_x, tl_y), self.w, self.h, linewidth=1, edgecolor='r', facecolor='none', alpha=0.8)
        ax.add_patch(self.patch) # Add the patch to the axis
        
    def getRoiImage(self, image):
        return image[int(self.cy-self.h/2):int(self.cy+self.h/2),int(self.cx-self.w/2):int(self.cx+self.w/2)]
        
    def getProfile(self, image, genPlots = True):
        imageRoi = self.getRoiImage(image)
        
        lineprofile_x = np.mean(imageRoi, axis = 0)
        lineprofile_y = np.mean(imageRoi, axis = 1)
        
        xpixels = np.linspace(self.cx-self.w/2,self.cx+self.w/2,len(lineprofile_x))
        ypixels = np.linspace(self.cy-self.h/2,self.cy+self.h/2,len(lineprofile_y))
        
        if genPlots:
            rootTitle = f"Profiles, c_x, c_y = {int(self.cx)}, {int(self.cy)}"
            
            # Create the separate figure
            fig, axs = plt.subplots(1,2)
            
            axs[0].plot(xpixels,lineprofile_x)
            axs[0].set_xlabel('X Axis (pixels)')
            axs[0].set_title('Averaged over Y Axis')
            axs[1].plot(ypixels,lineprofile_y)
            axs[1].set_xlabel('Y Axis (pixels)')
            axs[1].set_title('Averaged over X Axis')
            
            dataToSave = [lineprofile_x,lineprofile_y]
            header = ['x profile', 'y profile']
            make_separate_plot_window(fig, rootTitle, data = dataToSave, dataHeader = header)

        return xpixels, lineprofile_x, ypixels, lineprofile_y

    def checkClicked(self, mouse_x, mouse_y):
        # Was the click inside this roi
        return (abs(mouse_x-self.cx) < self.w/2 and abs(mouse_y-self.cy) < self.h/2)
    
    def destroy(self):
        self.patch.remove() # Remove the patch from the plot
        del self.patch # Delete the patch
        self.roiTitle.remove()# Remove the text from the plot
        del self.roiTitle # Delete the text
        
class timeTraceGUI():
    def __init__(self, wait = .033): 
        # Setup the tkinter GUI window
        self.root = tk.Tk()
        self.root.geometry("1650x700")
        self.root.configure(bg='white')
        self.root.wm_title("pbt")
        
        #Selection variables
        self.timeZeroPos = 0
        
        self.aReciprocal = np.array([0,0])
        self.bReciprocal = np.array([0,0])
        self.gammaReciprocal = np.array([0,0])
        
        # Data display settings and variables
        self.wait = wait
        self.rm = [] # list of rois
        self.roiActive = False
        self.relocatingRoi = None # The roi that the user is currently dragging around with the mouse
        self.relocatePin_x, self.relocatePin_y = 0, 0
        
        # Some general formatting vars
        padyControls = 1
        padySep = 1
        entryWidth = 10
        largeEntryWidth = 20
        sepWidth = 230
        sepHeight = 1
        buttonWidth = 18
        cntrlBg = '#2F8D35'
        
        # Make a Tkinter frame for the image
        self.imageFrame = tk.Frame(master=self.root, width=300, height=300, padx=5, pady=5, bg=cntrlBg)
        self.imageFrame.pack(side=tk.LEFT)
        
        # Make a Tkinter frame for the ROI selection buttons
        self.controls = tk.Frame(master=self.root, width=50, height=100, padx=5, pady=5, bg=cntrlBg)
        self.controls.pack(side=tk.LEFT)
        
        # Make a Tkinter frame for the data plots
        self.dataFrame = tk.Frame(master=self.root, width=50, height=100, padx=5, pady=5, bg=cntrlBg)
        self.dataFrame.pack(side=tk.LEFT)
        
        # Adding the ROI controls
        self.roiSelection = tk.StringVar(self.controls)
        self.roiSelection.set("rectangle") # default value
        def roiSelectionFunc(choice):
            self.clearRois()
        self.roiSelectionMenu = tk.OptionMenu(self.controls, self.roiSelection, "rectangle", "ellipse", "annulus", "line", command = roiSelectionFunc)
        
        def calibrateBravaisLatticeButtonFunc():
            if len(self.bravaisLatticePlotObjects) > 0:
                for po in self.bravaisLatticePlotObjects:
                    po.remove()# Remove objects from plot
                    del po # Delete objects
                self.bravaisLatticePlotObjects = [] # empty the list
                # Draw the canvas
                self.canvas.draw()
                self.calibrateBravaisLatticeButton.config(bg='white') # Set this button as inactive color
            else:
                roiImages = []
                cxs, cys = [], []
                for r in self.rm:
                    # Only count an ROI if it is active
                    if r.live:
                        roiImages.append(r.getRoiImage(self.imageSet[self.liveImageIndex]))
                        cxs.append(r.cx)
                        cys.append(r.cy)
                gamma, a, b = calibratebravais.measureLattice(self.imageSet[self.liveImageIndex],roiImages, cxs, cys, self.calibrationMillerIndicesEntry.get())
                # Store the reciprocal lattice vectors as global variables on this object
                self.aReciprocal = a
                self.bReciprocal = b
                self.gammaReciprocal = gamma
                latticePlotOrder=16
                for i in range(latticePlotOrder):
                    for j in range(latticePlotOrder):
                        I = i-latticePlotOrder//2
                        J = j-latticePlotOrder//2
                        self.bravaisLatticePlotObjects.append(self.imageAx.arrow(gamma[0]+I*a[0]+J*b[0],gamma[1]+I*a[1]+J*b[1],a[0],a[1],alpha=0.3))
                        self.bravaisLatticePlotObjects.append(self.imageAx.arrow(gamma[0]+I*a[0]+J*b[0],gamma[1]+I*a[1]+J*b[1],b[0],b[1],alpha=0.3))
                self.bravaisLatticePlotObjects.append(self.imageAx.scatter(gamma[0],gamma[1],color='red'))
                self.bravaisLatticePlotObjects.append(self.imageAx.text(gamma[0],gamma[1],'$\Gamma$'))
                # Draw the canvas
                self.canvas.draw()
                self.calibrateBravaisLatticeButton.config(bg='yellow') # Set this button as active color

        self.calibrateBravaisLatticeButton = tk.Button(
            master=self.controls,
            text="Calibrate Bravais Lattice",
            width=buttonWidth,
            height=1,
            fg='black', bg='white',
            command=calibrateBravaisLatticeButtonFunc)
    
        self.bravaisLatticePlotObjects = [] # A list that holds all of the plots associated with a bravias lattice calibration
        
        self.calibrationMillerIndicesEntry = tk.Entry(master=self.controls, width = entryWidth)
        self.roiFromMillerIndicesEntry = tk.Entry(master=self.controls, width = entryWidth)
        self.roiFromMillerIndicesSizeEntry = tk.Entry(master=self.controls, width = entryWidth)
        self.roiFromMillerIndicesSizeEntry.insert(-1,50)
        
        self.measureSelection = tk.StringVar(self.controls)
        self.measureSelection.set("time trace of gaussian fit") # default value
        self.measureSelectionMenu = tk.OptionMenu(self.controls, self.measureSelection, "time trace of gaussian fit", "static gaussian fit to current image", "time trace of profile", "static profile of current image")
        
        self.tZeroPos_label_string = tk.StringVar()
        self.tZeroPos_label_string.set(f'Time Zero Pos = {self.timeZeroPos} mm')
        tZeroPos_label = tk.Label(master=self.controls,textvar=self.tZeroPos_label_string, bg=cntrlBg)
        self.tZeroPosEntry = tk.Entry(master=self.controls, width = entryWidth)
        
        self.varConvertToTime = tk.IntVar()
        # When the convert to time check box state is changed, update the data plot xdata and replot the data plot
        def convertToTimeFunc():
            if self.varConvertToTime.get() == 1:
                self.activexdata = 6.67*(self.timeZeroPos - self.dsPositions)
                self.dataPlot.set_xdata(self.activexdata)
                self.activexlabel = r'$t-t_0$ (ps)'
                self.dataAx.set_xlabel(self.activexlabel)
            else:
                self.activexdata = self.dsPositions
                self.dataPlot.set_xdata(self.activexdata)
                self.activexlabel = 'dsPos (mm)'
                self.dataAx.set_xlabel(self.activexlabel)
                
            # Redo the xlimits on the plot
            self.dataAx.set_xlim([min(self.activexdata),max(self.activexdata)])
            self.datacanvas.draw()
        self.convertToTimeBox = tk.Checkbutton(master=self.controls, text='Convert to Time (ps)',variable=self.varConvertToTime, onvalue=1, offvalue=0, command = convertToTimeFunc ,bg=cntrlBg)
        
        def measureButtonFunc():
            selection = self.measureSelection.get()
            if selection == "static profile of current image":
                for r in self.rm:
                    # Only count an ROI if it is active
                    if r.live:
                        r.getProfile(self.imageSet[self.liveImageIndex])
            if selection == "time trace of profile":
                for r in self.rm:
                    # Only count an ROI if it is active
                    if r.live:
                        data_0 = r.getProfile(self.imageSet[0], genPlots = False)
                        if self.roiSelection.get() == "rectangle":
                            data_x = np.empty([len(self.activexdata),len(data_0[1])])
                            data_y = np.empty([len(self.activexdata),len(data_0[3])])
                            
                            for p in range(len(self.activexdata)):
                               _ , data_x[p], _ , data_y[p] = r.getProfile(self.imageSet[p], genPlots = False)
                            
                            make_profile_plot3d(self.activexdata, data_x, data_0[0], self.activexlabel, 'X-axis', f"Profiles, c_x, c_y = {int(r.cx)}, {int(r.cy)}","Averaged over Y Axis")
                            make_profile_plot3d(self.activexdata, data_y, data_0[2], self.activexlabel, 'Y-axis', f"Profiles, c_x, c_y = {int(r.cx)}, {int(r.cy)}","Averaged over X Axis")
            if selection == "static gaussian fit to current image":
                for r in self.rm:
                    # Only count an ROI if it is active
                    if r.live:
                        roiImage = r.getRoiImage(self.imageSet[self.liveImageIndex])
                        fig, ax, popt, rms, guess_prms = translationcorr.fit_image_to_gaussian(roiImage, return_figs = True)
                        # Translate the x and y fit values back to the coordinate system of the full image
                        popt[0] += r.cx - r.w/2 
                        popt[1] += r.cy - r.h/2
                        ax.set_title(f'$x_0$ = {round(popt[0],3)}, $y_0$ = {round(popt[1],3)}')
                        make_separate_plot_window(fig, rootTitle = f"Profiles, c_x, c_y = {int(r.cx)}, {int(r.cy)}", data = roiImage)
                        varNames = ['x_0', 'y_0', 'sigma_x', 'sigma_y', 'amplitude', 'offset', 'rotAngle']
                        print('__________________')
                        for vi in range(len(varNames)):
                            print(f'{varNames[vi]} = {popt[vi]}')
            if selection == "time trace of gaussian fit":
                rmLoc = [] # Local rm array that only stores the live rois
                for r in self.rm:
                    # Only count an ROI if it is active
                    if r.live:
                        rmLoc.append(r)
                popts = np.empty([len(rmLoc),7,len(self.activexdata)])
                for ri in range(len(rmLoc)):
                    for p in range(len(self.activexdata)):
                        roiImage = rmLoc[ri].getRoiImage(self.imageSet[p])
                        popt, rms, guess_prms = translationcorr.fit_image_to_gaussian(roiImage)
                        popts[ri,:,p] = popt
                        
                fig, ax = plt.subplots(2,1)
                avg_intensity = np.mean(popts[:,4,:]*popts[:,3,:]*popts[:,2,:],axis=0)
                ax[0].plot(self.activexdata,avg_intensity)
                ax[0].set_xlabel(self.activexlabel)
                ax[0].set_ylabel('Avg Intensity')
                for ri in range(len(rmLoc)):
                    ax[1].plot(self.activexdata,popts[ri,4,:]*popts[ri,3,:]*popts[ri,2,:], label = f'{int(self.rm[ri].cx)}, {int(self.rm[ri].cy)}')
                ax[1].set_xlabel(self.activexlabel)
                ax[1].set_ylabel('Intensity')
                ax[1].legend()
                
                dataToSave = np.array([self.dsPositions,avg_intensity]).transpose()
                make_separate_plot_window(fig, 'Intensity Plot', data = dataToSave, dataHeader = 'dsPos (mm), intensity')
                
                fig, ax = plt.subplots(2,1)
                avg_area = np.mean(popts[:,3,:]*popts[:,2,:],axis=0)
                ax[0].plot(self.activexdata,avg_area)
                ax[0].set_xlabel(self.activexlabel)
                ax[0].set_ylabel('Avg Area')
                for ri in range(len(rmLoc)):
                    ax[1].plot(self.activexdata,popts[ri,3,:]*popts[ri,2,:], label = f'{int(self.rm[ri].cx)}, {int(self.rm[ri].cy)}')
                ax[1].set_xlabel(self.activexlabel)
                ax[1].set_ylabel('Area')
                ax[1].legend()
                
                dataToSave = np.array([self.dsPositions,avg_area]).transpose()
                make_separate_plot_window(fig, 'Area Plot', data = dataToSave, dataHeader = 'dsPos (mm), area')
                
                fig, axs = plt.subplots(2,2)
                avg_x = np.mean(popts[:,0,:],axis=0)
                avg_y = np.mean(popts[:,1,:],axis=0)
                axs[0,0].plot(self.activexdata,avg_x)
                axs[0,1].plot(self.activexdata,avg_y)
                axs[0,0].set_xlabel(self.activexlabel)
                axs[0,0].set_ylabel('Avg X (pixels)')
                axs[0,1].set_xlabel(self.activexlabel)
                axs[0,1].set_ylabel('Avg Y (pixels)')
                for ri in range(len(rmLoc)):
                    axs[1,0].plot(self.activexdata,popts[ri,0,:], label = f'{int(self.rm[ri].cx)}, {int(self.rm[ri].cy)}')
                    axs[1,1].plot(self.activexdata,popts[ri,1,:], label = f'{int(self.rm[ri].cx)}, {int(self.rm[ri].cy)}')
                axs[1,0].set_xlabel(self.activexlabel)
                axs[1,0].set_ylabel('X (pixels)')
                axs[1,1].set_xlabel(self.activexlabel)
                axs[1,1].set_ylabel('Y (pixels)')
                axs[1,0].legend()
                axs[1,1].legend()
                dataToSave = np.array([self.dsPositions,avg_x,avg_y]).transpose()
                make_separate_plot_window(fig, 'XY Plot', data = dataToSave, dataHeader = 'dsPos (mm), xpos, ypos')
                    
        self.measureButton = tk.Button(
            master=self.controls,
            text="Measure",
            width=buttonWidth,
            height=1,
            fg='black', bg='white',
            command=measureButtonFunc)
        
        
        self.varDifferenceImage = tk.IntVar()
        # When the convert to time check box state is changed, update the data plot xdata and replot the data plot
        def differenceImageBoxFunc():            
            if self.varDifferenceImage.get() == 1:
                self.tZeroPosEntry.config(state='disabled') # Disable the time zero entry while the difference image is active
                tz_index = utils.find_nearest(self.timeZeroPos,self.dsPositions)
                self.btzImage = np.mean(self.imageSet[tz_index:],axis=0)
                for pi in range(len(self.dsPositions)):
                    self.imageSet[pi] -= self.btzImage
            else:
                self.tZeroPosEntry.config(state='normal') # enable the time zero entry
                for pi in range(len(self.dsPositions)):
                    self.imageSet[pi] += self.btzImage
                    
            # Update the minimum and maximum values of the slider
            new_min, new_max = np.min(self.imageSet), np.max(self.imageSet)
            self.slider_vmax.set_val(np.max(self.imageSet[self.liveImageIndex]))
            self.slider_vmin.set_val(np.min(self.imageSet[self.liveImageIndex]))
            sliders = [self.slider_vmin, self.slider_vmax]
            for s in sliders:
                s.valmin = new_min
                s.valmax = new_max
                s.ax.set_xlim(s.valmin,s.valmax)
                
                
            # Draw the changes
            self.imageObj.set_data(self.imageSet[self.liveImageIndex])
            self.getTrace()
            self.canvas.draw()
                
        self.differenceImageBox = tk.Checkbutton(master=self.controls, text='Convert to Difference Images',variable=self.varDifferenceImage, onvalue=1, offvalue=0, command = differenceImageBoxFunc ,bg=cntrlBg)
        
        self.cmapSelection = tk.StringVar(self.controls)
        self.cmapSelection.set("viridis") # default value
        def cmapSelectionFunc(choice):
            self.imageObj.set_cmap(choice)
            self.canvas.draw() # redraw the canvas to reflect this choice
            
        self.cmapSelectionMenu = tk.OptionMenu(self.controls, self.cmapSelection, 'viridis', 'plasma', 'inferno', 'magma', 'cividis', "bwr", "jet", "gray", command = cmapSelectionFunc)
        
        
        self.cursorPosLabelVar = tk.StringVar()
        self.cursorPosLabelVar.set('Coordinates: (-,-)')
        self.cursorPosLabel = tk.Label(master=self.controls,textvar=self.cursorPosLabelVar,bg=cntrlBg)
        
        self.cursorPixelValLabelVar = tk.StringVar()
        self.cursorPixelValLabelVar.set('Pixel val: 0.000 (no bg subtract)')
        self.cursorPixelValLabel = tk.Label(master=self.controls,textvar=self.cursorPixelValLabelVar,bg=cntrlBg)
        
        self.bgSubtractValue = 0
        self.bgSubtract_label_string = tk.StringVar()
        self.bgSubtract_label_string.set(f'bg subtract value = {self.bgSubtractValue}')
        bgSubtractValue_label = tk.Label(master=self.controls,textvar=self.bgSubtract_label_string, bg=cntrlBg)
        self.bgSubtractValueEntry = tk.Entry(master=self.controls, width = entryWidth)
        
        def getBgValueButtonFunc():
            self.bgSubtractValue = 0
            self.getTrace() # update the self.dataSignal array
            self.bgSubtractValue = round(np.mean(self.dataSignal),2) # acquire the mean value of the data signal for the bg subtract value
            self.bgSubtract_label_string.set(f'bg subtract value = {self.bgSubtractValue}')
            self.bgSubtractValueEntry.delete(0, tk.END)
            self.bgSubtractValueEntry.insert(-1,self.bgSubtractValue)
            self.getTrace() # Update the trace with this bg subtract value

        self.getBgValueButton = tk.Button(
            master=self.controls,
            text="Get bg Value",
            width=buttonWidth,
            height=1,
            fg='black', bg='white',
            command=getBgValueButtonFunc)
    

        def savePixelSumPlotButtonFunc():
            file_path = fd.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
            np.savetxt(file_path,np.array([self.dsPositions,self.dataSignal]).transpose(),delimiter=',',header='dsPos (mm), pixelSum')
            
        self.savePixelSumPlotButton = tk.Button(
            master=self.controls,
            text="Save Pixel Sum Data",
            width=buttonWidth,
            height=1,
            fg='black', bg='white',
            command=savePixelSumPlotButtonFunc)
    
        
        # setup the enter key to update entries
        def userPressReturn(event):
            entry = self.root.focus_get() # Get the entry that the user has selected
            if entry == self.tZeroPosEntry:
                self.timeZeroPos = float(self.tZeroPosEntry.get())
                self.tZeroPos_label_string.set(f'Time Zero Pos = {self.timeZeroPos} mm')
                convertToTimeFunc() # Recompute the x-axis of the data plots based on this time zero position
                self.updateImageTitle() # Update the image title based on this time zero position
                self.canvas.draw() # redraw the canvas so this change is updated on the gui
            if entry == self.bgSubtractValueEntry:
                if self.bgSubtractValueEntry.get() == '':
                    self.bgSubtractValueEntry.insert(-1,0)
                self.bgSubtractValue = float(self.bgSubtractValueEntry.get())
                self.bgSubtract_label_string.set(f'bg subtract value = {self.bgSubtractValue}')
                self.getTrace() # Update the trace with this bg subtract value
            if entry == self.roiFromMillerIndicesEntry:
                self.setRoiFromMiller()
            if entry == self.calibrationMillerIndicesEntry:
                calibrateBravaisLatticeButtonFunc() # execute the bravais lattice calibration same as the button on enter
                
                
                
        # Bind the enter key to activate selected entry
        self.root.bind('<Return>', userPressReturn)
        
        # Pack the ROI controls
        self.cursorPixelValLabel.pack(pady = padyControls, anchor='nw')
        self.cursorPosLabel.pack(pady = padyControls, anchor='nw')
        tk.Frame(master=self.controls, bd=100, relief='flat',height=sepHeight,width=sepWidth,bg='black').pack(side='top', pady=padySep)
        self.differenceImageBox.pack(pady = padyControls, anchor='nw')
        self.cmapSelectionMenu.pack(pady = padyControls, anchor='nw')
        tk.Frame(master=self.controls, bd=100, relief='flat',height=sepHeight,width=sepWidth,bg='black').pack(side='top', pady=padySep)
        self.roiSelectionMenu.pack(pady = padyControls, anchor='nw')
        tk.Label(master=self.controls,text='Calibrate Miller Indices e.g. "(0,1)(1,0)(0,2)"',bg=cntrlBg).pack(pady=padyControls, anchor='nw')
        self.calibrationMillerIndicesEntry.pack(pady = padyControls, anchor='nw')
        self.calibrateBravaisLatticeButton.pack(pady = padyControls, anchor='nw')
        tk.Label(master=self.controls,text='ROIs from miller indices "(m,n)..."',bg=cntrlBg).pack(pady=padyControls, anchor='nw')
        self.roiFromMillerIndicesEntry.pack(pady=padyControls, anchor='nw')
        tk.Label(master=self.controls,text='roi sizes "50,30,..."',bg=cntrlBg).pack(pady=padyControls, anchor='nw')
        self.roiFromMillerIndicesSizeEntry.pack(pady=padyControls, anchor='nw')
        tk.Frame(master=self.controls, bd=100, relief='flat',height=sepHeight,width=sepWidth,bg='black').pack(side='top', pady=padySep)
        tZeroPos_label.pack(pady = padyControls, anchor='nw')
        self.tZeroPosEntry.pack(pady = padyControls, anchor='nw')
        self.convertToTimeBox.pack(pady = padyControls, anchor='nw')
        tk.Frame(master=self.controls, bd=100, relief='flat',height=sepHeight,width=sepWidth,bg='black').pack(side='top', pady=padySep)
        bgSubtractValue_label.pack(pady = padyControls, anchor='nw')
        self.bgSubtractValueEntry.pack(pady = padyControls, anchor='nw')
        self.getBgValueButton.pack(pady = padyControls, anchor='nw')
        tk.Frame(master=self.controls, bd=100, relief='flat',height=sepHeight,width=sepWidth,bg='black').pack(side='top', pady=padySep)
        tk.Label(master=self.controls,text='Measurements',bg=cntrlBg).pack(pady=padyControls, anchor='nw')
        self.measureSelectionMenu.pack(pady = padyControls, anchor='nw')
        self.measureButton.pack(pady = padyControls, anchor='nw')
        tk.Frame(master=self.controls, bd=100, relief='flat',height=sepHeight,width=sepWidth,bg='black').pack(side='top', pady=padySep)
        self.savePixelSumPlotButton.pack(pady = padyControls, anchor='nw')
        
        # Get the initial image set
        # ~ x, y = np.linspace(-5,3,500), np.linspace(-3,3,333)
        # ~ X, Y = np.meshgrid(x,y)
        # ~ a, b = 0.1*np.random.random(2)
        
        # ~ image_0 = 5000*np.exp(-((X-a)**2/4+(Y-b)**2)/.025)
        # ~ self.h, self.w = np.shape(image_0)
        
        image_0 = tifffile.imread('pos67.25000000000000.tiff')
        self.h, self.w = np.shape(image_0)
        
        self.dsPositions = np.round(np.arange(65,75,1),4)
        self.activexdata = self.dsPositions
        self.activexlabel = 'dsPos (mm)'
        self.image_N = len(self.dsPositions)
        self.imageSet = np.zeros([self.image_N,self.h,self.w])
        self.liveImageIndex = 0
        
        for i in range(self.image_N):
            self.imageSet[i] = (1+i/self.image_N)*image_0 + 200*np.random.random(np.shape(image_0))
        
        # Create the data frame figures and axes
        self.dataFig, self.dataAx = plt.subplots(1,1,figsize=(5, 7))
        # Set the initial x-axis label as dsPos (mm), this should change when the user selects time as the x-plot instead
        self.dataAx.set_xlabel(self.activexlabel)
        
        self.dataSignal = np.zeros(len(self.dsPositions))
        self.dataPlot, = self.dataAx.plot(self.dsPositions,self.dataSignal)
        
        # Format the figure and the axes for the image figure
        self.imageFig, self.imageAx = plt.subplots(figsize=(8, 7))
        self.imageAx.xaxis.set_tick_params(labelbottom=False)
        self.imageAx.yaxis.set_tick_params(labelleft=False)
        self.imageAx.set_xticks([])
        self.imageAx.set_yticks([])
        self.imageObj = self.imageAx.imshow(self.imageSet[self.liveImageIndex])
        
        self.updateImageTitle()
        
        cur_xlim = self.imageAx.get_xlim()
        cur_ylim = self.imageAx.get_ylim()
        
        print('cur_xlim',cur_xlim)
        print('cur_ylim',cur_ylim)
        
        # Attach the matplotlib data figures to a tkinter gui window
        self.datacanvas = FigureCanvasTkAgg(self.dataFig, master=self.dataFrame)
        self.datatoolbar = NavigationToolbar2Tk(self.datacanvas, self.dataFrame)
        self.datatoolbar.update()
        self.datacanvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        self.datalabel = tk.Label(text="")
        self.datalabel.pack()
        
        # Connect the image figure to key press events
        self.imageFig.canvas.mpl_connect('button_press_event', self.camonclick)
        self.imageFig.canvas.mpl_connect('button_release_event', self.camonrelease)
        self.imageFig.canvas.mpl_connect('scroll_event', self.camonscroll)
        self.imageFig.canvas.mpl_connect('motion_notify_event', self.camonmove)
        
        # Build sliders for adjusting the brightness and contrast of the image
        ax_setVals = [plt.axes([0.15, 0.10, 0.5, 0.02]), plt.axes([0.15, 0.06, 0.5, 0.02]), plt.axes([0.15, 0.02, 0.5, 0.02])]
        imageMin, imageMax = np.min(self.imageSet), np.max(self.imageSet)
        self.slider_vmax = matplotlib.widgets.Slider(ax_setVals[0], r'$v_{max}$', imageMin, imageMax, valinit=np.max(self.imageSet[0]))
        self.slider_vmin = matplotlib.widgets.Slider(ax_setVals[1], r'$v_{min}$', imageMin, imageMax, valinit=np.min(self.imageSet[0]))
        self.slider_imageN = matplotlib.widgets.Slider(ax_setVals[2], r'Image #', 0, self.image_N-1, valinit=0, valstep=1)
        def sliderUpdateVmax(val):
            if val > self.imageObj.get_clim()[0]:
                self.imageObj.set_clim(self.imageObj.get_clim()[0], val)
            else:
                self.slider_vmax.set_val(self.imageObj.get_clim()[0]+1)
        def sliderUpdateVmin(val):
            if val < self.imageObj.get_clim()[1]:
                self.imageObj.set_clim(val, self.imageObj.get_clim()[1])
            else:
                self.slider_vmin.set_val(self.imageObj.get_clim()[1]-1)
        def sliderUpdateimageN(val):
            self.liveImageIndex = val
            self.imageObj.set_data(self.imageSet[self.liveImageIndex])
            self.updateImageTitle()
            
        self.slider_vmax.on_changed(sliderUpdateVmax)
        self.slider_vmin.on_changed(sliderUpdateVmin)
        self.slider_imageN.on_changed(sliderUpdateimageN)
        
        # Attach the matplotlib image figures to a tkinter gui window
        self.canvas = FigureCanvasTkAgg(self.imageFig, master=self.imageFrame)
        self.canvas._tkcanvas.pack(side=tk.RIGHT, fill=tk.BOTH, expand=1)
        self.label = tk.Label(text="")
        self.label.pack()
        
        def on_closing():
            if tk.messagebox.askokcancel("Quit", "Do you want to quit?"):
                self.root.quit()

        self.root.protocol("WM_DELETE_WINDOW", on_closing)
        self.root.mainloop()
    
    def updateImageTitle(self):
        dsPosString = '%.3f' % self.dsPositions[self.liveImageIndex]
        dsTimeString = '%.3f' % (6.67*(self.timeZeroPos - self.dsPositions[self.liveImageIndex]))
        self.imageAx.set_title(f'dsPos = {dsPosString} mm, $(t-t_0)$ = {dsTimeString} ps')
    
    def camonclick(self,event):
        ax = self.imageAx
        # Find the location of the mouse click and update the crosshair variable to this value
        selection = self.roiSelection.get()
        if event.inaxes == ax:
            if event.button == 1:
                if self.roiActive:
                    self.roiActive = False
                    self.rm[-1].goLive() # Set the roi that was just placed to live status
                else:
                    # Check whether we are clicking on an roi window
                    for i in range(len(self.rm)):
                        if self.rm[i].checkClicked(event.xdata,event.ydata):
                            self.relocatingRoi = self.rm[i]
                            self.relocatePin_x, self.relocatePin_y = event.xdata - self.relocatingRoi.cx, event.ydata - self.relocatingRoi.cy
                            self.relocatingRoi.goDead()
                            break # exit the loop on the 1st occurance of a valid roi
                    # If we aren't relocating a current roi, then make a new roi
                    if self.relocatingRoi == None:
                        self.roiActive = True
                        self.rm.append(RoiRectangle(event.xdata,event.ydata,0,0,ax))

            if event.button == 2:
                cur_xlim = ax.get_xlim()
                cur_ylim = ax.get_ylim()
                # compute new limits
                xlims = [event.xdata-(cur_xlim[1]-cur_xlim[0])/2, event.xdata+(cur_xlim[1]-cur_xlim[0])/2]
                ylims = [event.ydata-(cur_ylim[1]-cur_ylim[0])/2, event.ydata+(cur_ylim[1]-cur_ylim[0])/2]
                # make sure the limits don't fall outside the image size
                if xlims[0] < 0:
                    xlims[1] += -xlims[0]
                    xlims[0] += -xlims[0]
                if xlims[1] > self.w:
                    xlims[0] += self.w-xlims[1]
                    xlims[1] += self.w-xlims[1]
                if ylims[1] < 0:
                    ylims[0] += -ylims[1]
                    ylims[1] += -ylims[1]
                if ylims[0] > self.h:
                    ylims[1] += self.h-ylims[0]
                    ylims[0] += self.h-ylims[0]
                # set the new limits
                ax.set_xlim(*xlims)
                ax.set_ylim(*ylims)
                
                print('xlims',xlims)
                print('ylims',ylims)
                
            if event.button == 3:
                for i in range(len(self.rm)):
                    if self.rm[i].checkClicked(event.xdata,event.ydata):
                        if self.rm[i].live:
                            self.rm[i].goDead()
                        else:
                            self.rm[i].goLive()
                        
                        if event.key == 'control':
                            self.rm[i].destroy()
                            self.rm.pop(i) # Pop this item from the rm list
                            
                        break # Exits the loop on the first occurance of an ROI

            self.getTrace() # Draw the new time trace with this ROI
            self.canvas.draw()
    
    def camonrelease(self,event):
        if event.button == 1:
            if self.relocatingRoi != None:
                self.relocatingRoi.goLive()
                self.relocatingRoi = None
                self.getTrace() # Draw the new time trace with this ROI
                self.canvas.draw() # Draw the new roi color to show that it is live
    
    def camonscroll(self, event, base_scale = 1.15):
        # ~ print(event.button)
        ax = self.imageAx
        # get the current x and y limits
        if event.inaxes == ax:
            cur_xlim = list(ax.get_xlim())
            cur_ylim = list(ax.get_ylim())
            xdata = event.xdata # get event x location
            ydata = event.ydata # get event y location
            if event.button == 'up':
                # deal with zoom in
                scale_factor = base_scale
            elif event.button == 'down':
                # deal with zoom out
                scale_factor = 1/base_scale
            # compute new limits
            xlims = [xdata - (xdata-cur_xlim[0]) / scale_factor, xdata + (cur_xlim[1]-xdata) / scale_factor]
            ylims = [ydata - (ydata-cur_ylim[0]) / scale_factor, ydata + (cur_ylim[1]-ydata) / scale_factor]
            # make sure the limits aren't too big
            if (xlims[1]-xlims[0] > self.w) or (ylims[0]-ylims[1] > self.h):
                xlims = [0, self.w]
                ylims = [self.h, 0]

            # make sure the limits don't fall outside the image size
            if xlims[0] < 0:
                xlims[0] += -xlims[0]
                xlims[1] += -xlims[0]
                
            if xlims[1] > self.w:
                xlims[0] += self.w-xlims[1]
                xlims[1] += self.w-xlims[1]
            
            if ylims[1] < 0:
                ylims[1] += -ylims[1]
                ylims[0] += -ylims[1]
                
            if ylims[0] > self.h:
                ylims[0] += self.h-ylims[0]
                ylims[1] += self.h-ylims[0]
                
                
            print('xlims',xlims)
            print('ylims',ylims)
            
            # set the new limits
            ax.set_xlim(*xlims)
            ax.set_ylim(*ylims)
            
            self.canvas.draw()

    def camonmove(self, event):
        ax = self.imageAx
        if event.inaxes == ax:
            if 0 < event.ydata < self.h and 0 < event.xdata < self.w:
                pixelValString = '%.3f' % self.imageSet[self.liveImageIndex,int(event.ydata),int(event.xdata)]
                self.cursorPixelValLabelVar.set(f'Pixel val: {pixelValString} (no bg subtract)')
                self.cursorPosLabelVar.set(f'Coordinates: ({int(event.xdata)},{int(event.ydata)})')
                if self.roiActive:
                    self.rm[-1].updateShape(abs(event.xdata - self.rm[-1].cx)*2,abs(event.ydata - self.rm[-1].cy)*2) # width, height
                    self.canvas.draw()
                if self.relocatingRoi != None:
                    self.relocatingRoi.updatePosition(event.xdata - self.relocatePin_x, event.ydata - self.relocatePin_y)
                    self.canvas.draw()
                
    def clearRois(self):
        # Clear all existing ROIS
        for i in range(len(self.rm)):
            self.rm[i].patch.remove() # Remove the patch from the plot
            del self.rm[i].patch # Delete the patch
        self.rm = [] # make rm an empty list
        
        # redraw the canvas to reflect this change to the gui
        self.canvas.draw()
    
    def getTrace(self):
        if len(self.rm) > 0:
            # Loop through all the delay stage positions
            for p in range(len(self.dsPositions)):
                roiPixelSum = 0
                roiTotalArea = 0
                # Loop through all the ROIS
                for r in self.rm:
                    # Only count an ROI if it is active
                    if r.live:
                        roiImage = r.getRoiImage(self.imageSet[p])
                        roiTotalArea += roiImage.shape[0]*roiImage.shape[1]
                        roiPixelSum += np.sum(roiImage)
                
                if roiTotalArea > 0:        
                    self.dataSignal[p] = (roiPixelSum)/roiTotalArea - self.bgSubtractValue
                    
            
            if roiTotalArea > 0:
                self.dataPlot.set_ydata(self.dataSignal)
                self.dataAx.set_ylim([min(self.dataSignal)-0.1,max(self.dataSignal)+0.1])
                self.dataAx.set_title(f'Average ROI pixel value, bg subtract = {self.bgSubtractValue}')
                
        else:
            self.dataSignal = 0*self.dataSignal
        self.datacanvas.draw()
    
    def setRoiFromMiller(self):
        vals = calibratebravais.parse_cmis(self.roiFromMillerIndicesEntry.get())
        self.roiFromMillerIndicesEntry.delete(0,tk.END) # Clear this entry after the ROI has been created
        for vi in range(len(vals[:,0])):
            vec = self.aReciprocal*vals[vi,0] + self.bReciprocal*vals[vi,1] + self.gammaReciprocal
            # Create an ROI at this vector position
            sizes = calibratebravais.parse_cmis(self.roiFromMillerIndicesSizeEntry.get())[0] # We only take the 1st tuple here
            if len(sizes) == 1:
                w, h = sizes[0], sizes[0]
            else:
                w, h = sizes[0], sizes[1]
            
            self.rm.append(RoiRectangle(vec[0],vec[1],w,h,self.imageAx))
            self.rm[-1].goLive() # Set the roi that was just placed to live status
            
        self.getTrace() # Draw the new time trace with this ROI
        self.canvas.draw()
        
if __name__ == '__main__':
    guiObj = timeTraceGUI()

