import os.path as op
from setuptools import setup

version_py = op.join(op.dirname(__file__), 'version.py')
with open(version_py) as v:
    version = v.read().strip().split("=")[-1].strip().strip('"')

setup(
    name='blastdbget',
    version=version,
    url='http://github.com/brwnj/blastdbget',
    license='MIT',
    author='Joe Brown',
    author_email='brwnjm@gmail.com',
    description='Blast DB downloads via NCBI FTP.',
    long_description=__doc__,
    py_modules=['blastdbget'],
    install_requires=['sh'],
    entry_points='''
        [console_scripts]
        blastdbget=blastdbget:main
    '''
)
