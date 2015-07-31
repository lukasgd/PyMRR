# -*- coding: utf-8 -*-
"""
Created on Thu May 21 15:18:56 2015

@author: Sebastian Theilenberg
"""


import math
from scipy import odr
import numpy as np
import matplotlib.pyplot as plt
from warnings import warn
import pickle


class Calibrate(object):

    def __init__(self, x=None, y=None, dx=None, dy=None):
        if np.any(x):
            if not np.any(y):
                raise ValueError("no y-values provided!")
            self._x = np.asarray(x)
            self._xm = self._x.mean()
            _len = len(x)
            assert len(y) == _len
            self._y = np.asarray(y)
        if dx is not None:
            assert len(dx) == _len
            self._dx = np.asarray(dx)
        if dy is not None:
            assert len(dy) == _len
            self._dy = np.asarray(dy)
        self.result = None

    def __call__(self, x, std=False):
        self._has_run()
        y = self._func_values(x)
        if std:
            err = self._func_err(x)
            return y, err
        return y

    def save(self, filename):
        self._has_run()
        with open(filename, 'wb') as f:
            pickle.dump(self.result, f)

    def load(self, filename):
        with open(filename, 'rb') as f:
            self.result = pickle.load(f)

    def _has_run(self):
        if self.result is None:
            raise AttributeError("No calibration present. Run Calibrate.run()"
                                 "first")

    def _linear(self, P, x):
        "Linear function of regression."
        return P[0]*x + P[1]

    def _func_values(self, x):
        "Returns the calibrated values f(x) as np.array."
        x = np.array(x)
        m, n = self.result.beta
        return x*m + n

    def _func_err(self, x):
        x = np.asarray(x)
        dm, dn = self.result.sd_beta
        return np.sqrt(dm**2.*(x-self._xm)**2. + dn**2.)

    def run(self):
        Model = odr.Model(self._linear)
        Data = odr.RealData(self._x, self._y,	sx=self._dx, sy=self._dy)
        initial = self._initial_guess()
        solver = odr.ODR(Data, Model, initial)
        self.result = solver.run()
        return self.result.beta, self.result.sd_beta

    def _initial_guess(self):
        dy = self._y.max() - self._y.min()
        dx = self._x.max() - self._x.min()
        return (dy/dx, self._y[0] - self._x[0]*dy/dx)

    def plot(self, title=None, annotation=True):
        self._has_run()
        # find values
        t_ = np.linspace(self._x.min() - 20, self._x.max(), 100)
        err = self._func_err(t_)
        y = self._func_values(t_)

        plt.figure()
        if title is not None:
            plt.title(title)
        plt.minorticks_on()
        # plot margin
        plt.fill_between(t_, y - err, y + err, alpha=0.2, color='teal')
        # plot function
        plt.plot(t_, y, color='teal')
        # plot measurement values
        plt.errorbar(self._x, self._y, yerr=self._dy, xerr=self._dx,
                     ls='none', color='blue')
        # adjust xlim
        if plt.xlim()[0] < 0:
            plt.xlim(xmin=0)
        # labels
        plt.xlabel(r"$U\,\,\left[\si{\milli\volt}\right]$")
        plt.ylabel(r"$x\,\,\left[\si{\milli\meter}\right]$")
        # add function
        if annotation:
            # check latex settings
            if plt.rcParams["text.usetex"] is True:
                if ("\usepackage{siunitx}"
                        not in plt.rcParams["text.latex.preamble"]):
                    warn("Matplotlib.pyplot not fully configured to use"
                         "tex with siunitx. Add '\usepackage{siunitx}'"
                         "to rcParams['text.latex.preambel']",
                         UserWarning)
                else:
                    annotation = self._create_annotation()
                    plt.annotate(annotation, xy=(0.08, 0.82),
                                 xycoords="axes fraction")

    def _create_annotation(self):
        m, h = self.result.beta
        dm, dh = self.result.sd_beta
        # find precisions of last relevant decimal
        precisions = [int(math.floor(-math.log10(x)) + 1) for x in [dm, dh]]
        # calculate the decimals of the errors at these positions
        err = [int(round(x*10**precisions[i])) for i, x in enumerate([dm, dh])]
        # correct for rounding 0.09 to 0.1
        for i in range(2):
            if err[i] > 9:
                err[i] /= 10
                precisions[i] -= 1
        # create annotation string
        annotation = (r"$x = \SI{{{0:.{4}f}+-{1:.{4}f}}}"
                      "{{\milli\meter\per\milli\\volt}}\cdot U"
                      "+ \SI{{{2:.{5}f}+-{3:.{5}f}}}{{\milli\meter}}$"
                      ).format(m, dm, h, dh, *precisions)

        return annotation
