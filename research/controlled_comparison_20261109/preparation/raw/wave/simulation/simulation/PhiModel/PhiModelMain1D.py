
from pde import CartesianGrid, MemoryStorage, ScalarField, FieldCollection, PDEBase,CallbackTracker,ExplicitSolver,Controller,UnitGrid
import matplotlib.pyplot as plt
import matplotlib

import numba as nb
import numpy as np
from pde import ScalarField
import matplotlib.cm as cm
import os,pickle
import multiprocessing

from numba import njit, prange


def pickledump(path,filename,datadic):
    if not os.path.exists(path):
        os.makedirs(path)
    with open(path+filename, 'wb') as output:
        print('saved as:   ',path+filename)
        pickle.dump(datadic,output,pickle.HIGHEST_PROTOCOL)


class PhiModel1DPDE(PDEBase):
    def __init__(self,p):
        self.p=p

    def evolution_rate(self, state, t=0):
        alpha,gamma = self.p['alpha'],self.p['gamma']
        u, v = state
        rhs = state.copy()
        rhs[0] = v
        rhs[1] = (u+1j*alpha*u + v + np.abs(u)**2*u).laplace(bc=self.p['bc']) - self.p['gamma'] *v
        return rhs

    def _make_pde_rhs_numba(self, state):
        alpha,gamma = self.p['alpha'],self.p['gamma']
        laplace = state.grid.make_operator("laplace", bc =self.p['bc'])
        @nb.jit
        def pde_rhs(state_data, t):
            u = state_data[0]
            v = state_data[1]
            rate = np.empty_like(state_data)
            rate[0] = v
            rate[1] = laplace(u+1j*alpha*u + v + np.abs(u)**2*u) - gamma *v
            return rate
        return pde_rhs
def RandomInitialCondition(p,seed=0):
    np.random.seed(seed)
    Nx = p['Nx']
    Lx = p['Lx']
    amp = p['amp']
    bounds=[(-Lx/2,Lx/2)]
    shape=[Nx]
    grid = CartesianGrid(bounds,shape, periodic=p['periodic'])
    state = amp*(np.random.rand(4,Nx)-0.5)
    for n,i in enumerate(state):
        state[n] = i - np.average(i)
    return state,grid


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



def runsim(p):
    
    storage = MemoryStorage()
    trackers = ['progress'    , 'consistency'  ,     storage.tracker(interval=p['pt'])]
    state,grid = RandomInitialCondition(p,seed=p['seed'])
    state=FieldCollection([ScalarField(grid,np.vectorize(complex)(*state[:2]),dtype=complex),ScalarField(grid,np.vectorize(complex)(*state[2:]),dtype=complex)])            
    eq=PhiModel1DPDE(p)
    solver = ExplicitSolver(eq,adaptive=p['adaptive'])
    controller = Controller(solver, t_range=p['tf'],tracker=trackers)
    sol = controller.run(state, dt=p['dt'])
    
    
    
    field =[]    
    for n,[j,i] in enumerate(storage.items()):
        field.append(np.array(i.data))
    field=np.swapaxes(field,0,1)
    
    times = np.linspace(0,p['tf'],len(field[0]))


    phi,phidot = field 
    print('!!!!',len(phidot),p['num_frames'])

    logints = log_spaced_integers( p['num_frames'],len(phidot)-1)

    phi=phi[logints]
    phidot=phidot[logints]
    times=times[logints]


    argphi = np.angle(phi)
    datadic = {'phi':phi,'phidot':phidot,'times':times,'parameters':p}
    pickledump(os.getcwd()+f'/simulation/PhiModel/output/{p["name"]}/',f'/{p["filename"]}',datadic)
    distances, radial_acfs = compute_radial_autocorrelation(argphi)
    datadic['distances']=distances
    datadic['radial_acfs'] = radial_acfs
    pickledump(os.getcwd()+f'/simulation/PhiModel/output/{p["name"]}/',f'/{p["filename"]}',datadic)
    print('done')


@njit(parallel=True)
def compute_radial_autocorrelation(data, bin_width=1.0):
    num_frames, height = data.shape
    center_y = height // 2

    # Compute maximum possible distance
    max_radius = center_y
    num_bins = int(np.ceil(max_radius / bin_width))
    radial_acfs = np.zeros((num_frames, num_bins))
    counts = np.zeros(num_bins)

    # Precompute distance bins
    for dy in range(-center_y, height - center_y):
        
        distance = np.sqrt(dy**2)
        bin_idx = int(distance / bin_width)
        if bin_idx < num_bins:
            counts[bin_idx] += 1

    for t in range(num_frames):
        frame = data[t]
        mean = np.mean(frame)
        var = np.var(frame)
        if var == 0:
            continue  # Skip frames with zero variance

        for y in range(height):
            value = frame[y] - mean
            for dy in range(-center_y, height - center_y):
                distance = np.sqrt(dy**2)
                bin_idx = int(distance / bin_width)
                if bin_idx < num_bins:
                    shifted_y = (y + dy) % height
                    shifted_value = frame[shifted_y] - mean
                    radial_acfs[t, bin_idx] += value * shifted_value

        # Normalize by variance and counts
        for bin_idx in range(num_bins):
            if counts[bin_idx] > 0:
                radial_acfs[t, bin_idx] /= (var * counts[bin_idx])

    distances = np.linspace(0, max_radius, num_bins)

    return distances, radial_acfs/height

import itertools
def make_plist(para,varpar,varrange):
    plist = []
    ranges = [*varrange]
    for vals in zip(itertools.product(*ranges)):
        p0=dict(para)

        for val,p in zip(list(vals[0]),varpar):

            p0[p] = val
            p0['filename'] = p0['filename'] + '' + f'{p} = {val},'
        plist.append(p0)
    return plist


def Sweep(plist,cores=1):
    'Sweep over a n-D parameter range with values prange over parameters pname.'
    'plist is a list of dictionaries containing all permutations of the different parameter range s'
    # plist=[]
    # for p in prange:
    #     par = params.copy()
    #     par[pname] = p
    #     par['filename'] = f'{pname} = {np.round(p,4)}'
    #     plist.append(par)
    
    def main():
        pool = multiprocessing.Pool(cores)
        pool.map(runsim, plist)
        pool.close()
    if __name__ ==  '__main__':
        main()


p={ 'noise':.0,
    'bc': "natural",
    'alpha':8,#activity
    'gamma':0,#friction
    'Nx':4000, #discretization
    'Lx':1000,  #box size
    'dt':5e-5,#integration timesteps (if not adaptive)
    'num_frames':400,
    'pt':1,
    'tf':5000, #total time
    'amp':3e-2,#initial random noise amplitude
    'adaptive':False,
    'periodic':True,
    'name':'alphasweep1D/4/',
    'filename':''
}

p['seed']=1


alpharange = np.linspace(1,10,5)
runrange = np.arange(2,dtype=int)
gammarange = np.concatenate((np.array([0]),np.logspace(-2,1,10)))


varrange = [alpharange,gammarange,runrange]


varpar = ['alpha','gamma','seed']

plist = make_plist(p,varpar,varrange)

Sweep(plist,cores=50)

