from typing import Callable
from flask import json, jsonify
from fastapi import UploadFile
from hashlib import sha1
from doc2json.grobid2json.process_pdf import process_pdf_stream
from doc2json.tex2json.process_tex import process_tex_stream
from doc2json.jats2json.process_jats import process_jats_stream


def _process_pdf(file: UploadFile) -> json:
    pdf_stream = file.stream
    pdf_content = pdf_stream.read()
    # compute hash
    pdf_sha = sha1(pdf_content).hexdigest()
    # get results
    results = process_pdf_stream(file.filename, pdf_sha, pdf_content)
    return jsonify(results)

def _process_gz(file: UploadFile) -> json:
    zip_stream = file.stream
    zip_content = zip_stream.read()
    # get results
    results = process_tex_stream(file.filename, zip_content)
    return jsonify(results)

def _process_nxml(file: UploadFile) -> json:
    xml_stream = file.stream
    xml_content = xml_stream.read()
    # get results
    results = process_jats_stream(file.filename, xml_content)
    return jsonify(results)

def unknow_type() -> json:
    return { "Error": "Unknown file type!" }

FILE_TYPES: dict[str, Callable] = {
    'pdf': _process_pdf(),
    'gz': _process_gz(),
    'nxml': _process_nxml()
}