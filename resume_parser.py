import re
from pathlib import Path
from typing import Union

import pymupdf


_NOISE_PATTERNS = [
    r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b",  # dates like 12/05/2024
    r"\b\+?\d[\d\s().-]{7,}\b",              # phone numbers
    r"\b\S+@\S+\.\S+\b",                     # email
    r"https?://\S+|www\.\S+",                # urls
    r"\blinkedin\.com/\S+\b",
    r"\bgithub\.com/\S+\b",
]


def parse_resume_pdf(pdf_path: Union[str, Path]) -> str:
    """
    Extract and clean text from a resume PDF.

    Keeps content such as skills and experience as full as possible while
    removing common contact/header noise.

    Parameters
    ----------
    pdf_path:
        Path to a PDF file or a file-like object containing PDF bytes.

    Returns
    -------
    str
        Cleaned resume text.
    """
    doc = pymupdf.open(pdf_path)
    raw_text = '\n'.join([page.get_text() for page in doc])

    # Normalize whitespace and line endings
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    cleaned_lines = []
    seen_header_block = False

    for line in lines:
        lower = line.lower()

        # Skip obvious contact/header noise
        if any(re.search(pattern, line, flags=re.IGNORECASE) for pattern in _NOISE_PATTERNS):
            continue

        # Remove lines that are mostly contact info or separators
        if re.fullmatch(r"[-_=•·| ]+", line):
            continue

        if len(cleaned_lines) < 5 and (
            re.search(r"\b(resume|curriculum vitae|cv)\b", lower)
            or re.search(r"\b(email|phone|mobile|linkedin|github|address)\b", lower)
        ):
            continue

        # Many resumes start with name/contact block; once we hit a substantive line, keep going
        if len(line.split()) <= 4 and not re.search(r"\b(skills|experience|education|projects|summary)\b", lower):
            # likely name or short header; skip only in the opening lines
            continue

        cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)
    # Remove repeated excessive blank lines if any
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text