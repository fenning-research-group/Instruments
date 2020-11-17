from setuptools import setup, find_namespace_packages

microlib_name = 'frghardware.wardmapper'
setup(
    name=microlib_name,
    version="0.1.0",
    namespace_packages=['frghardware'],
    packages=[microlib_name],
    install_requires=['frghardware.components', 'numpy', 'thorlabs_apt']
)