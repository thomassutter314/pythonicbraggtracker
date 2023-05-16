import simpleroiselect
import numpy as np
import tkinter as tk
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTk, NavigationToolbar2Tk
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg,
    NavigationToolbar2Tk)

import translationcorr

def measureLattice(sampleImage, roiImages, cxs, cys, cmis, exponent = 4, latticePlotOrder=16):
    print("Measuring Lattice \nSelect three non-collinear Bragg peaks")
    Qs = np.zeros([3,2]) # Coordinates of the three user selected Bragg peaks
    qs = np.zeros([2,2]) # 2 lattice vectors computed from these 3 peaks
    
    MI = np.zeros([3,2]) # miller indices of selected bragg peaks
    
    # cmis is calibration miller indices string of the form (0,1)(1,0)(0,2)
    MI = parse_cmis(cmis)
    
    print(MI)
    
    mi = np.zeros([2,2]) # miller indices of bragg vectors

    for i in range(len(roiImages)):
        popt, rms, guess_prms = translationcorr.fitImageToGaussian(roiImages[i])
        h, w = np.shape(roiImages[i])
        tl_x, tl_y = cxs[i] - w/2, cys[i] - h/2
        Qs[i,:] = popt[0] + tl_x, popt[1] + tl_y # Set the Qs array to the x, y coordinates of the fit
        
    qs[0,:] = Qs[1,:] - Qs[0,:]
    qs[1,:] = Qs[2,:] - Qs[0,:]
    
    mi[0,:] = MI[1,:] - MI[0,:]
    mi[1,:] = MI[2,:] - MI[0,:]
    
    print('mi',mi)
    print('Qs',Qs)
    
    a = (mi[1,1]*qs[0,:] - mi[0,1]*qs[1,:])/(mi[1,1]*mi[0,0]-mi[0,1]*mi[1,0])
    b = (mi[0,0]*qs[1,:] - mi[1,0]*qs[0,:])/(mi[1,1]*mi[0,0]-mi[0,1]*mi[1,0])
    gamma = Qs[2,:] - (MI[2,0]*a + MI[2,1]*b)
    
    print(f'gamma = {gamma}')
    print(f'a = {np.sqrt(a[0]**2+a[1]**2)}')
    print(f'b = {np.sqrt(b[0]**2+b[1]**2)}')
    print(f'theta = {180/np.pi*np.arccos((a[0]*b[0]+a[1]*b[1])/(np.sqrt(a[0]**2+a[1]**2)*np.sqrt(b[0]**2+b[1]**2)))} deg')
    print(f'phi = {180/np.pi*np.arccos(a[0]/(np.sqrt(a[0]**2+a[1]**2)))} deg')
    
    return gamma, a, b
    

    
    fig, ax = plt.subplots()
    ax.set_xticks([])
    ax.set_yticks([])
    axcolor = 'white'
    ax.imshow(image, cmap='viridis',vmin=vm[0],vmax=vm[1]) # Give the ROI manager the plot
    for i in range(latticePlotOrder):
        for j in range(latticePlotOrder):
            I = i-latticePlotOrder//2
            J = j-latticePlotOrder//2
            ax.arrow(gamma[0]+I*a[0]+J*b[0],gamma[1]+I*a[1]+J*b[1],a[0],a[1],alpha=0.3)
            ax.arrow(gamma[0]+I*a[0]+J*b[0],gamma[1]+I*a[1]+J*b[1],b[0],b[1],alpha=0.3)
    ax.scatter(gamma[0],gamma[1],color='red')
    ax.text(gamma[0],gamma[1],'$\Gamma$')
    
    h,w = np.shape(image)
    ax.set_xlim([0,w])
    ax.set_ylim([0,h])
    
    print(f'gamma = {gamma}')
    print(f'a = {np.sqrt(a[0]**2+a[1]**2)}')
    print(f'b = {np.sqrt(b[0]**2+b[1]**2)}')
    print(f'theta = {180/np.pi*np.arccos((a[0]*b[0]+a[1]*b[1])/(np.sqrt(a[0]**2+a[1]**2)*np.sqrt(b[0]**2+b[1]**2)))} deg')
    print(f'phi = {180/np.pi*np.arccos(a[0]/(np.sqrt(a[0]**2+a[1]**2)))} deg')
    
    ax.set_title(f'a = {round(np.sqrt(a[0]**2+a[1]**2),2)}, b = {round(np.sqrt(b[0]**2+b[1]**2),2)}, theta = {round(180/np.pi*np.arccos((a[0]*b[0]+a[1]*b[1])/(np.sqrt(a[0]**2+a[1]**2)*np.sqrt(b[0]**2+b[1]**2))),2)} deg')
    
    plt.show()
    

def parse_cmis(s):
    MI = np.zeros([3,2]) # miller indices of selected bragg peaks
    for i in range(3):
        i1 = 1 + s.find('(')
        i2 = s[i1:].find(')')
        #print(s)
        #print(s[i1:i1+i2].split(','))
        
        MI[i,:] = list(map(float,s[i1:i1+i2].split(',')))
        
        s = s[i1+i2+1:]
        #print(s)
    return MI
        


parse_cmis('(0,1)(1,0)(0,2)')
