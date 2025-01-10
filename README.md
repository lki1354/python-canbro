# python-canbro

the name of the package canbro arose from can and broqer which are the two main python packages which are used in this combination. Additionaly the cantools is also a main contributer for now. But maybe will be replaced with a own implementation in future.

This package use the python-can and extend the python-cantools with the python-broqer package. There the functionality to work in a reactive style with can signals and messages will be provided.

## Dependencies

`canbro` requires the following dependencies:

- `can` (version 4.3.1 or later)
- `cantools` (version 39.4.4 or later)
- `broqer` (version 3.0.3 or later)

## Usage

### example cylce messages

```python
from can.interface import Bus
from cantools.database import load_file
from broqer import Sink
from canbro import Node

# load dbc file
db = load_file('device_CAN.dbc')

# create ECU node with virtual bus test
bus_e= Bus('test', interface='virtual')
ecu = Node(name="ECU",bus=bus_e,database=db )

# create VCU node with virtual bus test, and connect to ECU via same name of bus -> test
bus_v= Bus('test', interface='virtual')
vcu= Node(name='CONTROL',bus=bus_v,database=db )

def show_vcu_value(value):
    print( 'value={}'.format(value) , end='')

show_print = ecu.DEM._signal_operation_mode.subscribe(Sink(show_vcu_value))

vcu.DEM.start_periodic()

vcu.DEM._signal_operation_mode.notify(2)
```

## License

canbro is licensed under the LGPL-3.0 license. See the LICENSE file for more information.

## Author

canbro was created by Lukas Riegler.
Contact him via a issue on github.

## Version

canbro version 0.1.1 in progress.
