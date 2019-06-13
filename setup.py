from setuptools import setup

setup(

   name='slycot_reader',
   version='0.0.1',
   description='Reads Fortran source code in Slycot',
   author='KangWon LEE',
   author_email='kangwon@gmail.com',
   packages=['slycot_reader'],
   install_requires=[],
   test_suite="slycot_reader.tests.test_all" 
   # https://setuptools.readthedocs.io/en/latest/setuptools.html#test-build-package-and-run-a-unittest-suite
)
