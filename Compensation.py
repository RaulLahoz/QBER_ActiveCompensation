import numpy as np
import matplotlib.pyplot as plt
import tkinter as tki

import TimeTagger as TimeTagger

from ELL14 import ElliptecController



class ContinuousPolarizationOptimizer:
    """
    Class that continuously randomly varies waveplate positions and
    keeps track of optimal ones.
    """
    def __init__(self,
                 waveplates: tuple[ElliptecController, ...],
                 max_stepsize_deg: float = 2.0,
                 threshold: float = 0.01,
                 n_stored: int = 1):
        """
        Arguments:
        waveplates:         list of instances of ElliptecController class
        max_stepsize_deg:   maximum random waveplate rotation in degrees
        threshold:          QBER above which optimization is performed
        n_stored:           number of operation points kept in memory
        """
        self._waveplates = waveplates
        self._max_stepsize_deg = max_stepsize_deg
        self._threshold = threshold
        self._positions = np.zeros(len(waveplates), dtype=float)
        # Relevant for coordinate descent:
        self._current_wp = 0
        self._current_pos = 1
        self._origin_position = 0
        self._qbers = np.array([0.1, 0.1, 0.1])
        # Relevant for random minimizer:
        self._n_stored = n_stored
        self._previous_qbers = np.array([0.5])
        self._previous_positions = np.array([self._positions])
    
    def get_positions(self):
        positions = np.array([0, 0], dtype=float)
        for i in (0, 1):
            positions[i] = self._waveplates[i].get_position_deg()
        return positions

    def tune_voltages_manually(self):
        """
        Function that opens a GUI to tune the initial setting
        of the PCDM02.
        """
        root = tki.Tk()
        root.title("PCD-M02 testbench")

        # Functions that define what happens when you move any of the sliders:
        def slide0(val):
            self._waveplates[0].move_absolute_deg(ch0.get())

        def slide1(val):
            self._waveplates[1].move_absolute_deg(ch1.get())

        # Define the two sliders:
        ch0 = tki.Scale(root, from_=0, to=360, orient=tki.HORIZONTAL,
                        command=slide0, length=500)
        ch0.set(self._positions[0])
        ch0.pack()
        tki.Label(root, text="Waveplate 1").pack()
        ch1 = tki.Scale(root, from_=0, to=360, orient=tki.HORIZONTAL,
                        command=slide1, length=500)
        ch1.set(self._positions[1])
        ch1.pack()
        tki.Label(root, text="Channel 2").pack()

        # Run the GUI:
        root.mainloop()

        # After manual optimization is finished and the window is closed,
        # update the current waveplate positions:
        self._positions = self.get_positions()
        
    def random_minimizer(self, qber: float):
        """
        This function takes a measured QBER as input and compares it with
        10 values from previous measurements.
        If the newly measured one is lowest, then keep the settings used for
        it as a new point of operation, and apply random changes to it.
        If a stored one is lower, then revert to the respective point
        of operation and apply changes to that one.
        """
        try:
            positions = self.get_positions()
            # Change "default" state if new QBER is better than any old one:
            if qber < np.min(self._previous_qbers):
                self._positions = positions
            else:
                self._positions = self._previous_positions[np.argmin(self._previous_qbers)]
            # Append new QBER and setting to lists:
            if len(self._previous_qbers) < self._n_stored:
                self._previous_qbers = np.append(self._previous_qbers, qber)
                self._previous_positions = np.append(self._previous_positions, [positions], axis=0)
            else:
                self._previous_qbers = np.append(self._previous_qbers[1:], qber)
                self._previous_positions = np.append(self._previous_positions[1:], [positions], axis=0)
        except Exception as e:
            print(e)
            print("Error during Polarization Optimization")
        # Apply voltage change with random sign and amplitude to a random channel:
        delta_phi = np.random.uniform(-self._max_stepsize_deg, self._max_stepsize_deg)
        wp = np.random.randint(0, 2)
        self._waveplates[wp].move_relative_deg(delta_phi)
        self._positions = self.get_positions()

    def coordinate_descent_2nd_order(self, qber):
        """
        Method depending on adjusting the voltage of individual channels
        in an iterative fashion, relying on first and second order derivatives.
        Reference:
        https://iopscience.iop.org/article/10.1088/1742-6596/2086/1/012092.

        Args:
        - qber: QBER measured during most recent data acquisition by Bob.
        """
        # If QBER is low enough, reset to ground state and do nothing:
        if qber < self._threshold:
            self._current_wp = 0
            self._current_pos = 1
        # Otherwise, perform second order coordinate descent:
        else:
            # If current QBER value is the "central" one,
            # set current voltage as origin voltage:
            if self._current_pos == 1:
                position = self._waveplates[self._current_wp].get_position_deg()
                self._origin_position = position
            else:
                position = self._origin_position
            self._qbers[self._current_pos] = qber
            if self._current_pos == 1:
                self._waveplates[self._current_wp].move_absolute_deg(position + self._max_stepsize_deg)
            if self._current_pos == 2:
                self._waveplates[self._current_wp].move_absolute_deg(position - self._max_stepsize_deg)
            if self._current_pos == 0:
                # Compute and set new voltage via discrete first derivative:
                q_l, q, q_r = self._qbers
                dQ_dV = (q_r - q_l) / (2 * self._max_stepsize_deg)
                dQ2_dV2 = (q_r - 2 * q + q_l)
                dQ2_dV2 /= (self._max_stepsize_deg ** 2)
                step = dQ_dV / dQ2_dV2
                # Make sure to never change by more than 5V:
                sign = -1 if step < 0 else +1
                if np.abs(step) > 5:
                    step = sign * 5
                # Move the correct way depending on sign of second derivative:
                if dQ2_dV2 > 0:
                    self._waveplates[self._current_wp].move_absolute_deg(position - step)
                else:
                    self._waveplates[self._current_wp].move_absolute_deg(position + step)
            # Update position and channel:
            self._positions = self.get_positions()
            print(f"Position, Channel, Orientations: {self._current_pos}, {self._current_wp}, {self._positions}")
            self._current_pos += 1
            self._current_pos %= 3
            if self._current_pos == 1:
                self._current_wp += 1
                self._current_wp %= 2

