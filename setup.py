#! /usr/bin/env python

from setuptools import setup


setup(name='mmwave',
      version='0.1',
      description='mmWave gesture recognition',
      url='http://github.com/f12markovic/mmwave-gesture-recognition',
      author='Filip Markovic',
      author_email='f12markovic@gmail.com',
      license='MIT',
      packages=['mmwave'],
      install_requires=['pyserial',
                        'pyreadline',
                        'pynput',
                        'colorama',
                        'tqdm',
                        'pandas',
                        'numpy',
                        'matplotlib',
                        'scikit-learn',
                        'tensorflow'],
      zip_safe=False)
