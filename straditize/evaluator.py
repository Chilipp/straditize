"""Evaluator class for the straditize algorithms"""
import os.path as osp
import warnings
from PIL import Image
from functools import partial
import pandas as pd
import numpy as np
from collections import OrderedDict
from straditize.common import docstrings
from straditize.straditizer import Straditizer
from psy_strat.stratplot import stratplot


docstrings.get_sectionsf('stratplot')(stratplot)


def rmse(sim, ref):
    """Calculate the root mean squared error between simulation and reference

    Parameters
    ----------
    sim: np.ndarray
        The simluated data
    ref: np.ndarray
        The reference data"""
    return np.sqrt(((sim - ref) ** 2).mean())


def print_progressbar(iteration, total, prefix='', suffix='', length=100,
                       fill='█'):
    """
    Print iterations progress

    Taken from https://stackoverflow.com/a/34325723

    Parameters
    ----------
    iteration: int
        current iteration
    total: int
        total iterations
    prefix: str
        prefix string
    suffix: str
        suffix string
    decimals: int
        positive number of decimals in percent complete
    length: int
        character length of bar
    fill: str
        bar fill character
    """
    percent = ("{0:.1f}").format(
        100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end='\r')
    # Print New Line on Complete
    if iteration == total:
        print()


axislinestyle = {'left': '-', 'right': '-', 'bottom': '-', 'top': '-'}


