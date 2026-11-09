import numpy as np
def get_p():
    #superhexagon:
    #N=3 : X=11 Y=8
    #N=4 : X=15 Y=11
    #N=4 : X=19 Y=14
    foldername='coarsening/test'
    params = {  "N":12,
                "ke":0.3, 
                "ko":10,
                'fmax':0.05,
                'amp':1e-9, #perturbation amplitude
                "gamma": 0,#,0.022, #substrate friction
                "eta":.1,       #viscous damping
                "fcomp": 80,
                "tf":1000,"dt":5e-2,"pt":10,
                'outputpath':f'output/',
                'datapath':f'{foldername}/data/',
                'movpath':f'{foldername}/mov/',
                'pdfpath':f'{foldername}/pdf/',
                'defectpath':f'{foldername}/defectdata/',
                
                #initial conditions
                'rot angle':0,
                'shape':'superhexagon',  #'rectangle', 'superhexagon', 'disk','hexagonal annulus'
                
                #disk
                'circle_inner':10, #outer diameter in length units
                'circle_outer':20, #inner diameter in length units (0 for a full disk)
                
                #hexagonal annulus
                'd_annulus':7,
                
                
                'periodic':False, #NOT WORKING yet with constraints (TODO implement ghost cells)
                'perturb':'all',    #'all', 'edge' or 'none'
                'plot':False,
                'method':'constraint',
                'seed':3,           #random perturbation seed
                }
    return params