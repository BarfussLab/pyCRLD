# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/Agents/98_APOBase_commented.ipynb.

# %% auto 0
__all__ = ['aPObase']

# %% ../../nbs/Agents/98_APOBase_commented.ipynb 4
import jax
import numpy as np
import itertools as it

import jax.numpy as jnp
from jax import grad, jit, vmap
from functools import partial

from fastcore.utils import *

from .Base import abase
from ..Utils.Helpers import *

# %% ../../nbs/Agents/98_APOBase_commented.ipynb 5
class aPObase(abase):
    """
    Base class for
    deterministic policy-average (/ memory mean field) independent (multi-agent) 
    temporal-difference reinforcement learning with partial observability.

    To be used as a base for both, value and policy dynamics.
    """
    
    def __init__(self,
                 TransitionTensor,
                 RewardTensor,
                 ObservationTensor, 
                 DiscountFactors,
                 use_prefactor=False,
                 opteinsum=True,
                 **kwargs):
        """
        Parameters
        ----------
        TransitionTensor : transition model of the environment
        RewardTensor : reward model of the environment
        DiscountFactors : the agents' discount factors
        use_prefactor : use the 1-DiscountFactor prefactor (default: False)
        opteinsum : keyword argument to optimize einsum methods (default: True)
        """
        R = jnp.array(RewardTensor)
        T = jnp.array(TransitionTensor)
        O = jnp.array(ObservationTensor)
    
        # number of agents
        N = R.shape[0]  
        assert len(T.shape[1:-1]) == N, "Inconsistent number of agents"
        assert len(R.shape[2:-1]) == N, "Inconsistent number of agents"
        assert O.shape[0] == N, "Inconsistent number of agents"

        # number of actions for each agent        
        M = T.shape[1] 
        assert np.allclose(T.shape[1:-1], M), 'Inconsisten number of actions'
        assert np.allclose(R.shape[2:-1], M), 'Inconsisten number of actions'
        
        # number of states
        Z = T.shape[0] 
        assert T.shape[-1] == Z, 'Inconsisten number of states'
        assert R.shape[-1] == Z, 'Inconsisten number of states'
        assert R.shape[1] == Z, 'Inconsisten number of states'
        assert O.shape[1] == Z, 'Inconsistent number of states'

        # number of observations
        Q = O.shape[-1]
        
        self.R, self.T, self.O = R, T, O
        self.N, self.M, self.Z, self.Q = N, M, Z, Q
        
        # discount factors
        self.gamma = make_variable_vector(DiscountFactors, N)

        # use (1-DiscountFactor) prefactor to have values on scale of rewards
        self.pre = 1 - self.gamma if use_prefactor else np.ones(N)        
        self.use_prefactor = use_prefactor

        # 'load' the other agents actions summation tensor for speed
        self.Omega = self._OtherAgentsActionsSummationTensor()
        
        # state and obs distribution helpers
        self.has_last_statdist = False
        self._last_statedist = jnp.ones(Z) / Z
        self.has_last_obsdist = False
        self._last_obsdist = jnp.ones((N, Q)) / Q
        
        # use optimized einsum method
        self.opti = opteinsum  

   
    # =========================================================================
    #   Strategy averaging
    # =========================================================================
    @partial(jit, static_argnums=0)    
    def Xisa(self, X):
        """
        Compute state-action policy given the current observation-action policy
        """
        i = 0; a = 1; s = 2; o = 4  # variables
        args = [self.O, [i, s, o], X, [i, o, a], [i, s, a]]
        Xisa = jnp.einsum(*args, optimize=self.opti)
    
        # assert np.allclose(Xisa.sum(-1), 1.0), 'Not a policy. Must not happen!'
        return Xisa

    @partial(jit, static_argnums=0)
    def Tss(self, X):
        """Compute average transition model Tss given policy X"""
        Xisa = self.Xisa(X)
        return abase.Tss(self, Xisa)
    
    def Bios(self, X):
        """
        Compute 'belief' that environment is in stats s given agent i
        observes observation o (Bayes Rule)
        """
        pS = self.statedist(X)
        return self._bios(X, pS)
    
    @partial(jit, static_argnums=0)
    def _bios(self, X, pS):
        i, s, o = 0, 1, 2 # variables 

        b = jnp.einsum(self.O, [i,s,o], pS, [s], [i,s,o], optimize=self.opti)
        bsum = b.sum(axis=1, keepdims=True)
        bsum = bsum + (bsum == 0)  # to avoid dividing by zero
        Biso = b / bsum
        Bios = jnp.swapaxes(Biso, 1,-1)
        
        return Bios
        
    @partial(jit, static_argnums=0)
    def fast_Bios(self, X):
        """
        Compute 'belief' that environment is in stats s given agent i
        observes observation o (Bayes Rule)
        
        Unsafe when stationary state distribution is not unique
        (i.e., when policies are too extreme)
        """
        i, s, o = 0, 1, 2 # variables 
        # pS = self.statedist(X) # from full obs base (requires Tss from above)
        pS = self._jaxPs(X, self._last_statedist)

        b = jnp.einsum(self.O, [i,s,o], pS, [s], [i,s,o], optimize=self.opti)
        bsum = b.sum(axis=1, keepdims=True)
        bsum = bsum + (bsum == 0)  # to avoid dividing by zero
        Biso = b / bsum
        Bios = jnp.swapaxes(Biso, 1,-1)
        
        return Bios
    
    @partial(jit, static_argnums=0)    
    def Tioo(self, X, Bios=None, Xisa=None):
        """Compute average transition model Tioo, given joint policy X"""
        # For speed up
        Bios = self.fast_Bios(X) if Bios is None else Bios
        Xisa = self.Xisa(X) if Xisa is None else Xisa
        
        # variables 
        # agent i, state s, next state s_, observation o, next obs o', all acts
        i = 0; s = 1; s_ = 2; o = 3; o_ = 4; b2d = list(range(5, 5+self.N)) 

        Y4einsum = list(it.chain(*zip(Xisa,
                                      [[s, b2d[a]] for a in range(self.N)])))
        
        args = [Bios, [i, o, s]] + Y4einsum + [self.T, [s]+b2d+[s_],
                self.O, [i, s_, o_], [i, o, o_]]
        return jnp.einsum(*args, optimize=self.opti)
    
    @partial(jit, static_argnums=0)    
    def Tioao(self, X, Bios=None, Xisa=None):
        """Compute average transition model Tioao, given joint policy X"""
        # For speed up
        Bios = self.fast_Bios(X) if Bios is None else Bios
        Xisa = self.Xisa(X) if Xisa is None else Xisa
        
        # Variables
        # agent i, act a, state s, next state s_, observation o, next obs o_
        i = 0; a = 1; s = 2; s_ = 3; o = 4; o_ = 5;
        j2k = list(range(6, 6+self.N-1))  # other agents
        b2d = list(range(6+self.N-1, 6+self.N-1 + self.N))  # all actions
        e2f = list(range(5+2*self.N, 5+2*self.N + self.N-1))  # all other acts

        sumsis = [[j2k[l], s, e2f[l]] for l in range(self.N-1)]  # sum inds
        otherY = list(it.chain(*zip((self.N-1)*[Xisa], sumsis)))

        args = [self.Omega, [i]+j2k+[a]+b2d+e2f,
                Bios, [i, o, s]] + otherY + [self.T, [s]+b2d+[s_],
                self.O, [i, s_, o_], [i, o, a, o_]]
        return jnp.einsum(*args, optimize=self.opti)    
    
    @partial(jit, static_argnums=0)    
    def Rioa(self, X, Bios=None, Xisa=None):
        """Compute average reward Riosa, given joint policy X """
        # For speed up
        Bios = self.fast_Bios(X) if Bios is None else Bios
        Xisa = self.Xisa(X) if Xisa is None else Xisa
        
        # Variables
        # agent i, act a, state s, next state s_, observation o
        i = 0; a = 1; s = 2; s_ = 3; o = 4
        j2k = list(range(5, 5+self.N-1))  # other agents
        b2d = list(range(5+self.N-1, 5+self.N-1 + self.N))  # all actions
        e2f = list(range(4+2*self.N, 4+2*self.N + self.N-1))  # all other acts
 
        sumsis = [[j2k[l], s, e2f[l]] for l in range(self.N-1)]  # sum inds
        otherY = list(it.chain(*zip((self.N-1)*[Xisa], sumsis)))

        args = [self.Omega, [i]+j2k+[a]+b2d+e2f, Bios, [i, o, s]] +\
                otherY + [self.T, [s]+b2d+[s_], self.R, [i, s]+b2d+[s_],
                [i, o, a]]

        return jnp.einsum(*args, optimize=self.opti)
    
    @partial(jit, static_argnums=0)        
    def Rio(self, X, Bios=None, Xisa=None, Rioa=None):
        """Compute average reward Rio, given joint policy X"""       
        # For speed up
        if Rioa is None:  # Compute Rio from scratch
            Bios = self.fast_Bios(X) if Bios is None else Bios
            Xisa = self.Xisa(X) if Xisa is None else Xisa
            
            # Variables
            # agent i, state s, next state s_, observation o,  # all actions
            i = 0; s = 1; s_ = 2; o = 3; b2d = list(range(4, 4+self.N)) 
            
            Y4einsum = list(it.chain(*zip(Xisa,
                                    [[s, b2d[a]] for a in range(self.N)])))
            
            args = [Bios, [i, o, s]] + Y4einsum + [self.T, [s]+b2d+[s_],
                    self.R, [i, s]+b2d+[s_], [i, o]]
            return jnp.einsum(*args, optimize=self.opti)
        
        else:  # Compute Rio based on Rioa (should be faster by factor 20)
            i=0; o=1; a=2  # Variables
            args = [X, [i, o, a], Rioa, [i, o, a], [i, o]]
            return jnp.einsum(*args, optimize=self.opti)

    @partial(jit, static_argnums=0)        
    def Vio(self, X,
            Rio=None, Tioo=None, Bios=None, Xisa=None, Rioa=None,
            gamma=None):
        """Compute average observation values Vio, given joint policy X"""
        gamma = self.gamma if gamma is None else gamma 

        # For speed up
        Bios = self.fast_Bios(X) if Bios is None else Bios
        Xisa = self.Xisa(X) if Xisa is None else Xisa
        Rio = self.Rio(X, Bios=Bios, Xisa=Xisa, Rioa=Rioa) if Rio is None\
            else Rio
        Tioo = self.Tioo(X, Bios=Bios, Xisa=Xisa) if Tioo is None\
            else Tioo
        
        i = 0; o = 1; op = 2  # Variables
        n = np.newaxis
        Mioo = np.eye(self.Q)[n,:,:] - gamma[:, n, n] * Tioo
        invMioo = jnp.linalg.inv(Mioo)

        return self.pre[:,n] * jnp.einsum(invMioo, [i, o, op], Rio, [i, op],
                                          [i, o], optimize=self.opti)    

    @partial(jit, static_argnums=0)            
    def Qioa(self, X, Rioa=None, Vio=None, Tioao=None, Bios=None, Xisa=None,
             gamma=None):
        gamma = self.gamma if gamma is None else gamma 
        # For speed up
        Rioa = self.Rioa(X, Bios=Bios, Xisa=Xisa) if Rioa is None\
            else Rioa
        Vio = self.Vio(X, Bios=Bios, Xisa=Xisa, Rioa=Rioa) if Vio is None\
            else Vio        
        Tioao = self.Tioao(X, Bios=Bios, Xisa=Xisa) if Tioao is None\
            else Tioao

        nextQioa = jnp.einsum(Tioao, [0,1,2,3], Vio, [0,3], [0,1,2],
                             optimize=self.opti)
        n = np.newaxis
        return self.pre[:,n,n] * Rioa + gamma[:,n,n]*nextQioa    
    

    # =========================================================================
    #   HELPERS
    # =========================================================================
    @partial(jit, static_argnums=0)            
    def Ri(self, X):
        """Compute average reward Ri, given joint policy X""" 
        i, o = 0, 1
        return jnp.einsum(self.obsdist(X), [i, o], self.Rio(X), [i, o], [i])
    
    def obsdist(self, X):
        if self.has_last_obsdist:
            obsdist =  self._jobsdist(X, self._last_obsdist)
        else:
            obsdist = jnp.array(self._obsdist(X))
            self.has_last_obsdist = True
            
        self._last_obsdist = obsdist
        return obsdist

    @partial(jit, static_argnums=0)  
    def _jobsdist(self, X, pO0, rndkey=42):
        """Compute stationary distribution, given joint policy X"""
        Tioo = self.Tioo(X)
        Dio = jnp.zeros((self.N, self.Q))
        
        for i in range(self.N):
        
            pO = compute_stationarydistribution(Tioo[i])
            nrS = jnp.where(pO.mean(0)!=-10, 1, 0).sum()

            @jit
            def single_dist(pO):
                return jnp.max(jnp.where(pO.mean(0)!=-10,
                                         jnp.arange(pO.shape[0]), -1))
            @jit
            def multi_dist(pO):
                ix = jnp.argmin(jnp.linalg.norm(pO.T - pO0[i], axis=-1))
                return ix
            
            ix = jax.lax.cond(nrS == 1, single_dist, multi_dist, pO)

            Dio = Dio.at[i, :].set(pO[:, ix])

        return Dio
    
    def _obsdist(self, X):
        """Compute stationary distribution, given joint policy X"""
        Tioo = self.Tioo(X)
        Dio = np.zeros((self.N, self.Q))
        
        for i in range(self.N):
            pO = np.array(compute_stationarydistribution(Tioo[i]))
        
            pO = pO[:, pO.mean(0)!=-10]
            if len(pO[0]) == 0:  # this happens when the tollerance can distin.
                assert False, 'No _statdist return - must not happen'
            elif len(pO[0]) > 1:  # Should not happen, in an ideal world
                # sidenote: This means an ideal world is ergodic ;)
                print("More than 1 state-eigenvector found")
                print(pO.round(2))
                nr = len(pO[0])
                choice = np.random.randint(nr)
                print("taking random one: ", choice)
                pO = pO[:, choice]
                        
            Dio[i] = pO.flatten()

        return Dio
    # ===================
    # ======================================================
    #   Additional state based averages
    # =========================================================================
    @partial(jit, static_argnums=0)  
    def Tisas(self, X):
        """Compute average transition model Tisas, given joint policy X"""      
        Xisa = self.Xisa(X)
        return super().Tisas(Xisa)

    @partial(jit, static_argnums=0)  
    def Risa(self, X):
        """Compute average reward Risa, given joint policy X"""
        Xisa = self.Xisa(X)
        return super().Risa(Xisa)

    @partial(jit, static_argnums=0)  
    def Ris(self, X, Risa=None):
        """Compute average reward Ris, given joint policy X""" 
        Xisa = self.Xisa(X)
        return super().Ris(Xisa, Risa=Risa)
    
    @partial(jit, static_argnums=0)  
    def Vis(self, X, Ris=None, Tss=None, Risa=None):
        """Compute average state values Vis, given joint policy X"""
        Xisa = self.Xisa(X)
        Ris = self.Ris(X) if Ris is None else Ris
        Tss = self.Tss(X) if Tss is None else Tss
        return super().Vis(Xisa, Ris=Ris, Tss=Tss, Risa=Risa)

    @partial(jit, static_argnums=0)  
    def Qisa(self, X, Risa=None, Vis=None, Tisas=None):
        """Compute average state-action values Qisa, given joint policy X"""
        Xisa = self.Xisa(X)
        Risa = self.Risa(X) if Risa is None else Risa
        Vis = self.Vis(X) if Vis is None else Vis
        Tisas = self.Tisas(X) if Tisas is None else Tisas
        return super().Qisa(Xisa, Risa=Risa, Vis=Vis, Tisas=Tisas)

