import sys
import numpy as np
import src.wall_sim as sim
import src.wall_analysis as ana
import multiprocessing
#GET DATA



w = sim.wall()
# a = ana.analyze_wall()
acell = 0.075


#superhexagon:
#N=3 : X=11 Y=8
#N=4 : X=15 Y=11
#N=4 : X=19 Y=14
N = 120
X = 3 + (N-1)*4
Y = 2 + (N-1)*3

ko=10
expname = f'/NLstiffness/N={N}/'


def runsim(params):
    w = sim.wall()
    w.parameters(params=params) 
    w.geo()
    w.go()

def Sweep(plist,cores=1):
    'Sweep over a n-D parameter range with values prange over parameters pname.'
    'plist is a list of dictionaries containing all permutations of the different parameter range s'
    # plist=[]
    # for p in prange:
    #     par = params.copy()
    #     par[pname] = p
    #     par['filename'] = f'{params["movname"]} {pname} = {np.round(p,4)}'
    #     plist.append(par)
    def main():
        pool = multiprocessing.Pool(cores)
        pool.map(runsim, plist)
        pool.close()
    if __name__ ==  '__main__':
        main()

def animate(params):
    a = ana.analyze_wall(params)
    a.AnimateScatter(9999)
    # a.AnimateFull(params)


import itertools
def make_plist(para,study,varpar,varrange):
    plist = []
    ranges = [*varrange]
    for vals in zip(itertools.product(*ranges)):
        p0=dict(para)

        for val,p in zip(list(vals[0]),varpar):

            p0[p] = val
            p0['filename'] = p0['filename'] + '' + f'{p} = {val},'
        expname = f'/'
        p0['movname'] =f'{p0["filename"]}'  
        p0['datapath']=f'{study}/N={p0["N"]}/{expname}/data/'
        p0['movpath'] = f'{study}/N={p0["N"]}/{expname}/mov/'
        plist.append(p0)
    return plist


def SweepAnim(plist,cores=1):
    'Sweep over a n-D parameter range with values prange over parameters pname.'
    'plist is a list of dictionaries containing all permutations of the different parameter ranges'
    # plist=[]
    # for p in prange:
    #     par = params.copy()
    #     par[pname] = p
    #     par['filename'] = f'{params["movname"]} {pname} = {np.round(p,4)}'
    #     plist.append(par)
    def main():
        pool = multiprocessing.Pool(cores)
        pool.map(animate, plist)
        pool.close()
    if __name__ ==  '__main__':
        main()

params = {  "N":N,"X":X,"Y":Y,"rad": 1/3.,
            "ke":1,  "ko": ko,
            "th_c":np.radians(10),
            'fmax':9e10,
            'kNL':50,#50
            'amp':1e-2,
            "gamma": 0.2,
            "eta":1,
            # "kf": 1e3, "gf":500,
            # "kr": 1e2, "gr":50,#long. springs
            # "ks": 0, "gs":0e2,#wall
            "g": 0,"mass":0.2,
            "fcomp": 80,"v_comp":1e-5,
            "tf":2000,"dt":1e-2,"pt":500,"ct":2e-1,
            'O2':True,"NL":False,
            'datapath':f'data/{expname}/',
            'movpath':f'mov/{expname}/',
            'outputpath':f'simulation/Trihex/output/',
            'defectpath':f'defectdata/',
            'filename':'',
            'rotate90':False, 
            'rot angle':np.pi/6,
            'shape':'disk', 
            'odd':'trihex', #trihex or kekule
            'diluted': 'no', 
            'odd density': 1,
            'compression rate':0.0,
            'compression interval':0,
            'compression ratio':100,
            'periodic':False, #ONLY IN X direction for now (strip)
            'perturb':'all',
            'plot':False,
            'method':'constraint',
            'seed':3,
            'Full':True,
            'circle_inner':0,
            'circle_outer':100
}


disksize = np.linspace(80,80,1)
NLrange = np.linspace(50,50,1)

#,'saturation','geometric']
stp = [[1e9,50]]


params['fmax'] = 1e9    
params['kNL'] = 50
params['circle_outer'] = 100#disksize[0]
params['circle_inner'] = 30
ko_range = np.linspace(4,8,4)
gamma_range = np.linspace(.05,.3,5)
# runrange = np.arange(1,dtype=int)
# inrange = np.linspace(35,35,1)
varrange = [ko_range,gamma_range]
varpar = ['ko','gamma']

study = f'donut4_friction_sweep/'
        
plist = make_plist(params,study,varpar,varrange)



c=20
Sweep(plist,cores=c)
SweepAnim(plist,cores=c)


# for i in range(len(studies)):
#     # for N in Nrange:
#     #     params['N']=N
#     #     params['X'] = 3 + (N-1)*4
#     #     params['Y'] = 2 + (N-1)*3
#     for r in disksize:
#         params['circle_outer'] = r
#         for NL in NLrange:
#             params['kNL'] = NL
#             for ko in ko_range:
#                 params['ko']=ko
#                 expname = f'ko={ko}/'
#                 params['datapath']=f'{study}/N={N}/{expname}/data/'
#                 params['movpath'] = f'{study}/N={N}/{expname}/mov/'
#                 # params['datapath']=f'{study}/r={r}/{expname}/data/'
#                 # params['movpath'] = f'{study}/r={r}/{expname}/mov/'
#                 # 
#                 Sweep(params,seedrange,"seed",cores=c)
#                 SweepAnim(params,np.array([seedrange[0]]),"seed",cores=1)
