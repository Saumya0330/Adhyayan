import os

UPLOAD_DIR = "./data/uploads"

def save_uploaded_file(file_obj):
    # file_obj is a NamedString with .name that points to a temporary path
    temp_path = file_obj.name

    # Copy the file to your desired directory
    save_path = f"uploaded_files/{os.path.basename(temp_path)}"
    os.makedirs("uploaded_files", exist_ok=True)

    with open(temp_path, "rb") as src, open(save_path, "wb") as dst:
        dst.write(src.read())

    return save_path

