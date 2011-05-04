from setuptools import setup, find_packages
import os

version = '1.0dev'

setup(name='smtp2zope',
      version=version,
      description="Read an email from stdin and forward it to a url",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from
      # http://pypi.python.org/pypi?:action=list_classifiers
      classifiers=[
        "Programming Language :: Python",
        "Topic :: Communications :: Email",
        ],
      keywords='',
      author='',
      author_email='',
      url='http://svn.plone.org/svn/collective/smtp2zope',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          # -*- Extra requirements: -*-
      ],
      entry_points={
          'console_scripts': [
              'smtp2zope = smtp2zope.script:main',
              ],
          },
      )
