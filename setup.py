#!/usr/bin/env python

""" Setup mp3 decoder """

from setuptools import setup, Extension

interlace_module = Extension(
    "pymp3decoder._pymp3_c",
    sources=[
        "pymp3decoder/swig_interface.i",
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
)
