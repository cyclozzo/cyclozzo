try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

setup(
    name='cyclozzo-ose',
    version='1.0.1',
    description='Meta package for Cyclozzo-OSE',
    author='Stanislav Yudin / K7Computing Pvt Ltd',
    author_email='syudin@k7computing.com',
    url='http://www.cyclozzo.com',
    install_requires=[
		"cyclozzo-sdk>=1.0.138",
        "cyclozzo-runtime>=1.0.1",
        "cyclozzo-appserver>=1.0.1"
    ],
    setup_requires=[],
    namespace_packages = ['cyclozzo'],
    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    package_data={ 'cyclozzo': [ 'ose/settings.yaml' ] },
    zip_safe=True,
    options = { 'bdist_rpm': { 'requires': [ 'cyclozzo-sdk >= 1.0.138' ] } },
    scripts = [ 'scripts/cyclozzo' ],
)
