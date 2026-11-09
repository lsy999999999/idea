
from pde import CartesianGrid, MemoryStorage, ScalarField, FieldCollection, PDEBase,CallbackTracker,ExplicitSolver,Controller,UnitGrid
import matplotlib.pyplot as plt
import matplotlib,os,pickle
import numba as nb
import numpy as np
from pde import ScalarField
import matplotlib.cm as cm
from numba import njit, prange
import multiprocessing
import matplotlib.animation as animation


class PhiModel2DPDE(PDEBase):
    def __init__(self,p):
        self.p=p

    def evolution_rate(self, state, t=0):
        alpha,gamma = self.p['alpha'],self.p['gamma']
        u, v = state
        rhs = state.copy()
        rhs[0] = v
        if self.p['saturating']:
            rhs[1] = (u+1j*alpha*u/np.sqrt(1+u**2) + v).laplace(bc=self.p['bc']) - self.p['gamma'] *v
        else:
            rhs[1] = (u+1j*alpha*u + v + np.abs(u)**2*u).laplace(bc=self.p['bc']) - self.p['gamma'] *v
        return rhs

    def _make_pde_rhs_numba(self, state):
        alpha,gamma = self.p['alpha'],self.p['gamma']
        saturating = self.p['saturating']
        laplace = state.grid.make_operator("laplace", bc =self.p['bc'])
        @nb.jit
        def pde_rhs(state_data, t):
            u = state_data[0]
            v = state_data[1]
            rate = np.empty_like(state_data)
            rate[0] = v
            if saturating:
                rate[1] = laplace(u+1j*alpha*u/np.sqrt(1+u**2) + v) - gamma *v
            elif not saturating:
                rate[1] = laplace(u+1j*alpha*u + v + np.abs(u)**2*u) - gamma *v
            return rate
        return pde_rhs
def RandomInitialCondition(p,seed=0):
    Nx = p['Nx']
    Ny = p['Ny']
    Lx = p['Lx']
    Ly = p['Ly']
    amp = p['amp']
    bounds=[(-Lx/2,Lx/2),(-Ly/2,Ly/2)]
    shape=[Nx,Ny]
    grid = CartesianGrid(bounds,shape, periodic=p['periodic'])
    state = amp*(np.random.rand(4,Nx,Ny)-0.5)
    for n,i in enumerate(state):
        state[n] = i - np.average(i)
    return state,grid


import numpy as np

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



@njit(parallel=True)
def compute_radial_autocorrelation(data, bin_width=1.0):
    num_frames, height, width = data.shape
    center_y, center_x = height // 2, width // 2

    # Compute maximum possible distance
    max_radius = np.hypot(center_y, center_x)
    num_bins = int(np.ceil(max_radius / bin_width))
    radial_acfs = np.zeros((num_frames, num_bins))
    counts = np.zeros(num_bins)

    # Precompute distance bins
    for dy in range(-center_y, height - center_y):
        for dx in range(-center_x, width - center_x):
            distance = np.sqrt(dy**2 + dx**2)
            bin_idx = int(distance / bin_width)
            if bin_idx < num_bins:
                counts[bin_idx] += 1

    for t in prange(num_frames):
        frame = data[t]
        mean = np.mean(frame)
        var = np.var(frame)
        if var == 0:
            continue  # Skip frames with zero variance

        for y in range(height):
            for x in range(width):
                value = frame[y, x] - mean
                for dy in range(-center_y, height - center_y):
                    for dx in range(-center_x, width - center_x):
                        distance = np.sqrt(dy**2 + dx**2)
                        bin_idx = int(distance / bin_width)
                        if bin_idx < num_bins:
                            shifted_y = (y + dy) % height
                            shifted_x = (x + dx) % width
                            shifted_value = frame[shifted_y, shifted_x] - mean
                            radial_acfs[t, bin_idx] += value * shifted_value

        # Normalize by variance and counts
        for bin_idx in range(num_bins):
            if counts[bin_idx] > 0:
                radial_acfs[t, bin_idx] /= (var * counts[bin_idx])

    distances = np.linspace(0, max_radius, num_bins)

    return distances, radial_acfs


