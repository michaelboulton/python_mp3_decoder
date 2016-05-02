#!/usr/bin/env python

""" Setup mp3 decoder """

from setuptools import setup, Extension

from distutils.command.build import build
from subprocess import check_call


class SwigBuild(build):
    def run(self):
        swig_args = (["swig3.0", "-python", "swig_interface.i"],)
        self.execute(check_call, swig_args,
                     msg="Swiggifying interface")
        build.run(self)

interlace_module = Extension(
    "_pymp3_c",
    sources=[
        "swig_interface_wrap.c",
    ],
    libraries = ['mp3lame'],
)

setup(
    name="pymp3decoder",
    version="0.0.1",
    author="Michael Boulton",
    license="MIT",
    keywords="mp3 decoder",
    author_email="michael.boulton@gmail.com",
    description="Simple chunked mp3 decoder",
    use_2to3=True,
    ext_modules=[interlace_module],
    py_modules=["pymp3_c"],
    packages=["pymp3decoder"],
    test_suite="tests",
    setup_requires=['pytest-runner'],
    tests_require=['pytest', 'pyaudio'],
    cmdclass={'build': SwigBuild},
)
