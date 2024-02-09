# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/Agents/10_AStrategyBase.ipynb.

# %% auto 0
__all__ = ['strategybase']

# %% ../../nbs/Agents/10_AStrategyBase.ipynb 4
import numpy as np
import itertools as it
from functools import partial

# import jax
from jax import jit
import jax.numpy as jnp
from typing import Iterable
from fastcore.utils import *

from .Base import abase
from ..Utils.Helpers import *

# %% ../../nbs/Agents/10_AStrategyBase.ipynb 5
class strategybase(abase):
    """
    Base class for deterministic strategy-average independent (multi-agent)
    temporal-difference reinforcement learning in strategy space.        
    """
    
    def __init__(self,
                 env, # An environment object
                 learning_rates:Union[float, Iterable], # agents' learning rates
                 discount_factors:Union[float, Iterable], # agents' discount factors
                 choice_intensities:Union[float, Iterable]=1.0, # agents' choice intensities
                 use_prefactor=False,  # use the 1-DiscountFactor prefactor
                 opteinsum=True,  # optimize einsum functions
                 **kwargs):

        self.env = env
        Tt = env.T; assert np.allclose(Tt.sum(-1), 1)
        Rt = env.R    
        super().__init__(Tt, Rt, discount_factors, use_prefactor, opteinsum)
        self.F = jnp.array(env.F)

        # learning rates
        self.alpha = make_variable_vector(learning_rates, self.N)

        # intensity of choice
        self.beta = make_variable_vector(choice_intensities, self.N)

        
        self.TDerror = self.RPEisa
        
    @partial(jit, static_argnums=0)
    def step(self,
             Xisa  # Joint strategy
            ) -> tuple:  # (Updated joint strategy, Prediction error)
        """
        Performs a learning step along the reward-prediction/temporal-difference error
        in strategy space, given joint strategy `Xisa`.
        """
        TDe = self.TDerror(Xisa)
        n = jnp.newaxis
        XexpaTDe = Xisa * jnp.exp(self.alpha[:,n,n] * TDe)
        return XexpaTDe / XexpaTDe.sum(-1, keepdims=True), TDe
    
    @partial(jit, static_argnums=0)
    def reverse_step(self,
                    Xisa  # Joint strategy
                    ) -> tuple:  # (Updated joint strategy, Prediction error)
        """
        Performs a reverse learning step in strategy space,
        given joint strategy `Xisa`.
        
        This is useful to compute the separatrix of a multistable regime. 
        """
        TDe = self.TDerror(Xisa)
        n = jnp.newaxis
        XexpaTDe = Xisa * jnp.exp(self.alpha[:,n,n] * -TDe)
        return XexpaTDe / XexpaTDe.sum(-1, keepdims=True), TDe  

# %% ../../nbs/Agents/10_AStrategyBase.ipynb 9
@patch
def zero_intelligence_strategy(self:strategybase):
    """Returns strategy `Xisa` with equal action probabilities."""
    return jnp.ones((self.N, self.Z, self.M)) / float(self.M)

# %% ../../nbs/Agents/10_AStrategyBase.ipynb 10
@patch
def random_softmax_strategy(self:strategybase):
    """Returns softmax strategy `Xisa` with random action probabilities."""
    expQ = np.exp(np.random.randn(self.N, self.Z, self.M))
    X = expQ / expQ.sum(axis=-1, keepdims=True)
    return jnp.array(X)

# %% ../../nbs/Agents/10_AStrategyBase.ipynb 11
@patch
def id(self:strategybase
      ) -> str:  # id
    """Returns an identifier to handle simulation runs."""
    envid = self.env.id() + "__"
    agentsid = f"j{self.__class__.__name__}_"

    if hasattr(self, 'O') and hasattr(self, 'Q'):
        agentsid += 'PartObs_'        

    agentsid += f"{str(self.alpha)}_{str(self.gamma)}_{str(self.beta)}"\
        + f"pre{self.use_prefactor}"

    return envid + agentsid
