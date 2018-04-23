# Placeholder. will be filled later
import sys
from psyplot_gui import docstrings
import os
import os.path as osp


docstrings.delete_params('psyplot_gui.start_app.parameters', 'fnames',
                         'output')


@docstrings.dedent
def start_app(fname=None, output=None, xlim=None, ylim=None,
              full=False, reader_type='area', **kwargs):
    """
    Start the psyplot GUI with the straditizer setup

    Parameters
    ----------
    fname: str
        Either the path to a picture to digitize or a previously saved
        straditizer project (ending with ``'.pkl'``)
    output: str
        The path to the csv file where to save the digitized diagram
    xlim: list of int of length 2
        The x-limits of the data part of the diagram
    ylim: list of int of length 2
        The y-limits of the data part of the diagram
    full: bool
        If True, the image is digitzed and x- and ylim are set to the entire
        share of the array
    reader_type: { 'area' | 'bars' | 'rounded bars' | 'stacked area' | 'line' }
        Specify the reader type
    %(psyplot_gui.start_app.parameters.no_fnames|output)s
    """
    import numpy as np

    def set_x_and_ylim(stradi):
        if not xlim and stradi.data_xlim is None:
            stradi.data_xlim = [0, np.shape(stradi.image)[1]]
        if not ylim and stradi.data_ylim is None:
            stradi.data_ylim = [0, np.shape(stradi.image)[0]]

    if not output:
        from psyplot_gui.compat.qtcompat import QApplication
        from psyplot_gui import start_app, send_files_to_psyplot
        exec_ = kwargs.pop('exec_', True)
        if exec_:
            app = QApplication(sys.argv)
        cwd = osp.abspath(kwargs.get('pwd') or os.getcwd())
        mainwindow = start_app(exec_=False, callback='', **kwargs)
        if mainwindow is None:
            send_files_to_psyplot('straditize', [fname], None, xlim, ylim,
                                  full, reader_type)
            return
        stradi_widget = mainwindow.plugins[
            'straditize.widgets:StraditizerWidgets:straditizer']
        stradi_widget.switch_to_straditizer_layout()
        if fname:
            stradi_widget.menu_actions.open_straditizer(osp.join(cwd, fname))
            if not fname.endswith('.pkl') and (xlim or ylim):
                set_x_and_ylim(stradi_widget.straditizer)
            stradi = stradi_widget.straditizer
        else:
            if exec_:
                sys.excepthook = mainwindow.excepthook
                sys.exit(app.exec_())
            return mainwindow
    else:
        if not fname:
            raise IOError(
                'A file must be provided if the `output` parameter is used!')
        from straditize.straditizer import Straditizer
        if fname.endswith('.pkl'):
            stradi = Straditizer.load(fname, plot=False)
        else:
            from PIL import Image
            image = Image.open(fname)
            stradi = Straditizer(image)
            set_x_and_ylim(stradi)
    if xlim:
        stradi.data_xlim = xlim
    if ylim:
        stradi.data_ylim = ylim
    if xlim or ylim or full:
        set_x_and_ylim(stradi)
        stradi.init_reader(reader_type)
        stradi.data_reader.digitize()
    if output:
        stradi.final_df.to_csv(output)
    elif exec_:
        stradi_widget.refresh()
        sys.excepthook = mainwindow.excepthook
        sys.exit(app.exec_())
    else:
        stradi_widget.refresh()
        return mainwindow


def get_parser(create=True):
    from psyplot_gui import get_parser
    parser = get_parser(create=False)
    # delete the arguments that are not part of the GUI group
    gui_group = parser.unfinished_arguments['backend']['group']
    output_group = parser.unfinished_arguments['output']['group']
    for arg, d in list(parser.unfinished_arguments.items()):
        if d.get('group') != gui_group:
            parser.pop_arg(arg)
    parser.epilog = ""
    parser.setup_args(start_app)
    parser.update_arg('fname', positional=True, nargs='?')
    parser.update_arg('output', short='o', group=output_group)
    stradi_grp = parser.add_argument_group(
        'Straditizer options',
        'Options specific pollen diagram digitization')
    parser.update_arg('reader_type', short='rt',
                      choices=['area', 'bars', 'rounded bars',
                               'stacked area', 'line'],
                      group=stradi_grp)
    parser.append2help('reader_type', '. Default: %(default)s')
    parser.update_arg('xlim', type=int, nargs=2, metavar='val',
                      group=stradi_grp)
    parser.update_arg('ylim', type=int, nargs=2, metavar='val',
                      group=stradi_grp)
    parser.update_arg('full', group=stradi_grp, short='f')
    if create:
        parser.create_arguments()
    return parser


def main(exec_=True):
    parser = get_parser()
    parser.parse_known2func()


if __name__ == '__main__':
    main()
