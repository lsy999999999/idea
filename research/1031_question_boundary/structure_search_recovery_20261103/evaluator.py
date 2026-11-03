"""Organizer-only simulator for the SAME development case; never sent to Luna."""
import numpy as np


def observation(row):
    memory = np.sum(np.array(row['history'])*np.exp(np.array(row['times'])/2.2))*row['dt']
    return float(.7*row['u']+.3*row['u']**3+.8*memory*np.exp(-row['h']/2.2))


def acquire(designs, seed, repeats=4):
    rng = np.random.default_rng(seed)
    return [dict(r, repeat=k, o=observation(r)+float(rng.uniform(-.015,.015))) for r in designs for k in range(repeats)]


def hidden():
    rng = np.random.default_rng(3103101)
    designs = [dict(u=float(rng.uniform(-1.1,1.1)), h=float(rng.uniform(0,2.5)),
                    history=rng.uniform(-1,1,4).tolist(), times=[-4.,-3.,-2.,-1.], dt=1.) for _ in range(160)]
    return acquire(designs,3103102,1)
