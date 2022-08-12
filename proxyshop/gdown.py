"""
Modified from Gdown Project
Source: https://github.com/wkentaro/gdown
License: https://github.com/wkentaro/gdown/blob/main/LICENSE
"""
from __future__ import print_function
from pathlib import Path
import os
import os.path as osp
import re
import shutil
import sys
import tempfile
import textwrap
import requests

CHUNK_SIZE = 1024 * 1024  # 512KB
home = osp.expanduser("~")


def get_url_from_gdrive_confirmation(contents):
    url = ""
    for line in contents.splitlines():
        m = re.search(r'href="(\/uc\?export=download[^"]+)', line)
        if m:
            url = "https://docs.google.com" + m.groups()[0]
            url = url.replace("&amp;", "&")
            break
        m = re.search('id="downloadForm" action="(.+?)"', line)
        if m:
            url = m.groups()[0]
            url = url.replace("&amp;", "&")
            break
        m = re.search('"downloadUrl":"([^"]+)', line)
        if m:
            url = m.groups()[0]
            url = url.replace("\\u003d", "=")
            url = url.replace("\\u0026", "&")
            break
        m = re.search('<p class="uc-error-subcaption">(.*)</p>', line)
        if m:
            error = m.groups()[0]
            raise RuntimeError(error)
    if not url:
        raise RuntimeError(
            "Cannot retrieve the public link of the file. "
            "You may need to change the permission to "
            "'Anyone with the link', or have had many accesses."
        )
    return url


def download(
    file_id: str,
    path: str,
    callback: any
):
    """
    Download file from Gdrive ID.

    Parameters
    ----------
    file_id: str
        Google Drive's file ID.
    path: str
        Output path.
    callback: any
        Function to call on each chunk downloaded.

    Returns
    -------
    output: bool
        True if success, False if failed.
    """
    url = "https://drive.google.com/uc?id={id}".format(id=file_id)
    current = 0
    url_origin = url
    sess = requests.session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36"  # NOQA
    }

    # Get file resource
    while True:
        res = sess.get(url, headers=headers, stream=True, verify=True)

        if "Content-Disposition" in res.headers:
            # This is the file
            break

        # Need to redirect with confirmation
        try:
            url = get_url_from_gdrive_confirmation(res.text)
        except RuntimeError as e:
            print("Access denied with the following error:")
            error = "\n".join(textwrap.wrap(str(e)))
            print("\n", error, "\n", file=sys.stderr)
            print(
                "You may still be able to access the file from the browser:",
                file=sys.stderr,
            )
            print("\n\t", url_origin, "\n", file=sys.stderr)
            return False

    # Ensure path exists
    Path(os.path.dirname(Path(path))).mkdir(mode=511, parents=True, exist_ok=True)
    total = int(res.headers.get("Content-Length"))

    existing_tmp_files = []
    file_name = osp.basename(path)
    for file in os.listdir(osp.dirname(path) or "."):
        if file.startswith(file_name) and file != file_name:
            existing_tmp_files.append(osp.join(osp.dirname(path), file))
    if len(existing_tmp_files) != 0:
        tmp_file = existing_tmp_files[0]
        current = int(os.path.getsize(tmp_file))
        resume = True
    else:
        resume = False
        # mkstemp is preferred, but does not work on Windows
        # https://github.com/wkentaro/gdown/issues/153
        tmp_file = tempfile.mktemp(
            suffix=tempfile.template,
            prefix=osp.basename(path),
            dir=osp.dirname(path),
        )
    f = open(tmp_file, "ab")

    if tmp_file is not None and f.tell() != 0:
        headers["Range"] = "bytes={}-".format(f.tell())
        res = sess.get(url, headers=headers, stream=True, verify=True)

    # Let the user know its downloading
    print("Downloading...", file=sys.stderr)
    if resume:
        print("Resume:", tmp_file, file=sys.stderr)
    print("From:", url_origin, file=sys.stderr)
    print("To:", path, file=sys.stderr)

    # Try to download
    try:

        for chunk in res.iter_content(chunk_size=CHUNK_SIZE):
            f.write(chunk)
            current += int(CHUNK_SIZE)
            if callback:
                callback(current, total)
        if tmp_file:
            f.close()
            shutil.move(tmp_file, path)
    except IOError as e:
        print(e, file=sys.stderr)
        return False
    finally:
        sess.close()

    return True