import os
import sys

from setuptools.command.develop import develop
import epicscorelibs.path
import epicscorelibs.version
from setuptools_dso import Extension, setup
from epicscorelibs.config import get_config_var

# Place the directory containing _version_git on the path
TOP = os.path.dirname(os.path.abspath(__file__))
for d in os.listdir(TOP):
    if os.path.exists(os.path.join(TOP, d, "_version_git.py")):
        sys.path.append(os.path.join(TOP, d))

from _version_git import __version__, get_cmdclass  # noqa

sources = ['softioc/extension.c']

devIocStats_OSI = [
    "devIocStatsAnalog.c",
    "devIocStatsString.c",
    "devIocStatsWaveform.c",
    "devIocStatsSub.c",
    "devIocStatsTest.c",
]

devIocStats_OSD = [
    "osdCpuUsage.c",
    "osdCpuUtilization.c",
    "osdFdUsage.c",
    "osdMemUsage.c",
    "osdWorkspaceUsage.c",
    "osdClustInfo.c",
    "osdSuspTasks.c",
    "osdIFErrors.c",
    "osdBootInfo.c",
    "osdSystemInfo.c",
    "osdHostInfo.c",
    "osdPIDInfo.c",
]

devIocStats_src = os.path.join("softioc", "iocStats", "devIocStats")
devIocStats_posix = os.path.join(devIocStats_src, "os", "posix")
devIocStats_os = os.path.join(devIocStats_src, "os", get_config_var('OS_CLASS'))
devIocStats_default = os.path.join(devIocStats_src, "os", "default")

for f in devIocStats_OSI:
    sources.append(os.path.join(devIocStats_src, f))
for f in devIocStats_OSD:
    if os.path.exists(os.path.join(devIocStats_os, f)):
        sources.append(os.path.join(devIocStats_os, f))
    else:
        sources.append(os.path.join(devIocStats_default, f))

include_dirs = [
    epicscorelibs.path.include_path,
    devIocStats_src,
    devIocStats_os,
    devIocStats_default
]

if get_config_var("POSIX"):
    # If we're on a POSIX system, insert the POSIX folder into the list after
    # the os-specific one so that os-specific header files are used first.
    include_dirs.insert(
        include_dirs.index(devIocStats_os) + 1,
        devIocStats_posix
    )

# Extension with all our C code
ext = Extension(
    name='softioc._extension',
    sources = sources,
    include_dirs = include_dirs,
    dsos = [
        'epicscorelibs.lib.dbRecStd',
        'epicscorelibs.lib.dbCore',
        'epicscorelibs.lib.ca',
        'epicscorelibs.lib.Com',
    ],
    define_macros = get_config_var('CPPFLAGS'),
    extra_compile_args = get_config_var('CFLAGS') + ["-std=c99"],
    extra_link_args = get_config_var('LDFLAGS'),
)

# Add custom develop to add soft link to epicscorelibs in .
class Develop(develop):
    def install_for_development(self):
        develop.install_for_development(self)
        # Make a link here to epicscorelibs so `pip install -e .` works
        # If we don't do this dbCore can't be found when _extension is
        # built into .
        link = os.path.join(self.egg_path, "epicscorelibs")
        if not os.path.exists(link):
            os.symlink(os.path.join(self.install_dir, "epicscorelibs"), link)



setup(
    cmdclass=dict(develop=Develop, **get_cmdclass()),
    version=__version__,
    ext_modules = [ext],
    install_requires = [
        # Dependency version declared in pyproject.toml
        epicscorelibs.version.abi_requires(),
        "pvxslibs>=1.3.2a2",
        "numpy",
        "epicsdbbuilder>=1.4",
        "pyyaml>=6.0"
    ],
    zip_safe = False,  # setuptools_dso is not compatible with eggs!
)
