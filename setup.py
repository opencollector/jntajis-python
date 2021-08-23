from setuptools import setup, Extension

setup(
    use_scm_version={
        "tag_regex": r"^(?P<version>[vV]?\d+(?:\.\d+){0,2}[^\+]*)(?:\+.*)?$"
    },
    ext_modules=[
        Extension("jntajis._jntajis", ["src/jntajis/_jntajis.pyx"]),
    ],
)
