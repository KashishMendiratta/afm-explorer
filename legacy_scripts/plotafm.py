from collections import Counter
from itertools import islice
from argparse import ArgumentParser
import numpy as np
import matplotlib.pyplot as plt


def extract_data_points(fname):
    # return a dict called 'data', such that
    # data[s, i, j] = (d, f),
    # where s is the series, i, j are the point coordinates;
    # d is a numpy array containing measured distances,
    # f is a numpy array containing measured forces.
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
                    print(f"Storing data for series {s}, point ({i},{j}) with {len(d)} data points")
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
                        print(f"Parsed iIndex: {i}") 
                    except ValueError as e:
                        print(f"Error parsing iIndex: {line}. Error: {e}")
            elif 'jIndex:' in line:
                parts = line.split(':')
                if len(parts) == 2:
                    try:
                        j = int(parts[1].strip())
                        print(f"Parsed jIndex: {j}")  
                    except ValueError as e:
                        print(f"Error parsing jIndex: {line}. Error: {e}")
            elif 'recorded-num-points' in line:
                num_points = int(line.split()[-1])
                print(f"Recorded num points: {num_points}")  
                collecting_data = True
        elif collecting_data:
            parts = line.split()
            if len(parts) >= 2:
                try:
                    d.append(float(parts[0]))
                    f.append(float(parts[1]))
                except ValueError as e:
                    print(f"Error parsing line: {line}. Error: {e}")

    # Store the last block's data if exists
    if d and f and s is not None and i is not None and j is not None:
        print(f"Storing data for series {s}, point ({i},{j}) at end with {len(d)} data points")
        data[(s, i, j)] = (np.array(d), np.array(f))

    print(f"Parsed data points: {data.keys()}")  
    return data


def raw_plot(point, curve, save=None, show=True):
    """plot one raw distance-force curve"""
    # point is the triple (s, i, j) with series s, iIndex i, jIndex j
    # curve is the pair (d, f) of two numpy arrays with distances and forces
    s, i, j = point
    d, f = curve
    plt.figure(figsize=[9, 6])
    plt.plot(d, f, label=f'Series {s}, Point ({i}, {j})')
    plt.xlabel('Distance (m)')
    plt.ylabel('Force (N)')
    plt.title(f'Measurement at (i={i}, j={j}, series={s})')
    plt.legend()
    plt.grid()
    if save is not None:
        plt.savefig(save, dpi=200, bbox_inches='tight')
    if show:
        plt.show()
    plt.close()


def do_raw_plots(data, show, plotprefix):
    for point, curve in data.items():
        s, i, j = point
        print(f"plotting curve at {point}")
        fname = f'{plotprefix}-{s:01d}-{i:03d}-{j:03d}.png' if plotprefix is not None else None
        raw_plot(point, curve, show=show, save=fname)


def main(args):
    fname = args.textfile
    print(f"parsing {fname}...")
    full_data = extract_data_points(fname)
    if args.first is not None:
        data = dict((k, v) for k, v in islice(full_data.items(), args.first))
    else:
        data = full_data
    do_raw_plots(data, args.show, args.plotprefix)


def get_argument_parser():
    p = ArgumentParser()
    p.add_argument("--textfile", "-t", required=True,
        help="name of the data file containing AFM curves for many points")
    p.add_argument("--first", type=int,
        help="number of curves to extract and plot")
    p.add_argument("--plotprefix", default="curve",
        help="non-empty path prefix of plot files (PNGs); do not save plots if not given")
    p.add_argument("--show", action="store_true",
        help="show each plot")
    return p


if __name__ == "__main__":
    p = get_argument_parser()
    args = p.parse_args()
    main(args)
