from frgmapper.mapper import control
import np as numpy

wave=np.linspace(1700,2000,151,dtype=int)
wave=wave.tolist()

c = control()
c.connect()
c.connectStage()
c.takeBaseline(wave)
input('Place stage on integrating sphere: press enter to scan')
c.takeScan("test",wave,True,False,False) # green stage
input('Place mini module on sphere: press enter to scan')
c.takeScan("test",wave,True,False,False) # minimodule
input('Test completed: press enter to finish')