class StraditizeEvaluator:
    """An evaluator for the straditize components"""

    @docstrings.dedent
    def __init__(self, data, *args, name='data',
                 axislinestyle=axislinestyle, **kwargs):
        """
        Parameters
        ----------
        %(stratplot.parameters)s
        """
        self.data = data
        self.name = name
        self.sp, self.groupers = stratplot(data, *args, **kwargs)
        self.labels = OrderedDict()
        if axislinestyle is not None:
            self.sp.update(axislinestyle=axislinestyle)
        self.use_bars = kwargs.get('use_bars')

    @classmethod
    def from_polnet(cls, data, *args, **kwargs):
        data = data.drop_duplicates(
            ['age', 'original_varname']).sort_values(
                ['age', 'original_varname'])
        index = data.age.unique()
        columns = data.original_varname.unique()
        df = pd.DataFrame(
            [], columns=pd.Index(columns, name='original_varname'),
            index=pd.Index(index, name='age'))

        for key, row in data.iterrows():
            df.loc[row.age, row.original_varname] = row.percentage

        df = df[df.columns[(df > 1.0).any(axis=0)]]

        return cls(df, *args, calculate_percentages=False, percentages=True,
                   **kwargs)

    def export(self, filepath, dpi=300, labels={}):
        self.dpi = dpi
        self.filepath = filepath
        for key, val in sorted(labels.items()):
            self.labels[key] = val
        self.sp.export(filepath + '.png', dpi=dpi)
        # now hide the axes
        self.sp.update(axiscolor={'left': 'w', 'right': 'w'})
        self.sp.export(filepath + '-no-axes.png', dpi=dpi)
        self.sp.update(axiscolor={'left': 'k', 'right': 'k'})

    _results = None

    _dpi = None

    _data = None

    @property
    def data(self):
        return self._data[[arr.name for arr in self.sp]]

    @data.setter
    def data(self, value):
        self._data = value

    @property
    def transformed_data(self):
        """The :attr:`data` in pixel coordinates"""
        columns = self.data.columns
        widths = pd.Series(np.diff(self.column_bounds).ravel(), columns)
        xwidths = pd.Series(
            np.diff([ax.get_xlim() for ax in self.sp.axes]).ravel(), columns)

        df = self.data.fillna(0) * widths / xwidths

        y_px = self.data_ylim - self.data_ylim[0]
        y_data = next(np.sort(ax.get_ylim()) for ax in self.sp.axes)
        diff_px = np.diff(y_px)[0]
        diff_data = np.diff(y_data)[0]
        slope = diff_px / diff_data
        intercept = y_px[0] - slope * y_data[0]

        df.index = np.round(intercept + slope * df.index).astype(int)
        return df

    @property
    def dpi(self):
        if self._dpi is None:
            raise ValueError("The image has not yet been exported!")
        return self._dpi

    @dpi.setter
    def dpi(self, value):
        self._dpi = value

    @property
    def results(self):
        if self._results is None:
            names = [self.name, 'ntaxa', 'nsamples'] + list(self.labels)
            levels = labels = [[]] * len(names)
            self._results = pd.DataFrame(
                [], columns=pd.MultiIndex(levels, labels, names=names),
                index=pd.Index([], name='metric'))
        column = self.results_column
        try:
            return self._results[column]
        except KeyError:
            self._results[column] = np.nan
        return self._results[column]

    @property
    def results_column(self):
        """The column name in :attr:`all_results`"""
        return (self.name, len(self.sp), len(self.data)) + tuple(
            self.labels.values())

    @results.setter
    def results(self, value):
        column = self.results_column
        for key, val in value.items():
            self._results.loc[key, column] = val

    @property
    def all_results(self):
        return self._results

    @property
    def width(self):
        fig = next(iter(self.sp.figs))
        return fig.get_figwidth() * self.dpi

    @property
    def height(self):
        fig = next(iter(self.sp.figs))
        return fig.get_figheight() * self.dpi

    @property
    def data_xlim(self):
        minx = min(ax.get_position().x0 for ax in self.sp.axes)
        maxx = max(ax.get_position().x1 for ax in self.sp.axes)
        width = self.width
        return np.round([minx * width, maxx * width]).astype(int)

    @property
    def summed_perc(self):
        summed_perc = np.sum([ax.get_xlim()[1] for ax in self.sp.axes])
        return summed_perc

    @property
    def data_ylim(self):
        miny = min(ax.get_position().y0 for ax in self.sp.axes)
        maxy = max(ax.get_position().y1 for ax in self.sp.axes)
        height = self.height
        return height - np.round([maxy * height, miny * height]).astype(int)

    @property
    def column_starts(self):
        x0 = self.data_xlim[0]
        return -x0 + np.round(self.width * np.array(
            [ax.get_position().x0 for ax in self.sp.axes])).astype(int)

    @property
    def column_ends(self):
        x0 = self.data_xlim[0]
        return -x0 + np.round(self.width * np.array(
            [ax.get_position().x1 for ax in self.sp.axes])).astype(int)

    @property
    def column_bounds(self):
        return np.vstack([self.column_starts, self.column_ends]).T

    @property
    def full_df(self):
        # get the full_df in pixel coordinates
        df = self.transformed_data

        height = np.round(np.diff(self.data_ylim)).astype(int)[0]
        ncols = df.shape[1]
        interpolated = np.zeros((height, ncols), dtype=int)
        for i in np.arange(ncols):
            interpolated[:, i] = np.round(np.interp(
                np.arange(height), df.index.values, df.iloc[:, i].values,
                left=0, right=0))
        return pd.DataFrame(interpolated, index=pd.Index(np.arange(height)),
                            columns=np.arange(ncols)).fillna(0)

    def init_stradi(self, datalim=True, columns=True, names=True,
                    digitize=True, samples=True, axes=False):
        path = self.filepath
        if not axes:
            path += '-no-axes'
        image = Image.open(path + '.png')
        stradi = Straditizer(image)
        if datalim:
            stradi.data_xlim = self.data_xlim
            stradi.data_ylim = self.data_ylim
            stradi.init_reader('area' if not self.use_bars else 'bars')
        else:
            return stradi

        stradi.yaxis_px = np.array([0, np.diff(self.data_ylim)[0]])
        stradi.yaxis_data = np.array(self.sp[0].psy.ax.get_ylim())[::-1]

        if columns:
            stradi.data_reader.column_starts = self.column_starts
        else:
            return stradi

        if names:
            stradi.colnames_reader.column_names = self.data.columns.tolist()

        stradi.data_reader.xaxis_px = self.column_bounds[0]
        stradi.data_reader.xaxis_data = np.array(self.sp[0].psy.ax.get_xlim())

        if digitize:
            stradi.data_reader.full_df = self.full_df
        else:
            return stradi

        if samples:
            stradi.data_reader.sample_locs = self.transformed_data

        return stradi

    def evaluate_column_starts(self, close=True):
        stradi = self.init_stradi(columns=False, axes=True)
        starts = stradi.data_reader._get_column_starts()
        ref = self.column_starts
        results = self.results.copy()
        missing_cols = len(ref) - len(starts)
        results['starts_ref'] = len(ref)
        results['starts_found'] = len(starts)

        if not missing_cols:
            diff = np.abs(starts - ref).sum()
            width = np.diff(self.data_xlim)[0]
            results['starts_diff'] = diff
            results['starts_diff_perc'] = diff / width * self.summed_perc

            # now remove the yaxes
            stradi.data_reader.recognize_yaxes(remove=True)
            diff = np.abs(stradi.data_reader.column_starts - ref).sum()
            results['starts_diff_removey'] = diff
            results['starts_diff_removey_perc'] = \
                diff / width * self.summed_perc

        self.results = results
        return stradi.close() if close else stradi

    def evaluate_yaxes_removal(self, close=True):
        stradi = self.init_stradi(columns=False, axes=True)
        stradi_ref = self.init_stradi(digitize=False)

        # remove the y-axes
        stradi.data_reader._get_column_starts()
        stradi.data_reader.recognize_yaxes(remove=True)
        results = self.results
        # transform into black-and-white image
        im1 = np.where(stradi.data_reader.binary.astype(bool), 0, 255)
        im2 = np.where(stradi_ref.data_reader.binary.astype(bool), 0, 255)
        # calculate rmse
        results['yaxes_rmse'] = rmse(im1, im2)
        self.results = results

        return (stradi.close(), stradi_ref.close()) if close else (
            stradi, stradi_ref)

    def evaluate_sample_accuracy(self, close=True):
        stradi = self.init_stradi(digitize=False)
        stradi.data_reader.digitize()
        results = self.results
        ref = self.data.fillna(0)
        full_df = stradi.full_df
        indexes = list(map(partial(full_df.index.get_loc, method='nearest'),
                           ref.index))
        sim = full_df.iloc[indexes]
        results['samples_rmse'] = rmse(sim.values,
                                       ref.values)
        self.results = results
        return stradi.close() if close else stradi

    def evaluate_sample_position(self, close=True):
        stradi = self.init_stradi(samples=False)
        stradi.data_reader.add_samples(
            *stradi.data_reader.find_samples())

        final = stradi.final_df
        ref = self.data
        nfound = len(final)
        nref = len(ref)

        results = self.results
        results['samples_found'] = nfound
        results['samples_ref'] = nref

        closest = list(map(
            partial(final.index.get_loc, method='nearest'),
            ref.index))

        age_range = ref.index.max() - ref.index.min()

        # normalized rmse of the age
        results['samples_nrmse_y'] = rmse(
            final.index[closest].values, ref.index.values) / age_range

        self.results = results
        return stradi.close() if close else stradi

    def run(self):
        """Run all evaluations"""
        self.evaluate_column_starts()
        self.evaluate_yaxes_removal()
        self.evaluate_sample_accuracy()
        self.evaluate_sample_position()

    def close_figs(self):
        self.sp.close(figs=True)


