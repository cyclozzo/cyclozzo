try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

setup(
    name='cyclozzo-appserver',
    version='1.0.1',
    description='Cyclozzo App server',
    author='Sreejith K / K7Computing Pvt Ltd',
    author_email='sreejith.kesavan@k7cloud.com',
    url='http://www.k7computing.com',
    install_requires=[
        "cyclozzo-sdk >=1.0.138", 
        "cyclozzo-runtime >=1.0.1"
    ],
    scripts=['scripts/cyclozzo-appserver'],
    setup_requires=[],
    namespace_packages = ['cyclozzo'],
    packages=find_packages(exclude=['ez_setup']),
    package_data={'cyclozzo': ['appserver/appserver.yaml']},
    include_package_data=True,
    zip_safe=True,
)
