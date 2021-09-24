#!/usr/bin/env python
from setuptools import find_packages, setup
from src.oscar_pg_search import __version__


install_requires = [
    'django>=2.2,<3.3',
    'django-oscar>=3.0',
]

tests_require = [
    'django-webtest==1.9.7',
    'pytest-cov>=2.12,<2.13',
    'pytest-django>=4.4,<4.5',
    'freezegun>=1.1,<1.2',
    'sorl-thumbnail',
    'factory-boy>=3.2,<3.3',
    'coverage>=5.5,<5.6',
    'tox>=3.17,<3.21',
]

setup(
    name='django-oscar-pg-search',
    version=__version__,
    author="Snake-Soft",
    author_email="info@snake-soft.com",
    description="Pure Postgresql search backend for Django Oscar",
    long_description=open('README.rst').read(),
    license='BSD',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    include_package_data=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 2.2',
        'Framework :: Django :: 3.1',
        'Framework :: Django :: 3.2',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require={
        'test': tests_require,
    },
)
