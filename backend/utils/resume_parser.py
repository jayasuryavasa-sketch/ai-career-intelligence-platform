from pathlib import Path
from werkzeug.utils import secure_filename
from utils.error_handler import ApiError

ALLOWED={"pdf","docx","txt"}
def extract(file):
 name=secure_filename(file.filename or "")
 if not name or "." not in name or name.rsplit(".",1)[1].lower() not in ALLOWED: raise ApiError("Upload a PDF, DOCX, or TXT resume.")
 data=file.read(5*1024*1024+1); file.stream.seek(0)
 if len(data)>5*1024*1024: raise ApiError("Please upload a file smaller than 5 MB.",413,"file_too_large")
 ext=name.rsplit(".",1)[1].lower()
 try:
  if ext=="txt": content=data.decode("utf-8-sig")
  elif ext=="pdf":
   import io
   from PyPDF2 import PdfReader
   content="\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(data)).pages)
  else:
   import io
   from docx import Document
   content="\n".join(p.text for p in Document(io.BytesIO(data)).paragraphs)
 except Exception as e: raise ApiError("We could not read this document. Try exporting it as PDF, DOCX, or TXT.")
 if not content.strip(): raise ApiError("No readable text was found in the resume.")
 return name,content[:60000]
