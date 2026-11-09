import numpy as np
from pde import CartesianGrid, MemoryStorage, ScalarField, FieldCollection, PDEBase,CallbackTracker,ExplicitSolver,Controller,UnitGrid
import os,sys
import numba as nb
import pickle
import pde
import matplotlib.pyplot as plt
import matplotlib
import itertools
import multiprocessing
import numba as nb
import numpy as np



# fatboy equation with correlated noise (set noise=0 to get the noiseless case)
class FibreModel(PDEBase):
    def __init__(self,p):
        self.p=p
    def evolution_rate(self, state, t=0):
        u, v = state
        rhs = state.copy()
        ##### non-linear continuum equation for fatboy #####
        rhs[0] = v
        rhs[1] = -(u.laplace(bc = 'natural') + self.p['alpha']*(np.arctan(u.gradient(bc = 'natural').laplace(bc = 'natural')[0])) + (v.laplace(bc = 'natural'))).laplace(bc = 'natural')
        return rhs
    def _make_pde_rhs_numba(self, state):
        """ numba-compiled implementation of thea PDE """
        alpha =self.p['alpha']
        laplace = state.grid.make_operator("laplace", bc = 'natural')
        gradient = state.grid.make_operator("gradient", bc = 'natural')
        @nb.jit
        def pde_rhs(state_data, t):
            u = state_data[0]
            v = state_data[1]
            rate = np.empty_like(state_data)
            rate[0] = v
            rate[1] = -laplace( laplace(u) + alpha*np.arctan(laplace(gradient(u)[0])) + laplace(v))
            return rate
        return pde_rhs
    


class FibreModelNoise(FibreModel):
    def noise_realization(self, state, t):
        r = np.random.rand(1)*2*np.pi
        coords = state.grid.cell_coords
        x = coords[:,0]
        L = np.max(x)
        k=self.p['k_in']
        forcing = self.noise*np.cos(k*2*np.pi*x/L + r)
        return forcing

    def _make_noise_realization_numba(self, state):
        coords = state.grid.cell_coords
        noise=self.noise
        x = coords[:,0]
        print(x.shape)
        L = np.max(x)
        k=self.p['k_in']    
        @nb.jit
        def noise_realization(state_data, t):
            return noise*np.cos(k*2*np.pi*x/L + np.random.rand(1)*2*np.pi)
        return noise_realization
    

def get_initial_state(self, array_u, array_v):
    grid = CartesianGrid([[0, p['L']]], [p['N']], periodic=p['periodic'])
    return FieldCollection([ScalarField(grid, array_u),ScalarField(grid, array_v)])


def RandomInitialCondition(p,seed=0):
    rng=np.random.RandomState(seed)
    N=p['N']
    phi0 =p['amp']* (rng.rand(N)-0.5)
    phidot0 =p['amp']* (rng.rand(N)-0.5)
    phi0 = phi0 - np.average(phi0)
    phidot0 = phidot0 - np.average(phidot0)    
    return phi0,phidot0


def FourierTransform(phi, L, N):
    NT=phi.shape[0]
    NX=phi.shape[1]
    phihat=[]
    for timeidx in range(0,NT):
        x=np.fft.fft(phi[timeidx,:]) # the fft
        phihat.append(np.fft.fftshift(x)) # shift the fft so that the zero frequency is in the middle of the array
    phihat=np.array(phihat)
    freqs=np.fft.fftfreq(NX,L/N) # the actual k-space values
    return [phihat,np.fft.fftshift(freqs)]



def RunInstance(p,seed=0):
    print(seed)
    p['phi0'],p['phidot0'] = RandomInitialCondition(p,seed=int(seed))
    state = get_initial_state(p,p['phi0'],p['phidot0']) #initial field for u,v
    storage = MemoryStorage()
    trackers = ['progress'    , 'consistency'  ,     storage.tracker(interval=p['pt'])]#, CallbackTracker(ZerosCondition, interval=200*p['pt'])]
    eq = FibreModelNoise(p)  # define the pde
    solver = ExplicitSolver(eq,adaptive=p['adaptive'])
    controller = Controller(solver, t_range=p['tf'],tracker=trackers)
    sol = controller.run(state, dt=p['dt'])
    field =[]
    for j,i in storage.items():
        field.append(np.array(i.data))
    field=np.array(field)
    phi,phidot = np.asarray(field)[:,0,:],np.asarray(field)[:,1,:] 
    timestamps = np.array(storage.times)
    return phi,phidot,timestamps

def make_plist(p,varpar,varrange):
    plist = []
    ranges = [*varrange]
    for vals in zip(itertools.product(*ranges)):
        p0=dict(p)
        for val,par in zip(np.squeeze(vals),varpar):
            p0[par] = val
            p0['filename'] = p0['filename'] + '' + f'{par} = {val}'
        p0['path']+=f'alpha={p0["alpha"]}/'
        plist.append(p0)
    return plist



def log_spaced_integers(N, M):
    if N < 2:
        raise ValueError("N must be at least 2 to include both 0 and M.")
    if M <= 0:
        raise ValueError("M must be a positive integer.")
    
    # Generate N-1 logarithmically spaced points between 1 and M
    log_spaced = np.logspace(0, np.log10(M), N-1, dtype=int)
    
    # Prepend 0 to include it in the array
    log_spaced = np.insert(log_spaced, 0, 0)
    
    # Remove duplicates and ensure the last element is M
    unique_values = np.unique(log_spaced)
    if unique_values[-1] != M:
        unique_values[-1] = M
    
    return unique_values

def job(p):
    phi,phidot,times = RunInstance(p,seed=p['run'])
    ndata = np.min([p['num_frames'],len(phidot)/10])
    logints = log_spaced_integers( int(ndata),len(phidot)-1)
    phi=phi[logints]
    phidot=phidot[logints]
    print(times.shape,logints.shape,logints[-1])
    times=times[logints]
    dic = {'phi':phi,'phidot':phidot,'times':times,'parameters':p}
    if not os.path.exists(p['path']):
        os.makedirs(p['path'])
    with open(p['path']+p['filename'], 'wb') as output:
        pickle.dump(dic,output,pickle.HIGHEST_PROTOCOL)
        print('saved as ',p['path']+p['filename'])


p={ 'noise':.0,
    'bc': "natural",
    'k_in':10,
    'alpha':1,#activity
    'N':5000, #discretization
    'L':1000,  #box size
    'dt':2e-4,#integration timesteps (if not adaptive)
    'pt':1, #print timesteps,
    'num_frames':300,
    'tf':100000, #total time
    'amp':1e-10,#initial random noise amplitude
    'adaptive':False,
    'periodic':True,
    'run':0
}
p['path'] = 'simulation/Fatboy/data/fatboy/N=5000/'
p['filename'] = ''
varpar= np.array(['run','alpha'])
varrange=[np.arange(6,dtype=int),np.linspace(1,10,5)]
plist = make_plist(p,varpar,varrange)


if __name__ ==  '__main__':
    pool = multiprocessing.Pool(30)
    pool.map(job, plist)
    pool.close()
