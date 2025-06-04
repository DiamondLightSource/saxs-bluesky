import numpy as np
from scipy import signal
import matplotlib.pyplot as plt

import bluesky.plan_stubs as bps
import bluesky.plans as bp
from bluesky.protocols import Movable

from ophyd_async.epics.motor import Motor
from ophyd_async.epics.signal import epics_signal_r, epics_signal_rw

from bluesky import RunEngine


from ophyd_async.core import StandardReadable
from ophyd_async.epics.motor import Motor

from dodal.log import set_beamline as set_log_beamline
from dodal.utils import BeamlinePrefix, get_beamline_name, skip_device
from dodal.common.beamlines.beamline_utils import set_beamline as set_utils_beamline

import asyncio



class base_top(StandardReadable):
    """Physical motion for sample stage travel"""


    def __init__(self, prefix: str, name: str = "") -> None:

        #Motor has the bases 
        #Bases: StandardReadable, Movable, Stoppable, Flyable, Preparable

        BASE_PREFIX = prefix+"-MO-STABL-01:"

        self.x_motor = Motor(BASE_PREFIX + "X")  # x position of base table
        self.y_motor = Motor(BASE_PREFIX + "Y")  # y position of base table
        self.pitch_motor = Motor(BASE_PREFIX + "PITCH")  # pitch position of base table

        self.motors = {"X": self.x_motor, "Y": self.y_motor, "PITCH": self.pitch_motor}

        super().__init__(name)


    async def get_current_pos(self, axis: str):

        axis = axis.upper() # make it uppercase if the user hasn't

        axis_motor = self.motors[axis]

        reading = await axis_motor.user_readback.get_value()

        return reading



def center_sample(start: float, stop: float, n_steps: int, axis: str, 
                 exposure: float = 0.1, 
                 plot: bool = False):

    axis = axis.upper() # make it uppercase if the user hasn't

    BL = get_beamline_name("i22")
    set_log_beamline(BL)
    set_utils_beamline(BL)

    beamline_prefix = BeamlinePrefix(BL).beamline_prefix
    I22_base_top = base_top(beamline_prefix)
    current_pos = I22_base_top.get_current_pos(axis)

    print(current_pos)
    quit()

    #setup
    if current_pos != start:
        yield from bps.mv(I22_base_top.motors[axis], start)


    # create an array of steps for counts to be performed on
    step_array = np.linspace(start,stop,n_steps)

    detector = "nothing"

    #do the steps, take measurements
    for step in step_array:

        yield from bps.mv(I22_base_top.motors[axis], step)



    intensities = "something"


    # find the position where there is maximum intensity using a peak fit
    # must be a 1d array containing the summed intensity of each frame
    peak_indices, properties = signal.find_peaks(intensities)

    if len(peak_indices) == 0:
        print("No peaks in range, going to max intensity")
        maximum_peak_index = np.argmax(intensities)
        max_peak_position = step_array[maximum_peak_index]
        final_position = max_peak_position

    elif len(peak_indices) == 1:
        maximum_peak_index = peak_indices[0]
        max_peak_position = step_array[maximum_peak_index]
        final_position = max_peak_position

    elif len(peak_indices) > 1:
        maximum_peak_index = np.argmax(properties["prominences"]) #find the BIGGEST peak
        max_peak_position = step_array[maximum_peak_index]
        final_position = max_peak_position


    if plot:
        #plot a nice graph for the user to check their results
        plt.plot(step_array,intensities)
        plt.plot(peak_indices, step_array[peak_indices], "x")
        plt.vlines(x=peak_indices, ymin=x[peak_indices] - properties["prominences"],
                ymax = step_array[peak_indices], color = "C1")
        plt.hlines(y=properties["width_heights"], xmin=properties["left_ips"],
                xmax=properties["right_ips"], color = "C1")
        plt.show()

    # move the motor to the final position which should be the 
    # 'sample centre' position based on the maximum 
    # intensity measured if there was any peak

    yield from bps.mv(I22_base_top.motors[axis], final_position)



if __name__ == '__main__':

    RE = RunEngine({})
    # RE(center_sample(65,66,10,"Y"))

    RE(center_sample(64,65,10,"Y"))