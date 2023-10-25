from setuptools import setup, find_packages

setup(
    name='canbro',
    version='0.0.1',
    description='Python module for working with Controller Area Network (CAN) messages and signals',
    author='Lukas Riegler',
    author_email='lukasantonriegler@gmail.com',
    url='https://github.com/lki1354/python-canbro',
    packages=find_packages(),
    install_requires=[
        'python-can>=3.3',
        'cantools>=36.2',
        'broqer>=1.7',
    ],
    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
)
