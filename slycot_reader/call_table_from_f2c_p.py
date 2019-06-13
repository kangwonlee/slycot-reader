import os
import pprint
import re

default_path_dict = {
    'slycot': {
        'src': os.path.join(os.pardir, 'slycot', 'src'),
        'f2c': os.path.join(os.pardir, 'slycot', 'src-f2c'),
    },
    'lapack': {
        'src': os.path.join(os.pardir, 'slycot', 'src-f2c', 'lapack', 'SRC'),
        'f2c': os.path.join(os.pardir, 'slycot', 'src-f2c', 'lapack', 'src-f2c'),
        'install-f2c': os.path.join(os.pardir, 'slycot', 'src-f2c', 'lapack', 'install-f2c'),
    },
    'blas': {
        'src': os.path.join(os.pardir, 'slycot', 'src-f2c', 'lapack', 'BLAS', 'SRC'),
        'f2c': os.path.join(os.pardir, 'slycot', 'src-f2c', 'lapack', 'BLAS', 'src-f2c'),
    },
}

f2c_path_dict = {
    'src': {},
    'f2c': {},
}

for lib, path_dict in default_path_dict.items():
    f2c_path_dict['src'][lib] = path_dict['src']
    f2c_path_dict['f2c'][lib] = path_dict['f2c']

f2c_path_dict['f2c']['lapack-install'] = default_path_dict['lapack']['install-f2c']


