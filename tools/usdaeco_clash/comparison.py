"""Compare measured routes by element pair, retaining each uncertainty band."""


def decided(row):
    if row is None:
        return False
    if row.get('evidence', {}).get('method') == 'exact':
        return row['evidence']['band_decides']
    # A mesh surface inside its deflection band cannot settle hit versus miss,
    # even if a nominal touching tolerance happens to be wider than the band.
    return abs(row['distance']) > row['uncertainty']


def verdict(row):
    return row['kind'] if decided(row) else 'undecidable'


def comparison_rows(mesh, exact=None, reason=None):
    def indexed(rows):
        result = {}
        for row in rows:
            key = tuple(sorted(row['elements']))
            if key in result:
                raise ValueError('Comparison requires one result per pair and route')
            result[key] = row
        return result
    left, right = indexed(mesh), indexed(exact or [])
    result = []
    for pair in sorted(left.keys() | right.keys()):
        a, b = left.get(pair), right.get(pair)
        routes = [method for method, row in (('mesh', a), ('exact', b)) if decided(row)]
        settled = 'both' if len(routes) == 2 else routes[0] if routes else 'neither'
        if len(routes) == 2 and a['kind'] != b['kind']:
            settled = 'disagreement'
        row = dict(elements=list(pair), decided_by=settled)
        for method, value in (('mesh', a), ('exact', b)):
            row[method] = (dict(kind=value['kind'], distance=value['distance'], volume=value.get('volume'),
                                uncertainty=value['uncertainty'], verdict=verdict(value)) if value else
                           dict(verdict='NOT RUN' if method == 'exact' and exact is None else 'not reported',
                                reason=reason or 'No result within the reporting threshold'))
        result.append(row)
    return result


def compare(mesh, exact=None, reason=None, labels=None):
    lines = ['pair | mesh distance (m) | mesh volume (m³) | mesh uncertainty (m) | mesh verdict | exact distance (m) | exact volume (m³) | exact uncertainty (m) | exact verdict | decided by',
             '--- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- | ---']
    for row in comparison_rows(mesh, exact, reason):
        label = (labels or {}).get(tuple(row['elements']), ' / '.join(p.rsplit('/',1)[-1] for p in row['elements']))
        cells = [label]
        for method in ('mesh','exact'):
            data = row[method]
            cells.extend('—' if data.get(k) is None else format(data[k], '.9g') for k in ('distance','volume','uncertainty'))
            cells.append(data['verdict'] + (' ('+data['kind']+')' if data.get('kind') and data['verdict'] != data['kind'] else ''))
        cells.append(row['decided_by'])
        lines.append(' | '.join(cells))
    if exact is None:
        lines.append('\nExact NOT RUN: ' + (reason or 'No exact results supplied.'))
    lines.append('\nExact overlap distance is negative zero: common volume decides hard clashes; the bridge does not calculate penetration depth. Mesh volume is not measured.')
    return '\n'.join(lines)
