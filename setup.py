from setuptools import setup, Extension

setup(
    ext_modules=[
        Extension("jntajis._jntajis", ["src/jntajis/_jntajis.pyx"]),
    ],
)
