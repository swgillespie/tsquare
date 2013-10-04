try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(name="tsquare",
      version='0.1',
      description='Python TSquare API bindings',
      author='Sean Gillespie',
      author_email='sean.william.g@gmail.com',
      url='https://github.com/swgillespie/tsquare',
      py_modules=['tsquare',
                  'tsquare.core',
                  'tsquare.parsers'],
      long_description=open('README').read(),
      install_requires=['requests >= 1.2.3'],
      license='MIT',
      )