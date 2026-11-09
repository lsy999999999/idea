
import matplotlib.pyplot as plt
import numba as nb
import numpy as np
import matplotlib.cm as cm
from scipy.integrate import solve_ivp
from numba import njit, prange
from scipy.signal import savgol_filter



def gen_log_space(limit, n):
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

DEBUG = True  # Toggle this to enable/disable debug prints
@njit
def debug_print(t):
    if DEBUG:
        # Simple and Numba-safe print (no f-strings, no complex types)
        if int(t * 10) % 10 == 0:  # e.g., print every 0.1 time units
            print("t =", t)
@njit(parallel=True)
def fourier_rhs_pos_k(t, a_, alpha, N, L, B=1, P=1):
    debug_print(t)  # Controlled debug print

    Rea = a_[0*N:1*N]
    Ima = a_[1*N:2*N]
    Readot = a_[2*N:3*N]
    Imadot = a_[3*N:4*N]

    a = Rea + 1j * Ima
    adot = Readot + 1j * Imadot
    da = adot
    dda = np.zeros(N, dtype=np.complex128)

    abs_squared = np.abs(a)**2
    two_a = 2.0 * a

    for n in prange(N):
        k = n + 1
        q_n = 2 * np.pi * k / L
        linear = (1 - 1j * alpha) * a[n] + adot[n]
        onsite = abs_squared[n] * a[n]
        bath = 0.0 + 0.0j
        pdt = 0.0 + 0.0j

        if B == 1:
            bath = np.sum(abs_squared) - abs_squared[n]
            bath *= two_a[n]

            if P == 1:
                for i in range(N):
                    ai = a[i]
                    for j in range(N):
                        if i != j and i != n:
                            idx = n - i + j
                            if 0 <= idx < N:
                                pdt += ai * np.conjugate(a[j]) * a[idx]

        nonlinear = onsite + bath + pdt
        dda[n] = -q_n**2 * (linear + nonlinear)

    out = np.empty(4 * N, dtype=np.float64)
    for i in prange(N):
        out[i] = da[i].real
        out[N + i] = da[i].imag
        out[2 * N + i] = dda[i].real
        out[3 * N + i] = dda[i].imag

    return out


def integrate_fourier_system_pos_k(alpha=1.0, N=8, L=1.0, T=10.0, n_steps=100, amp=1e-5, B=1, P=1, run=1):
    seed = run
    np.random.seed(seed)
    # print('seed', seed)

    a0 = (np.random.rand(4, N) - 0.5) + 1j * (np.random.rand(4, N) - 0.5)
    a0 = a0.flatten() * amp
    t = np.linspace(0, T, int(10*n_steps))

    # Track last printed progress
    last_progress = [-1.0]  # Use mutable to allow updates from nested scope

    def rhs_wrapper(t, y):
        # Compute current progress percentage (0.0 to 1.0)
        progress = t / T
        if progress - last_progress[0] >= 1 / 1000:
            
            print(f"t = {t:.4f} ({int(progress * 1000)} / 1000)",end='\r')
            last_progress[0] = progress
        return fourier_rhs_pos_k(t, y, alpha, N, L, B, P)

    sol = solve_ivp(rhs_wrapper, (0, T), a0, dense_output=True)


    # print("Integration done.")
    logints = gen_log_space(n_steps*10,n_steps)
    
    y = sol.sol(t[logints])
    daRe, daIm, ddaRe, ddaIm = np.reshape(y, (4, N, y.shape[1]))
    ak = daRe + 1j * daIm
    akdot = ddaRe + 1j * ddaIm
    t=t[logints]

    return t, np.array(ak), np.array(akdot)



def average(*args,**kwargs):

    n=kwargs['run']
    aks=[]
    akdots=[]
    for n in np.arange(n):
        kwargs['run'] = n

        t,ak,akdot = integrate_fourier_system_pos_k(*args,**kwargs)

        aks.append(ak)
        akdots.append(akdot)

    
    aks=np.array(aks)
    akdots=np.array(akdots)
    return t,np.average(aks,axis=0),np.average(akdots,axis=0),aks,akdots


