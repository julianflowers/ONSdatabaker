#!/usr/bin/python

"""
Usage:
  bake.py [options] <recipe> <spreadsheet> [<params>...]

Options:
  --notiming            Suppress timing information.
  --preview             Preview selected cells in Excel.
  --nocsv               Don't produce CSV file.
  --debug               Debug Mode
  --nolookuperrors      Dont output 'NoLookuperror' to final CSV.
"""

import atexit
import codecs
import imp
import re
import sys
sys.stdout = codecs.getwriter('utf-8')(sys.stdout)

from timeit import default_timer as timer

from docopt import docopt
import xypath
import xypath.loader
from utf8csv import UnicodeWriter
import os.path

import bake
from constants import *
import overrides        # warning: changes xypath and messytables
import warnings
import xlutils.copy
import xlwt
import richxlrd.richxlrd as richxlrd
from datetime import datetime
import string

# If there's a custom template, use it. Otherwise use the default.
try:
    import structure_csv_user as template
    from structure_csv_user import *
except ImportError:
    import structure_csv_default as template
    from structure_csv_default import *


__version__ = "1.0.7"
Opt = None
crash_msg = []

def dim_name(dimension):
    if isinstance(dimension, int) and dimension <= 0:
        # the last dimension is dimension 0; but we index it as -1.
        return template.dimension_names[dimension-1]
    else:
        return dimension

# should agree with constants.py

class DimensionError(Exception):
    pass


def showtime(msg='unspecified'):
    if not Opt.timing:
        return
    global last
    t = timer()
    print "{}: {:.3f}s,  {:.3f}s total".format(msg, t - last, t - start)
    last = t

def onexit():
    return showtime('exit')

start = timer()
last = start

def rewrite_headers(row,dims):
    for i in range(0,len(row)):
        if i >= len(template.start.split(',')):
            which_cell_in_spread = (i - len(template.start.split(','))) % len(template.value_spread)
            which_dim = (i - len(template.start.split(','))) / len(template.value_spread)
            which_dim = int(which_dim)
            if template.value_spread[which_cell_in_spread] == 'value':
                row[i] = dims[which_dim]
    return row

def datematch(date, silent=False):
    """match mmm yyyy, mmm-mmm yyyy, yyyy Qn, yyyy"""
    if not isinstance(date, basestring):
        if isinstance(date, float) and date>=1000 and date<=9999 and int(date)==date:
            return "Year"
        if not silent:
            warnings.warn("Couldn't identify date {!r}".format(date))
        return ''
    d = date.strip()
    if re.match('\d{4}$', d):
        return 'Year'
    if re.match('\d{4} [Qq]\d$', d):
        return 'Quarter'
    if re.match('[A-Za-z]{3}-[A-Za-z]{3} \d{4}$', d):
        return 'Quarter'
    if re.match('[A-Za-z]{3} \d{4}$', d):
        return 'Month'
    if not silent:
        warnings.warn("Couldn't identify date {!r}".format(date))
    return ''

def parse_ob(ob):
    if isinstance(ob.value, datetime):
        return (ob.value, '')
    if isinstance(ob.value, float):
        return (ob.value, '')
    if ob.properties['richtext']:
        string = richxlrd.RichCell(ob.properties.cell.sheet, ob.y, ob.x).fragments.not_script.value
    else:
        string = ob.value
    value, datamarker = re.match(r"([-+]?[0-9]+\.?[0-9]*)?(.*)", string).groups()
    if value is None:
        value = ''
    return value.strip(), datamarker.strip()


class Options(object):
    def __init__(self):
        options = docopt(__doc__, version='databaker {}'.format(__version__))
        self.xls_files = [options['<spreadsheet>']]
        self.recipe_file = options['<recipe>']
        self.timing = not options['--notiming']
        self.preview = options['--preview']
        self.preview_filename = "preview-{spreadsheet}-{recipe}-{params}.xls"
        self.csv_filename = "data-{spreadsheet}-{recipe}-{params}.csv"
        self.csv = not options['--nocsv']
        self.debug = options['--debug']
        self.no_lookup_error = not options['--nolookuperrors']
        self.params = options['<params>']

