from setuptools import setup

microlib_name = 'yokogawa_SMU'
setup(
    name=microlib_name,
    version="0.1.0",
    packages=['yokogawa_SMU']
    # namespace_packages=['yokogawa_SMU'],
    packages=[microlib_name],
    install_requires=['numpy', 'pymeasure', 'pyserial', 'pandas', 'time', 'pyvisa', 'matplotlib', 'serial']
)