import os,pickle
def pickledump(path,filename,datadic):
    if not os.path.exists(path):
        os.makedirs(path)
    with open(path+filename, 'wb') as output:
        print('saved as:   ',path+filename)
        pickle.dump(datadic,output,pickle.HIGHEST_PROTOCOL)

def PlotModes(data,name,folder):

    import matplotlib
    fig=plt.figure(figsize=(6,3),dpi=200)
    # cx = fig.add_axes([2.3,0.2,.5,.5])
    cx = fig.add_axes([0.6,0.2,.5/2,.5])
    ax0 = fig.add_axes([0.15,0.2,.5/2,.5])
    cax1  = fig.add_axes([.85,0.2,.02,.5])
    cax2  = fig.add_axes([.4,0.2,.02,.5])

    axes = [ax0]
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("", ["b","r"])
    time,ak,akdot,aks,akdots=data
    ak_=ak[:30]
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("", ["#072C8A","#B4BFDC"])
    colors = cmap(np.linspace(0, 1, len(ak_)))

    for n,a in enumerate(ak_):
        axes[0].plot(time,np.abs(a),c=colors[n],lw=1)


    for a in np.array(axes).flatten():
        a.set_yscale('log')
        a.set_xscale('log')
        
    ax0.set_xlabel('time')
    ax0.set_ylabel('amplitude $|a_n|$')

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=0, vmax=len(ak_)))
    cb = plt.colorbar(sm,cax=cax2)
    cb.set_ticks([0,10,20,30])

    cb.set_label('mode $n$',labelpad=6)


    akabs = np.abs(ak[:100])
    tmin,tmax = 1,1e5
    im2 = cx.imshow(np.log10(akabs+1e-15),cmap = 'magma',aspect='auto',origin='lower', interpolation='none',vmin=-2,vmax=2,extent=[tmin,tmax,0,len(akabs)])
    cb = plt.colorbar(im2,label='$\\log |a_n|$',cax=cax1)
    
    cx.set_xscale('log')
    cx.set_yscale('log')
    # 
    
    cx.plot(time[1:],2e3*time[1:]**(-1/2),c='w',lw=1,label= '$\\propto t^{-1/2}$',linestyle='dashed',zorder=100)
    cx.legend(loc='lower left',fontsize=8)
    cx.set_xlabel('time')
    

    ax0.set_xlim([1e-1,2e5])
    ax0.set_ylim([1e-1,1e3])
    cx.set_xlim([1e2,1e5])
    cx.set_ylim([1,10e1])
    

    if not os.path.exists(folder):
        os.makedirs(folder)
    
    fig.savefig(folder+name)




alpha = 1
L =1000
n_steps= 2000
N=50
T=1000

eq = ['full','meanfield','uncoupled']
BP = [[1,1],[1,0],[0,0]]



# Absolute path of the script
script_path = os.path.abspath(__file__)
# Folder containing the script
script_dir = os.path.dirname(script_path)

# 
# for i in range(2):
#     data = average(alpha, N, L, T, n_steps,amp=1e-7,B=BP[i][0],P=BP[i][1],run=1)
#     dic = {'alpha':alpha,'L':L,'n_steps':n_steps,'N':N,'T':T,'data':data}
#     pickledump(script_dir+'/output/spectral2/',f'{eq[i]}',dic)
# 
# 




def load_data(path,filename):
    with open(path+filename, 'rb') as output:
        return pickle.load(output)

for n in ['full','meanfield']:

    dic = load_data(script_dir+f'/output/spectral2/',f'{n}')
    print(dic.keys())
    print(dic['alpha'],dic['N'],dic['L'])
    data = dic['data']
    PlotModes(data,n,script_dir+f'/output/spectral2/plots/')