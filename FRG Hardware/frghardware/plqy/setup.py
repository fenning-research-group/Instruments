from setuptools import setup

microlib_name = 'frghardware.plqy'
setup(
    name=microlib_name,
    version="0.1.0",
    namespace_packages=['frghardware'],
    packages=[microlib_name],
    install_requires=['numpy', 'pymeasure', 'pyserial']
)