class F2cpReader(object):
    def __init__(self):
        self.re_function_name = self.get_function_name_pattern()
        self.re_latter_line = self.get_latter_lines_pattern()
        self.re_first_line = self.get_first_line_pattern()
        self.re_arg_type_name_split = self.get_arg_type_name_split()
        self.big_table = {}
        self.arg_type_lookup = {}
        self.p_file_name = ''
        self.lib_name = ''
        self.p_file_path = ''

    def __del__(self):
        del self.re_function_name
        del self.re_latter_line
        del self.re_first_line
        del self.re_arg_type_name_split
        del self.big_table
        del self.arg_type_lookup

    @staticmethod
    def get_function_name_pattern():
        return re.compile(r'\w\s+\w+\s+(\w+?)\s*\(')

    @staticmethod
    def get_first_line_pattern():
        return re.compile(r'\w\s+(?P<return_type>\w+)\s+(?P<name>\w+?)\s*\((?P<arg_list>.*)\);')

    @staticmethod
    def get_calling_function_name_pattern():
        # for lines 2nd ~
        return re.compile(r'/\*:ref:\s+(?P<name>.*?)\s')

    @staticmethod
    def get_latter_lines_pattern():
        # for lines 2nd ~
        return re.compile(r'/\*:ref:\s+(?P<name>.*?)\s(?P<return_type>\d+)\s(?P<no_args>\d+)\s(?P<arg_types>.+)\s+\*/')

    @staticmethod
    def get_arg_type_name_split():
        # '(char *)a' -> ('(char *)', 'a')
        # 'char *a' -> ('char *', 'a')
        # 'char a' -> ('char', 'a')
        return re.compile(r'(?P<type>(\(.+\s+\*\))|(.+\s+\*)|(\w+))\s?(?P<name>.+)')

    def parse_f2c_p(self, f2c_p_file_path, b_verbose=False):

        if os.path.exists('.'.join([os.path.splitext(f2c_p_file_path)[0], 'c'])):

            self.get_lib_name_from_p_file_path(f2c_p_file_path)

            with open(f2c_p_file_path) as f:
                lines = f.readlines()
            # first line : c definitions
            # second line and after : list of other functions called

            caller_set = SetMdQuote()
            callee_set = SetMdQuote()

            for line in lines:
                line = line.strip()

                if not line.startswith('/*'):
                    # functions defined
                    info = self.find_function_info(line)
                    if b_verbose:
                        print(info)
                    caller_set.add(info['name'])
                else:
                    # functions used inside
                    info = self.find_calling_function_info(line)
                    callee_set.add(info['name'])

                self.update_big_table(info)

            # TODO: if more than one caller functions in one .P file, which function is calling which function(s)?
            for caller in caller_set:
                calls_set = self.big_table[caller].get('calls', callee_set)
                self.big_table[caller]['calls'] = calls_set.union(callee_set)

            for callee in callee_set:
                called_set = self.big_table[callee].get('called in', caller_set)
                self.big_table[callee]['called in'] = called_set.union(caller_set)

    def get_lib_name_from_p_file_path(self, f2c_p_file_path):
        """

        :param str f2c_p_file_path: path to the f2c P file
        :return:
        """

        path_lower = f2c_p_file_path.lower()

        # because lapack is a subfolder of slycot/f2c
        # and blas is a a subfolder of lapack
        if 'blas' in path_lower:
            self.lib_name = 'blas'
        elif 'install-f2c' in path_lower:
            self.lib_name = 'lapack install'
        elif ('lapack' in path_lower) and ('src-f2c' in path_lower):
            self.lib_name = 'lapack'
        elif 'slycot' in path_lower:
            self.lib_name = 'slycot'
        else:
            raise ValueError('library unknown')

    def update_big_table(self, info_dict):
        big_table_entry = self.big_table.get(info_dict['name'], {})

        # if already know return type in a string, do not update
        if not (('return type' in big_table_entry) and (isinstance(big_table_entry['return type'], str))):
            big_table_entry.update(info_dict)
            self.big_table[info_dict['name']] = big_table_entry
        # end if already know return type in a string, do not update

        self.update_arg_type_lookup(big_table_entry)

    def update_arg_type_lookup(self, big_table_entry):
        if ('arg types' in big_table_entry) and ('arg list' in big_table_entry):
            # begin update arg_type_lookup
            for type_id, arg_type_name in zip(big_table_entry['arg types'], big_table_entry['arg list']):
                arg_type_lookup_entry = self.arg_type_lookup.get(type_id, {})
                # count number of each case
                arg_type_lookup_entry[arg_type_name[0]] = arg_type_lookup_entry.get(arg_type_name[0], 0) + 1
                self.arg_type_lookup[type_id] = arg_type_lookup_entry
            # end update arg_type_lookup

    def find_c_function_name(self, f2c_p_first_line):
        """
        From the first line of the f2c P file, find function name using regex

        :param str f2c_p_first_line: first line of f2c P file
        :return: function name string
        """
        match = self.re_function_name.search(f2c_p_first_line)
        result = {
            'name': match.groups()[0],
            'start': match.regs[1][0],
            'end': match.regs[1][1],
        }

        return result

    def find_function_info(self, f2c_p_first_line):
        """
        Collect information about the function from the first line of the P file

        :param str f2c_p_first_line:
        :return: {'name': str, 'return type': str, '# arg': int, 'arg list': [str]}
        """
        match = self.re_first_line.search(f2c_p_first_line)
        arg_list = [s.strip() for s in match.group('arg_list').split(',')]

        # identify argument type and name
        arg_type_name_list = []
        for arg_type_name_str in arg_list:
            split = self.re_arg_type_name_split.search(arg_type_name_str)
            arg_type_name_list.append((split.group('type'), split.group('name')))

        result = {
            'name': match.group('name'),
            'return type': match.group('return_type'),
            '# arg': len(arg_list),
            'arg list': arg_type_name_list,
            'lib': self.lib_name,
            'path': self.p_file_path,
        }

        return result

    def find_calling_function_info(self, f2c_p_latter_line):
        match = self.re_latter_line.search(f2c_p_latter_line)
        if match is not None:
            result = {
                'name': match.group('name'),
                'return type': int(match.group('return_type')),
                '# arg': int(match.group('no_args')),
                'arg types': [int(s) for s in match.group('arg_types').split()],
                'lib': self.lib_name,
                'path': self.p_file_path,
            }
        else:
            match = self.get_calling_function_name_pattern().search(f2c_p_latter_line)
            result = {'name': match.group('name')}

        return result

    def find_any_missing_function(self):
        definition_missing_set = SetMdQuote(self.big_table.keys())
        never_called_set = SetMdQuote(self.big_table.keys())

        # function loop
        for function_name, function_info in self.big_table.items():
            if 'arg list' in function_info:
                # found definition
                definition_missing_set.remove(function_name)
            if 'arg types' in function_info:
                # found usage
                never_called_set.remove(function_name)

        definition_missing_dict = {}
        for function_name in definition_missing_set:
            definition_missing_dict[function_name] = self.big_table[function_name]
            definition_missing_dict[function_name].pop('arg types', None)

        never_called_dict = {}
        for function_name in never_called_set:
            never_called_dict[function_name] = self.big_table[function_name]
            never_called_dict[function_name].pop('arg types', None)

        return definition_missing_dict, never_called_dict


