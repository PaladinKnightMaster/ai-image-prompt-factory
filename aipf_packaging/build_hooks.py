"""setuptools command hooks that stage knowledge before sdist/wheel builds."""
from __future__ import annotations

from setuptools.command.build_py import build_py as _build_py
from setuptools.command.sdist import sdist as _sdist

from aipf_packaging.stage_knowledge import filter_sdist_knowledge_files, stage_knowledge


class build_py(_build_py):
    def run(self) -> None:
        stage_knowledge()
        super().run()


class sdist(_sdist):
    def run(self) -> None:
        stage_knowledge()
        super().run()

    def make_distribution(self) -> None:
        # setuptools sdist.run() builds the file list via egg_info and never
        # calls get_file_list(); filter here so only inventory knowledge ships.
        if getattr(self, "filelist", None) is not None:
            self.filelist.files = filter_sdist_knowledge_files(list(self.filelist.files))
        super().make_distribution()
