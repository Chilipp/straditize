import os
import os.path as osp
from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand
import sys


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to pytest")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = ''

    def run_tests(self):
        import shlex
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(shlex.split(self.pytest_args))
        sys.exit(errno)


def readme():
    with open('README.rst') as f:
        return f.read()


# read the version from version.py
with open(osp.join('straditize', 'version.py')) as f:
    exec(f.read())


dependencies = [
    'psyplot-gui>=1.2.3',
    'psyplot>=1.2.0',
    'psy-strat',
    'scipy',
    'scikit-image',
    'openpyxl',
    'netCDF4',
]

# Test for PyQt5 dependency. During a conda build, this is handled by the
# meta.yaml so we can skip this dependency
if not os.getenv('CONDA_BUILD'):
    # The package might nevertheless be installed, just registered with a
    # different name
    try:
        import PyQt5
    except ImportError:
        dependencies.append('pyqt5!=5.12')
        dependencies.append('PyQtWebEngine')
        dependencies.append('pyqt5-sip')


setup(name='straditize',
      version=__version__,
      description='Python package for digitizing pollen diagrams',
      long_description=readme(),
      classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Visualization',
        'Topic :: Scientific/Engineering :: GIS',
        'Topic :: Scientific/Engineering',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Operating System :: OS Independent',
      ],
      keywords=('visualization earth-sciences paleo climate paleoclimate '
                'pollen diagram digitization database'),
      url='https://github.com/Chilipp/straditize',
      author='Philipp Sommer',
      author_email='philipp.sommer@unil.ch',
      license="GPLv3",
      packages=find_packages(exclude=['docs', 'tests*', 'examples']),
      install_requires=dependencies,
      package_data={'straditize': [
          osp.join('straditize', 'widgets', 'icons', '*.png'),
          osp.join('straditize', 'widgets', 'docs', '*.rst'),
          osp.join('straditize', 'widgets', 'docs', '*.png'),
          osp.join('straditize', 'widgets', 'tutorial', '*', '*.rst'),
          osp.join('straditize', 'widgets', 'tutorial', '*', '*.png'),
          ]},
      include_package_data=True,
      tests_require=['pytest', 'psutil'],
      cmdclass={'test': PyTest},
      entry_points={
          'console_scripts': ['straditize=straditize.__main__:main'],
          'psyplot_gui': ['straditizer=straditize.widgets:StraditizerWidgets'],
          },
      zip_safe=False)