class Dict2MDTable(object):
    """
    >>> table = Dict2MDTable(
        {   # table data
            'a': {'b': 1, 'c': 2, 'd': 3},
            'e': {'b': 4, 'c': 5, 'd': 6},
        },
        [   # column order
            {'name':'b'}, {'name':'c', 'align': 'right'}, {'name':'d', 'align': 'left'}
        ],
    )
    >>> print(table)
    |    | b | c | d |
    |:-----:|:-----:|------:|:------|
    | a | 1 | 2 | 3 |
    | e | 4 | 5 | 6 |
    """
    align = {
        'right': '------:',
        'center': ':-----:',
        'left': ':------',
    }

    def __init__(self, input_dict, column_order_list=None, row_selection_list=None):
        """

        :param input_dict:
        :param column_order_list:
        :param list | tuple | set row_selection_list: if not given, all rows
        """
        self.input_dict = input_dict

        # to select rows of interest
        if row_selection_list is None:
            self.row_selection_list = list(self.input_dict.keys())
        elif isinstance(row_selection_list, (list, tuple, set)):
            self.row_selection_list = row_selection_list
        else:
            raise ValueError('expect row_selection_list to be one of list, tuple, and set')

        # column selection
        if column_order_list is None:
            one_sample = self.input_dict[SetMdQuote(self.input_dict.keys()).pop()]
            self.column_order_list = {'name': key for key in one_sample}
        elif isinstance(column_order_list, (list, tuple)):
            self.column_order_list = column_order_list
        else:
            raise ValueError('expect column_order_list to be a list or tuple')

    def first_row(self):
        space = '    '
        row_list = ['', space]
        for column in self.column_order_list:
            row_list.append(' %s ' % column.get('name', space))

        row_list.append('')

        result = '|'.join(row_list)

        return result

    def second_row(self):
        row_list = ['', self.align['center']]
        for column in self.column_order_list:
            row_list.append(self.align[column.get('align', 'center')])
        row_list.append('')
        result = '|'.join(row_list)

        return result

    def third_and_latter_row(self):
        # run get_third_and_latter_row_text() across self.row_selection_list and join with '\n'
        return '\n'.join(
            [self.get_third_and_latter_row_text(function_name) for function_name in self.row_selection_list])

    def get_third_and_latter_row_text(self, function_name):
        """
        Prepare third row text on the given function
        
        :param function_name: 
        :return: 
        """
        function_info_dict = self.input_dict[function_name]
        column_list = self.get_column_list_third_and_latter_row(function_info_dict, function_name)
        row_text = ' '.join(column_list)
        return row_text

    def get_column_list_third_and_latter_row(self, function_info_dict, function_name):
        column_list = ['|', '`%s`' % str(function_name), '|']
        # first column
        # loop for the following columns
        for column in self.column_order_list:
            column_list.append(str(function_info_dict.get(column['name'], '')))
            column_list.append('|')
        return column_list

    def __str__(self):
        table_list = [
            self.first_row(),
            self.second_row(),
            self.third_and_latter_row(),
        ]

        result = '\n'.join(table_list)

        return result


class Dict2MDTableSorted(Dict2MDTable):
    def __init__(self, input_dict, column_order_list=None, row_selection_list=None, sort_order=None):
        super().__init__(input_dict=input_dict,
                         column_order_list=column_order_list,
                         row_selection_list=row_selection_list)

        if sort_order is None:
            self.sort_order = {'name': 'lib', 'direction': 'descending'}
        elif isinstance(sort_order, (dict,)):
            self.sort_order = sort_order
        else:
            raise ValueError('expect sort_order to be a dict')

    def third_and_latter_row(self):

        # sort row_selection_list based on sort_order
        list_to_sort = list(self.row_selection_list)
        list_to_sort.sort(key=lambda key: self.input_dict[key][self.sort_order['name']],
                          reverse=('descending' == self.sort_order['direction']))

        # run get_third_and_latter_row_text() across self.row_selection_list and join with '\n'
        return '\n'.join(
            [self.get_third_and_latter_row_text(function_name) for function_name in list_to_sort])


