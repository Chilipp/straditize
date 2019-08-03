"""Evaluator class for the straditize algorithms"""
import os.path as osp
import shutil
import multiprocessing as mp
import warnings
from PIL import Image
from functools import partial
import pandas as pd
import numpy as np
from collections import OrderedDict
from straditize.common import docstrings
from straditize.straditizer import Straditizer
from psy_strat.stratplot import stratplot
from itertools import filterfalse


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

        df = (self.data.fillna(0) * widths / xwidths).round()

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

    def set_xtranslation(self, stradi):
        stradi.data_reader.xaxis_px = np.array([0, 1])
        dx = np.diff(self.sp[0].psy.ax.get_xlim())
        stradi.data_reader.xaxis_data = np.r_[
            0, dx / np.diff(self.column_bounds[0])]

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

        self.set_xtranslation(stradi)

        if digitize:
            stradi.data_reader.digitize()
            stradi.data_reader._full_df.loc[:] = np.where(
                stradi.data_reader.full_df.values, self.full_df.values, 0)

        else:
            return stradi

        if samples:
            stradi.data_reader.sample_locs = self.transformed_data

        return stradi

    def evaluate_column_starts(self, close=True, base='starts_'):
        stradi = self.init_stradi(columns=False, axes=True)
        starts = stradi.data_reader._get_column_starts()
        ref = self.column_starts
        results = self.results.copy()
        missing_cols = len(ref) - len(starts)
        results[base + 'missmatch'] = 100 * (len(starts) - len(ref)) / len(ref)
        results[base + 'missing'] = missing_cols

        if not missing_cols:
            diff = np.abs(starts - ref).sum()
            width = np.diff(self.data_xlim)[0]
            results[base + 'rmse'] = rmse(starts, ref) * self.summed_perc / width
            results[base + 'abs'] = diff * self.summed_perc / width

            # now remove the yaxes
            stradi.data_reader.recognize_yaxes(remove=True)
            starts = stradi.data_reader.column_starts
            diff = np.abs(starts - ref).sum()
            results[base + 'rmse_removey'] = rmse(starts, ref) * \
                self.summed_perc / width
            results[base + 'abs_removey'] = \
                diff * self.summed_perc / width

        self.results = results
        return stradi.close() if close else stradi

    def evaluate_yaxes_removal(self, close=True):
        stradi = self.init_stradi(columns=False, axes=True)
        stradi_ref = self.init_stradi(digitize=False)

        # get the vertical axes that are the difference between the two images
        orig = stradi.data_reader.binary.copy()
        ref = (orig - stradi_ref.data_reader.binary).astype(bool)

        # remove the y-axes
        stradi.data_reader._get_column_starts()
        stradi.data_reader.recognize_yaxes(remove=True)
        sim = (orig - stradi.data_reader.binary).astype(bool)
        results = self.results

        ref_sum = ref.sum()
        # pixels that have wrongly considered as being part of the y-axes
        false_positive = sim & (~ref)
        # pixels that have wrongly not considered as being part of the y-axis
        false_negative = (~sim) & ref
        # pixels that have been identified correctly
        correct = sim & ref
        # calculate rmse
        results['yaxes_false_pos'] = 100 * false_positive.sum() / ref_sum
        results['yaxes_false_neg'] = 100 * false_negative.sum() / ref_sum
        results['yaxes_correct'] = 100 * correct.sum() / ref_sum

        self.results = results

        return (stradi.close(), stradi_ref.close()) if close else (
            stradi, stradi_ref)

    def evaluate_sample_accuracy(self, close=True, stradi=None,
                                 base='samples_'):
        stradi = stradi or self.init_stradi(digitize=False)
        stradi.data_reader.digitize()
        if stradi.data_reader.exaggerated_reader is not None:
            stradi.data_reader.digitize_exaggerated()
        results = self.results
        ref = self.data.fillna(0)
        full_df = stradi.full_df
        indexes = list(map(partial(full_df.index.get_loc, method='nearest'),
                           ref.index))
        sim = full_df.iloc[indexes].values
        ref = ref.values
        results[base + 'rmse'] = rmse(sim, ref)
        results[base + 'too_high'] = 100 * (sim > ref).sum() / ref.size
        results[base + 'too_low'] = 100 * (sim < ref).sum() / ref.size

        mask5p = ref.astype(bool) & (~np.isnan(ref)) & (ref <= 5)
        sim = sim[mask5p]
        ref = ref[mask5p]
        results[base + '5p_rmse'] = rmse(sim, ref)
        results[base + '5p_too_high'] = 100 * (sim > ref).sum() / ref.size
        results[base + '5p_too_low'] = 100 * (sim < ref).sum() / ref.size
        self.results = results
        return stradi.close() if close else stradi

    def evaluate_sample_position(self, close=True, stradi=None,
                                 base='samples_'):
        stradi = stradi or self.init_stradi(samples=False)
        stradi.data_reader.add_samples(
            *stradi.data_reader.find_samples(max_len=8))

        final = stradi.final_df
        ref = self.data
        nfound = len(final)
        nref = len(ref)

        results = self.results
        results[base + 'missmatch'] = 100 * abs(nfound - nref)/ nref
        results[base + 'missing'] = nref - nfound

        closest = list(map(
            partial(final.index.get_loc, method='nearest'),
            ref.index))

        age_range = ref.index.max() - ref.index.min()

        # normalized rmse of the age
        results[base + 'nrmse_y'] = rmse(
            final.index[closest].values, ref.index.values) / age_range * 100

        self.results = results
        return stradi.close() if close else stradi

    def evaluate_full(self, close=True):
        stradi = self.evaluate_column_starts(False, 'full_starts_')
        self.set_xtranslation(stradi)
        if len(stradi.data_reader.column_starts) == len(self.column_starts):
            stradi = self.evaluate_sample_accuracy(
                False, stradi, 'full_samples_')
            return self.evaluate_sample_position(
                close, stradi, 'full_samples_')

    def run(self):
        """Run all evaluations"""
        self.evaluate_column_starts()
        self.evaluate_yaxes_removal()
        self.evaluate_sample_accuracy()
        self.evaluate_sample_position()
        self.evaluate_full()

    def close(self):
        import matplotlib.pyplot as plt
        self.sp.close(figs=True, data=True, ds=True)
        del self.sp
        plt.close('all')


