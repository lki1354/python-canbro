from setuptools import setup, find_packages

with open('README.md', 'rb') as readme_file:
    readme = readme_file.read().decode('utf-8')

setup(
    name='canbro',
    version='0.0.2-alpha',
    description='This package extend the python-can with the broqer package. This provides the functionality to work in a reactive style with can signals and messages.',
    author='Lukas Riegler',
    author_email='lukasantonriegler@gmail.com',
    url='https://github.com/lki1354/python-canbro',
    packages=find_packages(),
    long_description_content_type='text/markdown',
    long_description=readme,
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
