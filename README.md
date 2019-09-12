# Basic Gesture Recognition Using mmWave Sensor - TI AWR1642

Collecting data from TI AWR1642 via serial port and passing it through
pre-trained neural network for recognizing one of ten following gestures:

- Swipe Up
- Swipe Down
- Swipe Right
- Swipe Left
- Spin CW
- Spin CCW
- Letter Z
- Letter X
- Letter S
- Spiral Out

[![Watch the video](https://img.youtube.com/vi/bKT5YLit-_g/maxresdefault.jpg)](https://youtu.be/bKT5YLit-_g)

## Getting Started

These instructions will get you the project up and running on your local machine
for development and testing purposes.

### Prerequisites

#### On mmWave sensor side

For just flashing a .bin file:

- TI UniFlash - [cloud version](https://dev.ti.com/uniflash/) or [standalone version](http://www.ti.com/tool/UNIFLASH)

For developing, compiling and debugging the code:

- [CCS studio](http://www.ti.com/tool/CCSTUDIO) with mmWave support
- [TI mmWaveSDK 02.00.00.04](http://software-dl.ti.com/ra-processors/esd/MMWAVE-SDK/02_00_00_04/index_FDS.html) with modules:
    - SYS/BIOS 6.53.02.00
    - TI CGT C6000 8.1.3
    - TI CGT ARM 16.9.6
    - DSPLIB C64Px 3.4.0.0
    - DSPLIB C674x 3.4.0.0
    - MATHLIB C674x 3.1.2.1
    - XDCtools 3.50.04.43

##### Installation

```
chmod a+x mmwave_sdk_02_00_00_04-Linux-x86-Install.bin
./mmwave_sdk_02_00_00_04-Linux-x86-Install.bin
```

#### On the other side of the line:

- python3 with:
    - [pyserial](https://pypi.org/project/pyserial/)
    - [aenum](https://pypi.org/project/aenum/)
    - [numpy](https://pypi.org/project/numpy/)
    - [matplotlib](https://pypi.org/project/matplotlib/)
    - [pandas](https://pypi.org/project/pandas/)
    - [scikit-learn](https://pypi.org/project/scikit-learn/)
    - [tensorflow](https://pypi.org/project/tensorflow/)
    - [keras](https://pypi.org/project/Keras/)

##### Installation

For a single user

```
pip3 install --user pyserial aenum numpy matplotlib pandas scikit-learn tensorflow keras
```

or for all users

```
sudo pip3 install pyserial aenum numpy matplotlib pandas scikit-learn tensorflow keras
```

## Running

### Setting up AWR1642

Code used for AWR1642 is just a variation of mmWaveSDK demo provided with
version 02.00.00.04. Please follow TI's [guide](./mmwave_development/mmw_16xx_user_guide.pdf) on how to set up the AWR1642.

__Note__: instead of flashing xwr16xx_ccsdebug.bin (explained on page 19 of the
[guide](./mmwave_development/mmw_16xx_user_guide.pdf)) and then running CCSTUDIO for loading the code, it is possible to just
flash [xwr16xx_mmw_demo.bin](./mmwave_development/xwr16xx_mmw_demo.bin) file. This way CCSTUDIO is not needed and the
code will start running as soon as the board has been powered up. This is more
plug and play solution if you wish not to mess around with mmWave code.

### Collecting data

[_collect_data.py_](./collect_data.py) is used for saving of the data incoming from TI AWR1642.
The passed argument will be used for labeling of the data. Files will be saved
in [data](./data/) directory, distributed in proper gesture folders.

```
python3 collect_data.py up
python3 collect_data.py down
python3 collect_data.py right
python3 collect_data.py left
python3 collect_data.py cw
python3 collect_data.py ccw
python3 collect_data.py z
python3 collect_data.py s
python3 collect_data.py x
python3 collect_data.py spiral
```

### Training

[_nn.py_](./nn.py) is used for:

- training of neural network with previously saved data samples.
  (__Note__: These samples are already pre-processed and saved in pickle files.
  In order to refresh the database, --refresh-db flag should be passed (this can
  take some time)).
  Weights with best accuracy on test set will be saved in [.model_weights](./.model_weights) file
  and used later in [_test.py_](./test.py) script.

```
python3 nn.py train
```

or

```
python3 nn.py train --refresh-db
```

- evaluating the model with trained weights

```
python3 nn.py eval
```

### Testing

[_test.py_](./test.py) will create a connection with AWR1642 and it will propagate any
incoming data through NN with loaded, previously trained, weights.

```
python3 test.py
```

## Authors

* **Filip Markovic**

## License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for
details

## Acknowledgments

* Thanks to [NOVELIC](https://www.novelic.com/) for providing me with sensors
* Hat tip to [andry9454](https://github.com/andry9454) for [DropConnect](https://github.com/andry9454/KerasDropconnect) wrapper layer  and to [nigeljyng](https://gist.github.com/nigeljyng) for [TemporalMaxPooling](https://gist.github.com/nigeljyng/881ae30e7c35ca2b77f6975e50736493) layer implementation in keras
