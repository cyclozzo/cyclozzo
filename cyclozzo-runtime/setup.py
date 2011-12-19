try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

setup(
    name='cyclozzo-runtime',
    version='1.0.1',
    description='Cyclozzo Cloud Platform Run-Time',
    author='Stanislav Yudin / K7Computing Pvt Ltd',
    author_email='syudin@k7computing.com',
    url='http://www.k7computing.com',
    install_requires=[
		"cyclozzo-sdk>=1.0.138",
        "fabric>=1.2.2"
    ],
    setup_requires=[],
    namespace_packages = ['cyclozzo'],
    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    zip_safe=True,
    options = { 'bdist_rpm': { 'requires': [ 'cyclozzo-sdk >= 1.0.138' ] } }
)
