from math import pi, exp
import numpy as np

def inj(t):
    return ((t>1000 and t<2500) or (t>3500 and t<5500))*0.000005#*(sin(t/(2*pi*10)+1))

class PBLIF:
    """A Pulse Based Leaky Integrate and Fire model"""
    def __init__(self):
        # Initial State of variables
        # t, Vd, Vs
        self.t=[0]
        self.V=[[0,0]]
        # default time parameters
        self.dt=0.1 # ms
        self.tstop=2000 #ms
        # m,h,n,q
        self.m=[0]
        self.h=[0]
        self.n=[0]
        self.q=[0]
        # Ion Currents Over Tie
        self.INa=[0]
        self.IKf=[0]
        self.IKs=[0]
        # values for analytical solution to pulse based ODEs
        self.t0=0
        self.m0=0
        self.h0=0
        self.n0=0
        self.q0=0
        # Gate pulse parameters
        self.AM=22    # ms^-1
        self.BM=13    # ms^-1
        self.AH=0.5   # ms^-1
        self.BH=4     # ms^-1
        self.AN=1.5   # ms^-1
        self.BN=0.1   # ms^-1
        self.AQ=1.5   # ms^-1
        self.BQ=0.025 # ms^-1

        # Physical Dimensions and Measures
        ### Dendrite
        # Radius
        self.rd  = 50/2 # (41.5-62.5)/2 um
        self.rd/=10000  # convert to cm
        # Length
        self.ld  = 6000 # 5519-6789 um
        self.ld/=10000  # convert to cm
        # Resistance
        self.Rmd = 12000 # 10650-14350 Ohm cm^2
        ### Soma
        # Radius
        self.rs  = 80/2 # (77.5-82.5)/2 um
        self.rs/=10000  # convert to cm
        # Length
        self.ls  = 80 # 77.5-82.5 um
        self.ls/=10000  # convert to cm
        # Resistance
        self.Rms = 1100 # 1050-1150 Ohm cm^2
        ### Cytoplasm
        # Resistance
        self.Ri  = 70 # 70 Ohm cm
        
        # Conductances
        ### Dendrite
        self.gld = (2*pi*self.rd*self.ld)/(self.Rmd) # Ohm^-1
        ### Soma
        self.gls = (2*pi*self.rs*self.ls)/(self.Rms) # Ohm^-1
        ### Coupling
        self.gc =  2/( ((self.Ri*self.ld)/(pi*self.rd**2)) +\
                       ((self.Ri*self.ls)/(pi*self.rs**2)) )  # Ohm^-1
        ### Sodium
        self.gNa = 30 # mS/cm^2
        ### Potassium
        self.gKf = 4  # mS/cm^2
        self.gKs = 16 # mS/cm^2
        #### UNIT SCALING
        ### Sodium
        self.gNa/=10000000 # mS/cm^2
        ### Potassium
        self.gKf/=10000000 # mS/cm^2
        self.gKs/=10000000 # mS/cm^2
        
        # Capacitances
        ### Membrane Capacitance
        self.Cm = 1  # uF/cm^2
        self.Cm/=1e3 # convert to milliFarad
        ### Dendrite Capacitance
        self.Cd = 2*pi*self.rd*self.ld*self.Cm # mF
        ### Soma Capacitance
        self.Cs = 2*pi*self.rs*self.ls*self.Cm # mF
        # Equilibrium Potentials
        ### Leak
        self.El = 0 # mV
        ### Sodium
        self.ENa = 120 #mV
        ### Potassium
        self.EK = -10 #mV

        # Inputs
        ### Injected
        self.Iinj_d = inj
        self.Iinj_s = lambda t: 0
        ### Synaptic
        self.Isyn_d=0
        self.Isyn_s=0

        # Rheo and Threshold
        self.rheo = 4 # 3.5-6.5 nA
        self.rheo/= 1000000 # Convert to milliamp
        self.rn   = 1/(self.gld + (self.gls * self.gc)/(self.gls + self.gc))
        self.threshold = self.rheo*self.rn # Threshold in mV/cm^2
        ### Pulse state
        self.pulseState = False
    def ddt(self,slope,t,V):
        # V[0] = dendrite voltage
        # V[1] = Soma Voltage
        def changeState():
            self.t0=t
            self.m0=self.m[-1]
            self.h0=self.h[-1]
            self.n0=self.n[-1]
            self.q0=self.q[-1]
            self.pulseState = not self.pulseState

        def gateVal(alpha,beta,v0,pulse):
            # public double getValueOn(double t) 
    	    # value = v0 * Math.exp(-beta*(t - t0));
            # public double getValueOff(double t) 
    	    # value = 1 + (v0 - 1) * Math.exp(-alpha*(t - t0));
            ret=0;
            if (pulse):
                ret = v0 * exp(-beta*(t - self.t0));
            else:
                ret = 1 + (v0 - 1) * exp(-alpha*(t - self.t0));
            return ret
        if (slope==1):
            if (V[1]>self.threshold and not self.pulseState):
                changeState()
                
            if (self.pulseState):
                if (t-self.t0 > 0.6):
                    changeState()

        m = gateVal(self.AM,self.BM,self.m0,not self.pulseState)
        h = gateVal(self.AH,self.BH,self.h0,    self.pulseState)
        n = gateVal(self.AN,self.BN,self.n0,not self.pulseState)
        q = gateVal(self.AQ,self.BQ,self.q0,not self.pulseState)

        iNa = self.gNa * m**3 * h * (V[1]-self.ENa)
        iKf = self.gKf * n**4 * (V[1]-self.EK)
        iKs = self.gKs * q**2 * (V[1]-self.EK)
        Iion = iNa + iKf + iKs
        
        if (slope==1):
            # m,h,n,q
            self.m.append(m)
            self.h.append(h)
            self.n.append(n)
            self.q.append(q)
            # Currents over time
            if (iNa>1e50):
                print(f"{self.gNa} * {m**3} * {h} * ({V[1]}-{self.ENa})")
            self.INa.append(iNa)
            self.IKf.append(iKf)
            self.IKs.append(iKs)

        dVdt = np.array([
            (-self.Isyn_d-self.gld*(V[0]-self.El)-self.gc*(V[0]-V[1])+self.Iinj_d(t))/self.Cd,
            (-self.Isyn_s-self.gls*(V[1]-self.El)-self.gc*(V[1]-V[0])-Iion+self.Iinj_s(t))/self.Cs
        ])
    
        return dVdt
        
    def rk4Step(self):
        k1 = self.dt * self.ddt(1,self.t[-1], self.V[-1])
        k2 = self.dt * self.ddt(2,self.t[-1] + 0.5 * self.dt, self.V[-1] + 0.5 * k1)
        k3 = self.dt * self.ddt(3,self.t[-1] + 0.5 * self.dt, self.V[-1] + 0.5 * k2)
        k4 = self.dt * self.ddt(4,self.t[-1] + self.dt, self.V[-1] + k3)
    
        V = self.V[-1] + (1.0 / 6.0)*(k1 + 2 * k2 + 2 * k3 + k4)
        
        t = self.t[-1] + self.dt

        self.V.append(V)
        self.t.append(t)

    
