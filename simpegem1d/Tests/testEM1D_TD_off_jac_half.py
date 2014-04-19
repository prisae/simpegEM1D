import unittest
from SimPEG import *
import matplotlib.pyplot as plt
from simpegem1d import EM1D, EM1DAnal, BaseEM1D


class EM1D_TD_Jac_half_ProblemTests(unittest.TestCase):

    def setUp(self):

        TDsurvey = BaseEM1D.EM1DSurveyTD()
        TDsurvey.rxLoc = np.array([0., 0., 100.+50.])
        TDsurvey.txLoc = np.array([0., 0., 100.+50.])
        TDsurvey.fieldtype = 'secondary'
        # TDsurvey.rxType = 'Bz'
        TDsurvey.rxType = 'dBzdt'
        TDsurvey.waveType = 'stepoff'

        nearthick = np.logspace(-1, 1, 2)
        deepthick = np.logspace(1, 2, 5)
        hx = np.r_[nearthick, deepthick]

        mesh1D = Mesh.TensorMesh([hx], [0.])
        depth = -mesh1D.gridN
        LocSigZ = -mesh1D.gridCC
        nlay = depth.size
        topo = np.r_[0., 0., 100.]
        TDsurvey.depth = depth
        TDsurvey.topo = topo
        TDsurvey.LocSigZ = LocSigZ
        TDsurvey.time = np.logspace(-5, -2, 64)
        TDsurvey.switchInterp = True
        TDsurvey.setFrequency(TDsurvey.time)
        TDsurvey.HalfSwitch = True
        TDsurvey.Setup1Dsystem()

        sig_half = 1e-1
        chi_half = 0.

        expmap = BaseEM1D.BaseEM1DMap(mesh1D)
        tau = 1e-3
        eta = 2e-1
        c = 1.
        options = {'Frequency': TDsurvey.frequency, 'tau': np.ones(nlay)*tau, 'eta':np.ones(nlay)*eta, 'c':np.ones(nlay)*c}
        colemap = BaseEM1D.BaseColeColeMap(mesh1D, **options)

        modelReal = Maps.ComboMap(mesh1D, [expmap])
        modelComplex = Maps.ComboMap(mesh1D, [colemap, expmap])
        m_1D = np.log(np.ones(nlay)*sig_half)

        WT0 = np.load('../WT0.npy')
        WT1 = np.load('../WT1.npy')
        YBASE = np.load('../YBASE.npy')
        options = {'WT0': WT0, 'WT1': WT1, 'YBASE': YBASE}

        prob = EM1D.EM1D(mesh1D, modelReal, **options)
        prob.pair(TDsurvey)
        prob.chi = np.zeros(TDsurvey.nlay)


        self.survey = TDsurvey
        self.options = options
        self.modelReal = modelReal
        self.prob = prob
        self.mesh1D = mesh1D
        self.showIt = False


    def test_EM1DTDJvec_Half(self):
        self.prob.CondType = 'Real'
        self.prob.survey.txType = 'CircularLoop'

        I = 1e0
        a = 1e1
        self.prob.survey.I = I
        self.prob.survey.a = a

        sig_half = 0.01
        sig = np.ones(self.prob.survey.nlay)*sig_half
        m_1D = np.log(sig)

        self.prob.jacSwitch = True
        Hz, dHzdsig = self.prob.fields(m_1D)

        dsigdm = self.prob.mapping.transformDeriv(m_1D)
        dHzdsig = dHzdsig

        def fwdfun(m):
            self.prob.jacSwitch = False
            Hz = self.prob.fields(m)
            resp = self.prob.survey.projectFields(u=Hz)
            return resp
            # return Hz

        def jacfun(m, dm):
            self.prob.jacSwitch = True
            u = self.prob.fields(m)
            drespdmv = self.prob.Jvec(m, dm, u = u)
            return drespdmv



        dm = m_1D*0.5
        derChk = lambda m: [fwdfun(m), lambda mx: jacfun(m, mx)]
        passed = Tests.checkDerivative(derChk, m_1D, num=4, dx = dm, plotIt=False, eps = 1e-15)

        if passed:
            print "EM1DTD-half Jvec works"

    def test_EM1DTDJtvec_Half(self):
        self.prob.CondType = 'Real'
        self.prob.survey.txType = 'CircularLoop'

        I = 1e0
        a = 1e1
        self.prob.survey.I = I
        self.prob.survey.a = a

        sig_half = np.r_[0.01]
        self.prob.jacSwitch = False
        m_true = np.log(np.ones(self.prob.survey.nlay)*sig_half)
        Hz_true = self.prob.fields(m_true)
        dobs = self.prob.survey.projectFields(u=Hz_true)

        m_ini  = np.log(np.ones(self.prob.survey.nlay)*sig_half*10)
        Hz_ini = self.prob.fields(m_ini)
        resp_ini = self.prob.survey.projectFields(u=Hz_ini)
        dr = resp_ini-dobs

        def misfit(m, dobs):
            self.prob.jacSwitch = True
            Hz = self.prob.fields(m)
            dpred = self.survey.dpred(m, u = Hz)
            misfit = 0.5*np.linalg.norm(dpred-dobs)**2
            dmisfit = self.prob.Jtvec(m, dr, u = Hz)
            return misfit, dmisfit


        derChk = lambda m: misfit(m, dobs)
        passed = Tests.checkDerivative(derChk, m_ini, num=4, plotIt=False, eps = 1e-26)
        self.assertTrue(passed)
        if passed:
            print "EM1DFD-half Jtvec works"

if __name__ == '__main__':
    unittest.main()