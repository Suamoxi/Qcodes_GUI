from qcodes import Instrument,ChannelList,InstrumentChannel
from qcodes.instrument.parameter import Parameter
from qcodes.utils.validators import Numbers
from random import randint


class DummyInstrument(Instrument):

    def __init__(self, name = 'dummy', gates=['dac1', 'dac2', 'dac3'], **kwargs):

        """
        Random measurement demonstration dummy

        Args:
            name (string): name for the instrument
            gates (list): list of names that is used to create parameters for
                            the instrument
        """
        super().__init__(name, **kwargs)

        # make gates
        for _, g in enumerate(gates):
            self.add_parameter(g,
                               parameter_class=Parameter,
                               initial_value=0,
                               label='Gate {}'.format(g),
                               unit="V",
                               vals=Numbers(-800, 400),
                               get_cmd=lambda: randint(0, 100), set_cmd=None)

class DummyChannelInstrument(Instrument):
    """
    Dummy instrument with channels
    """

    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)

        channels = ChannelList(self, "TempSensors", DummyChannel, snapshotable=False)
        for chan_name in ('A', 'B', 'C', 'D', 'E', 'F'):
            channel = DummyChannel(self, f'Chan{chan_name}', chan_name)
            channels.append(channel)
            self.add_submodule(chan_name, channel)
        self.add_submodule("channels", channels)
        
class DummyChannel(InstrumentChannel):
    """
    A single dummy channel implementation
    """

    def __init__(self, parent, name, channel):
        super().__init__(parent, name)

        self._channel = channel

        # Add the various channel parameters
        self.add_parameter('temperature',
                           parameter_class=Parameter,
                           initial_value=0,
                           label=f"Temperature_{channel}",
                           unit='K',
                           vals=Numbers(0, 300),
                           get_cmd=None, set_cmd=None)


        self.add_parameter('dummy_start',
                           initial_value=0,
                           unit='some unit',
                           label='f start',
                           vals=Numbers(0, 1e3),
                           get_cmd=None,
                           set_cmd=None)

        self.add_parameter('dummy_stop',
                           unit='some unit',
                           label='f stop',
                           vals=Numbers(1, 1e3),
                           get_cmd=None,
                           set_cmd=None)

        self.add_parameter('dummy_n_points',
                           unit='',
                           vals=Numbers(1, 1e3),
                           get_cmd=None,
                           set_cmd=None)

        self.add_parameter('dummy_start_2',
                           initial_value=0,
                           unit='some unit',
                           label='f start',
                           vals=Numbers(0, 1e3),
                           get_cmd=None,
                           set_cmd=None)

        self.add_parameter('dummy_stop_2',
                           unit='some unit',
                           label='f stop',
                           vals=Numbers(1, 1e3),
                           get_cmd=None,
                           set_cmd=None)

        self.add_parameter('dummy_n_points_2',
                           unit='',
                           vals=Numbers(1, 1e3),
                           get_cmd=None,
                           set_cmd=None)


