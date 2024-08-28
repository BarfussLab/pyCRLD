# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/Environments/13_EnvRiskReward.ipynb.

# %% auto 0
__all__ = ['RiskReward']

# %% ../../nbs/Environments/13_EnvRiskReward.ipynb 5
from .Base import ebase
from ..Utils.Helpers import make_variable_vector

from fastcore.utils import *
from fastcore.test import *

import numpy as np

# %% ../../nbs/Environments/13_EnvRiskReward.ipynb 6
class RiskReward(ebase):
    """
    An MDP model for decision-making under uncertainty with two states 
    (prosperous and degraded) and two actions (cautious and risky).
    """
    
    def __init__(self, pc, pr, rs, rr, rd):
        self.pc = pc  # Collapse probability when risky in prosperous
        self.pr = pr  # Recovery probability when cautious in degraded
        self.rs = rs  # Reward for staying prosperous and cautious
        self.rr = rr  # Reward for staying prosperous but risky
        self.rd = rd  # Reward when in degraded state
        
        self.N = 1  # Number of agents
        self.M = 2  # Number of actions
        self.Z = 2  # Number of states
        self.state = 0  # Start in the prosperous state (index 0)
        
        super().__init__()

   

# %% ../../nbs/Environments/13_EnvRiskReward.ipynb 7
@patch
def TransitionTensor(self:RiskReward):
        """
        Define the Transition Tensor for the MDP.
        """
        T = np.zeros((self.Z, self.M, self.Z))
        T[0, 0, 0] = 1       # Prosperous and cautious stays prosperous
        T[0, 1, 0] = 1 - self.pc  # Prosperous and risky may stay
        T[0, 1, 1] = self.pc      # Prosperous and risky may collapse
        T[1, 0, 0] = self.pr      # Degraded and cautious may recover
        T[1, 0, 1] = 1 - self.pr  # Degraded and cautious may stay
        T[1, 1, 1] = 1       # Degraded and risky stays degraded
        return T




# %% ../../nbs/Environments/13_EnvRiskReward.ipynb 8
@patch
def RewardTensor(self:RiskReward):
        """
        Define the Reward Tensor for the MDP.
        """
        R = np.zeros((self.N, self.Z, self.M, self.Z))
        R[0, 0, 0, 0] = self.rs  # Prosperous and cautious
        R[0, 0, 1, 0] = self.rr  # Prosperous and risky but stays
        R[0, 0, 1, 1] = self.rd  # Prosperous and risky but collapses
        R[0, 1, :, 1] = self.rd  # Degraded state rewards
        return R



# %% ../../nbs/Environments/13_EnvRiskReward.ipynb 9
@patch
def actions(self:RiskReward):
        """
        Define the actions available in the MDP.
        """
        return [['cautious', 'risky']]



# %% ../../nbs/Environments/13_EnvRiskReward.ipynb 10
@patch
def states(self:RiskReward):
        """
        Define the states of the MDP.
        """
        return ['prosperous', 'degraded']



# %% ../../nbs/Environments/13_EnvRiskReward.ipynb 11
@patch
def id(self:RiskReward):
        """
        Provide an identifier for the environment.
        """
        return f"{self.__class__.__name__}_pc{self.pc}_pr{self.pr}_rs{self.rs}_rr{self.rr}_rd{self.rd}"
