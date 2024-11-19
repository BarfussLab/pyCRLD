"""Class for environment with Renewable Ressources"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/Environments/13_EnvRenewableRessources.ipynb.

# %% auto 0
__all__ = ['RenewableRessources']

# %% ../../nbs/Environments/13_EnvRenewableRessources.ipynb 6
from .Base import ebase
from ..Utils.Helpers import make_variable_vector

from fastcore.utils import *
from fastcore.test import *

from typing import Iterable
import numpy as np
from scipy.stats import norm

# %% ../../nbs/Environments/13_EnvRenewableRessources.ipynb 7
class RenewableRessources(ebase):
    """
    Environment with Renewable Ressources.
    """ 
    def __init__(self, r, C, pR=0.1, obs=None, deltaE=0.2, sig=1.0):
        self.r = r    # regrowth rate
        self.C = C    # Capacity
        self.pR = pR  # recovery propbability in the case of depeletion

        self.N = 1  # starting with one agent, but this could be made adaptive
        self.M = 3  # 2 for now, but eventually three?
        self.Z = len(self._growth_dict())
        
        self.obs = obs
        
        self.dE = deltaE  # difference from max_sus_yield form low and high 
        self.sig = sig  # std of normal for state transitions
        
        self.T = self.TransitionTensor()
        self.R = self.RewardTensor()
        self.O = self.ObservationTensor()
        super().__init__()

# %% ../../nbs/Environments/13_EnvRenewableRessources.ipynb 8
@patch
def _growth(self:RenewableRessources, stock):
    return self.r * stock * (1 - stock / self.C)


# %% ../../nbs/Environments/13_EnvRenewableRessources.ipynb 9
@patch
def _growth_dict(self:RenewableRessources):
    gdic = {0: self._growth(0)}

    stock = 1
    while self._growth(stock) > 0:
        gdic[stock] = self._growth(stock)
        stock += 1

    return gdic


# %% ../../nbs/Environments/13_EnvRenewableRessources.ipynb 10
@patch
def _action_values(self:RenewableRessources):
    """
    What are the extraction levels corresponding to actions?
    TODO: To be adjusted when multi agent system is considered.
    """
    gdic = self._growth_dict()
    max_sus_yield = max(gdic.values())
    zer_extract = 0
    low_extract = (1-self.dE) * max_sus_yield
    hig_extract = (1+self.dE) * max_sus_yield
    return zer_extract, low_extract, hig_extract

# %% ../../nbs/Environments/13_EnvRenewableRessources.ipynb 11
@patch
def actions(self:RenewableRessources):
    z, l, h = self._action_values()
    return [0, 1, 2], ["0","low","high"]


# %% ../../nbs/Environments/13_EnvRenewableRessources.ipynb 12
@patch
def states(self:RenewableRessources):
    return [i for i in range(len(self._growth_dict()))]

# %% ../../nbs/Environments/13_EnvRenewableRessources.ipynb 13
@patch

def obs_action_space(self:RenewableRessources):
    return np.zeros((self.Q, self.M))


# %% ../../nbs/Environments/13_EnvRenewableRessources.ipynb 14
@patch
def TransitionTensor(self:RenewableRessources):
    """Get the Transition Tensor."""
    dim = np.concatenate(([self.Z],
                          [self.M for _ in range(self.N)],
                          [self.Z]))
    Tsas = np.ones(dim) * (-1)

    for index, _ in np.ndenumerate(Tsas):
        Tsas[index] = self._transition_probability(index[0],
                                                   index[1:-1],
                                                   index[-1])
    return Tsas

# %% ../../nbs/Environments/13_EnvRenewableRessources.ipynb 15
@patch
def _transition_probability(self:RenewableRessources, s, jA, sprim):
    acts = np.array(jA)
    act_vals = np.array(self._action_values())

    total_harvest = sum(act_vals[acts])
    harvest_stock = max(s - total_harvest, 0)
    new_stock = max(harvest_stock + self._growth(harvest_stock),
                    self._recoverP(jA))
    new_stock = min(new_stock, self.Z-1)

    # lower_state = int(new_stock)
    # upper_state = lower_state+1
    # uniform distribution between neigboring states
    # if sprim == lower_state:
    #     p = upper_state - new_stock
    # elif sprim == upper_state:
    #     p = new_stock - lower_state
    # else:
    #     p = 0
        
    # gaussian distribution with std `sig` around new_stock
    sig = self.sig
    
    if sprim == 0:  # minimum 
        p = norm.cdf(0.5, new_stock, sig)
    elif sprim == self.Z-1: # maximum
        p = 1 - norm.cdf(self.Z-1.5, new_stock, sig)
    else:
        p = norm.cdf(sprim+0.5, new_stock, sig)\
            - norm.cdf(sprim-0.5, new_stock, sig)
         
    return p

# %% ../../nbs/Environments/13_EnvRenewableRessources.ipynb 18
@patch

def _recoverP(self:RenewableRessources, jA):
    '''
    makes random recovery action dependent.
    It must pay of to choose low at degredation
    '''
    hig_recoverP = (1+self.dE) * self.pR
    low_recoverP = (1-self.dE) * self.pR
    zer_recoverP = 0
    
    recover_vals = np.array([hig_recoverP, low_recoverP, zer_recoverP])
    
    return recover_vals[jA].mean()

# %% ../../nbs/Environments/13_EnvRenewableRessources.ipynb 19
@patch

def RewardTensor(self:RenewableRessources):
    """Get the Reward Tensor R[i,s,a1,...,aN,s']."""
    dim = np.concatenate(([self.N],
                          [self.Z],
                          [self.M for _ in range(self.N)],
                          [self.Z]))
    Risas = np.zeros(dim)

    for index, _ in np.ndenumerate(Risas):
        Risas[index] = self._reward(index[0], index[1], index[2:-1],
                                    index[-1])
    return Risas

# %% ../../nbs/Environments/13_EnvRenewableRessources.ipynb 20
@patch

def ObservationTensor(self:RenewableRessources):
    
    if self.obs is None:
        self.obs = [[s] for s in range(self.Z)]
    self.Q = len(self.obs)
    
    dim = np.concatenate(([self.N],
                  [self.Z],
                  [self.Q]))
    Oiso = np.zeros(dim)

    for o in range(self.Q):
        for s in self.obs[o]:
            Oiso[:,s,o] = 1
            
    Oiso = Oiso / Oiso.sum(-1, keepdims=True)

    return Oiso

# %% ../../nbs/Environments/13_EnvRenewableRessources.ipynb 22
@patch

def _reward(self:RenewableRessources, i, s, jA, sprim):
    act_vals = np.array(self._action_values())
    reward = 0.1*act_vals[jA[i]] if s == 0 or sprim == 0\
        else act_vals[jA[i]]
    return reward

# %% ../../nbs/Environments/13_EnvRenewableRessources.ipynb 24
@patch
def id(self:RenewableRessources):
    """
    Returns id string of environment TODO
    """
    # Default
    def shorten(a): 
        return a
        
    r= shorten(self.r)
    C= shorten(self.C)

    id = f"{self.__class__.__name__}_"+\
        f"{self.N}_{str(r)}_{str(C)}"

    return id

# %% ../../nbs/Environments/13_EnvRenewableRessources.ipynb 26
from .RenewableRessources import RenewableRessources
from ..Agents.POStrategyActorCritic import POstratAC
import numpy as np
