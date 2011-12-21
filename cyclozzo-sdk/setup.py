try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

setup(
    name='cyclozzo-sdk',
    version='1.0.138',
    description='Cyclozzo Cloud Platform SDK',
    author='Stanislav Yudin / K7Computing Pvt Ltd',
    author_email='syudin@k7computing.com',
    url='http://www.k7computing.com',
    install_requires=[
        "PyYAML>=3.09",
        "poster>=0.5",
        "mako>=0.2.5",
        "Thrift>=0.6.0",
        "pylibmc==0.9.1",
        "xmpppy>=0.4.0",
        "brukva>=0.0.1"
    ],
    namespace_packages = ['cyclozzo'], 
    setup_requires=[],
    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    zip_safe=True,
)