class TechnicalCSV(object):
    def __init__(self, filename):
        self.filehandle = open(filename, "wb")
        self.csv_writer = UnicodeWriter(self.filehandle)
        self.row_count = 0
        self.header_dimensions = None

    def write_header_if_needed(self, dimensions, ob):
        if self.header_dimensions is not None:
            # we've already written headers.
            return
        self.header_dimensions = dimensions
        header_row = template.start.split(',')

        # create new header row
        for i in range(dimensions):
            header_row.extend(template.repeat.format(num=i+1).split(','))

        # overwrite dimensions/subject/name as column header (if requested)
        if template.topic_headers_as_dims:
            dims = []
            for dimension in range(1, ob._cell.table.max_header+1):
                dims.append(ob._cell.table.headernames[dimension])
            header_row = rewrite_headers(header_row, dims)

        # Write to the file
        self.csv_writer.writerow(header_row)


    def footer(self):
        self.csv_writer.writerow(["*"*9, str(self.row_count)])
        self.filehandle.close()

    def handle_observation(self, ob):
        number_of_dimensions = ob.table.max_header
        self.write_header_if_needed(number_of_dimensions, ob)
        output_row = self.get_dimensions_for_ob(ob)
        self.output(output_row)

    def output(self, row):
        def translator(s):
            if not isinstance(s, basestring):
                return unicode(s)
            # this is slow. We can't just use translate because some of the
            # strings are unicode. This adds 0.2 seconds to a 3.4 second run.
            return unicode(s.replace('\n',' ').replace('\r', ' '))
        self.csv_writer.writerow([translator(item) for item in row])
        self.row_count += 1

    def get_dimensions_for_ob(self, ob):
        def cell_for_dimension(dimension):
            # implicit: obj
            try:
                cell = obj.table.headers.get(dimension, lambda _: None)(obj)
            except xypath.xypath.NoLookupError:
                print "no lookup to dimension {} from cell {}".format(dim_name(dimension), repr(ob._cell))
                if Opt.no_lookup_error:
                    cell = "NoLookupError"            # if user wants - output 'NoLookUpError' to CSV
                else:
                    cell = ''                         # Otherwise output a blanks
            return cell

        def value_for_dimension(dimension):
            # implicit: obj
            cell = cell_for_dimension(dimension)
            if cell is None:
                value = ''
            elif isinstance(cell, (basestring, float)):
                value = cell
            elif cell.properties['richtext']:
                value = richxlrd.RichCell(cell.properties.cell.sheet, cell.y, cell.x).fragments.not_script.value
            else:
                value = cell.value
            return value

        # TODO not really 'self'y
        """For a single observation cell, provide all the
           information for a single CSV row"""
        out = {}
        obj = ob._cell
        keys = ob.table.headers.keys()


        # Get fixed headers.
        values = {}
        values[OBS] = obj.value

        LAST_METADATA = 0 # since they're numbered -9 for obs, ... 0 for last one
        for dimension in range(OBS+1, LAST_METADATA + 1):
            values[dimension] = value_for_dimension(dimension)

        # Mutate values
        # Special handling per dimension.
        # NOTE  - variables beginning SH_ ... are dependent on user choices from the template file

        if template.SH_Split_OBS:
            if not isinstance(values[OBS], float):  # NOTE xls specific!
                ob_value, dm_value = parse_ob(ob)
                values[OBS] = ob_value
                # the observation is not actually a number
                # store it as a datamarker and nuke the observation field
                if values[template.SH_Split_OBS] == '':
                    values[template.SH_Split_OBS] = dm_value
                elif dm_value:
                    logging.warn("datamarker lost: {} on {!r}".format(dm_value, ob))

        if template.SH_Create_ONS_time:
            if values[TIMEUNIT] == '' and values[TIME] != '':
                # we've not actually been given a timeunit, but we have a time
                # determine the timeunit from the time
                values[TIMEUNIT] = datematch(values[TIME])

        for dimension in range(OBS, LAST_METADATA + 1):
            yield values[dimension]
            if dimension in template.SH_Repeat:         # Calls special handling - repeats
                yield values[dimension]
            for i in range(0, template.SKIP_AFTER[dimension]):
                yield ''

        for dimension in range(1, obj.table.max_header+1):
            name = obj.table.headernames[dimension]
            value = value_for_dimension(dimension)
            topic_headers = template.get_topic_headers(name, value)
            for col in topic_headers:
                yield col


