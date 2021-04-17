from ...core.devio import SCPI, interface



class ThorlabsInterface(SCPI.SCPIDevice):
    """
    Generic Thorlabs device interface using Serial communication.

    Args:
        conn: serial connection parameters (usually port or a tuple containing port and baudrate)
    """
    _allow_concatenate_write=False
    def __init__(self, conn):
        SCPI.SCPIDevice.__init__(self,conn,backend="serial",term_read=["\r","\n"],term_write="\r",timeout=5.,backend_defaults={"serial":("COM1",115200)})

    def open(self):
        SCPI.SCPIDevice.open(self)
        self.instr.flush_read()
    
    def _instr_write(self, msg):
        self.instr.flush_read()
        return self.instr.write(msg,read_echo=True)
    def _instr_read(self, raw=False, size=None):
        if size:
            data=self.instr.read(size=size)
        elif raw:
            data=self.instr.readline(remove_term=False)
        else:
            data=""
            while not data:
                data=self.instr.readline(remove_term=True).strip()
                while data[:1]==b">":
                    data=data[1:].strip()
        return data


class FW(ThorlabsInterface):
    """
    Thorlabs FW102/212 motorized filter wheels.

    Args:
        conn: serial connection parameters (usually port or a tuple containing port and baudrate)
        respect_bound(bool): if ``True``, avoid crossing the boundary between the first and the last position in the wheel
    """
    def __init__(self, conn, respect_bound=True):
        ThorlabsInterface.__init__(self,conn)
        self._add_settings_variable("pos",self.get_position,self.set_position)
        self._add_settings_variable("pcount",self.get_pcount,self.set_pcount)
        self._add_settings_variable("speed_mode",self.get_speed_mode,self.set_speed_mode)
        self._add_settings_variable("trigger_mode",self.get_trigger_mode,self.set_trigger_mode)
        self._add_settings_variable("sensors_mode",self.get_sensor_mode,self.set_sensor_mode)
        self.pcount=self.get_pcount()
        self.respect_bound=respect_bound

    _id_comm="*idn?"
    def get_position(self):
        """Get the wheel position (starting from 1)"""
        return self.ask("pos?","int")
    def set_position(self, pos):
        """Set the wheel position (starting from 1)"""
        if self.respect_bound: # check if the wheel could go through zero; if so, manually go around instead
            cur_pos=self.get_position()
            if abs(pos-cur_pos)>=self.pcount//2: # could switch by going through zero
                medp1=(2*cur_pos+pos)//3
                medp2=(cur_pos+2*pos)//3
                self.write("pos={}".format(medp1))
                self.write("pos={}".format(medp2))
                self.write("pos={}".format(pos))
            else:
                self.write("pos={}".format(pos))
        else:
            self.write("pos={}".format(pos))
        return self.get_position()

    def get_pcount(self):
        """Get the number of wheel positions (6 or 12)"""
        return self.ask("pcount?","int")
    def set_pcount(self, pcount):
        """Set the number of wheel positions (6 or 12)"""
        self.write("pcount={}".format(pcount))
        self.pcount=self.get_pcount()
        return self.pcount

    _p_speed_mode=interface.EnumParameterClass("speed_mode",{"low":0,"high":1})
    @interface.use_parameters(_returns="speed_mode")
    def get_speed_mode(self):
        """Get the motion speed mode (``"low"`` or ``"high"``)"""
        return self.ask("speed?","int")
    @interface.use_parameters
    def set_speed_mode(self, speed_mode):
        """Set the motion speed mode (``"low"`` or ``"high"``)"""
        self.write("speed={}".format(speed_mode))
        return self.get_speed_mode()

    _p_trigger_mode=interface.EnumParameterClass("trigger_mode",{"in":0,"out":1})
    @interface.use_parameters(_returns="trigger_mode")
    def get_trigger_mode(self):
        """Get the trigger mode (``"in"`` to input external trigger, ``"out"`` to output trigger)"""
        return self.ask("trig?","int")
    @interface.use_parameters
    def set_trigger_mode(self, trigger_mode):
        """Set the trigger mode (``"in"`` to input external trigger, ``"out"`` to output trigger)"""
        self.write("trig={}".format(trigger_mode))
        return self.get_trigger_mode()

    _p_sensor_mode=interface.EnumParameterClass("sensor_mode",{"off":0,"on":1})
    @interface.use_parameters(_returns="sensor_mode")
    def get_sensor_mode(self):
        """Get the sensor mode (``"off"`` to turn off when idle to eliminate stray light, ``"on"`` to remain on)"""
        return self.ask("sensors?","int")
    @interface.use_parameters
    def set_sensor_mode(self, sensor_mode):
        """Set the sensor mode (``"off"`` to turn off when idle to eliminate stray light, ``"on"`` to remain on)"""
        self.write("sensors={}".format(sensor_mode))
        return self.get_sensor_mode()

    def store_settings(self):
        """Store current settings as default"""
        self.write("save")






class MDT69xA(ThorlabsInterface):
    """
    Thorlabs MDT693A/4A high-voltage source.

    Uses MDT693A program interface, so should be compatible with both A and B versions
    (though it doesn't support all functions of MDT693B/4B)

    Args:
        conn: serial connection parameters (usually port or a tuple containing port and baudrate)
    """
    def __init__(self, conn):
        ThorlabsInterface.__init__(self,conn)
        self._add_settings_variable("voltage",self.get_voltage,self.set_voltage,mux=("xyz",1))
        self._add_status_variable("voltage_range",self.get_voltage_range)
        try:
            self.get_id(timeout=2.)
        except self.instr.Error as e:
            self.close()
            raise self.instr.BackendOpenError(e)

    _id_comm="I"
    _p_channel=interface.EnumParameterClass("channel",["x","y","z"])
    @interface.use_parameters
    def get_voltage(self, channel="x"):
        """Get the output voltage in Volts at a given channel"""
        resp=self.ask(channel.upper()+"R?")
        resp=resp.strip()[2:-1].strip()
        return float(resp)
    @interface.use_parameters
    def set_voltage(self, voltage, channel="x"):
        """Set the output voltage in Volts at a given channel"""
        self.write(channel.upper()+"V{:.3f}".format(voltage))
        return self.get_voltage(channel=channel)

    def get_voltage_range(self):
        """Get the selected voltage range in Volts (75, 100 or 150)."""
        resp=self.ask("%")
        resp=resp.strip()[2:-1].strip()
        return float(resp)