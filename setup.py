#!/usr/bin/env python

import copy

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildCmd(build_py):
    def run(self):
        # build foris plugin files
        from foris_plugins_distutils import build

        cmd = build(copy.copy(self.distribution))
        cmd.ensure_finalized()
        cmd.run()

        # build package
        build_py.run(self)


setup(
    name="Foris Subordinates Plugin",
    version="0.4",
    description="Subordinates plugin for foris web interface",
    author="CZ.NIC, z. s. p. o.",
    author_email="stepan.henek@nic.cz",
    url="https://gitlab.labs.nic.cz/turris/foris/foris-subordinates-plugin/",
    license="GPL-3.0",
    install_requires=["foris", "jinja2"],
    setup_requires=["babel", "libsass", "foris_plugins_distutils"],
    provides=["foris_plugins.subordinates"],
    packages=["foris_plugins.subordinates"],
    package_data={
        "": [
            "templates/**",
            "templates/**/*",
            "templates/javascript/**",
            "templates/javascript/**/*",
            "locale/**/LC_MESSAGES/*.mo",
            "static/css/*.css",
            "static/fonts/*",
            "static/img/*",
            "static/js/*.js",
            "static/js/contrib/*",
        ]
    },
    namespace_packages=["foris_plugins"],
    cmdclass={"build_py": BuildCmd},  # modify build_py to build the foris files as well
    dependency_links=[
        "git+https://gitlab.labs.nic.cz/turris/foris/foris-plugins-distutils.git"
        "#egg=foris_plugins_distutils"
    ],
)
