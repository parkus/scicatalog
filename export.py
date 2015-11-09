from numpy import isfinite
import itertools as it
from string import ascii_lowercase

def aastex(filename, values, err=None, notes=None, refkeys=None, compactrefs=False, sigfigs_err=2, fmts=None,
           force_fmt=False, hdr=None):
    """
    Format the arrays for inclusion as the body of an AASTEX deluxetable using \input{filename}. The user should
    create the table header separately -- this just produces the body.

    Paramteres
    ----------
    filename : str
        Name of text file to output. File extension will NOT be appended.
    values : 2D array-like
        Values for the table entries. Items must be of type str, int, or float (but table need not be homogenous).
    err : 2D array-like or list of two 2D array-like
        Errors on the values. Use a list of two arrays to specify negative and positive errors (in that order).
    notes :
    refkeys : 2D array-like
        Reference keys for the values, with mutilple refs for a single value separated by commas. These should
        correspond to the keys used by the bibliography of your tex file.
    compactrefs : True|False
        If True, assign numbers to the references and list citations at the end of the body.
    sigfigs_err : int
        Number of significant figures to show on the error.
    fmts : 1D arra-like
        Format specifier for each column. Overridden by error signficiant figures unless force_fmt=True.
    force_fmt: True|False
        Force format specifier to be used in printing number instead of the error preicision, even if an error is
        given. In this case, the same prevision will be used for the error.
    hdr : str
        Optional header to print above the data block -- useful if you want to write you column headings,
        etc. into your code.

    Returns
    -------
    None, writes a file to filename.
    """
    Nrows = len(values)
    Ncols = len(values[0])

    if err is None:
        errneg = errpos = [[None]*Ncols]*Nrows
    else:
        if hasattr(err[0][0], '__iter__'):
            assert len(err) == 2
            errneg, errpos = err
        else:
            errneg = errpos = err

    # check that dimensions all agree
    arys = filter(lambda a: a is not None, [values, errneg, errpos, notes, refkeys])
    equal_lens = lambda l0, a: all([l0 == l for l in map(len, a)])
    if not equal_lens(Nrows, arys):
        raise ValueError('All input must have the same number of rows.')
    for ary in arys:
        if not equal_lens(Ncols, ary):
            raise ValueError('All rows of the input must be the same length.')
    if fmts is not None:
        assert len(fmts) == Ncols

    # determine which columns will have references
    if refkeys is not None:
        refsbycol = zip(*refkeys)
        hasrefs = [not all(map(_isnull, refcol)) for refcol in refsbycol]

    # go through writing out the table line by line
    lines = [] if hdr is None else [hdr]
    lines.append('\\startdata')
    notedict = {}
    reflist = []
    alphabet = iter(ascii_lowercase)
    for i in range(Nrows):
        items = []
        for j in range(Ncols):
            # make entry
            value = values[i][j]
            if type(value) is str:
                item = '\\nodata' if _isnull(value) else value
            else:
                item = _tex_fmt(values[i][j], errneg[i][j], errpos[i][j], sigfigs_err, fmts[j], force_fmt)

            # add any note
            if notes is not None:
                note = notes[i][j]
                if note in notedict:
                    mark = notedict[note]
                else:
                    mark = alphabet.next()
                    notedict[mark] = '' if _isnull(note) else note
                item += '\\tablenotemark{{{}}}'.format(mark)
            items.append(item)

            # add references
            if refkeys is not None and hasrefs[j]:
                entry = refkeys[i][j]
                if _isnull(entry):
                    items.append('')
                else:
                    refs = entry.split(',')
                    if compactrefs:
                        if not _isnull(entry):
                            klist = []
                            for ref in refs:
                                try:
                                    k = reflist.index(ref) + 1
                                except ValueError:
                                    reflist.append(ref)
                                    k = len(reflist)
                                klist.append(k)
                            klist = map(str, klist)
                            items.append(','.join(klist))
                    else:
                        refs = ['\\citet{{{}}}'.format(r) for r in refs]
                        items.append(','.join(refs))

        lines.append(' & '.join(items) + '\\\\')
    lines.append('\\enddata')
    lines.append('')

    # add note legend
    for note, mark in notedict.items():
        lines.append('\\tablenotetext{{{}}}{{{}}}'.format(mark, note))
    lines.append('')

    # add reference legend
    if refkeys is not None and compactrefs:
        entries = []
        for i, ref in enumerate(reflist):
            entries.append('({}) \\citealt{{{}}}'.format(i+1, ref))
        reflgnd = '\\tablerefs{' +  '; '.join(entries) + '}'
        lines.append(reflgnd)
        lines.append('')

    # write to file
    with open(filename, 'w') as f:
        f.write('\n'.join(lines))