class BaselineScenario:
    """The baseline evaluation scenario for straditize with data from POLNET

    This class uses the default settings of the :class:`StraditizeEvaluator`
    and runs the analysis for a given dataset from POLNET."""

    def __init__(self, data, output_dir='.'):
        self.evaluators = []
        self.output_dir = output_dir
        grouped = data.groupby('e_')
        progress_args = (grouped.ngroups, 'Progress', 'Complete', 50)

        print_progressbar(0, *progress_args)
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', 'Distinct samples merged from',
                                    UserWarning)
            for i, (key, group) in enumerate(grouped, 1):
                evaluator = self.init_evaluator(key, group)
                self.export_evaluator(evaluator)
                evaluator.run()
                evaluator.close_figs()
                self.evaluators.append(evaluator)
                print_progressbar(i, *progress_args)

    def init_evaluator(self, name, data, *args, **kwargs):
        """Initialize an evaluator for a given data set"""
        import matplotlib.pyplot as plt
        if 'fig' not in kwargs:
            kwargs['fig'] = plt.figure(figsize=(12, 6))
        return StraditizeEvaluator.from_polnet(
            data, *args, name=str(name), **kwargs)

    def export_evaluator(self, evaluator, *args, **kwargs):
        evaluator.export(osp.join(self.output_dir, evaluator.name),
                         *args, **kwargs)
