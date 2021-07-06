import os
import sys

from setuptools.command.develop import develop
import epicscorelibs.path
import epicscorelibs.version
from setuptools_dso import Extension, setup
from epicscorelibs.config import get_config_var
from wheel.bdist_wheel import bdist_wheel

# Place the directory containing _version_git on the path
for path, _, filenames in os.walk(os.path.dirname(os.path.abspath(__file__))):
    if "_version_git.py" in filenames:
        sys.path.append(path)
        break

from _version_git import __version__, get_cmdclass  # noqa

sources = ['softioc/extension.c']

devIocStats_OSI = [
    "devIocStatsAnalog.c",
    "devIocStatsString.c",
    "devIocStatsWaveform.c",
    "devIocStatsSub.c",
    "devIocStatsTest.c",
    "devIocStats.h",
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
    "devIocStatsOSD.h",
]

devIocStats_src = os.path.join("iocStats", "devIocStats")
devIocStats_os = os.path.join(devIocStats_src, "os", get_config_var('OS_CLASS'))
devIocStats_default = os.path.join(devIocStats_src, "os", "default")

def _add_file(f):
    if f.endswith(".h"):
        # Only add header files if making an sdist
        # https://github.com/pypa/packaging-problems/issues/84#issuecomment-383718492
        should_add = "sdist" in sys.argv
    else:
        should_add = True
    if should_add:
        sources.append(f)

for f in devIocStats_OSI:
    _add_file(os.path.join(devIocStats_src, f))
for f in devIocStats_OSD:
    if os.path.exists(os.path.join(devIocStats_os, f)):
        _add_file(os.path.join(devIocStats_os, f))
    else:
        _add_file(os.path.join(devIocStats_default, f))

# Extension with all our C code
ext = Extension(
    name='softioc._extension',
    sources = sources,
    include_dirs=[
        epicscorelibs.path.include_path,
        devIocStats_src, devIocStats_os, devIocStats_default
    ],
    dsos = [
        'epicscorelibs.lib.qsrv',
        'epicscorelibs.lib.pvAccessIOC',
        'epicscorelibs.lib.pvAccess',
        'epicscorelibs.lib.pvData',
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


class Wheel(bdist_wheel):
    def get_tag(self):
        impl, abi_tag, plat_name = bdist_wheel.get_tag(self)
        # We want to produce manylinux tagged builds, but can't use
        # auditwheel as it isn't compatible with setuptools_dso
        # override the tag here as cibuildwheel won't let us do this
        plat_name = os.environ.get("AUDITWHEEL_PLAT", plat_name)
        return (impl, abi_tag, plat_name)


setup(
    cmdclass=dict(develop=Develop, bdist_wheel=Wheel, **get_cmdclass()),
    version=__version__,
    ext_modules = [ext],
    install_requires = [
        # Dependency version declared in pyproject.toml
        epicscorelibs.version.abi_requires(),
        "numpy",
        "epicsdbbuilder>=1.4"
    ],
    zip_safe = False,  # setuptools_dso is not compatible with eggs!
)
