#encoding: utf8

from setuptools import setup

setup(  
    name='rejit',
    version='0.1',
    description='Simple regular expression just-in-time compiler',
    author='Grzegorz Ludwikowski',
    author_email='ludwikowskig@gmail.com',
    url='https://github.com/ziowk/rejit',
    license='GPLv2',
    packages=['rejit',],
    extras_require = {
        'dev': ["graphviz", "pytest"]
        },
    keywords = ['regexp', 'regex', 'JIT', 'just-in-time', 'compiler'],
    classifiers = [
        'Develeopment Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.4',
        'Topic :: Text Processing',
        ],
    zip_safe = True,
)

