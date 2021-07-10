import numpy as np
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg

import struct
import pyaudio
from scipy.fftpack import fft
from scipy.signal import welch

import sys
import time


class AudioStream(object):
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    CHUNK = 1024 * 4
    def __init__(self):

        self.app = QtGui.QApplication(sys.argv)
        self.win = pg.GraphicsWindow(title="Spectrum Analyzer")
        self.win.setWindowTitle("Spectrum Analyzer")
        self.win.setGeometry(0, 0, 1910, 1070)

        self.prepare_plots()
        self.prepare_audio()

        # waveform and spectrum x points
        self.x = np.arange(0, 2 * self.CHUNK, 2)
        self.f = np.linspace(0, self.RATE / 2, self.CHUNK // 2)

    def prepare_plots(self):
        # pyqtgraph stuff
        pg.setConfigOptions(antialias=True)
        self.traces = dict()

        wf_xlabels = [(0, "0"), (2048, "2048"), (4096, "4096")]
        wf_xaxis = pg.AxisItem(orientation="bottom")
        wf_xaxis.setTicks([wf_xlabels])

        wf_ylabels = [(0, "0"), (127, "128"), (255, "255")]
        wf_yaxis = pg.AxisItem(orientation="left")
        wf_yaxis.setTicks([wf_ylabels])

        sp_xlabels = [
            (np.log10(10), "10"),
            (np.log10(100), "100"),
            (np.log10(1000), "1000"),
            (np.log10(22050), "22050"),
        ]
        sp_xaxis = pg.AxisItem(orientation="bottom")
        sp_xaxis.setTicks([sp_xlabels])

        self.waveform = self.win.addPlot(
            title="WAVEFORM",
            row=1,
            col=1,
            axisItems={"bottom": wf_xaxis, "left": wf_yaxis},
        )
        self.spectrum = self.win.addPlot(
            title="SPECTRUM", row=2, col=1, axisItems={"bottom": sp_xaxis},
        )

    def prepare_audio(self):
        # pyaudio stuff
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            output=True,
            frames_per_buffer=self.CHUNK,
        )

    def start(self):
        if (sys.flags.interactive != 1) or not hasattr(QtCore, "PYQT_VERSION"):
            QtGui.QApplication.instance().exec_()

    def set_plotdata(self, name, data_x, data_y):
        if name in self.traces:
            self.traces[name].setData(data_x, data_y)
        else:
            if name == "waveform":
                self.traces[name] = self.waveform.plot(pen="c", width=3)
                self.waveform.setYRange(0, 255, padding=0)
                self.waveform.setXRange(0, 2 * self.CHUNK, padding=0.005)
            if name == "spectrum":
                self.traces[name] = self.spectrum.plot(pen="m", width=3)
                self.spectrum.setLogMode(x=True, y=True)
                self.spectrum.setYRange(-4, 0, padding=0)
                self.spectrum.setXRange(
                    np.log10(20), np.log10(self.RATE / 2), padding=0.005
                )

    def update(self):
        wf_data = self.stream.read(self.CHUNK)
        wf_data = struct.unpack(str(2 * self.CHUNK) + "B", wf_data)
        wf_data = np.array(wf_data, dtype="b")[::2]

        # N = self.CHUNK
        # amp = 2 * np.sqrt(2)
        # freq = 1000.0
        # time = np.arange(N) / self.RATE
        # wf_data = amp * np.sin(2 * np.pi * freq * time)

        self.set_plotdata(
            name="waveform", data_x=self.x, data_y=wf_data,
        )

        # sp_data = fft(np.array(wf_data, dtype="int8"))
        # sp_data = fft(wf_data)
        f, sp_data = welch(wf_data, scaling="spectrum", nperseg=self.CHUNK // 3)

        # sp_data = np.abs(sp_data[0 : int(self.CHUNK / 2)]) * 2 / (128 * self.CHUNK)
        self.set_plotdata(name="spectrum", data_x=f * self.RATE, data_y=sp_data / 5)

    def animation(self):
        timer = QtCore.QTimer()
        timer.timeout.connect(self.update)
        timer.start(20)
        self.start()


if __name__ == "__main__":

    audio_app = AudioStream()
    audio_app.animation()
