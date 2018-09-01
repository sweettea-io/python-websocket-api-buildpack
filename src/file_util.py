"""
Utility methods related to files or their respective paths.
"""
import os
import shutil
import zipfile


def upsert_parent_dirs(filepath):
  """
  Similar to os.makedirs, but ignores filename and doesn't raise an error when
  a directory is already in existence...it just skips it.

  :param str filepath: File path to upsert all parent directories for
  """
  comps = [c for c in filepath.split('/') if c]
  comps.pop()

  if filepath.startswith('/'):
    path = '/'
  else:
    path = ''

  for dir in comps:
    path += (dir + '/')

    if not os.path.exists(path):
      try:
        os.mkdir(path)
      except:
        pass


def extract_in_place(archive_path):
  """
  Unpack a zipfile in place and remove it upon completion.

  Ex:
    extract_in_place('path/to/archive.zip')
    # => creates 'path/to/archive/' directory and removes original 'path/to/archive.zip' file.

  :param str archive_path: Path to zipfile
  :return: Path to directory where zipfile contents were extracted
  :rtype: str
  """
  filename_w_ext = archive_path.split('/').pop()  # e.g. model.zip
  ext = filename_w_ext.split('.').pop()           # e.g. zip
  extract_dir = archive_path[:-(len(ext) + 1)]    # e.g. /path/to/model

  # Remove destination dir if it already exists.
  if os.path.exists(extract_dir) and os.path.isdir(extract_dir):
    shutil.rmtree(extract_dir)

  # Unpack the archive.
  archive = zipfile.ZipFile(archive_path)
  archive.extractall(extract_dir)
  archive.close()

  # Remove the archive file.
  if os.path.exists(archive_path):
    os.remove(archive_path)

  return extract_dir
