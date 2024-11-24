import matplotlib.patches as patches
import numpy as np

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
      
