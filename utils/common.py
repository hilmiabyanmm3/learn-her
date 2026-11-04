import io
import os
import openpyxl
import zipfile

RY_TO_EV = 13.605698066
H_PLANCK_EV_S = 4.135667696e-15
CM_TO_EV = 1.0 / 8065.544


def extract_zip_to_dict(zip_bytes: bytes) -> dict[str, bytes]:
  """Reads an uploaded zip byte stream into a path-to-bytes dictionary."""
  files = {}
  with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
    for name in zf.namelist():
      if not name.endswith("/"):
        files[name] = zf.read(name)
  return files


def build_zip_from_dict(file_dict: dict[str, bytes | str]) -> bytes:
  """Builds a zip byte stream from a dictionary of filenames and contents."""
  buffer = io.BytesIO()
  with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for path, content in file_dict.items():
      if isinstance(content, str):
        zf.writestr(path, content.encode("utf-8"))
      else:
        zf.writestr(path, content)
  buffer.seek(0)
  return buffer.getvalue()


def find_excel_file(files: dict[str, bytes]) -> tuple[str, bytes] | None:
  """Locates the single canonical project Excel spreadsheet in the files map.

  Standardizes strictly on `<SurfaceName>_her_data_sheet.xlsx`.
  If legacy or duplicate spreadsheets (e.g. `<SurfaceName>_data_sheet.xlsx`)
  exist in the uploaded zip, they are automatically purged from `files`
  to guarantee that only ONE single, updated spreadsheet is exported.
  """
  xlsx_keys = [
      p
      for p in list(files.keys())
      if p.endswith(".xlsx") and not os.path.basename(p).startswith("~$")
  ]
  if not xlsx_keys:
    return None

  # 1. Prioritize canonical `<SurfaceName>_her_data_sheet.xlsx`
  canonical_key = next(
      (p for p in xlsx_keys if "_her_data_sheet.xlsx" in p.lower()), None
  )

  # 2. Fallback to generic `_data_sheet.xlsx` if _her_ is not yet present
  if not canonical_key:
    canonical_key = next(
        (p for p in xlsx_keys if "data_sheet.xlsx" in p.lower()), xlsx_keys[0]
    )

  # 3. Purge any duplicate or obsolete secondary .xlsx files from the dictionary
  for p in xlsx_keys:
    if p != canonical_key and p in files:
      del files[p]

  return canonical_key, files[canonical_key]