def runsim(p):
    
    storage = MemoryStorage()
    trackers = ['progress'    , 'consistency'  ,     storage.tracker(interval=p['pt'])]
    state,grid = RandomInitialCondition(p)
    state=FieldCollection([ScalarField(grid,np.vectorize(complex)(*state[:2]),dtype=complex),ScalarField(grid,np.vectorize(complex)(*state[2:]),dtype=complex)])            
    eq=PhiModel2DPDE(p)
    solver = ExplicitSolver(eq,adaptive=p['adaptive'])
    controller = Controller(solver, t_range=p['tf'],tracker=trackers)
    sol = controller.run(state, dt=p['dt'])
    
    
    
    field =[]    
    for n,[j,i] in enumerate(storage.items()):
        field.append(np.array(i.data))
    field=np.swapaxes(field,0,1)

    times = np.linspace(0,p['tf'],len(field[0]))

    phi,phidot = field
    logints = log_spaced_integers(len(phidot), p['num_frames'])
    phi=phi[logints]
    phidot=phidot[logints]
    times=times[logints]
    
    argphi = np.angle(phi)
    distances, radial_acfs = compute_radial_autocorrelation(argphi)
    datadic = {'phi':phi,'phidot':phidot,'times':times,'parameters':p,'distances':distances, 'radial_acfs':radial_acfs}
    pickledump(os.getcwd()+f'/simulation/PhiModel/output/{p["name"]}/data/',f'/{p["filename"]}',datadic)


def pickledump(path,filename,datadic):
    if not os.path.exists(path):
        os.makedirs(path)
    with open(path+filename, 'wb') as output:
        print('saved as:   ',path+filename)
        pickle.dump(datadic,output,pickle.HIGHEST_PROTOCOL)
def load_data(path,filename):
    with open(path+filename, 'rb') as output:
        return pickle.load(output)


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

def SweepAnim(plist,cores=1):
    def main():
        pool = multiprocessing.Pool(cores)
        pool.map(animate, plist)
        pool.close()
    if __name__ ==  '__main__':
        main()

def animate(params, fps=33, dpi=200):
    datadic = load_data(os.getcwd()+f'/simulation/PhiModel/output/{p["name"]}/data/',f'/{params["filename"]}')
    phi=datadic['phi']
    argphi=np.angle(phi)
    absphi=np.abs(phi)
    t, N, _ = phi.shape

    fig=plt.figure(figsize=(10,5),dpi=200)
    ax = fig.add_axes([.05,.1,.4,.8])
    bx = fig.add_axes([.55,.1,.4,.8])
    cax = fig.add_axes([.45,.1,.02,.8])
    
    im1 = ax.imshow(absphi[0], cmap='viridis', vmin=0, vmax=absphi[0].max())
    im2 = bx.imshow(argphi[0], cmap='hsv', vmin=-np.pi, vmax =np.pi)
    ax.axis('off')
    bx.axis('off')


    cb = plt.colorbar(im1,cax)
    def update(frame):
        print(frame)
        im1.set_array(absphi[frame])
        im2.set_array(argphi[frame])
        im1.set_clim(0, absphi[frame].max())
        cb.update_normal(im1)  # dynamically update colorbar to match im1

        return [im1,im2]
    movpath,movname = os.getcwd()+f'/simulation/PhiModel/output/{p["name"]}/mov/',f'/{params["filename"]}.mp4'
    if not os.path.exists(movpath):
        os.makedirs(movpath)
    

    ani = animation.FuncAnimation(fig, update, frames=t, interval=1000/fps)
    ani.save(movpath+movname, fps=fps, dpi=dpi)
    print(f'saved as {movpath+movname}')



p={ 'noise':.0,
    'bc': "natural",
    'alpha':5,#activity
    'gamma':0,#friction
    'Nx':100, #discretization
    'Ny':100, #discretization
    'Lx':100,  #box size
    'Ly':100,  #box size
    'dt':2e-4,#integration timesteps (if not adaptive)
    'num_frames':400,
    'pt':1e0,
    'tf':40000, #total time
    'amp':3e-6,#initial random noise amplitude
    'adaptive':True,
    'periodic':True,
    'saturating':False,
    'name':'friction8/',
    'filename':''
}


p['adaptive'] = True

alpharange = np.linspace(1,5,3)
runrange = np.arange(4,dtype=int)

gammarange = np.logspace(-1.5,0.5,10)
varrange = [alpharange,gammarange]


varpar = ['alpha','gamma']

plist = make_plist(p,varpar,varrange)

Sweep(plist,cores=20)
SweepAnim(plist,cores=20)











