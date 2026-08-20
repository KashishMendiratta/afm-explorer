from argparse import ArgumentParser
import pickle

import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from scipy.stats import linregress

@st.cache_data
def load_data(prefix):
    print(f"- Loading {prefix}{{.data.pickled,.heights.npy}}")
    hname = f"{prefix}.heights.npy"
    H = np.load(hname)
    m, n = H.shape
    fname = f"{prefix}.data.pickled"
    with open(fname, 'rb') as f:
        data = pickle.load(f)

    # Estimate all slopes
    slope_est = dict()  # maps tuple (s, i, j) to tuple (slope, anchors, info)
    for point, curve in data.items():
        s, i, j = point
        slope_est[point] = estimate_slope(curve, s)
    nseries = 1 + max(s for s, i, j in data.keys())
    slope_heatmaps = []
    for s in range(nseries):
        M = np.array([[(slope_est[s, i, j][0]) for j in range(n)] for i in range(m)], dtype=np.float64)
        slope_heatmaps.append(M)
    return H, data, slope_est, slope_heatmaps

def do_plot(point, curve, slope=None, anchors=None):
    """plot one distance-force curve with estimated slope"""
    s, i, j = point
    d, f = curve
    fig = plt.figure(figsize=[10, 6])
    plt.xlabel("distance (m)")
    plt.ylabel("force (N)")
    mode = 'push' if s == 0 else 'retract'
    plt.title(f"{mode} at ({i}, {j});  number of records: {len(d)}")
    label = f'data: {mode} at {(i, j)}'
    plt.scatter(d, f, s=1, label=label)
    plt.grid()
    if slope is not None and anchors is not None:
        anchor0, anchor1 = anchors[0], anchors[1]
        plt.axline(anchor0, slope=slope, color='red', linestyle='--', label=f'{slope:.4g} N/m')
        plt.plot([anchor0[0]], [anchor0[1]], 'rx')
        plt.plot([anchor1[0]], [anchor1[1]], 'rx')
    plt.legend()
    return fig

def estimate_slope(curve, s, nan=float("nan")):
    d, f = curve
    if s == 0:
        d, f = d[::-1], f[::-1]  # reverse d and f for series-0 spectra !

    # Downsample the data to speed up computation
    downsample_factor = 10
    d_down = d[::downsample_factor]
    f_down = f[::downsample_factor]

    # Apply a simple moving average filter to smooth the data
    window_size = 5
    f_smooth = np.convolve(f_down, np.ones(window_size) / window_size, mode='valid')
    d_smooth = d_down[:len(f_smooth)]

    # Select the region of interest (first 10% or at least 10 points)
    num_points = len(f_smooth)
    window_size = max(10, num_points // 10)
    best_slope = nan
    best_r_value = 0
    best_anchors = None

    # Iteratively find the best linear fit in the leftmost part
    for start in range(0, num_points - window_size):
        d_segment = d_smooth[start:start + window_size]
        f_segment = f_smooth[start:start + window_size]
        slope, intercept, r_value, p_value, std_err = linregress(d_segment, f_segment)
        if abs(r_value) > best_r_value:
            best_slope = slope
            best_r_value = abs(r_value)
            best_anchors = ((d_segment[0], f_segment[0]), (d_segment[-1], f_segment[-1]))

    # Return the best found slope and its anchors
    anchors = best_anchors if best_anchors else ((d_smooth[0], f_smooth[0]), (d_smooth[window_size], f_smooth[window_size]))
    info = {"r_value": best_r_value}

    return (best_slope, anchors, info)

# MAIN script

p = ArgumentParser()
p.add_argument("prefix",
    help="common path prefix for spectra (.data.pickled) and heights (.heights.npy)")
args = p.parse_args()
prefix = args.prefix

st.sidebar.title("AFM Data Explorer")
st.sidebar.write(f"Path prefix:\n'{prefix}'")
H, S, slope_est, slope_heatmaps = load_data(prefix)  # cached
m, n = H.shape
nseries = len(slope_heatmaps)

s = st.sidebar.selectbox('Select series', range(nseries))
i = st.sidebar.slider('Select vertical coordinate (i)', 0, m-1, 0)
j = st.sidebar.slider('Select horizontal coordinate (j)', 0, n-1, 0)

st.header('Heights Heatmap')
plt.imshow(H, cmap='turbo')
st.pyplot(plt)

st.header('Slope Heatmap')
plt.imshow(slope_heatmaps[s], cmap='turbo')
st.pyplot(plt)

st.header(f'Measurement at (s={s}, i={i}, j={j})')
point = (s, i, j)
curve = S[point]
slope, anchors, _ = slope_est[point]
fig = do_plot(point, curve, slope, anchors)
st.pyplot(fig)