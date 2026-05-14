import nidaqmx
from nidaqmx.constants import TerminalConfiguration

# read voltage from 6 channels
with nidaqmx.Task() as task:
    task.ai_channels.add_ai_voltage_chan(
        physical_channel="Dev1/ai0:5",
        terminal_config=TerminalConfiguration.DIFF 
    )
    raw_voltage = task.read()
    print(f"Raw voltage data: {raw_voltage}")