def _tex_fmt(value, errneg, errpos, sigfigs_err, fmt, forcefmt):
    """Format a value for tex display, suing the errors to define the precision unless fmt is specified."""
    if _isnull(value):
        return '\\nodata'

    if _isnull(errneg):
        if fmt is None:
            raise ValueError('Format must be specified for values that have no error.')
        else:
            if 'f' in fmt:
                return fmt.format(value)
            if 'g' in fmt:
                return _fmt_sig(value, int(fmt[fmt.index('g') - 1]))
            elif 'e' in fmt:
                left, right, exp = _split_numstr(fmt.format(value))
                exp = exp.replace('+', '')
                return '${}.{}\\sn{{{}}}$'.format(left, right, exp)
            else:
                raise ValueError('Format {} not understood.'.format(fmt))
    else:
        if not forcefmt:
            errstrs = [_fmt_sig(e, sigfigs_err) for e in [errneg, errpos]]
            minsigdig = min(map(_min_sigdig, errstrs))
            basestr = '{:e}'.format(value)
            maxsigdig = _max_sigdig(basestr)
            sigfigs = maxsigdig - minsigdig + 1
            left, right, exp = _split_numstr(basestr)
            exp = exp.replace('+', '')
            precision = -minsigdig if minsigdig < 0 else 0
            decform = '{:.' + str(precision) + 'f}'
            decstr = decform.format(value)
            lendec = len(decstr)
            lenexp = sigfigs + 4 + 0.5 *len(exp)
            if lendec < lenexp:
                vstr = decstr
                enstr, epstr = [decform.format(e) for e in [errneg, errpos]]
                SN = False
            else:
                modvals = [v*10**-int(exp) for v in [value, errneg, errpos]]
                vstr, enstr, epstr = [('{:.' + str(sigfigs - 1) + 'f}').format(v) for v in modvals]
                SN = True

        else:
            if 'f' in fmt:
                vstr, enstr, epstr = [fmt.format(v) for v in [value, errneg, errpos]]
                SN = False
            elif 'e' in fmt:
                left, right, exp = _split_numstr(fmt.format(value))
                vstr = left + '.' + right
                precision = len(right)
                emod = [e*10**int(exp) for e in [errneg, errpos]]
                enstr, epstr = ['{:.' + str(precision) + 'f}' for e in emod]
                SN = True
            else:
                raise ValueError('Format {} not understood.'.format(fmt))

        if SN:
            exp = exp.replace('+', '')
            return '${}_{{-{}}}^{{+{}}}\\sn{{{}}}$'.format(vstr, enstr, epstr,  exp)
        else:
            if enstr == epstr:
                return '$ {} \\pm {} $'.format(vstr, enstr)
            else:
                return '${}_{{-{}}}^{{+{}}}$'.format(vstr, enstr, epstr)


def _fmt_sig(value, sigfigs):
    vstr = ('{:.' + str(sigfigs) + 'g}').format(value)
    left, right, exp = _split_numstr(vstr)
    if right and len(right) < sigfigs - 1:
        right += '0' * (sigfigs - 1 - len(right))
        return _join_numstr(left, right, exp)
    else:
        return vstr


def _split_numstr(numstr):
    if 'e' in numstr:
        left, exp = numstr.split('e')
    else:
        left, exp = numstr, ''
    if '.' in left:
        left, right = left.split('.')
    else:
        right = ''
    return left, right, exp


def _join_numstr(left, right, exp):
    str = left
    if right: str += '.' + right
    if exp: str += 'e' + exp
    return str


def _min_sigdig(numstr):
    """Get place of least significant digit, where the units place is 0 as with round()."""
    left, right, exp = _split_numstr(numstr)
    exp = int(exp) if exp else 0
    if right:
        return exp - len(right)
    else:
        while left.endswith('0'): left = left[:-1]
        return exp + len(left) - 1


def _max_sigdig(numstr):
    """Get place of most significant digit, where the units place is 0 as with round()."""
    left, right, exp = _split_numstr(numstr)
    exp = int(exp) if exp else 0
    if exp:
        return int(exp)
    else:
        if left == '0':
            cnt = 0
            while right.startswith('0'):
                cnt += 1
                right = right[1:]
            return -cnt - 1
        else:
            return len(left) - 1


def _isnull(value):
     if not value:
         return True
     if type(value) is str:
         return value.lower() == 'none'
     else:
         return not isfinite(value)