from setuptools import setup


setup(
    name='blastdbget',
    version='0.0.5',
    url='http://github.com/brwnj/blastdbget',
    license='MIT',
    author='Joe Brown',
    author_email='brwnjm@gmail.com',
    description='Blast DB downloads via NCBI FTP.',
    long_description=__doc__,
    py_modules=['blastdbget'],
    install_requires=[
        'click>=2.0',
    ],
    entry_points='''
        [console_scripts]
        blastdbget=blastdbget:download
    '''
)