class Progress(object):
    # creates a progress bar
    def __init__(self, max_count, prefix=None, msg="\r{}{:3d}% - [{}{}]"):
        self.last_percent = None
        self.max_count = max_count
        self.msg = msg
        if prefix is not None:
            self.prefix = prefix + ' - '
        else:
            self.prefix = ''

    def update(self, count):
        percent = (((count+1) * 100) // self.max_count)
        if percent != self.last_percent:
            progress = percent / 5
            print self.msg.format(self.prefix, percent, '='*progress, " "*(20-progress)),
            sys.stdout.flush()
            self.last_percent = percent

def per_file(spreadsheet, recipe):
    def filenames():
        get_base = lambda filename: os.path.splitext(os.path.basename(filename))[0]
        xls_directory = os.path.dirname(spreadsheet)
        xls_base = get_base(spreadsheet)
        recipe_base = get_base(Opt.recipe_file)
        parsed_params = ','.join(Opt.params)

        csv_filename = Opt.csv_filename.format(spreadsheet=xls_base,
                                               recipe=recipe_base,
                                               params=parsed_params)

        csv_path = os.path.join(xls_directory, csv_filename)

        preview_filename = Opt.preview_filename.format(spreadsheet=xls_base,
                                                       recipe=recipe_base,
                                                       params=parsed_params)
        preview_path = os.path.join(xls_directory, preview_filename)
        return {'csv': csv_path, 'preview': preview_path}

    def make_preview():
        # call for each segment
        for i, header in tab.headers.items():
            if hasattr(header, 'bag') and not isinstance(header.bag, xypath.Table):
                for bag in header.bag:
                    writer.get_sheet(tab.index).write(bag.y, bag.x, bag.value,
                        xlwt.easyxf('pattern: pattern solid, fore-colour {}'.format(colourlist[i])))
                for ob in segment:
                    writer.get_sheet(tab.index).write(ob.y, ob.x, ob.value,
                        xlwt.easyxf('pattern: pattern solid, fore-colour {}'.format(colourlist[OBS])))


    tableset = xypath.loader.table_set(spreadsheet, extension='xls')
    showtime("file {!r} imported".format(spreadsheet))
    if Opt.preview:
        writer = xlutils.copy.copy(tableset.workbook)
    if Opt.csv:
        csv_file = filenames()['csv']
        csv = TechnicalCSV(csv_file)
    tabs = list(xypath.loader.get_sheets(tableset, recipe.per_file(tableset)))
    if not tabs:
        print "No matching tabs found."
        exit(1)
    for tab_num, tab in enumerate(tabs):
        try:
            showtime("tab {!r} imported".format(tab.name))
            pertab = recipe.per_tab(tab)
            if isinstance(pertab, xypath.xypath.Bag):
                pertab = [pertab]

            for seg_id, segment in enumerate(pertab):
                try:
                    if Opt.debug:
                        print "tab and segment available for interrogation"
                        import pdb; pdb.set_trace()

                    if Opt.preview:
                        make_preview()

                    if Opt.csv:
                        obs_count = len(segment)
                        progress = Progress(obs_count, 'Tab {}'.format(tab_num + 1))
                        for ob_num, ob in enumerate(segment):  # TODO use const
                            try:
                                csv.handle_observation(ob)
                            except Exception:
                                crash_msg.append("ob: {!r}".format(ob))
                                raise
                            progress.update(ob_num)
                        print
                    # hacky observation wiping
                    tab.headers = {}
                    tab.max_header = 0
                    tab.headernames = [None]
                except Exception:
                    crash_msg.append("segment: {!r}".format(seg_id))
                    raise
        except Exception:
            crash_msg.append("tab: {!r} {!r}".format(tab_num, tab.name))
            raise


    if Opt.csv:
        csv.footer()
    if Opt.preview:
        writer.save(filenames()['preview'])

def create_colourlist():
    # Function to dynamically assign colours to dimensions for preview
    "https://github.com/python-excel/xlwt/blob/master/xlwt/Style.py#L309"
    colours = ["lavender", "violet", "gray25", "sea_green",
              "pale_blue", "blue", "gray25", "rose", "tan", "light_yellow", "light_green", "light_turquoise",
              "light_blue", "sky_blue", "plum", "gold", "lime", "coral", "periwinkle", "ice_blue", "aqua"]
    numbers = []
    for i in range(len(template.dimension_names)-1, \
                   -(len(colours) - len(template.dimension_names)), -1):
        numbers.append(-i)
    colourlist = dict(zip(numbers, colours))
    return colourlist
colourlist = create_colourlist()



def main():
    global Opt
    Opt = Options()
    atexit.register(onexit)
    recipe = imp.load_source("recipe", Opt.recipe_file)
    for fn in Opt.xls_files:
        try:
            per_file(fn, recipe)
        except Exception:
            crash_msg.append("fn: {!r}".format(fn))
            crash_msg.append("recipe: {!r}".format(Opt.recipe_file))
            print "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@"
            print '\n'.join(crash_msg)
            print "@@@@@@@@@@@@@@@@@@@@@@@@@@@@@"
            raise

if __name__ == '__main__':
    main()