class NoVerticalsEvaluator(StraditizeEvaluator):
    """An evaluator for an image without y-axis"""

    def export(self, *args, **kwargs):
        super().export(*args, **kwargs)
        shutil.copyfile(self.filepath + '-no-axes.png', self.filepath + '.png')

    def evaluate_column_starts(self, close=True, base='starts_'):
        stradi = self.init_stradi(columns=False, axes=True)
        starts = stradi.data_reader._get_column_starts()
        ref = self.column_starts
        results = self.results.copy()
        missing_cols = len(ref) - len(starts)
        results[base + 'missmatch'] = 100 * (len(starts) - len(ref)) / len(ref)
        results[base + 'missing'] = missing_cols

        if not missing_cols:
            diff = np.abs(starts - ref).sum()
            width = np.diff(self.data_xlim)[0]
            results[base + 'rmse'] = rmse(starts, ref) * self.summed_perc / width
            results[base + 'abs'] = diff * self.summed_perc / width

        self.results = results
        return stradi.close() if close else stradi

    def evaluate_yaxes_removal(self, close=True):
        return


class ExaggerationsEvaluator(StraditizeEvaluator):
    """An evaluator with exaggerations"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # draw red exaggerations
        self.sp.update(exag_factor=5, exag='areax',
                       exag_color=[1, 0, 0, 1])

    def init_stradi(self, *args, **kwargs):
        stradi = super().init_stradi(*args, **kwargs)
        if stradi.data_reader is not None and stradi.data_reader.columns:
            exag = stradi.data_reader.create_exaggerations_reader(5)
            im = np.asarray(stradi.data_reader.image)
            mask = (im[..., 0] > 200) & (im[..., 1:-1].sum(axis=-1) < 100)
            exag.mark_as_exaggerations(mask)
        return stradi


class BaselineScenario:
    """The baseline evaluation scenario for straditize with data from POLNET

    This class uses the default settings of the :class:`StraditizeEvaluator`
    and runs the analysis for a given dataset from POLNET."""

    def __init__(self, output_dir='.'):
        self.output_dir = output_dir
        self.failed = []
        self._all_results = []
        self.results = None

    def __reduce__(self):
        return (self.__class__,
                (self.output_dir, ),
                {'failed': self.failed,
                 'results': self.results,
                 '_all_results': []
                 }
                )  # do not distribute all results

    def run(self, data, processes=None):
        self.failed.extend(data.e_.unique())
        all_results = self._all_results
        grouped = data.groupby('e_')
        progress_args = (grouped.ngroups, 'Progress', 'Complete', 50)

        print_progressbar(0, *progress_args)
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', 'Distinct samples merged from',
                                    UserWarning)
            warnings.filterwarnings('ignore', 'divide by zero encountered',
                                    RuntimeWarning)
            pool = mp.Pool(processes)
            for i, results in enumerate(pool.imap_unordered(self, grouped), 1):
                if np.ndim(results):
                    all_results.append(results)
                    self.failed.remove(int(results.name[0]))
                print_progressbar(i, *progress_args)
            pool.close()
            pool.join()
            pool.terminate()
        self.results = pd.concat(all_results, axis=1, sort=False).T
        self.results.index.names = self.index_names

    index_names = ['e_', 'ntaxa', 'nsamples']

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

    def __call__(self, data_tuple):
        key, group = data_tuple
        try:
            evaluator = self.init_evaluator(key, group)
        except Exception:
            return key
        else:
            try:
                self.export_evaluator(evaluator)
                evaluator.run()
            except Exception:
                evaluator.close()
                return key
        results = evaluator.results
        evaluator.close()
        return results


class DPI600Scenario(BaselineScenario):
    """Another evaluation scenario but with a resolution of 600 dpi"""

    def export_evaluator(self, *args, **kwargs):
        kwargs['dpi'] = 600
        return super().export_evaluator(*args, **kwargs)


class DPI150Scenario(BaselineScenario):
    """Another evaluation scenario but with a resolution of 150 dpi"""

    def export_evaluator(self, *args, **kwargs):
        kwargs['dpi'] = 150
        return super().export_evaluator(*args, **kwargs)


class BlackWhiteScenario(BaselineScenario):
    """An evaluation scenario with a binary (black and white) image"""

    def init_evaluator(self, *args, **kwargs):
        evaluator = super().init_evaluator(*args, **kwargs)
        evaluator.sp.update(color='k')
        return evaluator


class NoVerticalsScenario(BaselineScenario):
    """An evaluation scenario without y-axes in the plot"""

    def init_evaluator(self, name, data, *args, **kwargs):
        """Initialize an evaluator for a given data set"""
        import matplotlib.pyplot as plt
        if 'fig' not in kwargs:
            kwargs['fig'] = plt.figure(figsize=(12, 6))
        return NoVerticalsEvaluator.from_polnet(
            data, *args, name=str(name), **kwargs)


class ExaggerationsScenario(BaselineScenario):
    """An evaluation scenario with an exaggerated plot of low percentages"""

    def init_evaluator(self, name, data, *args, **kwargs):
        """Initialize an evaluator for a given data set"""
        import matplotlib.pyplot as plt
        if 'fig' not in kwargs:
            kwargs['fig'] = plt.figure(figsize=(12, 6))
        return ExaggerationsEvaluator.from_polnet(
            data, *args, name=str(name), **kwargs)