def scan_f2c():
    reader = F2cpReader()
    for lib, lib_path in f2c_path_dict['f2c'].items():
        reader.lib_name = lib
        for dir_name, dir_list, file_list in os.walk(lib_path):
            for file_name in file_list:
                if '.P' == os.path.splitext(file_name)[-1]:
                    reader.p_file_path = dir_name
                    reader.p_file_name = file_name
                    reader.parse_f2c_p(os.path.join(dir_name, file_name))
    return reader


class RecursivelyCheckNotDefined(object):
    def __init__(self, big_table_dict, not_defined_dict, function_selection_list):
        self.big_table_dict = big_table_dict
        self.not_defined_dict = not_defined_dict
        self.function_list = function_selection_list
        self.not_defined_set = SetMdQuote()
        self.checked_set = SetMdQuote()

    def check_list(self):
        for function_name in self.function_list:
            self.check_function(function_name)

    def check_function(self, function_name):
        if function_name in self.checked_set:
            return

        if function_name in self.not_defined_dict:
            self.not_defined_set.add(function_name)

        for callee_name in self.big_table_dict[function_name].get('calls', []):
            self.check_function(callee_name)

        self.checked_set.add(function_name)


def main():
    function_selection_list = ['sb02md_', 'sb02mt_', 'sb03md_', 'tb04ad_', 'td04ad_',
                               'sg02ad_', 'sg03ad_', 'tb01pd_', 'ab09ad_', 'ab09md_',
                               'ab09nd_', 'sb01bd_', 'sb02od_', 'sb03od_', 'sb04md_',
                               'sb04qd_', 'sb10ad_', 'sb10hd_', ]

    # scan through f2c folders
    reader = scan_f2c()
    # argument_type_id vs argument_type lookup table
    pprint.pprint(reader.arg_type_lookup)
    # size of the big table
    print('total functions: %d\n' % len(reader.big_table))

    big_table_printer = Dict2MDTable(
        reader.big_table,
        [{'name': 'return type'}, {'name': '# arg'}, {'name': 'arg list'}, {'name': 'lib'},
         {'name': 'path', 'align': 'left'},
         ],
        function_selection_list,
    )
    print(big_table_printer)

    # find functions not defined or not used
    definition_missing, never_called = reader.find_any_missing_function()

    # never called table
    print('never used %d\n' % len(never_called))
    never_called_table_converter = Dict2MDTable(
        never_called,
        [{'name': 'lib'}, {'name': '# arg'}, {'name': 'return type'}, {'name': 'path'}, ]
    )
    print(never_called_table_converter)

    # not defined table
    print('not defined %d\n' % len(definition_missing))
    not_defined_table_converter = Dict2MDTable(
        definition_missing,
        [{'name': 'lib'}, {'name': '# arg'}, {'name': 'return type'}, {'name': 'path'}, {'name': 'called in'}]
    )
    print(not_defined_table_converter)

    checker = RecursivelyCheckNotDefined(reader.big_table, definition_missing, function_selection_list)
    checker.check_list()
    print('not defined :')
    print(checker.not_defined_set)

    # list all the functions related to the slycot
    print('\n' + ('related : %d' % len(checker.checked_set)) + '\n')
    related_table = Dict2MDTableSorted(
        reader.big_table,
        [{'name': 'lib'}, {'name': '# arg'}, {'name': 'return type'}, {'name': 'calls'}],
        checker.checked_set
    )
    print(related_table)


def unique_list_ordered(function_selection_list):
    """
    Generate a list of unique elements preserving the first appearance order

    :param list function_selection_list: a list of possibly duplicated elements 
    :return: a list of unique elements
    """
    function_selection_unique = []
    for function_name in function_selection_list:
        if function_name not in function_selection_unique:
            function_selection_unique.append(function_name)
    return function_selection_unique


class SetMdQuote(set):
    """
    Replace small quote of set string with ` for github markdown
    """

    def __str__(self):
        return super().__str__().replace("'", '`').replace('SetMdQuote', '').replace('(', '').replace(')', '')

    def union(self, *other):
        return SetMdQuote(super().union(*other))


if __name__ == '__main__':
    main()
