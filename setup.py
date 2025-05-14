from setuptools import find_packages, setup

setup(
	name='mobidetails',
	version='20250512',
	packages=find_packages(),
	include_package_data=True,
	zip_safe=False,
	install_requires=[
		'flask',
	],	
)
