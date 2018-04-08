"""Create the psyplot icon

This script creates the psyplot icon with a dpi of 128 and a width and height
of 8 inches. The file is saved it to ``'icon1024.png'``"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcol

fig = plt.figure(figsize=(8, 8), dpi=128)

ax = fig.add_axes([0.0, 0.0, 1.0, 1.0], facecolor='none')
ax.axis('off')

cmap = plt.get_cmap('binary')

xlines = np.arange(0, 41, 5)
nlines = len(xlines)

colors = np.r_[cmap(np.linspace(0, 0.9, nlines // 2)),
               cmap(np.linspace(0, 0.9, nlines // 2))[::-1]]

full_cmap = mcol.LinearSegmentedColormap.from_list('Reds_sedR', colors,
                                                   nlines)

x = np.array([
    2, 5, 1, 8, 0, 5, 0, 6, 1, 4, 7, 5, 1, 1, 5, 0, 4, 0, 6, 1, 4, 1, 5, 2, 6,
    8, 5, 0, 3, 0, 6, 2, 1, 3, 2, 5, 7, 5, 4, 3])

for i in xlines:
    ax.plot(x + i, np.arange(len(x)), color=full_cmap(i/40.), lw=10.0)

patch = mpatches.Circle((0.5, 0.5), radius=0.49, transform=ax.transAxes,
                        facecolor='k', zorder=0.5)
# the border of the circle
border = mpatches.Circle((0.5, 0.5), radius=0.49, transform=ax.transAxes,
                         facecolor='none', edgecolor='lightgray', linewidth=10,
                         zorder=10)

for l in ax.lines:
    l.set_clip_path(patch)

ax.add_patch(patch)
ax.add_patch(border)

ax.set_xlim(0, 45)
ax.set_ylim(2.5, 40)

plt.savefig('icon1024.png', transparent=True)
