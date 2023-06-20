import os
from pathlib import Path
import re
from typing import Any
import requests
from bs4 import BeautifulSoup
import toml

CACHE = Path(f"{os.environ['HOME']}/.gmx_sim")


class CachedMdpOptions(dict):
    """ Cache the mdp options for different gmx versions."""
    def __init__(self) -> None:
        super().__init__()
        self.cache_file = CACHE / "mdp_options.toml"
        if not CACHE.exists():
            CACHE.mkdir(parents=True)
        if self.cache_file.exists():
            for key, item in toml.load(self.cache_file).items():
                self[key] = item

    def __setitem__(self, __key: Any, __value: Any) -> None:
        """ Save to cache if new item is added."""
        store = False
        if __key not in self:
            store = True
        return_val = super().__setitem__(__key, __value)
        if store:
            with open(self.cache_file, "w", encoding="utf-8") as fh:
                toml.dump(self, fh)
        return return_val


def get_mdp_options(gmx_version: str) -> list[str]:
    """ Query gmx manual to get all legal mdp options for this version.
    We add the text of some html elements that do not belong but it is minor.
    We could also get information about the mdp options, but that might
    need to be added, later. Checks if result is cached, otherwise queries
    the gmx manual and caches the result.
    Arguments:
        gmx_version (str): The gmx version to query. Must be of the form
            2020 or 2020.1
    Returns:
        mdp_options (list): A list of all legal mdp options for this version
            plus some html elements that do not belong.
    """
    # check that gmx version is legal
    gmx_version = gmx_version.strip("")
    gmx_version = gmx_version.strip("\n")
    if not re.match(r"^\d+(.\d+)?$", gmx_version):
        raise ValueError(f"Invalid {gmx_version=}")
    url = f"https://manual.gromacs.org/documentation/{gmx_version}/user-guide/mdp-options.html"
    cache = CachedMdpOptions()
    if url in cache:
        return cache[url]

    # Make request and parse html
    response = requests.get(url, timeout=100)
    soup = BeautifulSoup(response.content, "html.parser")

    mdp_options = []
    hits = soup.find_all("a")
    if len(hits) == 0:
        raise RuntimeError(f"Could not find hits for {gmx_version=}")
    for hit in hits:
        href = hit.attrs.get("href")
        if "mdp" in href:
            text = hit.get_text()
            if text != "¶":
                mdp_options.append(text)
    cache[url] = mdp_options
    return mdp_options
