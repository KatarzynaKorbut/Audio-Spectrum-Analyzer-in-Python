import numpy as np
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg

import struct
import pyaudio
from scipy.signal import welch

import sys


class AudioStream(object):
    FORMAT = pyaudio.paInt16
    FORMAT_BITS = 16
    CHANNELS = 1
    RATE = 44100
    CHUNK = 1024 * 4
    WF_Y_MAX = 2 ** (FORMAT_BITS - 3)
    NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "H"]

    def __init__(self):
        self.app = QtGui.QApplication(sys.argv)
        self.win = pg.GraphicsWindow(title="Spectrum Analyzer")
        self.win.setWindowTitle("Spectrum Analyzer")

        self.prepare_plots()
        self.prepare_audio()

        # waveform and spectrum x points
        self.x = np.arange(0, self.CHUNK)
        self.f = np.linspace(0, self.RATE / 2, self.CHUNK // 2)

    def piano_key_to_note(self, key):
        # key octave semitone
        #   0     -3        9
        #   1     -3       10
        #   2     -3       11
        #   3     -2        0
        #   4     -2        1
        #  27      0        0
        #  28      0        1
        #  29      0        2
        return (key - 27) // 12, (key - 27) % 12

    def note_to_freq(self, octave, semitone):
        """Zamiana oktawy i półtonu na częśtotliwość dźwięku
        octave == 1 --> oktawa razkreślna
        semitone == 0 --> dźwięk C
        """
        freq = 440.0 * 2 ** ((semitone - 9) / 12)
        freq *= 2 ** (octave - 1)
        return freq

    def note_to_description(self, octave, semitone):
        return f"{self.NOTE_NAMES[semitone]}{octave}"

    def prepare_plots(self):
        # pyqtgraph stuff
        pg.setConfigOptions(antialias=True)
        self.traces = dict()

        wf_xlabels = [(0, "0"), (2048, "2048"), (4096, "4096")]
        wf_xaxis = pg.AxisItem(orientation="bottom")
        wf_xaxis.setTicks([wf_xlabels])

        wf_yaxis = pg.AxisItem(orientation="left")
        wf_yaxis.setTicks(
            [
                [
                    (2 ** (self.FORMAT_BITS - 1) * v / 10, f"{10*v}%")
                    for v in range(-10, 11)
                ]
            ]
        )

        sp_xlabels = []
        for key in range(88):
            octave, semitone = self.piano_key_to_note(key)
            freq = self.note_to_freq(octave, semitone)
            description = self.note_to_description(octave, semitone)
            if self.NOTE_NAMES[semitone] in ("C", "E", "A"):
                sp_xlabels.append((np.log10(freq), description))

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
                self.waveform.setYRange(-self.WF_Y_MAX, self.WF_Y_MAX, padding=0)
                self.waveform.setXRange(0, self.CHUNK, padding=0.005)
            if name == "spectrum":
                self.traces[name] = self.spectrum.plot(pen="m", width=3)
                self.spectrum.setLogMode(x=True, y=False)
                # self.spectrum.setYRange(0, 2 * self.WF_Y_MAX, padding=0)
                self.spectrum.setXRange(
                    np.log10(20), np.log10(self.RATE / 2), padding=0.005
                )

    def update(self):
        wf_data = self.stream.read(self.CHUNK)
        wf_data = struct.unpack(f"{self.CHUNK}h", wf_data)
        wf_data = np.array(wf_data)

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
