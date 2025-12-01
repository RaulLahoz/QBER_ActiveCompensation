import time
import numpy as np
import matplotlib.pyplot as plt
import TimeTagger as TimeTagger
from ELL14 import ElliptecController

import time
import numpy as np
import matplotlib.pyplot as plt


class QBERWaveplateMapper:
    """
    Simple container class that stores settings
    and provides angle ranges and output matrix.
    """

    def __init__(self,
                 waveplates: tuple,
                 counter,
                 step_wp1: float = 10.0,
                 step_wp2: float = 10.0,
                 indiv_meas_duration: float = 0.2,
                 filename: str = "map_qber.txt"):

        self.wp_1 = waveplates[0]
        self.wp_2 = waveplates[1]
        self.ctr = counter

        self.step_wp1 = step_wp1
        self.step_wp2 = step_wp2
        self.indiv_meas_duration = indiv_meas_duration
        self.filename = filename

        # Angle range from -180 to +180
        self.angles_wp1 = np.arange(-180, 180 + step_wp1, step_wp1)
        self.angles_wp2 = np.arange(-180, 180 + step_wp2, step_wp2)

        # Storage matrix
        self.qber_map = np.zeros((len(self.angles_wp2), len(self.angles_wp1)))

    def plot_heatmap(self):
        plt.figure(figsize=(8, 6))
        plt.imshow(
            self.qber_map,
            extent=[-180, 180, -180, 180],
            origin='lower',
            aspect='auto',
            cmap='viridis'
        )
        plt.colorbar(label="QBER")
        plt.xlabel("QWP angle (°)")
        plt.ylabel("HWP angle (°)")
        plt.title("QBER Map: QWP vs HWP")
        plt.tight_layout()
        plt.show()

import time
import numpy as np
import matplotlib.pyplot as plt


if __name__ == "__main__":

    # Parameters
    indiv_meas_duration = 0.2
    tt_channels = [3, 4]
    step_wp1 = 10
    step_wp2 = 10

    # Angles from -180° to +180°
    angles_wp1 = np.arange(-180, 180 + step_wp1, step_wp1)
    angles_wp2 = np.arange(-180, 180 + step_wp2, step_wp2)

    # QBER storage matrix
    qber_map = np.zeros((len(angles_wp2), len(angles_wp1)))

    # Initialize waveplates
    wp_1 = ElliptecController(address="0", verbose=True)
    wp_2 = ElliptecController(address="2", verbose=True)

    # ===== Homing =====
    wp_1.home(direction=0)
    wp_2.home(direction=0)

    # Initialize Time Tagger counter
    tagger = TimeTagger.createTimeTagger()
    ctr = TimeTagger.Countrate(tagger, tt_channels)
    time.sleep(1)

    # -----------------------------------------------------------
    #                    CORE DOUBLE LOOP
    # -----------------------------------------------------------
    with open("map_qber.txt", "w") as f:
        f.write("angle_wp1\tangle_wp2\tcts_h\tcts_v\tqber\n")

        for i, angle_wp1 in enumerate(angles_wp1):
            for j, angle_wp2 in enumerate(angles_wp2):

                # Move waveplates
                wp_1.move_absolute_deg(angle_wp1)
                wp_2.move_absolute_deg(angle_wp2)

                # Wait for measurement
                ctr = TimeTagger.Countrate(tagger, tt_channels) # CRITICAL
                time.sleep(indiv_meas_duration)
                # Read counts
                cts_h = ctr.getData()[0] # Channel 3 (H)
                cts_v = ctr.getData()[1] # Channel 4 (V)
                # Compute QBER safely
                qber = cts_h / (cts_h + cts_v) if (cts_h + cts_v) > 0 else 0

                # Store QBER in matrix
                qber_map[j, i] = qber

                # Save to file
                f.write(f"{angle_wp1}\t{angle_wp2}\t{cts_h}\t{cts_v}\t{qber}\n")
                print(f"QBER={qber:.4f} at (QWP={angle_wp1}°, HWP={angle_wp2}°)")


    # -----------------------------------------------------------
    #                    HEATMAP
    # -----------------------------------------------------------
    plt.figure(figsize=(8, 6))
    plt.imshow(
        qber_map,
        extent=[-180, 180, -180, 180],
        origin='lower',
        aspect='auto',
        cmap='viridis'
    )
    plt.colorbar(label="QBER")
    plt.xlabel("QWP angle (°)")
    plt.ylabel("HWP angle (°)")
    plt.title("QBER Map: QWP vs HWP")
    plt.tight_layout()
    plt.show()


