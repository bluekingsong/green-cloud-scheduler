#!/usr/bin/env python
# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2012 Sina Corporation
# All Rights Reserved.
# Author: YuWei Peng <pengyuwei@gmail.com>
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import sys
from setuptools import setup, find_packages
from os import system;

requirements = ['pyzmq']#, 'python-novaclient', 'python-keystoneclient']

# install pyzmq
system('apt-get install libzmq-dev python-setuptools python-mysqldb redis-server python-redis python-zmq');
setup(
    name = "kanyun",
    version = "0.1",
#    package_dir = {'':'monitoring'},   # tell distutils packages are under src
    packages = ['bin',
            'kanyun',
            'kanyun.common',
            'kanyun.database',
            'kanyun.server',
            'kanyun.worker',
            'kanyun.client'],
    # Project uses reStructuredText, so ensure that the docutils get
    # installed or upgraded on the target machine
    install_requires = requirements,

    package_data = {
        # If any package contains *.txt or *.rst files, include them:
        '': ['*.txt', '*.rst'],
        # And include any *.msg files found in the 'hello' package, too:
        'bin': ['*.conf'],
        'worker': ['*.conf'],
        'server': ['*.conf'],
    },

    # metadata for upload to PyPI
    author = 'Sina Corp.',
    author_email = "pengyuwei@gmail.com",
    description = "OpenStack Monitoring System",
    long_description = "OpenStack Monitoring System",
    license = 'Apache',
    keywords = "vm openstack monitor kanyun",
    url = "https://git.sws.sina.com.cn/pyw_code/pyw_code",   # project home page, if any
    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],

    # could also include long_description, download_url, classifiers, etc.
)


