#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 23 12:17:12 2021

@author: Jonas
"""
import matplotlib.pyplot as plt
import numpy as np
import pickle
import matplotlib.animation as animation
import matplotlib
matplotlib.rcParams['animation.embed_limit'] = 2**128
import matplotlib.animation as animation
import matplotlib.cm as cm
import os
import src.wall_sim as sim



class analyze_wall():
    def __init__(self,p):
        self.p=p
        pkl = p['outputpath'] +p['datapath']+p['filename']
        path = os.getcwd()+'/' + pkl
        self.data=self.load(path)
        try:
            pkl = p['outputpath'] +p['defectpath']+p['filename']
            path = os.getcwd()+'/' + pkl
            self.defectdata=self.load(path)
        except FileNotFoundError:
            pass

        
        
    def listdir_nohidden(self,path):
        for f in os.listdir(path):
            if not f.startswith('.'):
                yield f
    def load(self,filename):
        with open(filename, 'rb') as output:
            return pickle.load(output)

    def compute_quantities(self):
        w=sim.wall()
        w.parameters(params=self.p)
        w.geo()
        
        self.hexlist=self.data['hexagon index']
        self.trihexlist=self.data['trihexagon index']
        self.pos = np.asarray(self.data['pos'])
        def compute_theta(pos,N=6):
            teq=np.pi*4/6
            r=np.roll(pos,1,axis=1)-pos
            th=np.angle(-r/np.roll(r,1,axis=1))%(2*np.pi)
            ang_data=th-teq
            r_av=np.average(np.abs(r))

            S1 = (ang_data[:,0]-ang_data[:,2])/np.sqrt(2)
            S2 = (ang_data[:,0]+ang_data[:,2]-2*ang_data[:,4])/np.sqrt(5)
            B = (ang_data[:,0]+ang_data[:,2]+ang_data[:,4])/np.sqrt(3)
            return S1,S2,B
       
        shearlist = np.zeros((np.shape(self.hexlist)[0],np.shape(self.pos)[0]),dtype=complex)
        bulklist = np.zeros((len(self.hexlist),np.shape(self.pos)[0]))

        for i,x in enumerate(self.hexlist):
            S1,S2,B = compute_theta(self.pos[:,x])
            shear=S1+1j*S2
            shearlist[i,:] = shear
            bulklist[i,:]=B

        bulklist = np.asarray(bulklist)
        shearlist = np.asarray(shearlist)
        frames = np.shape(shearlist)[1]
        # phase = np.angle(shearlist)%np.pi
        mag = np.abs(shearlist)
        S1 = np.real(shearlist)
        S2 = np.imag(shearlist)
        self.phi = S1+1j*S2
        theta = np.angle(S1+1j*np.abs(S2))
        self.phase = np.angle(S1 - np.sqrt(S1**2 + S2**2) +1j*S2)%np.pi
        self.magnitude = np.real(( (S1+1j*S2)* (S1-1j*S2) )**0.5)
        
        self.time = np.arange(self.phi.shape[1])*self.p['pt']
        self.c_angle=self.phase/np.pi
        self.c_mag = self.magnitude
        hexpos = self.pos[:,self.hexlist]
        self.avgpos = np.average(hexpos,axis=2)
        self.c_angle=np.array(self.c_angle).T
        self.c_mag=np.array(self.c_mag).T

    def get_correlation(self,th):
        Nx = self.p['Nx']
        Ny = self.p['Ny']
        
        self.time = self.time
        corr = np.zeros([len(self.time),self.phi.shape[1]],dtype=float)
        R = np.zeros(self.phi.shape[1])

        for n,t in enumerate(self.time):
            print('corr ',n)
            for x in range():
                for y in range(Ny):
                    dth = th[n,:,:] - np.roll(th[n,:,:],(x,y),axis=(0,1))
                    proj = np.real(np.exp(1j*dth))
                    corr_xy = np.average(proj)
                    corr[n,x,y] = corr_xy
                    if n==0:
                        A = np.min([np.sqrt(x**2+y**2),
                                        np.sqrt((x-Nx)**2+(y-Ny)**2),
                                        np.sqrt((x-Nx)**2+y**2),
                                        np.sqrt(x**2+(y-Ny)**2)])
                        R[x,y] = A
            
            
        
        self.fielddata['correlation'] = corr
        Nt = len(self.time)
        R = np.reshape(R,Nx*Ny)
        Rinds = R.argsort()
        R = R[Rinds[::-1]]        
        corrflat = np.reshape(corr,(Nt,Nx*Ny))
        for t,c in enumerate(corrflat):
            corrflat[t] = c[Rinds[::-1]]
                
        def avg_group(vA0, vB0):
            vA, ind, counts = np.unique(vA0, return_index=True, return_counts=True) # get unique values in vA0
            vB = vB0[ind]
            for dup in vB[counts>1]: # store the average (one may change as wished) of original elements in vA0 reference by the unique elements in vB
                vB[np.where(vA==dup)] = np.average(vB0[np.where(vA0==dup)])
            return vA, vB
        
        Ct=[]
        for t in range(Nt):
            R,C = avg_group(R,corrflat[t])            
            Ct.append(C)
        
        for n,i in enumerate(corr):
            fig,ax = plt.subplots(1,4)  
            ax[0].imshow(i)
            print(th)
            ax[1].imshow(th[n],cmap='hsv')
            ax[2].scatter(range(Nx),corr[n,:,0],s=5)
            print(np.shape(Ct))
            ax[3].scatter(R,Ct[n,:],s=5)
            plt.show()

        
        self.timeseries['1Dcorr'] = Ct
        self.timeseries['R'] = R


        
    def FullRender(self,filename):
        pos = self.pos[0]
        self.odraw = []
        self.p1draw= []
        self.p2draw= []
        for m,row in enumerate(self.hexlist):
            xp,yp = [np.real(pos[row]),np.imag(pos[row])]
            self.p1draw.append(self.ax.fill(xp,yp,fill=True,zorder=1,color=self.cmap(self.c_angle[m,0]), alpha=.3, joinstyle="round")[0])
        self.order = [0,1,2,6,7,12,11,10,9,8,3,4]
        for m,row in enumerate(self.trihexlist):
            trihexidx = np.unique(self.hexlist[row].flatten())
            xp,yp = [np.real(pos[trihexidx]),np.imag(pos[trihexidx])]
            xp = xp.flatten()[self.order]
            yp = yp.flatten()[self.order]
            self.p2draw.append(self.ax.fill(xp,yp,fill=False,zorder=1, alpha=.8,lw=1.5, joinstyle="round",c='grey')[0])
    def FullUpdate(self,i):
        if i%10==0:
            print(i,end='\r')
        pos = self.pos[i]
        x = np.real(pos)
        y = np.imag(pos)
        a = np.transpose([x,y])
        # boxverts = np.transpose([np.real(self.box[i]),np.imag(self.box[i])])
        for m,row in enumerate(self.hexlist):
            xp,yp = [np.real(pos[row]),np.imag(pos[row])]
            verts=np.transpose([xp,yp])
            self.p1draw[m].set_xy(verts)
            self.p1draw[m].set_color(self.cmap(self.c_angle[m,i]))
        for m,row in enumerate(self.trihexlist):
            trihexidx = np.unique(self.hexlist[row].flatten())
            xp,yp = [np.real(pos[trihexidx]),np.imag(pos[trihexidx])]
            xp = xp.flatten()[self.order]
            yp = yp.flatten()[self.order]
            verts=np.transpose([xp,yp])
            self.p2draw[m].set_xy(verts)
    def ScatterUpdate(self,i):
        if i%10==0:
            print(i,end='\r')
        pos = np.array([np.real(self.avgpos[i]),np.imag(self.avgpos[i])]).T
        
        for s in self.scats:
            s.set_offsets(pos)
        
        self.scats[0].set_array(self.magnitude.T[i])
        self.scats[1].set_array(self.c_angle[i])
        
        vmax = 4*np.mean(self.magnitude.T[i])
        vmin = 0
        self.scats[0].set_clim(vmin, vmax)

        try:
            xy = np.array([np.real(self.xy[i]),np.imag(self.xy[i])]).T
            self.defect.set_offsets(xy)         
            self.defect.set_array(self.charge[i])
        except AttributeError:
            pass
        
    def ScatterAnimate(self,filename):
        
        # print(np.shape(self.c_angle))
        self.scats=[]
        self.scats.append(self.ax.scatter(np.real(self.avgpos[0]),np.imag(self.avgpos[0]),c=self.magnitude.T[0],cmap=cm.viridis,vmin=0,vmax=1,marker = 'H',s=self.s**2))
        self.scats.append(self.bx.scatter(np.real(self.avgpos[0]),np.imag(self.avgpos[0]),c=self.c_angle[0],cmap=cm.hsv,vmin=0,vmax=1,marker = 'H',s=self.s**2))
        self.fig.colorbar(self.scats[0],cax=self.cbar_ax)

        # try:
        #     self.xy = self.defectdata['xy_avg']
        #     self.charge = self.defectdata['charge_avg']
        #     self.defect = self.bx.scatter(np.real(self.xy[0]),np.imag(self.xy[0]),c=self.charge[0],cmap='Greys',s=100)
        # except AttributeError:
        #     pass
        # plt.scatter(np.real(self.xy[0]),np.imag(self.xy[0]),c=self.charge[0],cmap='Greys',s=100)
        # plt.show()
        # sys.exit()
        
        
        
        
        

        
    def SetUpAxes(self,params):
        data=self.data
        self.pos,self.p = data['pos'],data['parameters']
        self.compute_quantities()
        figdim = [16, 6]
        xmin = np.min(np.real(self.pos.flatten()))-1
        xmax = np.max(np.real(self.pos.flatten()))+1
        ymax = np.max(np.imag(self.pos.flatten()))+1
        ymin = np.min(np.imag(self.pos.flatten()))-1
        self.s = np.sqrt(2)*72*figdim[1]/(ymax-ymin)
        xlim=[xmin,xmax]
        ylim=[ymin,ymax]
        
        
        
        self.fig,axes =plt.subplots(1,2,dpi=60,figsize=figdim)
        self.ax,self.bx=axes
        
                

        self.cbar_ax = self.fig.add_axes([0.45, 0.15, 0.03, 0.5])
        
        
        self.fig.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=None, hspace=None)
        self.cmap = plt.get_cmap('hsv')
        try:
            for a in axes:
                a.set_xlim(xlim)
                a.set_ylim(ylim)
                a.set_aspect("equal")
                a.axis("off")
        except ValueError:
            print('!')
            pass
        self.fig.set_figwidth(figdim[0])
        self.fig.set_figheight(figdim[1])
    
        nsteps=np.shape(self.pos)[0]-1
        path = self.p['outputpath'] + self.p['movpath']
        if not os.path.exists(path):
            os.makedirs(path)
        self.path=path
        self.nsteps=nsteps

    def AnimateFull(self,):
        self.SetUpAxes(self.p)
        self.FullRender(filename=self.path)
        ani=animation.FuncAnimation(self.fig,self.FullUpdate,np.arange(self.nsteps),blit=False,interval=30)
        ani.save(self.path+self.p['filename']+'-render.mp4')        
    def AnimateScatter(self,frames):
        self.SetUpAxes(self.p)
        self.nsteps = np.min([self.nsteps,frames])
        self.ScatterAnimate(filename=self.path)

        
#         
        # writer = animation.FFMpegWriter(
        #     fps=30,
        #     metadata=dict(artist='Me'),
        #     bitrate=3000,
        #     codec='libx264'  # explicitly request high-quality codec
        # )

        ani=animation.FuncAnimation(self.fig,self.ScatterUpdate,np.arange(self.nsteps),blit=False,interval=30)
        filename = self.p['filename'].replace(" ", "_")  # safer


        import platform
        if platform.system() == 'Windows':
            print('???')
            Writer = animation.writers['ffmpeg']
            writer = Writer(fps=30, metadata=dict(artist='Me'), bitrate=3000)
            ani.save(self.path+filename+'_scatter.mp4',writer=writer)        
        elif platform.system() != 'Windows':
            import matplotlib as mpl
            mpl.rcParams['animation.ffmpeg_path'] = r'/usr/local/Caskroom/miniconda/base/envs/spyder/bin/ffmpeg' 
        
            ani.save(self.path+filename+'_scatter.mp4')        


    def PlotAmplitudes(self):
        self.compute_quantities()
        mag=self.magnitude
        fig,ax=plt.subplots(1)
        ax.plot(np.sum(mag,axis=0))
        ax.set_xlabel('time')
        ax.set_ylabel('$\\sum | \\phi| ')
        pkl = self.p['outputpath'] +self.p['pdfpath']
        path = os.getcwd()+'/' + pkl
        if not os.path.exists(path):
            os.makedirs(path)
        print(path+self.p['filename'])
        fig.savefig(path+self.p['filename']+'.pdf')


    def PlotRadialKymo(self,t=-1):
        pos = self.data['pos']
        hexidx = self.data['hexagon index']
        trihexidx= self.data['trihexagon index']
        print(self.data['parameters']['tf'])
        pos0 = pos[0]
        centre = np.average(pos0)
        hexcentres = np.average(pos0[hexidx],axis=1)
        hexangle = np.angle(hexcentres - centre)
        argphi = np.real(self.magnitude.T * np.exp(1j*self.phase.T))
        arr1inds = hexangle.argsort()
        hexangle = hexangle[arr1inds[::-1]]
        argphi = argphi[:,arr1inds[::-1]]
        avg = 9
        hexavg =  hexangle.reshape(-1, avg).mean(axis=1)
        argphi=  argphi.reshape(argphi.shape[0],-1, avg).mean(axis=2)



        colors = cm.rainbow(np.linspace(0, 1, len(argphi)))
        fig,ax= plt.subplots(1,4,figsize=(18,6))

        fftphi = np.fft.fft(argphi,axis=1)
        fftfreq = np.fft.fftfreq(len(argphi[0]))

        ax[0].imshow(np.log10(np.abs(argphi)),aspect='auto',origin='lower')
        ax[1].imshow(np.log10(np.abs(fftphi)),aspect='auto',origin='lower')
        ax[2].scatter(hexavg,argphi[t])
        ax[3].scatter(hexavg,fftphi[t])
        plt.show()
        

    def PlotOddModulus(self,path):
        directory = os.fsencode(path)
        straindata = []
        for file in os.listdir(directory):
            filename = os.fsdecode(file)
            if not filename.endswith(".DS_Store"): 
                data = self.load(path+filename)
                self.pos,self.vel,self.p = data.pos,data.vel,data.params
                self.compute_quantities()
                straindata.append([self.p, self.uxx,self.uyy,self.uxy])
        return straindata
        
        