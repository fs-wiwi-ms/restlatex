import pytest
from app.parser import parse_tex_log


def test_parse_undefined_control_sequence():
    log = r"""
This is pdfTeX, Version 3.141592653-2.6-1.40.24 (TeX Live 2022/Debian)
entering extended mode
(./input.tex
LaTeX2e <2022-11-01> patch level 1
! Undefined control sequence.
l.6 \invalidcommand
                   {test}
The control sequence at the end of the top line
of your error message was never \def'ed.
! ==> Fatal error occurred, no output PDF file produced!
"""
    result = parse_tex_log(log)
    assert "! Undefined control sequence" in result
    assert "Line: 6" in result
    assert r"\invalidcommand" in result


def test_parse_package_error():
    log = r"""
! Package amsmath Error: Erroneous nesting of equation structures;
(amsmath)                trying to recover with `aligned'.

See the amsmath package documentation for explanation.
Type  H <return>  for immediate help.
 ...                                              
                                                  
l.12 \end{equation}
"""
    result = parse_tex_log(log)
    assert "! Package amsmath Error" in result
    assert "Line: 12" in result
    assert r"\end{equation}" in result


def test_parse_file_not_found():
    log = r"""
! LaTeX Error: File `nonexistent.sty' not found.

Type X to quit or <RETURN> to proceed,
or enter new name. (Default extension: sty)

Enter file name: 
! Emergency stop.
<read *> 
         
l.4 \usepackage
               {nonexistent}
"""
    result = parse_tex_log(log)
    assert "nonexistent.sty' not found" in result
    assert "Line: 4" in result
    assert r"\usepackage" in result


def test_parse_fallback_when_no_exclamation():
    result = parse_tex_log("", stderr_fallback="bwrap: fatal error occurred")
    assert "Compilation process error:" in result
    assert "bwrap: fatal error occurred" in result
