import os
import shutil

UPLOAD_DIR = "./data/uploads"

def save_uploaded_file(upload_file):
    """
    Save uploaded file from FastAPI UploadFile object
    """
    # Create upload directory if it doesn't exist
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    # Generate file path
    file_path = os.path.join(UPLOAD_DIR, upload_file.filename)
    
    # Save the file
    with open(file_path, "wb") as buffer:
        # Copy the file content to the new location
        shutil.copyfileobj(upload_file.file, buffer)
    
    return file_path