if __name__ == "__main__":
    # Test run setup
    TESTING = False
    meas_duration = 1  # seconds
    n_iterations = 50
    tt_channels = [3, 4] # Channel 3 (H), Channel 4 (V)
    qbers = np.zeros(n_iterations)

    # Initialize waveplates:
    wp_1 = ElliptecController(address="0", verbose=True)
    wp_2 = ElliptecController(address="2", verbose=True)
    waveplates = (wp_1, wp_2)
    optimizer = ContinuousPolarizationOptimizer(waveplates=waveplates, max_stepsize_deg=3)

    # Open GUI to make initial tuning:
    optimizer.tune_voltages_manually()  # Close the GUI window to move on, but CLOSE THE TIMETAGGER GUI before
    # Otherwise the connection to the TimeTagger cannot be established below, as it will be occupied

    # Initialize TimeTagger:
    if not TESTING:
        tagger = TimeTagger.createTimeTagger()
        ctr = TimeTagger.Countrate(tagger, tt_channels)

    # MEASUREMENT LOOP
    for i in range(n_iterations):
        if TESTING:
            qber = np.random.uniform(0, 0.2)
        else:
            cts_h = ctr.getData()[0] # Channel 3 (H)
            cts_v = ctr.getData()[1] # Channel 4 (V)
            qber = cts_h / (cts_h + cts_v)
        optimizer.coordinate_descent_2nd_order(qber)
        # optimizer.random_minimizer(qber)  # alternative
        qbers[i] = qber

    # Plot and save:
    np.savetxt("./QBERS.txt", qbers, delimiter="\n")
    plt.plot(range(n_iterations), qbers)
    plt.grid()
    plt.xlabel("Iteration")
    plt.ylabel("QBER")
    plt.tight_layout(pad=0.1)
    plt.savefig("./PolarizationStabilizationTest.jpg", dpi=600)
    plt.show()
