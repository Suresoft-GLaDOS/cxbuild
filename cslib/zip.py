import zipfile
import os


def zip_project(src_path, dest_file):
    with zipfile.ZipFile(dest_file, 'w') as zf:
        root_path = src_path
        for (path, directory, files) in os.walk(src_path):
            for i in files:
                full_path = os.path.join(path, i)
                relative_path = os.path.relpath(full_path, root_path)
                zf.write(full_path, relative_path, zipfile.ZIP_DEFLATED)
        zf.close()


def zip_folder(src_directory):
    dest_zip_path = os.path.abspath(os.path.join(src_directory + ".zip"))
    zip_project(src_directory, dest_zip_path)
    return dest_zip_path


def zip_file(src_file, dest_zip_path):
    with zipfile.ZipFile(dest_zip_path, 'w') as zf:
        root_path = os.path.dirname(src_file)
        full_path = src_file
        relative_path = os.path.relpath(full_path, root_path)
        zf.write(full_path, relative_path, zipfile.ZIP_DEFLATED)
        zf.close()
    return dest_zip_path

