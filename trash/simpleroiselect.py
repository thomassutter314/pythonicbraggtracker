import tifffile
import tkinter as tk

class RoiRectangle():
    def __init__(self,cx,cy,w,h,ax):
        self.cx = cx
        self.cy = cy
        self.w = w
        self.h = h
        self.patch = patches.Rectangle((self.cx, self.cy), self.w, self.h, linewidth=1, edgecolor='r', facecolor='none', alpha=0.8)
        self.live = False
        
        self.cRadius = 1
        # ~ self.cpatch = patches.Circle((self.cx,self.cy),self.cRadius, edgecolor=(1, 0, 0, 0.5), facecolor=(1, 0, 0, 1),fill=False)
        
        ax.add_patch(self.patch) # Add the patch to the axis
        # ~ ax.add_patch(self.cpatch) # Add the center patch to the axis
    
    def updateShape(self, w, h,):
        self.w = w
        self.h = h
        tl_x = self.cx - w/2
        tl_y = self.cy - h/2
        self.patch.set_xy((tl_x,tl_y)) # Update patch top left corner
        self.patch.set_width(w) # Update the patch with new width
        self.patch.set_height(h) # Update the patch with new height
    
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
        self.live = True
 
# incomplete function, might remove
class simpleRoiGui_rect():
    def __init__(self, image, wait = .033):
        self.image = image
        
        # Setup the tkinter GUI window
        self.root = tk.Tk()
        self.root.geometry("1000x700")
        self.root.configure(bg='white')
        self.root.wm_title("Q Scan")
        self.wait = int(wait*1000)
        
        # ROI stuff
        self.roiActive = False
        self.rm = [] # list of rois
        
        # Connect to the camera, collect the initial image and plot the image
        # SCAF
        self.camImage = tifffile.imread(self.dir_path + '//' + sorted_files[0]) # Loads the first image in the set
        self.h, self.w = self.camImage.shape
        self.camFig, self.camAx = plt.subplots()
        self.camImageObj = self.camAx.imshow(self.camImage)
        self.camAx.set_title('Select 2 ROIs')
    
        self.camAx.xaxis.set_tick_params(labelbottom=False)
        self.camAx.yaxis.set_tick_params(labelleft=False)
        self.camAx.set_xticks([])
        self.camAx.set_yticks([])
        
        # Make a Tkinter frame for the ROI selection buttons
        self.controls = tk.Frame(master=self.root, width=100, height=100, padx=5, pady=5)
        self.controls.pack(side=tk.RIGHT)

        self.trackButton = tk.Button(
            master=self.controls,
            text="Track",
            width=18,
            height=3,
            fg='black', bg='green',
            command=self.starttrack)

        # Pack controls
        self.trackButton.pack()
        
        # Build sliders for adjusting the brightness and contrast of the image
        ax_setVals = [plt.axes([0.15, 0.06, 0.5, 0.02]), plt.axes([0.15, 0.02, 0.5, 0.02])]
        imageMin, imageMax = np.min(self.camImage), np.max(self.camImage)
        slider_vmax = matplotlib.widgets.Slider(ax_setVals[0], r'$v_{max}$', imageMin, imageMax, valinit=imageMax)
        slider_vmin = matplotlib.widgets.Slider(ax_setVals[1], r'$v_{min}$', imageMin, imageMax, valinit=imageMin)
        def sliderUpdateVmax(val):
            if val > self.camImageObj.get_clim()[0]:
                self.camImageObj.set_clim(self.camImageObj.get_clim()[0], val)
            else:
                slider_vmax.set_val(self.camImageObj.get_clim()[0]+1)
        def sliderUpdateVmin(val):
            if val < self.camImageObj.get_clim()[1]:
                self.camImageObj.set_clim(val, self.camImageObj.get_clim()[1])
            else:
                slider_vmin.set_val(self.camImageObj.get_clim()[1]-1)
        slider_vmax.on_changed(sliderUpdateVmax)
        slider_vmin.on_changed(sliderUpdateVmin)
        
        pos0 = self.camAx.get_position()

        # Connect the cam figure to key press events
        self.camFig.canvas.mpl_connect('button_press_event', self.camonclick)
        self.camFig.canvas.mpl_connect('scroll_event', self.camonscroll)
        self.camFig.canvas.mpl_connect('motion_notify_event', self.camonmove)

        # Attach the matplotlib image figures to a tkinter gui window
        self.canvas = FigureCanvasTkAgg(self.camFig, master=self.root)
        self.canvas._tkcanvas.pack(side=tk.RIGHT, fill=tk.BOTH, expand=1)
        self.label = tk.Label(text="")
        self.label.pack()
                
        def on_closing():
            # ~ if tk.messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.camLive = False
            self.root.quit()
            

        self.update()
        self.root.protocol("WM_DELETE_WINDOW", on_closing)
        self.root.mainloop()
    
    def camonclick(self,event):
        ax = self.camAx
        # Find the location of the mouse click and update the crosshair variable to this value
        if event.inaxes == ax:
            if event.button == 1:
                if self.roiActive:
                    self.roiActive = False
                    self.rm[-1].goLive() # Set the roi that was just placed to live status
                else:
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
            if event.button == 3:
                for i in range(len(self.rm)):
                    if abs(event.xdata-self.rm[i].cx) < self.rm[i].w/2 and abs(event.ydata-self.rm[i].cy) < self.rm[i].h/2:
                        self.rm[i].patch.remove() # Remove the patch from the plot
                        del self.rm[i].patch # Delete the patch
                        self.rm.pop(i) # Pop this item from the rm list
                        break # Exits the loop on the first occurance of a ROI to remove.
                
    def camonscroll(self, event, base_scale = 1.15):
        # ~ print(event.button)
        ax = self.camAx
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
                xlims = cur_xlim
                ylims = cur_ylim
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
    
    def camonmove(self, event):
        ax = self.camAx
        if event.inaxes == ax:
            if self.roiActive:
                self.rm[-1].updateShape(abs(event.xdata - self.rm[-1].cx)*2,abs(event.ydata - self.rm[-1].cy)*2) # width, height
            
    def update(self):
        self.canvas.draw()
        self.root.after(self.wait, self.update)
      
