import argparse
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

def extract_data_points(fname):
    # Function to extract data points from the AFM text file
    data = dict()
    with open(fname, 'rt') as ftext:
        lines = ftext.readlines()

    s, i, j = None, None, None
    d, f = [], []
    collecting_data = False
    current_series = 0

    for line in lines:
        line = line.strip()

        if line.startswith('#'):
            if 'index:' in line:
                # Store the previous block's data if exists
                if d and f and s is not None and i is not None and j is not None:
                    data[(s, i, j)] = (np.array(d), np.array(f))
                    d, f = [], []  # Reset for new block

                # Alternate between series 0 and 1
                s = current_series
                current_series = (current_series + 1) % 2

            elif 'iIndex:' in line:
                parts = line.split(':')
                if len(parts) == 2:
                    try:
                        i = int(parts[1].strip())
                    except ValueError:
                        pass
            elif 'jIndex:' in line:
                parts = line.split(':')
                if len(parts) == 2:
                    try:
                        j = int(parts[1].strip())
                    except ValueError:
                        pass
            elif 'recorded-num-points' in line:
                num_points = int(line.split()[-1])
                collecting_data = True
        elif collecting_data:
            parts = line.split()
            if len(parts) >= 2:
                try:
                    d.append(float(parts[0]))
                    f.append(float(parts[1]))
                except ValueError:
                    pass

    # Store the last block's data if exists
    if d and f and s is not None and i is not None and j is not None:
        data[(s, i, j)] = (np.array(d), np.array(f))

    return data

def linear_func(x, m, c):
    return m * x + c

def fit_linear_segment(d, f, start_index=0, end_index=50):
    # Fit a linear model to a segment of the data
    d_segment = d[start_index:end_index]
    f_segment = f[start_index:end_index]
    
    popt, _ = curve_fit(linear_func, d_segment, f_segment)
    slope = popt[0]
    
    return slope

def find_best_linear_fit(d, f, window_size=50, step=10):
    best_slope = None
    best_intercept = None
    best_start = None
    best_end = None
    min_residuals = float('inf')
    
    for start in range(0, len(d) - window_size + 1, step):
        end = start + window_size
        d_window = d[start:end]
        f_window = f[start:end]
        
        popt, _ = curve_fit(linear_func, d_window, f_window)
        slope = popt[0]
        intercept = popt[1]
        
        residuals = np.sum((f_window - (slope * d_window + intercept)) ** 2)
        
        if residuals < min_residuals:
            min_residuals = residuals
            best_slope = slope
            best_intercept = intercept
            best_start = start
            best_end = end
    
    return best_slope, best_intercept, best_start, best_end


def raw_plot(point, curve, save=None, show=True):
    s, i, j = point
    d, f = curve

    fig, ax = plt.subplots(figsize=[9, 6])
    ax.plot(d, f, label=f'Push at Series {s}, Point ({i}, {j})')
    
    # Find the best linear fit for the data
    slope, intercept, start, end = find_best_linear_fit(d, f, window_size=50)
    
    
    if slope is not None and intercept is not None:
        # Extract a point on the line for ax.axline
        point_on_line = (d[start], intercept + slope * d[start])
        
        # Plot the fitted line
        ax.axline(point_on_line, slope=slope, color='r', linestyle='--', label=f'Fitted Line (slope={slope:.5f}) N/m')

        # Plot 'x' markers at the first and last points of the linear fit
        ax.plot(d[start], f[start], 'x', color='r', label='Start of Fit')
        ax.plot(d[end-1], f[end-1], 'x', color='r', label='End of Fit')

    ax.set_xlabel('Distance (m)')
    ax.set_ylabel('Force (N)')
    ax.set_title(f'Push at (i={i}, j={j}, series={s})')
    ax.legend()
    ax.grid()

    if save is not None:
        plt.savefig(save, dpi=200, bbox_inches='tight')
    if show:
        plt.show()
    plt.close()


def do_raw_plots(data, show, plotprefix):
    for point, curve in data.items():
        s, i, j = point
        fname = f'{plotprefix}-{s:01d}-{i:03d}-{j:03d}.png' if plotprefix is not None else None
        raw_plot(point, curve, show=show, save=fname)
        d, f = curve
        slope, intercept, _, _ = find_best_linear_fit(d, f)
        print(f"{s} {i:03d} {j:03d} {slope:.5f}")

def main(args):
    fname = args.textfile
    print(f"# parsing {fname}...")
    full_data = extract_data_points(fname)

    if args.first is not None:
        data = dict((k, v) for k, v in list(full_data.items())[:args.first])
    else:
        data = full_data

    print(f"# processing {len(data)} spectra...")
    do_raw_plots(data, args.show, args.plotprefix)

def get_argument_parser():
    p = argparse.ArgumentParser(description='Process AFM data and estimate slope of the left linear piece.')
    p.add_argument('--textfile', '-t', required=True, help='Name of the data file containing AFM curves for many points')
    p.add_argument('--first', type=int, help='Number of spectra to process')
    p.add_argument('--plotprefix', default=None, help='Non-empty path prefix of plot files (PNGs); do not save plots if not given')
    p.add_argument('--show', action='store_true', help='Show each plot')
    return p

if __name__ == '__main__':
    parser = get_argument_parser()
    args = parser.parse_args()
    main(args)
