#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 23 12:17:12 2021

@author: Jonas
"""
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
import sys, time, pickle
import scipy
import matplotlib.cm as cm
import os
import itertools
from scipy.stats import rankdata
from numba import jit,njit
import numba
from scipy.spatial import cKDTree

class data():
    pass
class wall():
    def __init__(self):
        pass
    def parameters(self,params,plot=False):
        self.p=params
        N=self.p['N']
        
        if self.p['shape']!='rectangle':
            self.X= 3 + (N-1)*4
            self.Y= 2 + (N-1)*3
            self.p['X']=self.X
            self.p['Y']=self.Y
        
        self.X=self.p['X']
        self.Y=self.p['Y']
        self.start = True
        self.data = data()
        self.data.pos = []
        self.data.vel = []
        self.data.fO = []


    def geo(self):        
        def get_gridhexlist():#find the appropriate vertices for the odd forces
            ehex = np.zeros((self.X,self.Y,6),dtype = int)
            ohex = []
            half = np.array([0,1,2])
            self.coorddict = {}
            for m in range(self.X):
                for n in range(self.Y): 
                    chi=0
                    a = self.Y*2 + 1
                    if m!=0 and m!=self.X-1:
                        if m%2==0:
                            a+=1
                            chi=-1
                        elif m%2==1:
                            a+=1
                    elif m==self.X-1:
                        if m%2==0:
                            chi=-1
                            a+=1
                    p1 = half + 2*n + m*(2*self.Y+2) + chi
                    p2 = np.flip(p1 + a)
                    hexidx = np.concatenate((p1,p2))
                    ehex[m,n] = hexidx
                    for idx in ehex[m,n]:
                        if f'{idx}' not in self.coorddict:
                            edgelength = 2*self.Y+1
                            bulklength = 2*(self.Y+1) 
                            x = idx // edgelength
                            y = np.remainder(idx,edgelength)
                            if x>0:
                                x = (idx - edgelength) // bulklength +1
                                y = np.remainder(idx-edgelength,bulklength)
                            self.coorddict[f'{idx}'] = (x,y)
            gridhexlist = np.reshape(ehex,(self.X*self.Y,6))
            return gridhexlist
        
        def get_trihexlist():
            self.xtri = int((self.X-1)/2)
            self.ytri = int(self.Y - (np.ceil(self.Y/3)))
            ntri = self.xtri*self.ytri
            trihexlist = np.zeros((self.xtri,self.ytri,3),dtype=int)
            for nx,x in enumerate(trihexlist):
                for ny,y in enumerate(x):
                    if ny%2==0:
                        trihex = [self.Y*2 + nx * 2 * self.Y + int(ny/2) * 3 + 1,
                                               self.Y*2  + nx * 2 * self.Y + int(ny/2) * 3,
                                               self.Y  + nx * 2 * self.Y + int(ny/2) * 3]
                        trihexlist[nx,ny,:] = trihex
                    elif ny%2==1: 
                        trihex = [self.Y + 2 + nx * 2 * self.Y + int((ny-1)/2) * 3,
                                               self.Y + 1 + nx * 2 * self.Y + int((ny-1)/2) * 3,
                                               2 + nx * 2 * self.Y + int((ny-1)/2) * 3]    
                        trihexlist[nx,ny,:] = trihex
            gridtrihexlist = np.reshape(trihexlist,(ntri,3))
            return gridtrihexlist
        
        def shape_superhexagon():
            Nlayer = self.xtri
            if self.xtri!=self.ytri:
                print(self.X,self.Y)
                print('Make sure the number of x- and y-layers of trihexagons is the same in order to make the superhexagon geometry')
                sys.exit()
            READY=True
            if READY:            
                N = int((self.xtri+1)/2)
                gridtrihexlist = np.reshape(self.gridtrihexlist,(self.xtri,self.ytri,3))
                
                removeidx = []
                if N%2==1:
                    for i in np.arange(N):
                        if i==0:
                            removeidx.append([])
                        else:
                            j1 = int(np.floor(i/2))
                            j2 = int(np.ceil(i/2))
                            removeidx.append(list(np.arange(-j1,j2)))
                    removeidx = removeidx[::-1]

                if N%2==0:

                    for i in np.arange(N):
                        if i==0:
                            removeidx.append([])
                        else:
                            if i%2==1:
                                j1 = int(np.floor(i/2))
                                j2 = int(np.ceil(i/2))
                                removeidx.append(list(np.arange(-j1,j2)-1))
                            else:
                                j1 = int(np.floor(i/2))
                                j2 = int(np.ceil(i/2))
                                removeidx.append(list(np.arange(-j1,j2)))
                    removeidx = removeidx[::-1]

                for id in removeidx[::-1][1:]:
                    removeidx.append(id)
                hexagonaltrihexlist = []
                for n,[ridx,layer] in enumerate(zip(removeidx,gridtrihexlist)):
                    idx = np.delete(np.arange(self.xtri),ridx)
                    hexagonaltrihexlist.append(gridtrihexlist[idx,n,:])
                hexagonaltrihexlist = np.array([item for sublist in hexagonaltrihexlist for item in sublist])
            trihexlist = np.asarray(hexagonaltrihexlist)    
            
            
            self.trihexlist = trihexlist
            self.hexlist = self.gridhexlist[np.unique(self.trihexlist.flatten())]
            trihexrank = rankdata(self.trihexlist,method='min')-1
            self.subsetidx = self.trihexlist.flatten()
            self.trihexlist = np.reshape(trihexrank,np.shape(self.trihexlist))
            self.posidx = np.unique(self.hexlist.flatten())
            self.pos = self.pos[self.posidx]
            hexrank =rankdata(self.hexlist,method='dense')-1
            self.hexlist = np.reshape(hexrank,np.shape(self.hexlist))

        
        def shape_rectangle():
            self.hexlist = self.gridhexlist
            self.trihexlist = self.gridtrihexlist
            trihexrank = rankdata(self.trihexlist,method='min')-1
            self.hexlist = self.hexlist[np.unique(self.trihexlist.flatten())]
            self.posidx = np.unique(self.hexlist.flatten())
            self.pos = self.pos[self.posidx]
            hexrank =rankdata(self.hexlist,method='dense')-1
            self.hexlist = np.reshape(hexrank,np.shape(self.hexlist))
            self.trihexlist = np.reshape(trihexrank,np.shape(self.trihexlist))
        
        # create the graph hexagonal lattice in a grid. This forms the background for other shapes created by removing hexagons
        self.G = nx.hexagonal_lattice_graph(self.Y, self.X, periodic=False, with_positions=True, create_using=None)
        self.posdict = nx.get_node_attributes(self.G, 'pos')
        self.N = len(self.posdict)
        posval = np.asarray(list(self.posdict.values()))
        self.pos = np.vectorize(complex)(posval[:,0],posval[:,1])
        self.gridhexlist = get_gridhexlist() # get indices of all hexagons        
        self.gridtrihexlist = get_trihexlist() # get list of trihexagon indices
            
        if self.p['shape'] == 'rectangle':#basis shape
            shape_rectangle()
        elif self.p['shape'] == 'disk':
            shape_rectangle()
            centraltrihexagon = int((self.trihexlist.shape[0]-1)/2)
            poscentre = np.average(self.pos[self.hexlist[self.trihexlist[centraltrihexagon]]])
            tricentres = np.average(self.pos[self.hexlist[self.trihexlist]],axis=(1,2))
            dcentre = np.abs(tricentres - poscentre)
            circleidx = np.where((dcentre<=self.p['circle_outer']) & (dcentre>=self.p['circle_inner']))[0]
            
            self.trihexlist = self.trihexlist[circleidx]
            trihexrank = rankdata(self.trihexlist,method='min')-1
            self.hexlist = self.hexlist[np.unique(self.trihexlist.flatten())]
            self.posidx2 = np.unique(self.hexlist.flatten())
            self.pos = self.pos[self.posidx2]
            hexrank =rankdata(self.hexlist,method='dense')-1
            self.hexlist = np.reshape(hexrank,np.shape(self.hexlist))
            self.trihexlist = np.reshape(trihexrank,np.shape(self.trihexlist))
            self.posidx = self.posidx[self.posidx2]
        elif self.p['shape'] == 'superhexagon':
            shape_superhexagon()
        elif self.p['shape'] == 'hexagonal annulus':
            shape_superhexagon()
            n=self.p['N']
            l=2*n-1
            Ntri = np.sum(np.array([6*i for i in range(n)]))+1
            l1 = list(range(n,2*n))
            l2 =  list(reversed(range(n,2*n-1)))
            layer=l1+l2
            b=np.arange(Ntri)
            n_annulus = self.p['d_annulus']
            nr=n-n_annulus
            l1 = list(range(nr,2*nr))
            l2 =  list(reversed(range(nr,2*nr-1)))
            removelayer =  l1+l2

            hexlayer  = []
            j=0
            for i in layer:
                hexlayer.append(range(j,j+i))
                j+=i
            if len(removelayer)==1:
                b = np.delete(b,np.argwhere(b==int(Ntri/2)))
            else:
                for n,i in zip(removelayer,np.arange(n_annulus,len(layer)-n_annulus)):   
                    removerow = hexlayer[i][self.p['d_annulus']:self.p['d_annulus']+n ]
                    for j in removerow:
                        b=np.delete(b,np.argwhere(b==j))


            self.trihexlist=self.trihexlist[b]
            trihexrank = rankdata(self.trihexlist,method='min')-1
            self.hexlist = self.hexlist[np.unique(self.trihexlist.flatten())]
            self.posidx2 = np.unique(self.hexlist.flatten())

            self.pos = self.pos[self.posidx2]
            hexrank =rankdata(self.hexlist,method='dense')-1
            self.hexlist = np.reshape(hexrank,np.shape(self.hexlist))
            self.trihexlist = np.reshape(trihexrank,np.shape(self.trihexlist))
            self.posidx = self.posidx[self.posidx2]
        
        self.vel = np.zeros_like(self.pos)
        self.N = np.shape(self.pos)[0]
        self.get_adj()
        #rotate
        self.pos = self.pos * np.exp(1j* self.p['rot angle'])
        self.pos_ini = np.copy(self.pos)
        
        if self.p['perturb']=='all':
            np.random.seed(seed=self.p['seed'])
            self.vel += self.p['amp'] * (np.random.randn(*self.pos.shape)-0.5) +self.p['amp']*1j*(np.random.randn(*self.pos.shape)-0.5)
        elif self.p['perturb']=='pos':
            np.random.seed(seed=self.p['seed'])
        elif self.p['perturb']=='posvel':
            np.random.seed(seed=self.p['seed'])
            self.pos += self.p['amp'] * (np.random.randn(*self.pos.shape)-0.5) +self.p['amp']*1j*(np.random.randn(*self.pos.shape)-0.5)
            np.random.seed(seed=self.p['seed']+1)
            self.vel += self.p['amp'] * (np.random.randn(*self.pos.shape)-0.5) +self.p['amp']*1j*(np.random.randn(*self.pos.shape)-0.5)
        elif self.p['perturb']=='edge':
            np.random.seed(seed=self.p['seed'])
            self.pos[0] += self.p['amp'] * (np.random.randn(*self.pos[0].shape)-0.5) +self.p['amp']*1j*(np.random.randn(*self.pos[0].shape)-0.5)
        elif self.p['perturb']=='none':
            pass
        self.get_constraints()    
        
        if self.p['plot']:# plotting for diagnosis
            self.PlotGeo()



        
        
    def get_adj(self):
        # NN adjacency matrices 
        self.adj1 = nx.linalg.graphmatrix.adjacency_matrix(self.G)

        self.adj1 = self.adj1[self.posidx]
        self.adj1 = self.adj1[:,self.posidx]
        self.adj2 = self.adj1**2
        self.adj2.setdiag(0,k=0)
        self.adj2.eliminate_zeros()
        self.adj3 = self.adj1*self.adj1*self.adj1
        self.adj3[self.adj3>0] = 1
        self.adj3[self.adj1>0] = 0
        self.adj23 = self.adj2 + self.adj3
        self.adj23[self.adj23>0]=1
        
    def get_constraints(self):
        
        a = self.adj1
        a= scipy.sparse.triu(a)
        N=a.get_shape()[0]
        a= np.array(a.nonzero())

        self.constr = []
        for a,b in a.T:
            idx_a = a
            idx_b = b
            # take the starting distance between particle a and b as the constraint length
            constr_len = np.abs(self.pos_ini[idx_b] - self.pos_ini[idx_a])
            self.constr.append((idx_a, idx_b, constr_len))    
        
        # ADD periodic constraints STRIP:
        if self.p['periodic'] and self.p['shape']=='rectangle':
            lbound = self.hexlist[self.trihexlist[:self.ytri][:,-1]]
            rbound = self.hexlist[self.trihexlist[-self.ytri:]]
            leftidx=np.empty(0,dtype=int)
            rightidx=np.empty(0,dtype=int)
            for n,[l,r] in enumerate(zip(lbound,rbound)):
                if n%2==0:
                    leftidx= np.concatenate((leftidx,l[:3]))
                    rightidx = np.concatenate((rightidx,r[1,np.array([-1,-2,-3])]))
                    rightidx = np.concatenate((rightidx,r[0,np.array([-2,-3,-4])]))
                elif n%2==1:
                    leftidx= np.concatenate((leftidx,l[np.array([-1,0,1,2,3])]))
                    rightidx = np.concatenate((rightidx,r[0,np.array([-1,-2])]))
            self.rightidx=rightidx[1:]
            self.leftidx = leftidx[:-1]
            constr_arr = np.array(self.constr)
            for l,r in zip(self.leftidx,self.rightidx):
                L0 = np.argwhere((constr_arr[:,0]==l,constr_arr[:,1]==l))
                R0 = np.argwhere((constr_arr[:,0]==r,constr_arr[:,1]==r))
                
                if L0.shape[0]!=3:
                    for i in L0:
                        nbconstr = constr_arr[i[1]]
                        nb = int(nbconstr[np.abs(i[0]-1)])
                        print(l,i,nb)
                        if nb in self.leftidx:
                            print('y')
                        else:
                            print(self.pos[nb]-self.pos[l])
                            d = self.pos[nb]-self.pos[l]
                            # D = 
                            # newconstr = (l,nb,)
                            
                            #add new constraint to right
        self.constr=np.array(self.constr)    
        
        
    
    def PlotGeo(self):
        for n,i in enumerate(self.pos):
            plt.scatter(np.real(i),np.imag(i),c='k',s=4)
            plt.annotate(n,(np.real(i),np.imag(i)),fontsize=7)
        for n,h in enumerate(self.hexlist):
            plt.annotate(n,(np.real(np.average(self.pos[h])),np.imag(np.average(self.pos[h]))),fontsize=10)
        colors = plt.cm.rainbow(np.linspace(0,1,len(self.trihexlist)))
        for n,i in enumerate(self.trihexlist):
            plt.annotate(n,(np.real(np.average(self.pos[self.hexlist[i]])),np.imag(np.average(self.pos[self.hexlist[i]]))),fontsize=14)
            for m,j in enumerate(self.hexlist[i]):
                plt.fill(np.real(self.pos[j]),np.imag(self.pos[j]),color=colors[n])                
        plt.show()

        
    def pickledump(self,path,filename):
        
        if not os.path.exists(path):
            os.makedirs(path)
        with open(path+filename, 'wb') as output:
            print('saved as:   ',path+filename)
            pickle.dump(self.datadic,output,pickle.HIGHEST_PROTOCOL)
            
    
    def go(self):
        p=self.p
        idx_a,idx_b,constr_len = self.constr.T

        idx_a=idx_a.astype(int)
        idx_b=idx_b.astype(int)
        hexlist = self.hexlist.astype(int)
        trihexlist = self.trihexlist.astype(int)
        print('trihex number: ',trihexlist.shape)






        posdata,veldata,fOdata= self.verlet(self.pos,self.vel,
                                     p['ko'],p['ke'],p['dt'],p['pt'],p['tf'],p['eta'],p['fmax'],p['gamma'],p['kNL'],
                                     idx_a,idx_b,constr_len,hexlist,trihexlist)
        

        pos,S1,S2,mag,B,phase  = self.filter_sort_analyze(np.array(posdata),hexlist)
        pos0=pos[0]
        diffs = pos0[:, np.newaxis] - pos0  # shape (N, N)
        distances = np.abs(diffs)  # shape (N, N)
        max_dist = np.max(distances)
        # print(max_dist)

        phi  =S1+1j*S2 
        t = np.logspace(0,np.log10(p['tf']+1),p['pt'])-1
        t=t[:len(pos)]
        unitcell = np.sqrt(3)
        max_unitcells=max_dist
        bin_edges = np.arange(max_unitcells)*(unitcell)+(0.5*unitcell)

        mag = np.abs(phi)
        phases=np.angle(phi)
        positions=np.average(pos,axis=2)[0]
        hw,correlation,bin_centers = self.get_correlation(mag,phases,positions,bin_edges)


        
        self.datadic = {'pos':np.array(posdata),'vel':np.array(veldata),'parameters':self.p,'hexagon index': self.hexlist, 'trihexagon index': self.trihexlist,'hw':hw,'correlation':correlation,'bin_centers':bin_centers,'mag':mag}
        self.pickledump(p['outputpath']+p['datapath'],p['filename'])

    def filter_sort_analyze(self,pos,hexlist):
        n=9
        # pos = posdata[:,:,0] - 1j* posdata[:,:,1]
        poshex=pos[:,hexlist]
        pos = np.asarray(pos[:,hexlist])
        CoMpos = np.average(pos,axis=2)
        def compute_theta(pos,teq=np.pi*4/6):
            r=np.roll(pos,1,axis=2)-pos
            th=np.angle(-r/np.roll(r,1,axis=2))%(2*np.pi)
            teq=0
            ang_data=th-teq
            # print(ang_data[0])

            r_av=np.average(np.abs(r))
            S1 = (ang_data[:,:,0]-ang_data[:,:,2])/np.sqrt(2)
            S2 = (ang_data[:,:,0]+ang_data[:,:,2]-2*ang_data[:,:,4])/np.sqrt(5)
            B = (ang_data[:,:,0]+ang_data[:,:,2]+ang_data[:,:,4])/np.sqrt(3)
            return S1,S2,B,th

        S1,S2,B,_ = compute_theta(poshex)
        phi = S1+ 1j*S2
        mag = np.abs(phi)
        phase = np.angle(S1 - np.sqrt(S1**2 + S2**2) +1j*S2)%np.pi    
        return pos,S1,S2,mag,B,phase

    def load(filename):
        with open(filename, 'rb') as output:
            return pickle.load(output)

    


    

    def get_correlation(self,mag,phases,positions,bin_edges):
        @jit(nopython=False) 
        def radial_phase_correlation_ckdtree(mag, phases, positions, bin_edges, pairs):
            nbins = len(bin_edges) - 1
            correlation = np.zeros(nbins)
            counts = np.zeros(nbins)
            weights = np.zeros(nbins)

            magmax = np.max(np.array([np.max(mag), 1e-15]))
            mag = mag / magmax

            for k in range(pairs.shape[0]):
                i = pairs[k, 0]
                j = pairs[k, 1]
                dz = positions[j] - positions[i]
                d = np.abs(dz)
                dphi = phases[j] - phases[i]
                w = (1e-15 + mag[j] + mag[i]) / 2.0
                cos_dphi = np.cos(dphi)

                # Binary search for bin index
                low = 0
                high = nbins
                while low < high:
                    mid = (low + high) // 2
                    if d < bin_edges[mid]:
                        high = mid
                    else:
                        low = mid + 1
                bin_idx = low - 1

                if 0 <= bin_idx < nbins:
                    weights[bin_idx] += w
                    correlation[bin_idx] += w * cos_dphi
                    counts[bin_idx] += 1

            for b in range(nbins):
                if counts[b] > 0:
                    correlation[b] /= weights[b]
                else:
                    correlation[b] = np.nan

            bin_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
            return bin_centers, correlation, counts
        

        def radial_phase_correlation_with_ckdtree(mag, phases, positions, bin_edges):
            coords = np.column_stack((positions.real, positions.imag))
            tree = cKDTree(coords)
            max_dist = bin_edges[-1]
            pairs = tree.query_pairs(r=max_dist, output_type='ndarray')
            return radial_phase_correlation_ckdtree(mag, phases, positions, bin_edges, pairs)

        correlation = []
        for n in np.arange(len(mag)):
            # bin_centers, c, counts = radial_phase_correlation(mag[n],phases[n], positions, bin_edges)
            bin_centers, c, counts = radial_phase_correlation_with_ckdtree(mag[n], phases[n], positions, bin_edges)
            correlation.append(c)
        correlation = np.array(correlation)
        bin_centers = np.insert(bin_centers,0,0)
        correlation = np.insert(correlation,0,np.ones_like(correlation[:,0]),axis=1)
            

        hw=[]
        corr_intp =[]

        dmax = 2*np.abs(np.min(np.real(positions)) - np.max(np.real(positions)))
        print(dmax)
        rr = np.linspace(0,dmax,int(dmax*20))
        for m in np.arange(len(correlation)):
            yintp = np.interp(rr,bin_centers,correlation[m])
            corr_intp.append(yintp)
            hw_idx = np.argmax(yintp<0.5)
            hw.append(rr[hw_idx])
        hw= np.array(hw)
        return hw,correlation,bin_centers


###NUMBA
    
    def verlet(self,pos,vel,ko,ke,dt,pt,tf,eta,fmax,gamma,kNL,
               Ia,Ib,Clen,hexlist,trihexlist):
        @jit(nopython=False) 
        def calculate_forces_NUMBA(pos,vel):            
            def get_angles(pos,vel):
                teq=np.pi*4/6
                dth=np.zeros_like(pos,dtype=np.float32)
                dthP=np.zeros_like(pos,dtype=np.float32)
                dthM=np.zeros_like(pos,dtype=np.float32)
                dthPP=np.zeros_like(pos,dtype=np.float32)
                dthMM=np.zeros_like(pos,dtype=np.float32)
                thdot=np.zeros_like(pos,dtype=np.float32)
                thdotP=np.zeros_like(pos,dtype=np.float32)
                thdotM=np.zeros_like(pos,dtype=np.float32)
                velP=np.zeros_like(pos,dtype=np.complex128)
                velM=np.zeros_like(pos,dtype=np.complex128)
                o=np.zeros_like(pos,dtype=np.complex128)
                oM=np.zeros_like(pos,dtype=np.complex128)
                oC=np.zeros_like(pos,dtype=np.complex128)
                for i in range(pos.shape[0]):
                    r = np.roll(pos[i],-1) - pos[i]
                    mag=np.absolute(r)                          #d=N
                    rh=np.zeros_like(mag,dtype=np.complex128)#r/mag     
                    th = np.zeros_like(mag)
                    for j in range(rh.shape[0]):
                        if mag[j]==0:
                            rh[j]=0
                            o[i,j]=0.
                        else:
                            rh[j] = r[j]/mag[j] 
                            o[i,j]=1j*rh[j]/mag[j]
                        
                    for j in range(rh.shape[0]):
                        if np.roll(rh,1)[j]==0:
                            th[j]=0.
                        else:
                            th[j]=np.angle(-rh[j]/np.roll(rh,1)[j])%(2*np.pi)    #d=N
                    
                    dth[i] = th-teq
                    

                    dthP[i]=np.roll(dth[i],-1)
                    dthM[i]=np.roll(dth[i],1)
                    dthPP[i]=np.roll(dth[i],-2)
                    dthMM[i]=np.roll(dth[i],2)
                    
                    oM[i]=np.roll(o[i],1)
                    oC[i]=o[i]+oM[i]
                    velP[i]=np.roll(vel[i],-1)
                    velM[i]=np.roll(vel[i],1)
                    thdot[i]=np.real(-oC[i]*np.conj(vel[i])+o[i]*np.conj(velP[i])+oM[i]*np.conj(velM[i]))
                    thdotP[i]=np.roll(thdot[i],-1)
                    thdotM[i]=np.roll(thdot[i],1)
                    
                return dth,dthP,dthM,thdot,thdotP,thdotM,o,oM,oC
            
            fe = np.zeros_like(pos,dtype=np.complex128) #N
            pos_reshape=np.zeros((hexlist.shape[0],hexlist.shape[1]),dtype=np.complex128) #Nhex*6
            vel_reshape=np.zeros((hexlist.shape[0],hexlist.shape[1]),dtype=np.complex128)#Nhex*6
            for i in range(hexlist.shape[0]):
                for j in range(hexlist.shape[1]):
                    pos_reshape[i,j] = pos[hexlist[i,j]]
                    vel_reshape[i,j] = vel[hexlist[i,j]]
                    
            dth,dthP,dthM,thdot,thdotP,thdotM,o,oM,oC = get_angles(pos_reshape,vel_reshape)#Nhex*6


            def even_elastic(dth,fe):
                feven = ke*(dth*oC-dthP*o-dthM*oM)
                fNL  = kNL*(dth**3*oC-dthP**3*o-dthM**3*oM)

                fd = eta*(thdot*oC-thdotP*o-thdotM*oM)
                for i in range(hexlist.shape[0]):
                    for j in range(hexlist.shape[1]):
                        fe[hexlist[i,j]] += feven[i,j] + fd[i,j] + fNL[i,j]
                return fe
            
            def trihex_odd_elastic(posflat,pos):
                leq = np.full(6,2)                         # NNN equilibrium length
                dl = np.zeros_like(hexlist,dtype=np.float64) #111,6
                lu = np.zeros_like(hexlist,dtype=np.complex128) #111,6
                for i in range(hexlist.shape[0]):                        
                    l = pos[i] - np.roll(pos[i],3) # NNN distances for each vertex on each hexagon
                    # print(np.abs(l))
                    lu[i] = l/np.abs(l)                # NNN unit vector
                    dl[i] = (np.abs(l)-leq)            # NNN deformation magnitude
                    # trihex = trihexlist
                
                fodd = np.zeros_like(hexlist,dtype=np.complex128)
                oddmag = np.zeros_like(hexlist,dtype=np.float64)

                for i in range(trihexlist.shape[0]):
                    oddmag[trihexlist[i,0],0] = dl[trihexlist[i,1],2] - dl[trihexlist[i,2],1] 
                    oddmag[trihexlist[i,1],2] = dl[trihexlist[i,2],1] - dl[trihexlist[i,0],0] 
                    oddmag[trihexlist[i,2],1] = dl[trihexlist[i,0],0] - dl[trihexlist[i,1],2] 
                
                def threshold_odd_force(oddmag):
                    if ko!=0. and fmax!=0.:
                        for i in range(oddmag.shape[0]):
                            oddmag[i][oddmag[i]>fmax] = fmax
                            oddmag[i][oddmag[i]<-fmax] = -fmax
                    return oddmag
                
                oddmag = threshold_odd_force(ko*oddmag)
                for i in range(fodd.shape[0]):
                    fodd[i] =  (oddmag[i]*lu[i] - np.roll(oddmag[i]*lu[i],3))
                fO = np.zeros_like(posflat,dtype=np.complex128)
                for i in range(hexlist.shape[0]):
                    fO[hexlist[i]] += fodd[i]
                return fO
            
            def substrate_friction(vel):
                fF = -gamma*vel
                return fF            

            fE=even_elastic(dth,fe)
            fO=trihex_odd_elastic(pos,pos_reshape)    
            fF = substrate_friction(vel)
            f = fE+fO+fF
            return f,fE,fO
        
        def get_forces(pos,vel):
            f,fe,fo = calculate_forces_NUMBA(pos,vel)
            if self.p['periodic']:
                L = np.array([3,4,5,6,0,1,2,8,9,10,11])
                R = len(self.pos) - np.array([8,7,6,5,16,15,14,4,3,2,1])-1

                fL = np.copy(f[L])
                fR = np.copy(f[R])
                f[L]+=fR
                f[R]+=fL
            return f,fe,fo
        
        
        def get_constraint_impulses_sparse(new_velocity,pos,Ia,Ib,Clen,dt): #sparse matrices no numba
            def calc_jacob_jacobderiv_constrvec():
                Nc=len(Clen)
                n = np.arange(Nc)
                idx_a = Ia
                idx_b = Ib
                constr_len=Clen
                #scipy sparse
                pos_a = pos[idx_a]
                pos_b = pos[idx_b]
                constr_dist = pos_b - pos_a
                pos_ax, pos_ay = (pos_a.real, pos_a.imag)
                pos_bx, pos_by = (pos_b.real, pos_b.imag)            
                J = np.array([-pos_bx+pos_ax,n,idx_a*2])
                J = np.concatenate((J,np.array([-pos_by+pos_ay,n,idx_a*2+1])),axis=1)
                J = np.concatenate((J,np.array([pos_bx-pos_ax,n,idx_b*2])),axis=1)
                J = np.concatenate((J,np.array([pos_by-pos_ay,n,idx_b*2+1])),axis=1)
                
                row = Nc 
                col = len(pos)*2
                c = 0.5 * (np.abs(constr_dist) - constr_len)
                constr_vec=c
                jacob = scipy.sparse.coo_matrix((J[0], (J[1], J[2])), shape=(row,col))
                
                return J,constr_vec,jacob
            
            J,constr_vec,jacob = calc_jacob_jacobderiv_constrvec()
            velocity_vec = np.empty((new_velocity.size*2,), dtype=float)
            velocity_vec[0::2] = new_velocity.real
            velocity_vec[1::2] = new_velocity.imag
            baum_const = 0.2
            baum_stab = (baum_const / dt) * constr_vec
            sjacob = scipy.sparse.csr_matrix(jacob) 
            
            A = sjacob.dot( sjacob.transpose())

            b = -jacob @ velocity_vec - baum_stab        
            sA = scipy.sparse.csr_matrix(A) 
            lagrange_multipliers = scipy.sparse.linalg.spsolve(sA,b)
            constraint_impulse_vec = jacob.T @ lagrange_multipliers
            xs = constraint_impulse_vec[0::2]
            ys = constraint_impulse_vec[1::2]
            constraint_impulses = xs + 1j*ys        
            return constraint_impulses



        t=0
        idx=0
        tprint = np.logspace(0,np.log10(tf+1),pt)-1
        # print(tprint)

        posdata=[]
        veldata=[]
        fEdata=[]
        fOdata=[]
        time0 = time.time()
        while t< tf:
            f,fE,fO= get_forces(pos,vel)
            new_velocity = vel + f * dt # calculate the new velocity based on the calculated forces
            constraint_velocity = get_constraint_impulses_sparse(new_velocity,pos,Ia,Ib,Clen,dt)             
            corrected_velocity = new_velocity +constraint_velocity # correct the new velocity with constraint impulses
            vel = corrected_velocity
            pos = pos + vel * dt
            if t > tprint[idx]:
                posdata.append(pos)
                # veldata.append(vel)
                # fEdata.append(fE)
                # fOdata.append(fO)
                idx+=1  
            try:
                print(np.round(t/tf*100,3), "%% done",np.round((time.time()-time0)/(t/tf)-(time.time()-time0+1e-15)), 'seconds remaining                                ', end='\r')  
            except ZeroDivisionError:
                pass 
                
            t+=dt
        return posdata,veldata,fOdata
        
    def load(self,filename):
        with open(filename, 'rb') as output:
            return pickle.load(output)
    
    







class DetectDefects():
    def __init__(self,data,phi,phase,magnitude,n_interp=400,wdwsize=8,shift=1,nshift=10,edge=1,plot=False,t0=0,tf=50):
        self.pos=data['pos']
        self.hexlist = data['hexagon index']
        self.p=data['parameters']
        self.pos0com = np.average(self.pos[0][self.hexlist],axis=1)
        self.com = np.average(self.pos0com)
        self.dcommax = np.max(np.abs(self.pos0com - self.com))        
        self.plot=plot
        self.phase = phase
        self.phi = phi
        self.magnitude = magnitude
        self.n_interp=n_interp
        self.wdwsize=wdwsize
        self.shift=shift
        self.nshift=nshift
        self.t0,self.tf=t0,np.min([tf,len(self.pos)])
        self.edge=edge
        self.datadic={}
        self.timestamps = np.arange(self.t0,self.tf)*self.p['pt'] + self.p['pt']
    def pickledump(self,path,filename):
        if not os.path.exists(path):
            os.makedirs(path)
        with open(path+filename, 'wb') as output:
            print('saved as:   ',path+filename)
            pickle.dump(self.datadic,output,pickle.HIGHEST_PROTOCOL)
        
    def dump_data(self):
        if len(self.datadic)==0:
            for key,value in self.dic.items():
                self.datadic[key] = [value]
        else:            
            for key,value in self.dic.items():
                self.datadic[key].append(value)
    def load_data(self,path,filename):
        with open(path+filename, 'rb') as output:
            return pickle.load(output)

    def go(self,p,save=True):
        for t in np.arange(self.t0,self.tf):
            self.dic={}
            self.t=t
            self.frame_analysis()
            self.dump_data()
        if save:
            self.pickledump(p['outputpath']+p['defectpath'],p['filename'])
        
    def frame_analysis(self):
        xdefect=[]
        ydefect=[]
        charge=[]
        for i in np.linspace(0,self.shift,self.nshift):
            self.eps=i
            self.interpolate_lattice()
            self.window_data()
            xyz = self.calculate_winding_number()
            xdefect.append(xyz[0])
            ydefect.append(xyz[1])
            charge.append(xyz[2])
            # col_defects = (defects)/(2*np.pi)+0.5
            # sys.exit()
        xdefect = np.array([item for sublist in xdefect for item in sublist])
        ydefect = np.array([item for sublist in ydefect for item in sublist])
        charge = np.array([item for sublist in charge for item in sublist])
        # arr1inds = xdefect.argsort()
        # ydefect= ydefect[arr1inds]
        # charge = charge[arr1inds]
        # xdefect=xdefect[arr1inds]
        
        
        mask = np.abs(xdefect + 1j*ydefect - self.com)<(self.dcommax-self.edge)

        self.xdefect = xdefect[mask]
        self.ydefect = ydefect[mask]
        self.charge  = charge[mask]
        self.reduce_defects()
        if self.plot:
            self.plot_frame()

        

        # plt.scatter(xdefect,ydefect,s=2)
        # plt.show()


    def interpolate_lattice(self):
        eps=self.eps
        x = np.real(self.pos0com)
        y = np.imag(self.pos0com)
        z = self.phi[:,self.t]
        X = np.linspace(min(x)+eps, max(x)+eps,self.n_interp)
        Y = np.linspace(min(y)+eps, max(y)+eps,self.n_interp)
        X, Y = np.meshgrid(X, Y)
        intp = scipy.interpolate.LinearNDInterpolator(list(zip(x, y)), z)
        Z = intp(X, Y)
        S1=np.real(Z)
        S2=np.imag(Z)
        phase_intp = np.angle(S1 - np.sqrt(S1**2 + S2**2) +1j*S2)%np.pi
        magnitude_intp = np.real(( (S1+1j*S2)* (S1-1j*S2) )**0.5)
        self.X,self.Y,self.phase_intp,self.magnitude_intp=X,Y,phase_intp,magnitude_intp
        
    def window_data(self):
        def blockshaped(arr, nrows, ncols):
            """
            Return an array of shape (n, nrows, ncols) where
            n * nrows * ncols = arr.size

            If arr is a 2D array, the returned array should look like n subblocks with
            each subblock preserving the "physical" layout of arr.
            """
            h, w = arr.shape
            assert h % nrows == 0, f"{h} rows is not evenly divisible by {nrows}"
            assert w % ncols == 0, f"{w} cols is not evenly divisible by {ncols}"
            return (arr.reshape(h//nrows, nrows, -1, ncols)
                    .swapaxes(1,2)
                    .reshape(-1, nrows, ncols))

        phase_block = blockshaped(self.phase_intp,self.wdwsize,self.wdwsize)
        self.x_block =np.average(blockshaped(self.X,self.wdwsize,self.wdwsize),axis=(1,2))
        self.y_block =np.average(blockshaped(self.Y,self.wdwsize,self.wdwsize),axis=(1,2))
        self.phase_block_wdw = np.concatenate([phase_block[:,0,:], phase_block[:,1:,-1], phase_block[:,-1,:-1], phase_block[:,1:-1,0]],axis=1)
        ngrid = int(np.sqrt(phase_block.shape[0]))
        xgrid = np.linspace(0,ngrid-1,ngrid)
        ygrid = np.linspace(0,ngrid-1,ngrid)
        xgrid,ygrid = np.meshgrid(xgrid,ygrid)
        return 
        
    def calculate_winding_number(self):
        def saw(x):
            i = [x<-np.pi/2][0]
            j = [np.logical_and(x>-np.pi/2, x<np.pi/2)][0]
            k = [x>np.pi/2][0]
            y=np.zeros_like(x)
            y[i]=x[i]+np.pi
            y[j]=x[j]
            y[k]=x[k]-np.pi
            return y

        test = self.phase_block_wdw
        diftest = (test - np.roll(test,1,axis=1))
        sawdiftest= saw(diftest)
        defects= np.sum(sawdiftest,axis=1).T

        defects[np.abs(defects)<np.pi-0.1]=0
        mask = np.logical_or(np.logical_and(defects>(np.pi-0.1),defects<(np.pi+0.1)),np.logical_and(defects<-np.pi+0.1,defects>-np.pi-0.1))
        defects = defects[mask]
        xx = self.x_block[mask]
        yy = self.y_block[mask]        
        return xx,yy,defects
    
    
    def reduce_defects(self):
        xy  =self.xdefect+1j*self.ydefect
        z = self.charge
        m, n = np.meshgrid(xy, xy)
        # get the distance via the norm
        D = abs(m-n)
        threshold = 4*self.shift
        D[D>threshold]=-1

        i=0
        lst=[]
        go=True
        exclude=np.empty(0,dtype=int)
        while go:
            cluster = np.where(D[i]>-1 )[0] 
            exclude = np.concatenate((exclude,cluster))
            rangelenD = np.arange(len(D))
            remain=np.setdiff1d(rangelenD,exclude)
            lst.append(cluster)
            try:
                i=remain[0]
            except IndexError:
                go=False
        xy_avg=[]
        charge_avg=[]
        charge_std=[]
        for cluster in lst:
            xy_avg.append(np.average(xy[cluster]))
            charge_avg.append(np.average(z[cluster]))
            charge_std.append(np.std(z[cluster]))
        charge_avg=np.array(charge_avg)
        charge_std=np.array(charge_std)
        
        charge_avg[charge_avg>0]=np.pi
        charge_avg[charge_avg<0]=-np.pi
        
        
        self.dic['xy_avg']=np.array(xy_avg)
        self.dic['charge_avg'] = charge_avg
        self.dic['charge_std']=charge_std
        self.dic['N_charge'] = len(self.dic['charge_avg'])
        self.dic['Np']= len(charge_avg[charge_avg>0])
        self.dic['Nm']= len(charge_avg[charge_avg<0])
    

    def gen_log_space(self,limit, n):
        result = [1]
        if n>1:  # just a check to avoid ZeroDivisionError
            ratio = (float(limit)/result[-1]) ** (1.0/(n-len(result)))
        while len(result)<n:
            next_value = result[-1]*ratio
            if next_value - result[-1] >= 1:
                # safe zone. next_value will be a different integer
                result.append(next_value)
            else:
                # problem! same integer. we need to find next_value by artificially incrementing previous value
                result.append(result[-1]+1)
                # recalculate the ratio so that the remaining values will scale correctly
                ratio = (float(limit)/result[-1]) ** (1.0/(n-len(result)))
        # round, re-adjust to 0 indexing (i.e. minus 1) and return np.uint64 array
        return np.array(list(map(lambda x: round(x)-1, result)), dtype=np.uint64)



    # def plot_frame(self):
    #     fig,[ax,bx,cx] = plt.subplots(1,3,figsize=(18,6))
    #     s=5
    #     bx.scatter(self.X,self.Y,c=self.phase_intp/(2*np.pi),cmap='hsv',s=s)
    #     # ax.scatter(DD.X,DD.Y,c=np.log10(DD.magnitude_intp),cmap='viridis',s=s)
    #     ax.scatter(np.real(a.avgpos[self.t]),np.imag(a.avgpos[self.t]),c=a.c_angle[self.t],cmap=cm.hsv,vmin=0,vmax=1,marker = 'h',s=20)
    #     cx.scatter(self.X,self.Y,c=self.phase_intp/(2*np.pi),cmap='hsv',s=s)
    #     # cx.scatter(x,y,c = z,cmap='Greys',marker='x',s=50)
    #     cx.scatter(np.real(self.dic['xy_avg']),np.imag(self.dic['xy_avg']),c=self.dic['charge_avg'],cmap='Greys',marker='o',s=100)
    #     plt.show()
        
    def plot_defect_statistics(self):
        # self.dic['xy_avg']
        if len(self.datadic)==0:
            self.datadic = self.load_data(self.p['outputpath']+self.p['defectpath'],self.p['filename'])
        fig,[ax,bx]=plt.subplots(1,2,figsize=(10,3),dpi=150)

        Nt = np.array(self.datadic['N_charge'])
        Np = np.array(self.datadic['Np'])
        Nm = np.array(self.datadic['Nm'])
        
        
        logints = self.gen_log_space(len(self.timestamps),100)
        time_logsampled = self.timestamps[logints]
        N_logsampled = Nt[logints]

        ax.scatter(self.timestamps[logints],Nt[logints])
        bx.scatter(self.timestamps[logints],Np[logints],c='b',label='$+\\frac{1}{2}$')
        bx.scatter(self.timestamps[logints],Nm[logints],c='r',label='$-\\frac{1}{2}$')
        
        try:
            eps=60
            a,b = np.polyfit(np.log10(time_logsampled)[-eps:],np.log10(N_logsampled)[-eps:],1)
            ax.plot(self.timestamps,10**(a*np.log10(self.timestamps)+b),label='$N(t) \\propto t^{{{:.2f}}}$'.format(a),c='r')
        except np.linalg.LinAlgError:
            pass
        for a in [ax,bx]:
            a.set_xscale('log')
            a.set_yscale('log')
            a.set_xlabel('time')
            a.set_ylabel('N')
            a.legend()
        plt.tight_layout()
        plt.show()
        
        
        
