#encoding: utf8

from setuptools import setup, Extension

setup(  
    name='rejit',
    version='0.1',
    description='Simple regular expression just-in-time compiler',
    author='Grzegorz Ludwikowski',
    author_email='ludwikowskig@gmail.com',
    url='https://github.com/ziowk/rejit',
    license='GPLv2',
    packages=['rejit',],
    ext_modules = [Extension('rejit.loadcode', sources=['rejit/loadcode.c'])],
    extras_require = {
        'dev': ["graphviz", "pytest"]
        },
    keywords = ['regexp', 'regex', 'JIT', 'just-in-time', 'compiler'],
    classifiers = [
        'Develeopment Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.4',
        'Topic :: Text Processing',
        ],
    zip_safe = True,
)

