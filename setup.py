from setuptools import setup, find_packages

setup(
    name='quickmud',
    version='0.1.0',
    packages=['mud'] + [f'mud.{p}' for p in find_packages('mud')],
    package_dir={'mud': 'mud'},
    entry_points={
        'console_scripts': [
            'mud=mud.__main__:cli',
        ],
    },
)
