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
      requires=['requests'],
      license='MIT',
      )