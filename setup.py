try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(name="tsquare",
      version='0.2.5',
      description='Python TSquare API bindings',
      author='Sean Gillespie',
      author_email='sean.william.g@gmail.com',
      url='https://github.com/swgillespie/tsquare',
      py_modules=['tsquare',
                  'tsquare.core',
                  'tsquare.parsers'],
      long_description="Get and manipulate the state of TSquare with python!",
      install_requires=['requests>=1.2.3',
                        'BeautifulSoup>=3.2.1',
                        'lxml>=3.1.0'],
      license='MIT',
      )