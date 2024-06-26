#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
import os
import os.path as osp
import re
import shutil
import sys
import tempfile
import requests
import six
import tqdm

CHUNK_SIZE = 512 * 1024  # 512KB

def extractDownloadLink(contents):
    for line in contents.splitlines():
        m = re.search(r'href="(https://download[^"]+)', line)
        if m:
            return m.groups()[0]
    return None

def download(url, output=None, quiet=False):
    url_origin = url.replace('http://', 'https://')
    sess = requests.Session()
    sess.headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    }

    while True:
        try:
            res = sess.get(url_origin, stream=True, verify=True)
        except requests.exceptions.SSLError as e:
            print(f"SSL error: {e}", file=sys.stderr)
            return
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}", file=sys.stderr)
            return

        if 'Content-Disposition' in res.headers:
            # This is the file
            break

        # Need to redirect with confirmation
        url_origin = extractDownloadLink(res.text)

        if url_origin is None:
            print(f'Permission denied: {url}', file=sys.stderr)
            print("Maybe you need to change permission to 'Anyone with the link'?", file=sys.stderr)
            return

    if output is None:
        m = re.search('filename="(.*)"', res.headers['Content-Disposition'])
        if m:
            output = m.groups()[0]
            output = output.encode('iso8859').decode('utf-8')
        else:
            output = osp.basename(url_origin)

    output_is_path = isinstance(output, six.string_types)

    if not quiet:
        print('Downloading...', file=sys.stderr)
        print('From:', url_origin, file=sys.stderr)
        print('To:', osp.abspath(output) if output_is_path else output, file=sys.stderr)

    if output_is_path:
        tmp_file = tempfile.mktemp(suffix='.tmp', prefix=osp.basename(output), dir=osp.dirname(output))
        f = open(tmp_file, 'wb')
    else:
        tmp_file = None
        f = output

    try:
        total = res.headers.get('Content-Length')
        if total is not None:
            total = int(total)
        if not quiet:
            pbar = tqdm.tqdm(total=total, unit='B', unit_scale=True)
        for chunk in res.iter_content(chunk_size=CHUNK_SIZE):
            f.write(chunk)
            if not quiet:
                pbar.update(len(chunk))
        if not quiet:
            pbar.close()
        if tmp_file:
            f.close()
            shutil.move(tmp_file, output)
    except IOError as e:
        print(e, file=sys.stderr)
        return
    finally:
        try:
            if tmp_file:
                os.remove(tmp_file)
        except OSError:
            pass
    return output


def main():
    desc = 'Simple command-line script to download files from Mediafire'
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('url', nargs='+')
    parser.add_argument('-o', '--output', help='output filename')
    args = parser.parse_args()

    if len(args.url) == 1 and args.output:
        download(args.url[0], args.output, quiet=False)
    else:
        for url in args.url:
            download(url, output=None, quiet=False)

if __name__ == "__main__":
    main()
