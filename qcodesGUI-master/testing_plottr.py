# -*- coding: utf-8 -*-
"""
Created on Tue Feb 23 12:27:37 2021

@author: aurel
"""

import os
import numpy as np
import time
import qcodes as qc
from qcodes import Station, initialise_or_create_database_at, \
    load_or_create_experiment, Measurement
from qcodes.tests.instrument_mocks import DummyInstrument, \
    DummyInstrumentWithMeasurement
from qcodes.utils.dataset.doNd import do1d
from qcodes.instrument_drivers.yokogawa.GS200 import GS200
qc.logger.start_all_logging()

yoko = GS200("YokoGS","GPIB0::1::INSTR")
dac = DummyInstrument('dac', gates=['ch1', 'ch2'])
dmm = DummyInstrumentWithMeasurement(name='dmm', setter_instr=dac)

station = qc.Station(yoko,dmm)

db_file_path = os.path.join(os.getcwd(), 'plottr_for_live_plotting_tutorial.db')
initialise_or_create_database_at(db_file_path)
exp = load_or_create_experiment(experiment_name='plottr_for_live_plotting_with_subsecond_refresh_rate',
                          sample_name="no sample")




meas = Measurement(exp=exp)
meas.register_parameter(yoko.voltage)
meas.register_parameter(dmm.v1,setpoints=(yoko.voltage,))
meas.register_parameter(dmm.v2,setpoints=(yoko.voltage,))


with meas.run() as datasaver:
    for yoko_sweep in np.linspace(0, 1, 11): # sweep points
        yoko.voltage(yoko_sweep)
        datasaver.add_result(
            (yoko.voltage, yoko.voltage()),
            (dmm.v1, dmm.v1()),
            (dmm.v2, dmm.v2())
            )
        time.sleep(5) # Can be removed if there is no intention to see a live plot

    dataset = datasaver.dataset
    
yoko.close()
dac.close()
dmm.close()