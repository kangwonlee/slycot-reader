from slycot_reader.call_table_from_f2c_p import Dict2MDTable, scan_f2c


class Dict2Cython(Dict2MDTable):
    """
    Objective : To automatically generate files for cython wraps around C functions

    * pyx files : (cython will generate a .c file with the same name so be careful not to overwrite the original c file)
        from f2c cimport *

        cimport numpy as np

        np.import_array()

        # c function signature
        cdef extern from "{c_header_file_name:s}.h":
            {return_type:s} {c_function_name:s} ({c_prototype_argument_list:s})

        # wrap the c function
        def {python_function_name:s} ({python_argument_list}):
            # c_function_argument_list may contain appropriate type casting
            {c_function_name:s} ({c_function_argument_list})

    * .h files :
        # include "f2c.h"
        {return_type:s} {c_function_name:s} ({c_prototype_argument_list:s})

    * setup.py entry :
        from distutils.core import setup, Extension

        import numpy
        from Cython.Distutils import build_ext

        setup(
            cmdclass={'build_ext': build_ext},
            ext_modules=[Extension("{module_name:s},
                                    sources=['{pyx_filename}', '{c_filename}', ...],
                                    include_dirs=[numpy.get_include()])],
        )

    ref : Valentin Haenel, 2.8.5.2. Numpy Support, 2.8.5. Cython, Scipy Lectures, Oct 18 2016, [Online] Available: http://www.scipy-lectures.org/advanced/interfacing_with_c/interfacing_with_c.html#id13
    """

    # TODO : check if these conversions are correct
    c_py_arg_proto_lookup = {
        'doublereal *': 'np.ndarray[double, ndim=1, mode="c"] {py_arg_name:s} not None',
        'integer *': 'np.ndarray[long int, ndim=1, mode="c"] {py_arg_name:s} not None',
        'ftnlen': '{py_arg_name:s}',
        'char *': '{py_arg_name:s}',
    }

    def __init__(self, input_dict, row_selection_list):
        super(Dict2Cython, self).__init__(input_dict, row_selection_list=row_selection_list)

    @staticmethod
    def write_pyx_header():
        return """from f2c cimport *

cimport numpy as np

np.import_array()
"""

    def get_function_prototype_text(self, function_name):
        return super().get_third_and_latter_row_text(function_name)

    def get_py_func_arg_list_txt(self, c_function_name):
        raise NotImplementedError()

    def get_c_func_arg_list_txt(self, c_function_name):
        raise NotImplementedError()

    def get_def_py_func_block(self, c_function_name):
        return '''def {python_function_name:s} ({python_argument_list}):
    {c_function_name:s} ({c_function_argument_list})'''.format(
            c_function_name=c_function_name,
            c_function_argument_list=self.get_c_func_arg_list_txt(c_function_name),
            python_function_name=self.get_py_func_name(c_function_name),
            python_argument_list=self.get_py_func_arg_list_txt(c_function_name),
        )

    @staticmethod
    def get_py_func_name(c_function_name):
        return c_function_name.strip('_').lower()

    def get_cdef_c_func_block(self, c_function_name, header_name=None):
        """
        For *.pyx file

        :param str c_function_name: for example, sb03md_
        :param str|None header_name: if None, for example, SB03MD
        :return:
        """
        if header_name is None:
            header_name = self.get_c_file_name(c_function_name)

        return '''cdef extern from "{c_header_file_name:s}.h":
    {prototype:s}'''.format(
            c_header_file_name=header_name,
            prototype=self.get_function_prototype_text(c_function_name),
        )

    @staticmethod
    def get_c_file_name(c_function_name):
        return c_function_name.strip('_').upper()

    def get_column_list_third_and_latter_row(self, function_info_dict, function_name):
        column_list = [
            function_info_dict['return type'],
            function_info_dict['name'],
            '(',
            ', '.join([' '.join(arg_type_name) for arg_type_name in function_info_dict['arg list']]),
            ')'
        ]
        return column_list

    def __str__(self):
        result = self.third_and_latter_row()

        return result


def main():
    function_selection_list = ['sb03md_', 'sb04md_', 'sg03ad_', 'sb04qd_', 'sb02md_',
                               'sb02mt_', 'sg02ad_', 'ab09md_', 'ab09nd_', 'sb10hd_',
                               'sb03od_', 'tb01pd_', 'td04ad_', 'sb02od_', ]

    # scan through f2c folders to build database
    reader = scan_f2c()

    # size of the big table
    print('total functions: %d\n' % len(reader.big_table))
    cython_writer = Dict2Cython(
        reader.big_table,
        function_selection_list
    )
    print(cython_writer)


if __name__ == '__main__':
    main()
